import { useEffect, useRef, useState } from 'react';

import { describeError } from '../../api/client';
import { imagesApi } from '../../api/services';
import { useToast } from '../../context/ToastContext';

/** Ligne d'une figure dans le texte d'un chapitre : [Figure:12 | Légende]. */
export const FIGURE_LINE = /^\[Figure:(\d+)(?:\s*\|\s*(.*?))?\]\s*$/;

export interface FigureRef { id: number; caption: string; line: string }

export function figuresIn(content: string): FigureRef[] {
  return content.split('\n').flatMap(line => {
    const match = FIGURE_LINE.exec(line.trim());
    return match ? [{ id: Number(match[1]), caption: match[2] ?? '', line }] : [];
  });
}

/** Insère `marker` sur sa propre ligne, à la position du curseur (début de ligne suivante). */
export function insertLine(content: string, position: number, marker: string): string {
  const at = Math.min(Math.max(position, 0), content.length);
  const end = content.indexOf('\n', at);
  const cut = end === -1 ? content.length : end;
  const before = content.slice(0, cut);
  const after = content.slice(cut);
  const prefix = before && !before.endsWith('\n') ? '\n' : '';
  const suffix = after.startsWith('\n') ? '' : '\n';
  return `${before}${prefix}${marker}${suffix}${after}`;
}

export function removeFigure(content: string, id: number): string {
  return content.split('\n').filter(line => {
    const match = FIGURE_LINE.exec(line.trim());
    return !match || Number(match[1]) !== id;
  }).join('\n');
}

const MAX_SIDE = 1600;
const MAX_DATA_URL = 3_500_000; // caractères base64 (~2,6 Mo d'image)

/** Réduit l'image à 1600 px côté navigateur (envoi léger, compatible avec la limite de Vercel). */
async function resizeToDataUrl(file: File): Promise<string> {
  const source = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('Lecture impossible'));
    reader.readAsDataURL(file);
  });
  const image = await new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Ce fichier n'est pas une image lisible."));
    img.src = source;
  });
  const scale = Math.min(1, MAX_SIDE / Math.max(image.width, image.height));
  if (scale === 1 && source.length < MAX_DATA_URL) return source;
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(image.width * scale);
  canvas.height = Math.round(image.height * scale);
  const ctx = canvas.getContext('2d');
  if (!ctx) return source;
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  const png = file.type === 'image/png' ? canvas.toDataURL('image/png') : '';
  // Envoi limité à environ 4 Mo : un PNG trop lourd (photo) est converti en JPEG.
  return png && png.length < MAX_DATA_URL ? png : canvas.toDataURL('image/jpeg', 0.85);
}

const urlCache = new Map<number, Promise<string>>();

function imageUrl(id: number): Promise<string> {
  let url = urlCache.get(id);
  if (!url) {
    url = imagesApi.file(id).then(res => res.blob()).then(blob => URL.createObjectURL(blob));
    url.catch(() => urlCache.delete(id));
    urlCache.set(id, url);
  }
  return url;
}

function Thumbnail({ id, alt }: { id: number; alt: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    imageUrl(id).then(url => alive && setSrc(url)).catch(() => alive && setFailed(true));
    return () => { alive = false; };
  }, [id]);
  if (failed) return <div className="figure-thumb missing">Image introuvable</div>;
  return src ? <img className="figure-thumb" src={src} alt={alt} /> : <div className="figure-thumb loading" />;
}

interface Props {
  projectId: number;
  content: string;
  /** Position du curseur dans la zone de texte, au moment de l'insertion. */
  cursor: () => number;
  onChange: (content: string) => void;
}

export default function FigureTools({ projectId, content, cursor, onChange }: Props) {
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<{ data: string; name: string } | null>(null);
  const [caption, setCaption] = useState('');
  const [uploading, setUploading] = useState(false);
  const figures = figuresIn(content);

  const choose = async (file: File | undefined) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Format non pris en charge', 'Choisissez une image (PNG, JPEG, WEBP ou GIF).');
      return;
    }
    try {
      const data = await resizeToDataUrl(file);
      setPending({ data, name: file.name });
      setCaption(file.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '));
    } catch (err) {
      toast.error('Image illisible', err instanceof Error ? err.message : undefined);
    }
  };

  const insert = async () => {
    if (!pending) return;
    setUploading(true);
    try {
      const uploaded = await imagesApi.upload(projectId, pending.data, caption.trim());
      onChange(insertLine(content, cursor(), uploaded.marker));
      setPending(null);
      toast.success('Figure insérée', 'Pensez à enregistrer le chapitre.');
    } catch (err) {
      toast.error("Envoi de l'image impossible", describeError(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="figure-tools">
      <div className="figure-tools-bar">
        <button type="button" className="secondary" onClick={() => input.current?.click()} disabled={uploading}>
          🖼 Insérer une image
        </button>
        <span className="figure-hint">
          La figure est placée à la position du curseur et numérotée automatiquement (Figure I.1, I.2…) à l'export.
        </span>
        <input ref={input} type="file" accept="image/*" hidden
               onChange={e => { void choose(e.target.files?.[0]); e.target.value = ''; }} />
      </div>

      {pending && (
        <div className="figure-pending">
          <img src={pending.data} alt="Aperçu de l'image" />
          <div className="figure-pending-form">
            <label htmlFor="figureCaption">Légende de la figure</label>
            <input id="figureCaption" type="text" value={caption} maxLength={300} autoFocus
                   placeholder="Ex. : Évolution du nombre de comptes mobile money (2015-2024)"
                   onChange={e => setCaption(e.target.value)}
                   onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); void insert(); } }} />
            <div className="figure-pending-actions">
              <button type="button" className="secondary" onClick={() => setPending(null)} disabled={uploading}>Annuler</button>
              <button type="button" className="primary" onClick={() => void insert()} disabled={uploading}>
                {uploading ? 'Envoi…' : 'Insérer la figure'}
              </button>
            </div>
          </div>
        </div>
      )}

      {figures.length > 0 && (
        <div className="figure-list">
          {figures.map((figure, index) => (
            <figure key={`${figure.id}-${index}`} className="figure-item">
              <Thumbnail id={figure.id} alt={figure.caption || `Figure ${index + 1}`} />
              <figcaption>
                <strong>Figure {index + 1}</strong>{figure.caption ? ` : ${figure.caption}` : ''}
              </figcaption>
              <button type="button" className="figure-remove" title="Retirer la figure du texte"
                      onClick={() => onChange(removeFigure(content, figure.id))}>✕</button>
            </figure>
          ))}
        </div>
      )}
    </div>
  );
}
