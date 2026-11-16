import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, Info, X, XCircle, type LucideIcon } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info' | 'warning';
interface Toast { id: number; type: ToastType; title: string; message: string; }

interface ToastApi {
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);
const ICONS: Record<ToastType, LucideIcon> = { success: CheckCircle2, error: XCircle, info: Info, warning: AlertTriangle };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const remove = useCallback((id: number) => setToasts(list => list.filter(t => t.id !== id)), []);

  const push = useCallback((type: ToastType, title: string, message = '') => {
    const id = ++nextId.current;
    setToasts(list => [...list.slice(-3), { id, type, title, message }]);
    setTimeout(() => remove(id), type === 'error' ? 8000 : 5000);
  }, [remove]);

  const api = useMemo<ToastApi>(() => ({
    success: (t, m) => push('success', t, m),
    error: (t, m) => push('error', t, m),
    info: (t, m) => push('info', t, m),
    warning: (t, m) => push('warning', t, m),
  }), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-container" role="status" aria-live="polite">
        {toasts.map(t => {
          const Icon = ICONS[t.type];
          return (
          <div key={t.id} className={`toast toast-${t.type}`} onClick={() => remove(t.id)}>
            <span className="toast-icon" aria-hidden="true"><Icon size={17} strokeWidth={2.2} /></span>
            <div className="toast-content">
              <strong>{t.title}</strong>
              {t.message && <span>{t.message}</span>}
            </div>
            <button type="button" className="toast-close" aria-label="Fermer"
                    onClick={e => { e.stopPropagation(); remove(t.id); }}><X size={16} /></button>
          </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast doit être utilisé dans <ToastProvider>');
  return ctx;
}
