import { useEffect, useState, type FormEvent } from 'react';

import { describeError } from '../../api/client';
import { collaborationApi } from '../../api/services';
import Modal from '../../components/Modal';
import { useToast } from '../../context/ToastContext';
import { formatDate } from '../../lib/format';
import type { Collaborator, ShareLink } from '../../lib/models';

const ROLE_LABELS = { viewer: 'Lecteur', editor: 'Éditeur', owner: 'Propriétaire' };

export default function CollaborationModal({ projectId, onClose }: { projectId: number; onClose: () => void }) {
  const toast = useToast();
  const [collaborators, setCollaborators] = useState<Collaborator[] | null>(null);
  const [links, setLinks] = useState<ShareLink[]>([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'viewer' | 'editor'>('viewer');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([collaborationApi.collaborators(projectId), collaborationApi.shareLinks(projectId)])
      .then(([c, l]) => { setCollaborators(c); setLinks(l); })
      .catch(err => setError(describeError(err)));
  }, [projectId]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError('');
    try { await fn(); } catch (err) { setError(describeError(err)); } finally { setBusy(false); }
  };

  const invite = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const c = await collaborationApi.addCollaborator(projectId, email.trim(), role);
      setCollaborators(list => [...(list ?? []), c]);
      setEmail('');
      toast.success('Collaborateur ajouté', `${c.user_name} a été notifié.`);
    });
  };

  const changeRole = (c: Collaborator, newRole: 'viewer' | 'editor') => run(async () => {
    const updated = await collaborationApi.updateCollaborator(c.id, newRole);
    setCollaborators(list => (list ?? []).map(x => (x.id === updated.id ? updated : x)));
  });

  const removeCollaborator = (c: Collaborator) => {
    if (!window.confirm(`Retirer ${c.user_name} des collaborateurs ?`)) return;
    run(async () => {
      await collaborationApi.removeCollaborator(c.id);
      setCollaborators(list => (list ?? []).filter(x => x.id !== c.id));
    });
  };

  const shareUrl = (l: ShareLink) => `${window.location.origin}${l.url}`;

  const createLink = () => run(async () => {
    const link = await collaborationApi.createShareLink(projectId, { can_comment: true, can_export: false });
    setLinks(list => [link, ...list]);
    try { await navigator.clipboard.writeText(shareUrl(link)); toast.success('Lien créé et copié'); }
    catch { toast.success('Lien créé'); }
  });

  const copy = async (l: ShareLink) => {
    try { await navigator.clipboard.writeText(shareUrl(l)); toast.success('Lien copié'); }
    catch { toast.error('Copie impossible', shareUrl(l)); }
  };

  const deleteLink = (l: ShareLink) => run(async () => {
    await collaborationApi.deleteShareLink(l.token);
    setLinks(list => list.filter(x => x.token !== l.token));
  });

  const revokeAll = () => {
    if (!window.confirm('Révoquer tous les liens de partage de ce mémoire ?')) return;
    run(async () => { await collaborationApi.revokeAll(projectId); setLinks([]); });
  };

  return (
    <Modal title="👥 Collaboration" wide onClose={onClose} footer={<button className="btn-secondary" onClick={onClose}>Fermer</button>}>
      <form className="modal-section" onSubmit={invite}>
        <h4>Inviter un collaborateur</h4>
        <p className="muted small" style={{ marginTop: 0 }}>La personne doit déjà avoir un compte MemoAI Pro.</p>
        <div className="modal-row">
          <input className="input" type="email" required value={email} onChange={e => setEmail(e.target.value)}
                 placeholder="email@universite.com" aria-label="Email du collaborateur" />
          <select className="input" style={{ flex: 'none', width: 130 }} value={role}
                  onChange={e => setRole(e.target.value as 'viewer' | 'editor')} aria-label="Rôle">
            <option value="viewer">Lecteur</option>
            <option value="editor">Éditeur</option>
          </select>
          <button className="btn-primary" style={{ flex: 'none' }} disabled={busy || !email.trim()}>Inviter</button>
        </div>
      </form>

      {error && <div className="alert error">⚠ {error}</div>}

      <h4 style={{ margin: '4px 0 10px' }}>Collaborateurs ({collaborators?.length ?? 0})</h4>
      {collaborators === null && !error && <div className="empty-box">Chargement…</div>}
      {collaborators?.length === 0 && <div className="empty-box">Aucun collaborateur pour le moment.</div>}
      <div className="item-list">
        {collaborators?.map(c => (
          <div className="item" key={c.id}>
            <div><strong>{c.user_name}</strong><small>{c.user_email} · ajouté le {formatDate(c.invited_at)}</small></div>
            <div className="item-actions">
              {c.role === 'owner' ? <span className="muted small">{ROLE_LABELS.owner}</span> : (
                <select className="input" style={{ width: 120, padding: '6px 8px' }} value={c.role} disabled={busy}
                        onChange={e => changeRole(c, e.target.value as 'viewer' | 'editor')} aria-label={`Rôle de ${c.user_name}`}>
                  <option value="viewer">Lecteur</option>
                  <option value="editor">Éditeur</option>
                </select>
              )}
              <button className="btn-icon" aria-label={`Retirer ${c.user_name}`} title="Retirer" onClick={() => removeCollaborator(c)}>🗑️</button>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '22px 0 10px', gap: 10, flexWrap: 'wrap' }}>
        <h4 style={{ margin: 0 }}>Liens de partage ({links.length})</h4>
        <div style={{ display: 'flex', gap: 8 }}>
          {links.length > 0 && <button className="btn-danger" onClick={revokeAll} disabled={busy}>Tout révoquer</button>}
          <button className="btn-secondary" onClick={createLink} disabled={busy}>🔗 Créer un lien</button>
        </div>
      </div>
      <div className="item-list">
        {links.map(l => (
          <div className="item" key={l.token}>
            <div style={{ minWidth: 0 }}>
              <strong>Lien en lecture{l.can_comment ? ' + commentaires' : ''}</strong>
              <small>{shareUrl(l)} · créé le {formatDate(l.created_at)}</small>
            </div>
            <div className="item-actions">
              <button className="btn-icon" title="Copier" aria-label="Copier le lien" onClick={() => copy(l)}>📋</button>
              <button className="btn-icon" title="Supprimer" aria-label="Supprimer le lien" onClick={() => deleteLink(l)}>🗑️</button>
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
