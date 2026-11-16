import { useEffect, useState } from 'react';

import { describeError } from '../../api/client';
import { aiApi, projectsApi } from '../../api/services';
import Layout from '../../components/Layout';
import type { Project } from '../../lib/models';
import '../../styles/workspace.css';

type Tool = 'chat' | 'reformulate' | 'summarize' | 'translate';

const TOOLS: { key: Tool; label: string }[] = [
  { key: 'chat', label: 'Discussion' },
  { key: 'reformulate', label: 'Reformuler' },
  { key: 'summarize', label: 'Résumer' },
  { key: 'translate', label: 'Traduire' },
];

/** Assistant IA de l'étudiant (cahier des charges §3.7). */
export default function AssistantPage() {
  const [tool, setTool] = useState<Tool>('chat');
  const [input, setInput] = useState('');
  const [lang, setLang] = useState('en');
  const [style, setStyle] = useState('academic');
  const [projectId, setProjectId] = useState<number | ''>('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [result, setResult] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    projectsApi.list('mine').then(setProjects).catch(() => undefined);
  }, []);

  const select = (t: Tool) => {
    setTool(t);
    setResult('');
    setError('');
  };

  const run = async () => {
    const text = input.trim();
    setLoading(true);
    setError('');
    setResult('');
    setCopied(false);
    try {
      const output = tool === 'chat' ? (await aiApi.chat(text, projectId || null)).response
        : tool === 'reformulate' ? (await aiApi.reformulate(text, style)).result
          : tool === 'summarize' ? (await aiApi.summarize(text)).summary
            : (await aiApi.translate(text, lang)).translation;
      setResult(output);
    } catch (err) {
      setError(describeError(err, 'Le service IA ne répond pas. Vérifiez la clé API côté serveur.'));
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    try { await navigator.clipboard.writeText(result); setCopied(true); } catch { /* ignore */ }
  };

  return (
    <Layout>
      <div className="scope-ws">
        <div className="ws">
          <div className="ws-head">
            <div>
              <span className="eyebrow">Intelligence artificielle</span>
              <h2>Assistant IA</h2>
              <p>Posez une question, reformulez, résumez ou traduisez un passage de votre mémoire.</p>
            </div>
          </div>

          <div className="tabs" role="tablist">
            {TOOLS.map(t => (
              <button key={t.key} className={`tab${tool === t.key ? ' active' : ''}`} role="tab"
                      aria-selected={tool === t.key} onClick={() => select(t.key)}>{t.label}</button>
            ))}
          </div>

          <section className="panel">
            <label className="sr-only" htmlFor="ai-input">Texte</label>
            <textarea id="ai-input" className="search" style={{ width: '100%', minHeight: 160, resize: 'vertical' }}
                      value={input} onChange={e => setInput(e.target.value)}
                      onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && input.trim() && !loading) run(); }}
                      placeholder={tool === 'chat'
                        ? "Ex. : Propose-moi une problématique sur l'impact du mobile money au Mali."
                        : 'Collez ici le passage à traiter...'} />
            <div className="toolbar" style={{ marginTop: 12 }}>
              {tool === 'chat' && projects.length > 0 && (
                <select className="btn" value={projectId} onChange={e => setProjectId(e.target.value ? Number(e.target.value) : '')}
                        aria-label="Mémoire de contexte">
                  <option value="">Sans contexte de mémoire</option>
                  {projects.map(p => <option key={p.id} value={p.id}>Contexte : {p.title}</option>)}
                </select>
              )}
              {tool === 'reformulate' && (
                <select className="btn" value={style} onChange={e => setStyle(e.target.value)} aria-label="Style">
                  <option value="academic">Style académique</option>
                  <option value="simple">Plus simple</option>
                  <option value="formal">Formel et concis</option>
                </select>
              )}
              {tool === 'translate' && (
                <select className="btn" value={lang} onChange={e => setLang(e.target.value)} aria-label="Langue cible">
                  <option value="en">Anglais</option>
                  <option value="fr">Français</option>
                  <option value="es">Espagnol</option>
                  <option value="ar">Arabe</option>
                  <option value="pt">Portugais</option>
                  <option value="de">Allemand</option>
                </select>
              )}
              <button className="btn primary" disabled={loading || !input.trim()} onClick={run}>
                {loading ? 'Génération...' : 'Lancer ✦'}
              </button>
              <span className="muted" style={{ fontSize: 12 }}>Ctrl+Entrée</span>
            </div>
          </section>

          {error && <div className="error">{error}</div>}

          {result && (
            <section className="panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>Résultat</h3>
                <button className="btn" onClick={copy}>{copied ? '✓ Copié' : '📋 Copier'}</button>
              </div>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, color: 'var(--text-secondary)', marginTop: 12 }}>{result}</div>
              <p className="note" style={{ marginTop: 14 }}>
                ⚠ Contenu généré par IA : vérifiez les faits et les références avant de les intégrer à votre mémoire.
              </p>
            </section>
          )}
        </div>
      </div>
    </Layout>
  );
}
