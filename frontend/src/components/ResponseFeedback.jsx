
import { useState } from "react";

const API_URL = "http://127.0.0.1:8000";

export default function ResponseFeedback({
  conversationId,
  question,
  answer,
}) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  async function submitFeedback(event) {
    event.preventDefault();
    setError("");

    if (!conversationId || !question?.trim() || !answer?.trim()) {
      setError("Impossible d'associer cette évaluation à une réponse.");
      return;
    }

    if (rating < 1 || rating > 5) {
      setError("Choisissez une note entre 1 et 5.");
      return;
    }

    setSending(true);

    try {
      const response = await fetch(`${API_URL}/api/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          question,
          answer,
          rating,
          comment,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Échec de l'envoi.");
      }

      setSubmitted(true);
    } catch (err) {
      setError(err.message || "Impossible d'envoyer l'évaluation.");
    } finally {
      setSending(false);
    }
  }

  if (submitted) {
    return <p className="feedback-success">Merci pour votre retour !</p>;
  }

  return (
    <form className="response-feedback" onSubmit={submitFeedback}>
      <p>Cette réponse vous a-t-elle aidé ?</p>

      <div className="feedback-stars" aria-label="Note sur 5">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            className={value <= rating ? "star selected" : "star"}
            onClick={() => setRating(value)}
            aria-label={`${value} sur 5`}
            aria-pressed={rating === value}
          >
            ★
          </button>
        ))}
      </div>

      <textarea
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder="Commentaire facultatif"
        maxLength={1000}
        rows={2}
      />

      {error && <p className="feedback-error">{error}</p>}

      <button type="submit" disabled={sending || rating === 0}>
        {sending ? "Envoi..." : "Envoyer l'évaluation"}
      </button>
    </form>
  );
}
