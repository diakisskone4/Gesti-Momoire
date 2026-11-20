import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';

import { describeError, tokens } from '../api/client';
import { authApi } from '../api/services';
import Layout from '../components/Layout';
import Modal from '../components/Modal';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { formatDate, initials } from '../lib/format';
import type { User } from '../lib/models';
import { ACADEMIC_TITLES, REVIEWER_ROLES, roleByCode } from '../lib/roles';
import '../styles/profile.css';

const LANGUAGES = [
  { value: 'fr', label: 'Français' }, { value: 'en', label: 'English' },
  { value: 'es', label: 'Español' }, { value: 'ar', label: 'العربية' },
];

type Form = Pick<User, 'first_name' | 'last_name' | 'phone' | 'language' | 'university' | 'faculty' | 'department'
  | 'student_number' | 'level' | 'academic_title' | 'speciality'>;

const toForm = (u: User): Form => ({
  first_name: u.first_name ?? '', last_name: u.last_name ?? '', phone: u.phone ?? '', language: u.language ?? 'fr',
  university: u.university ?? '', faculty: u.faculty ?? '', department: u.department ?? '',
  student_number: u.student_number ?? '', level: u.level ?? '', academic_title: u.academic_title ?? '', speciality: u.speciality ?? '',
});

export default function ProfilePage() {
  const auth = useAuth();
  const toast = useToast();
  const [user, setUser] = useState<User | null>(auth.user);
  const [form, setForm] = useState<Form | null>(auth.user ? toForm(auth.user) : null);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const load = () => {
    setLoading(true);
    setError('');
    auth.refreshProfile()
      .then(u => { setUser(u); setForm(toForm(u)); })
      .catch(err => setError(describeError(err, 'Impossible de charger votre profil.')))
      .finally(() => setLoading(false));
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, []);

  const bind = (key: keyof Form) => ({
    id: key, name: key, value: (form?.[key] ?? '') as string, disabled: !editMode,
    onChange: (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm(f => f && { ...f, [key]: e.target.value }),
  });

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setError('');
    try {
      const updated = await authApi.updateProfile(form);
      auth.setUser(updated);
      setUser(updated);
      setForm(toForm(updated));
      setEditMode(false);
      toast.success('Profil mis à jour');
    } catch (err) {
      setError(describeError(err, 'Impossible de mettre à jour le profil.'));
    } finally {
      setSaving(false);
    }
  };

  const cancel = () => {
    if (user) setForm(toForm(user));
    setEditMode(false);
    setError('');
  };

  const isStudent = user?.role === 'STUDENT';
  const isReviewer = !!user && REVIEWER_ROLES.includes(user.role);
  const fullName = user ? (`${user.first_name} ${user.last_name}`.trim() || user.email) : '';

  return (
    <Layout onRefresh={load}>
      <div className="scope-profile">
        <div className="profile-page">
          <div className="page-header">
            <div>
              <span className="eyebrow">MON COMPTE</span>
              <h1>Mon profil</h1>
              <p className="subtitle">Gérez vos informations personnelles</p>
            </div>
            <div className="header-actions">
              {!editMode && <button className="btn-secondary hide-mobile" onClick={load}>🔄 Rafraîchir</button>}
              {!editMode && user && <button className="btn-secondary" onClick={() => setEditMode(true)}>✏️ Modifier</button>}
              <button className="btn-danger" onClick={() => window.confirm('Êtes-vous sûr de vouloir vous déconnecter ?') && auth.logout()}>
                🚪 Déconnexion
              </button>
            </div>
          </div>

          {loading && !user && <div className="loading-state"><div className="spinner" /><p>Chargement de votre profil...</p></div>}
          {error && <div className="error-message">⚠ {error}</div>}

          {user && form && (
            <div className="profile-card">
              <div className="profile-avatar">
                <div className="avatar-circle"><span className="avatar-text">{initials(user)}</span></div>
                <div className="avatar-info">
                  <h2>{fullName}</h2>
                  <p className="avatar-email">{user.email}</p>
                  <span className="avatar-role">{roleByCode(user.role)?.label}</span>
                  {user.created_at && <p className="avatar-email" style={{ marginTop: 6 }}>Membre depuis le {formatDate(user.created_at)}</p>}
                </div>
              </div>

              <form onSubmit={save} className="profile-form">
                <div className="form-section">
                  <h3>Informations personnelles</h3>
                  <div className="form-row">
                    <div className="form-group"><label htmlFor="first_name">Prénom</label><input type="text" {...bind('first_name')} /></div>
                    <div className="form-group"><label htmlFor="last_name">Nom</label><input type="text" {...bind('last_name')} /></div>
                  </div>
                  <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input id="email" type="email" value={user.email} disabled title="L'email ne peut pas être modifié" />
                  </div>
                  <div className="form-row">
                    <div className="form-group"><label htmlFor="phone">Téléphone</label><input type="tel" {...bind('phone')} /></div>
                    <div className="form-group">
                      <label htmlFor="language">Langue préférée</label>
                      <select {...bind('language')}>{LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}</select>
                    </div>
                  </div>
                </div>

                {user.role !== 'ADMIN' && (
                  <div className="form-section">
                    <h3>Rattachement académique</h3>
                    <div className="form-row">
                      <div className="form-group"><label htmlFor="university">Université</label><input type="text" {...bind('university')} /></div>
                      <div className="form-group"><label htmlFor="faculty">Faculté</label><input type="text" {...bind('faculty')} /></div>
                    </div>
                    {isStudent && (
                      <div className="form-row">
                        <div className="form-group"><label htmlFor="department">Département</label><input type="text" {...bind('department')} /></div>
                        <div className="form-group"><label htmlFor="student_number">Matricule</label><input type="text" {...bind('student_number')} /></div>
                        <div className="form-group">
                          <label htmlFor="level">Niveau</label>
                          <select {...bind('level')}>
                            <option value="LICENCE">Licence</option><option value="MASTER">Master</option><option value="DOCTORAT">Doctorat</option>
                          </select>
                        </div>
                      </div>
                    )}
                    {isReviewer && (
                      <div className="form-row">
                        <div className="form-group">
                          <label htmlFor="academic_title">Grade</label>
                          <select {...bind('academic_title')}>
                            <option value="">—</option>
                            {ACADEMIC_TITLES.map(t => <option key={t} value={t}>{t}</option>)}
                          </select>
                        </div>
                        <div className="form-group"><label htmlFor="speciality">Spécialité</label><input type="text" {...bind('speciality')} /></div>
                      </div>
                    )}
                  </div>
                )}

                {editMode && (
                  <div className="form-actions">
                    <button type="button" className="btn-secondary" onClick={cancel}>Annuler</button>
                    <button type="submit" className="btn-primary" disabled={saving}>
                      {saving ? 'Sauvegarde...' : '💾 Sauvegarder les modifications'}
                    </button>
                  </div>
                )}
              </form>

              <div className="security-section">
                <h3>Sécurité</h3>
                <div className="security-actions">
                  <button className="btn-secondary" onClick={() => setShowPassword(true)}>🔒 Changer le mot de passe</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      {showPassword && <ChangePasswordModal onClose={() => setShowPassword(false)} />}
    </Layout>
  );
}

function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirm) {
      setError('Les nouveaux mots de passe ne correspondent pas.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const result = await authApi.changePassword(oldPassword, newPassword);
      // Les autres appareils sont déconnectés ; cette session reçoit de nouveaux jetons.
      if (result.access) tokens.save(result.access, result.refresh);
      toast.success('Mot de passe modifié', 'Vos autres appareils ont été déconnectés.');
      onClose();
    } catch (err) {
      setError(describeError(err, 'Modification impossible.'));
      setSaving(false);
    }
  };

  return (
    <Modal title="🔒 Changer le mot de passe" onClose={onClose}>
      <form onSubmit={submit}>
        <label className="form-field">Mot de passe actuel
          <input type="password" autoComplete="current-password" required value={oldPassword} onChange={e => setOldPassword(e.target.value)} />
        </label>
        <label className="form-field">Nouveau mot de passe
          <input type="password" autoComplete="new-password" required minLength={8} value={newPassword} onChange={e => setNewPassword(e.target.value)} />
        </label>
        <label className="form-field">Confirmation
          <input type="password" autoComplete="new-password" required value={confirm} onChange={e => setConfirm(e.target.value)} />
        </label>
        <p className="muted small">8 caractères minimum, pas uniquement des chiffres, différent de votre nom ou email.</p>
        {error && <div className="alert error">⚠ {error}</div>}
        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>Annuler</button>
          <button className="btn-primary" disabled={saving || !oldPassword || !newPassword}>{saving ? 'Enregistrement…' : 'Changer'}</button>
        </div>
      </form>
    </Modal>
  );
}
