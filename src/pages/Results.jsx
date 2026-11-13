import { useState } from "react";
import { SE, vis, tone } from "../data";
import { Pins, Seg, Stars } from "../components/Common";

export default function Results({ q, setQ, sel, pick, shops, loading, error, services }) {
  const [f, setF] = useState("Tous");
  const L = shops.filter(
    (r) =>
      r.v.includes(q.type) &&
      (f === "Domicile" ? r.dom : true) &&
      (!q.service || r.sp.includes(q.service)) &&
      (!q.lieu || `${r.q} ${r.city}`.toLowerCase().includes(q.lieu.toLowerCase()))
  );

  return (
    <div>
      <h2 className="ptitle">{L.length} atelier{L.length > 1 ? "s" : ""} à {q.lieu || "Parakou"}</h2>
      <div style={{ margin: "12px 0" }}>
        <Seg q={q} setQ={setQ} />
      </div>
      <div className="chips">
        {[["Tous", "Tous"], ["Domicile", "Dépannage à domicile"]].map(([k, l]) => (
          <button key={k} className={"chip" + (f === k ? " on" : "")} onClick={() => setF(k)}>{l}</button>
        ))}
        <select aria-label="Service" style={{ width: "auto" }} value={q.service} onChange={(e) => setQ({ ...q, service: e.target.value })}>
          <option value="">Tous les services</option>
          {services.map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </div>
      <div className="rs">
        <div>
          {error ? (
            <div className="card form-error" role="alert">Impossible de charger les ateliers : {error}</div>
          ) : loading ? (
            <div className="card mu">Chargement des ateliers…</div>
          ) : L.length === 0 ? (
            <div className="card">
              <b>Aucun atelier pour ces critères</b>
              <p className="mu">Essayez un autre quartier ou retirez un filtre. Les nouveaux ateliers apparaissent ici après leur inscription.</p>
            </div>
          ) : (
            L.map((r) => (
              <div key={r.id} className={"card it" + (r.id === sel ? " on" : "")} onClick={() => pick(r.id, true)}>
                <div className={"av " + tone(r)}>{vis(r)}</div>
                <div style={{ flex: 1 }}>
                  <div className="row">
                    <b>{r.n}</b>
                    <Stars r={r} />
                  </div>
                  <div className="mu sm">{r.t} · {r.q}, {r.city} · {r.h}</div>
                  <div style={{ marginTop: 8 }}>
                    {r.sp.slice(0, 3).map((x) => (
                      <span className="tag" key={x}>{SE[x]} {x}</span>
                    ))}
                    {r.dom ? <span className="tag r">À domicile</span> : null}
                  </div>
                  <a
                    className="btn p"
                    style={{ marginTop: 6 }}
                    href="#fiche"
                    onClick={(e) => {
                      e.stopPropagation();
                      pick(r.id);
                    }}
                  >
                    Voir la fiche
                  </a>
                </div>
              </div>
            ))
          )}
        </div>
        <Pins L={L} sel={sel} pick={(id) => pick(id, true)} />
      </div>
    </div>
  );
}
