import { useEffect, useState } from "react";
import "./styles.css";

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);

  const [messages, setMessages] = useState([
    {
      id: "welcome",
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

  /*
   * =====================================================
   * CHARGEMENT DES CONVERSATIONS
   * =====================================================
   */

  useEffect(() => {
    loadConversations();
  }, []);

  async function loadConversations() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/conversations"
      );

      if (!response.ok) {
        throw new Error(
          "Impossible de récupérer les conversations."
        );
      }

      const data = await response.json();

      setConversations(data.conversations);

      /*
       * Si des conversations existent déjà,
       * on ouvre la plus récente.
       */
      if (data.conversations.length > 0) {
        const firstConversation = data.conversations[0];

        setCurrentConversationId(firstConversation.id);

        await loadConversation(firstConversation.id);
      } else {
        /*
         * Première utilisation :
         * création automatique d'une conversation.
         */
        await createNewConversation();
      }
    } catch (error) {
      console.error(
        "Erreur lors du chargement des conversations :",
        error
      );
    }
  }

  /*
   * =====================================================
   * CHARGER UNE CONVERSATION
   * =====================================================
   */

  async function loadConversation(conversationId) {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/history/${conversationId}`
      );

      if (!response.ok) {
        throw new Error(
          "Impossible de récupérer la conversation."
        );
      }

      const data = await response.json();

      setCurrentConversationId(conversationId);

      if (data.messages.length > 0) {
        setMessages(data.messages);
      } else {
        setMessages([
          {
            id: "welcome",
            sender: "bot",
            text: "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. Comment puis-je vous aider ?",
            time: getCurrentTime(),
          },
        ]);
      }

      setInput("");
    } catch (error) {
      console.error(
        "Erreur lors du chargement de la conversation :",
        error
      );
    }
  }

  /*
   * =====================================================
   * NOUVELLE CONVERSATION
   * =====================================================
   */

  async function createNewConversation() {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/conversations",
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error(
          "Impossible de créer une conversation."
        );
      }

      const conversation = await response.json();

      setConversations((previousConversations) => [
        conversation,
        ...previousConversations,
      ]);

      setCurrentConversationId(conversation.id);

      setMessages([
        {
          id: "welcome",
          sender: "bot",
          text: "Bonjour ! Je suis l'assistant virtuel éducatif ESIC. Comment puis-je vous aider ?",
          time: getCurrentTime(),
        },
      ]);

      setInput("");
    } catch (error) {
      console.error(
        "Erreur lors de la création de la conversation :",
        error
      );
    }
  }

  /*
   * =====================================================
   * ENVOYER UN MESSAGE
   * =====================================================
   */

  async function sendMessage(event) {
    event.preventDefault();

    const question = input.trim();

    if (!question || loading) {
      return;
    }

    if (!currentConversationId) {
      console.error("Aucune conversation active.");
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
      const response = await fetch(
        "http://127.0.0.1:8000/api/chat",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: question,
            conversation_id: currentConversationId,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          "Erreur lors de la communication avec le serveur."
        );
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

      /*
       * On recharge la liste afin que le titre
       * de la conversation soit mis à jour.
       */
      const conversationsResponse = await fetch(
        "http://127.0.0.1:8000/api/conversations"
      );

      if (conversationsResponse.ok) {
        const conversationsData =
          await conversationsResponse.json();

        setConversations(
          conversationsData.conversations
        );
      }
    } catch (error) {
      console.error(error);

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

  /*
   * =====================================================
   * INTERFACE
   * =====================================================
   */

  return (
    <div className="app-layout">

      {/* =================================================
          SIDEBAR - HISTORIQUE DES CONVERSATIONS
          ================================================= */}

      <aside className="conversation-sidebar">

        <div className="sidebar-header">
          <h2>ESIC Assistant</h2>
        </div>

        <button
          type="button"
          className="new-conversation-button"
          onClick={createNewConversation}
        >
          + Nouvelle conversation
        </button>

        <div className="conversation-history">

          <h3>Historique</h3>

          {conversations.length === 0 ? (
            <p className="empty-history">
              Aucune conversation
            </p>
          ) : (
            conversations.map((conversation) => (
              <button
                type="button"
                key={conversation.id}
                className={`conversation-item ${
                  conversation.id === currentConversationId
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  loadConversation(conversation.id)
                }
              >
                <span className="conversation-title">
                  {conversation.title}
                </span>
              </button>
            ))
          )}

        </div>

      </aside>


      {/* =================================================
          APPLICATION PRINCIPALE
          ================================================= */}

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

              <span>
                Assistant virtuel éducatif
              </span>

            </div>

          </div>

          <div className="status">

            <span className="status-dot"></span>

            <span>
              En ligne
            </span>

          </div>

        </header>


        {/* ================= MAIN ================= */}

        <main className="chat-container">

          {/* Intro */}

          <section className="welcome-section">

            <div className="bot-avatar large">

              <img
                src="/esic-logo.png"
                alt="ESIC"
              />

            </div>

            <h2>
              ESIC Assistant
            </h2>

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

                    <img
                      src="/esic-logo.png"
                      alt="ESIC"
                    />

                  </div>

                )}

                <div className="message-content">

                  <div className="message-label">

                    {message.sender === "bot"
                      ? "ESIC Assistant"
                      : "Vous"}

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


            {/* ================= LOADING ================= */}

            {loading && (

              <div className="message-row bot">

                <div className="bot-avatar small">

                  <img
                    src="/esic-logo.png"
                    alt="ESIC"
                  />

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
                onChange={(event) =>
                  setInput(event.target.value)
                }
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

          <span className="footer-separator">
            •
          </span>

          <span>
            Assistant virtuel éducatif
          </span>

        </footer>

      </div>

    </div>
  );
}

export default App;