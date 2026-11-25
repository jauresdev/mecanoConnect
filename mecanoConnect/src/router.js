import { useEffect, useState } from "react";

export const go = (path) => {
  window.location.hash = path;
  window.scrollTo(0, 0);
};

export function useRoute() {
  const get = () => window.location.hash.slice(1) || "accueil";
  const [route, setRoute] = useState(get);
  useEffect(() => {
    const onChange = () => setRoute(get());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
