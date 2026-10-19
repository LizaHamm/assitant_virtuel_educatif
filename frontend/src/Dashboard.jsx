import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import "./Dashboard.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const REFRESH_MS = 15000;

const COLORS = ["#5145cd", "#159a92", "#f0a43c", "#dc6482", "#6485e5", "#8b6cc1"];

const TEXT = {
  fr: {
    loading: "Chargement du tableau de bord…",
    title: "Tableau de bord analytics",
    subtitle: "Suivi en direct de l’utilisation, du NLP, de la satisfaction et des tendances.",
    live: "Actualisation automatique",
    updated: "Mis à jour",
    totalQuestions: "Questions totales",
    totalQuestionsDesc: "Questions enregistrées dans les logs",
    questions24h: "Questions / 24 h",
    questions24hDesc: "Volume des dernières 24 heures",
    sessions: "Conversations",
    sessionsDesc: "Sessions distinctes enregistrées",
    resolution: "Taux de résolution",
    resolutionDesc: "Sans escalade ni clarification requise",
    avgRating: "Satisfaction moyenne",
    avgRatingDesc: "Moyenne des évaluations utilisateurs",
    satisfactionRate: "Taux de satisfaction",
    satisfactionRateDesc: "Part des notes de 4 ou 5 étoiles",
    responseTime: "Temps de réponse moyen",
    responseTimeDesc: "Mesuré sur les nouvelles interactions",
    categoryConfidence: "Confiance catégorie NLP",
    categoryConfidenceDesc: "Confiance moyenne du classifieur catégorie",
    intentConfidence: "Confiance intention NLP",
    intentConfidenceDesc: "Confiance moyenne du classifieur intention",
    unresolved: "Questions non résolues",
    unresolvedDesc: "Escalades ou demandes de clarification",
    peakHour: "Pic d’activité",
    peakHourDesc: "Heure la plus active dans les logs",
    hourly: "Volume en temps réel — 24 h",
    hourlyDesc: "Nombre de questions enregistrées heure par heure",
    evolution: "Évolution du volume — 14 jours",
    evolutionDesc: "Activité quotidienne de l’assistant",
    categories: "Répartition par catégorie NLP",
    categoriesDesc: "Catégories produites par le modèle NLP",
    intents: "Répartition par intention",
    intentsDesc: "Information, aide, réclamation… selon le modèle",
    frequent: "Top 10 des questions",
    frequentDesc: "Formulations les plus souvent rencontrées",
    trends: "Évolution des catégories",
    trendsDesc: "7 derniers jours comparés aux 7 précédents",
    emerging: "Sujets émergents",
    emergingDesc: "Mots-clés en progression sur les 7 derniers jours",
    peakHours: "Activité par heure",
    peakHoursDesc: "Répartition des questions selon l’heure de la journée",
    ratings: "Répartition des évaluations",
    ratingsDesc: "Notes données aux réponses du chatbot",
    unresolvedList: "Questions à améliorer",
    unresolvedListDesc: "Questions ambiguës ou ayant demandé une escalade",
    noData: "Pas encore assez de données.",
    noQuestions: "Aucune question enregistrée.",
    noRatings: "Aucune évaluation pour le moment.",
    noLatency: "Pas encore mesuré",
    occurrences: "Occurrences",
    questions: "Questions",
    current: "7 derniers jours",
    previous: "7 jours précédents",
    against: "contre",
    reason: "Raison",
    category: "Catégorie",
    apiError: "Impossible de charger les statistiques.",
    apiHint: "Vérifiez que FastAPI est démarré et que les routes /api/dashboard répondent.",
  },
  en: {
    loading: "Loading dashboard…",
    title: "Analytics dashboard",
    subtitle: "Live monitoring of usage, NLP, satisfaction and trends.",
    live: "Auto refresh",
    updated: "Updated",
    totalQuestions: "Total questions",
    totalQuestionsDesc: "Questions recorded in logs",
    questions24h: "Questions / 24h",
    questions24hDesc: "Volume over the last 24 hours",
    sessions: "Conversations",
    sessionsDesc: "Distinct recorded sessions",
    resolution: "Resolution rate",
    resolutionDesc: "Without escalation or clarification",
    avgRating: "Average satisfaction",
    avgRatingDesc: "Average user rating",
    satisfactionRate: "Satisfaction rate",
    satisfactionRateDesc: "Share of 4 or 5 star ratings",
    responseTime: "Average response time",
    responseTimeDesc: "Measured on new interactions",
    categoryConfidence: "NLP category confidence",
    categoryConfidenceDesc: "Average category classifier confidence",
    intentConfidence: "NLP intent confidence",
    intentConfidenceDesc: "Average intent classifier confidence",
    unresolved: "Unresolved questions",
    unresolvedDesc: "Escalations or clarification requests",
    peakHour: "Peak activity",
    peakHourDesc: "Most active hour in logs",
    hourly: "Real-time volume — 24h",
    hourlyDesc: "Questions recorded hour by hour",
    evolution: "Volume trend — 14 days",
    evolutionDesc: "Daily assistant activity",
    categories: "NLP category breakdown",
    categoriesDesc: "Categories produced by the NLP model",
    intents: "Intent breakdown",
    intentsDesc: "Information, help, complaint… according to the model",
    frequent: "Top 10 questions",
    frequentDesc: "Most frequently encountered formulations",
    trends: "Category trends",
    trendsDesc: "Last 7 days compared with the previous 7 days",
    emerging: "Emerging topics",
    emergingDesc: "Keywords increasing over the last 7 days",
    peakHours: "Activity by hour",
    peakHoursDesc: "Question distribution by time of day",
    ratings: "Rating breakdown",
    ratingsDesc: "Ratings given to chatbot responses",
    unresolvedList: "Questions to improve",
    unresolvedListDesc: "Ambiguous questions or questions escalated to a human",
    noData: "Not enough data yet.",
    noQuestions: "No questions recorded.",
    noRatings: "No ratings yet.",
    noLatency: "Not measured yet",
    occurrences: "Occurrences",
    questions: "Questions",
    current: "Last 7 days",
    previous: "Previous 7 days",
    against: "vs.",
    reason: "Reason",
    category: "Category",
    apiError: "Unable to load statistics.",
    apiHint: "Make sure FastAPI is running and /api/dashboard routes are responding.",
  },
};

const CATEGORY_EN = {
  "orientation et formation": "Orientation and programs",
  "services campus": "Campus services",
  "emplois du temps et planning": "Schedules and planning",
  "règlement et vie étudiante": "Rules and student life",
  "reglement et vie etudiante": "Rules and student life",
  "procédures administratives": "Administrative procedures",
  "procedures administratives": "Administrative procedures",
  "contacts et information générale": "Contacts and general information",
  "contacts et information generale": "Contacts and general information",
  "non classée": "Unclassified",
  "non classee": "Unclassified",
};

const INTENT_EN = {
  info: "Information",
  aide: "Help",
  reclamation: "Complaint",
  "réclamation": "Complaint",
  "non classée": "Unclassified",
  "non classee": "Unclassified",
};

function translateLabel(value, language, dictionary) {
  if (!value) return language === "en" ? "Other" : "Autre";
  if (language !== "en") return value;
  return dictionary[String(value).trim().toLowerCase()] || value;
}

async function fetchDashboard(path, language) {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    throw new Error(language === "en" ? `API error (${response.status})` : `Erreur API (${response.status})`);
  }
  return response.json();
}

function StatCard({ label, value, description }) {
  return (
    <article className="dashboard-stat">
      <span className="dashboard-stat-label">{label}</span>
      <strong className="dashboard-stat-value">{value}</strong>
      <span className="dashboard-stat-description">{description}</span>
    </article>
  );
}

function PanelTitle({ title, description }) {
  return (
    <div className="dashboard-panel-heading">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}

function DonutPanel({ title, description, data, dataKey, nameKey, language, dictionary, emptyText }) {
  return (
    <article className="dashboard-panel">
      <PanelTitle title={title} description={description} />
      {data.length ? (
        <>
          <div className="dashboard-chart dashboard-pie-chart">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey={dataKey} nameKey={nameKey} innerRadius={48} outerRadius={78} paddingAngle={3}>
                  {data.map((item, index) => (
                    <Cell key={`${item[nameKey]}-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [value, translateLabel(name, language, dictionary)]} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="dashboard-legend">
            {data.map((item, index) => (
              <div className="dashboard-legend-item" key={`${item[nameKey]}-${index}`}>
                <span className="dashboard-legend-color" style={{ background: COLORS[index % COLORS.length] }} />
                <span className="dashboard-legend-name">{translateLabel(item[nameKey], language, dictionary)}</span>
                <strong>{item[dataKey]}</strong>
              </div>
            ))}
          </div>
        </>
      ) : <p className="dashboard-empty">{emptyText}</p>}
    </article>
  );
}

export default function Dashboard() {
  const [language, setLanguage] = useState(() => localStorage.getItem("esicLanguage") || "fr");
  const [data, setData] = useState({
    overview: {}, questions: [], categories: [], intents: [], evolution: [], hourly: [],
    peakHours: [], trends: [], emerging: [], unresolved: [], feedback: { distribution: [] },
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const t = TEXT[language] || TEXT.fr;

  useEffect(() => {
    const syncLanguage = () => setLanguage(localStorage.getItem("esicLanguage") || "fr");
    window.addEventListener("storage", syncLanguage);
    const timer = window.setInterval(syncLanguage, 300);
    return () => {
      window.removeEventListener("storage", syncLanguage);
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadData(firstLoad = false) {
      if (firstLoad) setLoading(true);
      setError("");
      try {
        const [overview, questions, categories, intents, evolution, hourly, peakHours, trends, emerging, unresolved, feedback] = await Promise.all([
          fetchDashboard("/api/dashboard/overview", language),
          fetchDashboard("/api/dashboard/top-questions?limite=10", language),
          fetchDashboard("/api/dashboard/categories", language),
          fetchDashboard("/api/dashboard/intents", language),
          fetchDashboard("/api/dashboard/evolution?jours=14", language),
          fetchDashboard("/api/dashboard/hourly?heures=24", language),
          fetchDashboard("/api/dashboard/peak-hours", language),
          fetchDashboard("/api/dashboard/tendances", language),
          fetchDashboard("/api/dashboard/emerging-topics?limite=8", language),
          fetchDashboard("/api/dashboard/unresolved?limite=10", language),
          fetchDashboard("/api/dashboard/feedback-summary", language),
        ]);
        if (!active) return;
        setData({
          overview,
          questions: questions.top_questions ?? [],
          categories: categories.categories ?? [],
          intents: intents.intents ?? [],
          evolution: evolution.evolution ?? [],
          hourly: hourly.hourly ?? [],
          peakHours: peakHours.heures ?? [],
          trends: trends.tendances ?? [],
          emerging: emerging.sujets ?? [],
          unresolved: unresolved.questions_non_resolues ?? [],
          feedback: feedback ?? { distribution: [] },
        });
        setLastUpdated(new Date());
      } catch (err) {
        if (active) setError(`${t.apiError} ${err.message || ""}`.trim());
      } finally {
        if (active) setLoading(false);
      }
    }

    loadData(true);
    const refreshTimer = window.setInterval(() => loadData(false), REFRESH_MS);
    return () => {
      active = false;
      window.clearInterval(refreshTimer);
    };
  }, [language]);

  const overview = data.overview || {};
  const ratingData = useMemo(
    () => (data.feedback?.distribution || []).map((item) => ({ ...item, label: `${item.rating}★` })),
    [data.feedback]
  );

  const formatPercent = (value) => value == null ? "—" : `${value}%`;
  const formatRating = (value) => value == null ? "—" : `${value} / 5`;
  const formatLatency = (value) => value == null ? t.noLatency : `${Math.round(value)} ms`;

  if (loading) {
    return <main className="dashboard-page" aria-live="polite"><p className="dashboard-loading">{t.loading}</p></main>;
  }

  if (error && !lastUpdated) {
    return (
      <main className="dashboard-page">
        <header className="dashboard-header"><div><p className="dashboard-eyebrow">ESIC ASSISTANT</p><h1>{t.title}</h1></div></header>
        <div className="dashboard-error" role="alert"><strong>{t.apiError}</strong><p>{error}</p><p>{t.apiHint}</p></div>
      </main>
    );
  }

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <p className="dashboard-eyebrow">ESIC ASSISTANT</p>
          <h1>{t.title}</h1>
          <p className="dashboard-subtitle">{t.subtitle}</p>
        </div>
        <div className="dashboard-live-wrap">
          <span className="dashboard-live"><span className="dashboard-live-dot" />{t.live}</span>
          {lastUpdated && <span className="dashboard-updated">{t.updated} {lastUpdated.toLocaleTimeString(language === "en" ? "en-GB" : "fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>}
        </div>
      </header>

      {error && <div className="dashboard-warning" role="status">{error}</div>}

      <section className="dashboard-stats dashboard-stats-5">
        <StatCard label={t.totalQuestions} value={overview.total_questions ?? 0} description={t.totalQuestionsDesc} />
        <StatCard label={t.questions24h} value={overview.questions_24h ?? 0} description={t.questions24hDesc} />
        <StatCard label={t.sessions} value={overview.sessions ?? 0} description={t.sessionsDesc} />
        <StatCard label={t.resolution} value={formatPercent(overview.resolution_rate)} description={t.resolutionDesc} />
        <StatCard label={t.avgRating} value={formatRating(overview.average_rating)} description={t.avgRatingDesc} />
        <StatCard label={t.satisfactionRate} value={formatPercent(overview.satisfaction_rate)} description={t.satisfactionRateDesc} />
        <StatCard label={t.responseTime} value={formatLatency(overview.average_response_ms)} description={t.responseTimeDesc} />
        <StatCard label={t.categoryConfidence} value={formatPercent(overview.average_category_confidence)} description={t.categoryConfidenceDesc} />
        <StatCard label={t.intentConfidence} value={formatPercent(overview.average_intent_confidence)} description={t.intentConfidenceDesc} />
        <StatCard label={t.unresolved} value={overview.unresolved_count ?? 0} description={t.unresolvedDesc} />
        <StatCard label={t.peakHour} value={overview.peak_hour ?? "—"} description={`${t.peakHourDesc}${overview.peak_hour_count ? ` · ${overview.peak_hour_count} ${t.questions.toLowerCase()}` : ""}`} />
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-panel dashboard-panel-wide">
          <PanelTitle title={t.hourly} description={t.hourlyDesc} />
          <div className="dashboard-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.hourly}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" tick={{ fontSize: 11 }} interval={3} /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="nombre" name={t.questions} stroke="#5145cd" strokeWidth={3} dot={false} /></LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="dashboard-panel dashboard-panel-wide">
          <PanelTitle title={t.evolution} description={t.evolutionDesc} />
          <div className="dashboard-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.evolution}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="nombre" name={t.questions} stroke="#159a92" strokeWidth={3} dot={false} /></LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <DonutPanel title={t.categories} description={t.categoriesDesc} data={data.categories} dataKey="nombre" nameKey="categorie" language={language} dictionary={CATEGORY_EN} emptyText={t.noQuestions} />
        <DonutPanel title={t.intents} description={t.intentsDesc} data={data.intents} dataKey="nombre" nameKey="intent" language={language} dictionary={INTENT_EN} emptyText={t.noQuestions} />

        <article className="dashboard-panel dashboard-panel-wide">
          <PanelTitle title={t.frequent} description={t.frequentDesc} />
          {data.questions.length ? (
            <div className="dashboard-chart dashboard-bar-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.questions} layout="vertical" margin={{ top: 8, right: 20, bottom: 8, left: 8 }}><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="question" width={210} tick={{ fontSize: 11 }} interval={0} /><Tooltip /><Bar dataKey="nombre" name={t.occurrences} fill="#5145cd" radius={[0, 6, 6, 0]} /></BarChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="dashboard-empty">{t.noQuestions}</p>}
        </article>

        <article className="dashboard-panel">
          <PanelTitle title={t.trends} description={t.trendsDesc} />
          {data.trends.length ? <div className="dashboard-trends">{data.trends.map((item) => (
            <div className="dashboard-trend-row" key={item.categorie}>
              <div className="dashboard-trend-info"><strong>{translateLabel(item.categorie, language, CATEGORY_EN)}</strong><p>{item.questions_7_derniers_jours} {t.against} {item.questions_7_jours_precedents}</p></div>
              <span className={item.evolution > 0 ? "trend-up" : item.evolution < 0 ? "trend-down" : "trend-neutral"}>{item.evolution > 0 ? "+" : ""}{item.evolution}%</span>
            </div>
          ))}</div> : <p className="dashboard-empty">{t.noData}</p>}
        </article>

        <article className="dashboard-panel">
          <PanelTitle title={t.emerging} description={t.emergingDesc} />
          {data.emerging.length ? <div className="dashboard-trends">{data.emerging.map((item) => (
            <div className="dashboard-trend-row" key={item.sujet}>
              <div className="dashboard-trend-info"><strong>{item.sujet}</strong><p>{item.questions_7_derniers_jours} {t.against} {item.questions_7_jours_precedents}</p></div>
              <span className={item.variation > 0 ? "trend-up" : item.variation < 0 ? "trend-down" : "trend-neutral"}>{item.variation > 0 ? "+" : ""}{item.variation}</span>
            </div>
          ))}</div> : <p className="dashboard-empty">{t.noData}</p>}
        </article>

        <article className="dashboard-panel dashboard-panel-wide">
          <PanelTitle title={t.peakHours} description={t.peakHoursDesc} />
          <div className="dashboard-chart dashboard-compact-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.peakHours}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="heure" tick={{ fontSize: 10 }} interval={2} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="nombre" name={t.questions} fill="#6485e5" radius={[5, 5, 0, 0]} /></BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="dashboard-panel">
          <PanelTitle title={t.ratings} description={t.ratingsDesc} />
          {data.feedback?.total ? (
            <div className="dashboard-chart dashboard-compact-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ratingData}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="label" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name={t.occurrences} fill="#f0a43c" radius={[5, 5, 0, 0]} /></BarChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="dashboard-empty">{t.noRatings}</p>}
        </article>

        <article className="dashboard-panel">
          <PanelTitle title={t.unresolvedList} description={t.unresolvedListDesc} />
          {data.unresolved.length ? <div className="dashboard-unresolved-list">{data.unresolved.map((item, index) => (
            <div className="dashboard-unresolved-item" key={`${item.question}-${index}`}>
              <strong>{item.question}</strong>
              <span>{t.category} : {translateLabel(item.categorie, language, CATEGORY_EN)}</span>
              <span>{t.reason} : {item.raison}</span>
            </div>
          ))}</div> : <p className="dashboard-empty">{t.noData}</p>}
        </article>
      </section>
    </main>
  );
}
