import { useCallback, useEffect, useState } from "react";
import { api, apiList, clearSession } from "../api";
import { go } from "../router";

const STATUS_LABELS = {
  new: "Envoyée",
  answered: "Réponse reçue",
  accepted: "Acceptée par vous",
  in_progress: "Réparation en cours",
  declined: "Refusée",
  completed: "Terminée",
  cancelled: "Annulée",
};

const setWhenChanged = (setter, nextValue) =>
  setter((currentValue) =>
    JSON.stringify(currentValue) === JSON.stringify(nextValue)
      ? currentValue
      : nextValue
  );

export default function CustomerDashboard({ user, onLogout }) {
  const [quotes, setQuotes] = useState([]);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyQuoteId, setBusyQuoteId] = useState(null);

  const loadQuotes = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const items = await apiList("/quotes/");
      setWhenChanged(setQuotes, items);
      setError("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQuotes();
    const refresh = () => {
      if (document.visibilityState === "visible") loadQuotes(true);
    };
    const intervalId = window.setInterval(refresh, 15000);
    window.addEventListener("focus", refresh);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", refresh);
    };
  }, [loadQuotes]);

  const decide = async (quoteId, decision) => {
    setBusyQuoteId(quoteId);
    setError("");
    setNotice("");
    try {
      await api(`/quotes/${quoteId}/decide/`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      });
      setNotice(
        decision === "accepted"
          ? "Devis accepté. Le réparateur peut commencer le travail."
          : "Vous avez refusé le devis."
      );
      await loadQuotes();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyQuoteId(null);
    }
  };

  const cancel = async (quoteId) => {
    setBusyQuoteId(quoteId);
    setError("");
    setNotice("");
    try {
      await api(`/quotes/${quoteId}/cancel/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice("Votre demande a été annulée.");
      await loadQuotes();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyQuoteId(null);
    }
  };

  const logout = () => {
    clearSession();
    onLogout();
    go("accueil");
  };

  const newReplyCount = quotes.filter(
    (quote) => quote.status === "answered"
  ).length;
  const visibleQuotes =
    filter === "all" ? quotes : quotes.filter((quote) => quote.status === filter);

  return (
    <main className="dashboard customer-dashboard">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">ESPACE CLIENT</p>
          <h1>Bonjour{user.first_name ? ` ${user.first_name}` : ""}</h1>
          <p className="mu">
            Retrouvez les réponses des réparateurs et suivez vos demandes.
          </p>
        </div>
        <div className="row">
          <button className="btn" type="button" onClick={() => loadQuotes()}>
            Actualiser
          </button>
          <button className="btn" type="button" onClick={logout}>
            Se déconnecter
          </button>
        </div>
      </div>

      {newReplyCount > 0 && (
        <p className="form-success" role="status">
          Vous avez {newReplyCount} nouvelle{newReplyCount > 1 ? "s" : ""} réponse
          {newReplyCount > 1 ? "s" : ""} de réparateur.
        </p>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p className="form-success" role="status">{notice}</p>}

      <section className="dashboard-section">
        <div className="sec">
          <h2>Mes demandes de devis</h2>
          <a className="btn p" href="#resultats">Trouver un réparateur</a>
        </div>
        <div className="quote-filters" role="tablist" aria-label="Filtrer les demandes">
          {[
            ["all", "Toutes"],
            ["answered", "Réponses reçues"],
            ["accepted", "Acceptées"],
            ["in_progress", "En cours"],
            ["completed", "Terminées"],
          ].map(([value, label]) => (
            <button
              key={value}
              className={`chip${filter === value ? " on" : ""}`}
              type="button"
              role="tab"
              aria-selected={filter === value}
              onClick={() => setFilter(value)}
            >
              {label}
              {value === "answered" && newReplyCount > 0
                ? ` (${newReplyCount})`
                : ""}
            </button>
          ))}
        </div>

        {loading ? (
          <p className="card mu">Chargement de vos demandes…</p>
        ) : quotes.length === 0 ? (
          <div className="card customer-empty">
            <span className="stat-icon">🔎</span>
            <h3>Aucune demande pour le moment</h3>
            <p className="mu">
              Parcourez les ateliers librement. Connectez-vous uniquement lorsque
              vous souhaitez envoyer une demande de devis.
            </p>
            <a className="btn p" href="#resultats">Parcourir les réparateurs</a>
          </div>
        ) : visibleQuotes.length === 0 ? (
          <p className="card mu">Aucune demande dans cette catégorie.</p>
        ) : (
          <div className="dashboard-list">
            {visibleQuotes.map((quote) => (
              <article
                className={`card quote-card${quote.status === "answered" ? " quote-card-reply" : ""}`}
                key={quote.id}
              >
                <div className="row">
                  <h3>{quote.shop_name}</h3>
                  <span className={`shop-badge status-${quote.status}`}>
                    {STATUS_LABELS[quote.status] || quote.status}
                  </span>
                </div>
                <p className="mu">
                  {quote.vehicle_model} · {new Date(quote.created_at).toLocaleDateString("fr-FR")}
                </p>
                <p>{quote.problem}</p>
                {quote.mechanic_response ? (
                  <div className="mechanic-reply">
                    <b>Réponse du réparateur</b>
                    <p>{quote.mechanic_response}</p>
                  </div>
                ) : (
                  <p className="mu">En attente de la réponse du réparateur.</p>
                )}
                {quote.status === "answered" && (
                  <div className="row customer-quote-actions">
                    <button
                      className="btn p"
                      type="button"
                      disabled={busyQuoteId === quote.id}
                      onClick={() => decide(quote.id, "accepted")}
                    >
                      Accepter le devis
                    </button>
                    <button
                      className="btn"
                      type="button"
                      disabled={busyQuoteId === quote.id}
                      onClick={() => decide(quote.id, "declined")}
                    >
                      Refuser
                    </button>
                  </div>
                )}
                {["new", "answered"].includes(quote.status) && (
                  <button
                    className="text-button"
                    type="button"
                    disabled={busyQuoteId === quote.id}
                    onClick={() => cancel(quote.id)}
                  >
                    Annuler cette demande
                  </button>
                )}
                {quote.status === "completed" && (
                  <p className="form-success">Le réparateur a signalé que le travail est terminé.</p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
