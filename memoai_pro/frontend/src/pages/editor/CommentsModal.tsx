import { useEffect, useState, type FormEvent } from 'react';

import { describeError } from '../../api/client';
import { collaborationApi } from '../../api/services';
import Modal from '../../components/Modal';
import { useAuth } from '../../context/AuthContext';
import { timeAgo } from '../../lib/format';
import type { Chapter, Comment, Project } from '../../lib/models';
import { roleByCode } from '../../lib/roles';

/** Fil de commentaires d'un mémoire (étudiant, encadrement, jury). */
export default function CommentsModal({ project, chapters, onClose }: { project: Project; chapters: Chapter[]; onClose: () => void }) {
  const { user } = useAuth();
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [content, setContent] = useState('');
  const [chapterId, setChapterId] = useState<number | ''>('');
  const [showResolved, setShowResolved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    collaborationApi.comments(project.id).then(setComments).catch(err => setError(describeError(err)));
  }, [project.id]);

  const chapterTitle = (id: number | null) => chapters.find(c => c.id === id)?.title;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const c = await collaborationApi.addComment({
        project: project.id, chapter: chapterId === '' ? undefined : chapterId, content: content.trim(),
      });
      setComments(list => [c, ...(list ?? [])]);
      setContent('');
    } catch (err) {
      setError(describeError(err, "Impossible d'envoyer le commentaire."));
    } finally {
      setBusy(false);
    }
  };

  const toggleResolved = async (c: Comment) => {
    try {
      await collaborationApi.resolveComment(c.id, !c.resolved);
      setComments(list => (list ?? []).map(x => (x.id === c.id ? { ...x, resolved: !c.resolved } : x)));
    } catch (err) {
      setError(describeError(err));
    }
  };

  const visible = comments?.filter(c => showResolved || !c.resolved) ?? [];
  const resolvedCount = comments?.filter(c => c.resolved).length ?? 0;

  return (
    <Modal title="💬 Commentaires" wide onClose={onClose} footer={<button className="btn-secondary" onClick={onClose}>Fermer</button>}>
      <form className="modal-section" onSubmit={submit}>
        <label className="form-field">Nouveau commentaire
          <textarea rows={3} value={content} onChange={e => setContent(e.target.value)} required
                    placeholder="Question pour votre encadreur, note de relecture…" />
        </label>
        <div className="modal-row">
          <select className="input" value={chapterId} onChange={e => setChapterId(e.target.value ? Number(e.target.value) : '')}
                  aria-label="Chapitre concerné">
            <option value="">Mémoire entier</option>
            {chapters.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
          <button className="btn-primary" style={{ flex: 'none' }} disabled={busy || !content.trim()}>Envoyer</button>
        </div>
      </form>

      {error && <div className="alert error">⚠ {error}</div>}

      {resolvedCount > 0 && (
        <label className="checkbox">
          <input type="checkbox" checked={showResolved} onChange={e => setShowResolved(e.target.checked)} />
          Afficher les commentaires résolus ({resolvedCount})
        </label>
      )}

      {comments === null && !error && <div className="empty-box">Chargement…</div>}
      {comments !== null && visible.length === 0 && <div className="empty-box">Aucun commentaire.</div>}
      <div className="item-list">
        {visible.map(c => (
          <div className="item" key={c.id} style={c.resolved ? { opacity: 0.6 } : undefined}>
            <div style={{ minWidth: 0, flex: 1 }}>
              <strong>
                {c.user.full_name}{' '}
                <span className="muted small" style={{ fontWeight: 400 }}>
                  · {c.user.id === user?.id ? 'vous' : roleByCode(c.user.role)?.label} · {timeAgo(c.created_at)}
                  {c.chapter && chapterTitle(c.chapter) ? ` · ${chapterTitle(c.chapter)}` : ''}
                </span>
              </strong>
              <p style={{ margin: '6px 0 0', whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', fontSize: 14 }}>{c.content}</p>
            </div>
            <div className="item-actions">
              <button className="btn-icon" title={c.resolved ? 'Rouvrir' : 'Marquer comme résolu'}
                      aria-label={c.resolved ? 'Rouvrir' : 'Marquer comme résolu'} onClick={() => toggleResolved(c)}>
                {c.resolved ? '↺' : '✓'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
