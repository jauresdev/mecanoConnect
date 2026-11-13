import { useState } from "react";
import { api } from "../api";
import { go } from "../router";

export default function Quote({ r, q, user }) {
  const [st, setSt] = useState(1);
  const [d, setD] = useState({ veh: "", pb: "", urg: "planned" });
  const [ok, setOk] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const vehicleType = r.vehicleTypes?.find((item) => item.name === q.type);

  const submit = async () => {
    setError("");
    setBusy(true);
    try {
      await api("/quotes/", {
        method: "POST",
        body: JSON.stringify({
          shop: r.apiId,
          vehicle_type: vehicleType?.id,
          vehicle_model: d.veh.trim(),
          problem: d.pb.trim(),
          urgency: d.urg,
        }),
      });
      setOk(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  if (ok)
    return (
      <div className="card q">
        <h2 style={{ marginTop: 0 }}>Demande envoyée</h2>
        <p className="mu">{r.n} a bien reçu votre demande. Le mécanicien pourra la consulter dans son espace.</p>
        <a className="btn p" href="#accueil">Retour à l’accueil</a>
      </div>
    );

  return (
    <div className="card q">
      <div className="steps">
        {[1, 2, 3].map((i) => (
          <i key={i} className={i <= st ? "on" : ""}></i>
        ))}
      </div>
      <h2 style={{ marginTop: 0 }}>Demander un devis à {r.n}</h2>

      {st === 1 && (
        <div>
          <label>Type de véhicule</label>
          <div className="seg"><button type="button" className="on">{q.type}</button></div>
          <label htmlFor="veh">Marque et modèle</label>
          <input id="veh" required placeholder="Par exemple Honda CG 125" value={d.veh} onChange={(e) => setD({ ...d, veh: e.target.value })} />
        </div>
      )}

      {st === 2 && (
        <div>
          <label htmlFor="pb">Décrivez le problème</label>
          <textarea id="pb" required rows="4" placeholder="Le moteur chauffe et cale au ralenti" value={d.pb} onChange={(e) => setD({ ...d, pb: e.target.value })}></textarea>
          <label>Urgence</label>
          <div className="seg">
            {[["immediate", "Immédiate"], ["planned", "Planifiée"]].map(([value, label]) => (
              <button type="button" key={value} className={d.urg === value ? "on" : ""} onClick={() => setD({ ...d, urg: value })}>{label}</button>
            ))}
          </div>
        </div>
      )}

      {st === 3 && (
        <div>
          <p><b>Véhicule :</b> {q.type}, {d.veh}</p>
          <p><b>Problème :</b> {d.pb}</p>
          <p><b>Urgence :</b> {d.urg === "immediate" ? "Immédiate" : "Planifiée"}</p>
        </div>
      )}

      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="row" style={{ marginTop: 16 }}>
        {st > 1 && <button className="btn" type="button" onClick={() => setSt(st - 1)}>Retour</button>}
        {st < 3 ? (
          <button
            className="btn p"
            type="button"
            disabled={(st === 1 && (!d.veh.trim() || !vehicleType)) || (st === 2 && !d.pb.trim())}
            onClick={() => setSt(st + 1)}
          >Continuer</button>
        ) : (
          <button className="btn p" type="button" disabled={busy || !user} onClick={submit}>
            {busy ? "Envoi…" : "Envoyer la demande"}
          </button>
        )}
      </div>
      {!user && <p className="mu">Connectez-vous pour envoyer une demande.</p>}
    </div>
  );
}
