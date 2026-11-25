import { useEffect, useState } from "react";
import { api, apiList } from "../api";

const CATEGORIES = [
  ["engine", "Panne moteur"],
  ["electrical", "Problème électrique"],
  ["brakes", "Freinage"],
  ["battery", "Batterie"],
  ["tires", "Pneumatique"],
  ["maintenance", "Entretien"],
  ["accident", "Accident"],
  ["other", "Autre problème"],
];

export default function Quote({ r, q, user }) {
  const [st, setSt] = useState(1);
  const [vehicles, setVehicles] = useState([]);
  const [vehicleId, setVehicleId] = useState("");
  const [newVehicle, setNewVehicle] = useState({
    vehicle_type: "",
    make: "",
    model: "",
    year: "",
  });
  const [d, setD] = useState({
    category: "other",
    problem: "",
    urgency: "planned",
    location: "",
    service_mode: "workshop",
    availability: "",
  });
  const [images, setImages] = useState([]);
  const [ok, setOk] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const compatibleTypes = r.vehicleTypes || [];
  const selectedVehicle = vehicles.find(
    (vehicle) => String(vehicle.id) === vehicleId
  );

  useEffect(() => {
    let active = true;
    apiList("/vehicles/")
      .then((items) => {
        const compatible = items.filter((vehicle) =>
          compatibleTypes.some((type) => type.id === vehicle.vehicle_type)
        );
        if (active) {
          setVehicles(compatible);
          setVehicleId((current) =>
            compatible.some((vehicle) => String(vehicle.id) === current)
              ? current
              : String(compatible[0]?.id || "")
          );
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [r.apiId]);

  const createVehicle = async () => {
    setError("");
    setBusy(true);
    try {
      const vehicle = await api("/vehicles/", {
        method: "POST",
        body: JSON.stringify({
          ...newVehicle,
          year: newVehicle.year ? Number(newVehicle.year) : null,
        }),
      });
      setVehicles((current) => [...current, vehicle]);
      setVehicleId(String(vehicle.id));
      setNewVehicle({ vehicle_type: "", make: "", model: "", year: "" });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!selectedVehicle) {
      setError("Enregistrez puis sélectionnez un véhicule compatible.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const body = new FormData();
      body.append("shop", String(r.apiId));
      body.append("vehicle", String(selectedVehicle.id));
      body.append("vehicle_type", String(selectedVehicle.vehicle_type));
      body.append(
        "vehicle_model",
        `${selectedVehicle.make} ${selectedVehicle.model}`.trim()
      );
      body.append("problem", d.problem.trim());
      body.append("category", d.category);
      body.append("urgency", d.urgency);
      body.append("location", d.location.trim());
      body.append("service_mode", d.service_mode);
      body.append("availability", d.availability.trim());
      images.forEach((image, index) => body.append(`images[${index}]`, image));
      await api("/quotes/", { method: "POST", body });
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
        <p className="mu">
          {r.n} a reçu votre demande. Vous pourrez suivre les échanges, le devis
          et le rendez-vous dans votre espace client.
        </p>
        <a className="btn p" href="#client">Voir mes demandes</a>
      </div>
    );

  return (
    <div className="card q">
      <div className="steps">
        {[1, 2, 3].map((i) => (
          <i key={i} className={i <= st ? "on" : ""}></i>
        ))}
      </div>
      <h2 style={{ marginTop: 0 }}>Demander une réparation à {r.n}</h2>

      {st === 1 && (
        <div>
          <label htmlFor="saved-vehicle">Véhicule enregistré</label>
          {vehicles.length > 0 ? (
            <select
              id="saved-vehicle"
              value={vehicleId}
              onChange={(event) => setVehicleId(event.target.value)}
            >
              {vehicles.map((vehicle) => (
                <option key={vehicle.id} value={vehicle.id}>
                  {vehicle.vehicle_type_name} · {vehicle.make} {vehicle.model}
                  {vehicle.year ? ` (${vehicle.year})` : ""}
                </option>
              ))}
            </select>
          ) : (
            <p className="mu">
              Aucun véhicule compatible n’est enregistré. Ajoutez-en un ci-dessous.
            </p>
          )}
          <fieldset>
            <legend>Enregistrer un véhicule</legend>
            <label htmlFor="vehicle-type">Auto ou Moto</label>
            <select
              id="vehicle-type"
              value={newVehicle.vehicle_type}
              onChange={(event) =>
                setNewVehicle({ ...newVehicle, vehicle_type: event.target.value })
              }
            >
              <option value="">Choisir le type</option>
              {compatibleTypes.map((type) => (
                <option key={type.id} value={type.id}>{type.name}</option>
              ))}
            </select>
            <div className="form-grid">
              <div>
                <label htmlFor="vehicle-make">Marque</label>
                <input
                  id="vehicle-make"
                  value={newVehicle.make}
                  maxLength="80"
                  onChange={(event) =>
                    setNewVehicle({ ...newVehicle, make: event.target.value })
                  }
                  placeholder="Honda"
                />
              </div>
              <div>
                <label htmlFor="vehicle-model">Modèle</label>
                <input
                  id="vehicle-model"
                  value={newVehicle.model}
                  maxLength="120"
                  onChange={(event) =>
                    setNewVehicle({ ...newVehicle, model: event.target.value })
                  }
                  placeholder="CG 125"
                />
              </div>
            </div>
            <label htmlFor="vehicle-year">Année (facultative)</label>
            <input
              id="vehicle-year"
              type="number"
              min="1900"
              max={new Date().getFullYear() + 1}
              value={newVehicle.year}
              onChange={(event) =>
                setNewVehicle({ ...newVehicle, year: event.target.value })
              }
            />
            <button
              className="btn"
              type="button"
              disabled={
                busy ||
                !newVehicle.vehicle_type ||
                !newVehicle.make.trim() ||
                !newVehicle.model.trim()
              }
              onClick={createVehicle}
            >
              Enregistrer le véhicule
            </button>
          </fieldset>
        </div>
      )}

      {st === 2 && (
        <div>
          <label htmlFor="category">Catégorie de panne</label>
          <select
            id="category"
            value={d.category}
            onChange={(event) => setD({ ...d, category: event.target.value })}
          >
            {CATEGORIES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <label htmlFor="pb">Décrivez le problème</label>
          <textarea
            id="pb"
            required
            rows="4"
            maxLength="3000"
            placeholder="Décrivez les symptômes et les circonstances."
            value={d.problem}
            onChange={(event) => setD({ ...d, problem: event.target.value })}
          />
          <label htmlFor="quote-images">Photos (facultatif, 4 maximum)</label>
          <input
            id="quote-images"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={(event) => {
              const selected = Array.from(event.target.files || []);
              if (selected.length > 4 || selected.some((file) => file.size > 5 * 1024 * 1024)) {
                setError("Choisissez au plus 4 photos de 5 Mo chacune.");
                event.target.value = "";
                setImages([]);
                return;
              }
              setError("");
              setImages(selected);
            }}
          />
          <p className="mu sm">JPG, PNG ou WebP, 5 Mo maximum par photo.</p>
          <label>Urgence</label>
          <div className="seg">
            {[["immediate", "Immédiate"], ["planned", "Planifiée"]].map(([value, label]) => (
              <button
                type="button"
                key={value}
                className={d.urgency === value ? "on" : ""}
                onClick={() => setD({ ...d, urgency: value })}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {st === 3 && (
        <div>
          <p><b>Véhicule :</b> {selectedVehicle?.vehicle_type_name}, {selectedVehicle?.make} {selectedVehicle?.model}</p>
          <p><b>Catégorie :</b> {CATEGORIES.find(([value]) => value === d.category)?.[1]}</p>
          <p><b>Problème :</b> {d.problem}</p>
          <p><b>Urgence :</b> {d.urgency === "immediate" ? "Immédiate" : "Planifiée"}</p>
          <label htmlFor="service-mode">Lieu de l’intervention</label>
          <select
            id="service-mode"
            value={d.service_mode}
            onChange={(event) => setD({ ...d, service_mode: event.target.value })}
          >
            <option value="workshop">En atelier</option>
            {r.dom && <option value="on_site">Sur place</option>}
          </select>
          <label htmlFor="request-location">Localisation (quartier ou adresse utile)</label>
          <input
            id="request-location"
            required
            maxLength="250"
            value={d.location}
            onChange={(event) => setD({ ...d, location: event.target.value })}
            placeholder="Par exemple : Banikanni, Parakou"
          />
          <label htmlFor="availability">Vos disponibilités</label>
          <textarea
            id="availability"
            required
            rows="3"
            maxLength="1000"
            value={d.availability}
            onChange={(event) => setD({ ...d, availability: event.target.value })}
            placeholder="Par exemple : lundi ou mercredi après 15 h"
          />
        </div>
      )}

      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="row" style={{ marginTop: 16 }}>
        {st > 1 && <button className="btn" type="button" onClick={() => setSt(st - 1)}>Retour</button>}
        {st < 3 ? (
          <button
            className="btn p"
            type="button"
            disabled={
              (st === 1 && !selectedVehicle) ||
              (st === 2 && !d.problem.trim()) ||
              (st === 3 && (!d.location.trim() || !d.availability.trim()))
            }
            onClick={() => setSt(st + 1)}
          >
            Continuer
          </button>
        ) : (
          <button
            className="btn p"
            type="button"
            disabled={busy || !user || !d.location.trim() || !d.availability.trim()}
            onClick={submit}
          >
            {busy ? "Envoi…" : "Envoyer la demande"}
          </button>
        )}
      </div>
    </div>
  );
}
