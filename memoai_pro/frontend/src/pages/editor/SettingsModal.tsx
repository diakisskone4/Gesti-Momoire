import { useEffect, useState } from 'react';

import { describeError } from '../../api/client';
import { authApi, projectsApi } from '../../api/services';
import Modal from '../../components/Modal';
import { useToast } from '../../context/ToastContext';
import type { Project, User } from '../../lib/models';

const label = (u: User) => [u.academic_title, u.full_name].filter(Boolean).join(' ');

/** Titre, thème, encadrement et jury d'un mémoire. */
export default function SettingsModal({ project, onClose, onSaved }: { project: Project; onClose: () => void; onSaved: (p: Project) => void }) {
  const toast = useToast();
  const [title, setTitle] = useState(project.title);
  const [theme, setTheme] = useState(project.theme ?? '');
  const [supervisor, setSupervisor] = useState<number | null>(project.supervisor);
  const [coSupervisor, setCoSupervisor] = useState<number | null>(project.co_supervisor);
  const [jury, setJury] = useState<number[]>(project.jury ?? []);
  const [supervisors, setSupervisors] = useState<User[]>([]);
  const [coSupervisors, setCoSupervisors] = useState<User[]>([]);
  const [juryMembers, setJuryMembers] = useState<User[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const locked = project.status === 'REVIEW' || project.status === 'VALIDATED';

  useEffect(() => {
    authApi.directory('SUPERVISOR').then(setSupervisors).catch(() => undefined);
    authApi.directory('SUPERVISOR,CO_SUPERVISOR').then(setCoSupervisors).catch(() => undefined);
    authApi.directory('JURY').then(setJuryMembers).catch(() => undefined);
  }, []);

  const save = async () => {
    setSaving(true);
    setError('');
    try {
      const updated = await projectsApi.update(project.id, {
        title: title.trim(), theme: theme.trim(), supervisor, co_supervisor: coSupervisor, jury,
      });
      toast.success('Mémoire mis à jour');
      onSaved(updated);
    } catch (err) {
      setError(describeError(err, 'Enregistrement impossible.'));
      setSaving(false);
    }
  };

  return (
    <Modal title="⚙ Paramètres du mémoire" onClose={onClose} footer={<>
      <button className="btn-secondary" onClick={onClose}>Annuler</button>
      <button className="btn-primary" onClick={save} disabled={saving || !title.trim()}>{saving ? 'Enregistrement…' : 'Enregistrer'}</button>
    </>}>
      <label className="form-field">Titre<input value={title} maxLength={255} onChange={e => setTitle(e.target.value)} /></label>
      <label className="form-field">Thème / problématique
        <textarea rows={3} value={theme} maxLength={255} onChange={e => setTheme(e.target.value)} />
      </label>

      {locked && <div className="alert info">Le mémoire est {project.status === 'REVIEW' ? 'en relecture' : 'validé'} : évitez de changer l'encadrement maintenant.</div>}

      <div className="modal-row">
        <label className="form-field">Encadreur
          <select value={supervisor ?? ''} onChange={e => setSupervisor(e.target.value ? Number(e.target.value) : null)}>
            <option value="">— Aucun —</option>
            {supervisors.map(u => <option key={u.id} value={u.id}>{label(u)}</option>)}
          </select>
        </label>
        <label className="form-field">Co-encadreur
          <select value={coSupervisor ?? ''} onChange={e => setCoSupervisor(e.target.value ? Number(e.target.value) : null)}>
            <option value="">— Aucun —</option>
            {coSupervisors.map(u => <option key={u.id} value={u.id} disabled={u.id === supervisor}>{label(u)}</option>)}
          </select>
        </label>
      </div>

      {juryMembers.length > 0 && (
        <fieldset className="modal-section" style={{ margin: 0 }}>
          <legend className="small" style={{ fontWeight: 700 }}>Membres du jury</legend>
          {juryMembers.map(u => (
            <label className="checkbox" key={u.id}>
              <input type="checkbox" checked={jury.includes(u.id)}
                     onChange={e => setJury(list => (e.target.checked ? [...list, u.id] : list.filter(x => x !== u.id)))} />
              {label(u)}{u.speciality ? ` — ${u.speciality}` : ''}
            </label>
          ))}
        </fieldset>
      )}

      {error && <div className="alert error">⚠ {error}</div>}
    </Modal>
  );
}
