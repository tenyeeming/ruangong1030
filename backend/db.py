"""共用資料庫連線；SQL 使用 ? 參數，MySQL 驅動改用 %s。"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g


def get_db():
    if "signup_db" not in g:
        if current_app.config["DB_DRIVER"] == "mysql":
            import pymysql

            g.signup_db = pymysql.connect(
                host=current_app.config["MYSQL_HOST"],
                port=int(current_app.config["MYSQL_PORT"]),
                user=current_app.config["MYSQL_USER"],
                password=current_app.config["MYSQL_PASSWORD"],
                database=current_app.config["MYSQL_DATABASE"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                connect_timeout=5,
                read_timeout=10,
                write_timeout=10,
            )
        else:
            path = Path(current_app.config["SQLITE_PATH"])
            path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(str(path), timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            g.signup_db = connection
    return g.signup_db


@contextmanager
def cursor():
    result = get_db().cursor()
    try:
        yield result
    finally:
        result.close()


def execute(result, sql, parameters=()):
    # 僅替換開發者寫死的 SQL 佔位符；使用者資料永遠另外傳入。
    if current_app.config["DB_DRIVER"] == "mysql":
        sql = sql.replace("?", "%s")
    return result.execute(sql, parameters)


def close_db(error=None):
    connection = g.pop("signup_db", None)
    if connection is not None:
        # 未 commit 的交易在 request 結束時回滾，包含失敗的寫入。
        try:
            connection.rollback()
        finally:
            connection.close()


def init_app(app):
    app.teardown_appcontext(close_db)
