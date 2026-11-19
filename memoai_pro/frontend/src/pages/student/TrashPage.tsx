import { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, FileText, Quote, RotateCcw, Trash2, type LucideIcon } from 'lucide-react';

import { describeError } from '../../api/client';
import { trashApi, type TrashItem, type TrashKind } from '../../api/services';
import Layout from '../../components/Layout';
import { useToast } from '../../context/ToastContext';
import { formatDateTime } from '../../lib/format';
import '../../styles/projects.css';
import '../../styles/trash.css';

const KIND: Record<TrashKind, { icon: LucideIcon; label: string }> = {
  project: { icon: BookOpen, label: 'Mémoires' },
  chapter: { icon: FileText, label: 'Chapitres et sections' },
  reference: { icon: Quote, label: 'Références' },
};

type Filter = 'all' | TrashKind;

function daysLeft(purgeAt: string): number {
  return Math.max(0, Math.ceil((new Date(purgeAt).getTime() - Date.now()) / 86_400_000));
}

export default function TrashPage() {
  const toast = useToast();
  const [items, setItems] = useState<TrashItem[]>([]);
  const [retention, setRetention] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<Filter>('all');
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    trashApi.list()
      .then(data => { setItems(data.items); setRetention(data.retention_days); })
      .catch(err => setError(describeError(err, 'Impossible de charger la corbeille.')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  const shown = useMemo(() => items.filter(i => filter === 'all' || i.kind === filter), [items, filter]);
  const key = (item: TrashItem) => `${item.kind}-${item.id}`;

  const restore = async (item: TrashItem) => {
    setBusy(key(item));
    try {
      await trashApi.restore(item.kind, item.id);
      toast.success('Élément restauré', item.kind === 'project'
        ? `« ${item.title} » est de retour dans vos mémoires.`
        : `« ${item.title} » est de retour dans « ${item.project_title} ».`);
      load();
    } catch (err) {
      toast.error('Restauration impossible', describeError(err));
    } finally {
      setBusy(null);
    }
  };

  const remove = async (item: TrashItem) => {
    const what = item.kind === 'project' ? 'ce mémoire, tous ses chapitres et ses références' : 'cet élément';
    if (!window.confirm(`Supprimer définitivement « ${item.title} » ? ${what[0].toUpperCase()}${what.slice(1)} ne pourra plus être récupéré.`)) return;
    setBusy(key(item));
    try {
      await trashApi.remove(item.kind, item.id);
      setItems(list => list.filter(i => key(i) !== key(item)));
      toast.success('Supprimé définitivement');
    } catch (err) {
      toast.error('Suppression impossible', describeError(err));
    } finally {
      setBusy(null);
    }
  };

  const empty = async () => {
    if (!window.confirm(`Vider la corbeille ? Les ${items.length} élément(s) seront supprimés définitivement.`)) return;
    setBusy('all');
    try {
      await trashApi.empty();
      setItems([]);
      toast.success('Corbeille vidée');
    } catch (err) {
      toast.error('Impossible de vider la corbeille', describeError(err));
    } finally {
      setBusy(null);
    }
  };

  const count = (kind: TrashKind) => items.filter(i => i.kind === kind).length;

  return (
    <Layout>
      <div className="scope-projects scope-trash">
        <div className="projects-page">
          <div className="page-header">
            <div>
              <span className="eyebrow">CORBEILLE</span>
              <h1>Corbeille</h1>
              <p className="subtitle">
                Les éléments supprimés restent ici {retention} jours : restaurez-les ou supprimez-les définitivement.
              </p>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button className="btn-secondary" onClick={load} disabled={loading}>🔄 Rafraîchir</button>
              <button className="btn-danger-outline" onClick={empty} disabled={!items.length || busy !== null}>
                <Trash2 size={16} aria-hidden="true" /> Vider la corbeille
              </button>
            </div>
          </div>

          <div className="trash-filters" role="tablist" aria-label="Filtrer la corbeille">
            {(['all', 'project', 'chapter', 'reference'] as Filter[]).map(f => (
              <button key={f} type="button" role="tab" aria-selected={filter === f}
                      className={filter === f ? 'active' : ''} onClick={() => setFilter(f)}>
                {f === 'all' ? `Tout (${items.length})` : `${KIND[f].label} (${count(f)})`}
              </button>
            ))}
          </div>

          {loading && (
            <div className="loading-state"><div className="spinner" /><p>Chargement de la corbeille...</p></div>
          )}

          {error && !loading && (
            <div className="error-state">
              <p>⚠️ {error}</p>
              <button className="btn-primary" onClick={load}>Réessayer</button>
            </div>
          )}

          {!loading && !error && shown.length === 0 && (
            <div className="empty-state">
              <Trash2 size={40} strokeWidth={1.5} aria-hidden="true" />
              <h3>La corbeille est vide</h3>
              <p>Les mémoires, chapitres et références que vous supprimez apparaîtront ici.</p>
            </div>
          )}

          {!loading && !error && shown.length > 0 && (
            <ul className="trash-list">
              {shown.map(item => {
                const Icon = KIND[item.kind].icon;
                const left = daysLeft(item.purge_at);
                return (
                  <li key={key(item)} className="trash-item">
                    <span className={`trash-icon kind-${item.kind}`}><Icon size={20} aria-hidden="true" /></span>
                    <div className="trash-info">
                      <strong>{item.title}</strong>
                      <span className="trash-meta">
                        {item.details}
                        {item.kind !== 'project' && <> · dans « {item.project_title} »</>}
                      </span>
                      <span className="trash-meta">
                        Supprimé le {formatDateTime(item.deleted_at)} ·{' '}
                        <span className={left <= 3 ? 'trash-soon' : ''}>
                          {left > 0 ? `suppression définitive dans ${left} jour${left > 1 ? 's' : ''}` : 'suppression imminente'}
                        </span>
                      </span>
                    </div>
                    <div className="trash-actions">
                      <button className="btn-small primary" disabled={busy !== null} onClick={() => restore(item)}>
                        <RotateCcw size={14} aria-hidden="true" /> Restaurer
                      </button>
                      <button className="btn-small danger" disabled={busy !== null} onClick={() => remove(item)}>
                        <Trash2 size={14} aria-hidden="true" /> Supprimer
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </Layout>
  );
}
