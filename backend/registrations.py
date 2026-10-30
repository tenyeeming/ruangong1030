"""秉軒：送出報名、查詢活動報名清單。"""

import re
from datetime import datetime

from flask import Blueprint, jsonify, request

from .db import cursor, execute, get_db

registrations_bp = Blueprint("registrations", __name__)


def error(message, status=400):
    return jsonify(ok=False, error=message), status


@registrations_bp.post("/api/events/<int:event_id>/register")
def register(event_id):
    if not request.is_json:
        return error("請使用 application/json 傳送資料", 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("請提供有效的 JSON 物件")

    name, phone = data.get("name"), data.get("phone")
    if not isinstance(name, str) or not isinstance(phone, str):
        return error("姓名和電話必須是字串且不可空白")
    name, phone = name.strip(), phone.strip()
    if not name or not phone:
        return error("姓名和電話必填")
    if len(name) > 50:
        return error("姓名不可超過 50 個字")
    # 和前端工作指南一致：台灣手機 09 開頭，共 10 碼，保留開頭的 0。
    if not re.fullmatch(r"09[0-9]{8}", phone):
        return error("電話須為 09 開頭的 10 位數字")

    with cursor() as result:
        execute(result, "SELECT id FROM events WHERE id = ?", (event_id,))
        if result.fetchone() is None:
            return error("活動不存在", 404)
        execute(
            result,
            "INSERT INTO registrations (event_id, name, phone) VALUES (?, ?, ?)",
            (event_id, name, phone),
        )
        get_db().commit()
    return jsonify(ok=True), 201


@registrations_bp.get("/api/events/<int:event_id>/registrations")
def list_registrations(event_id):
    with cursor() as result:
        execute(result, "SELECT id, title FROM events WHERE id = ?", (event_id,))
        event = result.fetchone()
        if event is None:
            return error("活動不存在", 404)
        execute(
            result,
            "SELECT name, phone, created_at FROM registrations "
            "WHERE event_id = ? ORDER BY created_at, id",
            (event_id,),
        )
        registrations = []
        for row in result.fetchall():
            timestamp = row["created_at"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            registrations.append({
                "name": row["name"],
                "phone": row["phone"],
                "created_at": timestamp.strftime("%Y-%m-%d %H:%M"),
            })
    response = jsonify(
        event={"id": event["id"], "title": event["title"]},
        registrations=registrations,
    )
    response.headers["Cache-Control"] = "no-store"
    return response
