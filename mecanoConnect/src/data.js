export const S = ["Vidange", "Freins", "Moteur", "Électricité", "Pneus", "Diagnostic"];

export const WORDS = [
  ["Cherchez", "Moto ou voiture, service, quartier : les ateliers près de chez vous s’affichent."],
  ["Comparez", "Notes, spécialités et horaires de chaque mécanicien ou garage."],
  ["Demandez un devis", "Décrivez la panne et recevez une réponse du réparateur."],
];

// Emojis par service et visuel de carte (style "annonces colorées")
export const SE = { Vidange: "🛢️", Freins: "🛑", Moteur: "⚙️", Électricité: "🔋", Pneus: "🛞", Diagnostic: "🔍" };
export const vis = (r) => (r.v.length > 1 ? "🔧" : r.v[0] === "Moto" ? "🏍️" : "🚗");
export const tone = (r) => "t" + (((r.id - 1) % 4) + 1); // t1 vert, t2 rouge, t3 ambre, t4 acier
