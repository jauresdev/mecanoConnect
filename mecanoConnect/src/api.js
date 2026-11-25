const API_BASE = import.meta.env.VITE_API_URL || "/api";
const SESSION_KEY = "mecanoconnect.session";

export function readSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

export function saveSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

async function refreshAccessToken(session) {
  if (!session?.refresh) return null;
  const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: session.refresh }),
  });
  if (!response.ok) return null;
  const tokens = await response.json();
  const updated = { ...session, access: tokens.access };
  saveSession(updated);
  return updated;
}

export async function api(path, options = {}, retry = true) {
  let session = readSession();
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (session?.access) headers.set("Authorization", `Bearer ${session.access}`);

  let response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401 && retry && session?.refresh) {
    session = await refreshAccessToken(session);
    if (session) return api(path, options, false);
  }

  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 429) {
      const retryAfter = Number(response.headers.get("Retry-After"));
      const detail = payload?.detail || "";
      const waitMatch = detail.match(/(?:available in|dans)\s+([\d.]+)\s*(seconds?|secondes?)/i);
      const waitSeconds = retryAfter || (waitMatch ? Number(waitMatch[1]) : 0);
      const waitMessage = waitSeconds
        ? ` Réessayez dans environ ${Math.max(1, Math.ceil(waitSeconds / 60))} minute(s).`
        : "";
      throw new Error(`Trop de tentatives. Veuillez patienter.${waitMessage}`);
    }
    const message = payload
      ? Object.entries(payload)
          .map(([key, value]) => {
            const detail = Array.isArray(value) ? value.join(" ") : String(value);
            return key === "detail" || key === "non_field_errors"
              ? detail
              : `${key}: ${detail}`;
          })
          .join(" · ")
      : `Erreur du serveur (${response.status}).`;
    throw new Error(message || `Erreur du serveur (${response.status}).`);
  }
  return payload;
}

export async function apiList(path) {
  const results = [];
  let next = path;
  while (next) {
    const page = await api(next);
    if (!Array.isArray(page?.results)) {
      throw new Error("La réponse de l’API ne contient pas de liste valide.");
    }
    results.push(...page.results);
    if (page.next) {
      const nextUrl = new URL(page.next, window.location.origin);
      next = `${nextUrl.pathname.replace(/^\/api(?=\/)/, "")}${nextUrl.search}`;
    } else {
      next = null;
    }
  }
  return results;
}
