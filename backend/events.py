"""活動模組：新增活動、活動清單。"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from .db import cursor, execute, get_db

events_bp = Blueprint("events", __name__)

# 接受 "2026-11-10 18:00" 與 <input type="datetime-local"> 的 "2026-11-10T18:00"
DATE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def error(message, status=400):
    return jsonify(ok=False, error=message), status


def parse_event_date(text):
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    return None


def format_datetime(value):
    # SQLite 回傳字串、PyMySQL 回傳 datetime，統一成 API 規格的格式。
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%Y-%m-%d %H:%M")


@events_bp.get("/api/events")
def list_events():
    with cursor() as result:
        execute(
            result,
            "SELECT id, title, description, event_date FROM events "
            "ORDER BY event_date IS NULL, event_date, id",
        )
        events = [
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "event_date": format_datetime(row["event_date"]),
            }
            for row in result.fetchall()
        ]
    response = jsonify(events)
    response.headers["Cache-Control"] = "no-store"
    return response


@events_bp.post("/api/events")
def create_event():
    if not request.is_json:
        return error("請使用 application/json 傳送資料", 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("請提供有效的 JSON 物件")

    title = data.get("title")
    description = data.get("description") or ""
    event_date = data.get("event_date") or ""
    if not all(isinstance(value, str) for value in (title, description, event_date)):
        return error("活動名稱、說明、日期必須是字串")
    title, description, event_date = title.strip(), description.strip(), event_date.strip()
    if not title:
        return error("活動名稱必填")
    if len(title) > 100:
        return error("活動名稱不可超過 100 個字")

    parsed_date = None
    if event_date:
        parsed_date = parse_event_date(event_date)
        if parsed_date is None:
            return error("活動日期格式錯誤，應為 YYYY-MM-DD HH:MM")

    with cursor() as result:
        execute(
            result,
            "INSERT INTO events (title, description, event_date) VALUES (?, ?, ?)",
            (
                title,
                description or None,
                parsed_date.strftime("%Y-%m-%d %H:%M:%S") if parsed_date else None,
            ),
        )
        event_id = result.lastrowid
        get_db().commit()
    return jsonify(ok=True, id=event_id), 201
