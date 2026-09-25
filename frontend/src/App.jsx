import { useEffect, useRef, useState } from "react";
import { getSessionId } from "./session";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const WELCOME_TEXT =
  "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. Comment puis-je vous aider ?";

function formatTime(date) {
  return date.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Transforme l'historique renvoyé par l'API en messages affichables,
// dans l'ordre chronologique : question de l'utilisateur puis réponse du bot.
function historyToMessages(items) {
  return items.flatMap((item, index) => {
    const time = formatTime(new Date(item.created_at));
    return [
      { id: `history-${index}-user`, sender: "user", text: item.question, time },
      { id: `history-${index}-bot`, sender: "bot", text: item.answer, time },
    ];
  });
}

function App() {
  // Identifiant de session, lu une seule fois au chargement (US-002)
  const [sessionId] = useState(getSessionId);

  const [messages, setMessages] = useState([
    {
      id: "welcome",
      sender: "bot",
      text: WELCOME_TEXT,
      time: getCurrentTime(),
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const messagesEndRef = useRef(null);

  function getCurrentTime() {
    return formatTime(new Date());
  }

  // Restauration de l'historique au chargement de la page (US-002)
  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      try {
        const response = await fetch(`${API_URL}/api/history/${sessionId}`);
        if (!response.ok) {
          throw new Error("Historique indisponible.");
        }
        const data = await response.json();
        if (!cancelled && data.messages.length > 0) {
          setMessages((previousMessages) => [
            previousMessages[0], // message d'accueil conservé en tête
            ...historyToMessages(data.messages),
          ]);
        }
      } catch (error) {
        if (!cancelled) {
          setMessages((previousMessages) => [
            ...previousMessages,
            {
              id: "history-error",
              sender: "bot",
              text: "L'historique de la conversation n'a pas pu être récupéré. Vous pouvez tout de même poser votre question.",
              time: getCurrentTime(),
            },
          ]);
        }
      } finally {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      }
    }

    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Défilement automatique vers le dernier message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading]);

  async function sendMessage(event) {
    event.preventDefault();

    const question = input.trim();

    if (!question || loading || historyLoading) {
      return;
    }

    const userMessage = {
      id: Date.now(),
      sender: "user",
      text: question,
      time: getCurrentTime(),
    };

    setMessages((previousMessages) => [
      ...previousMessages,
      userMessage,
    ]);

    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: question,
        }),
      });

      if (!response.ok) {
        throw new Error("Erreur lors de la communication avec le serveur.");
      }

      const data = await response.json();

      const botMessage = {
        id: Date.now() + 1,
        sender: "bot",
        text: data.answer,
        time: getCurrentTime(),
      };

      setMessages((previousMessages) => [
        ...previousMessages,
        botMessage,
      ]);
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        sender: "bot",
        text: "Une erreur est survenue. Vérifiez que le serveur est bien démarré.",
        time: getCurrentTime(),
      };

      setMessages((previousMessages) => [
        ...previousMessages,
        errorMessage,
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">

      {/* ================= HEADER ================= */}
      <header className="topbar">

        <div className="brand">
          <img
            src="/esic-logo.png"
            alt="Logo ESIC"
            className="esic-logo"
          />

          <div className="brand-divider"></div>

          <div className="assistant-brand">
            <h1>Campus Assistant</h1>
            <span>Assistant virtuel éducatif</span>
          </div>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          <span>En ligne</span>
        </div>

      </header>


      {/* ================= MAIN ================= */}
      <main className="chat-container">

        {/* Intro */}
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


        {/* ================= CHAT ================= */}
        <section className="messages-container">

          {messages.map((message) => (
            <div
              key={message.id}
              className={`message-row ${message.sender}`}
            >

              {message.sender === "bot" && (
                <div className="bot-avatar small">
                  <img src="/esic-logo.png" alt="ESIC" />
                </div>
              )}

              <div className="message-content">

                <div className="message-label">
                  {message.sender === "bot" ? "ESIC Assistant" : "Vous"}
                </div>

                <div className="message-bubble">
                  {message.text}
                </div>

                <span className="message-time">
                  {message.time}
                </span>

              </div>

            </div>
          ))}


          {/* Loading */}
          {loading && (
            <div className="message-row bot">

              <div className="bot-avatar small">
                <img src="/esic-logo.png" alt="ESIC" />
              </div>

              <div className="message-content">

                <div className="message-label">
                  ESIC Assistant
                </div>

                <div className="message-bubble typing-bubble">

                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>

                </div>

              </div>

            </div>
          )}

          <div ref={messagesEndRef} />

        </section>


        {/* ================= INPUT ================= */}
        <form
          className="input-area"
          onSubmit={sendMessage}
        >

          <div className="input-wrapper">

            <input
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={
                historyLoading
                  ? "Chargement de la conversation..."
                  : "Écrivez votre question..."
              }
              disabled={loading || historyLoading}
              maxLength={1000}
              aria-label="Votre question"
            />

            <button
              type="submit"
              className="send-button"
              disabled={!input.trim() || loading || historyLoading}
              aria-label="Envoyer la question"
            >
              <span>➤</span>
            </button>

          </div>

          <p className="input-hint">
            Appuyez sur Entrée pour envoyer
          </p>

        </form>

      </main>


      {/* ================= FOOTER ================= */}
      <footer className="footer">
        <span>ESIC</span>
        <span className="footer-separator">•</span>
        <span>Assistant virtuel éducatif</span>
      </footer>

    </div>
  );
}

export default App;