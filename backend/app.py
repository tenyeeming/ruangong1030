"""Flask 啟動入口與本機測試命令；整合活動 API、報名 API 與前端頁面。"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import click
from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

from . import db
from .events import events_bp
from .registrations import registrations_bp

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True, static_folder=None)
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
    # from_prefixed_env 會把純數字密碼解析成 int，PyMySQL 只接受字串
    app.config["MYSQL_PASSWORD"] = str(app.config["MYSQL_PASSWORD"])

    db.init_app(app)
    app.register_blueprint(events_bp)
    app.register_blueprint(registrations_bp)

    # 前端與 API 同一個來源，前端不需要 CORS。
    # 只開放頁面、css、js 的網址；不用萬用路由，API 打錯方法才會回 405 而不是 404。
    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<page>.html")
    def page(page):
        return send_from_directory(FRONTEND_DIR, f"{page}.html")

    @app.get("/css/<path:filename>")
    def css(filename):
        return send_from_directory(FRONTEND_DIR / "css", filename)

    @app.get("/js/<path:filename>")
    def js(filename):
        return send_from_directory(FRONTEND_DIR / "js", filename)

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
