import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { describeError } from '../../api/client';
import { chaptersApi, projectsApi } from '../../api/services';
import Layout from '../../components/Layout';
import { useToast } from '../../context/ToastContext';
import { wordCount } from '../../lib/format';
import type { Chapter, Project } from '../../lib/models';
import { PROJECT_STATUS_LABELS } from '../../lib/roles';
import CollaborationModal from './CollaborationModal';
import CommentsModal from './CommentsModal';
import CoverModal from './CoverModal';
import ExportModal from './ExportModal';
import ReferencesModal from './ReferencesModal';
import SettingsModal from './SettingsModal';
import VerifyModal from './VerifyModal';
import '../../styles/editor.css';

type ModalName = 'export' | 'references' | 'collaboration' | 'comments' | 'settings' | 'verify' | 'cover' | null;

const CHAPTER_STATUS: Record<string, string> = { draft: 'Brouillon', review: 'En révision', validated: 'Validé' };

/** Chapitres de premier niveau suivis de leurs sections, dans l'ordre. */
function outline(chapters: Chapter[]): { chapter: Chapter; depth: number; number: string }[] {
  const byParent = new Map<number | null, Chapter[]>();
  chapters.forEach(c => {
    const key = c.parent ?? null;
    byParent.set(key, [...(byParent.get(key) ?? []), c]);
  });
  byParent.forEach(list => list.sort((a, b) => a.order - b.order || a.id - b.id));
  const result: { chapter: Chapter; depth: number; number: string }[] = [];
  const walk = (parent: number | null, depth: number, prefix: string) => {
    (byParent.get(parent) ?? []).forEach((c, i) => {
      const number = prefix ? `${prefix}.${i + 1}` : String(i + 1);
      result.push({ chapter: c, depth, number });
      walk(c.id, depth + 1, number);
    });
  };
  walk(null, 0, '');
  return result;
}

export default function EditorPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const navigate = useNavigate();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [project, setProject] = useState<Project | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<{ title: string; content: string }>({ title: '', content: '' });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [modal, setModal] = useState<ModalName>(null);
  const pollTimer = useRef<number>();

  const selected = chapters.find(c => c.id === selectedId) ?? null;
  const dirty = !!selected && (draft.title !== selected.title || draft.content !== (selected.content ?? ''));
  const tree = useMemo(() => outline(chapters), [chapters]);
  const topLevelCount = chapters.filter(c => c.parent === null).length;

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setLoadError('');
    try {
      const [p, list] = await Promise.all([projectsApi.get(projectId), chaptersApi.list(projectId)]);
      setProject(p);
      setChapters(list);
      setSelectedId(prev => (prev && list.some(c => c.id === prev) ? prev : outline(list)[0]?.chapter.id ?? null));
    } catch (err) {
      setLoadError(describeError(err, 'Impossible de charger le mémoire.'));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (!projectId || Number.isNaN(projectId)) navigate('/projects', { replace: true });
    else load();
    return () => window.clearTimeout(pollTimer.current);
  }, [projectId, load, navigate]);

  // Retour de paiement Stripe
  useEffect(() => {
    const payment = searchParams.get('payment');
    if (!payment) return;
    if (payment === 'success') toast.success('Paiement reçu', "L'export de votre mémoire est débloqué.");
    else toast.warning('Paiement annulé');
    searchParams.delete('payment');
    setSearchParams(searchParams, { replace: true });
  }, [searchParams, setSearchParams, toast]);

  // Copie de travail du chapitre sélectionné
  useEffect(() => {
    if (selected) setDraft({ title: selected.title, content: selected.content ?? '' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  // Avertit avant de quitter la page avec des modifications non enregistrées.
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const select = (chapter: Chapter) => {
    if (chapter.id === selectedId) return;
    if (dirty && !window.confirm('Des modifications ne sont pas enregistrées. Changer de chapitre quand même ?')) return;
    setSelectedId(chapter.id);
  };

  const save = useCallback(async () => {
    if (!selected || !dirty || saving) return;
    if (!draft.title.trim()) {
      toast.error('Titre requis', 'Le chapitre doit avoir un titre.');
      return;
    }
    setSaving(true);
    try {
      const updated = await chaptersApi.update(selected.id, { title: draft.title.trim(), content: draft.content });
      setChapters(list => list.map(c => (c.id === updated.id ? updated : c)));
      setDraft({ title: updated.title, content: updated.content ?? '' });
      toast.success('Chapitre enregistré', `« ${updated.title} » (version ${updated.version})`);
    } catch (err) {
      toast.error('Erreur de sauvegarde', describeError(err, 'Impossible de sauvegarder le chapitre.'));
    } finally {
      setSaving(false);
    }
  }, [selected, dirty, saving, draft, toast]);

  // Ctrl+S / Cmd+S
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        save();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [save]);

  const addChapter = async (parent: Chapter | null = null) => {
    if (dirty && !window.confirm('Des modifications ne sont pas enregistrées. Continuer quand même ?')) return;
    const siblings = chapters.filter(c => (c.parent ?? null) === (parent?.id ?? null));
    const order = siblings.reduce((max, c) => Math.max(max, c.order), 0) + 1;
    try {
      const created = await chaptersApi.create({
        project: projectId, parent: parent?.id ?? null, order,
        title: parent ? `Section ${siblings.length + 1}` : `Chapitre ${topLevelCount + 1}`,
        content: '', type: parent ? 'section' : 'chapter', status: 'draft',
      });
      setChapters(list => [...list, created]);
      setSelectedId(created.id);
      setDraft({ title: created.title, content: '' });
    } catch (err) {
      toast.error('Erreur de création', describeError(err, 'Impossible de créer le chapitre.'));
    }
  };

  const removeChapter = async () => {
    if (!selected) return;
    const children = chapters.filter(c => c.parent === selected.id).length;
    const msg = children
      ? `Supprimer « ${selected.title} » et ses ${children} section(s) ? Cette action est irréversible.`
      : `Supprimer « ${selected.title} » ? Cette action est irréversible.`;
    if (!window.confirm(msg)) return;
    try {
      await chaptersApi.remove(selected.id);
      const removed = new Set<number>([selected.id]);
      let grew = true;
      while (grew) {
        grew = false;
        chapters.forEach(c => { if (c.parent && removed.has(c.parent) && !removed.has(c.id)) { removed.add(c.id); grew = true; } });
      }
      const remaining = chapters.filter(c => !removed.has(c.id));
      setChapters(remaining);
      setSelectedId(outline(remaining)[0]?.chapter.id ?? null);
      toast.success('Chapitre supprimé');
    } catch (err) {
      toast.error('Suppression impossible', describeError(err));
    }
  };

  const generatePlan = async () => {
    if (!project) return;
    setGenerating(true);
    const finish = (status: string, error: string | null) => {
      setGenerating(false);
      if (status === 'COMPLETED') {
        toast.success('Plan généré', "Vérifiez les références suggérées avant de les utiliser.");
        load();
      } else {
        toast.error('Génération échouée', error || 'La génération du plan a échoué.');
      }
    };
    try {
      const task = await projectsApi.generatePlan(project.id);
      if (task.status === 'COMPLETED' || task.status === 'FAILED') {
        finish(task.status, task.error);
        return;
      }
      // Worker Celery en production : interrogation du statut toutes les 3 secondes.
      const poll = async () => {
        try {
          const t = await projectsApi.aiTask(task.ai_task_id);
          if (t.status === 'COMPLETED' || t.status === 'FAILED') finish(t.status, t.error);
          else pollTimer.current = window.setTimeout(poll, 3000);
        } catch (err) {
          setGenerating(false);
          toast.error('Suivi impossible', describeError(err));
        }
      };
      pollTimer.current = window.setTimeout(poll, 3000);
    } catch (err) {
      setGenerating(false);
      toast.error('Génération impossible', describeError(err, 'Impossible de générer le plan.'));
    }
  };

  const canGeneratePlan = project?.status === 'DRAFT';

  return (
    <Layout>
      <div className="scope-editor">
        <div className="editor-page">
          <Link className="back-link" to="/projects">← Mes mémoires</Link>
          <span className="eyebrow">ÉDITEUR DE MÉMOIRE</span>

          {project && (
            <div className="title-row">
              <div>
                <h2>{project.title}</h2>
                {project.theme && <p className="project-theme">{project.theme}</p>}
                <p className="project-theme" style={{ marginTop: 4 }}>
                  Statut : <strong>{PROJECT_STATUS_LABELS[project.status]}</strong>
                  {project.supervisor_detail && <> · Encadreur : {project.supervisor_detail.full_name}</>}
                  {project.template_detail && <> · Modèle : {project.template_detail.name}</>}
                </p>
              </div>
              <div className="actions">
                <button type="button" className="secondary" onClick={() => setModal('cover')}>📄 Page de garde</button>
                <button type="button" className="secondary" onClick={() => setModal('settings')}>⚙ Paramètres</button>
                <button type="button" className="secondary" onClick={() => setModal('comments')}>💬 Commentaires</button>
                <button type="button" className="secondary" onClick={() => setModal('collaboration')}>👥 Collaborer</button>
                <button type="button" className="secondary" onClick={() => setModal('references')}>📚 Bibliographie</button>
                <button type="button" className="secondary" onClick={() => setModal('export')}>📥 Exporter</button>
                {canGeneratePlan && (
                  <button type="button" className="primary" disabled={generating} onClick={generatePlan}>
                    {generating ? 'Génération…' : '✦ Générer le plan avec IA'}
                  </button>
                )}
              </div>
            </div>
          )}

          {project?.review_comment && project.status === 'IN_PROGRESS' && (
            <div className="message error">↺ Corrections demandées par l'encadrement : {project.review_comment}</div>
          )}

          {loading && (
            <div className="loading"><div className="spinner" /><p>Chargement du mémoire...</p></div>
          )}

          {!loading && loadError && (
            <div className="error-container">
              <p>❌ {loadError}</p>
              <button className="primary" onClick={load}>Réessayer</button>
              <button className="secondary" onClick={() => navigate('/projects')} style={{ marginLeft: 10 }}>Retour aux mémoires</button>
            </div>
          )}

          {!loading && project && (
            <div className="editor-layout">
              <aside className="chapters">
                <div className="chapters-header">
                  <h3>Plan du mémoire</h3>
                  <button type="button" className="add-button" title="Ajouter un chapitre" aria-label="Ajouter un chapitre"
                          onClick={() => addChapter()}>+</button>
                </div>
                <div className="chapter-summary">📚 {topLevelCount} chapitre(s) · {chapters.length - topLevelCount} section(s)</div>

                {tree.length > 0 ? (
                  <div className="chapter-list">
                    {tree.map(({ chapter, depth, number }) => (
                      <button type="button" key={chapter.id}
                              className={`chapter-item${chapter.id === selectedId ? ' selected' : ''}`}
                              style={{ paddingLeft: 12 + depth * 16, fontSize: depth ? 13 : undefined }}
                              onClick={() => select(chapter)}>
                        <span className="chapter-number">{number}</span>
                        <span>{chapter.title}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="empty-chapters">
                    <p>Aucun chapitre n'a encore été créé.</p>
                    <button type="button" className="primary" onClick={() => addChapter()}>+ Créer le premier chapitre</button>
                  </div>
                )}
              </aside>

              <section className="workspace">
                {!selected && tree.length > 0 && (
                  <div className="empty-chapters">
                    <h3>Sélectionnez un chapitre</h3>
                    <p>Choisissez un chapitre dans la liste de gauche pour commencer à rédiger.</p>
                  </div>
                )}

                {!selected && tree.length === 0 && (
                  <div className="empty-chapters">
                    <h3>Commencez votre mémoire</h3>
                    <p>Créez un chapitre ou générez automatiquement un plan avec l'intelligence artificielle.</p>
                    {canGeneratePlan && (
                      <button type="button" className="primary" disabled={generating} onClick={generatePlan}>
                        {generating ? 'Génération…' : '✦ Générer le plan'}
                      </button>
                    )}
                  </div>
                )}

                {selected && (
                  <div>
                    <div className="workspace-header">
                      <div><h3>{draft.title || 'Sans titre'}</h3></div>
                      <span className="status">
                        {CHAPTER_STATUS[selected.status] ?? selected.status} · v{selected.version}{dirty ? ' · non enregistré' : ''}
                      </span>
                    </div>

                    <div className="field-label">
                      <label htmlFor="chapterTitle">Titre</label>
                      <input id="chapterTitle" type="text" value={draft.title} maxLength={255}
                             onChange={e => setDraft(d => ({ ...d, title: e.target.value }))} placeholder="Titre du chapitre" />
                    </div>

                    <div className="field-label">
                      <label htmlFor="chapterContent">Contenu</label>
                      <textarea id="chapterContent" className="content-editor" value={draft.content}
                                onChange={e => setDraft(d => ({ ...d, content: e.target.value }))}
                                placeholder="Commencez à rédiger votre chapitre..." />
                    </div>

                    <div className="editor-actions" style={{ flexWrap: 'wrap', alignItems: 'center' }}>
                      <span style={{ marginRight: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
                        {wordCount(draft.content)} mots · Ctrl+S pour enregistrer
                      </span>
                      {selected.parent === null && (
                        <button type="button" className="secondary" onClick={() => addChapter(selected)}>+ Section</button>
                      )}
                      <button type="button" className="secondary" disabled={!draft.content.trim()} onClick={() => setModal('verify')}>
                        ✦ Vérifier avec l'IA
                      </button>
                      <button type="button" className="secondary" onClick={removeChapter}>🗑 Supprimer</button>
                      <button type="button" className="primary" disabled={saving || !dirty} onClick={save}>
                        {saving ? 'Sauvegarde…' : '✓ Sauvegarder'}
                      </button>
                    </div>
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      </div>

      {project && modal === 'export' && <ExportModal project={project} onClose={() => setModal(null)} />}
      {project && modal === 'references' && <ReferencesModal projectId={project.id} onClose={() => setModal(null)} />}
      {project && modal === 'collaboration' && <CollaborationModal projectId={project.id} onClose={() => setModal(null)} />}
      {project && modal === 'comments' && (
        <CommentsModal project={project} chapters={chapters} onClose={() => setModal(null)} />
      )}
      {project && modal === 'settings' && (
        <SettingsModal project={project} onClose={() => setModal(null)} onSaved={p => { setProject(p); setModal(null); }} />
      )}
      {project && modal === 'cover' && (
        <CoverModal project={project} onClose={() => setModal(null)} onEditSettings={() => setModal('settings')} />
      )}
      {modal === 'verify' && selected && (
        <VerifyModal text={draft.content} title={draft.title} onClose={() => setModal(null)} />
      )}
    </Layout>
  );
}
