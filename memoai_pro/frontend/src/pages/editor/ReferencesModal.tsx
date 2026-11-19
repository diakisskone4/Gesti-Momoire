import { useEffect, useState } from 'react';

import { describeError } from '../../api/client';
import { referencesApi } from '../../api/services';
import Modal from '../../components/Modal';
import { useToast } from '../../context/ToastContext';
import type { Reference } from '../../lib/models';

type Draft = Pick<Reference, 'title' | 'authors' | 'journal' | 'doi'> & { id?: number; year: number | '' };

const EMPTY: Draft = { title: '', authors: '', year: new Date().getFullYear(), journal: '', doi: '' };

export default function ReferencesModal({ projectId, onClose }: { projectId: number; onClose: () => void }) {
  const toast = useToast();
  const [refs, setRefs] = useState<Reference[] | null>(null);
  const [doi, setDoi] = useState('');
  const [importing, setImporting] = useState(false);
  const [editing, setEditing] = useState<Draft | null>(null);
  const [error, setError] = useState('');
  const [bibtex, setBibtex] = useState<Record<number, string>>({});

  useEffect(() => {
    referencesApi.list(projectId).then(setRefs).catch(err => setError(describeError(err)));
  }, [projectId]);

  const importDoi = async () => {
    setImporting(true);
    setError('');
    try {
      const ref = await referencesApi.importByDoi(doi.trim(), projectId);
      setRefs(list => [...(list ?? []), ref]);
      setDoi('');
      toast.success('Référence importée', ref.title);
    } catch (err) {
      setError(describeError(err, 'Import impossible.'));
    } finally {
      setImporting(false);
    }
  };

  const save = async () => {
    if (!editing || editing.year === '') return;
    setError('');
    const data = { ...editing, year: Number(editing.year), project: projectId };
    try {
      const saved = editing.id ? await referencesApi.update(editing.id, data) : await referencesApi.create(data);
      setRefs(list => (editing.id ? (list ?? []).map(r => (r.id === saved.id ? saved : r)) : [...(list ?? []), saved]));
      setBibtex(b => { const next = { ...b }; delete next[saved.id]; return next; });
      setEditing(null);
    } catch (err) {
      setError(describeError(err, "Impossible d'enregistrer la référence."));
    }
  };

  const remove = async (ref: Reference) => {
    if (!window.confirm(`Placer « ${ref.title} » dans la corbeille ? Restaurable pendant 30 jours.`)) return;
    try {
      await referencesApi.remove(ref.id);
      setRefs(list => (list ?? []).filter(r => r.id !== ref.id));
    } catch (err) {
      setError(describeError(err));
    }
  };

  const toggleBibtex = async (ref: Reference) => {
    if (bibtex[ref.id]) {
      setBibtex(b => { const next = { ...b }; delete next[ref.id]; return next; });
      return;
    }
    try {
      const { bibtex: value } = await referencesApi.bibtex(ref.id);
      setBibtex(b => ({ ...b, [ref.id]: value }));
    } catch (err) {
      setError(describeError(err));
    }
  };

  const field = (key: keyof Draft) => ({
    value: (editing?.[key] ?? '') as string | number,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
      setEditing(d => d && { ...d, [key]: key === 'year' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value }),
  });

  return (
    <Modal title="📚 Bibliographie" wide onClose={onClose} footer={<button className="btn-secondary" onClick={onClose}>Fermer</button>}>
      <div className="modal-section">
        <h4>Importer par DOI</h4>
        <div className="modal-row">
          <input className="input" value={doi} onChange={e => setDoi(e.target.value)} placeholder="Ex. 10.1038/nature12373"
                 aria-label="DOI" onKeyDown={e => e.key === 'Enter' && doi.trim() && importDoi()} />
          <button className="btn-primary" style={{ flex: 'none' }} onClick={importDoi} disabled={!doi.trim() || importing}>
            {importing ? 'Import…' : '📥 Importer'}
          </button>
        </div>
      </div>

      {error && <div className="alert error">⚠ {error}</div>}

      {editing ? (
        <div className="modal-section">
          <h4>{editing.id ? 'Modifier' : 'Ajouter'} une référence</h4>
          <label className="form-field">Titre *<input {...field('title')} /></label>
          <div className="modal-row">
            <label className="form-field">Auteurs *<input {...field('authors')} placeholder="Diallo, A. ; Traoré, B." /></label>
            <label className="form-field" style={{ maxWidth: 140 }}>Année *<input type="number" {...field('year')} /></label>
          </div>
          <label className="form-field">Revue / éditeur<input {...field('journal')} /></label>
          <label className="form-field">DOI<input {...field('doi')} /></label>
          <div className="modal-row" style={{ justifyContent: 'flex-end' }}>
            <button className="btn-secondary" style={{ flex: 'none' }} onClick={() => setEditing(null)}>Annuler</button>
            <button className="btn-primary" style={{ flex: 'none' }} onClick={save}
                    disabled={!editing.title.trim() || !editing.authors.trim() || editing.year === ''}>💾 Enregistrer</button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 0 12px' }}>
          <strong>Références ({refs?.length ?? 0})</strong>
          <button className="btn-secondary" onClick={() => setEditing({ ...EMPTY })}>➕ Ajouter manuellement</button>
        </div>
      )}

      {refs === null && !error && <div className="empty-box">Chargement…</div>}
      {refs?.length === 0 && <div className="empty-box">📭 Aucune référence bibliographique</div>}
      <div className="item-list">
        {refs?.map(ref => (
          <div className="item" key={ref.id}>
            <div style={{ minWidth: 0, flex: 1 }}>
              <strong>{ref.title}</strong>
              <small>{ref.authors} · {ref.year}{ref.journal ? ` · ${ref.journal}` : ''}{ref.doi ? ` · DOI ${ref.doi}` : ''}</small>
              {bibtex[ref.id] && <pre>{bibtex[ref.id]}</pre>}
            </div>
            <div className="item-actions">
              <button className="btn-icon" title="Modifier" aria-label="Modifier"
                      onClick={() => setEditing({ id: ref.id, title: ref.title, authors: ref.authors, year: ref.year, journal: ref.journal ?? '', doi: ref.doi ?? '' })}>✏️</button>
              <button className="btn-icon" title="BibTeX" aria-label="Afficher le BibTeX" onClick={() => toggleBibtex(ref)}>📄</button>
              <button className="btn-icon" title="Supprimer" aria-label="Supprimer" onClick={() => remove(ref)}>🗑️</button>
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
