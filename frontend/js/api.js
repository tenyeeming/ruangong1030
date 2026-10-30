const USE_MOCK = true;           // 後端好了改成 false
const BASE = "/api";

const mockEvents = [
  { id: 1, title: "迎新晚會", description: "地點：活動中心", event_date: "2026-11-10 18:00" },
  { id: 2, title: "程式讀書會", description: "地點：E301", event_date: "2026-11-15 19:00" },
];

// 使用者輸入的內容放進 innerHTML 前一定要先跳脫，避免 XSS
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// 連線失敗或回傳不是 JSON 時，統一回 { ok: false, error }
async function request(url, options) {
  try {
    const res = await fetch(url, options);
    return await res.json();
  } catch (err) {
    return { ok: false, error: "無法連線到伺服器" };
  }
}

function postJson(url, data) {
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

async function getEvents() {
  if (USE_MOCK) return mockEvents;
  return request(`${BASE}/events`);
}

async function createEvent(data) {
  if (USE_MOCK) return { ok: true, id: 99 };
  return postJson(`${BASE}/events`, data);
}

async function register(eventId, data) {
  if (USE_MOCK) return { ok: true };
  return postJson(`${BASE}/events/${encodeURIComponent(eventId)}/register`, data);
}

async function getRegistrations(eventId) {
  if (USE_MOCK) return {
    event: { id: eventId, title: "迎新晚會" },
    registrations: [{ name: "王小明", phone: "0912345678", created_at: "2026-10-30 14:00" }],
  };
  return request(`${BASE}/events/${encodeURIComponent(eventId)}/registrations`);
}
