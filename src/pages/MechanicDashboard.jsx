import { useCallback, useEffect, useState } from "react";
import { api, apiList, clearSession } from "../api";
import { PrivateImage } from "../components/Common";
import { parseMapLocation } from "../location";
import { go } from "../router";

const EMPTY_SHOP = {
  name: "",
  business_type: "garage",
  description: "",
  city: "Parakou",
  district: "",
  address: "",
  latitude: "",
  longitude: "",
  phone: "",
  whatsapp: "",
  opening_hours: {},
  mobile_service: false,
  services: [],
  vehicle_types: [],
};

const WEEK_DAYS = [
  ["monday", "Lundi"],
  ["tuesday", "Mardi"],
  ["wednesday", "Mercredi"],
  ["thursday", "Jeudi"],
  ["friday", "Vendredi"],
  ["saturday", "Samedi"],
  ["sunday", "Dimanche"],
];

const STATUS_LABELS = {
  new: "En attente de réponse",
  answered: "Répondue",
  discussion: "En discussion",
  quote_sent: "Devis envoyé",
  quote_accepted: "Devis accepté",
  quote_declined: "Devis refusé",
  appointment_confirmed: "Rendez-vous confirmé",
  accepted: "Acceptée",
  in_progress: "En cours",
  declined: "Refusée",
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

const setWhenChanged = (setter, nextValue) =>
  setter((currentValue) =>
    JSON.stringify(currentValue) === JSON.stringify(nextValue)
      ? currentValue
      : nextValue
  );

export default function MechanicDashboard({ user, onLogout, onPreviewShop }) {
  const [shops, setShops] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [services, setServices] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [shop, setShop] = useState(EMPTY_SHOP);
  const [locationInput, setLocationInput] = useState("");
  const [locationMessage, setLocationMessage] = useState("");
  const [photoFile, setPhotoFile] = useState(null);
  const [editingShopId, setEditingShopId] = useState(null);
  const [showShopForm, setShowShopForm] = useState(false);
  const [answers, setAnswers] = useState({});
  const [messages, setMessages] = useState({});
  const [offerForms, setOfferForms] = useState({});
  const [appointmentInputs, setAppointmentInputs] = useState({});
  const [declineReasons, setDeclineReasons] = useState({});
  const [quoteFilter, setQuoteFilter] = useState("all");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(true);
  const [savingShop, setSavingShop] = useState(false);
  const [savingQuoteId, setSavingQuoteId] = useState(null);

  const loadDashboard = useCallback(async (silent = false) => {
    if (!silent) setBusy(true);
    setError("");
    try {
      const [shopList, quoteList, serviceList, vehicleList, notificationList, appointmentList] = await Promise.all([
        apiList("/shops/"),
        apiList("/quotes/"),
        apiList("/services/"),
        apiList("/vehicle-types/"),
        apiList("/notifications/"),
        apiList("/appointments/"),
      ]);
      setWhenChanged(setShops, shopList.filter((item) => item.owner === user.id));
      setWhenChanged(setQuotes, quoteList);
      setWhenChanged(setNotifications, notificationList);
      setWhenChanged(setAppointments, appointmentList);
      setWhenChanged(setServices, serviceList);
      setWhenChanged(setVehicles, vehicleList);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      if (!silent) setBusy(false);
    }
  }, [user.id]);

  useEffect(() => {
    loadDashboard();
    const refresh = () => {
      if (document.visibilityState === "visible") loadDashboard(true);
    };
    const intervalId = window.setInterval(refresh, 30000);
    window.addEventListener("focus", refresh);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", refresh);
    };
  }, [loadDashboard]);

  const updateShop = (event) => {
    const { name, value, checked, type } = event.target;
    setShop({ ...shop, [name]: type === "checkbox" ? checked : value });
  };

  const updateSelection = (field, id) => {
    const selected = shop[field].includes(id)
      ? shop[field].filter((value) => value !== id)
      : [...shop[field], id];
    setShop({ ...shop, [field]: selected });
  };

  const updateOpeningHours = (day, value) => {
    setShop((currentShop) => {
      const openingHours = { ...currentShop.opening_hours };
      if (value === "closed") {
        openingHours[day] = null;
      } else if (value === "unknown") {
        delete openingHours[day];
      } else if (value === "open") {
        openingHours[day] = {
          open: openingHours[day]?.open || "",
          close: openingHours[day]?.close || "",
        };
      } else {
        openingHours[day] = {
          ...openingHours[day],
          [value.field]: value.value,
        };
      }
      return { ...currentShop, opening_hours: openingHours };
    });
  };

  const beginCreateShop = () => {
    setShop(EMPTY_SHOP);
    setLocationInput("");
    setLocationMessage("");
    setPhotoFile(null);
    setEditingShopId(null);
    setShowShopForm(true);
    setError("");
    setNotice("");
    document.getElementById("shop-form")?.scrollIntoView({ behavior: "smooth" });
  };

  const beginEditShop = (item) => {
    setLocationInput(
      item.latitude != null && item.longitude != null
        ? `${item.latitude}, ${item.longitude}`
        : ""
    );
    setLocationMessage("");
    setPhotoFile(null);
    setShop({
      name: item.name,
      business_type: item.business_type,
      description: item.description || "",
      city: item.city,
      district: item.district,
      address: item.address || "",
      latitude: item.latitude ?? "",
      longitude: item.longitude ?? "",
      phone: item.phone,
      whatsapp: item.whatsapp || "",
      opening_hours: item.opening_hours || {},
      mobile_service: item.mobile_service,
      services: item.services,
      vehicle_types: item.vehicle_types,
    });
    setEditingShopId(item.id);
    setShowShopForm(true);
    setError("");
    setNotice("");
    window.setTimeout(
      () => document.getElementById("shop-form")?.scrollIntoView({ behavior: "smooth" }),
      0
    );
  };

  const closeShopForm = () => {
    setShowShopForm(false);
    setEditingShopId(null);
    setShop(EMPTY_SHOP);
    setLocationInput("");
    setLocationMessage("");
    setPhotoFile(null);
    setError("");
  };

  const updateMapLocation = (event) => {
    const value = event.target.value;
    const coordinates = parseMapLocation(value);
    setLocationInput(value);
    setShop((currentShop) => ({
      ...currentShop,
      latitude: coordinates?.latitude ?? "",
      longitude: coordinates?.longitude ?? "",
    }));
    setLocationMessage(
      !value.trim()
        ? ""
        : coordinates
          ? `Position repérée : ${coordinates.latitude}, ${coordinates.longitude}`
          : "Coordonnées non reconnues. Collez la position copiée dans Google Maps ou un lien complet contenant les coordonnées."
    );
    setError("");
  };

  const saveShop = async (event) => {
    event.preventDefault();
    setError("");
    setNotice("");
    if (photoFile && photoFile.size > 5 * 1024 * 1024) {
      setError("La photo ne peut pas dépasser 5 Mo.");
      return;
    }
    const invalidHours = WEEK_DAYS.some(([day]) => {
      const hours = shop.opening_hours[day];
      return (
        hours &&
        (!hours.open ||
          !hours.close ||
          hours.open >= hours.close)
      );
    });
    if (invalidHours) {
      setError("Vérifiez les heures d’ouverture et de fermeture de chaque jour.");
      return;
    }
    if (locationInput.trim() && (shop.latitude === "" || shop.longitude === "")) {
      setError(
        "La localisation collée n’a pas été reconnue. Copiez les coordonnées Google Maps (ex. 9.337, 2.630) ou un lien complet contenant la position."
      );
      return;
    }
    setSavingShop(true);
    try {
      const savedShop = await api(editingShopId ? `/shops/${editingShopId}/` : "/shops/", {
        method: editingShopId ? "PATCH" : "POST",
        body: JSON.stringify({
          ...shop,
          latitude: shop.latitude === "" ? null : Number(shop.latitude),
          longitude: shop.longitude === "" ? null : Number(shop.longitude),
        }),
      });
      let photoError = "";
      if (photoFile) {
        const formData = new FormData();
        formData.append("photo", photoFile);
        try {
          await api(`/shops/${savedShop.id}/`, {
            method: "PATCH",
            body: formData,
          });
        } catch (uploadError) {
          photoError = ` Les autres informations ont été enregistrées, mais la photo n’a pas pu être envoyée : ${uploadError.message}`;
        }
      }
      setShop(EMPTY_SHOP);
      setShowShopForm(false);
      setEditingShopId(null);
      setPhotoFile(null);
      setNotice(
        (editingShopId
          ? "Les informations de votre atelier ont été mises à jour."
          : "Votre atelier est enregistré. Vous pouvez maintenant gérer sa fiche depuis Mes ateliers.") +
          photoError
      );
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingShop(false);
    }
  };

  const replyToQuote = async (quoteId) => {
    setError("");
    setNotice("");
    setSavingQuoteId(quoteId);
    try {
      await api(`/quotes/${quoteId}/respond/`, {
        method: "POST",
        body: JSON.stringify({ response: answers[quoteId] || "" }),
      });
      setAnswers({ ...answers, [quoteId]: "" });
      setNotice("Votre réponse a été envoyée au client.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingQuoteId(null);
    }
  };

  const acceptRequest = async (quoteId) => {
    setSavingQuoteId(quoteId);
    setError("");
    try {
      await api(`/quotes/${quoteId}/accept-request/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice("Vous avez accepté d’étudier cette demande.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingQuoteId(null);
    }
  };

  const declineRequest = async (quoteId) => {
    setSavingQuoteId(quoteId);
    setError("");
    try {
      await api(`/quotes/${quoteId}/decline-request/`, {
        method: "POST",
        body: JSON.stringify({ reason: declineReasons[quoteId] || "" }),
      });
      setNotice("La demande a été refusée.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingQuoteId(null);
    }
  };

  const sendMessage = async (quoteId) => {
    const message = messages[quoteId]?.trim();
    if (!message) return;
    setSavingQuoteId(quoteId);
    setError("");
    try {
      await api(`/quotes/${quoteId}/message/`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      setMessages((current) => ({ ...current, [quoteId]: "" }));
      setNotice("Votre message a été envoyé au client.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingQuoteId(null);
    }
  };

  const updateOffer = (quoteId, field, value) => {
    setOfferForms((current) => ({
      ...current,
      [quoteId]: {
        description: "",
        labor_cost: "",
        travel_cost: "0",
        estimated_duration_minutes: "60",
        valid_days: "7",
        conditions: "",
        parts: [{ name: "", quantity: "1", unit_price: "" }],
        ...current[quoteId],
        [field]: value,
      },
    }));
  };

  const updateOfferPart = (quoteId, index, field, value) => {
    const current = offerForms[quoteId] || {};
    const parts = current.parts || [{ name: "", quantity: "1", unit_price: "" }];
    updateOffer(quoteId, "parts", parts.map((part, partIndex) =>
      partIndex === index ? { ...part, [field]: value } : part
    ));
  };

  const createOffer = async (quoteId) => {
    const form = offerForms[quoteId] || {};
    const validUntil = new Date();
    validUntil.setDate(validUntil.getDate() + Number(form.valid_days || 7));
    const parts = (form.parts || []).filter((part) => part.name.trim()).map((part) => ({
      name: part.name.trim(),
      quantity: Number(part.quantity),
      unit_price: Number(part.unit_price),
    }));
    setSavingQuoteId(quoteId);
    setError("");
    try {
      await api(`/quotes/${quoteId}/offers/`, {
        method: "POST",
        body: JSON.stringify({
          description: form.description?.trim() || "",
          labor_cost: Number(form.labor_cost),
          travel_cost: Number(form.travel_cost || 0),
          estimated_duration_minutes: Number(form.estimated_duration_minutes),
          valid_until: validUntil.toISOString().slice(0, 10),
          conditions: form.conditions?.trim() || "",
          parts,
        }),
      });
      setNotice("Le devis estimatif a été envoyé au client.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingQuoteId(null);
    }
  };

  const proposeAppointment = async (quoteId) => {
    const scheduledAt = appointmentInputs[quoteId];
    if (!scheduledAt) return;
    setSavingQuoteId(quoteId);
    setError("");
    try {
      await api(`/quotes/${quoteId}/appointments/`, {
        method: "POST",
        body: JSON.stringify({ scheduled_at: new Date(scheduledAt).toISOString() }),
      });
      setAppointmentInputs((current) => ({ ...current, [quoteId]: "" }));
      setNotice("Votre proposition de rendez-vous a été envoyée.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingQuoteId(null);
    }
  };

  const updateAppointment = async (appointmentId) => {
    try {
      await api(`/appointments/${appointmentId}/cancel/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice("Le créneau a été annulé. Vous pouvez proposer une nouvelle date.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
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

  const completeQuote = async (quoteId) => {
    setError("");
    setNotice("");
    setSavingQuoteId(quoteId);
    try {
      await api(`/quotes/${quoteId}/complete/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice("La réparation est marquée comme terminée.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingQuoteId(null);
    }
  };

  const startQuote = async (quoteId) => {
    setError("");
    setNotice("");
    setSavingQuoteId(quoteId);
    try {
      await api(`/quotes/${quoteId}/start/`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      setNotice("La réparation est maintenant marquée comme en cours.");
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingQuoteId(null);
    }
  };

  const visibleQuotes =
    quoteFilter === "all"
      ? quotes
      : quotes.filter((quote) => quote.status === quoteFilter);
  const newQuoteCount = quotes.filter((quote) => quote.status === "new").length;
  const acceptedQuoteCount = quotes.filter((quote) => ["accepted", "quote_accepted", "appointment_confirmed", "in_progress"].includes(quote.status)).length;
  const completedQuoteCount = quotes.filter((quote) => quote.status === "completed").length;

  const logout = () => {
    clearSession();
    onLogout();
    go("accueil");
  };

  return (
    <main className="dashboard">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">ESPACE GARAGE & RÉPARATEUR</p>
          <h1>Bonjour{user.first_name ? ` ${user.first_name}` : ""}</h1>
          <p className="mu">Votre tableau de bord pour piloter vos ateliers et suivre vos clients.</p>
        </div>
        <div className="row">
          <button className="btn" type="button" onClick={loadDashboard}>Actualiser</button>
          <button className="btn" type="button" onClick={logout}>Se déconnecter</button>
        </div>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p className="form-success" role="status">{notice}</p>}

      <section className="dashboard-section">
        <div className="sec"><h2>Notifications</h2></div>
        {notifications.length === 0 ? (
          <p className="card mu">Aucune notification.</p>
        ) : (
          <div className="dashboard-list">
            {notifications.slice(0, 8).map((notification) => (
              <article className="card" key={notification.id}>
                <div className="row">
                  <b>{notification.event.replaceAll("_", " ")}</b>
                  {!notification.is_read && (
                    <button className="text-button" type="button" onClick={() => markNotificationRead(notification.id)}>
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
        <div className="sec"><h2>Calendrier des rendez-vous</h2></div>
        {appointments.length === 0 ? (
          <p className="card mu">Aucun rendez-vous proposé ou confirmé.</p>
        ) : (
          <div className="dashboard-list">
            {appointments.map((appointment) => (
              <article className="card" key={appointment.id}>
                <div className="row">
                  <b>{appointment.shop_name}</b>
                  <span className={`shop-badge status-${appointment.status}`}>{appointment.status}</span>
                </div>
                <p>{new Date(appointment.scheduled_at).toLocaleString("fr-FR")} · {appointment.duration_minutes} min</p>
                {appointment.note && <p>{appointment.note}</p>}
                {["proposed", "confirmed"].includes(appointment.status) && (
                  <button className="btn" type="button" onClick={() => updateAppointment(appointment.id)}>
                    Annuler / proposer un autre créneau
                  </button>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-stats" aria-label="Résumé de l’activité">
        <article className="card stat-card">
          <span className="stat-icon">🔧</span>
          <span className="stat-value">{shops.length}</span>
          <span className="mu">Atelier{shops.length !== 1 ? "s" : ""}</span>
        </article>
        <article className="card stat-card">
          <span className="stat-icon">📩</span>
          <span className="stat-value">{newQuoteCount}</span>
          <span className="mu">Nouvelle{newQuoteCount !== 1 ? "s" : ""} demande{newQuoteCount !== 1 ? "s" : ""}</span>
        </article>
        <article className="card stat-card">
          <span className="stat-icon">🛠️</span>
          <span className="stat-value">{acceptedQuoteCount}</span>
          <span className="mu">Réparation{acceptedQuoteCount !== 1 ? "s" : ""} en cours</span>
        </article>
        <article className="card stat-card">
          <span className="stat-icon">✅</span>
          <span className="stat-value">{completedQuoteCount}</span>
          <span className="mu">Intervention{completedQuoteCount !== 1 ? "s" : ""} terminée{completedQuoteCount !== 1 ? "s" : ""}</span>
        </article>
      </section>

      <section className="dashboard-section">
        <div className="sec">
          <h2>Mes ateliers</h2>
          {!busy && shops.length > 0 && (
            <button className="btn p" type="button" onClick={beginCreateShop}>+ Ajouter un atelier</button>
          )}
        </div>
        {busy ? <p className="mu">Chargement de votre espace…</p> : shops.length === 0 ? (
          <p className="card mu">Vous n’avez pas encore enregistré d’atelier. Ajoutez-en un ci-dessous pour apparaître dans l’annuaire.</p>
        ) : (
          <div className="cg">
            {shops.map((item) => (
              <article className="card mechanic-shop" key={item.id}>
                <div className="row">
                  <h3>{item.name}</h3>
                  <span className={item.is_verified ? "shop-badge verified" : "shop-badge"}>
                    {item.is_verified ? "Vérifié" : "En attente de vérification"}
                  </span>
                </div>
                <p className="mu">{item.district}, {item.city} · {item.phone}</p>
                <p>{item.description || "Aucune description renseignée."}</p>
                <p className="mu">{item.vehicle_types.map((id) => vehicles.find((vehicle) => vehicle.id === id)?.name).filter(Boolean).join(" · ") || "Aucun véhicule renseigné"}</p>
                <div className="shop-card-actions">
                  <button className="btn" type="button" onClick={() => beginEditShop(item)}>Modifier les informations</button>
                  <button className="btn" type="button" onClick={() => onPreviewShop(item.id)}>Voir la fiche publique</button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <div className="sec">
          <h2>Demandes de devis</h2>
          <div className="quote-filters" role="tablist" aria-label="Filtrer les demandes">
            {[
              ["all", "Toutes"],
              ["new", "À traiter"],
              ["discussion", "En discussion"],
              ["answered", "Répondues"],
              ["quote_sent", "Devis envoyés"],
              ["quote_accepted", "Devis acceptés"],
              ["appointment_confirmed", "Rendez-vous"],
              ["accepted", "Acceptées"],
              ["in_progress", "En cours"],
              ["completed", "Terminées"],
            ].map(([filter, label]) => (
              <button
                key={filter}
                className={`chip${quoteFilter === filter ? " on" : ""}`}
                type="button"
                role="tab"
                aria-selected={quoteFilter === filter}
                onClick={() => setQuoteFilter(filter)}
              >
                {label}
                {filter === "new" && newQuoteCount > 0 ? ` (${newQuoteCount})` : ""}
              </button>
            ))}
          </div>
        </div>
        {busy ? <p className="mu">Chargement des demandes…</p> : quotes.length === 0 ? (
          <p className="card mu">Aucune demande pour le moment. Les demandes de vos clients apparaîtront ici.</p>
        ) : visibleQuotes.length === 0 ? (
          <p className="card mu">Aucune demande dans cette catégorie.</p>
        ) : (
          <div className="dashboard-list">
            {visibleQuotes.map((quote) => (
              <article className="card quote-card" key={quote.id}>
                <div className="row">
                  <h3>{quote.shop_name}</h3>
                  <span className={`shop-badge status-${quote.status}`}>{STATUS_LABELS[quote.status] || quote.status}</span>
                </div>
                <p className="mu">Client : {quote.customer_name} · {quote.urgency === "immediate" ? "🚨 Urgent" : "Planifiée"} · {new Date(quote.created_at).toLocaleDateString("fr-FR")}</p>
                <p><b>{quote.vehicle_model}</b> · {CATEGORY_LABELS[quote.category] || quote.category} · {quote.problem}</p>
                {quote.location && <p>Localisation : {quote.location}</p>}
                <p className="mu">
                  {quote.service_mode === "on_site" ? "Intervention sur place" : "Intervention en atelier"}
                  {quote.availability ? ` · Disponibilités du client : ${quote.availability}` : ""}
                </p>
                {quote.attachments?.length > 0 && (
                  <div className="row">
                    {quote.attachments.map((attachment) => (
                      <PrivateImage
                        key={attachment.id}
                        className="shop-photo-preview"
                        src={attachment.image}
                        alt="Photo jointe par le client"
                      />
                    ))}
                  </div>
                )}
                {quote.mechanic_response && <p className="form-success">Votre réponse : {quote.mechanic_response}</p>}
                {quote.status === "new" && (
                  <div className="quote-reply">
                    <div className="row">
                      <button className="btn p" type="button" disabled={savingQuoteId === quote.id} onClick={() => acceptRequest(quote.id)}>
                        Accepter la demande
                      </button>
                      <button className="btn" type="button" disabled={savingQuoteId === quote.id} onClick={() => declineRequest(quote.id)}>
                        Refuser
                      </button>
                    </div>
                    <label htmlFor={`decline-${quote.id}`}>Motif facultatif en cas de refus</label>
                    <input id={`decline-${quote.id}`} maxLength="1000" value={declineReasons[quote.id] || ""} onChange={(event) => setDeclineReasons({ ...declineReasons, [quote.id]: event.target.value })} />
                    <label htmlFor={`answer-${quote.id}`}>Réponse rapide (parcours historique)</label>
                    <textarea id={`answer-${quote.id}`} rows="2" maxLength="3000" value={answers[quote.id] || ""} onChange={(event) => setAnswers({ ...answers, [quote.id]: event.target.value })} placeholder="Répondez au client." />
                    <button className="btn" type="button" disabled={savingQuoteId === quote.id || !answers[quote.id]?.trim()} onClick={() => replyToQuote(quote.id)}>
                      Envoyer une réponse
                    </button>
                  </div>
                )}
                {quote.refusal_reason && <p className="mu">Motif de refus saisi : {quote.refusal_reason}</p>}
                {quote.messages?.length > 0 && (
                  <details>
                    <summary>Échanges avec le client ({quote.messages.length})</summary>
                    {quote.messages.map((message) => (
                      <p key={message.id}>
                        <b>{message.author_name}</b> · {new Date(message.created_at).toLocaleString("fr-FR")}
                        <br />{message.message}
                      </p>
                    ))}
                  </details>
                )}
                {["discussion", "answered", "quote_sent"].includes(quote.status) && (
                  <div className="quote-reply">
                    <label htmlFor={`message-${quote.id}`}>Question ou réponse au client</label>
                    <textarea
                      id={`message-${quote.id}`}
                      rows="2"
                      maxLength="3000"
                      value={messages[quote.id] || ""}
                      onChange={(event) => setMessages({ ...messages, [quote.id]: event.target.value })}
                    />
                    <button className="btn" type="button" disabled={savingQuoteId === quote.id || !messages[quote.id]?.trim()} onClick={() => sendMessage(quote.id)}>
                      Envoyer le message
                    </button>
                  </div>
                )}
                {quote.offers?.length > 0 && (
                  <div className="mechanic-reply">
                    <b>Historique des devis estimatifs</b>
                    {quote.offers.map((offer) => (
                      <div className="quote-offer" key={offer.id}>
                        <h4>Version {offer.version} · {offer.is_supplemental ? "Devis complémentaire" : "Devis initial"} · {offer.status}</h4>
                        <p>{offer.description}</p>
                        {offer.parts.map((part) => <p key={part.id}>{part.quantity} × {part.name} — {Number(part.unit_price).toLocaleString("fr-FR")} FCFA</p>)}
                        <p>Main-d’œuvre : {Number(offer.labor_cost).toLocaleString("fr-FR")} FCFA</p>
                        <p>Déplacement : {Number(offer.travel_cost).toLocaleString("fr-FR")} FCFA</p>
                        <p><b>Total estimatif : {Number(offer.total).toLocaleString("fr-FR")} FCFA (XOF)</b></p>
                        <p>Durée : {offer.estimated_duration_minutes} min · Valide jusqu’au {new Date(`${offer.valid_until}T00:00:00`).toLocaleDateString("fr-FR")}</p>
                        {offer.conditions && <p>Conditions : {offer.conditions}</p>}
                      </div>
                    ))}
                  </div>
                )}
                {["discussion", "answered", "accepted", "quote_accepted", "appointment_confirmed", "in_progress"].includes(quote.status) && (
                  <details className="quote-reply">
                    <summary>
                      {["accepted", "quote_accepted", "appointment_confirmed", "in_progress"].includes(quote.status)
                        ? "Envoyer un devis complémentaire (l’intervention sera suspendue jusqu’à l’accord du client)"
                        : "Créer ou modifier un devis (une nouvelle version sera historisée)"}
                    </summary>
                    {(() => {
                      const form = offerForms[quote.id] || {
                        description: "",
                        labor_cost: "",
                        travel_cost: "0",
                        estimated_duration_minutes: "60",
                        valid_days: "7",
                        conditions: "",
                        parts: [{ name: "", quantity: "1", unit_price: "" }],
                      };
                      return (
                        <>
                          <label htmlFor={`offer-description-${quote.id}`}>Description de l’intervention</label>
                          <textarea id={`offer-description-${quote.id}`} rows="3" value={form.description} onChange={(event) => updateOffer(quote.id, "description", event.target.value)} />
                          <div className="form-grid">
                            <div>
                              <label htmlFor={`labor-${quote.id}`}>Main-d’œuvre (FCFA)</label>
                              <input id={`labor-${quote.id}`} type="number" min="0" step="1" value={form.labor_cost} onChange={(event) => updateOffer(quote.id, "labor_cost", event.target.value)} />
                            </div>
                            <div>
                              <label htmlFor={`travel-${quote.id}`}>Déplacement (FCFA)</label>
                              <input id={`travel-${quote.id}`} type="number" min="0" step="1" value={form.travel_cost} onChange={(event) => updateOffer(quote.id, "travel_cost", event.target.value)} />
                            </div>
                            <div>
                              <label htmlFor={`duration-${quote.id}`}>Durée estimée (minutes)</label>
                              <input id={`duration-${quote.id}`} type="number" min="1" value={form.estimated_duration_minutes} onChange={(event) => updateOffer(quote.id, "estimated_duration_minutes", event.target.value)} />
                            </div>
                            <div>
                              <label htmlFor={`valid-${quote.id}`}>Validité (jours)</label>
                              <input id={`valid-${quote.id}`} type="number" min="1" max="365" value={form.valid_days} onChange={(event) => updateOffer(quote.id, "valid_days", event.target.value)} />
                            </div>
                          </div>
                          <label>Pièces et fournitures</label>
                          {form.parts.map((part, index) => (
                            <div className="form-grid" key={index}>
                              <input aria-label="Nom de la pièce" value={part.name} placeholder="Nom de la pièce" onChange={(event) => updateOfferPart(quote.id, index, "name", event.target.value)} />
                              <input aria-label="Quantité" type="number" min="1" value={part.quantity} onChange={(event) => updateOfferPart(quote.id, index, "quantity", event.target.value)} />
                              <input aria-label="Prix unitaire FCFA" type="number" min="0" step="1" value={part.unit_price} placeholder="Prix unitaire FCFA" onChange={(event) => updateOfferPart(quote.id, index, "unit_price", event.target.value)} />
                            </div>
                          ))}
                          <button className="btn" type="button" onClick={() => updateOffer(quote.id, "parts", [...form.parts, { name: "", quantity: "1", unit_price: "" }])}>
                            Ajouter une pièce
                          </button>
                          <label htmlFor={`conditions-${quote.id}`}>Conditions éventuelles</label>
                          <textarea id={`conditions-${quote.id}`} rows="2" value={form.conditions} onChange={(event) => updateOffer(quote.id, "conditions", event.target.value)} />
                          <p className="mu">Le montant total est calculé par le serveur. Il s’agit d’une estimation, pas d’une facture. Aucun supplément ne sera engagé sans accord du client.</p>
                          <button className="btn p" type="button" disabled={savingQuoteId === quote.id || !form.description.trim() || form.labor_cost === ""} onClick={() => createOffer(quote.id)}>
                            {["accepted", "quote_accepted", "appointment_confirmed", "in_progress"].includes(quote.status)
                              ? "Envoyer le devis complémentaire"
                              : "Envoyer le devis estimatif"}
                          </button>
                        </>
                      );
                    })()}
                  </details>
                )}
                {quote.status === "quote_accepted" && (
                  <div className="quote-reply">
                    <label htmlFor={`appointment-${quote.id}`}>Proposer une date et une heure</label>
                    <input
                      id={`appointment-${quote.id}`}
                      type="datetime-local"
                      min={new Date(Date.now() + 60000).toISOString().slice(0, 16)}
                      value={appointmentInputs[quote.id] || ""}
                      onChange={(event) => setAppointmentInputs({ ...appointmentInputs, [quote.id]: event.target.value })}
                    />
                    <button className="btn p" type="button" disabled={savingQuoteId === quote.id || !appointmentInputs[quote.id]} onClick={() => proposeAppointment(quote.id)}>
                      Proposer le rendez-vous
                    </button>
                  </div>
                )}
                {quote.appointments?.map((appointment) => (
                  <p className="mechanic-reply" key={appointment.id}>
                    Rendez-vous {appointment.status} : {new Date(appointment.scheduled_at).toLocaleString("fr-FR")} · {appointment.duration_minutes} min
                  </p>
                ))}
                {quote.status === "accepted" && (
                  <div className="row quote-status-actions">
                    <button className="btn p" type="button" disabled={savingQuoteId === quote.id} onClick={() => startQuote(quote.id)}>
                      Commencer la réparation
                    </button>
                    <button className="btn" type="button" disabled={savingQuoteId === quote.id} onClick={() => completeQuote(quote.id)}>
                      Marquer comme terminée
                    </button>
                  </div>
                )}
                {quote.status === "appointment_confirmed" && (
                  <button className="btn p" type="button" disabled={savingQuoteId === quote.id} onClick={() => startQuote(quote.id)}>
                    Commencer l’intervention
                  </button>
                )}
                {quote.status === "in_progress" && (
                  <button className="btn p" type="button" disabled={savingQuoteId === quote.id} onClick={() => completeQuote(quote.id)}>
                    {savingQuoteId === quote.id ? "Mise à jour…" : "Signaler le travail terminé"}
                  </button>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      {(showShopForm || shops.length === 0) && (
      <section className="dashboard-section" id="shop-form">
        <div className="sec">
          <h2>{editingShopId ? "Modifier mon atelier" : "Ajouter un atelier"}</h2>
          {shops.length > 0 && <button className="btn" type="button" onClick={closeShopForm}>Annuler</button>}
        </div>
        <form className="card shop-form" onSubmit={saveShop}>
          <label htmlFor="shop-name">Nom de l’atelier</label>
          <input id="shop-name" name="name" required maxLength="160" value={shop.name} onChange={updateShop} />
          <label htmlFor="shop-type">Type d’activité</label>
          <select id="shop-type" name="business_type" value={shop.business_type} onChange={updateShop}>
            <option value="garage">Garage</option>
            <option value="mechanic">Mécanicien</option>
          </select>
          <div className="form-grid">
            <div>
              <label htmlFor="shop-city">Ville</label>
              <input id="shop-city" name="city" required value={shop.city} onChange={updateShop} />
            </div>
            <div>
              <label htmlFor="shop-district">Quartier</label>
              <input id="shop-district" name="district" required value={shop.district} onChange={updateShop} />
            </div>
            <div>
              <label htmlFor="shop-phone">Téléphone</label>
              <input id="shop-phone" name="phone" type="tel" required value={shop.phone} onChange={updateShop} />
            </div>
            <div>
              <label htmlFor="shop-whatsapp">WhatsApp (facultatif)</label>
              <input id="shop-whatsapp" name="whatsapp" type="tel" value={shop.whatsapp} onChange={updateShop} />
            </div>
          </div>
          <label htmlFor="shop-address">Adresse (facultative)</label>
          <input id="shop-address" name="address" value={shop.address} onChange={updateShop} />
          <label htmlFor="shop-photo">Photo principale de l’atelier (facultative)</label>
          <input
            id="shop-photo"
            name="photo"
            type="file"
            accept="image/*"
            onChange={(event) => setPhotoFile(event.target.files?.[0] || null)}
            aria-describedby="shop-photo-help"
          />
          <p id="shop-photo-help" className="mu sm">
            Image JPG, PNG ou WebP, 5 Mo maximum.
          </p>
          {photoFile && (
            <p className="sm form-success" role="status">
              Photo sélectionnée : {photoFile.name}
            </p>
          )}
          {!photoFile && editingShopId && shops.find((item) => item.id === editingShopId)?.photo && (
            <img
              className="shop-photo-preview"
              src={shops.find((item) => item.id === editingShopId).photo}
              alt="Photo actuelle de l’atelier"
            />
          )}
          <fieldset>
            <legend>Position sur la carte (facultative)</legend>
            <p className="mu sm">
              Dans Google Maps, faites un clic droit sur votre emplacement, cliquez sur les coordonnées pour les copier, puis collez-les ici.
            </p>
            <label htmlFor="shop-location">Coordonnées ou lien Google Maps</label>
            <input
              id="shop-location"
              name="map_location"
              type="text"
              autoComplete="off"
              placeholder="Ex. 9.337, 2.630 ou collez le lien Google Maps"
              value={locationInput}
              onChange={updateMapLocation}
              aria-describedby="shop-location-help shop-location-status"
            />
            <p id="shop-location-help" className="mu sm">
              Les coordonnées GPS ou un lien complet Google Maps avec la position sont acceptés.
            </p>
            {locationMessage && (
              <p
                id="shop-location-status"
                className={`sm ${shop.latitude === "" ? "form-error" : "form-success"}`}
                role="status"
              >
                {locationMessage}
              </p>
            )}
          </fieldset>
          <fieldset>
            <legend>Horaires d’ouverture (facultatifs)</legend>
            <div className="opening-hours-editor">
              {WEEK_DAYS.map(([day, label]) => {
                const hours = shop.opening_hours[day];
                const status = !Object.hasOwn(shop.opening_hours, day)
                  ? "unknown"
                  : hours === null
                    ? "closed"
                    : "open";
                return (
                  <div className="opening-hours-row" key={day}>
                    <label htmlFor={`hours-${day}-status`}>{label}</label>
                    <select
                      id={`hours-${day}-status`}
                      value={status}
                      onChange={(event) => updateOpeningHours(day, event.target.value)}
                    >
                      <option value="unknown">Non renseigné</option>
                      <option value="open">Ouvert</option>
                      <option value="closed">Fermé</option>
                    </select>
                    {status === "open" ? (
                      <div className="opening-time-fields">
                        <label className="sr-only" htmlFor={`hours-${day}-open`}>Ouverture {label}</label>
                        <input
                          id={`hours-${day}-open`}
                          type="time"
                          value={hours?.open || ""}
                          onChange={(event) => updateOpeningHours(day, { field: "open", value: event.target.value })}
                          aria-label={`Heure d’ouverture ${label}`}
                        />
                        <span className="mu">à</span>
                        <label className="sr-only" htmlFor={`hours-${day}-close`}>Fermeture {label}</label>
                        <input
                          id={`hours-${day}-close`}
                          type="time"
                          value={hours?.close || ""}
                          onChange={(event) => updateOpeningHours(day, { field: "close", value: event.target.value })}
                          aria-label={`Heure de fermeture ${label}`}
                        />
                      </div>
                    ) : <span aria-hidden="true" />}
                  </div>
                );
              })}
            </div>
          </fieldset>
          <label htmlFor="shop-description">Description (facultative)</label>
          <textarea id="shop-description" name="description" rows="3" maxLength="3000" value={shop.description} onChange={updateShop} />
          <fieldset>
            <legend>Véhicules pris en charge</legend>
            <div className="choice-list">
              {vehicles.map((item) => (
                <label key={item.id}>
                  <input type="checkbox" checked={shop.vehicle_types.includes(item.id)} onChange={() => updateSelection("vehicle_types", item.id)} />
                  {item.name}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>Services proposés</legend>
            <div className="choice-list">
              {services.map((item) => (
                <label key={item.id}>
                  <input type="checkbox" checked={shop.services.includes(item.id)} onChange={() => updateSelection("services", item.id)} />
                  {item.name}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="check-label">
            <input name="mobile_service" type="checkbox" checked={shop.mobile_service} onChange={updateShop} />
            Je propose le dépannage à domicile
          </label>
          <div className="row shop-form-actions">
            <button className="btn p" type="submit" disabled={savingShop || busy}>
              {savingShop ? "Enregistrement…" : editingShopId ? "Enregistrer les modifications" : "Créer mon atelier"}
            </button>
            {shops.length > 0 && <button className="btn" type="button" onClick={closeShopForm}>Annuler</button>}
          </div>
        </form>
      </section>
      )}
    </main>
  );
}
