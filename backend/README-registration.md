# 秉軒：報名模組使用與上傳教學

本模組使用 Python 3.10 以上與 Flask，實作基本款的兩支報名 API。
`backend/registrations.py` 是主要負責檔案；`db.py`、`app.py` 是可供小組整合的共用基礎。
尚未實作活動模組、前端、管理員登入或 Pro 版功能。

## 1. 本機執行（Windows PowerShell）

先到你克隆的專案根目錄：

```powershell
cd "C:\Users\User\Desktop\軟工1030"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example .env
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app init-demo
.\.venv\Scripts\python.exe -m flask --app backend.app:create_app run --port 5000
```

不需要啟用虛擬環境，因此不受 PowerShell 腳本執行原則影響。
`.env` 已存在時請直接編輯，勿重複複製覆蓋密碼。
`init-demo` 會顯示測試活動 ID，首次執行為 1。請讓這個視窗保持執行。
資料存在 Flask instance 資料夾的 `signup.db`，重開伺服器後仍會保留；`.gitignore` 已排除。
所有命令都從專案根目錄執行。若 `python` 無法使用，改用 `py -3`。

這是 API 後端，沒有首頁；瀏覽 `http://127.0.0.1:5000/` 出現 JSON 404 是正常現象。
Flask 的開發伺服器用於本機驗證；push 到 GitHub 也不會自動變成可執行的公開網站。

## 2. 手動驗證兩支 API

另開一個 PowerShell 視窗。如果 init-demo 顯示的 ID 不是 1，請更改 `$eventId`。

```powershell
$eventId = 1
$baseUrl = "http://127.0.0.1:5000/api/events/$eventId"
$payload = @{ name = "王小明"; phone = "0912345678" } | ConvertTo-Json
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)

# 正常報名，預期回傳 ok: True，HTTP 201
Invoke-RestMethod -Uri "$baseUrl/register" -Method Post -ContentType "application/json; charset=utf-8" -Body $bodyBytes

# 查看清單；ConvertTo-Json 用來完整顯示巢狀資料
Invoke-RestMethod -Uri "$baseUrl/registrations" | ConvertTo-Json -Depth 5
```

Postman 也可使用：POST `http://127.0.0.1:5000/api/events/1/register`，
Body 選 raw → JSON，填入 `{"name":"王小明","phone":"0912345678"}`。

## 3. API 規格

`POST /api/events/{id}/register`

```json
{"name":"王小明","phone":"0912345678"}
```

成功：HTTP 201，`{"ok":true}`。
姓名、電話會去除前後空白；姓名限 1–50 字，電話依前端文件檢查為 `09` 開頭的 10 位數字。
電話請傳字串，以保留開頭的 0。
Pro：同一活動同名且同電話視為重複報名，回 HTTP 409；活動超過 `deadline` 後回 HTTP 403「此活動已截止報名」。
資料表另有 `UNIQUE (event_id, name, phone)`，兩人同時送出也只會成功一筆。

`GET /api/events/{id}/registrations`

成功：HTTP 200，格式如下。沒有報名資料時 `registrations` 是 `[]`。
清單依報名時間、ID 遞增排序，只回傳指定活動的資料。
報名時間依資料庫的時間設定，MySQL 整合時請小組統一資料庫時區。

```json
{
  "event": {"id": 1, "title": "迎新晚會"},
  "count": 1,
  "registrations": [
    {"name": "王小明", "phone": "0912345678", "created_at": "2026-10-30 14:00"}
  ]
}
```

失敗一律回 `{"ok":false,"error":"原因"}`：欄位或 JSON 錯誤為 400、已截止報名為 403、
活動不存在為 404、不支援的方法為 405、重複報名為 409、資料過大為 413、未使用 JSON 為 415、資料庫操作失敗為 503。
SQL 使用參數化查詢；資料庫錯誤細節留在伺服器 log。

## 4. 切換到小組的 MySQL

SQLite 是本機驗證模式，不會與 MySQL 自動同步。和組員整合時，請先取得活動模組負責人的
`schema.sql`，由該檔建立 `events`、`registrations` 表，不要把 `sqlite_demo.sql` 匯入 MySQL。
MySQL 服務及資料庫需事先建立，並使用有查詢及新增權限的帳號。

修改根目錄 `.env`，填入自己的連線設定：

```dotenv
SIGNUP_DB_DRIVER=mysql
SIGNUP_MYSQL_HOST=127.0.0.1
SIGNUP_MYSQL_PORT=3306
SIGNUP_MYSQL_USER=signup_user
SIGNUP_MYSQL_PASSWORD=自己的資料庫密碼
SIGNUP_MYSQL_DATABASE=event_signup
```

若密碼包含 `#` 或空白，請用單引號包住整個值。
停止伺服器（Ctrl+C）後，重新執行 `flask ... run` 命令才會載入新設定。
MySQL 模式不使用 `init-demo`；先以活動模組新增活動，或由組員執行文件中的測試活動 INSERT。
再使用真實活動 ID 重做第 2 節測試。

主要 SQL 仍使用文件的 `?`，`db.execute()` 會轉為 PyMySQL 的 `%s`，資料另以參數傳入。
不會建立、刪除或修改小組的 MySQL 資料表。

## 5. 和組員整合

已經使用這個 `create_app()` 的活動模組，可在 `backend/app.py` 內加入：

```python
from .events import events_bp
app.register_blueprint(events_bp)
```

上面假設組員把活動 Blueprint 命名為 `events_bp`；請依對方實際名稱調整。
活動模組可共用 `backend.db` 的 `cursor`、`execute`、`get_db`。

如果組員已有另一個 Flask 入口，請把本入口的資料庫設定、`db.init_app(app)`、
`app.register_blueprint(registrations_bp)` 與錯誤處理合併到該入口，最後只啟動一個 Flask 應用程式。
不要各自在同一個 port 啟動一個伺服器。

前端使用相同的 API 路徑，將 `USE_MOCK` 改成 `false` 即可串接。
前端與 API 應使用同一個來源；若前端另開 Live Server（不同 port），需由小組另行設定代理或允許指定來源的 CORS。
目前沒有加入開放所有來源的 CORS。報名清單依基本款規格公開，課堂展示請使用假姓名與電話。

## 6. 自動測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

測試使用獨立的暫存 SQLite 資料庫，涵蓋正常報名、空白與錯誤欄位、活動不存在、空清單、
活動間資料隔離、排序、SQL 注入字串、交易失敗回滾、JSON 錯誤格式與資料庫驅動參數轉換。
不會修改本機試跑資料，也不需要 MySQL；實際 MySQL 連線須在第 4 節設定後另外驗證。

## 7. 由你自己 commit、push

本次程式碼沒有自動 commit 或 push。先確認分支及變更：

```powershell
cd "C:\Users\User\Desktop\軟工1030"
git branch --show-current
git status
git diff
```

應在 `feature/registration`；如果仍在 main，先執行 `git switch -c feature/registration`。
若提示分支已存在，改用 `git switch feature/registration`。

確認 `.env`、`.venv`、`instance`、資料庫檔案沒有出現在待提交清單。
`git diff` 不會顯示尚未追蹤的新檔內容，因此在下一步暫存後用 `git diff --cached` 再確認。

```powershell
git add .gitignore backend
git diff --cached --stat
git diff --cached
git commit -m "完成報名與報名清單 API"
git push -u origin feature/registration
```

如果 commit 顯示 `Author identity unknown`，先設定你自己的資訊，再重新執行 commit：

```powershell
git config user.name "你的名字"
git config user.email "你的 GitHub 電子郵件或 noreply 電子郵件"
```

push 時依 Git 的提示登入你自己的 GitHub 帳號；該帳號需要此倉庫的寫入權限，
否則請倉庫擁有者加入你為 collaborator 並接受邀請。不要輸入 GitHub 帳號密碼當作 Git 密碼，
也不要把存取權杖貼進程式碼或遠端網址。

push 成功後，開啟 https://github.com/tenyeeming/ruangong1030 ，選 **Compare & pull request**：

1. base 選 `main`，compare 選 `feature/registration`。
2. 標題填「完成報名與報名清單 API」。
3. 說明填入兩支 API、使用 Flask、測試結果，以及「MySQL 連線待小組整合驗證」。
4. 按 **Create pull request**，請組員檢查後合併。

若 push 顯示遠端同名分支已有其他提交，先停止並檢查差異，不要使用 `--force` 覆蓋組員工作。
GitHub 儲存程式碼；GitHub Pages 無法執行這個 Python／資料庫後端。

## 參考

- Flask Blueprint：https://flask.palletsprojects.com/en/stable/blueprints/
- PyMySQL 參數化查詢與 commit：https://pymysql.readthedocs.io/en/latest/user/examples.html
