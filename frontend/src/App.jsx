
import { useEffect, useRef, useState } from "react";
import "./styles.css";
import Dashboard from "./Dashboard";

const API_URL = "http://127.0.0.1:8000";

const WELCOME_MESSAGE = {
  id: "welcome",
  sender: "bot",
  text: "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. Comment puis-je vous aider ?",
  time: new Date().toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  }),
};

const SUGGESTIONS = [
  "Quels sont les horaires de la bibliothèque ?",
  "Comment contacter la scolarité ?",
  "Quelles sont les règles du campus ?",
  "Quelles sont les sanctions en cas de fraude ?",
  "Quand sont les examens ?",
  "Quelles sont les vacances ?",
  "Quand sont les rattrapages ?",
  "Quelles sont les dates importantes ?",
];

const UI_TEXT = {
  fr: { subtitle: "Assistant virtuel éducatif", online: "En ligne", newChat: "+ Nouvelle conversation", history: "Historique", noHistory: "Aucune conversation", admin: "Administration", kiosk: "Mode Borne", exitKiosk: "Quitter le mode Borne", welcome: "Je suis l’assistant virtuel éducatif ESIC.", welcomePrompt: "Posez-moi votre question pour commencer.", suggestions: "Questions fréquentes", placeholder: "Écrivez votre question...", inputHint: "Appuyez sur Entrée pour envoyer ou sur le microphone pour dicter votre question.", user: "Vous", language: "Langue", emptyAnswer: "Je n'ai pas reçu de réponse du serveur." },
  en: { subtitle: "Educational virtual assistant", online: "Online", newChat: "+ New conversation", history: "History", noHistory: "No conversations yet", admin: "Administration", kiosk: "Kiosk mode", exitKiosk: "Exit kiosk mode", welcome: "I’m the ESIC educational virtual assistant.", welcomePrompt: "Ask me a question to get started.", suggestions: "Frequently asked questions", placeholder: "Type your question...", inputHint: "Press Enter to send or use the microphone to dictate your question.", user: "You", language: "Language", emptyAnswer: "I did not receive a response from the server." }
};

const SUGGESTIONS_EN = [
  "What are the library opening hours?",
  "How can I contact the student office?",
  "What are the campus rules?",
  "What are the penalties for cheating?",
  "When are the exams?",
  "When are the holidays?",
  "When are the resit exams?",
  "What are the important dates?",
];

function currentTime() {
  return new Date().toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || `Erreur serveur (${response.status}).`);
  }

  return data;
}

// US-030 — identifiant pseudonyme de la borne et journalisation centralisée.
function getKioskId() {
  const storageKey = "esicKioskId";
  let kioskId = localStorage.getItem(storageKey);
  if (!kioskId) {
    kioskId = typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `kiosk-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(storageKey, kioskId);
  }
  return kioskId;
}

function logKioskInteraction(eventType, details = {}, conversationId = null) {
  // La journalisation ne doit jamais bloquer l'envoi d'une question au chatbot.
  fetch(`${API_URL}/api/kiosk/interactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    keepalive: true,
    body: JSON.stringify({
      kiosk_id: getKioskId(),
      event_type: eventType,
      conversation_id: conversationId,
      details,
      occurred_at: new Date().toISOString(),
    }),
  }).catch((error) => {
    console.warn("Journalisation borne indisponible :", error);
  });
}

function ResponseFeedback({ conversationId, question, answer, language = "fr" }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");

    if (!rating) {
      setError(language === "en" ? "Choose a rating from 1 to 5." : "Choisissez une note de 1 à 5.");
      return;
    }

    setSending(true);

    try {
      await readResponse(
        await fetch(`${API_URL}/api/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            conversation_id: conversationId,
            question,
            answer,
            rating,
            comment,
          }),
        })
      );

      setSubmitted(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  if (submitted) {
    return <p className="feature-success">{language === "en" ? "Thank you for your feedback." : "Merci pour votre évaluation."}</p>;
  }

  return (
    <form className="feature-panel feedback-panel" onSubmit={submit}>
      <p className="feature-title">{language === "en" ? "Was this answer helpful?" : "Cette réponse vous a-t-elle aidé ?"}</p>

      <div className="rating-buttons">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            className={value <= rating ? "rating-star selected" : "rating-star"}
            onClick={() => setRating(value)}
            aria-label={`${value} sur 5`}
            aria-pressed={rating === value}
          >
            ★
          </button>
        ))}
      </div>

      <textarea
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder={language === "en" ? "Optional comment" : "Commentaire facultatif"}
        maxLength={1000}
        rows={2}
      />

      {error && <p className="feature-error">{error}</p>}

      <button type="submit" disabled={sending || rating === 0}>
        {sending ? (language === "en" ? "Sending..." : "Envoi...") : (language === "en" ? "Submit feedback" : "Envoyer l'évaluation")}
      </button>
    </form>
  );
}

function MessageActions({ conversationId, question, answer, language = "fr" }) {
  const [mode, setMode] = useState("");
  const [correctedAnswer, setCorrectedAnswer] = useState("");
  const [reason, setReason] = useState("");
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function submitCorrection(event) {
    event.preventDefault();
    setSending(true);
    setError("");
    setStatus("");

    try {
      await readResponse(
        await fetch(`${API_URL}/api/corrections`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            incorrect_answer: answer,
            corrected_answer: correctedAnswer,
          }),
        })
      );

      setStatus(language === "en" ? "Correction submitted for review." : "Correction transmise pour validation.");
      setMode("");
      setCorrectedAnswer("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  async function submitEscalation(event) {
    event.preventDefault();
    setSending(true);
    setError("");
    setStatus("");

    try {
      await readResponse(
        await fetch(`${API_URL}/api/escalations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            conversation_id: conversationId,
            question,
            reason,
          }),
        })
      );

      setStatus(language === "en" ? "Your request has been sent to the ESIC team." : "Votre demande a été enregistrée pour l'équipe ESIC.");
      setMode("");
      setReason("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="message-actions">
      <div className="message-action-buttons">
        <button type="button" onClick={() => setMode(mode === "correction" ? "" : "correction")}>
          {language === "en" ? "Report an incorrect answer" : "Signaler une réponse incorrecte"}
        </button>
        <button type="button" onClick={() => setMode(mode === "escalation" ? "" : "escalation")}>
          {language === "en" ? "Request human assistance" : "Demander une aide humaine"}
        </button>
      </div>

      {mode === "correction" && (
        <form className="feature-panel" onSubmit={submitCorrection}>
          <p className="feature-title">{language === "en" ? "Suggest a correction" : "Proposer une correction"}</p>
          <p className="feature-muted">{language === "en" ? "Question:" : "Question :"} {question}</p>
          <p className="feature-muted">{language === "en" ? "Current answer:" : "Réponse actuelle :"} {answer}</p>

          <textarea
            value={correctedAnswer}
            onChange={(event) => setCorrectedAnswer(event.target.value)}
            placeholder={language === "en" ? "Enter the corrected answer" : "Saisissez la réponse corrigée"}
            maxLength={5000}
            required
            rows={4}
          />

          <button type="submit" disabled={sending || !correctedAnswer.trim()}>
            {sending ? (language === "en" ? "Sending..." : "Envoi...") : (language === "en" ? "Submit correction" : "Envoyer la correction")}
          </button>
        </form>
      )}

      {mode === "escalation" && (
        <form className="feature-panel" onSubmit={submitEscalation}>
          <p className="feature-title">{language === "en" ? "Request assistance" : "Demander une prise en charge"}</p>
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder={language === "en" ? "Explain why you need help (optional)" : "Expliquez pourquoi vous avez besoin d'aide (facultatif)"}
            maxLength={1000}
            rows={3}
          />
          <button type="submit" disabled={sending}>
            {sending ? (language === "en" ? "Sending..." : "Envoi...") : (language === "en" ? "Send request" : "Envoyer la demande")}
          </button>
        </form>
      )}

      {status && <p className="feature-success">{status}</p>}
      {error && <p className="feature-error">{error}</p>}
    </div>
  );
}

function AdminPanel({ onClose, language = "fr" }) {
  const [token, setToken] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [category, setCategory] = useState("general");
  const [corrections, setCorrections] = useState([]);
  const [escalations, setEscalations] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [kioskStatuses, setKioskStatuses] = useState([]);
  const [kioskStatusUpdatedAt, setKioskStatusUpdatedAt] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function adminFetch(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      "X-Admin-Token": token,
      ...(options.headers || {}),
    };

    return readResponse(
      await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
      })
    );
  }

  async function refreshAdminData() {
    setError("");
    setNotice("");
    setBusy(true);

    try {
      const [correctionData, escalationData, knowledgeData, statsData, kioskData] =
        await Promise.all([
          adminFetch("/api/admin/corrections?status=pending"),
          adminFetch("/api/admin/escalations?status=pending"),
          adminFetch("/api/admin/knowledge"),
          adminFetch("/api/feedback/statistics"),
          adminFetch("/api/kiosk/status"),
        ]);

      setCorrections(correctionData.corrections || []);
      setEscalations(escalationData.escalations || []);
      setKnowledge(knowledgeData.entries || []);
      setStatistics(statsData);
      setKioskStatuses(kioskData.kiosks || []);
      setKioskStatusUpdatedAt(new Date());
      setAuthenticated(true);
    } catch (err) {
      setAuthenticated(false);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function addKnowledge(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setBusy(true);

    try {
      await adminFetch("/api/admin/knowledge", {
        method: "POST",
        body: JSON.stringify({ question, answer, category }),
      });

      setQuestion("");
      setAnswer("");
      setCategory("general");
      setNotice("Connaissance ajoutée.");
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function reviewCorrection(id, status) {
    setError("");
    setNotice("");

    try {
      await adminFetch(`/api/admin/corrections/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });

      setNotice("Correction mise à jour.");
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  async function reviewEscalation(id, status) {
    setError("");
    setNotice("");

    try {
      await adminFetch(`/api/admin/escalations/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });

      setNotice("Demande mise à jour.");
      await refreshAdminData();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="admin-overlay">
      <section className="admin-panel">
        <div className="admin-header">
          <h2>{language === "en" ? "ESIC Administration" : "Administration ESIC"}</h2>
          <button type="button" onClick={onClose}>{language === "en" ? "Close" : "Fermer"}</button>
        </div>

        {!authenticated && (
          <form
            className="feature-panel"
            onSubmit={(event) => {
              event.preventDefault();
              refreshAdminData();
            }}
          >
            <label htmlFor="admin-token">{language === "en" ? "Administrator token" : "Jeton administrateur"}</label>
            <input
              id="admin-token"
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              autoComplete="current-password"
              required
            />
            <button type="submit" disabled={busy || !token}>
              {busy ? (language === "en" ? "Signing in..." : "Connexion...") : (language === "en" ? "Open administration" : "Ouvrir l'administration")}
            </button>
          </form>
        )}

        {error && <p className="feature-error">{error}</p>}
        {notice && <p className="feature-success">{notice}</p>}

        {authenticated && (
          <>
            <div className="feature-panel kiosk-monitor-panel">
              <div className="kiosk-monitor-heading">
                <div>
                  <h3>US-031 — {language === "en" ? "Kiosk status" : "État des bornes"}</h3>
                  <p>{language === "en" ? "Status based on the latest heartbeat." : "Statut calculé à partir du dernier signal reçu."}</p>
                </div>
                <button type="button" onClick={refreshAdminData} disabled={busy}>
                  {busy ? (language === "en" ? "Refreshing…" : "Actualisation…") : (language === "en" ? "Refresh" : "Actualiser")}
                </button>
              </div>
              <p className="kiosk-monitor-updated">
                Dernière actualisation : {kioskStatusUpdatedAt
                  ? kioskStatusUpdatedAt.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
                  : "pas encore actualisé"}
              </p>
              {kioskStatuses.length === 0 ? (
                <p>Aucune borne n’a encore envoyé de signal. Ouvre l’application dans le navigateur de la borne.</p>
              ) : (
                <div className="kiosk-status-list">
                  {kioskStatuses.map((kiosk) => (
                    <div className="kiosk-status-item" key={kiosk.kiosk_id}>
                      <div className="kiosk-status-main">
                        <span className={`kiosk-status-dot ${kiosk.status === "online" ? "online" : "offline"}`} />
                        <div>
                          <strong>Borne {kiosk.kiosk_id.slice(0, 8)}</strong>
                          <span className="kiosk-status-label">{kiosk.status === "online" ? "En ligne" : "Hors ligne"}</span>
                        </div>
                      </div>
                      <div className="kiosk-status-meta">
                        <span>Dernier signal : {kiosk.last_seen ? new Date(kiosk.last_seen).toLocaleString("fr-FR") : "inconnu"}</span>
                        <span>{kiosk.interactions_count} interaction(s)</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="feature-panel">
              <h3>US-024 — {language === "en" ? "Feedback" : "Évaluations"}</h3>
              <p>{language === "en" ? "Number of ratings:" : "Nombre d'évaluations :"} {statistics?.total ?? 0}</p>
              <p>
                {language === "en" ? "Average rating:" : "Note moyenne :"}{" "}
                {statistics?.average_rating == null
                  ? (language === "en" ? "No ratings" : "Aucune note")
                  : `${statistics.average_rating} / 5`}
              </p>
              <p>
                {language === "en" ? "Breakdown:" : "Répartition :"}{" "}
                {(statistics?.distribution || [])
                  .map((item) => `${item.rating}★ : ${item.count}`)
                  .join(" · ") || (language === "en" ? "No feedback" : "Aucune évaluation")}
              </p>
            </div>

            <form className="feature-panel" onSubmit={addKnowledge}>
              <h3>US-025 — {language === "en" ? "Add knowledge" : "Ajouter une connaissance"}</h3>
              <label htmlFor="knowledge-question">{language === "en" ? "Question" : "Question"}</label>
              <input
                id="knowledge-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                minLength={3}
                maxLength={1000}
                required
              />

              <label htmlFor="knowledge-answer">{language === "en" ? "Answer" : "Réponse"}</label>
              <textarea
                id="knowledge-answer"
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                maxLength={5000}
                required
                rows={4}
              />

              <label htmlFor="knowledge-category">{language === "en" ? "Category" : "Catégorie"}</label>
              <input
                id="knowledge-category"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                maxLength={100}
              />

              <button type="submit" disabled={busy}>
                Ajouter à la base de connaissances
              </button>
              <p className="feature-muted">
                Connaissances enregistrées : {knowledge.length}
              </p>
            </form>

            <div className="feature-panel">
              <h3>US-026 — {language === "en" ? "Corrections to review" : "Corrections à valider"}</h3>
              {corrections.length === 0 && <p>{language === "en" ? "No pending corrections." : "Aucune correction en attente."}</p>}

              {corrections.map((item) => (
                <article className="admin-item" key={item.id}>
                  <p><strong>{language === "en" ? "Question:" : "Question :"}</strong> {item.question}</p>
                  <p><strong>{language === "en" ? "Current answer:" : "Réponse actuelle :"}</strong> {item.incorrect_answer}</p>
                  <p><strong>{language === "en" ? "Suggested correction:" : "Correction proposée :"}</strong> {item.corrected_answer}</p>
                  <div className="admin-actions">
                    <button type="button" onClick={() => reviewCorrection(item.id, "approved")}>
                      {language === "en" ? "Approve" : "Approuver"}
                    </button>
                    <button type="button" onClick={() => reviewCorrection(item.id, "rejected")}>
                      {language === "en" ? "Reject" : "Rejeter"}
                    </button>
                  </div>
                </article>
              ))}
            </div>

            <div className="feature-panel">
              <h3>US-027 — {language === "en" ? "Human assistance requests" : "Demandes d'aide humaine"}</h3>
              {escalations.length === 0 && <p>{language === "en" ? "No pending requests." : "Aucune demande en attente."}</p>}

              {escalations.map((item) => (
                <article className="admin-item" key={item.id}>
                  <p><strong>{language === "en" ? "Question:" : "Question :"}</strong> {item.question}</p>
                  <p><strong>{language === "en" ? "Reason:" : "Motif :"}</strong> {item.reason || (language === "en" ? "Not specified" : "Non précisé")}</p>
                  <p><strong>{language === "en" ? "Conversation:" : "Conversation :"}</strong> {item.conversation_id}</p>
                  <div className="admin-actions">
                    <button type="button" onClick={() => reviewEscalation(item.id, "handled")}>
                      {language === "en" ? "Mark as handled" : "Marquer comme traitée"}
                    </button>
                    <button type="button" onClick={() => reviewEscalation(item.id, "rejected")}>
                      {language === "en" ? "Reject" : "Rejeter"}
                    </button>
                  </div>
                </article>
              ))}
            </div>

            <button type="button" onClick={refreshAdminData} disabled={busy}>
              Actualiser les données
            </button>
          </>
        )}
      </section>
    </div>
  );
}

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [currentView, setCurrentView] = useState("chat");
  const [sidebarOpen, setSidebarOpen] = useState(() => typeof window !== "undefined" && window.innerWidth > 768);
  const [pageError, setPageError] = useState("");
  const [openConversationMenuId, setOpenConversationMenuId] = useState(null);
  const [pinnedConversationIds, setPinnedConversationIds] = useState(() => {
    try { return JSON.parse(localStorage.getItem("esicPinnedConversationIds") || "[]"); }
    catch { return []; }
  });
  const [isKioskMode, setIsKioskMode] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [speechMessage, setSpeechMessage] = useState("");
  const [language, setLanguage] = useState(() => localStorage.getItem("esicLanguage") || "fr");
  const recognitionRef = useRef(null);
  const ui = UI_TEXT[language] || UI_TEXT.fr;
  // Epic 8 — notifications, simulation SSO ENT et informations contextuelles.
  const [advancedInfo, setAdvancedInfo] = useState([]);
  const [notificationStatus, setNotificationStatus] = useState("unsupported");
  const [notificationMessage, setNotificationMessage] = useState("");
  const [ssoUser, setSsoUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("esicDemoSsoUser") || "null"); } catch { return null; }
  });
  const [ssoOpen, setSsoOpen] = useState(false);
  const [ssoName, setSsoName] = useState("");
  const [ssoEmail, setSsoEmail] = useState("");
  const [ssoMessage, setSsoMessage] = useState("");
  const [pushSubscription, setPushSubscription] = useState(null);

  useEffect(() => {
    localStorage.setItem("esicLanguage", language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem("esicPinnedConversationIds", JSON.stringify(pinnedConversationIds));
  }, [pinnedConversationIds]);

  useEffect(() => {
    const close = (event) => { if (!event.target.closest(".conversation-wrapper")) setOpenConversationMenuId(null); };
    const escape = (event) => { if (event.key === "Escape") setOpenConversationMenuId(null); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", escape); };
  }, []);

  useEffect(() => {
    // Keep the untouched welcome screen aligned with the selected language.
    setMessages((previous) => {
      if (previous.length === 1 && previous[0]?.id === "welcome") {
        return [{ ...previous[0], text: language === "en"
          ? "Hello! I’m the ESIC educational virtual assistant. How can I help you?"
          : "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. Comment puis-je vous aider ?" }];
      }
      return previous;
    });
    refreshProactiveInfo();
    refreshNotifications();
  }, [language]);

  useEffect(() => {
    loadConversations();
    refreshProactiveInfo();
    refreshNotifications();
    const timer = window.setInterval(() => {
      refreshProactiveInfo();
      refreshNotifications();
    }, 60000);
    return () => window.clearInterval(timer);
  }, []);

  async function refreshProactiveInfo() {
    try {
      const response = await fetch(`${API_URL}/api/proactive/info?language=${language}`);
      if (!response.ok) return;
      const data = await response.json();
      setAdvancedInfo(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      console.warn("Informations contextuelles indisponibles :", error);
    }
  }

  async function refreshNotifications() {
    try {
      const response = await fetch(`${API_URL}/api/notifications?language=${language}`);
      if (!response.ok) return;
      const data = await response.json();
      const items = Array.isArray(data.items) ? data.items : [];
      const seenKey = "esicSeenNotificationIds";
      const seen = new Set(JSON.parse(localStorage.getItem(seenKey) || "[]"));
      if ("Notification" in window && Notification.permission === "granted") {
        items.filter((item) => !seen.has(String(item.id))).forEach((item) => {
          try { new Notification(item.title || "ESIC", { body: item.body || "Nouvelle information ESIC", tag: String(item.id) }); } catch {}
          seen.add(String(item.id));
        });
        localStorage.setItem(seenKey, JSON.stringify([...seen].slice(-100)));
      }
      setNotificationStatus("ready");
    } catch (error) {
      console.warn("Notifications indisponibles :", error);
    }
  }

  async function enableNotifications() {
    setNotificationMessage("");
    if (!("Notification" in window)) {
      setNotificationStatus("unsupported");
      setNotificationMessage("Ce navigateur ne prend pas en charge les notifications.");
      return;
    }
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setNotificationStatus(permission);
        setNotificationMessage("Autorisation refusée. Vous pouvez l'activer dans les paramètres du navigateur.");
        return;
      }
      setNotificationStatus("granted");
      setNotificationMessage("Notifications du navigateur activées pendant que l'application fonctionne.");
      new Notification("ESIC Assistant", { body: "Les notifications sont activées." });
      await refreshNotifications();
    } catch {
      setNotificationMessage("Impossible d'activer les notifications sur cet appareil.");
    }
  }

  async function demoSsoLogin(event) {
    event.preventDefault();
    setSsoMessage("");
    try {
      const response = await fetch(`${API_URL}/api/sso/demo-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: ssoName.trim(), email: ssoEmail.trim() }),
      });
      const data = await readResponse(response);
      const user = data.user;
      localStorage.setItem("esicDemoSsoUser", JSON.stringify(user));
      setSsoUser(user);
      setSsoOpen(false);
      setSsoMessage(`Connecté en mode démonstration : ${user.name}`);
    } catch (error) {
      setSsoMessage(error.message || "Connexion de démonstration impossible.");
    }
  }

  function demoSsoLogout() {
    localStorage.removeItem("esicDemoSsoUser");
    setSsoUser(null);
    setSsoMessage("Session de démonstration fermée.");
  }

  // US-031 — signal périodique pour que l'administration sache si cette borne répond.
  useEffect(() => {
    const sendHeartbeat = () => {
      fetch(`${API_URL}/api/kiosk/heartbeat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        keepalive: true,
        body: JSON.stringify({ kiosk_id: getKioskId(), mode: isKioskMode ? "kiosk" : "web" }),
      }).catch((error) => console.warn("Signal de borne indisponible :", error));
    };

    sendHeartbeat();
    const heartbeatTimer = window.setInterval(sendHeartbeat, 20000);
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") sendHeartbeat();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      window.clearInterval(heartbeatTimer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [isKioskMode]);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return undefined;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = language === "en" ? "en-US" : "fr-FR";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
      setSpeechMessage("Je vous écoute… Parlez maintenant.");
    };

    recognition.onresult = (event) => {
      let transcript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        transcript += event.results[index][0].transcript;
      }
      if (transcript.trim()) {
        setInput(transcript.trim());
        logKioskInteraction("voice_transcription", { character_count: transcript.trim().length }, currentConversationId);
      }
    };

    recognition.onerror = (event) => {
      setIsListening(false);
      const messages = {
        "not-allowed": "L'accès au microphone est refusé. Autorisez-le dans les paramètres du navigateur.",
        "service-not-allowed": "La reconnaissance vocale n'est pas autorisée par le navigateur.",
        "no-speech": "Aucune parole détectée. Réessayez en parlant après avoir activé le micro.",
        "audio-capture": "Aucun microphone n'a été détecté.",
        network: "La reconnaissance vocale nécessite une connexion réseau dans ce navigateur.",
      };
      setSpeechMessage(messages[event.error] || "La reconnaissance vocale a rencontré une erreur. Réessayez.");
    };

    recognition.onend = () => {
      setIsListening(false);
      setSpeechMessage((current) => current === "Je vous écoute… Parlez maintenant."
        ? "Dictée terminée. Vous pouvez modifier le texte puis l'envoyer."
        : current);
    };

    recognitionRef.current = recognition;
    return () => {
      recognition.onstart = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.stop();
      recognitionRef.current = null;
    };
  }, [language]);

  function toggleVoiceInput() {
    setSpeechMessage("");
    if (!speechSupported || !recognitionRef.current) {
      setSpeechMessage("La reconnaissance vocale n'est pas prise en charge par ce navigateur. Essayez Chrome ou Edge.");
      return;
    }

    if (isListening) {
      logKioskInteraction("voice_listening_stopped", {}, currentConversationId);
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    try {
      logKioskInteraction("voice_listening_started", {}, currentConversationId);
      recognitionRef.current.start();
    } catch (error) {
      setSpeechMessage("Impossible de démarrer le microphone. Attendez un instant puis réessayez.");
    }
  }

  async function loadConversations() {
    try {
      const data = await readResponse(
        await fetch(`${API_URL}/api/conversations`)
      );

      const list = Array.isArray(data.conversations)
        ? data.conversations
        : [];

      setConversations(list);

      const savedId = localStorage.getItem("currentConversationId");
      const savedConversation = list.find((item) => item.id === savedId);

      if (savedConversation) {
        const loaded = await loadConversation(savedConversation.id);
        if (loaded) return;
      }

      localStorage.removeItem("currentConversationId");

      if (list.length > 0) {
        const loaded = await loadConversation(list[0].id);
        if (loaded) return;
      }

      await createNewConversation();
    } catch (err) {
      setPageError(err.message);
    }
  }

  async function loadConversation(conversationId) {
    if (!conversationId) return false;

    try {
      const response = await fetch(
        `${API_URL}/api/history/${conversationId}`
      );

      if (response.status === 404) {
        localStorage.removeItem("currentConversationId");
        setCurrentConversationId(null);
        return false;
      }

      const data = await readResponse(response);

      setCurrentConversationId(conversationId);
      localStorage.setItem("currentConversationId", conversationId);

      const loadedMessages = Array.isArray(data.messages)
        ? data.messages.map((message, index) => ({
            ...message,
            id: message.id ?? `history-${conversationId}-${index}`,
            time: message.time ?? "",
          }))
        : [];

      setMessages(loadedMessages.length ? loadedMessages : [WELCOME_MESSAGE]);
      setInput("");
      setPageError("");
      return true;
    } catch (err) {
      setPageError(err.message);
      return false;
    }
  }

  async function createNewConversation() {
    try {
      const conversation = await readResponse(
        await fetch(`${API_URL}/api/conversations`, {
          method: "POST",
        })
      );

      setConversations((previous) => [
        conversation,
        ...previous.filter((item) => item.id !== conversation.id),
      ]);

      setCurrentConversationId(conversation.id);
      localStorage.setItem("currentConversationId", conversation.id);
      setMessages([{
        ...WELCOME_MESSAGE,
        text: language === "en" ? "Hello! I’m the ESIC educational virtual assistant. How can I help you?" : WELCOME_MESSAGE.text,
        id: `welcome-${Date.now()}`,
        time: currentTime(),
      }]);
      setInput("");
      setPageError("");
      return conversation;
    } catch (err) {
      setPageError(err.message);
      return null;
    }
  }

  async function refreshConversations() {
    try {
      const data = await readResponse(
        await fetch(`${API_URL}/api/conversations`)
      );
      setConversations(Array.isArray(data.conversations) ? data.conversations : []);
    } catch (err) {
      setPageError(err.message);
    }
  }

  function togglePinnedConversation(id) {
    setPinnedConversationIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [id, ...prev]);
    setOpenConversationMenuId(null);
  }

  async function renameConversationItem(conversation) {
    const oldTitle = conversation.title || "Nouvelle conversation";
    const title = window.prompt(language === "en" ? "Rename conversation" : "Renommer la conversation", oldTitle);
    if (title === null || !title.trim() || title.trim() === oldTitle) { setOpenConversationMenuId(null); return; }
    try {
      const updated = await readResponse(await fetch(`${API_URL}/api/conversations/${conversation.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: title.trim() }) }));
      setConversations((prev) => prev.map((x) => x.id === conversation.id ? updated : x));
      setOpenConversationMenuId(null);
    } catch (err) { setPageError(err.message); }
  }

  async function deleteConversationItem(conversation) {
    if (!window.confirm(language === "en" ? "Delete this conversation permanently?" : "Supprimer définitivement cette conversation ?")) { setOpenConversationMenuId(null); return; }
    try {
      await readResponse(await fetch(`${API_URL}/api/conversations/${conversation.id}`, { method: "DELETE" }));
      setPinnedConversationIds((prev) => prev.filter((id) => id !== conversation.id));
      const remaining = conversations.filter((x) => x.id !== conversation.id);
      setConversations(remaining);
      setOpenConversationMenuId(null);
      if (conversation.id === currentConversationId) {
        localStorage.removeItem("currentConversationId");
        if (remaining.length) await loadConversation(remaining[0].id); else await createNewConversation();
      }
    } catch (err) { setPageError(err.message); }
  }

  const orderedConversations = [...conversations].sort((a, b) => {
    const ap = pinnedConversationIds.includes(a.id) ? 1 : 0;
    const bp = pinnedConversationIds.includes(b.id) ? 1 : 0;
    return ap !== bp ? bp - ap : String(b.updated_at || "").localeCompare(String(a.updated_at || ""));
  });

  async function sendMessage(event, suggestion = null) {
    if (event?.preventDefault) event.preventDefault();

    const question = typeof suggestion === "string"
      ? suggestion.trim()
      : input.trim();

    if (!question || loading) return;

    if (isKioskMode) {
      logKioskInteraction("question_submitted", {
        question,
        input_method: suggestion ? "touch_category_or_suggestion" : "text_or_voice",
      }, currentConversationId);
    }

    setPageError("");

    let activeId = currentConversationId;

    if (!activeId) {
      const created = await createNewConversation();
      if (!created) return;
      activeId = created.id;
    }

    setMessages((previous) => [
      ...previous,
      {
        id: `user-${Date.now()}`,
        sender: "user",
        text: question,
        time: currentTime(),
      },
    ]);

    setInput("");
    setLoading(true);

    try {
      const send = (conversationId) =>
        fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: question,
            conversation_id: conversationId,
            language, // US-032 : le backend doit respecter la langue demandée.

          }),
        });

      let response = await send(activeId);

      if (response.status === 404) {
        localStorage.removeItem("currentConversationId");
        const created = await createNewConversation();

        if (!created) throw new Error("Impossible de recréer la conversation.");

        activeId = created.id;
        setCurrentConversationId(activeId);
        response = await send(activeId);
      }

      const data = await readResponse(response);
      if (isKioskMode) {
        logKioskInteraction("assistant_response_received", {
          answer_character_count: (data.answer || "").length,
        }, activeId);
      }

      setMessages((previous) => [
        ...previous,
        {
          id: `bot-${Date.now()}`,
          sender: "bot",
          text: data.answer || ui.emptyAnswer,
          time: currentTime(),
          question,
        },
      ]);

      await refreshConversations();
    } catch (err) {
      setPageError(err.message);

      setMessages((previous) => [
        ...previous,
        {
          id: `error-${Date.now()}`,
          sender: "bot",
          text: err.message || "Une erreur est survenue.",
          time: currentTime(),
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function getQuestionForMessage(index) {
    const message = messages[index];

    if (message?.question) return message.question;

    for (let i = index - 1; i >= 0; i -= 1) {
      if (messages[i].sender === "user") {
        return messages[i].text;
      }
    }

    return "";
  }

  return (
    <div className={`app-layout ${isKioskMode ? "kiosk-mode" : ""} ${sidebarOpen ? "sidebar-is-open" : "sidebar-is-collapsed"}`}>
      {sidebarOpen && <button type="button" className="sidebar-backdrop" aria-label={language === "en" ? "Close history sidebar" : "Fermer l’historique"} onClick={() => setSidebarOpen(false)} />}
      <aside
        className={`conversation-sidebar ${isKioskMode ? "kiosk-sidebar-hidden" : ""} ${sidebarOpen ? "conversation-sidebar-open" : ""}`}
      >
        <div className="sidebar-header">
          <h2>ESIC Assistant</h2>
          <button type="button" className="sidebar-close-button" onClick={() => setSidebarOpen(false)} aria-label={language === "en" ? "Close history" : "Fermer l’historique"}>×</button>
        </div>

        <button
          type="button"
          className="new-conversation-button"
          onClick={createNewConversation}
          disabled={loading}
        >
          {language === "en" ? "+ New conversation" : "+ Nouvelle conversation"}
        </button>

        <div className="conversation-history">
          <h3>{ui.history}</h3>

          {conversations.length === 0 ? (
            <p className="empty-history">{ui.noHistory}</p>
          ) : (
            orderedConversations.map((conversation) => {
              const isPinned = pinnedConversationIds.includes(conversation.id);
              const isActive = conversation.id === currentConversationId;
              const menuOpen = openConversationMenuId === conversation.id;
              return (
                <div key={conversation.id} className={`conversation-wrapper ${isActive ? "active" : ""}`}>
                  <button type="button" className="conversation-item" disabled={loading}
                    onClick={() => { loadConversation(conversation.id); setOpenConversationMenuId(null); if (window.innerWidth <= 768) setSidebarOpen(false); }}>
                    {isPinned && <span className="conversation-pin-indicator" title="Épinglée">◆</span>}
                    <span className="conversation-title">{conversation.title || (language === "en" ? "New conversation" : "Nouvelle conversation")}</span>
                  </button>
                  <button type="button" className="conversation-menu-button" aria-expanded={menuOpen}
                    onClick={(event) => { event.stopPropagation(); setOpenConversationMenuId((current) => current === conversation.id ? null : conversation.id); }}>⋯</button>
                  {menuOpen && (
                    <div className="conversation-menu" role="menu">
                      <button type="button" onClick={() => renameConversationItem(conversation)}><span>✎</span><span>{language === "en" ? "Rename" : "Renommer"}</span></button>
                      <button type="button" onClick={() => togglePinnedConversation(conversation.id)}><span>⌖</span><span>{isPinned ? (language === "en" ? "Unpin" : "Désépingler") : (language === "en" ? "Pin" : "Épingler")}</span></button>
                      <div className="menu-separator" />
                      <button type="button" className="delete-menu-item" onClick={() => deleteConversationItem(conversation)}><span>♲</span><span>{language === "en" ? "Delete" : "Supprimer"}</span></button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        <button
          type="button"
          className="admin-open-button"
          onClick={() => setAdminOpen(true)}
        >
          {language === "en" ? "Administration" : "Administration"}
        </button>
      </aside>

      <div className="app">
        <header className="topbar">
          <button type="button" className="sidebar-toggle-button" onClick={() => setSidebarOpen((open) => !open)} aria-label={sidebarOpen ? (language === "en" ? "Hide history" : "Masquer l’historique") : (language === "en" ? "Show history" : "Afficher l’historique")} aria-expanded={sidebarOpen} title={sidebarOpen ? (language === "en" ? "Hide history" : "Masquer l’historique") : (language === "en" ? "Show history" : "Afficher l’historique")}>☰</button>
          <div className="brand">
            <img src="/esic-logo.png" alt="ESIC logo" className="esic-logo" />
            <div className="brand-divider" />
            <div className="assistant-brand">
              <h1>Campus Assistant</h1>
              <span>{ui.subtitle}</span>
            </div>
          </div>

          <nav className="main-navigation" aria-label={language === "en" ? "Main navigation" : "Navigation principale"}>
            <button type="button" className={`navigation-button ${currentView === "chat" ? "navigation-button-active" : ""}`} onClick={() => { setCurrentView("chat"); setAdminOpen(false); setSidebarOpen(false); }} aria-current={currentView === "chat" ? "page" : undefined}>{language === "en" ? "Chat" : "Chatbot"}</button>
            <button type="button" className={`navigation-button ${currentView === "dashboard" ? "navigation-button-active" : ""}`} onClick={() => { setCurrentView("dashboard"); setAdminOpen(false); setSidebarOpen(false); }} aria-current={currentView === "dashboard" ? "page" : undefined}>{language === "en" ? "Dashboard" : "Tableau de bord"}</button>
          </nav>

          <label className="language-selector" htmlFor="esic-language">
            <span>{ui.language}</span>
            <select id="esic-language" value={language} onChange={(event) => setLanguage(event.target.value)} aria-label={ui.language}>
              <option value="fr">Français</option>
              <option value="en">English</option>
            </select>
          </label>

          {currentView === "chat" && <>
          <button
            type="button"
            className="kiosk-toggle-button"
            onClick={() => {
              const nextMode = !isKioskMode;
              setIsKioskMode(nextMode);
              logKioskInteraction(nextMode ? "kiosk_mode_entered" : "kiosk_mode_exited", {}, currentConversationId);
            }}
            aria-pressed={isKioskMode}
          >
            {isKioskMode ? ui.exitKiosk : ui.kiosk}
          </button>

          <div className="status">
            <span className="status-dot" />
            <span>{ui.online}</span>
          </div>
          </>}
        </header>

        {currentView === "dashboard" ? (
          <div className="dashboard-view"><Dashboard language={language} /></div>
        ) : (
          <>
        <section className="epic8-toolbar" aria-label="Fonctionnalités avancées">
          <div className="epic8-user-status">
            {ssoUser ? <><span className="epic8-status-dot" /> Connecté ENT (démo) : <strong>{ssoUser.name}</strong></> : <span>{language === "en" ? "Visitor session" : "Session visiteur"}</span>}
          </div>
          <div className="epic8-actions">
            {ssoUser ? <button type="button" className="epic8-button" onClick={demoSsoLogout}>{language === "en" ? "Sign out of ENT" : "Déconnexion ENT"}</button> : <button type="button" className="epic8-button" onClick={() => setSsoOpen(true)}>{language === "en" ? "Sign in to ENT" : "Connexion ENT"}</button>}
            <button type="button" className="epic8-button secondary" onClick={enableNotifications}>{language === "en" ? "Enable notifications" : "Activer les notifications"}</button>
          </div>
        </section>
        {ssoMessage && <p className="epic8-inline-message" role="status">{ssoMessage}</p>}
        {notificationMessage && <p className="epic8-inline-message" role="status">{notificationMessage}</p>}
        {advancedInfo.length > 0 && <section className="epic8-context" aria-label="Informations utiles selon le contexte">
          <div><span className="epic8-context-label">{language === "en" ? "Good to know" : "À retenir"}</span><h3>{language === "en" ? "Useful campus updates" : "Informations utiles du campus"}</h3></div>
          <div className="epic8-context-items">{advancedInfo.map((item) => <article className="epic8-context-card" key={item.id}><strong>{item.title}</strong><p>{item.body}</p>{item.date && <small>{item.date}</small>}</article>)}</div>
        </section>}
        {ssoOpen && <div className="epic8-modal-backdrop" role="presentation" onClick={() => setSsoOpen(false)}><section className="epic8-modal" role="dialog" aria-modal="true" aria-labelledby="epic8-sso-title" onClick={(event) => event.stopPropagation()}>
          <button type="button" className="epic8-modal-close" onClick={() => setSsoOpen(false)} aria-label={language === "en" ? "Close" : "Fermer"}>×</button>
          <h2 id="epic8-sso-title">{language === "en" ? "Sign in to ENT" : "Connexion à l'ENT"}</h2>
          <p>{language === "en" ? "SSO sign-in prototype: use a demo profile. This does not validate real ENT credentials." : "Prototype de connexion SSO : utilisez un profil de démonstration. Cette étape ne valide pas de vrais identifiants ENT."}</p>
          <form onSubmit={demoSsoLogin} className="epic8-sso-form"><label>{language === "en" ? "Display name" : "Nom affiché"}<input value={ssoName} onChange={(event) => setSsoName(event.target.value)} required maxLength={80} placeholder={language === "en" ? "e.g. Alex Martin" : "Ex. Alex Martin"} /></label><label>{language === "en" ? "Email address" : "Adresse e-mail"}<input type="email" value={ssoEmail} onChange={(event) => setSsoEmail(event.target.value)} required maxLength={160} placeholder={language === "en" ? "first.last@example.com" : "prenom.nom@exemple.fr"} /></label><button type="submit" className="epic8-button">{language === "en" ? "Continue in demo mode" : "Continuer en mode démo"}</button></form>
        </section></div>}

        <main className="chat-container">
          {isKioskMode ? (
            <section className="kiosk-welcome">
              <p className="kiosk-eyebrow">{language === "en" ? "WELCOME TO ESIC" : "ACCUEIL ESIC"}</p>
              <h2>{language === "en" ? "Welcome to your campus" : "Bienvenue sur votre campus"}</h2>
              <p>
                {language === "en" ? "What are you looking for? Select a category to get started." : "Que recherchez-vous ? Touchez une catégorie pour commencer."}
              </p>

              <div className="kiosk-grid">
                <button
                  type="button"
                  className="kiosk-card"
                  onClick={() => {
                    logKioskInteraction("kiosk_category_selected", { category: "library" }, currentConversationId);
                    sendMessage(null, "Quels sont les horaires de la bibliothèque ?");
                  }}
                  disabled={loading}
                >
                  <span className="kiosk-card-icon">01</span>
                  <strong>{language === "en" ? "Library" : "Bibliothèque"}</strong>
                  <span>{language === "en" ? "Opening hours and services" : "Horaires et services"}</span>
                </button>

                <button
                  type="button"
                  className="kiosk-card"
                  onClick={() => {
                    logKioskInteraction("kiosk_category_selected", { category: "training" }, currentConversationId);
                    sendMessage(null, "Quelles formations sont proposées à l'ESIC ?");
                  }}
                  disabled={loading}
                >
                  <span className="kiosk-card-icon">02</span>
                  <strong>{language === "en" ? "Programs" : "Formations"}</strong>
                  <span>{language === "en" ? "Courses and programs" : "Parcours et programmes"}</span>
                </button>

                <button
                  type="button"
                  className="kiosk-card"
                  onClick={() => {
                    logKioskInteraction("kiosk_category_selected", { category: "contacts" }, currentConversationId);
                    sendMessage(null, "Comment contacter le service de scolarité ?");
                  }}
                  disabled={loading}
                >
                  <span className="kiosk-card-icon">03</span>
                  <strong>{language === "en" ? "Contacts" : "Contacts"}</strong>
                  <span>{language === "en" ? "Services and support" : "Services et assistance"}</span>
                </button>

                <button
                  type="button"
                  className="kiosk-card"
                  onClick={() => {
                    logKioskInteraction("kiosk_category_selected", { category: "campus_services" }, currentConversationId);
                    sendMessage(null, "Quels services sont disponibles sur le campus ?");
                  }}
                  disabled={loading}
                >
                  <span className="kiosk-card-icon">04</span>
                  <strong>{language === "en" ? "Campus life" : "Vie du campus"}</strong>
                  <span>{language === "en" ? "Services and useful information" : "Services et informations pratiques"}</span>
                </button>
              </div>
            </section>
          ) : (
            <section className="welcome-section">
              <div className="bot-avatar large">
                <img src="/esic-logo.png" alt="ESIC" />
              </div>
              <h2>ESIC Assistant</h2>
              <p>
                {ui.welcome}
                <br />
                {ui.welcomePrompt}
              </p>
            </section>
          )}

          {pageError && (
            <div className="feature-error page-error" role="alert">
              {pageError}
            </div>
          )}

          <section className="messages-container">
            {messages.map((message, index) => {
              const isBot = message.sender === "bot";
              const question = isBot ? getQuestionForMessage(index) : "";

              return (
                <div
                  key={message.id ?? `${message.sender}-${index}`}
                  className={`message-row ${message.sender}`}
                >
                  {isBot && (
                    <div className="bot-avatar small">
                      <img src="/esic-logo.png" alt="ESIC" />
                    </div>
                  )}

                  <div className="message-content">
                    <div className="message-label">
                      {isBot ? "ESIC Assistant" : ui.user}
                    </div>

                    <div className="message-bubble">{message.text}</div>
                    <span className="message-time">{message.time}</span>

                    {isBot && !message.isError && question && currentConversationId && (
                      <>
                        <ResponseFeedback
                          language={language}
                          key={`feedback-${message.id}`}
                          conversationId={currentConversationId}
                          question={question}
                          answer={message.text}
                        />
                        <MessageActions
                          language={language}
                          key={`actions-${message.id}`}
                          conversationId={currentConversationId}
                          question={question}
                          answer={message.text}
                        />
                      </>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="message-row bot">
                <div className="bot-avatar small">
                  <img src="/esic-logo.png" alt="ESIC" />
                </div>
                <div className="message-content">
                  <div className="message-label">ESIC Assistant</div>
                  <div className="message-bubble typing-bubble">
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                  </div>
                </div>
              </div>
            )}
          </section>

          <section className="suggestions-section">
            <h3>{ui.suggestions}</h3>
            <div className="suggestions-list">
              {(language === "en" ? SUGGESTIONS_EN : SUGGESTIONS).map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="suggestion-button"
                  onClick={() => sendMessage(null, suggestion)}
                  disabled={loading}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </section>

          <form className="input-area" onSubmit={sendMessage}>
            <div className="input-wrapper">
              <input
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder={ui.placeholder}
                disabled={loading}
                maxLength={1000}
                aria-label={ui.placeholder}
              />
              <button
                type="button"
                className={`voice-button ${isListening ? "is-listening" : ""}`}
                onClick={toggleVoiceInput}
                disabled={loading}
                aria-label={isListening ? (language === "en" ? "Stop voice dictation" : "Arrêter la dictée vocale") : (language === "en" ? "Dictate a question" : "Dicter une question")}
                aria-pressed={isListening}
                title={isListening ? (language === "en" ? "Stop dictation" : "Arrêter la dictée") : (language === "en" ? "Dictate a question" : "Dicter une question")}
              >
                <span aria-hidden="true">{isListening ? "■" : "🎙"}</span>
              </button>
              <button
                type="submit"
                className="send-button"
                disabled={!input.trim() || loading}
                aria-label={language === "en" ? "Send question" : "Envoyer la question"}
              >
                <span>➤</span>
              </button>
            </div>
            <p className="input-hint">{ui.inputHint}</p>
            {speechMessage && (
              <p className={`speech-status ${isListening ? "speech-status-active" : ""}`} role="status" aria-live="polite">
                {speechMessage}
              </p>
            )}
          </form>
        </main>

        <footer className="footer">
          <span>ESIC</span>
          <span className="footer-separator">•</span>
          <span>{ui.subtitle}</span>
        </footer>
          </>
        )}
      </div>

      {adminOpen && currentView === "chat" && <AdminPanel language={language} onClose={() => setAdminOpen(false)} />}
    </div>
  );
}

export default App;
