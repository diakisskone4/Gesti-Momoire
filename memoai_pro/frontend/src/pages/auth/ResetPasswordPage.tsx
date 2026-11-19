import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { describeError } from '../../api/client';
import { authApi } from '../../api/services';
import { forgotPath, loginPath, roleBySlug } from '../../lib/roles';
import AuthShell from './AuthShell';

/** Page ouverte depuis le lien reçu par email : choix du nouveau mot de passe. */
export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const uid = params.get('uid') ?? '';
  const token = params.get('token') ?? '';
  const role = roleBySlug(params.get('espace')) ?? roleBySlug('etudiant')!;

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) return setError('Le mot de passe doit contenir au moins 8 caractères.');
    if (password !== confirm) return setError('Les deux mots de passe ne correspondent pas.');
    setLoading(true);
    try {
      const res = await authApi.confirmPasswordReset(uid, token, password);
      setDone(res.message);
    } catch (err) {
      setError(describeError(err, 'Réinitialisation impossible.'));
    } finally {
      setLoading(false);
    }
  };

  const linkBroken = !uid || !token;

  return (
    <AuthShell role={role.code} home={loginPath(role)}>
      <span className="eyebrow">Nouveau mot de passe</span>
      <h2>Choisissez un nouveau mot de passe</h2>

      {done ? (
        <>
          <div className="success" role="status"><span>✅ {done}</span></div>
          <p className="hint">Par sécurité, vous avez été déconnecté de tous vos appareils.</p>
          <Link className="primary" to={loginPath(role)} style={{ display: 'block', textAlign: 'center', textDecoration: 'none' }}>
            Se connecter
          </Link>
        </>
      ) : linkBroken ? (
        <>
          <div className="error" role="alert"><span>Ce lien est incomplet. Ouvrez le lien reçu par email ou faites une nouvelle demande.</span></div>
          <Link className="back-link" to={forgotPath(role)}>Faire une nouvelle demande →</Link>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <p className="sub">Au moins 8 caractères, pas uniquement des chiffres, différent de votre nom ou de votre email.</p>
          <label className="field password">Nouveau mot de passe
            <input type={show ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                   autoComplete="new-password" autoFocus required />
            <button type="button" className="toggle-pw" onClick={() => setShow(s => !s)} aria-pressed={show}
                    aria-label="Afficher le mot de passe">{show ? 'Masquer' : 'Afficher'}</button>
          </label>
          <label className="field">Confirmer le mot de passe
            <input type={show ? 'text' : 'password'} value={confirm} onChange={e => setConfirm(e.target.value)}
                   autoComplete="new-password" required />
          </label>

          {error && (
            <div className="error" role="alert">
              <span>{error}{' '}
                {error.includes('expiré') && <Link to={forgotPath(role)}>Nouvelle demande →</Link>}
              </span>
            </div>
          )}

          <button className="primary" disabled={loading || !password || !confirm}>
            {loading && <span className="spinner" aria-hidden="true" />}
            {loading ? 'Enregistrement…' : 'Enregistrer le mot de passe'}
          </button>
        </form>
      )}

      {!done && <Link className="back-link" to={loginPath(role)}>← Retour à la connexion</Link>}
    </AuthShell>
  );
}
