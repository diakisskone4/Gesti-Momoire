import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { describeError } from '../../api/client';
import { projectsApi } from '../../api/services';
import Layout from '../../components/Layout';
import { useToast } from '../../context/ToastContext';
import type { Project } from '../../lib/models';
import { LEVEL_LABELS, PROJECT_STATUS_LABELS } from '../../lib/roles';
import { STATUS_CLASS } from './DashboardPage';
import '../../styles/projects.css';

export default function ProjectsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    projectsApi.list('mine', showArchived)
      .then(setProjects)
      .catch(err => setError(describeError(err, 'Impossible de charger vos mémoires.')))
      .finally(() => setLoading(false));
  }, [showArchived]);

  useEffect(load, [load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return projects.filter(p => !term || p.title.toLowerCase().includes(term) || p.theme?.toLowerCase().includes(term));
  }, [projects, search]);

  const replace = (updated: Project) => setProjects(list => list.map(p => (p.id === updated.id ? updated : p)));
  const fail = (err: unknown, fallback: string) => toast.error('Action impossible', describeError(err, fallback));

  const remove = (p: Project) => {
    if (!window.confirm(`Placer « ${p.title} » dans la corbeille ? Vous pourrez le restaurer pendant 30 jours.`)) return;
    projectsApi.remove(p.id)
      .then(() => { setProjects(list => list.filter(x => x.id !== p.id)); toast.success('Mémoire placé dans la corbeille', 'Restaurable depuis le menu « Corbeille ».'); })
      .catch(err => fail(err, 'Impossible de supprimer le mémoire.'));
  };

  const submit = (p: Project) => {
    if (!window.confirm(`Soumettre « ${p.title} » à votre encadreur pour relecture ?`)) return;
    projectsApi.submitReview(p.id)
      .then(updated => { replace(updated); toast.success('Mémoire soumis', 'Votre encadreur a été notifié.'); })
      .catch(err => fail(err, 'Impossible de soumettre le mémoire.'));
  };

  const archive = (p: Project) => projectsApi.archive(p.id)
    .then(updated => {
      if (showArchived) replace(updated);
      else setProjects(list => list.filter(x => x.id !== p.id));
      toast.info('Mémoire archivé', showArchived ? '' : 'Cochez « Afficher les archives » pour le retrouver.');
    })
    .catch(err => fail(err, "Impossible d'archiver le mémoire."));

  const restore = (p: Project) => projectsApi.restore(p.id)
    .then(updated => { replace(updated); toast.success('Mémoire restauré'); })
    .catch(err => fail(err, 'Impossible de restaurer le mémoire.'));

  return (
    <Layout>
      <div className="scope-projects">
        <div className="projects-page">
          <div className="page-header">
            <div>
              <span className="eyebrow">MES MÉMOIRES</span>
              <h1>Mes mémoires</h1>
              <p className="subtitle">Gérez tous vos mémoires et projets de recherche</p>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button className="btn-secondary" onClick={load}>🔄 Rafraîchir</button>
              <button className="btn-primary" onClick={() => navigate('/projects/new')}>+ Nouveau mémoire</button>
            </div>
          </div>

          <div className="search-bar">
            <div className="search-input-wrapper">
              <span className="search-icon">🔍</span>
              <input type="search" value={search} onChange={e => setSearch(e.target.value)}
                     placeholder="Rechercher un mémoire..." className="search-input" aria-label="Rechercher un mémoire" />
            </div>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 13, color: 'var(--text-secondary)' }}>
              <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} />
              Afficher les archives
            </label>
            <span className="project-count">{filtered.length} mémoire(s)</span>
          </div>

          {loading && (
            <div className="loading-state">
              <div className="spinner" />
              <p>Chargement de vos mémoires...</p>
            </div>
          )}

          {error && !loading && (
            <div className="error-state">
              <p>⚠️ {error}</p>
              <button className="btn-primary" onClick={load}>Réessayer</button>
            </div>
          )}

          {!loading && !error && (
            <div className="projects-grid">
              {filtered.map(p => (
                <div key={p.id} className="project-card" role="link" tabIndex={0}
                     onClick={() => navigate(`/projects/${p.id}/editor`)}
                     onKeyDown={e => e.key === 'Enter' && e.target === e.currentTarget && navigate(`/projects/${p.id}/editor`)}>
                  <div className="project-card-header">
                    <div className="project-status">
                      <span className={`status-badge ${STATUS_CLASS[p.status] ?? 'status-draft'}`}>{PROJECT_STATUS_LABELS[p.status] ?? p.status}</span>
                      <button className="btn-delete" title="Supprimer" aria-label={`Supprimer ${p.title}`}
                              onClick={e => { e.stopPropagation(); remove(p); }}>🗑️</button>
                    </div>
                    <h3>{p.title}</h3>
                    {p.theme && <p className="project-theme">{p.theme}</p>}
                  </div>

                  <div className="supervision" onClick={e => e.stopPropagation()}>
                    {p.supervisor_detail ? (
                      <span className="meta-item">🧑‍🏫 {p.supervisor_detail.academic_title} {p.supervisor_detail.full_name}</span>
                    ) : !p.co_supervisor_detail && (
                      <span className="meta-item muted">Aucun encadreur rattaché</span>
                    )}
                    {p.review_comment && p.status === 'IN_PROGRESS' && (
                      <div className="review-note"><strong>Corrections demandées :</strong> {p.review_comment}</div>
                    )}
                    <div className="card-buttons">
                      {(p.status === 'DRAFT' || p.status === 'IN_PROGRESS') && (
                        <button className="btn-small primary" disabled={!p.supervisor && !p.co_supervisor}
                                title={p.supervisor || p.co_supervisor ? '' : 'Ajoutez un encadreur pour pouvoir soumettre'}
                                onClick={() => submit(p)}>📨 Soumettre à l'encadreur</button>
                      )}
                      {p.status === 'REVIEW' && <span className="waiting">⏳ En attente de relecture</span>}
                      {p.status !== 'ARCHIVED'
                        ? <button className="btn-small" onClick={() => archive(p)}>Archiver</button>
                        : <button className="btn-small" onClick={() => restore(p)}>Restaurer</button>}
                    </div>
                  </div>

                  <div className="project-card-footer">
                    <div className="project-meta">
                      {p.level && <span className="meta-item">📚 {LEVEL_LABELS[p.level]}</span>}
                      {p.university && <span className="meta-item">🏫 {p.university}</span>}
                      {p.academic_year && <span className="meta-item">📅 {p.academic_year}</span>}
                    </div>
                    <div className="project-actions">
                      <span className="chapter-count">{(p.chapters ?? []).filter(c => c.parent === null).length} chapitre(s)</span>
                      <span className="arrow">→</span>
                    </div>
                  </div>
                </div>
              ))}

              {filtered.length === 0 && (
                <div className="empty-state">
                  <div className="empty-icon">📝</div>
                  <h3>Aucun mémoire trouvé</h3>
                  <p>{search ? `Aucun résultat pour « ${search} »` : 'Commencez votre premier mémoire dès maintenant'}</p>
                  <button className="btn-primary" onClick={() => navigate('/projects/new')}>+ Créer un mémoire</button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
