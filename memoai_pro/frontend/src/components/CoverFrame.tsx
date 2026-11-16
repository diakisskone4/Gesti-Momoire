import { useEffect, useRef, useState } from 'react';

// Page A4 à 96 ppp
const A4_WIDTH = 794;
const A4_HEIGHT = 1123;

/**
 * Affiche une page de garde (document HTML fourni par le backend) réduite à la largeur
 * disponible. L'iframe est isolée (sandbox sans scripts).
 */
export default function CoverFrame({ html, title, maxWidth }: { html: string | null; title: string; maxWidth?: number }) {
  const wrapper = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(maxWidth ?? 300);

  useEffect(() => {
    const el = wrapper.current;
    if (!el) return;
    const update = () => setWidth(Math.min(el.clientWidth || 300, maxWidth ?? Infinity));
    update();
    const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(update) : null;
    observer?.observe(el);
    return () => observer?.disconnect();
  }, [maxWidth]);

  const scale = width / A4_WIDTH;
  return (
    <div ref={wrapper} className="cover-frame" style={{ maxWidth }}>
      <div style={{ width, height: A4_HEIGHT * scale, overflow: 'hidden', position: 'relative' }}>
        {html ? (
          <iframe
            title={title}
            srcDoc={html}
            sandbox=""
            tabIndex={-1}
            style={{
              width: A4_WIDTH, height: A4_HEIGHT, border: 0, transform: `scale(${scale})`,
              transformOrigin: '0 0', pointerEvents: 'none', background: '#fff',
            }}
          />
        ) : (
          <div className="cover-frame-loading">Chargement…</div>
        )}
      </div>
    </div>
  );
}
