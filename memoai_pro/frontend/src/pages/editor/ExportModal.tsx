import { useState } from 'react';

import { describeError, request } from '../../api/client';
import { projectsApi } from '../../api/services';
import Modal from '../../components/Modal';
import { useToast } from '../../context/ToastContext';
import { downloadBlob } from '../../lib/format';
import type { Project } from '../../lib/models';

const FORMATS = [
  { key: 'docx', icon: '📝', name: 'Word (DOCX)', desc: 'Format éditable' },
  { key: 'pdf', icon: '📄', name: 'PDF', desc: 'Format universel' },
  { key: 'html', icon: '🌐', name: 'HTML', desc: 'Pour le web' },
];

function filenameFrom(res: Response, fallback: string): string {
  const header = res.headers.get('Content-Disposition') ?? '';
  const star = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(header);
  if (star) return decodeURIComponent(star[1].replace(/"/g, ''));
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1] : fallback;
}

export default function ExportModal({ project, onClose }: { project: Project; onClose: () => void }) {
  const toast = useToast();
  const [format, setFormat] = useState('docx');
  const [includeChapters, setIncludeChapters] = useState(true);
  const [includeBibliography, setIncludeBibliography] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [needsPayment, setNeedsPayment] = useState(project.export_allowed === false);

  const exportNow = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await projectsApi.export(project.id, format, includeChapters, includeBibliography);
      downloadBlob(await res.blob(), filenameFrom(res, `${project.title}.${format}`));
      toast.success('Export réussi', `Le mémoire a été exporté en ${format.toUpperCase()}.`);
      onClose();
    } catch (err) {
      const e = err as { status?: number };
      if (e.status === 402) setNeedsPayment(true);
      setError(describeError(err, "L'export a échoué."));
    } finally {
      setLoading(false);
    }
  };

  const pay = async () => {
    setLoading(true);
    setError('');
    try {
      const { url } = await request<{ url: string }>('/payments/checkout/', { method: 'POST', body: { project_id: project.id } });
      window.location.href = url;
    } catch (err) {
      setError(describeError(err, 'Le paiement est indisponible.'));
      setLoading(false);
    }
  };

  return (
    <Modal title="📄 Exporter le mémoire" onClose={onClose} footer={<>
      <button className="btn-secondary" onClick={onClose}>Annuler</button>
      {needsPayment
        ? <button className="btn-primary" onClick={pay} disabled={loading}>💳 Débloquer l'export (29,99 €)</button>
        : <button className="btn-primary" onClick={exportNow} disabled={loading || (!includeChapters && !includeBibliography)}>
            {loading ? 'Export en cours…' : '📥 Exporter'}
          </button>}
    </>}>
      <p className="muted" style={{ marginTop: 0 }}>Choisissez le format d'export :</p>
      <div className="format-options" role="radiogroup" aria-label="Format">
        {FORMATS.map(f => (
          <button type="button" key={f.key} role="radio" aria-checked={format === f.key}
                  className={`format-option${format === f.key ? ' selected' : ''}`} onClick={() => setFormat(f.key)}>
            <span aria-hidden="true">{f.icon}</span>
            <strong>{f.name}</strong>
            <small>{f.desc}</small>
          </button>
        ))}
      </div>
      <label className="checkbox">
        <input type="checkbox" checked={includeChapters} onChange={e => setIncludeChapters(e.target.checked)} /> Inclure les chapitres
      </label>
      <label className="checkbox">
        <input type="checkbox" checked={includeBibliography} onChange={e => setIncludeBibliography(e.target.checked)} /> Inclure la bibliographie
      </label>
      {needsPayment && <div className="alert info">L'export final de ce mémoire est payant. La rédaction reste gratuite.</div>}
      {error && <div className="alert error">⚠ {error}</div>}
    </Modal>
  );
}
