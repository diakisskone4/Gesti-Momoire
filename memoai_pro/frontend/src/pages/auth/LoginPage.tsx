import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';

import { ApiError, describeError } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { homeFor, loginPath, registerPath, roleByCode, roleBySlug, type RoleDef } from '../../lib/roles';
import AuthShell, { AuthTabs, SpaceLink, STAFF_FEATURES, STUDENT_FEATURES } from './AuthShell';

/** /login (étudiant) et /pro/login/:role (encadreur, co-encadreur, jury, administrateur). */
export default function LoginPage() {
  const { role: slug } = useParams();
  const auth = useAuth();
  const navigate = useNavigate();

  const role = slug ? roleBySlug(slug) : roleByCode('STUDENT');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [otherRole, setOtherRole] = useState<RoleDef>();

  if (!role || (slug && role.code === 'STUDENT')) return <Navigate to="/pro" replace />;
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
    <AuthShell
      home={isStudent ? '/login' : '/pro'}
      pill={isStudent ? 'Espace étudiant' : 'Enseignants & administration'}
      title={isStudent ? 'Construisez un mémoire' : 'Accompagnez vos étudiants'}
      highlight={isStudent ? 'plus intelligent.' : "jusqu'à la soutenance."}
      text={isStudent
        ? "Organisez vos idées, rédigez vos chapitres et laissez l'IA vous aider, de la première idée jusqu'à la version finale."
        : "Suivez l'avancement des mémoires, relisez les chapitres et validez le travail de vos étudiants."}
      features={isStudent ? STUDENT_FEATURES : STAFF_FEATURES}
      quote={isStudent ? "Votre assistant académique, de la première idée jusqu'à la version finale." : ''}
    >
      <AuthTabs loginUrl={loginPath(role)} registerUrl={registerPath(role)} active="login" />

      {!isStudent && (
        <div className="role-chip">
          <span className="icon" aria-hidden="true">{role.icon}</span>
          <span><strong>{role.label}</strong><small>Espace enseignants & administration</small></span>
          <Link to="/pro">Changer de profil</Link>
        </div>
      )}

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

      <div className="divider">{isStudent ? "Vous n'êtes pas étudiant ?" : 'Vous êtes étudiant ?'}</div>
      {isStudent
        ? <SpaceLink student={false} to="/pro" subtitle="Encadreur, co-encadreur, jury ou administrateur" />
        : <SpaceLink student to="/login" subtitle="Rédigez et suivez votre mémoire" />}
    </AuthShell>
  );
}
