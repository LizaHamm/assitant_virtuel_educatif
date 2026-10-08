// =====================================================
// ESIC CAMPUS ASSISTANT
// Frontend - US-001 / US-002 / US-003 / US-005 / US-011 / US-012 / US-013
// =====================================================

const input = document.getElementById("question");
const button = document.getElementById("sendButton");
const conversation = document.getElementById("conversation");
const sessionInfo = document.getElementById("sessionInfo");
const suggestionsContainer = document.getElementById("suggestions");

const historyList = document.getElementById("historyList");
const clearHistoryButton = document.getElementById("clearHistoryButton");
const newConversationButton = document.getElementById("newConversationButton");
const sidebarToggle = document.getElementById("sidebarToggle");
const appLayout = document.getElementById("appLayout");

const API_URL = "http://127.0.0.1:8000";
const SIDEBAR_STORAGE_KEY = "esic_sidebar_collapsed";

let sessionId = null;
let sessionNumber = null;
let contextVersion = 1;
let envoiEnCours = false;


// =====================================================
// SIDEBAR
// =====================================================

function appliquerEtatSidebar() {
    if (!appLayout || !sidebarToggle) return;

    const collapsed =
        localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";

    appLayout.classList.toggle("sidebar-collapsed", collapsed);

    sidebarToggle.setAttribute(
        "aria-expanded",
        String(!collapsed)
    );

    sidebarToggle.setAttribute(
        "aria-label",
        collapsed
            ? "Ouvrir les discussions"
            : "Fermer les discussions"
    );
}

function toggleSidebar() {
    if (!appLayout || !sidebarToggle) return;

    const collapsed =
        !appLayout.classList.contains("sidebar-collapsed");

    appLayout.classList.toggle(
        "sidebar-collapsed",
        collapsed
    );

    localStorage.setItem(
        SIDEBAR_STORAGE_KEY,
        String(collapsed)
    );

    sidebarToggle.setAttribute(
        "aria-expanded",
        String(!collapsed)
    );

    sidebarToggle.setAttribute(
        "aria-label",
        collapsed
            ? "Ouvrir les discussions"
            : "Fermer les discussions"
    );
}

sidebarToggle?.addEventListener(
    "click",
    (event) => {
        event.preventDefault();
        event.stopPropagation();
        toggleSidebar();
    }
);

appliquerEtatSidebar();


// =====================================================
// SESSION
// =====================================================

async function initialiserSession() {
    const savedSessionId =
        sessionStorage.getItem("session_id");

    const savedSessionNumber =
        sessionStorage.getItem("session_number");

    if (savedSessionId) {
        sessionId = savedSessionId;
        sessionNumber = savedSessionNumber;

        afficherSession();

        await chargerHistoriqueSession();
        await chargerToutesLesSessions();

        return;
    }

    await creerNouvelleSession(false);
    await chargerToutesLesSessions();
}

function afficherSession() {
    if (!sessionInfo) return;

    sessionInfo.textContent =
        `Session #${sessionNumber ?? "-"}`;
}


// =====================================================
// SUGGESTIONS
// =====================================================

async function chargerSuggestions() {
    if (!suggestionsContainer) return;

    try {
        const response =
            await fetch(`${API_URL}/suggestions`);

        if (!response.ok) {
            throw new Error(
                "Impossible de récupérer les suggestions"
            );
        }

        const data =
            await response.json();

        suggestionsContainer.innerHTML = "";

        if (!data.suggestions?.length) {
            suggestionsContainer.hidden = true;
            return;
        }

        suggestionsContainer.hidden = false;

        data.suggestions.forEach(
            (suggestion) => {
                const suggestionButton =
                    document.createElement("button");

                suggestionButton.type = "button";
                suggestionButton.className =
                    "suggestion-button";

                suggestionButton.textContent =
                    suggestion.question;

                suggestionButton.addEventListener(
                    "click",
                    (event) => {
                        event.preventDefault();
                        envoyerQuestion(
                            suggestion.question
                        );
                    }
                );

                suggestionsContainer.appendChild(
                    suggestionButton
                );
            }
        );

    } catch (error) {
        console.error(
            "Erreur chargement suggestions :",
            error
        );

        suggestionsContainer.hidden = true;
    }
}


// =====================================================
// NOUVELLE SESSION
// =====================================================

async function creerNouvelleSession(
    afficherMessage = true
) {
    try {
        const response =
            await fetch(
                `${API_URL}/session`,
                {
                    method: "POST",
                }
            );

        if (!response.ok) {
            throw new Error(
                "Erreur création session"
            );
        }

        const data =
            await response.json();

        sessionId = data.session_id;
        sessionNumber = data.session_number;

        contextVersion =
            data.context_version || 1;

        sessionStorage.setItem(
            "session_id",
            sessionId
        );

        sessionStorage.setItem(
            "session_number",
            sessionNumber
        );

        afficherSession();

        if (afficherMessage) {
            afficherBienvenue();
            input?.focus();
        }

    } catch (error) {
        console.error(
            "Erreur création session :",
            error
        );
    }
}

function afficherBienvenue() {
    if (!conversation) return;

    conversation.innerHTML = "";

    ajouterMessage(
        "Bonjour 👋 Comment puis-je vous aider ?",
        "bot",
        false
    );

    faireDefilerEnBas();
}


// =====================================================
// SCROLL UNIQUEMENT DANS LA ZONE DE CHAT
// =====================================================

function faireDefilerEnBas() {
    if (!conversation) return;

    conversation.scrollTop =
        conversation.scrollHeight;
}


// =====================================================
// ENVOYER UNE QUESTION
// =====================================================

async function envoyerQuestion(
    questionSuggestion = null
) {
    const rawQuestion =
        questionSuggestion !== null
            ? questionSuggestion
            : input?.value;

    const question =
        (rawQuestion || "").trim();

    if (
        !question ||
        !sessionId ||
        envoiEnCours
    ) {
        return;
    }

    envoiEnCours = true;

    ajouterMessage(
        question,
        "user"
    );

    if (input) {
        input.value = "";
    }

    const botMessage =
        ajouterMessage(
            "Réponse en cours...",
            "bot"
        );

    button.disabled = true;

    setSuggestionsDisabled(true);

    try {

        const response =
            await fetch(
                `${API_URL}/chat`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body: JSON.stringify({
                        question:
                            question,

                        session_id:
                            sessionId,
                    }),
                }
            );

        let data = {};

        try {
            data =
                await response.json();
        } catch {
            data = {};
        }

        if (!response.ok) {

            const detailMessage =
                typeof data.detail === "object" &&
                data.detail !== null
                    ? data.detail.message
                    : data.detail;

            const error =
                new Error(
                    detailMessage ||
                    "Erreur serveur"
                );

            error.status =
                response.status;

            error.detail =
                data.detail;

            throw error;
        }


        // =================================================
        // REPONSE NORMALE
        // =================================================

        remplacerTexteMessage(
            botMessage,
            data.answer ||
            "Aucune réponse."
        );

        contextVersion =
            data.context_version ||
            contextVersion;


        console.log(
            "Source :",
            data.source
        );

        // IMPORTANT :
        // On NE recharge plus toute la liste des sessions
        // après chaque question.
        //
        // Cela évite le rafraîchissement visuel
        // et le déplacement de la page.


    } catch (error) {

        console.error(
            "Erreur communication backend :",
            error
        );


        // =================================================
        // US-013 : RATE LIMIT
        // =================================================

        if (error.status === 429) {

            const detail =
                typeof error.detail === "object" &&
                error.detail !== null
                    ? error.detail
                    : {};

            const message =
                detail.message ||
                "Trop de questions envoyées. Veuillez patienter avant de réessayer.";

            const waitSeconds =
                Number(
                    detail.retry_after_seconds
                );

            if (
                Number.isFinite(
                    waitSeconds
                ) &&
                waitSeconds > 0
            ) {

                remplacerTexteMessage(
                    botMessage,

                    `⏳ ${message} ` +
                    `Réessayez dans environ ` +
                    `${waitSeconds} secondes.`
                );

            } else {

                remplacerTexteMessage(
                    botMessage,

                    `⏳ ${message}`
                );
            }
        }


        // =================================================
        // US-012 : SECURITE
        // =================================================

        else if (
            error.status === 400 &&
            typeof error.detail === "object" &&
            error.detail !== null
        ) {

            remplacerTexteMessage(
                botMessage,

                error.detail.message ||
                "❌ Requête bloquée pour des raisons de sécurité."
            );
        }


        // =================================================
        // ERREUR GENERALE
        // =================================================

        else {

            remplacerTexteMessage(
                botMessage,

                "❌ Impossible de contacter le serveur."
            );
        }

    } finally {

        button.disabled = false;

        setSuggestionsDisabled(false);

        envoiEnCours = false;

        // Toujours rester en bas du chat
        // sans toucher au scroll de la page.
        faireDefilerEnBas();

        input?.focus();
    }
}


// =====================================================
// DESACTIVER / ACTIVER SUGGESTIONS
// =====================================================

function setSuggestionsDisabled(
    disabled
) {
    document
        .querySelectorAll(
            ".suggestion-button"
        )
        .forEach(
            (element) => {
                element.disabled =
                    disabled;
            }
        );
}


// =====================================================
// AJOUTER MESSAGE
// =====================================================

function ajouterMessage(
    texte,
    type,
    autoScroll = true
) {
    const row =
        document.createElement("div");

    row.className =
        `message-row ${type}`;


    // =================================================
    // AVATAR BOT
    // =================================================

    if (type === "bot") {

        const avatar =
            document.createElement("div");

        avatar.className =
            "bot-avatar small";

        avatar.innerHTML =
            '<span class="bot-avatar-mark">AI</span>';

        row.appendChild(avatar);
    }


    // =================================================
    // CONTENU
    // =================================================

    const content =
        document.createElement("div");

    content.className =
        "message-content";


    // =================================================
    // LABEL
    // =================================================

    const label =
        document.createElement("div");

    label.className =
        "message-label";

    label.textContent =
        type === "bot"
            ? "Assistant ESIC"
            : "Vous";

    content.appendChild(label);


    // =================================================
    // BULLE
    // =================================================

    const bubble =
        document.createElement("div");

    bubble.className =
        "message-bubble";

    bubble.textContent =
        texte;

    content.appendChild(bubble);


    // =================================================
    // HEURE
    // =================================================

    const time =
        document.createElement("div");

    time.className =
        "message-time";

    time.textContent =
        new Date().toLocaleTimeString(
            "fr-FR",
            {
                hour: "2-digit",
                minute: "2-digit",
            }
        );

    content.appendChild(time);

    row.appendChild(content);

    conversation.appendChild(row);


    if (autoScroll) {
        faireDefilerEnBas();
    }

    return bubble;
}


// =====================================================
// MODIFIER REPONSE BOT
// =====================================================

function remplacerTexteMessage(
    element,
    texte
) {
    if (!element) return;

    element.textContent =
        texte;

    requestAnimationFrame(
        () => {
            faireDefilerEnBas();
        }
    );
}


// =====================================================
// HISTORIQUE DE LA SESSION
// =====================================================

async function chargerHistoriqueSession() {
    if (
        !sessionId ||
        !conversation
    ) {
        return;
    }

    try {

        const response =
            await fetch(
                `${API_URL}/history/${sessionId}`
            );

        if (!response.ok) {
            throw new Error(
                "Erreur historique"
            );
        }

        const data =
            await response.json();

        contextVersion =
            data.context_version || 1;

        conversation.innerHTML = "";


        if (!data.history?.length) {

            ajouterMessage(
                "Bonjour 👋 Comment puis-je vous aider ?",
                "bot",
                false
            );

            requestAnimationFrame(
                faireDefilerEnBas
            );

            return;
        }


        // Reconstruction de l'historique
        // sans scroll à chaque message.

        data.history.forEach(
            (message, index) => {

                if (
                    index > 0 &&
                    message.context_version !==
                        data.history[
                            index - 1
                        ].context_version
                ) {

                    const separator =
                        document.createElement(
                            "div"
                        );

                    separator.className =
                        "context-reset";

                    separator.textContent =
                        "Nouveau contexte";

                    conversation.appendChild(
                        separator
                    );
                }


                ajouterMessage(
                    message.question,
                    "user",
                    false
                );

                ajouterMessage(
                    message.answer,
                    "bot",
                    false
                );
            }
        );


        // Un seul scroll à la fin
        requestAnimationFrame(
            faireDefilerEnBas
        );

    } catch (error) {

        console.error(
            "Erreur chargement historique :",
            error
        );

        conversation.innerHTML = "";

        ajouterMessage(
            "Bonjour 👋 Comment puis-je vous aider ?",
            "bot",
            false
        );
    }
}


// =====================================================
// TOUTES LES SESSIONS
// =====================================================

async function chargerToutesLesSessions() {
    if (!historyList) return;

    try {

        const response =
            await fetch(
                `${API_URL}/sessions`
            );

        if (!response.ok) {
            throw new Error(
                "Erreur récupération sessions"
            );
        }

        const data =
            await response.json();

        historyList.innerHTML = "";


        if (!data.sessions?.length) {

            historyList.innerHTML =
                `<p class="empty-history">
                    Aucune conversation.
                </p>`;

            return;
        }


        for (
            const session of data.sessions
        ) {

            const historyResponse =
                await fetch(
                    `${API_URL}/history/${session.session_id}`
                );

            const historyData =
                historyResponse.ok
                    ? await historyResponse.json()
                    : { history: [] };


            const firstMessage =
                historyData.history?.[0]?.question ||
                "Nouvelle conversation";


            const item =
                document.createElement(
                    "div"
                );

            item.className =
                "conversation-item" +
                (
                    session.session_id ===
                    sessionId
                        ? " active"
                        : ""
                );

            item.title =
                firstMessage;


            // =================================================
            // CONTENU
            // =================================================

            const content =
                document.createElement(
                    "div"
                );

            content.className =
                "conversation-item-content";


            const title =
                document.createElement(
                    "span"
                );

            title.className =
                "conversation-title";

            title.textContent =
                firstMessage;


            const meta =
                document.createElement(
                    "span"
                );

            meta.className =
                "conversation-meta";

            meta.textContent =
                `Session #${session.session_number}`;


            content.appendChild(
                title
            );

            content.appendChild(
                meta
            );


            // =================================================
            // DELETE
            // =================================================

            const deleteButton =
                document.createElement(
                    "button"
                );

            deleteButton.type =
                "button";

            deleteButton.className =
                "conversation-delete";

            deleteButton.textContent =
                "🗑";

            deleteButton.title =
                "Supprimer cette discussion";

            deleteButton.setAttribute(
                "aria-label",
                `Supprimer la discussion ${session.session_number}`
            );


            deleteButton.addEventListener(
                "click",
                async (event) => {

                    event.preventDefault();
                    event.stopPropagation();

                    await supprimerConversation(
                        session.session_id,
                        session.session_number
                    );
                }
            );


            item.appendChild(
                content
            );

            item.appendChild(
                deleteButton
            );


            // =================================================
            // CHANGER DE SESSION
            // =================================================

            item.addEventListener(
                "click",
                async (event) => {

                    event.preventDefault();

                    if (
                        session.session_id ===
                        sessionId
                    ) {
                        return;
                    }

                    await changerDeConversation(
                        session.session_id,
                        session.session_number
                    );
                }
            );


            historyList.appendChild(
                item
            );
        }

    } catch (error) {

        console.error(
            "Erreur historique :",
            error
        );

        historyList.innerHTML =
            `<p class="empty-history">
                ❌ Impossible de charger l'historique.
            </p>`;
    }
}


// =====================================================
// CHANGER DE CONVERSATION
// =====================================================

async function changerDeConversation(
    id,
    number
) {
    sessionId = id;
    sessionNumber = number;

    sessionStorage.setItem(
        "session_id",
        sessionId
    );

    sessionStorage.setItem(
        "session_number",
        sessionNumber
    );

    afficherSession();

    await chargerHistoriqueSession();

    await chargerToutesLesSessions();

    input?.focus();
}


// =====================================================
// SUPPRIMER UNE CONVERSATION
// =====================================================

async function supprimerConversation(
    id,
    number
) {
    const current =
        id === sessionId;


    const confirmation =
        confirm(
            current
                ? `Supprimer la discussion Session #${number} ? Une nouvelle conversation sera créée.`
                : `Supprimer la discussion Session #${number} ?`
        );


    if (!confirmation) return;


    try {

        const response =
            await fetch(
                `${API_URL}/sessions/${id}`,
                {
                    method: "DELETE",
                }
            );


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Erreur suppression conversation"
            );
        }


        if (current) {

            sessionStorage.removeItem(
                "session_id"
            );

            sessionStorage.removeItem(
                "session_number"
            );

            sessionId = null;
            sessionNumber = null;
            contextVersion = 1;

            await creerNouvelleSession(
                true
            );
        }


        await chargerToutesLesSessions();

    } catch (error) {

        console.error(
            "Erreur suppression conversation :",
            error
        );

        alert(
            "❌ Impossible de supprimer cette discussion."
        );
    }
}


// =====================================================
// EFFACER TOUT L'HISTORIQUE
// =====================================================

async function effacerHistorique() {

    const confirmation =
        confirm(
            "Voulez-vous vraiment supprimer tout l'historique ?"
        );


    if (!confirmation) return;


    try {

        const response =
            await fetch(
                `${API_URL}/sessions`,
                {
                    method: "DELETE",
                }
            );


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Erreur suppression historique"
            );
        }


        sessionId =
            data.session_id;

        sessionNumber =
            data.session_number;

        contextVersion =
            data.context_version || 1;


        sessionStorage.setItem(
            "session_id",
            sessionId
        );

        sessionStorage.setItem(
            "session_number",
            sessionNumber
        );


        afficherSession();

        afficherBienvenue();

        await chargerToutesLesSessions();

        input?.focus();

    } catch (error) {

        console.error(
            "Erreur suppression historique :",
            error
        );

        alert(
            "❌ Impossible de supprimer l'historique."
        );
    }
}


// =====================================================
// EVENEMENTS
// =====================================================

newConversationButton?.addEventListener(
    "click",
    async (event) => {

        event.preventDefault();
        event.stopPropagation();

        await creerNouvelleSession(
            true
        );

        await chargerToutesLesSessions();
    }
);


clearHistoryButton?.addEventListener(
    "click",
    (event) => {

        event.preventDefault();
        event.stopPropagation();

        effacerHistorique();
    }
);


// =====================================================
// BOUTON ENVOYER
// =====================================================

button?.addEventListener(
    "click",
    (event) => {

        event.preventDefault();
        event.stopPropagation();

        envoyerQuestion();
    }
);


// =====================================================
// PROTECTION CONTRE SUBMIT
// =====================================================

document.addEventListener(
    "submit",
    (event) => {

        event.preventDefault();
        event.stopPropagation();

        if (
            event.target &&
            input &&
            event.target.contains(input)
        ) {
            envoyerQuestion();
        }
    },
    true
);


// =====================================================
// ENTRÉE CLAVIER
// =====================================================

input?.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Enter"
        ) {

            event.preventDefault();
            event.stopPropagation();

            envoyerQuestion();
        }
    }
);


// =====================================================
// DEMARRAGE
// =====================================================

(async function demarrer() {

    await chargerSuggestions();

    await initialiserSession();

    input?.focus();

})();