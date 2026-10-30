-- 僅供 SQLite 本機試跑與自動測試，不取代活動模組負責的 MySQL schema.sql。
-- created_at 用本地時間，和 MySQL 的 CURRENT_TIMESTAMP 一致（SQLite 的 CURRENT_TIMESTAMP 是 UTC）。
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    event_date DATETIME,
    deadline DATETIME,
    created_at DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    created_at DATETIME DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (event_id) REFERENCES events(id),
    UNIQUE (event_id, name, phone)
);
