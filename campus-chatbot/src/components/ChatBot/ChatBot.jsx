import { useEffect, useRef, useState } from "react";
import { sendQuestion, fetchHistory } from "./chatApi";
import "./ChatBot.css";

function getCurrentTime() {
  return new Date().toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

const WELCOME = {
  id: 1,
  sender: "bot",
  text: "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. Comment puis-je vous aider ?",
  time: getCurrentTime(),
};

export default function ChatBot() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  // --- Historique (US-002) ---
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(false);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(event) {
    event.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const userMessage = { id: Date.now(), sender: "user", text: question, time: getCurrentTime() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const answer = await sendQuestion(question);
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, sender: "bot", text: answer, time: getCurrentTime() },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: "bot",
          text: "Une erreur est survenue. Vérifiez que le serveur est bien démarré.",
          time: getCurrentTime(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function toggleHistory() {
    const willShow = !showHistory;
    setShowHistory(willShow);
    if (!willShow) return; // on referme, pas besoin de recharger

    setHistoryLoading(true);
    setHistoryError(false);
    try {
      const data = await fetchHistory();
      setHistory(data);
    } catch {
      setHistoryError(true);
    } finally {
      setHistoryLoading(false);
    }
  }

  return (
    <div className="app">
      {/* ================= HEADER ================= */}
      <header className="topbar">
        <div className="brand">
          <img src="/esic-logo.png" alt="Logo ESIC" className="esic-logo" />
          <div className="brand-divider" />
          <div className="assistant-brand">
            <h1>Campus Assistant</h1>
            <span>Assistant virtuel éducatif</span>
          </div>
        </div>

        <button type="button" className="history-button" onClick={toggleHistory}>
          {showHistory ? "Fermer" : "Historique"}
        </button>
      </header>

      {/* ================= PANNEAU HISTORIQUE (US-002), sur le côté ================= */}
      {showHistory && (
        <>
          <div className="history-backdrop" onClick={() => setShowHistory(false)} />
          <aside className="history-panel">
            <div className="history-panel-header">
              <h2>Historique</h2>
              <button
                type="button"
                className="history-close"
                onClick={() => setShowHistory(false)}
                aria-label="Fermer l'historique"
              >
                ✕
              </button>
            </div>

            <div className="history-panel-body">
              {historyLoading && <p className="history-status">Chargement de l'historique…</p>}
              {historyError && <p className="history-status error">Impossible de charger l'historique.</p>}
              {!historyLoading && !historyError && history.length === 0 && (
                <p className="history-status">Aucune question posée pour l'instant dans cette session.</p>
              )}
              {!historyLoading && !historyError && history.length > 0 && (
                <ul className="history-list">
                  {history.map((entry, i) => (
                    <li key={i} className="history-item">
                      <div className="history-question">
                        <span className="history-tag">Vous</span> {entry.question}
                        <span className="history-time">{entry.time}</span>
                      </div>
                      <div className="history-answer">
                        <span className="history-tag">ESIC Assistant</span> {entry.answer}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        </>
      )}

      {/* ================= MAIN ================= */}
      <main className="chat-container">
        <section className="welcome-section">
          <div className="bot-avatar large">
            <img src="/esic-logo.png" alt="ESIC" />
          </div>
          <h2>ESIC Assistant</h2>
          <p>
            Je suis l'assistant virtuel éducatif ESIC.
            <br />
            Posez-moi votre question pour commencer.
          </p>
        </section>

        <section className="messages-container">
          {messages.map((message) => (
            <div key={message.id} className={`message-row ${message.sender}`}>
              {message.sender === "bot" && (
                <div className="bot-avatar small">
                  <img src="/esic-logo.png" alt="ESIC" />
                </div>
              )}

              <div className="message-content">
                <div className="message-label">{message.sender === "bot" ? "ESIC Assistant" : "Vous"}</div>
                <div className="message-bubble">{message.text}</div>
                <span className="message-time">{message.time}</span>
              </div>
            </div>
          ))}

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
          <div ref={endRef} />
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
  );
}