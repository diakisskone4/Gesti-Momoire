import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { describeError } from '../api/client';
import { notificationsApi } from '../api/services';
import { useAuth } from '../context/AuthContext';
import type { AppNotification } from '../lib/models';
import { timeAgo } from '../lib/format';

const POLL_MS = 30000;

/** Nombre de notifications non lues, actualisé toutes les 30 secondes. */
export function useUnreadCount() {
  const [count, setCount] = useState(0);
  const refresh = useCallback(() => {
    notificationsApi.unreadCount().then(r => setCount(r.count)).catch(() => undefined);
  }, []);
  useEffect(() => {
    refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') refresh();
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [refresh]);
  return { count, refresh };
}

export default function NotificationsPanel({ onChange, onNavigate }: { onChange: () => void; onNavigate: () => void }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<AppNotification[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    notificationsApi.list().then(setItems).catch(err => setError(describeError(err)));
  }, []);

  const open = (n: AppNotification) => {
    if (!n.read) {
      notificationsApi.markRead(n.id).then(onChange).catch(() => undefined);
      setItems(list => list?.map(x => (x.id === n.id ? { ...x, read: true } : x)) ?? null);
    }
    if (n.target_type === 'project') {
      const target = user?.role === 'STUDENT' ? `/projects/${n.target_id}/editor`
        : user?.role === 'JURY' ? '/jury' : user?.role === 'ADMIN' ? '/admin' : '/supervision';
      onNavigate();
      navigate(target);
    }
  };

  const markAll = () => {
    notificationsApi.markAllRead().then(() => {
      setItems(list => list?.map(x => ({ ...x, read: true })) ?? null);
      onChange();
    }).catch(err => setError(describeError(err)));
  };

  const unread = items?.filter(n => !n.read).length ?? 0;

  return (
    <div className="notif-panel">
      <div className="notif-head">
        <strong>Notifications</strong>
        {unread > 0 && <button type="button" className="link-btn" onClick={markAll}>Tout marquer comme lu</button>}
      </div>
      {error && <p className="notif-empty">{error}</p>}
      {!error && items === null && <p className="notif-empty">Chargement…</p>}
      {items?.length === 0 && <p className="notif-empty">📭 Aucune notification</p>}
      <ul className="notif-list">
        {items?.map(n => (
          <li key={n.id}>
            <button type="button" className={`notif-item${n.read ? '' : ' unread'}`} onClick={() => open(n)}>
              <span className="notif-text">
                <strong>{n.actor_name ?? 'MemoAI'}</strong> {n.verb}
                {n.description && <em>« {n.description} »</em>}
              </span>
              <small>{timeAgo(n.created_at)}</small>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
