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

async function fetchDashboard(path) {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Erreur API (${response.status})`);
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
  const [data, setData] = useState({
    questions: [],
    categories: [],
    evolution: [],
    trends: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    Promise.all([
      fetchDashboard("/api/dashboard/top-questions?limite=10"),
      fetchDashboard("/api/dashboard/categories"),
      fetchDashboard("/api/dashboard/evolution?jours=14"),
      fetchDashboard("/api/dashboard/tendances"),
    ])
      .then(([questions, categories, evolution, trends]) => {
        if (!active) return;
        setData({
          questions: questions.top_questions ?? [],
          categories: categories.categories ?? [],
          evolution: evolution.evolution ?? [],
          trends: trends.tendances ?? [],
        });
      })
      .catch((err) => {
        if (active) setError(err.message || "Impossible de charger les statistiques.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const totalQuestions = data.categories.reduce(
    (sum, item) => sum + item.nombre,
    0
  );

  if (loading) {
    return <main className="dashboard-page"><p>Chargement du tableau de bord…</p></main>;
  }

  if (error) {
    return (
      <main className="dashboard-page">
        <h1>Tableau de bord</h1>
        <p className="dashboard-error">{error}</p>
        <p>Vérifie que le backend FastAPI est démarré et que les routes répondent.</p>
      </main>
    );
  }

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <p className="dashboard-eyebrow">ESIC ASSISTANT</p>
          <h1>Tableau de bord</h1>
          <p className="dashboard-subtitle">
            Consulte l’utilisation de l’assistant éducatif.
          </p>
        </div>
        <span className="dashboard-live">
          <span /> Statistiques chargées
        </span>
      </header>

      <section className="dashboard-stats">
        <StatCard
          label="Questions enregistrées"
          value={totalQuestions}
          description="Total des questions présentes dans les logs"
        />
        <StatCard
          label="Catégories détectées"
          value={data.categories.length}
          description="Catégories estimées à partir des questions"
        />
        <StatCard
          label="Questions sur 14 jours"
          value={data.evolution.reduce((sum, item) => sum + item.nombre, 0)}
          description="Questions enregistrées sur la période"
        />
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-panel dashboard-panel-wide">
          <div className="dashboard-panel-heading">
            <div>
              <h2>Évolution des questions</h2>
              <p>Activité quotidienne sur les 14 derniers jours</p>
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
                  name="Questions"
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
              <h2>Répartition par catégorie</h2>
              <p>Classification indicative</p>
            </div>
          </div>
          {data.categories.length ? (
            <div className="dashboard-chart">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.categories}
                    dataKey="nombre"
                    nameKey="categorie"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                  >
                    {data.categories.map((item, index) => (
                      <Cell
                        key={item.categorie}
                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="dashboard-empty">Aucune question enregistrée.</p>
          )}
          <div className="dashboard-legend">
            {data.categories.map((item, index) => (
              <div className="dashboard-legend-item" key={item.categorie}>
                <span style={{ background: PIE_COLORS[index % PIE_COLORS.length] }} />
                <span>{item.categorie}</span>
                <strong>{item.nombre}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="dashboard-panel dashboard-panel-wide">
          <div className="dashboard-panel-heading">
            <div>
              <h2>Questions les plus fréquentes</h2>
              <p>Les 10 formulations les plus souvent rencontrées</p>
            </div>
          </div>
          {data.questions.length ? (
            <div className="dashboard-chart dashboard-bar-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.questions} layout="vertical" margin={{ left: 12, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis
                    type="category"
                    dataKey="question"
                    width={180}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip />
                  <Bar dataKey="nombre" name="Occurrences" fill="#5145cd" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="dashboard-empty">Aucune question enregistrée.</p>
          )}
        </article>

        <article className="dashboard-panel">
          <div className="dashboard-panel-heading">
            <div>
              <h2>Tendances</h2>
              <p>7 derniers jours comparés aux 7 précédents</p>
            </div>
          </div>
          {data.trends.length ? (
            <div className="dashboard-trends">
              {data.trends.map((item) => (
                <div className="dashboard-trend-row" key={item.categorie}>
                  <div>
                    <strong>{item.categorie}</strong>
                    <p>
                      {item.questions_7_derniers_jours} contre{" "}
                      {item.questions_7_jours_precedents}
                    </p>
                  </div>
                  <span className={item.evolution > 0 ? "trend-up" : item.evolution < 0 ? "trend-down" : ""}>
                    {item.evolution > 0 ? "+" : ""}
                    {item.evolution}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="dashboard-empty">Pas encore assez de données.</p>
          )}
        </article>
      </section>
    </main>
  );
}