import { Stars } from "../components/Common";
import { SE, vis, tone } from "../data";

export default function Detail({ r }) {
  const phone = r.phone?.replace(/[^\d+]/g, "");
  const whatsapp = r.whatsapp?.replace(/\D/g, "");

  return (
    <div>
      <a className="mu back" href="#resultats">← Retour aux résultats</a>
      <div className={"ph " + tone(r)} style={{ marginTop: 12 }}>
        <div>{vis(r)}</div><div>🛞</div><div>🔧</div><div>⚙️</div>
      </div>
      <div className="sp">
        <div>
          <div className="card">
            <div className="row">
              <div className={"av " + tone(r)}>{vis(r)}</div>
              <div>
                <h1 style={{ fontSize: 26 }}>{r.n}</h1>
                <div className="mu">{r.t} · {r.q}, {r.city} · {r.h}</div>
              </div>
            </div>
            <p>{r.desc}</p>
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
