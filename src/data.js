export const UNIVERSES = {
  auto: {
    key: "auto",
    type: "Voiture",
    vehicleSlug: "voiture",
    name: "Mécano Auto",
    icon: "🚗",
    description: "Garages et spécialistes pour l’entretien et la réparation de voitures.",
  },
  moto: {
    key: "moto",
    type: "Moto",
    vehicleSlug: "moto",
    name: "Mécano Moto",
    icon: "🏍️",
    description: "Mécaniciens et ateliers dédiés aux motos et deux-roues.",
  },
};

export const WORDS = [
  ["Choisissez", "Sélectionnez l’univers auto ou moto adapté à votre véhicule."],
  ["Comparez", "Notes, spécialités et horaires de chaque mécanicien ou garage."],
  ["Demandez un devis", "Décrivez la panne et recevez une réponse du réparateur."],
];

// Emojis par service et visuel de carte (style "annonces colorées")
export const SE = {
  Vidange: "🛢️",
  Freins: "🛑",
  Moteur: "⚙️",
  Électricité: "🔋",
  Pneus: "🛞",
  Diagnostic: "🔍",
  Carrosserie: "🚘",
  "Climatisation automobile": "❄️",
  "Boîte de vitesses": "⚙️",
  "Chaîne et transmission": "⛓️",
  Carburateur: "⚙️",
  "Suspension moto": "🏍️",
  "Mécanique générale": "🔧",
  "Électricité automobile": "🔋",
  "Diagnostic électronique": "🔍",
  "Moteur et transmission": "⚙️",
  "Réparation moteur moto": "🔧",
  "Électricité moto": "🔋",
  "Transmission moto": "⛓️",
  "Entretien et vidange moto": "🛢️",
  "Pneumatiques moto": "🛞",
};
export const vis = (r) => (r.v.length > 1 ? "🔧" : r.v[0] === "Moto" ? "🏍️" : "🚗");
export const tone = (r) => "t" + (((r.id - 1) % 4) + 1); // t1 vert, t2 rouge, t3 ambre, t4 acier
