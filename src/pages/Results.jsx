import { useState } from "react";
import { SE, vis, tone } from "../data";
import { calculateDistanceKm, distanceBand } from "../location";
import { Pins, Seg, Stars } from "../components/Common";

export default function Results({ q, setQ, sel, pick, shops, loading, error, services }) {
  const [f, setF] = useState("Tous");
  const [customerPosition, setCustomerPosition] = useState(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState("");
  const L = shops.filter(
    (r) =>
      r.v.includes(q.type) &&
      (f === "Domicile" ? r.dom : true) &&
      (!q.service || r.sp.includes(q.service)) &&
      (!q.lieu || `${r.q} ${r.city}`.toLowerCase().includes(q.lieu.toLowerCase()))
  );
  const locateCustomer = () => {
    if (customerPosition || locating) return;
    if (!navigator.geolocation) {
      setLocationError("La géolocalisation n’est pas disponible sur cet appareil.");
      return;
    }

    setLocating(true);
    setLocationError("");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setCustomerPosition({
          latitude: coords.latitude,
          longitude: coords.longitude,
        });
        setLocating(false);
      },
      (error) => {
        setLocationError(
          error.code === error.PERMISSION_DENIED
            ? "Autorisez l’accès à votre position dans le navigateur pour calculer les distances."
            : error.code === error.POSITION_UNAVAILABLE
              ? "Votre position est momentanément indisponible."
              : "La recherche de votre position a expiré. Réessayez."
        );
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }
    );
  };
  const selectShop = (id, stay) => {
    pick(id, stay);
    const selectedShop = L.find((shop) => shop.id === id);
    if (
      selectedShop &&
      Number.isFinite(Number(selectedShop.latitude)) &&
      Number.isFinite(Number(selectedShop.longitude)) &&
      selectedShop.latitude !== "" &&
      selectedShop.longitude !== ""
    ) {
      locateCustomer();
    }
  };

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
              <div key={r.id} className={"card it" + (r.id === sel ? " on" : "")} onClick={() => selectShop(r.id, true)}>
                <div className={"av " + tone(r)}>{vis(r)}</div>
                <div style={{ flex: 1 }}>
                  <div className="row">
                    <b>{r.n}</b>
                    <Stars r={r} />
                  </div>
                  <div className="mu sm">{r.t} · {r.q}, {r.city} · {r.h}</div>
                  {customerPosition &&
                    r.latitude != null &&
                    r.longitude != null &&
                    Number.isFinite(Number(r.latitude)) &&
                    Number(r.latitude) >= -90 &&
                    Number(r.latitude) <= 90 &&
                    Number.isFinite(Number(r.longitude)) &&
                    Number(r.longitude) >= -180 &&
                    Number(r.longitude) <= 180 && (
                      <div className={`distance-label ${distanceBand(
                        calculateDistanceKm(customerPosition, {
                          latitude: Number(r.latitude),
                          longitude: Number(r.longitude),
                        })
                      )}`}>
                        À{" "}
                        {calculateDistanceKm(customerPosition, {
                          latitude: Number(r.latitude),
                          longitude: Number(r.longitude),
                        }).toLocaleString("fr-FR", { maximumFractionDigits: 1 })}{" "}
                        km à vol d’oiseau
                      </div>
                    )}
                  {customerPosition &&
                    (r.latitude == null ||
                      r.longitude == null ||
                      !Number.isFinite(Number(r.latitude)) ||
                      Number(r.latitude) < -90 ||
                      Number(r.latitude) > 90 ||
                      !Number.isFinite(Number(r.longitude)) ||
                      Number(r.longitude) < -180 ||
                      Number(r.longitude) > 180) && (
                      <div className="distance-label unknown">
                        Distance indisponible : position du garage non renseignée
                      </div>
                    )}
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
                      selectShop(r.id);
                    }}
                  >
                    Voir la fiche
                  </a>
                </div>
              </div>
            ))
          )}
        </div>
        <Pins
          shops={L}
          sel={sel}
          pick={selectShop}
          customerPosition={customerPosition}
          locationError={locationError}
          onLocate={locateCustomer}
          locating={locating}
        />
      </div>
    </div>
  );
}
