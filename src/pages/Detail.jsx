import { useEffect, useState } from "react";
import { api, apiList } from "../api";
import { Stars } from "../components/Common";
import { SE, vis, tone } from "../data";

const formatReviewDate = (value) =>
  new Date(value).toLocaleDateString("fr-FR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

const WEEK_DAYS = [
  ["monday", "Lundi"],
  ["tuesday", "Mardi"],
  ["wednesday", "Mercredi"],
  ["thursday", "Jeudi"],
  ["friday", "Vendredi"],
  ["saturday", "Samedi"],
  ["sunday", "Dimanche"],
];

const getCurrentAvailability = (openingHours = {}) => {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Africa/Porto-Novo",
    weekday: "long",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  const day = values.weekday.toLowerCase();
  const hours = openingHours[day];
  if (!Object.hasOwn(openingHours, day)) {
    return { label: "Horaires à confirmer", open: null };
  }
  if (hours === null) return { label: "Fermé aujourd’hui", open: false };
  if (!hours?.open || !hours?.close) {
    return { label: "Horaires à confirmer", open: null };
  }

  const currentTime = `${values.hour}:${values.minute}`;
  if (currentTime >= hours.open && currentTime < hours.close) {
    return { label: `Ouvert · ferme à ${hours.close}`, open: true };
  }
  return { label: `Fermé · ${hours.open}–${hours.close}`, open: false };
};

export default function Detail({ r, session }) {
  const phone = r.phone?.replace(/[^\d+]/g, "");
  const whatsapp = r.whatsapp?.replace(/\D/g, "");
  const [reviews, setReviews] = useState([]);
  const [reviewsLoading, setReviewsLoading] = useState(true);
  const [reviewsError, setReviewsError] = useState("");
  const [hasCompletedQuote, setHasCompletedQuote] = useState(false);
  const [reviewsLoaded, setReviewsLoaded] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [savingReview, setSavingReview] = useState(false);
  const [reviewNotice, setReviewNotice] = useState("");

  const isCustomer = session?.user?.role === "customer";
  const myReview = reviews.find((review) => review.is_mine);
  const availability = getCurrentAvailability(r.openingHours);

  useEffect(() => {
    let active = true;
    setReviews([]);
    setReviewsLoaded(false);
    setHasCompletedQuote(false);
    setReviewsLoading(true);
    setReviewsError("");
    setReviewNotice("");

    const shopId = r.apiId ?? r.id;
    const loadReviews = isCustomer
      ? apiList("/reviews/")
      : apiList(`/shops/${shopId}/reviews/`);
    const requests = [loadReviews];
    if (isCustomer) {
      requests.push(apiList("/quotes/"));
    }

    Promise.all(requests)
      .then(([reviewList, quotes = []]) => {
        if (!active) return;
        setReviews(reviewList.filter((review) => review.shop === shopId));
        setHasCompletedQuote(
          quotes.some(
            (quote) =>
              quote.shop === shopId && quote.status === "completed"
          )
        );
        setReviewsLoaded(true);
      })
      .catch((error) => {
        if (active) setReviewsError(error.message);
      })
      .finally(() => {
        if (active) setReviewsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [r.apiId, r.id, isCustomer, session?.access]);

  const submitReview = async (event) => {
    event.preventDefault();
    if (!rating) {
      setReviewsError("Choisissez une note de 1 à 5 étoiles.");
      return;
    }

    setSavingReview(true);
    setReviewsError("");
    setReviewNotice("");
    try {
      const savedReview = await api("/reviews/", {
        method: "POST",
        body: JSON.stringify({
          shop: r.apiId ?? r.id,
          rating,
          comment: comment.trim(),
        }),
      });
      setReviews((current) => [savedReview, ...current]);
      setReviewNotice(
        "Votre avis a été envoyé. Il sera visible après validation."
      );
      setComment("");
    } catch (error) {
      setReviewsError(error.message);
    } finally {
      setSavingReview(false);
    }
  };

  return (
    <div>
      <a className="mu back" href="#resultats">← Retour aux résultats</a>
      <div className={`ph ${tone(r)}${r.photo ? " has-photo" : ""}`} style={{ marginTop: 12 }}>
        {r.photo ? (
          <img src={r.photo} alt={`Atelier ${r.n}`} />
        ) : (
          <><div>{vis(r)}</div><div>🛞</div><div>🔧</div><div>⚙️</div></>
        )}
      </div>
      {r.gallery?.length > 0 && (
        <div className="shop-public-gallery" aria-label="Photos de l’atelier">
          {r.gallery.map((image, index) => (
            <img key={`${image}-${index}`} src={image} alt={`Photo ${index + 1} de ${r.n}`} />
          ))}
        </div>
      )}
      <div className="sp">
        <div>
          <div className="card">
            <div className="row">
              {r.ownerPhoto ? (
                <img
                  className="profile-avatar"
                  src={r.ownerPhoto}
                  alt={`Profil de ${r.ownerName || r.n}`}
                />
              ) : (
                <div className={"av " + tone(r)}>{vis(r)}</div>
              )}
              <div>
                <h1 style={{ fontSize: 26 }}>{r.n}</h1>
                {r.ownerName && <div className="mu">{r.ownerName}</div>}
                <div className="mu">{r.t} · {r.q}, {r.city}</div>
                {r.isVerified && (
                  <span className="verification-badge">✓ Professionnel vérifié</span>
                )}
                <span className={`shop-availability${availability.open === true ? " is-open" : availability.open === false ? " is-closed" : ""}`}>
                  {availability.label}
                </span>
              </div>
            </div>
            <p>{r.desc}</p>
            {r.yearsExperience != null && (
              <p className="mu">
                {r.yearsExperience} {r.yearsExperience === 1 ? "an" : "ans"} d’expérience
              </p>
            )}
            <Stars r={r} />
            <h3 style={{ margin: "16px 0 8px" }}>Spécialités</h3>
            {r.sp.map((x) => (
              <span className="tag" key={x}>{SE[x]} {x}</span>
            ))}
            <h3 style={{ margin: "12px 0 8px" }}>Véhicules pris en charge</h3>
            {r.v.map((x) => (
              <span className="tag" key={x}>{x}</span>
            ))}
            {r.dom ? <span className="tag r">Dépannage à domicile</span> : null}
          </div>
          <section className="card shop-hours">
            <h2>Horaires d’ouverture</h2>
            <ul>
              {WEEK_DAYS.map(([day, label]) => {
                const hours = r.openingHours?.[day];
                const schedule = !Object.hasOwn(r.openingHours || {}, day)
                  ? "Non renseigné"
                  : hours === null
                    ? "Fermé"
                    : hours?.open && hours?.close
                      ? `${hours.open} – ${hours.close}`
                      : "À confirmer";
                return <li key={day}><span>{label}</span><span>{schedule}</span></li>;
              })}
            </ul>
          </section>
          <section className="card review-section" aria-labelledby="reviews-title">
            <div className="sec">
              <h2 id="reviews-title">Avis des clients</h2>
              <span className="mu sm">
                {r.a ? `${r.a} avis` : "Aucun avis publié"}
              </span>
            </div>

            {reviewsLoading ? (
              <p className="mu">Chargement des avis…</p>
            ) : reviewsError && !reviewsLoaded ? (
              <p className="form-error" role="alert">
                Impossible de charger les avis : {reviewsError}
              </p>
            ) : (
              <>
                {reviews
                  .filter((review) => review.is_mine || review.comment || review.rating)
                  .map((review) => (
                    <article className="review-item" key={review.id}>
                      <div className="row">
                        <b>{review.is_mine ? "Votre avis" : review.customer_name || "Client"}</b>
                        <span className="star" aria-label={`${review.rating} sur 5 étoiles`}>
                          {"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}
                          <span className="review-rating-number">{review.rating}/5</span>
                        </span>
                      </div>
                      {review.comment && <p>{review.comment}</p>}
                      {review.is_mine && !review.is_approved && (
                        <p className="mu sm">En attente de validation par un administrateur.</p>
                      )}
                      <time className="mu sm" dateTime={review.created_at}>
                        {formatReviewDate(review.created_at)}
                      </time>
                    </article>
                  ))}
                {reviews.filter((review) => !review.is_mine).length === 0 && (
                  <p className="mu">Aucun avis publié pour le moment.</p>
                )}
              </>
            )}

            {isCustomer && !reviewsLoading && (
              myReview ? (
                <p className="review-guidance mu">
                  Vous avez déjà envoyé un avis pour cet atelier.
                </p>
              ) : hasCompletedQuote ? (
                <form className="review-form" onSubmit={submitReview}>
                  <h3>Laissez votre avis</h3>
                  <fieldset className="rating-fieldset">
                    <legend>Votre note</legend>
                    <div className="rating-picker" role="group" aria-label="Choisir une note sur cinq">
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button
                          key={value}
                          className="rating-star"
                          type="button"
                          aria-label={`${value} étoile${value > 1 ? "s" : ""}`}
                          aria-pressed={rating === value}
                          onClick={() => setRating(value)}
                        >
                          {value <= rating ? "★" : "☆"}
                        </button>
                      ))}
                      <span className="mu sm">
                        {rating ? `${rating}/5` : "Sélectionnez une note"}
                      </span>
                    </div>
                  </fieldset>
                  <label htmlFor="review-comment">Votre commentaire (facultatif)</label>
                  <textarea
                    id="review-comment"
                    rows="4"
                    maxLength="1500"
                    placeholder="Partagez votre expérience avec cet atelier…"
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                  />
                  <button className="btn p" type="submit" disabled={savingReview}>
                    {savingReview ? "Envoi…" : "Envoyer mon avis"}
                  </button>
                </form>
              ) : (
                <p className="review-guidance mu">
                  Vous pourrez noter cet atelier après la fin d’une réparation demandée sur MécanoConnect.
                </p>
              )
            )}
            {!session?.access && !reviewsLoading && (
              <p className="review-guidance mu">
                <a href="#connexion">Connectez-vous comme client</a> pour laisser un avis après une réparation terminée.
              </p>
            )}
            {reviewsError && reviewsLoaded && (
              <p className="form-error" role="alert">{reviewsError}</p>
            )}
            {reviewNotice && <p className="form-success" role="status">{reviewNotice}</p>}
          </section>
        </div>
        <div className="card">
          <h3>Contacter {r.n}</h3>
          <div className="acts">
            <a className="btn p" href="#devis">Demander un devis</a>
            {phone && <a className="btn" href={`tel:${phone}`}>Appeler {r.phone}</a>}
            {whatsapp && <a className="btn" href={`https://wa.me/${whatsapp}`} target="_blank" rel="noreferrer">Écrire sur WhatsApp</a>}
          </div>
          {r.address && <p className="mu" style={{ fontSize: 13 }}>{r.address}</p>}
        </div>
      </div>
    </div>
  );
}
