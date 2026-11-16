import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { describeError, request } from '../api/client';
import '../styles/workspace.css';

interface SharedChapter { id: number; title: string; content: string; children: SharedChapter[]; }
interface SharedProject {
  title: string; theme: string | null; level: string; university: string | null; academic_year: string | null;
  author: string; status_label: string; chapters: SharedChapter[];
  references: { authors: string; year: number; title: string; journal: string | null; doi: string | null }[];
}

function ChapterBlock({ chapter, depth }: { chapter: SharedChapter; depth: number }) {
  const Heading = depth === 0 ? 'h3' : 'h4';
  return (
    <section className="chapter" style={{ marginLeft: depth * 16 }}>
      <Heading style={{ color: 'var(--text-primary)', margin: '0 0 8px' }}>{chapter.title}</Heading>
      {chapter.content
        ? <div className="content" style={{ whiteSpace: 'pre-wrap' }}>{chapter.content}</div>
        : <div className="content muted">(section vide)</div>}
      {chapter.children.map(c => <ChapterBlock key={c.id} chapter={c} depth={depth + 1} />)}
    </section>
  );
}

/** /share/:token — lecture publique d'un mémoire partagé par son auteur. */
export default function SharedPage() {
  const { token } = useParams();
  const [data, setData] = useState<SharedProject | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    request<SharedProject>(`/projects/shared/${encodeURIComponent(token ?? '')}/`)
      .then(setData)
      .catch(err => setError(describeError(err, 'Lien invalide.')));
  }, [token]);

  return (
    <div className="scope-ws" style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <div className="ws" style={{ maxWidth: 860, margin: '0 auto', padding: '32px 16px' }}>
        <Link to="/login" style={{ color: '#0f766e', fontWeight: 800, textDecoration: 'none' }}>MemoAI Pro</Link>
        {!data && !error && <div className="state">Chargement…</div>}
        {error && <div className="empty"><strong>Mémoire indisponible</strong>{error}</div>}
        {data && (
          <>
            <div className="ws-head">
              <div>
                <span className="eyebrow">Mémoire partagé · lecture seule</span>
                <h2>{data.title}</h2>
                <div className="meta" style={{ marginTop: 8 }}>
                  <span>✍️ {data.author}</span>
                  <span>🎓 {data.level}</span>
                  {data.university && <span>🏛 {data.university}</span>}
                  {data.academic_year && <span>📅 {data.academic_year}</span>}
                  <span>{data.status_label}</span>
                </div>
              </div>
            </div>
            {data.theme && <p className="note"><strong>Thème :</strong> {data.theme}</p>}
            <div className="panel">
              {data.chapters.length === 0 && <p className="muted">Aucun chapitre rédigé.</p>}
              {data.chapters.map(c => <ChapterBlock key={c.id} chapter={c} depth={0} />)}
            </div>
            {data.references.length > 0 && (
              <div className="panel">
                <h3>Bibliographie</h3>
                {data.references.map((r, i) => (
                  <p key={i} style={{ margin: '0 0 8px', color: 'var(--text-secondary)', fontSize: 14 }}>
                    {r.authors} ({r.year}). <em>{r.title}</em>.{r.journal ? ` ${r.journal}.` : ''}{r.doi ? ` doi:${r.doi}` : ''}
                  </p>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
