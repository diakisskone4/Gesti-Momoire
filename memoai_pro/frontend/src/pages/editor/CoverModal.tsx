import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { describeError } from '../../api/client';
import { modelesApi } from '../../api/services';
import CoverFrame from '../../components/CoverFrame';
import Modal from '../../components/Modal';
import type { Project } from '../../lib/models';

/** Page de garde du mémoire, générée à partir de son modèle et de ses informations. */
export default function CoverModal({ project, onClose, onEditSettings }: {
  project: Project; onClose: () => void; onEditSettings: () => void;
}) {
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState('');
  const hasTemplate = !!project.template_detail;

  useEffect(() => {
    if (!hasTemplate) return;
    modelesApi.projectCover(project.id).then(r => setHtml(r.html)).catch(err => setError(describeError(err)));
  }, [project.id, project.updated_at, hasTemplate]);

  const print = () => {
    if (!html) return;
    const win = window.open('', '_blank', 'noopener=no');
    if (!win) return;
    win.document.write(html);
    win.document.close();
    win.focus();
    win.print();
  };

  if (!hasTemplate) {
    return (
      <Modal title="📄 Page de garde" onClose={onClose} footer={<>
        <button className="btn-secondary" onClick={onClose}>Fermer</button>
        <Link className="btn-primary" to="/modeles" style={{ textDecoration: 'none' }}>Voir les modèles</Link>
      </>}>
        <p style={{ marginTop: 0, lineHeight: 1.6 }}>
          Ce mémoire n'utilise pas encore de modèle. Achetez un modèle pour obtenir une page de garde aux normes
          universitaires (6 styles), automatiquement remplie avec vos informations et intégrée à vos exports.
        </p>
      </Modal>
    );
  }

  return (
    <Modal title={`📄 Page de garde — ${project.template_detail!.name}`} wide onClose={onClose} footer={<>
      <button className="btn-secondary" onClick={onEditSettings}>⚙ Modifier les informations</button>
      <button className="btn-secondary" onClick={onClose}>Fermer</button>
      <button className="btn-primary" onClick={print} disabled={!html}>🖨 Imprimer</button>
    </>}>
      <p className="muted small" style={{ marginTop: 0 }}>
        Remplie avec le titre, l'université, la faculté, l'encadrement et le jury du mémoire. Elle est ajoutée
        automatiquement en première page de vos exports Word, PDF et HTML.
      </p>
      {error ? <div className="alert error">⚠ {error}</div> : (
        <div style={{ maxWidth: 520, margin: '0 auto', boxShadow: '0 6px 24px rgba(0,0,0,.15)' }}>
          <CoverFrame html={html} title="Page de garde du mémoire" />
        </div>
      )}
    </Modal>
  );
}
