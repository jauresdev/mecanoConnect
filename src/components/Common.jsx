import { go } from "../router";

const Ic = ({ children, size = 18, ...p }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    {children}
  </svg>
);
export const IcSearch = (p) => <Ic {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Ic>;
export const IcPin = (p) => <Ic {...p}><path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></Ic>;
export const IcHeart = (p) => <Ic {...p}><path d="M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.4 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z" /></Ic>;
export const IcChat = (p) => <Ic {...p}><path d="M21 12a8 8 0 0 1-11.7 7L4 20l1.2-4.6A8 8 0 1 1 21 12z" /></Ic>;
export const IcPlus = (p) => <Ic {...p}><path d="M12 5v14M5 12h14" /></Ic>;
export const IcArrow = (p) => <Ic {...p}><path d="M5 12h14M13 6l6 6-6 6" /></Ic>;
export const IcCheck = (p) => <Ic {...p}><path d="M20 6 9 17l-5-5" /></Ic>;
const IcWrench = (p) => (
  <Ic {...p} strokeWidth="2.4">
    <path d="M14.7 6.3a4 4 0 0 0 5 5l-9.4 9.4a2.1 2.1 0 0 1-3-3l9.4-9.4z" />
    <path d="M14.7 6.3a4 4 0 0 1 5-1.6l-2.6 2.6 1.1 1.1 2.6-2.6a4 4 0 0 1-5 5" />
  </Ic>
);

const jump = (id) => (e) => {
  e.preventDefault();
  const el = () => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  if ((window.location.hash.slice(1) || "accueil") === "accueil") el();
  else {
    go("accueil");
    setTimeout(el, 80);
  }
};

export const Head = ({ user, onLogout }) => (
  <header>
    <a href="#accueil" className="logo" aria-label="MécanoConnect, accueil">
      <span className="logo-i"><IcWrench size={22} /></span>
      <span className="logo-t">mécano<b>connect</b></span>
    </a>
    <nav className="links" aria-label="Navigation principale">
      <a href="#resultats">Réparateurs</a>
      <a href="#accueil" onClick={jump("services")}>Services</a>
      <a href="#accueil" onClick={jump("comment")}>Comment ça marche</a>
    </nav>
    <div className="hr">
      <a className="ibtn" href="#resultats" aria-label="Favoris"><IcHeart /></a>
      {user ? (
        <>
          {user.role === "mechanic" && <a className="btn" href="#mecanicien">Mon espace</a>}
          {user.role === "customer" && <a className="btn" href="#client">Mes demandes</a>}
          <button className="login logout-link" type="button" onClick={onLogout}>Déconnexion</button>
        </>
      ) : (
        <>
          <a className="login" href="#connexion">Se connecter</a>
          <a className="btn p" href="#inscription"><IcPlus size={16} /> <span>Mécanicien</span></a>
        </>
      )}
    </div>
  </header>
);

export const Stars = ({ r }) => (
  r.s == null || !r.a ? (
    <span className="mu">Pas encore d’avis</span>
  ) : (
    <span className="star" aria-label={`Note ${r.s} sur 5, ${r.a} avis`}>
      ★ {Number(r.s).toLocaleString("fr-FR", { maximumFractionDigits: 1 })}{" "}
      <span className="mu">({r.a})</span>
    </span>
  )
);

export const Pins = ({ L, sel, pick }) => (
  <div className="map" role="group" aria-label="Carte des réparateurs">
    <span className="road r1"></span>
    <span className="road r2"></span>
    <span className="you" title="Vous êtes ici"></span>
    {L.map((r) => (
      <button
        key={r.id}
        className={"pin" + (r.id === sel ? " on" : "")}
        style={{ left: r.x + "%", top: r.y + "%" }}
        aria-label={r.n}
        onClick={() => pick(r.id)}
      ></button>
    ))}
  </div>
);

export const Seg = ({ q, setQ }) => (
  <div className="seg">
    {[["Moto", "🏍️"], ["Voiture", "🚗"]].map(([t, e]) => (
      <button type="button" key={t} className={q.type === t ? "on" : ""} onClick={() => setQ({ ...q, type: t })}>
        <span aria-hidden="true">{e}</span> {t}
      </button>
    ))}
  </div>
);
