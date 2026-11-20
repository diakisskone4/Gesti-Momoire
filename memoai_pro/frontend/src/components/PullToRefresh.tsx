import { useEffect, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';

const TRIGGER = 64;   // distance (px) à partir de laquelle on recharge
const MAX = 96;

/**
 * « Tirer pour actualiser », comme dans les applications mobiles : en haut de la page,
 * glisser le doigt vers le bas recharge les données. Sans effet à la souris.
 */
export default function PullToRefresh({ onRefresh }: { onRefresh: () => unknown }) {
  const [pull, setPull] = useState(0);
  const [busy, setBusy] = useState(false);
  const start = useRef<number | null>(null);
  const pullRef = useRef(0);
  const refresh = useRef(onRefresh);
  refresh.current = onRefresh;

  useEffect(() => {
    document.documentElement.classList.add('has-ptr');
    const onStart = (e: TouchEvent) => {
      start.current = window.scrollY <= 0 && e.touches.length === 1 ? e.touches[0].clientY : null;
    };
    const onMove = (e: TouchEvent) => {
      if (start.current === null) return;
      const dy = e.touches[0].clientY - start.current;
      if (dy <= 0 || window.scrollY > 0) { pullRef.current = 0; setPull(0); return; }
      pullRef.current = Math.min(MAX, dy * 0.5);
      setPull(pullRef.current);
    };
    const onEnd = async () => {
      const reached = pullRef.current >= TRIGGER;
      start.current = null;
      pullRef.current = 0;
      setPull(0);
      if (!reached) return;
      setBusy(true);
      navigator.vibrate?.(10);
      const minDelay = new Promise(r => setTimeout(r, 700));
      try { await Promise.all([Promise.resolve(refresh.current()), minDelay]); } finally { setBusy(false); }
    };
    window.addEventListener('touchstart', onStart, { passive: true });
    window.addEventListener('touchmove', onMove, { passive: true });
    window.addEventListener('touchend', onEnd);
    return () => {
      document.documentElement.classList.remove('has-ptr');
      window.removeEventListener('touchstart', onStart);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onEnd);
    };
  }, []);

  const shown = busy ? TRIGGER : pull;
  if (!shown) return null;
  return (
    <div className={`ptr${busy ? ' busy' : ''}${pull >= TRIGGER ? ' ready' : ''}`} style={{ height: shown }} role="status"
         aria-live="polite">
      <span className="ptr-icon" style={{ transform: busy ? undefined : `rotate(${pull * 3}deg)` }}>
        <RefreshCw size={18} strokeWidth={2.2} />
      </span>
      <span className="ptr-label">{busy ? 'Actualisation…' : pull >= TRIGGER ? 'Relâchez pour actualiser' : 'Tirez pour actualiser'}</span>
    </div>
  );
}
