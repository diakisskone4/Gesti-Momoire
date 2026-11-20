import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { BookMarked, Download, FileText, MessageSquare, Settings, Users } from 'lucide-react';

import { ApiError, describeError } from '../../api/client';
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
import FigureTools from './FigureTools';
import ReferencesModal from './ReferencesModal';
import SettingsModal from './SettingsModal';
import VerifyModal from './VerifyModal';
import '../../styles/editor.css';

type ModalName = 'export' | 'references' | 'collaboration' | 'comments' | 'settings' | 'verify' | 'cover' | null;

const CHAPTER_STATUS: Record<string, string> = { draft: 'Brouillon', review: 'En révision', validated: 'Validé' };

// Contenu « vide » : rien, ou seulement les conseils du modèle (même règle que le serveur).
const PLACEHOLDER = /^\s*(\[(Conseil du modèle|Sous-parties prévues)[^\]]*\]\s*)*$/;
const isPlaceholder = (content: string | null) => !content || PLACEHOLDER.test(content);
const normalize = (title: string) => title.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const isPersonalPage = (c: Chapter) => /dedicace|remerciement/.test(normalize(c.title));
const isTocPage = (c: Chapter) => /^(sommaire|table des matieres)/.test(normalize(c.title).trim());
/** Pages établies à partir du texte des chapitres : résumé, sigles, liste des tableaux et figures
 *  (liminaires) et annexes (fin). */
const isTextBasedPage = (c: Chapter) =>
  (c.type === 'preliminary' && /resume|abstract|sigle|abreviation|tableau|figure/.test(normalize(c.title)))
  || (c.type === 'back' && /annexe/.test(normalize(c.title)));

/** Une partie a-t-elle encore du contenu à rédiger (elle-même ou l'une de ses sections) ? */
function needsWriting(chapters: Chapter[], id: number): boolean {
  const part = chapters.find(c => c.id === id);
  if (!part) return false;
  if (isTextBasedPage(part)) return isPlaceholder(part.content);
  return isPlaceholder(part.content) || chapters.some(c => c.parent === id && isPlaceholder(c.content));
}

const MAX_ATTEMPTS = 3; // une réponse de l'IA coupée avant la fin est reprise là où elle s'est arrêtée

/** Parties que l'IA peut rédiger, dans l'ordre : les chapitres d'abord, puis le résumé, les sigles et les
 *  annexes (établis à partir du texte des chapitres). Jamais la dédicace ni les remerciements. */
export function aiWritingQueue(chapters: Chapter[]): Chapter[] {
  const top = chapters.filter(c => c.parent === null).sort((a, b) => a.order - b.order || a.id - b.id);
  const sections = (id: number) => chapters.filter(c => c.parent === id);
  const body = top.filter(c => !isPersonalPage(c) && !isTocPage(c) && c.type !== 'preliminary' && c.type !== 'back'
    && (isPlaceholder(c.content) || sections(c.id).some(s => isPlaceholder(s.content))));
  const pages = top.filter(c => !isPersonalPage(c) && isTextBasedPage(c) && isPlaceholder(c.content));
  return [...body, ...pages];
}

interface AiRun { done: number; total: number; current: string }

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
  const contentRef = useRef<HTMLTextAreaElement>(null);
  const [generating, setGenerating] = useState(false);
  const [modal, setModal] = useState<ModalName>(null);
  const [aiRun, setAiRun] = useState<AiRun | null>(null);
  const stopAi = useRef(false);
  const pollTimer = useRef<number>();

  const selected = chapters.find(c => c.id === selectedId) ?? null;
  const dirty = !!selected && (draft.title !== selected.title || draft.content !== (selected.content ?? ''));
  const tree = useMemo(() => outline(chapters), [chapters]);
  // Sommaire : généré automatiquement à l'export. Affiché dans le plan juste avant le corps du mémoire
  // (ou à la place d'une partie « Sommaire » ajoutée par l'étudiant).
  const [tocOpen, setTocOpen] = useState(false);
  const hasTocChapter = tree.some(({ chapter, depth }) => depth === 0 && isTocPage(chapter));
  const tocIndex = (() => {
    const i = tree.findIndex(({ chapter, depth }) => depth === 0 && chapter.type !== 'preliminary' && !isTocPage(chapter));
    return i === -1 ? tree.length : i;
  })();
  const tocPreview = tree.filter(({ chapter, depth }) => depth <= 1 && !isTocPage(chapter));
  const topLevelCount = chapters.filter(c => c.parent === null).length;
  const aiQueue = useMemo(() => aiWritingQueue(chapters), [chapters]);
  // Lus pendant la rédaction IA (boucle asynchrone) : valeurs à jour sans relancer la boucle.
  const dirtyRef = useRef(false);
  dirtyRef.current = dirty;
  const selectedIdRef = useRef<number | null>(null);
  selectedIdRef.current = selectedId;

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
    if (isTocPage(chapter) && chapter.parent === null) {
      openToc();
      return;
    }
    if (chapter.id === selectedId && !tocOpen) return;
    if (dirty && !window.confirm('Des modifications ne sont pas enregistrées. Changer de chapitre quand même ?')) return;
    setTocOpen(false);
    setSelectedId(chapter.id);
  };

  const openToc = () => {
    if (tocOpen) return;
    if (dirty && !window.confirm('Des modifications ne sont pas enregistrées. Changer de chapitre quand même ?')) return;
    setTocOpen(true);
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
      ? `Placer « ${selected.title} » et ses ${children} section(s) dans la corbeille ? Restaurable pendant 30 jours.`
      : `Placer « ${selected.title} » dans la corbeille ? Restaurable pendant 30 jours.`;
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
      toast.success('Chapitre placé dans la corbeille', 'Restaurable depuis le menu « Corbeille ».');
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
  const canWriteWithAi = !!project && !['REVIEW', 'VALIDATED'].includes(project.status) && aiQueue.length > 0;

  /** Rédige tout le plan avec l'IA, partie par partie (une requête courte par partie). */
  const writeWithAi = async () => {
    if (!project || aiRun) return;
    if (dirty) {
      toast.warning("Enregistrez d'abord", 'Sauvegardez le chapitre en cours avant de lancer la rédaction.');
      return;
    }
    const queue = aiWritingQueue(chapters);
    if (!queue.length) return;
    if (!window.confirm(
      `L'IA va rédiger ${queue.length} partie(s) de votre mémoire, l'une après l'autre (environ une minute chacune).\n\n`
      + 'La dédicace et les remerciements ne sont pas rédigés, et le texte que vous avez déjà écrit '
      + "n'est jamais remplacé.\n\nContinuer ?",
    )) return;

    stopAi.current = false;
    let written = 0;
    const failed: string[] = [];
    let fatal = false;
    for (let i = 0; i < queue.length && !stopAi.current && !fatal; i++) {
      const part = queue[i];
      let complete = false;
      for (let attempt = 1; attempt <= MAX_ATTEMPTS && !complete && !stopAi.current; attempt++) {
        setAiRun({ done: i, total: queue.length, current: attempt === 1 ? part.title : `${part.title} (suite)` });
        try {
          const res = await chaptersApi.generateContent(part.id);
          setChapters(res.chapters);
          const shown = res.chapters.find(c => c.id === selectedIdRef.current);
          if (shown && !dirtyRef.current) setDraft({ title: shown.title, content: shown.content ?? '' });
          complete = !needsWriting(res.chapters, part.id);
        } catch (err) {
          const status = err instanceof ApiError ? err.status : 0;
          failed.push(`${part.title} : ${describeError(err, 'Rédaction impossible.')}`);
          // Serveur injoignable, modèle non acheté, IA saturée ou indisponible : inutile de continuer.
          fatal = [0, 402, 429, 503].includes(status);
          break;
        }
      }
      if (complete) written += 1;
      else if (!stopAi.current && !fatal && !failed.some(f => f.startsWith(`${part.title} :`))) {
        failed.push(`${part.title} : rédaction incomplète, relancez le bouton pour terminer`);
      }
    }
    const stopped = stopAi.current;
    setAiRun(null);
    if (written) {
      toast.success('Rédaction terminée', `${written} partie(s) rédigée(s). Relisez et complétez les mentions [source à compléter].`);
    }
    if (failed.length) toast.error("Certaines parties n'ont pas été rédigées", failed.join(' · '));
    else if (stopped) toast.info('Rédaction arrêtée', 'Vous pourrez relancer la rédaction des parties restantes.');
  };

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
              <div className="actions editor-tools">
                <button type="button" className="secondary" onClick={() => setModal('cover')}><FileText size={17} /><span>Page de garde</span></button>
                <button type="button" className="secondary" onClick={() => setModal('settings')}><Settings size={17} /><span>Paramètres</span></button>
                <button type="button" className="secondary" onClick={() => setModal('comments')}><MessageSquare size={17} /><span>Commentaires</span></button>
                <button type="button" className="secondary" onClick={() => setModal('collaboration')}><Users size={17} /><span>Collaborer</span></button>
                <button type="button" className="secondary" onClick={() => setModal('references')}><BookMarked size={17} /><span>Bibliographie</span></button>
                <button type="button" className="secondary" onClick={() => setModal('export')}><Download size={17} /><span>Exporter</span></button>
                {canGeneratePlan && (
                  <button type="button" className="primary" disabled={generating || !!aiRun} onClick={generatePlan}>
                    {generating ? 'Génération…' : '✦ Générer le plan avec IA'}
                  </button>
                )}
                {canWriteWithAi && (
                  <button type="button" className="primary" disabled={!!aiRun || generating} onClick={writeWithAi}
                          title="Rédige le contenu de tout le plan, sauf la dédicace et les remerciements">
                    {aiRun ? 'Rédaction en cours…' : "✦ Rédiger le mémoire avec l'IA"}
                  </button>
                )}
              </div>
            </div>
          )}

          {aiRun && (
            <div className="ai-progress" role="status" aria-live="polite">
              <div className="ai-progress-head">
                <strong>Rédaction par l'IA : partie {aiRun.done + 1} sur {aiRun.total}</strong>
                <button type="button" className="secondary" onClick={() => { stopAi.current = true; }}>
                  Arrêter après cette partie
                </button>
              </div>
              <p>En cours : « {aiRun.current} »</p>
              <div className="ai-progress-bar" aria-hidden="true">
                <i style={{ width: `${Math.max(4, (aiRun.done / aiRun.total) * 100)}%` }} />
              </div>
              <small>Gardez cette page ouverte. La dédicace, les remerciements et votre propre texte ne sont pas modifiés.</small>
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
                    {tree.map(({ chapter, depth, number }, index) => (
                      <Fragment key={chapter.id}>
                        {!hasTocChapter && index === tocIndex && (
                          <button type="button" className={`chapter-item toc-item${tocOpen ? ' selected' : ''}`}
                                  onClick={openToc} title="Généré automatiquement à l'export">
                            <span className="chapter-number">≡</span>
                            <span>Sommaire <small>(automatique)</small></span>
                          </button>
                        )}
                        <button type="button"
                                className={`chapter-item${(isTocPage(chapter) && depth === 0 ? tocOpen : chapter.id === selectedId && !tocOpen) ? ' selected' : ''}`}
                                style={{ paddingLeft: 12 + depth * 16, fontSize: depth ? 13 : undefined }}
                                onClick={() => select(chapter)}>
                          <span className="chapter-number">{number}</span>
                          <span>{chapter.title}</span>
                        </button>
                      </Fragment>
                    ))}
                    {!hasTocChapter && tocIndex === tree.length && (
                      <button type="button" className={`chapter-item toc-item${tocOpen ? ' selected' : ''}`} onClick={openToc}>
                        <span className="chapter-number">≡</span>
                        <span>Sommaire <small>(automatique)</small></span>
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="empty-chapters">
                    <p>Aucun chapitre n'a encore été créé.</p>
                    <button type="button" className="primary" onClick={() => addChapter()}>+ Créer le premier chapitre</button>
                  </div>
                )}
              </aside>

              <section className="workspace">
                {tocOpen && (
                  <div className="toc-preview">
                    <div className="workspace-header">
                      <div><h3>Sommaire</h3></div>
                      <span className="status">Généré automatiquement</span>
                    </div>
                    <p className="toc-note">
                      Le sommaire est créé automatiquement à l'export (Word et PDF), à partir de votre plan, avec les
                      numéros de page : chiffres romains pour les pages liminaires, puis 1, 2, 3… à partir de
                      l'introduction. Il se met à jour tout seul si vous modifiez les titres. Dans Word, acceptez la
                      mise à jour des champs à l'ouverture pour afficher les numéros de page.
                    </p>
                    <ol className="toc-list">
                      {tocPreview.map(({ chapter, depth, number }) => (
                        <li key={chapter.id} className={depth ? 'toc-sub' : 'toc-main'}>
                          <span className="toc-number">{number}</span>
                          <span>{chapter.title}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {!tocOpen && !selected && tree.length > 0 && (
                  <div className="empty-chapters">
                    <h3>Sélectionnez un chapitre</h3>
                    <p>Choisissez un chapitre dans la liste de gauche pour commencer à rédiger.</p>
                  </div>
                )}

                {!tocOpen && !selected && tree.length === 0 && (
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

                {!tocOpen && selected && (
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
                      <textarea id="chapterContent" ref={contentRef} className="content-editor" value={draft.content}
                                onChange={e => setDraft(d => ({ ...d, content: e.target.value }))}
                                placeholder="Commencez à rédiger votre chapitre..." />
                    </div>

                    {project && (
                      <FigureTools projectId={project.id} content={draft.content}
                                   cursor={() => contentRef.current?.selectionStart ?? draft.content.length}
                                   onChange={content => setDraft(d => ({ ...d, content }))} />
                    )}

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
