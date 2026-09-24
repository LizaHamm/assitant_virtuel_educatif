import { useState } from "react";
import "./styles.css";

function App() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: "bot",
      text: "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. Comment puis-je vous aider ?",
      time: getCurrentTime(),
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  function getCurrentTime() {
    return new Date().toLocaleTimeString("fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  async function sendMessage(event) {
    event.preventDefault();

    const question = input.trim();

    if (!question || loading) {
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
      const response = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
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