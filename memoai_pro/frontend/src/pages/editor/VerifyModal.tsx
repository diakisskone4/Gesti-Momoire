import { useEffect, useState } from 'react';

import { describeError } from '../../api/client';
import { aiApi, type VerifyResult } from '../../api/services';
import Modal from '../../components/Modal';

const ISSUE_LABELS: Record<string, string> = {
  incoherence: 'Incohérence',
  affirmation_sans_source: 'Affirmation sans source',
  imprecision: 'Imprécision',
  style: 'Style',
};

/** Relecture scientifique du chapitre par l'IA (§3.7). */
export default function VerifyModal({ text, title, onClose }: { text: string; title: string; onClose: () => void }) {
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    aiApi.verify(text)
      .then(r => !cancelled && setResult(r))
      .catch(err => !cancelled && setError(describeError(err, "Le service IA ne répond pas.")));
    return () => { cancelled = true; };
  }, [text]);

  return (
    <Modal title={`✦ Relecture IA — ${title}`} wide onClose={onClose} footer={<button className="btn-secondary" onClick={onClose}>Fermer</button>}>
      {!result && !error && <div className="empty-box">L'IA relit votre chapitre… (cela peut prendre une minute)</div>}
      {error && <div className="alert error">⚠ {error}</div>}
      {result && (
        <>
          <div className="modal-section" style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <strong style={{ fontSize: 30, color: result.score >= 70 ? '#16a34a' : result.score >= 40 ? '#d97706' : '#dc2626' }}>
              {result.score}<span className="muted small">/100</span>
            </strong>
            <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{result.summary}</p>
          </div>
          {result.issues.length === 0 && <div className="alert success">Aucun problème relevé.</div>}
          <div className="item-list">
            {result.issues.map((issue, i) => (
              <div className="item" key={i} style={{ display: 'block' }}>
                <strong>{ISSUE_LABELS[issue.type] ?? issue.type}</strong>
                <small style={{ fontStyle: 'italic' }}>« {issue.excerpt} »</small>
                <p style={{ margin: '8px 0 4px', fontSize: 14, color: 'var(--text-secondary)' }}>{issue.explanation}</p>
                <p style={{ margin: 0, fontSize: 14, color: '#0f766e' }}>→ {issue.suggestion}</p>
              </div>
            ))}
          </div>
          <p className="muted small">Contenu généré par IA : vérifiez chaque suggestion avant de l'appliquer.</p>
        </>
      )}
    </Modal>
  );
}
