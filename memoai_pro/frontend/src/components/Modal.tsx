import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

interface Props {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}

/** Fenêtre modale : fermeture par Échap, clic à l'extérieur ou bouton ✕. */
export default function Modal({ title, onClose, children, footer, wide }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
      previous?.focus?.();
    };
  }, [onClose]);

  return (
    <div className="modal-overlay" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className={`modal-content${wide ? ' wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}
           tabIndex={-1} ref={ref}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Fermer"><X size={18} /></button>
        </div>
        {children}
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}
