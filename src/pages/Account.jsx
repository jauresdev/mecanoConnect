import { useState } from "react";
import { api, saveSession } from "../api";
import { go } from "../router";

export default function Account({ mode, onLogin }) {
  const choosingMechanicSpace = mode === "inscription";
  const mechanicSpace =
    mode === "inscription-moto"
      ? "moto"
      : mode === "inscription-auto"
        ? "auto"
        : mode === "inscription-auto-moto"
          ? "both"
        : "";
  const mechanicSpaceLabel =
    mechanicSpace === "moto"
      ? "moto"
      : mechanicSpace === "auto"
        ? "automobile"
        : "automobile et moto";
  const registering =
    [
      "inscription-moto",
      "inscription-auto",
      "inscription-auto-moto",
      "inscription-client",
    ].includes(mode);
  const role = mode === "inscription-client" ? "customer" : "mechanic";
  const [values, setValues] = useState({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (event) => {
    setValues({ ...values, [event.target.name]: event.target.value });
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (registering) {
        await api("/auth/register/", {
          method: "POST",
          body: JSON.stringify({
            ...values,
            role,
            ...(role === "mechanic" ? { vehicle_scope: mechanicSpace } : {}),
          }),
        });
      }
      const tokens = await api("/auth/token/", {
        method: "POST",
        body: JSON.stringify({
          username: values.username,
          password: values.password,
        }),
      });
      const user = await api("/auth/me/", {
        headers: { Authorization: `Bearer ${tokens.access}` },
      });
      const session = { ...tokens, user };
      saveSession(session);
      onLogin(session);
      const returnTo = window.sessionStorage.getItem("mecanoconnect.returnTo");
      window.sessionStorage.removeItem("mecanoconnect.returnTo");
      go(returnTo || (user.role === "mechanic" ? "mecanicien" : "client"));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="account card">
      <a className="mu back" href="#accueil">← Retour à l’accueil</a>
      <h1>
        {choosingMechanicSpace
          ? "Choisir mon espace mécanicien"
          : registering
            ? role === "mechanic"
              ? `Créer mon espace mécanicien ${mechanicSpaceLabel}`
              : "Créer un compte client"
            : "Se connecter"}
      </h1>
      {choosingMechanicSpace ? (
        <>
          <p className="mu">
            Choisissez votre activité pour créer un espace et un profil adaptés à votre atelier.
          </p>
          <div className="shop-card-actions">
            <a className="btn p" href="#inscription-moto">Mécanicien moto</a>
            <a className="btn p" href="#inscription-auto">Mécanicien automobile</a>
            <a className="btn p" href="#inscription-auto-moto">Automobile et moto</a>
          </div>
          <p className="account-switch mu">
            Vous avez déjà un compte ? <a href="#connexion">Se connecter</a>
          </p>
        </>
      ) : (
      <>
      <p className="mu">
        {registering
          ? role === "mechanic"
            ? "Après la création du compte, complétez la fiche de votre atelier. Elle sera envoyée à l’administration et publiée après validation."
            : "Créez un compte pour envoyer des demandes de devis et suivre les réponses des réparateurs."
          : "Connectez-vous pour accéder à votre espace MécanoConnect."}
      </p>
      <form onSubmit={submit}>
        {registering && (
          <>
            <label htmlFor="first_name">Prénom</label>
            <input id="first_name" name="first_name" autoComplete="given-name" value={values.first_name} onChange={update} />
            <label htmlFor="last_name">Nom</label>
            <input id="last_name" name="last_name" autoComplete="family-name" value={values.last_name} onChange={update} />
            <label htmlFor="email">Adresse e-mail</label>
            <input id="email" name="email" type="email" autoComplete="email" required value={values.email} onChange={update} />
            <label htmlFor="phone">Téléphone</label>
            <input id="phone" name="phone" type="tel" autoComplete="tel" required value={values.phone} onChange={update} />
          </>
        )}
        <label htmlFor="username">Nom d’utilisateur</label>
        <input id="username" name="username" autoComplete="username" required value={values.username} onChange={update} />
        <label htmlFor="password">Mot de passe</label>
        <input id="password" name="password" type="password" autoComplete={registering ? "new-password" : "current-password"} minLength={registering ? 10 : undefined} required value={values.password} onChange={update} />
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="btn p" type="submit" disabled={busy}>
          {busy ? "Veuillez patienter…" : registering ? `Créer mon compte ${role === "mechanic" ? `mécanicien ${mechanicSpaceLabel}` : "client"}` : "Se connecter"}
        </button>
      </form>
      <p className="account-switch mu">
        {registering ? "Vous avez déjà un compte ?" : "Pas encore de compte ?"}{" "}
        <a href={registering ? "#connexion" : "#inscription"}>{registering ? "Se connecter" : "Choisir mon espace mécanicien"}</a>
        {!registering && <> · <a href="#inscription-client">Créer un compte client</a></>}
      </p>
      </>
      )}
    </section>
  );
}
