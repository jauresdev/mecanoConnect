import { UNIVERSES, WORDS, SE, vis, tone } from "../data";
import { Seg, IcSearch, IcPin, IcArrow, IcCheck, Stars } from "../components/Common";
import { go } from "../router";

export default function Home({ q, setQ, pick, shops, services, loading, error }) {
  const visibleShops = shops.filter((shop) => shop.v.includes(q.type));
  const search = (e) => {
    e.preventDefault();
    go("resultats");
  };
  const chip = (s) => {
    setQ({ ...q, service: s });
    go("resultats");
  };
  const chooseUniverse = (universe) => (event) => {
    event.preventDefault();
    setQ({ ...q, type: universe.type, service: "" });
    go("resultats");
  };

  return (
    <div>
      <section className="universe-chooser" id="univers">
        <div className="universe-heading">
          <p className="eyebrow">UNE PLATEFORME, DEUX UNIVERS</p>
          <h2>Choisissez votre univers</h2>
          <p className="mu">Trouvez le spécialiste correspondant à votre véhicule.</p>
        </div>
        <div className="universe-grid">
          {[UNIVERSES.auto, UNIVERSES.moto].map((universe) => (
            <a
              key={universe.key}
              className={`universe-card ${universe.key}`}
              href="#resultats"
              onClick={chooseUniverse(universe)}
            >
              <span className="universe-icon" aria-hidden="true">{universe.icon}</span>
              <span className="universe-copy">
                <b>{universe.name}</b>
                <span>{universe.description}</span>
                <strong>Explorer l’univers <span aria-hidden="true">→</span></strong>
              </span>
            </a>
          ))}
        </div>
      </section>

      <section className="hero">
        <div className="hero-l">
          <h1>
            Ça tombe en panne.<br />
            Ça se répare.<br />
            <span className="y">Près de chez vous !</span>
          </h1>
          <p className="lead">Mécaniciens et garages pour motos et voitures à Parakou. Comparez, appelez, demandez un devis.</p>
          <div className="mt16"><Seg q={q} setQ={setQ} /></div>
          <form className="sb" onSubmit={search} role="search">
            <IcSearch className="mu" />
            <input
              aria-label="Quartier"
              placeholder="Quartier, par exemple Banikanni"
              value={q.lieu}
              onChange={(e) => setQ({ ...q, lieu: e.target.value })}
            />
            <span className="loc"><IcPin size={15} /> Parakou</span>
            <button className="btn p">Chercher <IcArrow size={16} /></button>
          </form>
        </div>
        <div className="stage" aria-hidden="true">
          <span className="glow"></span>
          <span className="em e1">🛞</span>
          <span className="em e2">🔋</span>
          <span className="em e3">🏍️</span>
          <span className="em e4">🚗</span>
          <span className="em e5">🔧</span>
          <span className="em e6">⚙️</span>
        </div>
      </section>

      <div className="chips" id="services">
        {services.map((service) => (
          <button key={service.id} className={"chip" + (q.service === service.name ? " on" : "")} onClick={() => chip(service.name)}>
            <span aria-hidden="true">{SE[service.name] || "🔧"}</span> {service.name}
          </button>
        ))}
        <button className="chip" onClick={() => chip("")}>Tous</button>
      </div>

      <div className="sec">
        <h2>Professionnels {q.type === "Voiture" ? "auto" : "moto"} près de vous</h2>
        <a className="more" href="#resultats">Voir tout <IcArrow size={14} /></a>
      </div>
      {error && <p className="form-error" role="alert">Impossible de charger les ateliers : {error}</p>}
      {loading ? (
        <p className="card mu">Chargement des ateliers…</p>
      ) : visibleShops.length === 0 ? (
        <div className="card mu">
          Aucun atelier n’est encore publié dans votre ville. Revenez bientôt pour découvrir les réparateurs inscrits.
        </div>
      ) : (
      <div className="cg">
        {visibleShops.slice(0, 4).map((r) => (
          <a key={r.id} href="#fiche" className={"pc " + tone(r)} onClick={(e) => { e.preventDefault(); pick(r.id); }}>
            <div className="vis">
              {r.isVerified && <span className="vb"><IcCheck size={12} /> Professionnel vérifié</span>}
              <span className="em-l">{vis(r)}</span>
            </div>
            <div className="inf">
              <b>{r.n}</b>
              <span className="mu"><IcPin size={13} /> {r.q} · {r.city}</span>
              <span className="mu"><Stars r={r} /></span>
            </div>
          </a>
        ))}
      </div>
      )}

      <div className="sec" id="comment">
        <h2>Comment ça marche</h2>
      </div>
      <div className="g3">
        {WORDS.map(([a, b], i) => (
          <div className="card step" key={a}>
            <span className="num">{i + 1}</span>
            <b>{a}</b>
            <p className="mu">{b}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
