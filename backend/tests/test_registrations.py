"""使用獨立的 SQLite 檔案驗證 API，不會碰到開發或 MySQL 資料庫。"""

import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import patch

from backend.app import create_app
from backend.db import execute


@contextmanager
def database(path):
    # SQLite 的交易 context manager 不會 close；Windows 測試須明確關閉檔案。
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            yield connection


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        temporary_root = Path(__file__).parents[2] / "instance" / "test-temp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "test.db"
        self.app = create_app({
            "TESTING": True,
            "DB_DRIVER": "sqlite",
            "SQLITE_PATH": str(self.path),
        })
        self.client = self.app.test_client()
        schema = Path(__file__).parents[1] / "sqlite_demo.sql"
        with database(self.path) as connection:
            connection.executescript(schema.read_text(encoding="utf-8"))
            connection.executemany(
                "INSERT INTO events (id, title) VALUES (?, ?)",
                [(1, "迎新晚會"), (2, "程式讀書會")],
            )

    def signup(self, payload, event_id=1):
        return self.client.post(f"/api/events/{event_id}/register", json=payload)

    def test_register_persists_and_list_matches_contract(self):
        response = self.signup({"name": " 王小明 ", "phone": " 0912345678 "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"ok": True})
        self.assertTrue(response.is_json)
        response = self.client.get("/api/events/1/registrations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["event"], {"id": 1, "title": "迎新晚會"})
        self.assertEqual(len(response.json["registrations"]), 1)
        row = response.json["registrations"][0]
        self.assertEqual(row["name"], "王小明")
        self.assertEqual(row["phone"], "0912345678")
        self.assertEqual(set(row), {"name", "phone", "created_at"})
        self.assertRegex(row["created_at"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_missing_blank_or_non_string_fields(self):
        for payload in (
            {}, {"name": "王小明"}, {"phone": "0912345678"},
            {"name": "  ", "phone": "0912345678"},
            {"name": "王小明", "phone": " "},
            {"name": None, "phone": "0912345678"},
            {"name": ["王小明"], "phone": "0912345678"},
            {"name": "王小明", "phone": 912345678},
        ):
            with self.subTest(payload=payload):
                response = self.signup(payload)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json["ok"])
                self.assertTrue(response.json["error"])

    def test_invalid_phone(self):
        for phone in ("123", "09123456789", "0812345678", "09abcdefgh", "09１２３４５６７８"):
            with self.subTest(phone=phone):
                self.assertEqual(self.signup({"name": "小明", "phone": phone}).status_code, 400)

    def test_name_length_boundary(self):
        self.assertEqual(self.signup({"name": "王" * 50, "phone": "0912345678"}).status_code, 201)
        self.assertEqual(self.signup({"name": "王" * 51, "phone": "0912345678"}).status_code, 400)

    def test_invalid_json(self):
        for body in ('{"name":', "[]", "null", '"text"'):
            with self.subTest(body=body):
                response = self.client.post(
                    "/api/events/1/register", data=body, content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json["ok"])

    def test_wrong_content_type(self):
        response = self.client.post("/api/events/1/register", data={"name": "小明"})
        self.assertEqual(response.status_code, 415)
        self.assertFalse(response.json["ok"])

    def test_nonexistent_event_for_both_endpoints(self):
        responses = [
            self.signup({"name": "王小明", "phone": "0912345678"}, 999),
            self.client.get("/api/events/999/registrations"),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json, {"ok": False, "error": "活動不存在"})

    def test_empty_registration_list(self):
        response = self.client.get("/api/events/1/registrations")
        self.assertEqual(response.json, {
            "event": {"id": 1, "title": "迎新晚會"}, "registrations": [],
        })

    def test_does_not_mix_other_events(self):
        self.signup({"name": "王小明", "phone": "0912345678"}, 2)
        self.assertEqual(self.client.get("/api/events/1/registrations").json["registrations"], [])
        self.assertEqual(len(self.client.get("/api/events/2/registrations").json["registrations"]), 1)

    def test_list_is_ordered_by_time_then_id(self):
        with database(self.path) as connection:
            connection.executemany(
                "INSERT INTO registrations (event_id, name, phone, created_at) VALUES (1, ?, ?, ?)",
                [("後", "0912345678", "2026-10-30 15:00:00"),
                 ("先", "0912345679", "2026-10-30 14:00:00"),
                 ("同時", "0912345680", "2026-10-30 14:00:00")],
            )
        rows = self.client.get("/api/events/1/registrations").json["registrations"]
        self.assertEqual([row["name"] for row in rows], ["先", "同時", "後"])

    def test_sql_injection_text_is_stored_as_data(self):
        name = "Robert'); DROP TABLE events;--"
        self.assertEqual(self.signup({"name": name, "phone": "0912345678"}).status_code, 201)
        response = self.client.get("/api/events/1/registrations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["registrations"][0]["name"], name)

    def test_failed_commit_rolls_back_and_returns_json(self):
        with patch("backend.registrations.get_db") as connection:
            connection.return_value.commit.side_effect = sqlite3.OperationalError("test failure")
            with self.assertLogs(self.app.logger, level="ERROR"):
                response = self.signup({"name": "小明", "phone": "0912345678"})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json["ok"])
        self.assertNotIn("test failure", response.get_data(as_text=True))
        self.assertEqual(self.client.get("/api/events/1/registrations").json["registrations"], [])

    def test_bad_routes_methods_and_oversized_body_return_json(self):
        for response, status in (
            (self.client.get("/not-an-api"), 404),
            (self.client.get("/api/events/1/register"), 405),
            (self.signup({"name": "王" * 20000, "phone": "0912345678"}), 413),
        ):
            self.assertEqual(response.status_code, status)
            self.assertFalse(response.json["ok"])

    def test_init_demo_is_repeatable_without_deleting_registrations(self):
        self.signup({"name": "王小明", "phone": "0912345678"})
        runner = self.app.test_cli_runner()
        self.assertEqual(runner.invoke(args=["init-demo"]).exit_code, 0)
        self.assertEqual(runner.invoke(args=["init-demo"]).exit_code, 0)
        with database(self.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM events").fetchone()[0], 3)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM registrations").fetchone()[0], 1)

    def test_mysql_placeholder_adapter_keeps_values_separate(self):
        # 驗證驅動適配；實際 MySQL 連線仍需小組的資料庫測試。
        with self.app.app_context(), patch("backend.db.get_db") as connection:
            self.app.config["DB_DRIVER"] = "mysql"
            result = connection.return_value.cursor.return_value
            execute(result, "SELECT id FROM events WHERE id = ?", (1,))
            result.execute.assert_called_once_with("SELECT id FROM events WHERE id = %s", (1,))


if __name__ == "__main__":
    unittest.main()
