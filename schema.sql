-- 活動報名平台（Pro 版）
-- 新建：mysql -u root -p --default-character-set=utf8mb4 < schema.sql
-- 已用基本款建過資料表：改執行 upgrade_pro.sql

CREATE DATABASE IF NOT EXISTS event_signup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE event_signup;

CREATE TABLE IF NOT EXISTS events (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  title       VARCHAR(100) NOT NULL,
  description TEXT,
  event_date  DATETIME,
  deadline    DATETIME,              -- Pro：報名截止時間，NULL 表示不截止
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registrations (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  event_id   INT NOT NULL,
  name       VARCHAR(50) NOT NULL,
  phone      VARCHAR(20) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES events(id),
  UNIQUE KEY uq_registration (event_id, name, phone)   -- Pro：同一活動不可同名且同電話重複報名
);
