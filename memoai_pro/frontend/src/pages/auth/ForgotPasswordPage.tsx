import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { describeError } from '../../api/client';
import { authApi } from '../../api/services';
import { loginPath, roleByCode, type RoleCode } from '../../lib/roles';
import AuthShell, { SpaceBadge } from './AuthShell';

/** « Mot de passe oublié ? » : un lien de réinitialisation est envoyé à l'adresse email du compte. */
export default function ForgotPasswordPage({ roleCode = 'STUDENT' }: { roleCode?: RoleCode }) {
  const role = roleByCode(roleCode)!;
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await authApi.requestPasswordReset(email.trim());
      setSent(res.message);
    } catch (err) {
      setError(describeError(err, "La demande n'a pas pu être envoyée. Réessayez."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell role={role.code} home={loginPath(role)}>
      {role.code !== 'STUDENT' && <SpaceBadge icon={role.icon} label={`Espace ${role.label.toLowerCase()}`} />}

      <span className="eyebrow">Mot de passe oublié</span>
      <h2>Réinitialisez votre mot de passe</h2>
      <p className="sub">
        Saisissez l'adresse email utilisée lors de votre inscription : nous vous enverrons un lien pour choisir
        un nouveau mot de passe.
      </p>

      {sent ? (
        <>
          <div className="success" role="status"><span>✉️ {sent}</span></div>
          <p className="hint">Le lien est valable 1 heure. Vous n'avez rien reçu ? Vérifiez l'adresse saisie ou refaites une demande.</p>
          <button type="button" className="primary" onClick={() => setSent('')}>Renvoyer un email</button>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <label className="field">Adresse email
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} autoFocus
                   placeholder="vous@universite.com" autoComplete="email" required />
          </label>

          {error && <div className="error" role="alert"><span>{error}</span></div>}

          <button className="primary" disabled={loading || !email.includes('@')}>
            {loading && <span className="spinner" aria-hidden="true" />}
            {loading ? 'Envoi…' : 'Recevoir le lien par email'}
          </button>
        </form>
      )}

      <Link className="back-link" to={loginPath(role)}>← Retour à la connexion</Link>
    </AuthShell>
  );
}
