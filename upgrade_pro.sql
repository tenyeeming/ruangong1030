-- 基本款資料庫升級到 Pro 版（只需執行一次）
-- mysql -u root -p --default-character-set=utf8mb4 < upgrade_pro.sql
-- 若已有重複報名資料，加 UNIQUE 會失敗，請先刪除重複的列

USE event_signup;

ALTER TABLE events ADD COLUMN deadline DATETIME AFTER event_date;
ALTER TABLE registrations ADD UNIQUE KEY uq_registration (event_id, name, phone);
