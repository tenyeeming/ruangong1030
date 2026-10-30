"""Flask 啟動入口與本機測試命令；沒有實作組員的活動 API。"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import click
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from . import db
from .registrations import registrations_bp


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.json.ensure_ascii = False
    app.config.from_mapping(
        DB_DRIVER="sqlite",
        SQLITE_PATH=str(Path(app.instance_path) / "signup.db"),
        MYSQL_HOST="127.0.0.1",
        MYSQL_PORT=3306,
        MYSQL_USER="signup_user",
        MYSQL_PASSWORD="",
        MYSQL_DATABASE="event_signup",
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    app.config.from_prefixed_env(prefix="SIGNUP")
    if test_config:
        app.config.update(test_config)
    if app.config["DB_DRIVER"] not in ("sqlite", "mysql"):
        raise ValueError("SIGNUP_DB_DRIVER 必須是 sqlite 或 mysql")

    db.init_app(app)
    app.register_blueprint(registrations_bp)

    @app.errorhandler(HTTPException)
    def http_error(exception):
        messages = {
            400: "請求內容不正確",
            404: "找不到此 API，請檢查網址及活動 ID",
            405: "此 API 不支援這個 HTTP 方法",
            413: "送出的資料過大",
        }
        response = exception.get_response()
        response.data = app.json.dumps({
            "ok": False,
            "error": messages.get(exception.code, "請求失敗"),
        })
        response.content_type = "application/json; charset=utf-8"
        return response

    def database_error(exception):
        # 詳細錯誤留在本機 log；API 不回傳密碼、SQL 或內部路徑。
        app.logger.error("資料庫操作失敗", exc_info=True)
        return jsonify(ok=False, error="資料庫操作失敗，請確認連線與資料表設定"), 503

    app.register_error_handler(sqlite3.Error, database_error)
    if app.config["DB_DRIVER"] == "mysql":
        import pymysql

        app.register_error_handler(pymysql.MySQLError, database_error)

    @app.cli.command("init-demo")
    def init_demo():
        """只供 SQLite：建立測試資料表及一筆活動，不清除現有資料。"""
        if app.config["DB_DRIVER"] != "sqlite":
            raise click.ClickException("init-demo 僅支援 SQLite；MySQL 請匯入組員的 schema.sql")
        connection = db.get_db()
        schema = Path(__file__).with_name("sqlite_demo.sql").read_text(encoding="utf-8")
        connection.executescript(schema)
        row = connection.execute(
            "SELECT id FROM events WHERE title = ? ORDER BY id LIMIT 1",
            ("報名模組測試活動",),
        ).fetchone()
        if row is None:
            event_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            result = connection.execute(
                "INSERT INTO events (title, description, event_date) VALUES (?, ?, ?)",
                ("報名模組測試活動", "供秉軒測試兩支報名 API", event_date),
            )
            event_id = result.lastrowid
            connection.commit()
        else:
            event_id = row["id"]
        click.echo(f"SQLite 測試資料庫已就緒，活動 ID：{event_id}")

    return app
