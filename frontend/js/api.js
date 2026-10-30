const USE_MOCK = true;           // 後端好了改成 false
const BASE = "/api";

const mockEvents = [
  { id: 1, title: "迎新晚會", description: "地點：活動中心", event_date: "2026-11-10 18:00" },
  { id: 2, title: "程式讀書會", description: "地點：E301", event_date: "2026-11-15 19:00" },
];

async function getEvents() {
  if (USE_MOCK) return mockEvents;
  return (await fetch(`${BASE}/events`)).json();
}

async function createEvent(data) {
  if (USE_MOCK) return { ok: true, id: 99 };
  return (await fetch(`${BASE}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })).json();
}

async function register(eventId, data) {
  if (USE_MOCK) return { ok: true };
  return (await fetch(`${BASE}/events/${eventId}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })).json();
}

async function getRegistrations(eventId) {
  if (USE_MOCK) return {
    event: { id: eventId, title: "迎新晚會" },
    registrations: [{ name: "王小明", phone: "0912345678", created_at: "2026-10-30 14:00" }],
  };
  return (await fetch(`${BASE}/events/${eventId}/registrations`)).json();
}
