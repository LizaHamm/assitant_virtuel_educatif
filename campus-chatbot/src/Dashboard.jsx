import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";

/* Couleurs et libellés associés à chaque catégorie "maison" (voir app.py,
   trouver_reponse). Le jour où l'US-014 (NLP) de tes camarades remplace la
   catégorie, ces deux objets n'ont qu'à être mis à jour avec leurs noms. */
const COULEURS_CATEGORIES = {
  horaires: "#087da8",
  calendrier: "#52c7a5",
  formations: "#48b8d0",
  contact: "#073b52",
  reglement: "#e0a458",
  general: "#9aabb2",
  sans_reponse: "#d9534f",
};

const LIBELLES_CATEGORIES = {
  horaires: "Horaires",
  calendrier: "Calendrier",
  formations: "Formations",
  contact: "Contacts",
  reglement: "Règlement",
  general: "Général",
  sans_reponse: "Sans réponse",
};

function Dashboard({ apiUrl }) {
  const [topQuestions, setTopQuestions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [evolution, setEvolution] = useState([]);
  const [tendances, setTendances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erreur, setErreur] = useState(null);

  useEffect(() => {
    chargerDonnees();
  }, []);

  async function chargerDonnees() {
    setLoading(true);
    setErreur(null);

    try {
      const [topRes, catRes, evoRes, tendRes] = await Promise.all([
        fetch(`${apiUrl}/api/dashboard/top-questions`),
        fetch(`${apiUrl}/api/dashboard/categories`),
        fetch(`${apiUrl}/api/dashboard/evolution?jours=14`),
        fetch(`${apiUrl}/api/dashboard/tendances`),
      ]);

      if (!topRes.ok || !catRes.ok || !evoRes.ok || !tendRes.ok) {
        throw new Error("Erreur serveur");
      }

      const top = await topRes.json();
      const cat = await catRes.json();
      const evo = await evoRes.json();
      const tend = await tendRes.json();

      setTopQuestions(top.top_questions);

      setCategories(
        cat.categories.map((c) => ({
          ...c,
          libelle: LIBELLES_CATEGORIES[c.categorie] || c.categorie,
        }))
      );

      setEvolution(
        evo.evolution.map((e) => ({
          ...e,
          jour: new Date(e.date).toLocaleDateString("fr-FR", {
            day: "2-digit",
            month: "2-digit",
          }),
        }))
      );

      setTendances(tend.tendances);
    } catch (error) {
      console.error(error);
      setErreur(
        "Impossible de charger les statistiques. Vérifie que le serveur Flask est bien démarré."
      );
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="dashboard-message">Chargement des statistiques...</div>;
  }

  if (erreur) {
    return <div className="dashboard-message dashboard-message-error">{erreur}</div>;
  }

  const totalQuestions = categories.reduce((somme, c) => somme + c.nombre, 0);

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Statistiques du chatbot</h2>
        <button type="button" className="dashboard-refresh" onClick={chargerDonnees}>
          Actualiser
        </button>
      </div>

      <div className="dashboard-stat-cards">
        <div className="stat-card">
          <span className="stat-value">{totalQuestions}</span>
          <span className="stat-label">Questions posées (total)</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{categories.length}</span>
          <span className="stat-label">Catégories détectées</span>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* US-019 : top des questions les plus posées */}
        <div className="dashboard-card">
          <h3>Top des questions les plus posées</h3>

          {topQuestions.length === 0 ? (
            <p className="dashboard-empty">Pas encore de données.</p>
          ) : (
            <ol className="top-questions-list">
              {topQuestions.map((q, index) => (
                <li key={index}>
                  <span className="top-question-text">{q.question}</span>
                  <span className="top-question-count">{q.nombre}</span>
                </li>
              ))}
            </ol>
          )}
        </div>

        {/* US-020 : répartition par catégorie */}
        <div className="dashboard-card">
          <h3>Répartition par catégorie</h3>

          {categories.length === 0 ? (
            <p className="dashboard-empty">Pas encore de données.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={categories} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" allowDecimals={false} />
                <YAxis type="category" dataKey="libelle" width={100} />
                <Tooltip />
                <Bar dataKey="nombre" radius={[0, 6, 6, 0]}>
                  {categories.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={COULEURS_CATEGORIES[entry.categorie] || "#087da8"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* US-021 : évolution du volume dans le temps */}
        <div className="dashboard-card dashboard-card-wide">
          <h3>Évolution du volume de questions (14 derniers jours)</h3>

          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={evolution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="jour" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="nombre"
                stroke="#087da8"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* US-022 : sujets émergents / tendances */}
        <div className="dashboard-card dashboard-card-wide">
          <h3>Tendances (7 derniers jours vs semaine précédente)</h3>

          {tendances.length === 0 ? (
            <p className="dashboard-empty">
              Pas encore assez de données pour comparer deux semaines.
            </p>
          ) : (
            <table className="tendances-table">
              <thead>
                <tr>
                  <th>Catégorie</th>
                  <th>Cette semaine</th>
                  <th>Semaine précédente</th>
                  <th>Évolution</th>
                </tr>
              </thead>
              <tbody>
                {tendances.map((t) => (
                  <tr key={t.categorie}>
                    <td>{LIBELLES_CATEGORIES[t.categorie] || t.categorie}</td>
                    <td>{t.questions_7_derniers_jours}</td>
                    <td>{t.questions_7_jours_precedents}</td>
                    <td
                      className={
                        t.evolution > 0
                          ? "trend-up"
                          : t.evolution < 0
                          ? "trend-down"
                          : "trend-flat"
                      }
                    >
                      {t.evolution > 0 ? "▲" : t.evolution < 0 ? "▼" : "–"}{" "}
                      {Math.abs(t.evolution)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;