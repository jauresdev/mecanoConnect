let googleMapsPromise;

export function loadGoogleMaps() {
  if (window.google?.maps?.Map) return Promise.resolve(window.google.maps);
  if (googleMapsPromise) return googleMapsPromise;

  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  if (!apiKey) {
    return Promise.reject(
      new Error(
        "Ajoutez votre clé Google Maps JavaScript API dans le fichier .env.local."
      )
    );
  }

  googleMapsPromise = new Promise((resolve, reject) => {
    const callbackName = `mecanoconnectGoogleMaps${Date.now()}`;
    const script = document.createElement("script");
    let timeoutId;
    const query = new URLSearchParams({
      key: apiKey,
      callback: callbackName,
      loading: "async",
      v: "weekly",
    });

    window.gm_authFailure = () => {
      window.dispatchEvent(new Event("mecanoconnect-google-maps-auth-failure"));
    };
    window[callbackName] = () => {
      window.clearTimeout(timeoutId);
      delete window[callbackName];
      resolve(window.google.maps);
    };
    script.async = true;
    script.src = `https://maps.googleapis.com/maps/api/js?${query}`;
    script.onerror = () => {
      window.clearTimeout(timeoutId);
      delete window[callbackName];
      googleMapsPromise = undefined;
      reject(
        new Error(
          "Google Maps n’a pas pu être chargé. Vérifiez la clé API, sa facturation et ses restrictions."
        )
      );
    };
    timeoutId = window.setTimeout(() => {
      if (!window.google?.maps?.Map) {
        delete window[callbackName];
        googleMapsPromise = undefined;
        reject(
          new Error(
            "Google Maps ne répond pas. Vérifiez la connexion et la configuration de la clé API."
          )
        );
      }
    }, 12000);
    document.head.appendChild(script);
  });

  return googleMapsPromise;
}
