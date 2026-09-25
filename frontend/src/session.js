// Identifiant de session de conversation (US-002).
// Stocké dans sessionStorage : il survit au rafraîchissement de la page,
// mais disparaît à la fermeture de l'onglet. C'est un UUID aléatoire :
// aucune donnée personnelle n'est utilisée (RGPD).
// US-003 (redémarrer la conversation) utilisera resetSessionId().

const STORAGE_KEY = "esic-chat-session-id";

export function getSessionId() {
  let sessionId = sessionStorage.getItem(STORAGE_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(STORAGE_KEY, sessionId);
  }
  return sessionId;
}

export function resetSessionId() {
  const sessionId = crypto.randomUUID();
  sessionStorage.setItem(STORAGE_KEY, sessionId);
  return sessionId;
}
