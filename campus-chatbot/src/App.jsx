import { useEffect, useRef, useState } from "react";
import Dashboard from "./Dashboard";
import "./styles.css";

const API_URL = "http://127.0.0.1:8000";

const SUGGESTIONS = [
  "À quelle heure ouvre la bibliothèque ?",
  "Quand sont mes examens ?",
  "Comment demander un certificat de scolarité ?",
  "Comment faire une demande de stage ou d'alternance ?",
];

/* Petites icônes en SVG (pas d'emoji) */

function PinIcon() {
  return (
    <svg className="pin-icon" width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <circle cx="12" cy="8" r="5" />
      <rect x="11" y="12" width="2" height="9" />
    </svg>
  );
}

function DotsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <circle cx="5" cy="12" r="2" />
      <circle cx="12" cy="12" r="2" />
      <circle cx="19" cy="12" r="2" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" aria-hidden="true">
      <line x1="4" y1="7" x2="20" y2="7" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="17" x2="20" y2="17" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="4" y1="20" x2="20" y2="20" />
      <rect x="6" y="12" width="3" height="6" />
      <rect x="11" y="8" width="3" height="10" />
      <rect x="16" y="4" width="3" height="14" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  );
}

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);

  // Menu déroulant ouvert (id de la conversation concernée)
  const [openMenuId, setOpenMenuId] = useState(null);

  // Sidebar en tiroir sur mobile (US-004)
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Vue affichée dans la zone principale : "chat" ou "dashboard" (Epic 5)
  const [view, setView] = useState("chat");

  // Renommage d'une conversation (id de celle en cours d'édition)
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const skipRenameSave = useRef(false);

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

  /*
   * Ferme le menu déroulant si on clique ailleurs
   * ou si on appuie sur Échap.
   */
  useEffect(() => {
    if (openMenuId === null) {
      return;
    }

    function handleClickOutside(event) {
      if (!event.target.closest(".conversation-actions")) {
        setOpenMenuId(null);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setOpenMenuId(null);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [openMenuId]);

  /*
   * Recharge la liste depuis le serveur et la renvoie
   * (utile après épinglage, renommage, suppression).
   */
  async function refreshConversations() {
    try {
      const response = await fetch(`${API_URL}/api/conversations`);

      if (!response.ok) {
        throw new Error("Impossible de récupérer les conversations.");
      }

      const data = await response.json();
      setConversations(data.conversations);
      return data.conversations;
    } catch (error) {
      console.error("Erreur lors du rechargement de la liste :", error);
      return null;
    }
  }

  async function loadConversations() {
    try {
      const response = await fetch(`${API_URL}/api/conversations`);

      if (!response.ok) {
        throw new Error("Impossible de récupérer les conversations.");
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
        await createNewConversation(true);
      }
    } catch (error) {
      console.error("Erreur lors du chargement des conversations :", error);
    }
  }

  /*
   * =====================================================
   * CHARGER UNE CONVERSATION
   * =====================================================
   */

  async function loadConversation(conversationId) {
    setSidebarOpen(false); // on referme le tiroir immédiatement, avant même la requête

    try {
      const response = await fetch(`${API_URL}/api/history/${conversationId}`);

      if (!response.ok) {
        throw new Error("Impossible de récupérer la conversation.");
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
      console.error("Erreur lors du chargement de la conversation :", error);
    }
  }

  /*
   * =====================================================
   * NOUVELLE CONVERSATION (US-003)
   * =====================================================
   */

  async function createNewConversation(force = false) {
    /*
     * Si la conversation actuelle est déjà vide,
     * inutile d'en créer une autre.
     * (force = true : on crée quand même, utilisé quand
     * il n'existe plus aucune conversation.)
     */
    const currentConversation = conversations.find(
      (conversation) => conversation.id === currentConversationId
    );

    if (
      force !== true &&
      currentConversation &&
      currentConversation.title === "Nouvelle conversation"
    ) {
      setInput("");
      setSidebarOpen(false);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/api/conversations`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Impossible de créer une conversation.");
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
      setSidebarOpen(false);
    } catch (error) {
      console.error("Erreur lors de la création de la conversation :", error);
    }
  }

  /*
   * =====================================================
   * ÉPINGLER / RENOMMER / SUPPRIMER
   * =====================================================
   */

  async function togglePin(conversation) {
    setOpenMenuId(null);

    try {
      const response = await fetch(
        `${API_URL}/api/conversations/${conversation.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pinned: !conversation.pinned }),
        }
      );

      if (!response.ok) {
        throw new Error("Impossible d'épingler la conversation.");
      }

      await refreshConversations();
    } catch (error) {
      console.error(error);
    }
  }

  function startRename(conversation) {
    setOpenMenuId(null);
    setEditingId(conversation.id);
    setEditingTitle(conversation.title);
  }

  function cancelRename() {
    setEditingId(null);
    setEditingTitle("");
  }

  async function saveRename(conversationId) {
    const title = editingTitle.trim();
    const original = conversations.find(
      (conversation) => conversation.id === conversationId
    );

    // Titre vide ou inchangé : on annule simplement
    if (!title || (original && title === original.title)) {
      cancelRename();
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/conversations/${conversationId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title }),
        }
      );

      if (!response.ok) {
        throw new Error("Impossible de renommer la conversation.");
      }

      await refreshConversations();
    } catch (error) {
      console.error(error);
    }

    cancelRename();
  }

  async function deleteConversation(conversation) {
    setOpenMenuId(null);

    const confirmed = window.confirm(
      `Supprimer la conversation « ${conversation.title} » ?`
    );

    if (!confirmed) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/conversations/${conversation.id}`,
        { method: "DELETE" }
      );

      if (!response.ok) {
        throw new Error("Impossible de supprimer la conversation.");
      }

      const remaining = await refreshConversations();

      /*
       * Si on vient de supprimer la conversation affichée,
       * on ouvre la suivante, ou on en crée une nouvelle
       * s'il n'en reste aucune.
       */
      if (conversation.id === currentConversationId && remaining) {
        if (remaining.length > 0) {
          await loadConversation(remaining[0].id);
        } else {
          await createNewConversation(true);
        }
      }
    } catch (error) {
      console.error(error);
    }
  }

  /*
   * =====================================================
   * ENVOYER UN MESSAGE
   * =====================================================
   */

  async function sendMessage(event, suggestedQuestion) {
    if (event) {
      event.preventDefault();
    }

    const question = (suggestedQuestion ?? input).trim();

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

    setMessages((previousMessages) => [...previousMessages, userMessage]);

    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: question,
          conversation_id: currentConversationId,
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

      setMessages((previousMessages) => [...previousMessages, botMessage]);

      /*
       * On recharge la liste afin que le titre
       * de la conversation soit mis à jour.
       */
      await refreshConversations();
    } catch (error) {
      console.error(error);

      const errorMessage = {
        id: Date.now() + 1,
        sender: "bot",
        text: "Une erreur est survenue. Vérifiez que le serveur est bien démarré.",
        time: getCurrentTime(),
      };

      setMessages((previousMessages) => [...previousMessages, errorMessage]);
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

      {/* Fond assombri derrière la sidebar quand elle est ouverte sur mobile */}
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* =================================================
          SIDEBAR - HISTORIQUE DES CONVERSATIONS
          ================================================= */}

      <aside className={`conversation-sidebar ${sidebarOpen ? "open" : ""}`}>

        <div className="sidebar-header">
          <h2>ESIC Assistant</h2>
        </div>

        {/* ================= NAVIGATION (Epic 5) ================= */}

        <nav className="sidebar-nav">

          <button
            type="button"
            className={`sidebar-nav-item ${view === "chat" ? "active" : ""}`}
            onClick={() => setView("chat")}
          >
            <ChatIcon />
            <span>Conversations</span>
          </button>

          <button
            type="button"
            className={`sidebar-nav-item ${view === "dashboard" ? "active" : ""}`}
            onClick={() => setView("dashboard")}
          >
            <ChartIcon />
            <span>Statistiques</span>
          </button>

        </nav>

        <button
          type="button"
          className="new-conversation-button"
          onClick={() => {
            setView("chat");
            createNewConversation();
          }}
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
              <div
                key={conversation.id}
                className={`conversation-row ${
                  openMenuId === conversation.id ? "menu-open" : ""
                }`}
              >

                {editingId === conversation.id ? (

                  /* ---------- Mode renommage ---------- */
                  <input
                    className="conversation-rename-input"
                    value={editingTitle}
                    maxLength={60}
                    autoFocus
                    onFocus={(event) => event.target.select()}
                    onChange={(event) =>
                      setEditingTitle(event.target.value)
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.currentTarget.blur();
                      }

                      if (event.key === "Escape") {
                        skipRenameSave.current = true;
                        event.currentTarget.blur();
                      }
                    }}
                    onBlur={() => {
                      if (skipRenameSave.current) {
                        skipRenameSave.current = false;
                        cancelRename();
                        return;
                      }

                      saveRename(conversation.id);
                    }}
                    aria-label="Nouveau nom de la conversation"
                  />

                ) : (

                  <>
                    {/* ---------- Conversation ---------- */}
                    <button
                      type="button"
                      className={`conversation-item ${
                        conversation.id === currentConversationId
                          ? "active"
                          : ""
                      }`}
                      onClick={() => {
                        setView("chat");
                        loadConversation(conversation.id);
                      }}
                    >
                      {conversation.pinned && (
                        <span className="pin-badge">
                          <PinIcon />
                        </span>
                      )}

                      <span className="conversation-title">
                        {conversation.title}
                      </span>
                    </button>

                    {/* ---------- Bouton ⋯ + menu déroulant ---------- */}
                    <div className="conversation-actions">

                      <button
                        type="button"
                        className="menu-trigger"
                        aria-label="Options de la conversation"
                        aria-haspopup="menu"
                        aria-expanded={openMenuId === conversation.id}
                        onClick={() =>
                          setOpenMenuId(
                            openMenuId === conversation.id
                              ? null
                              : conversation.id
                          )
                        }
                      >
                        <DotsIcon />
                      </button>

                      {openMenuId === conversation.id && (
                        <div className="conversation-menu" role="menu">

                          <button
                            type="button"
                            role="menuitem"
                            className="menu-item"
                            onClick={() => togglePin(conversation)}
                          >
                            <PinIcon />
                            <span>
                              {conversation.pinned
                                ? "Désépingler"
                                : "Épingler"}
                            </span>
                          </button>

                          <button
                            type="button"
                            role="menuitem"
                            className="menu-item"
                            onClick={() => startRename(conversation)}
                          >
                            <EditIcon />
                            <span>Renommer</span>
                          </button>

                          <button
                            type="button"
                            role="menuitem"
                            className="menu-item danger"
                            onClick={() => deleteConversation(conversation)}
                          >
                            <TrashIcon />
                            <span>Supprimer</span>
                          </button>

                        </div>
                      )}

                    </div>
                  </>

                )}

              </div>
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

            {/* Bouton ☰ : visible uniquement sur mobile (voir CSS) */}
            <button
              type="button"
              className="sidebar-toggle"
              onClick={() => setSidebarOpen((open) => !open)}
              aria-label="Afficher l'historique des conversations"
              aria-expanded={sidebarOpen}
            >
              <MenuIcon />
            </button>

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

        {view === "dashboard" ? (

          <main className="dashboard-container">
            <Dashboard apiUrl={API_URL} />
          </main>

        ) : (

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
              Je suis l'assistant virtuel éducatif ESIC.
              <br />
              Posez-moi votre question pour commencer.
            </p>

            {/* ================= SUGGESTIONS (US-005) ================= */}
            {messages.length === 1 && !loading && (
              <div className="suggestions">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    type="button"
                    key={suggestion}
                    className="suggestion-button"
                    onClick={() => sendMessage(null, suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

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

        )}


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