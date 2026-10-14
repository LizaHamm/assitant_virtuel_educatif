
import { useEffect, useState } from "react";
import "./styles.css";

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

function ResponseFeedback({ conversationId, question, answer }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");

    if (!rating) {
      setError("Choisissez une note de 1 à 5.");
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
    return <p className="feature-success">Merci pour votre évaluation.</p>;
  }

  return (
    <form className="feature-panel feedback-panel" onSubmit={submit}>
      <p className="feature-title">Cette réponse vous a-t-elle aidé ?</p>

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
        placeholder="Commentaire facultatif"
        maxLength={1000}
        rows={2}
      />

      {error && <p className="feature-error">{error}</p>}

      <button type="submit" disabled={sending || rating === 0}>
        {sending ? "Envoi..." : "Envoyer l'évaluation"}
      </button>
    </form>
  );
}

function MessageActions({ conversationId, question, answer }) {
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

      setStatus("Correction transmise pour validation.");
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

      setStatus("Votre demande a été enregistrée pour l'équipe ESIC.");
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
          Signaler une réponse incorrecte
        </button>
        <button type="button" onClick={() => setMode(mode === "escalation" ? "" : "escalation")}>
          Demander une aide humaine
        </button>
      </div>

      {mode === "correction" && (
        <form className="feature-panel" onSubmit={submitCorrection}>
          <p className="feature-title">Proposer une correction</p>
          <p className="feature-muted">Question : {question}</p>
          <p className="feature-muted">Réponse actuelle : {answer}</p>

          <textarea
            value={correctedAnswer}
            onChange={(event) => setCorrectedAnswer(event.target.value)}
            placeholder="Saisissez la réponse corrigée"
            maxLength={5000}
            required
            rows={4}
          />

          <button type="submit" disabled={sending || !correctedAnswer.trim()}>
            {sending ? "Envoi..." : "Envoyer la correction"}
          </button>
        </form>
      )}

      {mode === "escalation" && (
        <form className="feature-panel" onSubmit={submitEscalation}>
          <p className="feature-title">Demander une prise en charge</p>
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Expliquez pourquoi vous avez besoin d'aide (facultatif)"
            maxLength={1000}
            rows={3}
          />
          <button type="submit" disabled={sending}>
            {sending ? "Envoi..." : "Envoyer la demande"}
          </button>
        </form>
      )}

      {status && <p className="feature-success">{status}</p>}
      {error && <p className="feature-error">{error}</p>}
    </div>
  );
}

function AdminPanel({ onClose }) {
  const [token, setToken] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [category, setCategory] = useState("general");
  const [corrections, setCorrections] = useState([]);
  const [escalations, setEscalations] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [statistics, setStatistics] = useState(null);
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
      const [correctionData, escalationData, knowledgeData, statsData] =
        await Promise.all([
          adminFetch("/api/admin/corrections?status=pending"),
          adminFetch("/api/admin/escalations?status=pending"),
          adminFetch("/api/admin/knowledge"),
          adminFetch("/api/feedback/statistics"),
        ]);

      setCorrections(correctionData.corrections || []);
      setEscalations(escalationData.escalations || []);
      setKnowledge(knowledgeData.entries || []);
      setStatistics(statsData);
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
          <h2>Administration ESIC</h2>
          <button type="button" onClick={onClose}>Fermer</button>
        </div>

        {!authenticated && (
          <form
            className="feature-panel"
            onSubmit={(event) => {
              event.preventDefault();
              refreshAdminData();
            }}
          >
            <label htmlFor="admin-token">Jeton administrateur</label>
            <input
              id="admin-token"
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              autoComplete="current-password"
              required
            />
            <button type="submit" disabled={busy || !token}>
              {busy ? "Connexion..." : "Ouvrir l'administration"}
            </button>
          </form>
        )}

        {error && <p className="feature-error">{error}</p>}
        {notice && <p className="feature-success">{notice}</p>}

        {authenticated && (
          <>
            <div className="feature-panel">
              <h3>US-024 — Évaluations</h3>
              <p>Nombre d'évaluations : {statistics?.total ?? 0}</p>
              <p>
                Note moyenne :{" "}
                {statistics?.average_rating == null
                  ? "Aucune note"
                  : `${statistics.average_rating} / 5`}
              </p>
              <p>
                Répartition :{" "}
                {(statistics?.distribution || [])
                  .map((item) => `${item.rating}★ : ${item.count}`)
                  .join(" · ") || "Aucune évaluation"}
              </p>
            </div>

            <form className="feature-panel" onSubmit={addKnowledge}>
              <h3>US-025 — Ajouter une connaissance</h3>
              <label htmlFor="knowledge-question">Question</label>
              <input
                id="knowledge-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                minLength={3}
                maxLength={1000}
                required
              />

              <label htmlFor="knowledge-answer">Réponse</label>
              <textarea
                id="knowledge-answer"
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                maxLength={5000}
                required
                rows={4}
              />

              <label htmlFor="knowledge-category">Catégorie</label>
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
              <h3>US-026 — Corrections à valider</h3>
              {corrections.length === 0 && <p>Aucune correction en attente.</p>}

              {corrections.map((item) => (
                <article className="admin-item" key={item.id}>
                  <p><strong>Question :</strong> {item.question}</p>
                  <p><strong>Réponse actuelle :</strong> {item.incorrect_answer}</p>
                  <p><strong>Correction proposée :</strong> {item.corrected_answer}</p>
                  <div className="admin-actions">
                    <button type="button" onClick={() => reviewCorrection(item.id, "approved")}>
                      Approuver
                    </button>
                    <button type="button" onClick={() => reviewCorrection(item.id, "rejected")}>
                      Rejeter
                    </button>
                  </div>
                </article>
              ))}
            </div>

            <div className="feature-panel">
              <h3>US-027 — Demandes d'aide humaine</h3>
              {escalations.length === 0 && <p>Aucune demande en attente.</p>}

              {escalations.map((item) => (
                <article className="admin-item" key={item.id}>
                  <p><strong>Question :</strong> {item.question}</p>
                  <p><strong>Motif :</strong> {item.reason || "Non précisé"}</p>
                  <p><strong>Conversation :</strong> {item.conversation_id}</p>
                  <div className="admin-actions">
                    <button type="button" onClick={() => reviewEscalation(item.id, "handled")}>
                      Marquer comme traitée
                    </button>
                    <button type="button" onClick={() => reviewEscalation(item.id, "rejected")}>
                      Rejeter
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
  const [pageError, setPageError] = useState("");

  useEffect(() => {
    loadConversations();
  }, []);

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

  async function sendMessage(event, suggestion = null) {
    if (event?.preventDefault) event.preventDefault();

    const question = typeof suggestion === "string"
      ? suggestion.trim()
      : input.trim();

    if (!question || loading) return;

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

      setMessages((previous) => [
        ...previous,
        {
          id: `bot-${Date.now()}`,
          sender: "bot",
          text: data.answer || "Je n'ai pas reçu de réponse du serveur.",
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
    <div className="app-layout">
      <aside className="conversation-sidebar">
        <div className="sidebar-header">
          <h2>ESIC Assistant</h2>
        </div>

        <button
          type="button"
          className="new-conversation-button"
          onClick={createNewConversation}
          disabled={loading}
        >
          + Nouvelle conversation
        </button>

        <div className="conversation-history">
          <h3>Historique</h3>

          {conversations.length === 0 ? (
            <p className="empty-history">Aucune conversation</p>
          ) : (
            conversations.map((conversation) => (
              <button
                type="button"
                key={conversation.id}
                className={`conversation-item ${
                  conversation.id === currentConversationId ? "active" : ""
                }`}
                onClick={() => loadConversation(conversation.id)}
                disabled={loading}
              >
                <span className="conversation-title">
                  {conversation.title || "Nouvelle conversation"}
                </span>
              </button>
            ))
          )}
        </div>

        <button
          type="button"
          className="admin-open-button"
          onClick={() => setAdminOpen(true)}
        >
          Administration
        </button>
      </aside>

      <div className="app">
        <header className="topbar">
          <div className="brand">
            <img src="/esic-logo.png" alt="Logo ESIC" className="esic-logo" />
            <div className="brand-divider" />
            <div className="assistant-brand">
              <h1>Campus Assistant</h1>
              <span>Assistant virtuel éducatif</span>
            </div>
          </div>

          <div className="status">
            <span className="status-dot" />
            <span>En ligne</span>
          </div>
        </header>

        <main className="chat-container">
          <section className="welcome-section">
            <div className="bot-avatar large">
              <img src="/esic-logo.png" alt="ESIC" />
            </div>
            <h2>ESIC Assistant</h2>
            <p>
              Je suis l’assistant virtuel éducatif ESIC.
              <br />
              Posez-moi votre question pour commencer.
            </p>
          </section>

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
                      {isBot ? "ESIC Assistant" : "Vous"}
                    </div>

                    <div className="message-bubble">{message.text}</div>
                    <span className="message-time">{message.time}</span>

                    {isBot && !message.isError && question && currentConversationId && (
                      <>
                        <ResponseFeedback
                          key={`feedback-${message.id}`}
                          conversationId={currentConversationId}
                          question={question}
                          answer={message.text}
                        />
                        <MessageActions
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
            <h3>Questions fréquentes</h3>
            <div className="suggestions-list">
              {SUGGESTIONS.map((suggestion) => (
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
                placeholder="Écrivez votre question..."
                disabled={loading}
                maxLength={1000}
                aria-label="Votre question"
              />
              <button
                type="submit"
                className="send-button"
                disabled={!input.trim() || loading}
                aria-label="Envoyer la question"
              >
                <span>➤</span>
              </button>
            </div>
            <p className="input-hint">Appuyez sur Entrée pour envoyer</p>
          </form>
        </main>

        <footer className="footer">
          <span>ESIC</span>
          <span className="footer-separator">•</span>
          <span>Assistant virtuel éducatif</span>
        </footer>
      </div>

      {adminOpen && <AdminPanel onClose={() => setAdminOpen(false)} />}
    </div>
  );
}

export default App;
