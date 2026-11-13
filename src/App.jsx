import { useEffect, useState } from "react";
import { apiList, clearSession, readSession } from "./api";
import { S } from "./data";
import { useRoute, go } from "./router";
import { Head } from "./components/Common";
import Account from "./pages/Account";
import Home from "./pages/Home";
import Results from "./pages/Results";
import Detail from "./pages/Detail";
import Quote from "./pages/Quote";
import MechanicDashboard from "./pages/MechanicDashboard";
import CustomerDashboard from "./pages/CustomerDashboard";

export default function App() {
  const route = useRoute();
  const [q, setQ] = useState({ type: "Moto", service: "", lieu: "" });
  const [sel, setSel] = useState(null);
  const [session, setSession] = useState(readSession);
  const [shops, setShops] = useState([]);
  const [directoryLoading, setDirectoryLoading] = useState(true);
  const [directoryError, setDirectoryError] = useState("");

  useEffect(() => {
    let active = true;
    if (!["accueil", "resultats", "fiche"].includes(route)) return undefined;
    setDirectoryLoading(true);
    Promise.all([apiList("/shops/"), apiList("/services/"), apiList("/vehicle-types/")])
      .then(([shopList, serviceList, vehicleList]) => {
        const serviceNames = new Map(serviceList.map((item) => [item.id, item.name]));
        const vehicleNames = new Map(vehicleList.map((item) => [item.id, item.name]));
        const mappedShops = shopList.map((shop, index) => ({
          id: shop.id,
          apiId: shop.id,
          n: shop.name,
          t: shop.business_type === "garage" ? "Garage" : "Mécanicien",
          q: shop.district,
          city: shop.city,
          d: null,
          s: shop.average_rating,
          a: shop.review_count,
          v: shop.vehicle_types.map((id) => vehicleNames.get(id)).filter(Boolean),
          vehicleTypes: shop.vehicle_types.map((id) => ({
            id,
            name: vehicleNames.get(id),
          })).filter((item) => item.name),
          sp: shop.services.map((id) => serviceNames.get(id)).filter(Boolean),
          serviceIds: shop.services,
          o: null,
          dom: shop.mobile_service,
          x: shop.longitude
            ? Math.max(8, Math.min(92, 48 + Number(shop.longitude) * 100))
            : 12 + ((index * 19) % 76),
          y: shop.latitude
            ? Math.max(8, Math.min(92, 52 - Number(shop.latitude) * 100))
            : 14 + ((index * 23) % 72),
          h: "Horaires à confirmer",
          desc: shop.description || "Aucune description renseignée.",
          phone: shop.phone,
          whatsapp: shop.whatsapp,
          address: shop.address,
          isVerified: shop.is_verified,
        }));
        if (active) {
          setShops(mappedShops);
          setDirectoryError("");
          setSel((current) =>
            mappedShops.some((shop) => shop.id === current)
              ? current
              : mappedShops[0]?.id ?? null
          );
        }
      })
      .catch((error) => {
        if (active) setDirectoryError(error.message);
      })
      .finally(() => {
        if (active) setDirectoryLoading(false);
      });
    return () => {
      active = false;
    };
  }, [route]);

  useEffect(() => {
    const handleStorage = () => setSession(readSession());
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  useEffect(() => {
    if (route === "mecanicien" && !session?.access) go("connexion");
    else if (route === "mecanicien" && session.user?.role !== "mechanic") go("accueil");
    else if (route === "client" && !session?.access) go("connexion");
    else if (route === "client" && session.user?.role !== "customer") go("accueil");
    else if (route === "devis" && !session?.access) {
      window.sessionStorage.setItem("mecanoconnect.returnTo", "devis");
      go("connexion");
    } else if (route === "devis" && session.user?.role !== "customer") {
      go("mecanicien");
    }
    else if (
      ["connexion", "inscription", "inscription-client"].includes(route) &&
      session?.access
    ) {
      go(session.user?.role === "mechanic" ? "mecanicien" : "client");
    }
  }, [route, session]);

  const handleLogout = () => {
    clearSession();
    setSession(null);
  };

  const pick = (id, stay) => {
    setSel(id);
    if (!stay) go("fiche");
    else if (route === "accueil") go("resultats");
  };
  const r = shops.find((shop) => shop.id === sel) || shops[0];

  return (
    <div className="w">
      <Head user={session?.user} onLogout={handleLogout} />
      {route === "resultats" ? (
        <Results q={q} setQ={setQ} sel={sel} pick={pick} shops={shops} loading={directoryLoading} error={directoryError} services={S} />
      ) : route === "fiche" ? (
        r ? <Detail r={r} /> : <p className="card mu">Cet atelier n’est plus disponible.</p>
      ) : route === "devis" ? (
        r ? <Quote r={r} q={q} user={session?.user} /> : <p className="card mu">Cet atelier n’est plus disponible.</p>
      ) : route === "connexion" || route === "inscription" ? (
        <Account mode={route} onLogin={setSession} />
      ) : route === "inscription-client" ? (
        <Account mode={route} onLogin={setSession} />
      ) : route === "mecanicien" && session?.user?.role === "mechanic" ? (
        <MechanicDashboard
          user={session.user}
          onLogout={handleLogout}
          onPreviewShop={(id) => {
            setSel(id);
            go("fiche");
          }}
        />
      ) : route === "client" && session?.user?.role === "customer" ? (
        <CustomerDashboard user={session.user} onLogout={handleLogout} />
      ) : (
        <Home q={q} setQ={setQ} pick={pick} shops={shops} loading={directoryLoading} error={directoryError} />
      )}
      <footer>MécanoConnect · Fait au Bénin. Les ateliers de démonstration de la page d’accueil restent fictifs.</footer>
    </div>
  );
}
