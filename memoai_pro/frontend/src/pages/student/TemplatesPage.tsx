import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { describeError } from '../../api/client';
import { modelesApi, projectsApi } from '../../api/services';
import CoverFrame from '../../components/CoverFrame';
import Layout from '../../components/Layout';
import Modal from '../../components/Modal';
import { useToast } from '../../context/ToastContext';
import { formatDate, formatPrice } from '../../lib/format';
import type { MemoirTemplate, PaymentOptions, Project, TemplatePurchase } from '../../lib/models';
import MobileMoneyModal from './MobileMoneyModal';
import '../../styles/workspace.css';

type LevelFilter = 'ALL' | 'LICENCE' | 'MASTER' | 'DOCTORAT' | 'OWNED';

const FILTERS: { key: LevelFilter; label: string }[] = [
  { key: 'ALL', label: 'Tous' },
  { key: 'LICENCE', label: 'Licence' },
  { key: 'MASTER', label: 'Master' },
  { key: 'DOCTORAT', label: 'Doctorat' },
  { key: 'OWNED', label: 'Mes modèles' },
];

const PURCHASE_STATUS: Record<string, string> = {
  PENDING: 'En attente de paiement', SUBMITTED: 'En vérification', PAID: 'Payé', FAILED: 'Échoué', CANCELLED: 'Annulé / expiré',
};

/** Catalogue des modèles de mémoire payants (mobile money direct, ou page Jɛmɛnipay selon le serveur). */
export default function TemplatesPage() {
  const toast = useToast();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [templates, setTemplates] = useState<MemoirTemplate[] | null>(null);
  const [covers, setCovers] = useState<Record<string, string>>({});
  const [purchases, setPurchases] = useState<TemplatePurchase[]>([]);
  const [filter, setFilter] = useState<LevelFilter>('ALL');
  const [error, setError] = useState('');
  const [buying, setBuying] = useState<string | null>(null);
  const [detail, setDetail] = useState<MemoirTemplate | null>(null);
  const [applyTo, setApplyTo] = useState<MemoirTemplate | null>(null);
  const [returnState, setReturnState] = useState<{ status: 'checking' | 'paid' | 'pending' | 'failed'; name?: string } | null>(null);
  const [options, setOptions] = useState<PaymentOptions | null>(null);
  const [paying, setPaying] = useState<TemplatePurchase | null>(null);
  const pollTimer = useRef<number>();

  const load = useCallback(async () => {
    setError('');
    try {
      const [list, mine] = await Promise.all([modelesApi.list(), modelesApi.purchases()]);
      setTemplates(list);
      setPurchases(mine);
      list.forEach(t => {
        modelesApi.cover(t.slug).then(r => setCovers(c => ({ ...c, [t.slug]: r.html }))).catch(() => undefined);
      });
    } catch (err) {
      setError(describeError(err, 'Impossible de charger les modèles.'));
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { modelesApi.paymentOptions().then(setOptions).catch(() => undefined); }, []);

  /** Ouvre le paiement d'un achat : fenêtre mobile money ou page Jɛmɛnipay. */
  const openPayment = async (purchase: TemplatePurchase) => {
    if (purchase.provider !== 'mobile_money') {
      window.location.assign(purchase.checkout_url);
      return;
    }
    const current = options?.mode === 'mobile_money' ? options : await modelesApi.paymentOptions();
    if (current.mode !== 'mobile_money') throw new Error("Ce mode de paiement n'est plus proposé. Relancez l'achat.");
    setOptions(current);
    setDetail(null);
    setBuying(null);
    setPaying(purchase);
  };

  const paymentUpdated = (purchase: TemplatePurchase) => {
    setPaying(purchase);
    if (purchase.status === 'PAID') toast.success('Paiement confirmé', `Le modèle « ${purchase.template_name} » est débloqué.`);
    if (purchase.status !== paying?.status) load();
  };

  // Retour de la page de paiement Jɛmɛnipay : /modeles?achat=<id>&transaction_id=…
  useEffect(() => {
    const id = parseInt(searchParams.get('achat') ?? '', 10);
    if (!id) return;
    searchParams.delete('achat');
    searchParams.delete('transaction_id');
    setSearchParams(searchParams, { replace: true });
    setReturnState({ status: 'checking' });

    let attempts = 0;
    const check = async () => {
      attempts += 1;
      try {
        const p = await modelesApi.verify(id);
        if (p.status === 'PAID') {
          setReturnState({ status: 'paid', name: p.template_name });
          toast.success('Paiement confirmé', `Le modèle « ${p.template_name} » est débloqué.`);
          load();
        } else if (p.status === 'PENDING' && attempts < 15) {
          pollTimer.current = window.setTimeout(check, 4000);
        } else if (p.status === 'PENDING') {
          setReturnState({ status: 'pending', name: p.template_name });
        } else {
          setReturnState({ status: 'failed', name: p.template_name });
        }
      } catch (err) {
        setReturnState({ status: 'pending' });
        toast.error('Vérification impossible', describeError(err));
      }
    };
    check();
    return () => window.clearTimeout(pollTimer.current);
  }, [searchParams, setSearchParams, toast, load]);

  const visible = useMemo(() => (templates ?? []).filter(t =>
    filter === 'ALL' ? true : filter === 'OWNED' ? t.owned && !t.is_free : t.level === filter || t.level === ''), [templates, filter]);

  const buy = async (t: MemoirTemplate) => {
    setBuying(t.slug);
    try {
      await openPayment(await modelesApi.purchase(t.slug));
    } catch (err) {
      setBuying(null);
      toast.error('Paiement indisponible', describeError(err));
    }
  };

  const retryPending = async (p: TemplatePurchase) => {
    try {
      const updated = await modelesApi.verify(p.id);
      setPurchases(list => list.map(x => (x.id === updated.id ? updated : x)));
      if (updated.status === 'PAID') { toast.success('Paiement confirmé'); load(); }
      else if (updated.status === 'SUBMITTED' || (updated.status === 'PENDING' && (updated.checkout_url || updated.provider === 'mobile_money'))) await openPayment(updated);
      else toast.warning('Session expirée', 'Relancez un achat depuis le catalogue.');
    } catch (err) {
      toast.error('Vérification impossible', describeError(err));
    }
  };

  const ownedCount = templates?.filter(t => t.owned && !t.is_free).length ?? 0;
  const paidSample = templates?.find(t => !t.is_free);

  return (
    <Layout onRefresh={load}>
      <div className="scope-ws">
        <div className="ws">
          <div className="ws-head">
            <div>
              <span className="eyebrow">Modèles de mémoire</span>
              <h2>Des modèles prêts à rédiger</h2>
              <p>Page de garde aux normes universitaires et plan commenté section par section.
                {templates?.some(t => t.is_free) && ' Un modèle est offert gratuitement.'} Les autres s'achètent une seule fois
                {paidSample ? ` (${formatPrice(paidSample.price, paidSample.currency)})` : ''} et s'utilisent sur tous vos mémoires.</p>
            </div>
            <button className="btn hide-mobile" onClick={load}>↻ Actualiser</button>
          </div>

          {returnState && (
            <div className={returnState.status === 'paid' ? 'ok' : returnState.status === 'failed' ? 'error' : 'note'} role="status">
              {returnState.status === 'checking' && '⏳ Vérification de votre paiement auprès de Jɛmɛnipay…'}
              {returnState.status === 'paid' && `✅ Paiement confirmé : « ${returnState.name} » est à vous. Cliquez sur « Utiliser ce modèle ».`}
              {returnState.status === 'pending' && "⏳ Paiement pas encore confirmé. S'il a abouti sur votre téléphone, il apparaîtra d'ici quelques minutes (voir « Mes achats » ci-dessous)."}
              {returnState.status === 'failed' && "Le paiement n'a pas abouti ou la session a expiré. Vous pouvez relancer l'achat."}
            </div>
          )}

          <div className="toolbar">
            <div className="tabs" role="tablist">
              {FILTERS.map(f => (
                <button key={f.key} role="tab" aria-selected={filter === f.key}
                        className={`tab${filter === f.key ? ' active' : ''}`} onClick={() => setFilter(f.key)}>
                  {f.label}{f.key === 'OWNED' && <span className="count">{ownedCount}</span>}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="error">{error}</div>}
          {templates === null && !error && <div className="state">Chargement des modèles…</div>}
          {templates !== null && visible.length === 0 && (
            <div className="empty"><strong>Aucun modèle ici</strong>{filter === 'OWNED' ? "Vous n'avez encore acheté aucun modèle." : ''}</div>
          )}

          <div className="tpl-grid">
            {visible.map(t => (
              <article key={t.slug} className="tpl-card" style={{ '--tpl-accent': t.accent_color } as React.CSSProperties}>
                <button type="button" className="tpl-cover" onClick={() => setDetail(t)} aria-label={`Voir le modèle ${t.name}`}>
                  <CoverFrame html={covers[t.slug] ?? null} title={`Page de garde ${t.name}`} />
                  {t.is_free ? <span className="tpl-owned tpl-free">Gratuit</span>
                    : t.owned && <span className="tpl-owned">✓ Acheté</span>}
                </button>
                <div className="tpl-body">
                  <div className="meta">
                    <span className="badge role">{t.level_label}</span>
                    <span className="badge role">Garde : {t.cover_label}</span>
                  </div>
                  <h3>{t.name}</h3>
                  <p className="theme">{t.tagline}</p>
                  <p className="tpl-domain">📚 {t.domain}</p>
                  <div className="tpl-footer">
                    <strong className="tpl-price">{t.is_free ? 'Gratuit' : t.owned ? 'Acheté' : formatPrice(t.price, t.currency)}</strong>
                    <div className="actions" style={{ marginTop: 0 }}>
                      <button className="btn" onClick={() => setDetail(t)}>Voir le plan</button>
                      {t.owned
                        ? <button className="btn primary" onClick={() => setApplyTo(t)}>Utiliser ce modèle</button>
                        : <button className="btn primary" disabled={buying !== null} onClick={() => buy(t)}>
                            {buying === t.slug ? 'Redirection…' : 'Acheter'}
                          </button>}
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>

          <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.6 }}>
            {options?.mode === 'mobile_money'
              ? '🔒 Paiement par Orange Money, Moov Money ou Wave. Le modèle est débloqué dès que nous avons confirmé la réception de votre paiement.'
              : options?.mode === 'jemeni' && "🔒 Paiement sécurisé par Jɛmɛnipay : saisissez votre numéro Jɛmɛnipay, puis validez la demande dans l'application Jɛmɛnipay de votre téléphone. Le modèle est débloqué dès la confirmation du paiement."}
          </p>

          {purchases.length > 0 && (
            <section className="panel">
              <h3>Mes achats</h3>
              <div className="table-wrap" style={{ border: 0 }}>
                <table className="cards-mobile">
                  <thead><tr><th>Modèle</th><th>Date</th><th className="num">Montant</th><th>Statut</th><th /></tr></thead>
                  <tbody>
                    {purchases.map(p => (
                      <tr key={p.id}>
                        <td className="cell-title" data-label="Modèle">{p.template_name}</td>
                        <td data-label="Date">{formatDate(p.paid_at ?? p.created_at)}</td>
                        <td className="num" data-label="Montant">{formatPrice(p.amount_charged ?? p.amount, p.currency)}</td>
                        <td data-label="Statut"><span className={`badge ${p.status === 'PAID' ? 'VALIDATED' : p.status === 'PENDING' || p.status === 'SUBMITTED' ? 'DRAFT' : 'ARCHIVED'}`}>
                          {PURCHASE_STATUS[p.status]}</span>{p.status === 'FAILED' && p.review_note && <><br /><span className="muted">{p.review_note}</span></>}</td>
                        <td className="cell-actions">{(p.status === 'PENDING' || p.status === 'SUBMITTED') && <button className="btn" onClick={() => retryPending(p)}>{p.status === 'SUBMITTED' ? 'Suivre' : 'Vérifier / payer'}</button>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      </div>

      {detail && (
        <TemplateDetailModal template={detail} cover={covers[detail.slug] ?? null} onClose={() => setDetail(null)}
                             buying={buying !== null}
                             onBuy={() => buy(detail)} onUse={() => { setApplyTo(detail); setDetail(null); }} />
      )}
      {paying && options && (
        <MobileMoneyModal key={paying.id} purchase={paying} options={options} onClose={() => { setPaying(null); load(); }}
                          onUpdate={paymentUpdated} />
      )}
      {applyTo && (
        <ApplyModal template={applyTo} onClose={() => setApplyTo(null)}
                    onApplied={projectId => navigate(`/projects/${projectId}/editor`)}
                    onNewProject={() => navigate(`/projects/new?modele=${applyTo.slug}`)} />
      )}
    </Layout>
  );
}

function TemplateDetailModal({ template: t, cover, onClose, onBuy, onUse, buying }: {
  template: MemoirTemplate; cover: string | null; onClose: () => void; onBuy: () => void; onUse: () => void; buying: boolean;
}) {
  const items = t.structure ?? t.outline.map(o => ({ title: o.title, type: o.type, guidance: '', sections: o.sections.map(title => ({ title, guidance: '' })) }));
  return (
    <Modal title={t.name} wide onClose={onClose} footer={<>
      <button className="btn-secondary" onClick={onClose}>Fermer</button>
      {t.owned
        ? <button className="btn-primary" onClick={onUse}>Utiliser ce modèle</button>
        : <button className="btn-primary" disabled={buying} onClick={onBuy}>Acheter — {formatPrice(t.price, t.currency)}</button>}
    </>}>
      <div className="tpl-detail">
        <div><CoverFrame html={cover} title={`Page de garde ${t.name}`} maxWidth={300} /></div>
        <div>
          <p style={{ marginTop: 0, lineHeight: 1.6, color: 'var(--text-secondary)' }}>{t.description}</p>
          <h4 style={{ margin: '14px 0 8px' }}>Plan du modèle</h4>
          {!t.owned && <p className="muted small" style={{ marginTop: 0 }}>Les conseils de rédaction détaillés sont débloqués après l'achat.</p>}
          <ol className="tpl-outline">
            {items.map((item, i) => (
              <li key={i} className={item.type === 'preliminary' || item.type === 'back' ? 'muted' : ''}>
                <strong>{item.title}</strong>
                {item.guidance && <small>{item.guidance}</small>}
                {item.sections.length > 0 && (
                  <ul>{item.sections.map((s, j) => <li key={j}>{s.title}{s.guidance && <small>{s.guidance}</small>}</li>)}</ul>
                )}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </Modal>
  );
}

function ApplyModal({ template, onClose, onApplied, onNewProject }: {
  template: MemoirTemplate; onClose: () => void; onApplied: (projectId: number) => void; onNewProject: () => void;
}) {
  const toast = useToast();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [projectId, setProjectId] = useState<number | ''>('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    projectsApi.list('mine')
      .then(list => setProjects(list.filter(p => p.status !== 'REVIEW' && p.status !== 'VALIDATED')))
      .catch(err => setError(describeError(err)));
  }, []);

  const selected = projects?.find(p => p.id === projectId);
  const apply = async () => {
    if (!selected) return;
    const existing = selected.chapters.length;
    if (existing && !window.confirm(`« ${selected.title} » contient déjà ${existing} chapitre(s). Le plan du modèle sera ajouté à la suite, sans rien supprimer. Continuer ?`)) return;
    setBusy(true);
    setError('');
    try {
      const res = await modelesApi.apply(template.slug, selected.id);
      toast.success('Modèle appliqué', `${res.chapters_created} chapitres et sections ajoutés, page de garde incluse.`);
      onApplied(selected.id);
    } catch (err) {
      setError(describeError(err, "Impossible d'appliquer le modèle."));
      setBusy(false);
    }
  };

  return (
    <Modal title={`Utiliser « ${template.name} »`} onClose={onClose} footer={<>
      <button className="btn-secondary" onClick={onClose}>Annuler</button>
      <button className="btn-primary" disabled={!selected || busy} onClick={apply}>{busy ? 'Application…' : 'Appliquer au mémoire'}</button>
    </>}>
      <p className="muted" style={{ marginTop: 0 }}>
        Le plan commenté est ajouté à votre mémoire et sa page de garde sera incluse dans vos exports.
      </p>
      {projects === null && !error && <div className="empty-box">Chargement…</div>}
      {projects?.length === 0 && <div className="empty-box">Aucun mémoire modifiable.</div>}
      {projects && projects.length > 0 && (
        <label className="form-field">Mémoire
          <select value={projectId} onChange={e => setProjectId(e.target.value ? Number(e.target.value) : '')}>
            <option value="">— Choisir un mémoire —</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.title}{p.template_detail ? ` (modèle actuel : ${p.template_detail.name})` : ''}</option>
            ))}
          </select>
        </label>
      )}
      <button type="button" className="btn-secondary" onClick={onNewProject}>＋ Créer un nouveau mémoire avec ce modèle</button>
      {error && <div className="alert error">⚠ {error}</div>}
    </Modal>
  );
}
