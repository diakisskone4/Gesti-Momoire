import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArcElement, Chart, DoughnutController, Tooltip } from 'chart.js';
import {
  AlertTriangle, ArrowRight, BookOpen, CheckCircle2, Circle, Clock, FilePlus2, FileText, GraduationCap,
  LayoutTemplate, PenLine, RefreshCw, Send, Sparkles, Target, Trash2, UserRound,
} from 'lucide-react';

import { describeError } from '../../api/client';
import { projectsApi } from '../../api/services';
import Layout from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { formatDate, formatNumber, timeAgo } from '../../lib/format';
import type { Project } from '../../lib/models';
import { projectProgress } from '../../lib/progress';
import { LEVEL_LABELS, PROJECT_STATUS_LABELS } from '../../lib/roles';
import '../../styles/dashboard-pro.css';

Chart.register(DoughnutController, ArcElement, Tooltip);

/** Classes de badge de statut (réutilisées par la page « Mes mémoires »). */
export const STATUS_CLASS: Record<string, string> = {
  DRAFT: 'status-draft', IN_PROGRESS: 'status-progress', REVIEW: 'status-review',
  VALIDATED: 'status-completed', COMPLETED: 'status-completed', ARCHIVED: 'status-draft',
};

const STATUS_ORDER = ['DRAFT', 'IN_PROGRESS', 'REVIEW', 'VALIDATED'] as const;
const STATUS_COLORS: Record<string, string> = {
  DRAFT: '#94a3b8', IN_PROGRESS: '#2563eb', REVIEW: '#d97706', VALIDATED: '#0f766e',
};

function greeting(): string {
  const hour = new Date().getHours();
  return hour < 12 ? 'Bonjour' : hour < 18 ? 'Bon après-midi' : 'Bonsoir';
}

interface Step { done: boolean; label: string; hint: string; to?: string; }

function nextSteps(p: Project): Step[] {
  const progress = projectProgress(p);
  return [
    { done: !!(p.supervisor || p.co_supervisor), label: 'Rattacher un encadreur', hint: 'Nécessaire pour soumettre le mémoire',
      to: `/projects/${p.id}/editor` },
    { done: !!p.template_detail?.paid, label: 'Choisir un modèle de mémoire', hint: 'Page de garde + génération IA du plan et du contenu',
      to: '/modeles' },
    { done: progress.chaptersTotal > 0, label: 'Établir le plan', hint: 'Avec le modèle ou générez-le avec l\'IA',
      to: `/projects/${p.id}/editor` },
    { done: progress.percent >= 50, label: 'Rédiger la moitié du mémoire', hint: `${formatNumber(progress.words)} / ${formatNumber(progress.targetWords)} mots`,
      to: `/projects/${p.id}/editor` },
    { done: ['REVIEW', 'VALIDATED', 'COMPLETED'].includes(p.status), label: 'Soumettre à l\'encadreur', hint: 'Depuis « Mes mémoires »',
      to: '/projects' },
  ];
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { isDark } = useTheme();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const chartRef = useRef<HTMLCanvasElement>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    return projectsApi.list('mine')
      .then(setProjects)
      .catch(err => setError(describeError(err, 'Impossible de charger le tableau de bord.')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { void load(); }, [load]);

  const rows = useMemo(() => projects.map(p => ({ project: p, progress: projectProgress(p) })), [projects]);
  const current = rows[0];
  const totals = useMemo(() => ({
    active: projects.filter(p => p.status !== 'ARCHIVED').length,
    words: rows.reduce((s, r) => s + r.progress.words, 0),
    avg: rows.length ? Math.round(rows.reduce((s, r) => s + r.progress.percent, 0) / rows.length) : 0,
    review: projects.filter(p => p.status === 'REVIEW').length,
    validated: projects.filter(p => p.status === 'VALIDATED' || p.status === 'COMPLETED').length,
    changes: projects.filter(p => p.status === 'IN_PROGRESS' && p.review_comment).length,
  }), [projects, rows]);

  const statusCounts = STATUS_ORDER.map(s => ({ status: s, count: projects.filter(p => p.status === s || (s === 'VALIDATED' && p.status === 'COMPLETED')).length }));

  useEffect(() => {
    if (!chartRef.current || !projects.length) return;
    const chart = new Chart(chartRef.current, {
      type: 'doughnut',
      data: {
        labels: statusCounts.map(s => PROJECT_STATUS_LABELS[s.status]),
        datasets: [{
          data: statusCounts.map(s => s.count),
          backgroundColor: statusCounts.map(s => STATUS_COLORS[s.status]),
          borderWidth: 2,
          borderColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-card').trim() || '#fff',
        }],
      },
      options: { responsive: true, maintainAspectRatio: false, cutout: '72%', plugins: { legend: { display: false } } },
    });
    return () => chart.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projects, isDark]);

  const activity = useMemo(() => projects
    .flatMap(p => [
      { date: p.updated_at, text: `Mise à jour de « ${p.title} »`, icon: PenLine },
      ...(p.submitted_at ? [{ date: p.submitted_at, text: `« ${p.title} » soumis pour relecture`, icon: Send }] : []),
      ...(p.validated_at ? [{ date: p.validated_at, text: `« ${p.title} » validé`, icon: CheckCircle2 }] : []),
      { date: p.created_at, text: `Création de « ${p.title} »`, icon: FilePlus2 },
    ])
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    .slice(0, 6), [projects]);

  const today = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());

  return (
    <Layout onRefresh={load}>
      <div className="scope-dash">
        <header className="dash-head">
          <div>
            <p className="dash-date">{today}</p>
            <h1>{greeting()}, {user?.first_name || 'cher étudiant'}</h1>
            <p className="dash-sub">Suivez l'avancement de vos mémoires et reprenez là où vous vous êtes arrêté.</p>
          </div>
          <div className="dash-actions hide-mobile">
            <button className="dash-btn ghost" onClick={load} aria-label="Actualiser"><RefreshCw size={16} /> Actualiser</button>
            <Link className="dash-btn ghost" to="/modeles"><LayoutTemplate size={16} /> Modèles</Link>
            <Link className="dash-btn primary" to="/projects/new"><FilePlus2 size={16} /> Nouveau mémoire</Link>
          </div>
        </header>

        {/* Téléphone : raccourcis en tuiles, comme l'écran d'accueil d'une application. */}
        <nav className="quick-actions show-mobile" aria-label="Raccourcis">
          <Link to="/projects/new" className="qa primary"><span><FilePlus2 size={20} /></span>Nouveau</Link>
          <Link to="/modeles" className="qa"><span><LayoutTemplate size={20} /></span>Modèles</Link>
          <Link to="/assistant" className="qa"><span><Sparkles size={20} /></span>Assistant</Link>
          <Link to="/corbeille" className="qa"><span><Trash2 size={20} /></span>Corbeille</Link>
        </nav>

        {loading && <div className="dash-state"><span className="dash-spinner" /> Chargement du tableau de bord…</div>}
        {error && !loading && (
          <div className="dash-state error"><AlertTriangle size={18} /> {error}
            <button className="dash-btn ghost" onClick={load}>Réessayer</button></div>
        )}

        {!loading && !error && projects.length === 0 && (
          <section className="dash-empty">
            <GraduationCap size={40} strokeWidth={1.5} />
            <h2>Commencez votre premier mémoire</h2>
            <p>Créez votre mémoire, choisissez un modèle aux normes universitaires et laissez l'IA générer le plan et une première version du contenu.</p>
            <div className="dash-actions" style={{ justifyContent: 'center' }}>
              <Link className="dash-btn primary" to="/projects/new"><FilePlus2 size={16} /> Créer un mémoire</Link>
              <Link className="dash-btn ghost" to="/modeles"><LayoutTemplate size={16} /> Découvrir les modèles</Link>
            </div>
          </section>
        )}

        {!loading && !error && projects.length > 0 && (
          <>
            <section className="kpis" aria-label="Indicateurs">
              <Kpi icon={BookOpen} label="Mémoires actifs" value={formatNumber(totals.active)}
                   foot={`${projects.length - totals.active} archivé(s)`} />
              <Kpi icon={PenLine} label="Mots rédigés" value={formatNumber(totals.words)}
                   foot={`≈ ${formatNumber(Math.round(totals.words / 300))} pages`} />
              <Kpi icon={Target} label="Progression moyenne" value={`${totals.avg} %`} foot="par rapport aux pages visées" bar={totals.avg} />
              <Kpi icon={Send} label="En relecture" value={formatNumber(totals.review)}
                   foot={totals.changes ? `${totals.changes} correction(s) demandée(s)` : `${totals.validated} validé(s)`}
                   tone={totals.changes ? 'warn' : undefined} />
            </section>

            <div className="dash-grid">
              <div className="dash-main">
                {current && (
                  <section className="card focus">
                    <div className="card-head">
                      <div>
                        <span className="card-kicker">Mémoire en cours</span>
                        <h2>{current.project.title}</h2>
                        {current.project.theme && <p className="muted clamp">{current.project.theme}</p>}
                      </div>
                      <span className={`pill ${current.project.status}`}>{PROJECT_STATUS_LABELS[current.project.status]}</span>
                    </div>

                    {current.project.review_comment && current.project.status === 'IN_PROGRESS' && (
                      <div className="callout warn"><AlertTriangle size={16} />
                        <span><strong>Corrections demandées :</strong> {current.project.review_comment}</span></div>
                    )}

                    <div className="focus-stats">
                      <div>
                        <span className="label">Avancement</span>
                        <strong>{current.progress.percent} %</strong>
                        <div className="bar"><i style={{ width: `${current.progress.percent}%` }} /></div>
                        <small>{formatNumber(current.progress.words)} / {formatNumber(current.progress.targetWords)} mots</small>
                      </div>
                      <div>
                        <span className="label">Chapitres entamés</span>
                        <strong>{current.progress.chaptersStarted} / {current.progress.chaptersTotal}</strong>
                        <small>{current.progress.emptyBlocks} partie(s) à rédiger</small>
                      </div>
                      <div>
                        <span className="label">Encadrement</span>
                        <strong className="small-strong"><UserRound size={15} />
                          {current.project.supervisor_detail?.full_name ?? 'Non rattaché'}</strong>
                        <small>{current.project.template_detail ? `Modèle : ${current.project.template_detail.name}` : 'Aucun modèle'}</small>
                      </div>
                    </div>

                    <div className="focus-foot">
                      <span className="muted"><Clock size={14} /> Modifié {timeAgo(current.project.updated_at).toLowerCase()}</span>
                      <button className="dash-btn primary" onClick={() => navigate(`/projects/${current.project.id}/editor`)}>
                        Continuer la rédaction <ArrowRight size={16} />
                      </button>
                    </div>
                  </section>
                )}

                <section className="card">
                  <div className="card-head">
                    <h2 className="card-title">Mes mémoires</h2>
                    <Link to="/projects" className="link">Tout voir <ArrowRight size={14} /></Link>
                  </div>
                  {/* Téléphone : chaque mémoire est un widget (titre, statut, avancement). */}
                  <ul className="memo-widgets show-mobile">
                    {rows.slice(0, 6).map(({ project: p, progress }) => (
                      <li key={p.id}>
                        <Link to={`/projects/${p.id}/editor`} className="memo-widget">
                          <span className="mw-icon"><FileText size={18} /></span>
                          <span className="mw-body">
                            <strong>{p.title}</strong>
                            <span className="mw-meta">
                              <span className={`pill ${p.status}`}>{PROJECT_STATUS_LABELS[p.status]}</span>
                              <small>{formatDate(p.updated_at)}</small>
                            </span>
                            <span className="mw-progress">
                              <span className="bar small"><i style={{ width: `${progress.percent}%` }} /></span>
                              <small>{progress.percent} %</small>
                            </span>
                          </span>
                          <ArrowRight size={16} className="mw-go" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <div className="table-scroll hide-mobile">
                    <table className="dash-table">
                      <thead>
                        <tr><th>Mémoire</th><th>Statut</th><th>Avancement</th><th className="num">Chapitres</th><th>Modifié</th><th /></tr>
                      </thead>
                      <tbody>
                        {rows.slice(0, 6).map(({ project: p, progress }) => (
                          <tr key={p.id}>
                            <td>
                              <Link to={`/projects/${p.id}/editor`} className="row-title"><FileText size={16} /> {p.title}</Link>
                              <small className="muted">{LEVEL_LABELS[p.level]}{p.university ? ` · ${p.university}` : ''}</small>
                            </td>
                            <td><span className={`pill ${p.status}`}>{PROJECT_STATUS_LABELS[p.status]}</span></td>
                            <td className="progress-cell">
                              <div className="bar small"><i style={{ width: `${progress.percent}%` }} /></div>
                              <span>{progress.percent} %</span>
                            </td>
                            <td className="num">{progress.chaptersTotal}</td>
                            <td className="nowrap">{formatDate(p.updated_at)}</td>
                            <td><Link to={`/projects/${p.id}/editor`} className="icon-link" aria-label={`Ouvrir ${p.title}`}><ArrowRight size={16} /></Link></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>

              <aside className="dash-side">
                {current && (
                  <section className="card">
                    <h2 className="card-title">Prochaines étapes</h2>
                    <ul className="steps">
                      {nextSteps(current.project).map(step => (
                        <li key={step.label} className={step.done ? 'done' : ''}>
                          {step.done ? <CheckCircle2 size={18} /> : <Circle size={18} />}
                          <div>
                            {step.to && !step.done ? <Link to={step.to}>{step.label}</Link> : <span>{step.label}</span>}
                            <small>{step.hint}</small>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                <section className="card">
                  <h2 className="card-title">Répartition par statut</h2>
                  <div className="donut">
                    <canvas ref={chartRef} role="img" aria-label="Répartition des mémoires par statut" />
                    <div className="donut-center"><strong>{projects.length}</strong><span>mémoires</span></div>
                  </div>
                  <ul className="legend">
                    {statusCounts.map(s => (
                      <li key={s.status}><i style={{ background: STATUS_COLORS[s.status] }} />
                        {PROJECT_STATUS_LABELS[s.status]}<strong>{s.count}</strong></li>
                    ))}
                  </ul>
                </section>

                <section className="card">
                  <h2 className="card-title">Activité récente</h2>
                  <ul className="timeline">
                    {activity.map((a, i) => (
                      <li key={i}><span className="t-icon"><a.icon size={14} /></span>
                        <div><p>{a.text}</p><small>{timeAgo(a.date)}</small></div></li>
                    ))}
                  </ul>
                </section>

                <Link to="/assistant" className="card promo">
                  <Sparkles size={20} />
                  <div><strong>Assistant IA</strong><small>Reformuler, résumer, traduire un passage</small></div>
                  <ArrowRight size={16} />
                </Link>
              </aside>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}

function Kpi({ icon: Icon, label, value, foot, bar, tone }: {
  icon: typeof BookOpen; label: string; value: string; foot: string; bar?: number; tone?: 'warn';
}) {
  return (
    <div className={`kpi${tone ? ` ${tone}` : ''}`}>
      <div className="kpi-top"><span className="kpi-label">{label}</span><span className="kpi-icon"><Icon size={18} /></span></div>
      <strong className="kpi-value">{value}</strong>
      {bar !== undefined && <div className="bar small"><i style={{ width: `${bar}%` }} /></div>}
      <span className="kpi-foot">{foot}</span>
    </div>
  );
}
