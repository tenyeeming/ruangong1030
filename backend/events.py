"""活動模組：新增活動、活動清單（Pro：截止時間、報名人數）。"""

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


def to_datetime(value):
    # SQLite 回傳字串、PyMySQL 回傳 datetime，統一轉成 datetime。
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def format_datetime(value):
    value = to_datetime(value)
    return value.strftime("%Y-%m-%d %H:%M") if value else None


def is_closed(deadline):
    # 截止時間當下仍可報名，超過才算截止；沒有設定截止時間就永遠開放。
    deadline = to_datetime(deadline)
    return deadline is not None and datetime.now() > deadline


@events_bp.get("/api/events")
def list_events():
    with cursor() as result:
        execute(
            result,
            "SELECT e.id, e.title, e.description, e.event_date, e.deadline, "
            "(SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id) AS count "
            "FROM events e "
            "ORDER BY e.event_date IS NULL, e.event_date, e.id",
        )
        events = [
            {
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "event_date": format_datetime(row["event_date"]),
                "deadline": format_datetime(row["deadline"]),
                "is_closed": is_closed(row["deadline"]),
                "count": int(row["count"]),
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
    deadline = data.get("deadline") or ""
    if not all(isinstance(value, str) for value in (title, description, event_date, deadline)):
        return error("活動名稱、說明、日期、截止時間必須是字串")
    title, description = title.strip(), description.strip()
    event_date, deadline = event_date.strip(), deadline.strip()
    if not title:
        return error("活動名稱必填")
    if len(title) > 100:
        return error("活動名稱不可超過 100 個字")

    parsed_date = None
    if event_date:
        parsed_date = parse_event_date(event_date)
        if parsed_date is None:
            return error("活動日期格式錯誤，應為 YYYY-MM-DD HH:MM")

    parsed_deadline = None
    if deadline:
        parsed_deadline = parse_event_date(deadline)
        if parsed_deadline is None:
            return error("報名截止時間格式錯誤，應為 YYYY-MM-DD HH:MM")
        if parsed_date and parsed_deadline > parsed_date:
            return error("報名截止時間不可晚於活動時間")

    def to_db(value):
        return value.strftime("%Y-%m-%d %H:%M:%S") if value else None

    with cursor() as result:
        execute(
            result,
            "INSERT INTO events (title, description, event_date, deadline) VALUES (?, ?, ?, ?)",
            (title, description or None, to_db(parsed_date), to_db(parsed_deadline)),
        )
        event_id = result.lastrowid
        get_db().commit()
    return jsonify(ok=True, id=event_id), 201
