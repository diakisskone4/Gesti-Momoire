import { useState, type ChangeEvent, type FormEvent } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';

import { describeError } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import type { RegisterPayload } from '../../lib/models';
import { ACADEMIC_TITLES, homeFor, loginPath, registerPath, roleByCode, roleBySlug } from '../../lib/roles';
import AuthShell, { AuthTabs, SpaceLink, STAFF_FEATURES, STUDENT_FEATURES } from './AuthShell';

/** /register (étudiant) et /pro/register/:role. */
export default function RegisterPage() {
  const { role: slug } = useParams();
  const auth = useAuth();
  const navigate = useNavigate();
  const role = slug ? roleBySlug(slug) : roleByCode('STUDENT');

  const [f, setF] = useState<RegisterPayload>(() => ({
    email: '', first_name: '', last_name: '', phone: '', password: '', password2: '',
    role: role?.code ?? 'STUDENT', language: 'fr', university: '', faculty: '', department: '', student_number: '',
    level: role?.code === 'STUDENT' ? 'MASTER' : '', academic_title: '', speciality: '', admin_code: '',
  }));
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!role || (slug && role.code === 'STUDENT')) return <Navigate to="/pro/register" replace />;
  const isStudent = role.code === 'STUDENT';
  const isReviewer = ['SUPERVISOR', 'CO_SUPERVISOR', 'JURY'].includes(role.code);
  const isAdmin = role.code === 'ADMIN';

  const bind = (key: keyof RegisterPayload) => ({
    value: f[key] as string,
    onChange: (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF(prev => ({ ...prev, [key]: e.target.value })),
  });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (f.password !== f.password2) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }
    setLoading(true);
    try {
      const user = await auth.register({
        ...f, email: f.email.trim(), first_name: f.first_name.trim(), last_name: f.last_name.trim(),
      });
      navigate(homeFor(user.role), { replace: true });
    } catch (err) {
      setLoading(false);
      setError(describeError(err, 'Impossible de créer le compte.'));
    }
  };

  return (
    <AuthShell
      wide
      home={isStudent ? '/login' : '/pro'}
      pill={isStudent ? 'Inscription étudiant' : `Inscription ${role.label}`}
      title={isStudent ? 'Donnez vie à votre' : 'Rejoignez'}
      highlight={isStudent ? 'projet académique.' : 'MemoAI Pro.'}
      text={role.description}
      features={isStudent ? STUDENT_FEATURES : STAFF_FEATURES}
      quote={isStudent ? "Rédaction et sauvegarde cloud gratuites : vous ne payez que l'export final." : ''}
    >
      <AuthTabs loginUrl={loginPath(role)} registerUrl={registerPath(role)} active="register" />

      {!isStudent && (
        <div className="role-chip">
          <span className="icon" aria-hidden="true">{role.icon}</span>
          <span><strong>{role.label}</strong><small>Espace enseignants & administration</small></span>
          <Link to="/pro/register">Changer de profil</Link>
        </div>
      )}

      <span className="eyebrow">Nouveau compte</span>
      <h2>{isStudent ? 'Créez votre compte étudiant' : `Créez votre compte ${role.label.toLowerCase()}`}</h2>
      {isStudent && <p className="sub">Commencez gratuitement, vous pourrez choisir votre encadreur ensuite.</p>}
      {isReviewer && <p className="sub">Vos étudiants pourront vous choisir lors de la création de leur mémoire.</p>}
      {isAdmin && <p className="sub">L'inscription administrateur nécessite le code d'accès fourni par l'équipe technique.</p>}

      <form onSubmit={submit} noValidate>
        <fieldset className="group">
          <legend>Identité</legend>
          <div className="grid">
            <label className="field">Prénom <span className="req">*</span>
              <input {...bind('first_name')} autoComplete="given-name" required />
            </label>
            <label className="field">Nom <span className="req">*</span>
              <input {...bind('last_name')} autoComplete="family-name" required />
            </label>
          </div>
          <div className="grid">
            <label className="field">Adresse email <span className="req">*</span>
              <input type="email" {...bind('email')} placeholder="vous@universite.com" autoComplete="email" required />
            </label>
            <label className="field">Téléphone
              <input type="tel" {...bind('phone')} placeholder="+223 ..." autoComplete="tel" />
            </label>
          </div>
        </fieldset>

        {isStudent && (
          <fieldset className="group">
            <legend>Parcours académique</legend>
            <div className="grid">
              <label className="field">Université <span className="req">*</span>
                <input {...bind('university')} placeholder="ex. USTTB" required />
              </label>
              <label className="field">Niveau <span className="req">*</span>
                <select {...bind('level')} required>
                  <option value="LICENCE">Licence</option>
                  <option value="MASTER">Master</option>
                  <option value="DOCTORAT">Doctorat</option>
                </select>
              </label>
            </div>
            <div className="grid">
              <label className="field">Faculté<input {...bind('faculty')} /></label>
              <label className="field">Département<input {...bind('department')} /></label>
            </div>
            <label className="field">Matricule<input {...bind('student_number')} /></label>
          </fieldset>
        )}

        {isReviewer && (
          <fieldset className="group">
            <legend>Profil académique</legend>
            <div className="grid">
              <label className="field">Grade <span className="req">*</span>
                <select {...bind('academic_title')} required>
                  <option value="" disabled>Choisir…</option>
                  {ACADEMIC_TITLES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
              <label className="field">Université {role.code !== 'JURY' && <span className="req">*</span>}
                <input {...bind('university')} required={role.code !== 'JURY'} />
              </label>
            </div>
            <div className="grid">
              <label className="field">Faculté / institution<input {...bind('faculty')} /></label>
              <label className="field">Spécialité<input {...bind('speciality')} placeholder="ex. Économie du développement" /></label>
            </div>
          </fieldset>
        )}

        {isAdmin && (
          <fieldset className="group">
            <legend>Accès</legend>
            <label className="field">Code d'accès administrateur <span className="req">*</span>
              <input type="password" {...bind('admin_code')} autoComplete="off" required />
              <span className="hint">Code défini côté serveur (variable ADMIN_REGISTRATION_CODE).</span>
            </label>
          </fieldset>
        )}

        <fieldset className="group">
          <legend>Sécurité</legend>
          <div className="grid">
            <label className="field password">Mot de passe <span className="req">*</span>
              <input type={showPassword ? 'text' : 'password'} {...bind('password')} autoComplete="new-password" required minLength={8} />
              <button type="button" className="toggle-pw" onClick={() => setShowPassword(s => !s)}
                      aria-pressed={showPassword} aria-label="Afficher les mots de passe">
                {showPassword ? 'Masquer' : 'Afficher'}
              </button>
            </label>
            <label className="field">Confirmation <span className="req">*</span>
              <input type={showPassword ? 'text' : 'password'} {...bind('password2')} autoComplete="new-password" required />
            </label>
          </div>
          <p className="field"><span className="hint" style={{ marginTop: -8 }}>
            8 caractères minimum, pas uniquement des chiffres, et différent de votre nom ou de votre email.
          </span></p>
        </fieldset>

        {error && <div className="error" role="alert"><span>{error}</span></div>}

        <button className="primary" disabled={loading}>
          {loading && <span className="spinner" aria-hidden="true" />}
          {loading ? 'Création du compte…' : 'Créer mon compte'}
        </button>
        <p className="legal">En créant un compte, vous acceptez les conditions d'utilisation de MemoAI Pro.</p>
      </form>

      <div className="divider">{isStudent ? "Vous n'êtes pas étudiant ?" : 'Vous êtes étudiant ?'}</div>
      {isStudent
        ? <SpaceLink student={false} to="/pro/register" subtitle="Encadreur, co-encadreur, jury ou administrateur" />
        : <SpaceLink student to="/register" subtitle="Créez votre compte étudiant gratuitement" />}
    </AuthShell>
  );
}
