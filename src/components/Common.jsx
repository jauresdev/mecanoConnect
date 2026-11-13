import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { calculateDistanceKm, distanceBand } from "../location";
import { loadGoogleMaps } from "../googleMaps";
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

const DEFAULT_MAP_CENTER = [9.337, 2.63];
const MAP_COLORS = {
  near: "#16834b",
  medium: "#d18b00",
  far: "#d73535",
  unknown: "#687483",
  client: "#2563eb",
};

const hasCoordinates = ({ latitude, longitude }) =>
  latitude != null &&
  latitude !== "" &&
  longitude != null &&
  longitude !== "" &&
  Number.isFinite(Number(latitude)) &&
  Number.isFinite(Number(longitude)) &&
  Number(latitude) >= -90 &&
  Number(latitude) <= 90 &&
  Number(longitude) >= -180 &&
  Number(longitude) <= 180;

const mapPinSvg = (color, selected = false, client = false) => `
  <svg xmlns="http://www.w3.org/2000/svg" width="40" height="48" viewBox="0 0 40 48">
    <path d="M20 2C10.6 2 3 9.6 3 19c0 12.2 17 27 17 27s17-14.8 17-27C37 9.6 29.4 2 20 2Z"
      fill="${color}" stroke="${selected ? "#263445" : "#ffffff"}" stroke-width="${selected ? 3 : 2}"
      stroke-linejoin="round"/>
    <circle cx="20" cy="19" r="10" fill="#ffffff"/>
    ${
      client
        ? '<circle cx="20" cy="16.5" r="3" fill="#2563eb"/><path d="M14.5 26c.5-3.1 2.4-4.8 5.5-4.8s5 1.7 5.5 4.8" fill="none" stroke="#2563eb" stroke-width="2.2" stroke-linecap="round"/>'
        : '<path d="M24.7 13.1a5.2 5.2 0 0 0-5.8 6.7l-4.3 4.3a1.8 1.8 0 0 0 2.5 2.5l4.3-4.3a5.2 5.2 0 0 0 6.7-5.8l-3.3 3.3-2.2-2.2 3.3-3.3a5.2 5.2 0 0 0-1.2-.9Z" fill="#263445"/>'
    }
  </svg>`;

const leafletPinIcon = (color, selected = false, client = false) =>
  L.divIcon({
    className: "garage-marker-icon",
    html: mapPinSvg(color, selected, client),
    iconSize: [40, 48],
    iconAnchor: [20, 46],
    tooltipAnchor: [0, -42],
  });

const googlePinIcon = (maps, color, selected = false, client = false) => ({
  url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(
    mapPinSvg(color, selected, client)
  )}`,
  scaledSize: new maps.Size(40, 48),
  anchor: new maps.Point(20, 46),
});

export const Pins = ({
  shops,
  sel,
  pick,
  customerPosition,
  locationError,
  onLocate,
  locating,
}) => {
  const mapElement = useRef(null);
  const mapInstance = useRef(null);
  const markers = useRef(new Map());
  const customerMarker = useRef(null);
  const pickRef = useRef(pick);
  const [mapError, setMapError] = useState("");
  const [mapReady, setMapReady] = useState(false);

  pickRef.current = pick;

  useEffect(() => {
    let active = true;
    let fallbackActivated = false;
    const showOpenStreetMap = (message) => {
      if (!active || fallbackActivated) return;
      fallbackActivated = true;
      setMapError(message);
      const map = L.map(mapElement.current, { scrollWheelZoom: false });
      map.setView(DEFAULT_MAP_CENTER, 12);
      L.tileLayer("https://tile.openstreetmap.de/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, tuiles <a href="https://www.openstreetmap.de/">OpenStreetMap.de</a>',
      }).addTo(map);
      mapInstance.current = {
        provider: "openstreetmap",
        map,
        markers: L.featureGroup().addTo(map),
      };
      setMapReady(true);
    };
    const handleGoogleMapsAuthFailure = () => {
      if (mapInstance.current?.provider === "google") {
        markers.current.forEach((marker) => marker.setMap(null));
        markers.current.clear();
        customerMarker.current?.setMap(null);
        customerMarker.current = null;
        mapInstance.current = null;
        mapElement.current.replaceChildren();
      }
      showOpenStreetMap(
        "Google Maps n’est pas disponible avec cette clé API. La carte OpenStreetMap est affichée à la place."
      );
    };

    window.addEventListener(
      "mecanoconnect-google-maps-auth-failure",
      handleGoogleMapsAuthFailure
    );
    loadGoogleMaps()
      .then((maps) => {
        if (!active || fallbackActivated) return;
        const map = new maps.Map(mapElement.current, {
          center: { lat: DEFAULT_MAP_CENTER[0], lng: DEFAULT_MAP_CENTER[1] },
          zoom: 12,
          fullscreenControl: true,
          mapTypeControl: true,
          streetViewControl: false,
          gestureHandling: "cooperative",
        });
        mapInstance.current = { provider: "google", map };
        setMapError("");
        setMapReady(true);
      })
      .catch(() => {
        showOpenStreetMap(
          "Google Maps ne peut pas être chargé. La carte OpenStreetMap est affichée à la place."
        );
      });
    return () => {
      active = false;
      window.removeEventListener(
        "mecanoconnect-google-maps-auth-failure",
        handleGoogleMapsAuthFailure
      );
      markers.current.forEach((marker) => marker.setMap(null));
      markers.current.clear();
      customerMarker.current?.setMap(null);
      customerMarker.current = null;
      if (mapInstance.current?.provider === "openstreetmap") {
        mapInstance.current.map.remove();
      }
      mapInstance.current = null;
    };
  }, []);

  useEffect(() => {
    const mapState = mapInstance.current;
    if (!mapState) return;
    const { provider, map } = mapState;
    if (provider === "openstreetmap") {
      const markerGroup = mapState.markers;
      markerGroup.clearLayers();
      const locatedShops = shops.filter(hasCoordinates);

      locatedShops.forEach((shop) => {
        const distance = customerPosition
          ? calculateDistanceKm(customerPosition, {
              latitude: Number(shop.latitude),
              longitude: Number(shop.longitude),
            })
          : null;
        const band = distance == null ? "unknown" : distanceBand(distance);
        const marker = L.marker(
          [Number(shop.latitude), Number(shop.longitude)],
          { icon: leafletPinIcon(MAP_COLORS[band], shop.id === sel) }
        );
        const label = document.createElement("span");
        label.textContent =
          distance == null
            ? shop.n
            : `${shop.n} · ${distance.toLocaleString("fr-FR", {
                maximumFractionDigits: 1,
              })} km`;
        marker.bindTooltip(label);
        marker.on("click", () => pickRef.current(shop.id, true));
        marker.addTo(markerGroup);
      });

      const bounds = L.latLngBounds([]);
      locatedShops.forEach((shop) =>
        bounds.extend([Number(shop.latitude), Number(shop.longitude)])
      );
      if (customerPosition) {
        L.marker(
          [customerPosition.latitude, customerPosition.longitude],
          { icon: leafletPinIcon(MAP_COLORS.client, true, true), zIndexOffset: 1000 }
        )
          .bindTooltip("Votre position")
          .addTo(markerGroup);
        bounds.extend([
          customerPosition.latitude,
          customerPosition.longitude,
        ]);
      }

      if (bounds.isValid()) {
        if (locatedShops.length === 1 && !customerPosition) {
          map.setView(
            [Number(locatedShops[0].latitude), Number(locatedShops[0].longitude)],
            14
          );
        } else {
          map.fitBounds(bounds, { padding: [36, 36], maxZoom: 14 });
        }
      } else {
        map.setView(DEFAULT_MAP_CENTER, 12);
      }
      return;
    }

    const maps = window.google?.maps;
    if (!maps) return;

    const locatedShops = shops.filter(hasCoordinates);
    const currentIds = new Set(locatedShops.map((shop) => shop.id));
    markers.current.forEach((marker, id) => {
      if (!currentIds.has(id)) {
        marker.setMap(null);
        markers.current.delete(id);
      }
    });

    locatedShops.forEach((shop) => {
      const selected = shop.id === sel;
      const position = {
        lat: Number(shop.latitude),
        lng: Number(shop.longitude),
      };
      const distance = customerPosition
        ? calculateDistanceKm(customerPosition, {
            latitude: position.lat,
            longitude: position.lng,
          })
        : null;
      const band =
        distance == null ? "unknown" : distanceBand(distance);
      const markerOptions = {
        map,
        position,
        title:
          distance == null
            ? shop.n
            : `${shop.n} · ${distance.toLocaleString("fr-FR", {
                maximumFractionDigits: 1,
              })} km`,
        icon: googlePinIcon(maps, MAP_COLORS[band], selected),
        zIndex: selected ? 2 : 1,
      };
      const marker = markers.current.get(shop.id);
      if (marker) {
        marker.setOptions(markerOptions);
      } else {
        const newMarker = new maps.Marker(markerOptions);
        newMarker.addListener("click", () => pickRef.current(shop.id, true));
        markers.current.set(shop.id, newMarker);
      }
    });

    if (customerPosition) {
      const clientPosition = {
        lat: customerPosition.latitude,
        lng: customerPosition.longitude,
      };
      if (customerMarker.current) {
        customerMarker.current.setPosition(clientPosition);
      } else {
        customerMarker.current = new maps.Marker({
          map,
          position: clientPosition,
          title: "Votre position",
          zIndex: 3,
          icon: googlePinIcon(maps, MAP_COLORS.client, true, true),
        });
      }
    } else if (customerMarker.current) {
      customerMarker.current.setMap(null);
      customerMarker.current = null;
    }

    const bounds = new maps.LatLngBounds();
    let hasBounds = false;
    locatedShops.forEach((shop) => {
      bounds.extend({
        lat: Number(shop.latitude),
        lng: Number(shop.longitude),
      });
      hasBounds = true;
    });
    if (customerPosition) {
      bounds.extend({
        lat: customerPosition.latitude,
        lng: customerPosition.longitude,
      });
      hasBounds = true;
    }
    if (hasBounds) {
      map.fitBounds(bounds, 48);
      if (locatedShops.length === 1 && !customerPosition) {
        maps.event.addListenerOnce(map, "bounds_changed", () => {
          if (map.getZoom() > 15) map.setZoom(15);
        });
      }
    } else {
      map.setCenter({ lat: DEFAULT_MAP_CENTER[0], lng: DEFAULT_MAP_CENTER[1] });
      map.setZoom(12);
    }
  }, [shops, sel, customerPosition, mapReady]);

  const locatedShopCount = shops.filter(hasCoordinates).length;
  const unlocatedShopCount = shops.length - locatedShopCount;

  return (
    <div className="map google-map" role="group" aria-label="Carte Google Maps des réparateurs">
      <div className="map-canvas" ref={mapElement} />
      <div className="map-action">
        <button className="btn map-location-btn" type="button" onClick={onLocate} disabled={locating}>
          {locating ? "Localisation…" : "Me localiser"}
        </button>
      </div>
      {(mapError || unlocatedShopCount > 0) && (
        <p className="map-message" role="status">
          {mapError}
          {mapError && unlocatedShopCount > 0 && <br />}
          {unlocatedShopCount > 0 &&
            (locatedShopCount === 0
              ? "Aucun garage n’a encore renseigné ses coordonnées."
              : `${unlocatedShopCount} garage${unlocatedShopCount > 1 ? "s" : ""} sans coordonnées GPS n’appara${unlocatedShopCount > 1 ? "issent" : "ît"} pas sur la carte.`)}
        </p>
      )}
      {locationError && <p className="map-location-error" role="alert">{locationError}</p>}
      <div className="map-legend" aria-label="Légende des distances">
        <span><i className="legend-dot client" />Vous</span>
        <span><i className="legend-dot near" />0–5 km</span>
        <span><i className="legend-dot medium" />5–15 km</span>
        <span><i className="legend-dot far" />Plus de 15 km</span>
        {!customerPosition && <span><i className="legend-dot unknown" />Distance inconnue</span>}
      </div>
    </div>
  );
};

export const Seg = ({ q, setQ }) => (
  <div className="seg">
    {[["Moto", "🏍️"], ["Voiture", "🚗"]].map(([t, e]) => (
      <button type="button" key={t} className={q.type === t ? "on" : ""} onClick={() => setQ({ ...q, type: t })}>
        <span aria-hidden="true">{e}</span> {t}
      </button>
    ))}
  </div>
);
