import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { ApiError, describeError } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { forgotPath, homeFor, loginPath, registerPath, roleByCode, type RoleCode, type RoleDef } from '../../lib/roles';
import AuthShell, { AuthTabs, SpaceBadge } from './AuthShell';

/** Connexion d'un espace : /login (étudiant), /encadreur/login, /co-encadreur/login, /jury/login, /admin/login.
 *  Chaque page ne connaît que son propre rôle et ne renvoie vers aucun autre espace. */
export default function LoginPage({ roleCode = 'STUDENT' }: { roleCode?: RoleCode }) {
  const auth = useAuth();
  const navigate = useNavigate();

  const role = roleByCode(roleCode)!;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [otherRole, setOtherRole] = useState<RoleDef>();

  const isStudent = role.code === 'STUDENT';
  const label = role.label.toLowerCase();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setOtherRole(undefined);
    setLoading(true);
    try {
      const user = await auth.login(email.trim(), password, role.code);
      navigate(homeFor(user.role), { replace: true });
    } catch (err) {
      setLoading(false);
      if (err instanceof ApiError && err.status === 401) setError('Email ou mot de passe incorrect.');
      else setError(describeError(err, 'Connexion impossible.'));
      if (err instanceof ApiError) setOtherRole(roleByCode((err.data as { role?: string } | null)?.role));
    }
  };

  return (
    <AuthShell role={role.code} home={loginPath(role)}>
      <AuthTabs loginUrl={loginPath(role)} registerUrl={registerPath(role)} active="login" />

      {!isStudent && <SpaceBadge icon={role.icon} label={`Espace ${label}`} />}

      <span className="eyebrow">{isStudent ? 'Bon retour' : `Connexion ${label}`}</span>
      <h2>Connectez-vous</h2>
      <p className="sub">
        {isStudent ? 'Retrouvez vos mémoires là où vous les avez laissés.' : `Accédez à votre espace ${label}.`}
      </p>

      <form onSubmit={submit} noValidate>
        <label className="field">Adresse email
          <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                 placeholder="vous@universite.com" autoComplete="email" required />
        </label>

        <label className="field password">Mot de passe
          <input type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                 placeholder="Votre mot de passe" autoComplete="current-password" required />
          <button type="button" className="toggle-pw" onClick={() => setShowPassword(s => !s)}
                  aria-pressed={showPassword} aria-label="Afficher le mot de passe">
            {showPassword ? 'Masquer' : 'Afficher'}
          </button>
        </label>

        <div className="forgot-row">
          <Link className="forgot-link" to={forgotPath(role)}>Mot de passe oublié ?</Link>
        </div>

        {error && (
          <div className="error" role="alert">
            <span>{error}{' '}
              {otherRole && <Link to={loginPath(otherRole)}>Aller à l'espace {otherRole.label} →</Link>}
            </span>
          </div>
        )}

        <button className="primary" disabled={loading || !email || !password}>
          {loading && <span className="spinner" aria-hidden="true" />}
          {loading ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>

    </AuthShell>
  );
}
