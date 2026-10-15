// Service d'appel au backend.
const API_URL = import.meta.env?.VITE_API_URL ?? "http://localhost:5000";
const USE_MOCK = false;

// --- Identifiant de session, gardé dans le navigateur (survit à un F5) ---
const SESSION_KEY = "chatbot_session_id";

export function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

// Contrat : POST /api/chat   body: { question, session_id }   ->   { answer }
export async function sendQuestion(question) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 800));
    return `Réponse simulée : vous avez demandé « ${question} ».`;
  }
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: getSessionId() }),
  });
  if (!res.ok) throw new Error(`Erreur serveur (${res.status})`);
  const data = await res.json();
  return data.answer;
}

// Contrat : GET /api/history/<session_id>   ->   { history: [{ question, answer, time }] }
export async function fetchHistory() {
  const res = await fetch(`${API_URL}/api/history/${getSessionId()}`);
  if (!res.ok) throw new Error(`Erreur serveur (${res.status})`);
  const data = await res.json();
  return data.history;
}