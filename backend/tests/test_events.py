"""使用獨立的 SQLite 檔案驗證活動 API，不會碰到開發或 MySQL 資料庫。"""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from backend.app import create_app


class EventTests(unittest.TestCase):
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
        with closing(sqlite3.connect(self.path)) as connection:
            connection.executescript(schema.read_text(encoding="utf-8"))

    def create(self, payload):
        return self.client.post("/api/events", json=payload)

    def test_empty_list(self):
        response = self.client.get("/api/events")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    def test_create_and_list_matches_contract(self):
        response = self.create({
            "title": " 迎新晚會 ", "description": "地點：活動中心", "event_date": "2026-11-10T18:00",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"ok": True, "id": 1})
        self.assertEqual(self.client.get("/api/events").json, [{
            "id": 1, "title": "迎新晚會", "description": "地點：活動中心", "event_date": "2026-11-10 18:00",
        }])

    def test_optional_fields(self):
        self.assertEqual(self.create({"title": "只有名稱"}).status_code, 201)
        event = self.client.get("/api/events").json[0]
        self.assertIsNone(event["description"])
        self.assertIsNone(event["event_date"])

    def test_list_is_ordered_by_date_with_undated_last(self):
        self.create({"title": "未定"})
        self.create({"title": "後", "event_date": "2026-12-01 10:00"})
        self.create({"title": "先", "event_date": "2026-11-01 10:00"})
        titles = [event["title"] for event in self.client.get("/api/events").json]
        self.assertEqual(titles, ["先", "後", "未定"])

    def test_invalid_fields(self):
        for payload in (
            {}, {"title": "  "}, {"title": None}, {"title": 123},
            {"title": "王" * 101},
            {"title": "活動", "event_date": "明天"},
            {"title": "活動", "event_date": "2026-13-01 10:00"},
            {"title": "活動", "description": ["x"]},
        ):
            with self.subTest(payload=payload):
                response = self.create(payload)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json["ok"])
                self.assertTrue(response.json["error"])

    def test_title_length_boundary(self):
        self.assertEqual(self.create({"title": "王" * 100}).status_code, 201)

    def test_invalid_json_and_content_type(self):
        response = self.client.post("/api/events", data='{"title":', content_type="application/json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/events", data={"title": "活動"})
        self.assertEqual(response.status_code, 415)

    def test_created_event_accepts_registration(self):
        event_id = self.create({"title": "整合測試"}).json["id"]
        response = self.client.post(
            f"/api/events/{event_id}/register", json={"name": "王小明", "phone": "0912345678"},
        )
        self.assertEqual(response.status_code, 201)
        rows = self.client.get(f"/api/events/{event_id}/registrations").json["registrations"]
        self.assertEqual(len(rows), 1)

    def test_frontend_is_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("活動清單", response.get_data(as_text=True))
        response.close()
        for path in ("/index.html", "/create.html", "/register.html", "/registrations.html",
                     "/css/style.css", "/js/api.js"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()
        response = self.client.get("/nope.html")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json["ok"])


if __name__ == "__main__":
    unittest.main()
