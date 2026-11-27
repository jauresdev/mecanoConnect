import { useCallback, useEffect, useState } from "react";
import { api, apiList, clearSession } from "../api";
import { PrivateImage } from "../components/Common";
import { go } from "../router";

const STATUS_LABELS = {
  new: "En attente de réponse",
  answered: "Réponse reçue",
  discussion: "En discussion",
  declined: "Demande refusée",
  quote_sent: "Devis envoyé",
  quote_accepted: "Devis accepté",
  quote_declined: "Devis refusé",
  appointment_confirmed: "Rendez-vous confirmé",
  accepted: "Acceptée",
  in_progress: "Réparation en cours",
  completed: "Terminée",
  cancelled: "Annulée",
};

const CATEGORY_LABELS = {
  engine: "Panne moteur",
  electrical: "Problème électrique",
  brakes: "Freinage",
  battery: "Batterie",
  tires: "Pneumatique",
  maintenance: "Entretien",
  accident: "Accident",
  other: "Autre problème",
};

const EVENT_LABELS = {
  request_created: "Nouvelle demande",
  request_accepted: "Demande prise en charge",
  request_declined: "Demande refusée",
  message_received: "Nouveau message",
  quote_sent: "Nouveau devis",
  quote_accepted: "Devis accepté",
  quote_declined: "Devis refusé",
  quote_changes_requested: "Modification du devis demandée",
  appointment_proposed: "Proposition de rendez-vous",
  appointment_confirmed: "Rendez-vous confirmé",
  appointment_cancelled: "Rendez-vous annulé",
};

const money = (amount) =>
  `${Number(amount || 0).toLocaleString("fr-FR")} FCFA (XOF)`;

const setWhenChanged = (setter, nextValue) =>
  setter((currentValue) =>
    JSON.stringify(currentValue) === JSON.stringify(nextValue)
      ? currentValue
      : nextValue
  );

export default function CustomerDashboard({ user, onLogout, universe }) {
  const [quotes, setQuotes] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [filter, setFilter] = useState("all");
  const [messages, setMessages] = useState({});
  const [reportReasons, setReportReasons] = useState({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyQuoteId, setBusyQuoteId] = useState(null);

  const loadDashboard = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const [quoteList, notificationList, vehicleList] = await Promise.all([
        apiList("/quotes/"),
        apiList("/notifications/"),
        apiList("/vehicles/"),
      ]);
      setWhenChanged(setQuotes, quoteList);
      setWhenChanged(setNotifications, notificationList);
      setWhenChanged(setVehicles, vehicleList);
      setError("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    const refresh = () => {
      if (document.visibilityState === "visible") loadDashboard(true);
    };
    const intervalId = window.setInterval(refresh, 15000);
    window.addEventListener("focus", refresh);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", refresh);
    };
  }, [loadDashboard]);

  const runQuoteAction = async (quoteId, path, body, successMessage) => {
    setBusyQuoteId(quoteId);
    setError("");
    setNotice("");
    try {
      await api(`/quotes/${quoteId}/${path}/`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setNotice(successMessage);
      await loadDashboard(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyQuoteId(null);
    }
  };

  const decide = (quoteId, decision) =>
    runQuoteAction(
      quoteId,
      "decide",
      { decision },
      decision === "accepted"
        ? "Devis accepté. Aucun supplément ne pourra être engagé sans votre accord."
        : "Vous avez refusé le devis."
    );

  const sendMessage = (quoteId) => {
    const message = messages[quoteId]?.trim();
    if (!message) return;
    runQuoteAction(quoteId, "message", { message }, "Votre message a été envoyé.");
    setMessages((current) => ({ ...current, [quoteId]: "" }));
  };

  const requestChanges = (quoteId) =>
    runQuoteAction(
      quoteId,
      "request-changes",
      { reason: messages[quoteId]?.trim() || "" },
      "Votre demande de modification a été transmise au réparateur."
    );

  const cancelQuote = (quoteId) =>
    runQuoteAction(
      quoteId,
      "cancel",
      {},
      "Votre demande a été annulée."
    );

  const reportQuote = (quoteId) => {
    const reason = reportReasons[quoteId]?.trim();
    if (!reason) {
      setError("Indiquez le motif du signalement.");
      return;
    }
    runQuoteAction(
      quoteId,
      "report",
      { reason },
      "Votre signalement a été transmis à l’administration."
    );
    setReportReasons((current) => ({ ...current, [quoteId]: "" }));
  };

  const updateAppointment = async (appointmentId, action) => {
    setBusyQuoteId(`appointment-${appointmentId}`);
    setError("");
    try {
      await api(`/appointments/${appointmentId}/${action}/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice(
        action === "confirm"
          ? "Votre rendez-vous est confirmé."
          : "Le rendez-vous a été annulé. Vous pourrez convenir d’une nouvelle date."
      );
      await loadDashboard(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyQuoteId(null);
    }
  };

  const markNotificationRead = async (notificationId) => {
    try {
      await api(`/notifications/${notificationId}/read/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await loadDashboard(true);
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const logout = () => {
    clearSession();
    onLogout();
    go("accueil");
  };

  const newReplyCount = notifications.filter((item) => !item.is_read).length;
  const visibleQuotes =
    filter === "all" ? quotes : quotes.filter((quote) => quote.status === filter);

  return (
    <main className="dashboard customer-dashboard">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">ESPACE CLIENT · {universe.name.toUpperCase()}</p>
          <h1>Bonjour{user.first_name ? ` ${user.first_name}` : ""}</h1>
          <p className="mu">
            Retrouvez vos véhicules, les échanges avec les réparateurs, les devis
            et vos rendez-vous.
          </p>
        </div>
        <div className="row">
          <button className="btn" type="button" onClick={() => loadDashboard()}>
            Actualiser
          </button>
          <button className="btn" type="button" onClick={logout}>
            Se déconnecter
          </button>
        </div>
      </div>

      {newReplyCount > 0 && (
        <p className="form-success" role="status">
          Vous avez {newReplyCount} notification{newReplyCount > 1 ? "s" : ""} à consulter.
        </p>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p className="form-success" role="status">{notice}</p>}

      <section className="dashboard-section">
        <div className="sec">
          <h2>Mes véhicules</h2>
          <a className="btn p" href="#resultats">Demander une réparation</a>
        </div>
        {vehicles.length ? (
          <div className="dashboard-list">
            {vehicles.map((vehicle) => (
              <article className="card" key={vehicle.id}>
                <b>{vehicle.vehicle_type_name} · {vehicle.make} {vehicle.model}</b>
                {vehicle.year && <span className="mu"> · {vehicle.year}</span>}
                {vehicle.registration && <p className="mu">Immatriculation : {vehicle.registration}</p>}
              </article>
            ))}
          </div>
        ) : (
          <p className="card mu">
            Enregistrez un véhicule depuis le formulaire de demande pour pouvoir le
            sélectionner lors de vos prochaines réparations.
          </p>
        )}
      </section>

      <section className="dashboard-section">
        <div className="sec"><h2>Notifications</h2></div>
        {notifications.length === 0 ? (
          <p className="card mu">Aucune notification.</p>
        ) : (
          <div className="dashboard-list">
            {notifications.slice(0, 10).map((notification) => (
              <article className="card" key={notification.id}>
                <div className="row">
                  <b>{EVENT_LABELS[notification.event] || notification.event}</b>
                  {!notification.is_read && (
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => markNotificationRead(notification.id)}
                    >
                      Marquer comme lue
                    </button>
                  )}
                </div>
                <p>{notification.message}</p>
                <p className="mu">{new Date(notification.created_at).toLocaleString("fr-FR")}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <div className="sec">
          <h2>Mes demandes d’intervention</h2>
          <a className="btn p" href="#resultats">Trouver un réparateur</a>
        </div>
        <div className="quote-filters" role="tablist" aria-label="Filtrer les demandes">
          {[
            ["all", "Toutes"],
            ["new", "En attente"],
            ["discussion", "En discussion"],
            ["quote_sent", "Devis reçus"],
            ["quote_accepted", "Devis acceptés"],
            ["appointment_confirmed", "Rendez-vous"],
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
            </button>
          ))}
        </div>

        {loading ? (
          <p className="card mu">Chargement de vos demandes…</p>
        ) : quotes.length === 0 ? (
          <div className="card customer-empty">
            <span className="stat-icon">🔎</span>
            <h3>Aucune demande pour le moment</h3>
            <p className="mu">Parcourez les ateliers et envoyez une demande lorsque vous êtes prêt.</p>
            <a className="btn p" href="#resultats">Parcourir les réparateurs</a>
          </div>
        ) : visibleQuotes.length === 0 ? (
          <p className="card mu">Aucune demande dans cette catégorie.</p>
        ) : (
          <div className="dashboard-list">
            {visibleQuotes.map((quote) => {
              const activeOffer = quote.offers?.find((offer) => offer.status === "sent");
              return (
                <article className="card quote-card" key={quote.id}>
                  <div className="row">
                    <h3>{quote.shop_name}</h3>
                    <span className={`shop-badge status-${quote.status}`}>
                      {STATUS_LABELS[quote.status] || quote.status}
                    </span>
                  </div>
                  <p className="mu">
                    {quote.vehicle_model} · {CATEGORY_LABELS[quote.category] || quote.category} · {new Date(quote.created_at).toLocaleDateString("fr-FR")}
                  </p>
                  <p>{quote.problem}</p>
                  {quote.location && <p><b>Localisation :</b> {quote.location}</p>}
                  <p className="mu">
                    Intervention {quote.service_mode === "on_site" ? "sur place" : "en atelier"}
                    {quote.availability ? ` · Disponibilités : ${quote.availability}` : ""}
                  </p>
                  {quote.attachments?.length > 0 && (
                    <div className="row">
                      {quote.attachments.map((attachment) => (
                        <PrivateImage
                          key={attachment.id}
                          className="shop-photo-preview"
                          src={attachment.image}
                          alt="Photo du problème signalé"
                        />
                      ))}
                    </div>
                  )}

                  {quote.refusal_reason && (
                    <div className="mechanic-reply">
                      <b>Motif de refus</b>
                      <p>{quote.refusal_reason}</p>
                    </div>
                  )}
                  {quote.mechanic_response && (
                    <div className="mechanic-reply">
                      <b>Réponse du réparateur</b>
                      <p>{quote.mechanic_response}</p>
                    </div>
                  )}

                  {quote.offers?.length > 0 && (
                    <section className="mechanic-reply">
                      <b>Historique des devis estimatifs</b>
                      {quote.offers.map((offer) => (
                        <div key={offer.id} className="quote-offer">
                          <h4>Version {offer.version} · {offer.is_supplemental ? "Devis complémentaire" : "Devis initial"} · {offer.status}</h4>
                          <p>{offer.description}</p>
                          {offer.parts.map((part) => (
                            <p key={part.id} className="mu">
                              {part.quantity} × {part.name} — {money(part.unit_price)} / pièce
                            </p>
                          ))}
                          <p>Main-d’œuvre : {money(offer.labor_cost)}</p>
                          <p>Déplacement : {money(offer.travel_cost)}</p>
                          <p><b>Total estimatif : {money(offer.total)}</b></p>
                          <p>Durée estimée : {offer.estimated_duration_minutes} min · Valide jusqu’au {new Date(`${offer.valid_until}T00:00:00`).toLocaleDateString("fr-FR")}</p>
                          {offer.conditions && <p>Conditions : {offer.conditions}</p>}
                        </div>
                      ))}
                    </section>
                  )}

                  {quote.status === "quote_sent" && activeOffer && (
                    activeOffer.is_expired ? (
                      <div>
                        <p className="form-error" role="status">
                          Ce devis estimatif a expiré. Demandez une nouvelle proposition au réparateur.
                        </p>
                        <button
                          className="btn"
                          type="button"
                          disabled={busyQuoteId === quote.id}
                          onClick={() => decide(quote.id, "declined")}
                        >
                          Refuser le devis expiré
                        </button>
                      </div>
                    ) : (
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
                    )
                  )}

                  {["new", "discussion", "answered", "quote_sent"].includes(quote.status) && (
                    <div className="quote-reply">
                      <label htmlFor={`message-${quote.id}`}>Votre message au réparateur</label>
                      <textarea
                        id={`message-${quote.id}`}
                        rows="2"
                        maxLength="3000"
                        value={messages[quote.id] || ""}
                        onChange={(event) => setMessages({ ...messages, [quote.id]: event.target.value })}
                      />
                      <div className="row">
                        <button
                          className="btn"
                          type="button"
                          disabled={busyQuoteId === quote.id || !messages[quote.id]?.trim()}
                          onClick={() => sendMessage(quote.id)}
                        >
                          Envoyer un message
                        </button>
                        {quote.status === "quote_sent" && (
                          <button
                            className="btn"
                            type="button"
                            disabled={busyQuoteId === quote.id}
                            onClick={() => requestChanges(quote.id)}
                          >
                            Demander une modification du devis
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                  {quote.messages?.length > 0 && (
                    <details>
                      <summary>Voir les échanges ({quote.messages.length})</summary>
                      {quote.messages.map((message) => (
                        <p key={message.id}>
                          <b>{message.author_name}</b> · {new Date(message.created_at).toLocaleString("fr-FR")}
                          <br />{message.message}
                        </p>
                      ))}
                    </details>
                  )}

                  {quote.appointments?.map((appointment) => (
                    <div className="mechanic-reply" key={appointment.id}>
                      <b>Rendez-vous · {appointment.status}</b>
                      <p>{new Date(appointment.scheduled_at).toLocaleString("fr-FR")} · {appointment.duration_minutes} min</p>
                      {appointment.note && <p>{appointment.note}</p>}
                      {appointment.status === "proposed" && (
                        <button
                          className="btn p"
                          type="button"
                          disabled={busyQuoteId === `appointment-${appointment.id}`}
                          onClick={() => updateAppointment(appointment.id, "confirm")}
                        >
                          Confirmer ce rendez-vous
                        </button>
                      )}
                      {["proposed", "confirmed"].includes(appointment.status) && (
                        <button
                          className="btn"
                          type="button"
                          disabled={busyQuoteId === `appointment-${appointment.id}`}
                          onClick={() => updateAppointment(appointment.id, "cancel")}
                        >
                          Annuler / demander un report
                        </button>
                      )}
                    </div>
                  ))}

                  {["new", "discussion", "answered", "quote_sent", "quote_accepted"].includes(quote.status) && (
                    <button
                      className="text-button"
                      type="button"
                      disabled={busyQuoteId === quote.id}
                      onClick={() => cancelQuote(quote.id)}
                    >
                      Annuler cette demande
                    </button>
                  )}

                  {quote.status === "completed" && (
                    <p className="form-success">L’intervention est terminée.</p>
                  )}

                  <details>
                    <summary>Signaler un problème</summary>
                    <label htmlFor={`report-${quote.id}`}>Motif du signalement</label>
                    <textarea
                      id={`report-${quote.id}`}
                      rows="2"
                      maxLength="2000"
                      value={reportReasons[quote.id] || ""}
                      onChange={(event) => setReportReasons({ ...reportReasons, [quote.id]: event.target.value })}
                    />
                    <button
                      className="btn"
                      type="button"
                      disabled={busyQuoteId === quote.id}
                      onClick={() => reportQuote(quote.id)}
                    >
                      Envoyer le signalement
                    </button>
                  </details>

                  {quote.events?.length > 0 && (
                    <details>
                      <summary>Historique des actions</summary>
                      {quote.events.map((event) => (
                        <p key={event.id} className="mu">
                          {event.details} · {new Date(event.created_at).toLocaleString("fr-FR")}
                        </p>
                      ))}
                    </details>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
