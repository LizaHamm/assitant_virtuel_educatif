
import { useEffect, useState } from "react";
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

const PIE_COLORS = [
  "#5145cd",
  "#159a92",
  "#f0a43c",
  "#dc6482",
  "#6485e5",
  "#8b6cc1",
];

const TEXT = {
  fr: {
    loading: "Chargement du tableau de bord…",
    title: "Tableau de bord",
    subtitle: "Consultez l’utilisation de l’assistant éducatif.",
    loaded: "Statistiques chargées",
    questions: "Questions enregistrées",
    questionsDesc: "Total des questions présentes dans les journaux",
    categories: "Catégories détectées",
    categoriesDesc: "Catégories estimées à partir des questions",
    last14: "Questions sur 14 jours",
    last14Desc: "Questions enregistrées sur la période",
    evolution: "Évolution des questions",
    evolutionDesc: "Activité quotidienne sur les 14 derniers jours",
    distribution: "Répartition par catégorie",
    classification: "Classification indicative",
    frequent: "Questions les plus fréquentes",
    frequentDesc: "Les 10 formulations les plus souvent rencontrées",
    trends: "Tendances",
    trendsDesc: "7 derniers jours comparés aux 7 précédents",
    noQuestions: "Aucune question enregistrée.",
    noData: "Pas encore assez de données.",
    occurrences: "Occurrences",
    questionsLabel: "Questions",
    against: "contre",
    apiError: "Impossible de charger les statistiques.",
    apiHint: "Vérifiez que le backend FastAPI est démarré et que les routes répondent.",
    genericError: "Une erreur est survenue.",
  },
  en: {
    loading: "Loading dashboard…",
    title: "Dashboard",
    subtitle: "Explore usage of the educational assistant.",
    loaded: "Statistics loaded",
    questions: "Recorded questions",
    questionsDesc: "Total questions available in the logs",
    categories: "Detected categories",
    categoriesDesc: "Categories estimated from the questions",
    last14: "Questions over 14 days",
    last14Desc: "Questions recorded during this period",
    evolution: "Question activity",
    evolutionDesc: "Daily activity over the last 14 days",
    distribution: "Category breakdown",
    classification: "Indicative classification",
    frequent: "Most frequent questions",
    frequentDesc: "The 10 most frequently encountered questions",
    trends: "Trends",
    trendsDesc: "Last 7 days compared with the previous 7 days",
    noQuestions: "No questions have been recorded.",
    noData: "Not enough data yet.",
    occurrences: "Occurrences",
    questionsLabel: "Questions",
    against: "vs.",
    apiError: "Unable to load statistics.",
    apiHint: "Make sure the FastAPI backend is running and the endpoints are responding.",
    genericError: "Something went wrong.",
  },
};

const CATEGORY_LABELS = {
  fr: {},
  en: {
    general: "General",
    generalites: "General",
    formations: "Programs",
    formation: "Programs",
    scolarite: "Student services",
    examens: "Exams",
    examen: "Exams",
    vacances: "Holidays",
    bibliotheque: "Library",
    contacts: "Contacts",
    campus: "Campus",
    reglement: "Campus rules",
    reglements: "Campus rules",
    sanctions: "Penalties",
    stages: "Internships",
    alternance: "Work-study",
    administratif: "Administration",
    administration: "Administration",
  },
};

function translateCategory(category, language) {
  if (!category) return language === "en" ? "Other" : "Autre";

  const key = String(category).trim().toLowerCase();

  return CATEGORY_LABELS[language]?.[key] || category;
}

async function fetchDashboard(path, language) {
  const response = await fetch(`${API_URL}${path}`);

  if (!response.ok) {
    throw new Error(
      language === "en"
        ? `API error (${response.status})`
        : `Erreur API (${response.status})`
    );
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

export default function Dashboard() {
  const [language, setLanguage] = useState(
    () => localStorage.getItem("esicLanguage") || "fr"
  );

  const [data, setData] = useState({
    questions: [],
    categories: [],
    evolution: [],
    trends: [],
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const t = TEXT[language] || TEXT.fr;

  useEffect(() => {
    const syncLanguage = () => {
      setLanguage(localStorage.getItem("esicLanguage") || "fr");
    };

    window.addEventListener("storage", syncLanguage);

    // L'événement storage ne se déclenche pas dans le même onglet.
    const timer = window.setInterval(syncLanguage, 300);

    return () => {
      window.removeEventListener("storage", syncLanguage);
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadData() {
      setLoading(true);
      setError("");

      try {
        const [questions, categories, evolution, trends] = await Promise.all([
          fetchDashboard("/api/dashboard/top-questions?limite=10", language),
          fetchDashboard("/api/dashboard/categories", language),
          fetchDashboard("/api/dashboard/evolution?jours=14", language),
          fetchDashboard("/api/dashboard/tendances", language),
        ]);

        if (!active) return;

        setData({
          questions: questions.top_questions ?? [],
          categories: categories.categories ?? [],
          evolution: evolution.evolution ?? [],
          trends: trends.tendances ?? [],
        });
      } catch (err) {
        if (active) {
          setError(
            `${t.apiError} ${err.message || t.genericError}`
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadData();

    return () => {
      active = false;
    };
  }, [language]);

  const totalQuestions = data.categories.reduce(
    (sum, item) => sum + (Number(item.nombre) || 0),
    0
  );

  const totalLast14Days = data.evolution.reduce(
    (sum, item) => sum + (Number(item.nombre) || 0),
    0
  );

  if (loading) {
    return (
      <main className="dashboard-page" aria-live="polite">
        <p className="dashboard-loading">{t.loading}</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="dashboard-page">
        <header className="dashboard-header">
          <div>
            <p className="dashboard-eyebrow">ESIC ASSISTANT</p>
            <h1>{t.title}</h1>
          </div>
        </header>

        <div className="dashboard-error" role="alert">
          <strong>{t.apiError}</strong>
          <p>{error}</p>
          <p>{t.apiHint}</p>
        </div>
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

        <span className="dashboard-live">
          <span className="dashboard-live-dot" />
          {t.loaded}
        </span>
      </header>

      <section className="dashboard-stats">
        <StatCard
          label={t.questions}
          value={totalQuestions}
          description={t.questionsDesc}
        />

        <StatCard
          label={t.categories}
          value={data.categories.length}
          description={t.categoriesDesc}
        />

        <StatCard
          label={t.last14}
          value={totalLast14Days}
          description={t.last14Desc}
        />
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-panel dashboard-panel-wide">
          <div className="dashboard-panel-heading">
            <div>
              <h2>{t.evolution}</h2>
              <p>{t.evolutionDesc}</p>
            </div>
          </div>

          <div className="dashboard-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.evolution}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="nombre"
                  name={t.questionsLabel}
                  stroke="#5145cd"
                  strokeWidth={3}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="dashboard-panel">
          <div className="dashboard-panel-heading">
            <div>
              <h2>{t.distribution}</h2>
              <p>{t.classification}</p>
            </div>
          </div>

          {data.categories.length ? (
            <div className="dashboard-chart dashboard-pie-chart">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.categories}
                    dataKey="nombre"
                    nameKey="categorie"
                    innerRadius={48}
                    outerRadius={78}
                    paddingAngle={3}
                  >
                    {data.categories.map((item, index) => (
                      <Cell
                        key={item.categorie || index}
                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value, name) => [
                      value,
                      translateCategory(name, language),
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="dashboard-empty">{t.noQuestions}</p>
          )}

          <div className="dashboard-legend">
            {data.categories.map((item, index) => (
              <div
                className="dashboard-legend-item"
                key={item.categorie || index}
              >
                <span
                  className="dashboard-legend-color"
                  style={{
                    background: PIE_COLORS[index % PIE_COLORS.length],
                  }}
                />
                <span className="dashboard-legend-name">
                  {translateCategory(item.categorie, language)}
                </span>
                <strong>{item.nombre}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="dashboard-panel dashboard-panel-wide">
          <div className="dashboard-panel-heading">
            <div>
              <h2>{t.frequent}</h2>
              <p>{t.frequentDesc}</p>
            </div>
          </div>

          {data.questions.length ? (
            <div className="dashboard-chart dashboard-bar-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.questions}
                  layout="vertical"
                  margin={{ top: 8, right: 20, bottom: 8, left: 8 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    horizontal={false}
                  />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis
                    type="category"
                    dataKey="question"
                    width={180}
                    tick={{ fontSize: 11 }}
                    interval={0}
                  />
                  <Tooltip />
                  <Bar
                    dataKey="nombre"
                    name={t.occurrences}
                    fill="#5145cd"
                    radius={[0, 6, 6, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="dashboard-empty">{t.noQuestions}</p>
          )}
        </article>

        <article className="dashboard-panel">
          <div className="dashboard-panel-heading">
            <div>
              <h2>{t.trends}</h2>
              <p>{t.trendsDesc}</p>
            </div>
          </div>

          {data.trends.length ? (
            <div className="dashboard-trends">
              {data.trends.map((item) => (
                <div
                  className="dashboard-trend-row"
                  key={item.categorie}
                >
                  <div className="dashboard-trend-info">
                    <strong>
                      {translateCategory(item.categorie, language)}
                    </strong>
                    <p>
                      {item.questions_7_derniers_jours} {t.against}{" "}
                      {item.questions_7_jours_precedents}
                    </p>
                  </div>

                  <span
                    className={
                      item.evolution > 0
                        ? "trend-up"
                        : item.evolution < 0
                          ? "trend-down"
                          : "trend-neutral"
                    }
                  >
                    {item.evolution > 0 ? "+" : ""}
                    {item.evolution}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="dashboard-empty">{t.noData}</p>
          )}
        </article>
      </section>
    </main>
  );
}
