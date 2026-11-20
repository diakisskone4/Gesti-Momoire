import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';

import { describeError } from '../../api/client';
import { collaborationApi, projectsApi } from '../../api/services';
import Layout from '../../components/Layout';
import { formatDate, initials, timeAgo } from '../../lib/format';
import type { Chapter, Comment, Project } from '../../lib/models';
import { LEVEL_LABELS, PROJECT_STATUS_LABELS } from '../../lib/roles';
import '../../styles/workspace.css';

type Filter = 'todo' | 'IN_PROGRESS' | 'VALIDATED' | 'all';

const TABS: { key: Filter; label: string }[] = [
  { key: 'todo', label: 'À relire' },
  { key: 'IN_PROGRESS', label: 'En rédaction' },
  { key: 'VALIDATED', label: 'Validés' },
  { key: 'all', label: 'Tous' },
];

const MY_ROLE_LABELS: Record<string, string> = {
  SUPERVISOR: 'Encadreur', CO_SUPERVISOR: 'Co-encadreur', JURY: 'Jury', OWNER: 'Auteur', ADMIN: 'Admin',
};

function matches(p: Project, f: Filter): boolean {
  switch (f) {
    case 'todo': return p.status === 'REVIEW';
    case 'IN_PROGRESS': return p.status === 'IN_PROGRESS' || p.status === 'DRAFT';
    case 'VALIDATED': return p.status === 'VALIDATED' || p.status === 'COMPLETED';
    default: return true;
  }
}

/** Chapitres de premier niveau suivis de leurs sections. */
function ordered(chapters: Chapter[]): { chapter: Chapter; depth: number }[] {
  const out: { chapter: Chapter; depth: number }[] = [];
  const walk = (parent: number | null, depth: number) =>
    chapters.filter(c => (c.parent ?? null) === parent).sort((a, b) => a.order - b.order)
      .forEach(c => { out.push({ chapter: c, depth }); walk(c.id, depth + 1); });
  walk(null, 0);
  return out;
}

/** Espace encadreur / co-encadreur (scope « supervised ») et jury (scope « jury »). */
export default function SupervisionPage({ scope }: { scope: 'supervised' | 'jury' }) {
  const isJury = scope === 'jury';
  const [projects, setProjects] = useState<Project[]>([]);
  const [filter, setFilter] = useState<Filter>('todo');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selected, setSelected] = useState<Project | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    projectsApi.list(scope)
      .then(list => {
        setProjects(list);
        if (!list.some(p => p.status === 'REVIEW')) setFilter('all');
      })
      .catch(err => setError(describeError(err, 'Impossible de charger les mémoires.')))
      .finally(() => setLoading(false));
  }, [scope]);

  useEffect(load, [load]);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return projects
      .filter(p => matches(p, filter))
      .filter(p => !term || [p.title, p.theme, p.owner?.full_name, p.owner?.email].some(v => v?.toLowerCase().includes(term)));
  }, [projects, filter, search]);

  const count = (...statuses: string[]) => projects.filter(p => statuses.includes(p.status)).length;

  const onDecided = (updated: Project, decision: 'approve' | 'request_changes') => {
    setProjects(list => list.map(x => (x.id === updated.id ? updated : x)));
    setMessage(decision === 'approve'
      ? `« ${updated.title} » a été validé. L'étudiant a été notifié.`
      : `Corrections demandées pour « ${updated.title} ». L'étudiant a été notifié.`);
    setSelected(null);
  };

  return (
    <Layout onRefresh={load}>
      <div className="scope-ws">
        <div className="ws">
          <div className="ws-head">
            <div>
              <span className="eyebrow">{isJury ? 'Espace jury' : 'Espace encadrement'}</span>
              <h2>{isJury ? 'Mémoires à évaluer' : 'Mémoires de mes étudiants'}</h2>
              <p>{isJury
                ? 'Consultez les mémoires dont vous êtes membre du jury et validez-les pour la soutenance.'
                : 'Les étudiants vous rattachent à leur mémoire lors de sa création. Relisez, commentez et validez.'}</p>
            </div>
            <button className="btn hide-mobile" onClick={load}>↻ Actualiser</button>
          </div>

          <div className="stats">
            <div className="stat accent"><strong>{count('REVIEW')}</strong><span>À relire</span></div>
            <div className="stat"><strong>{projects.length}</strong><span>Mémoires suivis</span></div>
            <div className="stat"><strong>{count('IN_PROGRESS', 'DRAFT')}</strong><span>En rédaction</span></div>
            <div className="stat"><strong>{count('VALIDATED', 'COMPLETED')}</strong><span>Validés</span></div>
          </div>

          <div className="toolbar">
            <div className="tabs" role="tablist">
              {TABS.map(t => (
                <button key={t.key} className={`tab${filter === t.key ? ' active' : ''}`} role="tab"
                        aria-selected={filter === t.key} onClick={() => setFilter(t.key)}>
                  {t.label}<span className="count">{projects.filter(p => matches(p, t.key)).length}</span>
                </button>
              ))}
            </div>
            <input className="search" type="search" placeholder="Rechercher un étudiant, un titre..."
                   value={search} onChange={e => setSearch(e.target.value)} aria-label="Rechercher" />
          </div>

          {error && <div className="error">{error}</div>}
          {message && <div className="ok">{message}</div>}
          {loading && <div className="state">Chargement...</div>}

          {!loading && !visible.length && (
            <div className="empty">
              <strong>{projects.length ? 'Aucun mémoire dans ce filtre' : 'Aucun mémoire pour le moment'}</strong>
              {!projects.length && (isJury
                ? 'Les mémoires apparaîtront ici quand un étudiant vous ajoutera à son jury.'
                : 'Les mémoires apparaîtront ici quand un étudiant vous choisira comme encadreur.')}
            </div>
          )}

          {!loading && visible.length > 0 && (
            <div className="cards">
              {visible.map(p => (
                <article className="card" key={p.id}>
                  <div className="meta">
                    <span className={`badge ${p.status}`}>{PROJECT_STATUS_LABELS[p.status]}</span>
                    {p.my_role && <span className="badge role">{MY_ROLE_LABELS[p.my_role] ?? p.my_role}</span>}
                  </div>
                  <h3>{p.title}</h3>
                  {p.theme && <p className="theme">{p.theme}</p>}
                  {p.owner && (
                    <div className="person">
                      <span className="avatar">{initials(p.owner)}</span>
                      <span><strong>{p.owner.full_name}</strong><small>{p.owner.email}</small></span>
                    </div>
                  )}
                  <div className="meta">
                    <span>🎓 {LEVEL_LABELS[p.level]}</span>
                    {p.university && <span>🏛 {p.university}</span>}
                    <span>📄 {p.chapters.filter(c => c.parent === null).length} chapitre(s)</span>
                    {p.submitted_at && p.status === 'REVIEW' && <span>📨 soumis le {formatDate(p.submitted_at)}</span>}
                  </div>
                  {p.review_comment && <div className="note"><strong>Dernier retour :</strong> {p.review_comment}</div>}
                  <div className="actions">
                    <button className="btn primary" onClick={() => { setMessage(''); setSelected(p); }}>
                      {p.status === 'REVIEW' ? 'Relire et décider' : 'Consulter'}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        {selected && <ReviewDrawer project={selected} onClose={() => setSelected(null)} onDecided={onDecided} />}
      </div>
    </Layout>
  );
}

function ReviewDrawer({ project: p, onClose, onDecided }: {
  project: Project; onClose: () => void; onDecided: (p: Project, d: 'approve' | 'request_changes') => void;
}) {
  const [comment, setComment] = useState('');
  const [saving, setSaving] = useState(false);
  const [reviewError, setReviewError] = useState('');
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    collaborationApi.comments(p.id).then(setComments).catch(() => undefined);
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [p.id, onClose]);

  const decide = async (decision: 'approve' | 'request_changes') => {
    setReviewError('');
    if (decision === 'request_changes' && !comment.trim()) {
      setReviewError("Expliquez à l'étudiant les corrections attendues.");
      return;
    }
    setSaving(true);
    try {
      onDecided(await projectsApi.review(p.id, decision, comment.trim()), decision);
    } catch (err) {
      setReviewError(describeError(err, 'Action impossible.'));
      setSaving(false);
    }
  };

  const addComment = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const c = await collaborationApi.addComment({ project: p.id, content: newComment.trim() });
      setComments(list => [c, ...list]);
      setNewComment('');
    } catch (err) {
      setReviewError(describeError(err));
    }
  };

  return (
    <div className="backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={p.title}>
        <div className="drawer-head">
          <div>
            <span className={`badge ${p.status}`}>{PROJECT_STATUS_LABELS[p.status]}</span>
            <h2>{p.title}</h2>
            <div className="meta">
              <span>{p.owner?.full_name}</span>
              <span>{LEVEL_LABELS[p.level]} · {p.university || '—'}</span>
              {p.supervisor_detail && <span>Encadreur : {p.supervisor_detail.full_name}</span>}
              {p.co_supervisor_detail && <span>Co-encadreur : {p.co_supervisor_detail.full_name}</span>}
            </div>
          </div>
          <button className="btn" onClick={onClose} aria-label="Fermer">✕</button>
        </div>

        {p.theme && <p className="theme"><strong>Thème :</strong> {p.theme}</p>}

        {!p.chapters.length && (
          <div className="empty"><strong>Aucun chapitre rédigé</strong>L'étudiant n'a pas encore commencé la rédaction.</div>
        )}
        {ordered(p.chapters).map(({ chapter: c, depth }) => (
          <section className="chapter" key={c.id} style={{ marginLeft: depth * 16 }}>
            <h4>{c.title}</h4>
            {c.content
              ? <div className="content" style={{ whiteSpace: 'pre-wrap' }}>{c.content}</div>
              : <div className="content muted">(vide)</div>}
          </section>
        ))}

        <section className="panel">
          <h3>Commentaires ({comments.length})</h3>
          <form onSubmit={addComment} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input className="search" value={newComment} onChange={e => setNewComment(e.target.value)}
                   placeholder="Laisser un commentaire à l'étudiant…" aria-label="Nouveau commentaire" />
            <button className="btn" disabled={!newComment.trim()}>Envoyer</button>
          </form>
          {comments.map(c => (
            <div className="note" key={c.id} style={{ marginBottom: 8, opacity: c.resolved ? 0.6 : 1 }}>
              <strong>{c.user.full_name}</strong> <span className="muted">· {timeAgo(c.created_at)}{c.resolved ? ' · résolu' : ''}</span>
              <div style={{ whiteSpace: 'pre-wrap', marginTop: 4 }}>{c.content}</div>
            </div>
          ))}
        </section>

        {p.status === 'REVIEW' ? (
          <div className="review-box">
            <strong>Votre décision</strong>
            <textarea value={comment} onChange={e => setComment(e.target.value)}
                      placeholder="Commentaire pour l'étudiant (obligatoire pour demander des corrections)" />
            {reviewError && <div className="error">{reviewError}</div>}
            <div className="actions">
              <button className="btn primary" disabled={saving} onClick={() => decide('approve')}>✓ Valider le mémoire</button>
              <button className="btn warn" disabled={saving} onClick={() => decide('request_changes')}>↺ Demander des corrections</button>
            </div>
          </div>
        ) : (
          <>
            {reviewError && <div className="error">{reviewError}</div>}
            <div className="note">Les décisions sont possibles quand l'étudiant soumet son mémoire pour relecture.</div>
          </>
        )}
      </aside>
    </div>
  );
}
