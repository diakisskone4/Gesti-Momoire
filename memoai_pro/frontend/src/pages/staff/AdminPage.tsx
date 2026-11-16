import { useCallback, useEffect, useState } from 'react';

import { describeError } from '../../api/client';
import { adminApi } from '../../api/services';
import Layout from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { formatDate, formatNumber } from '../../lib/format';
import type { AdminStats, AdminUser } from '../../lib/models';
import { LEVEL_LABELS, PROJECT_STATUS_LABELS, ROLES, type RoleCode } from '../../lib/roles';
import '../../styles/workspace.css';

const STATUS_KEYS = ['DRAFT', 'IN_PROGRESS', 'REVIEW', 'VALIDATED', 'ARCHIVED'];
const pct = (value: number | undefined, total: number) => (total ? Math.round(((value ?? 0) / total) * 100) : 0);

/** Espace administrateur : tableau de bord et gestion des utilisateurs (§3.17). */
export default function AdminPage() {
  const { user: me } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roleFilter, setRoleFilter] = useState<RoleCode | ''>('');
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const loadStats = useCallback(() => {
    adminApi.stats().then(setStats).catch(() => setError('Impossible de charger les statistiques.'));
  }, []);

  const loadUsers = useCallback(() => {
    setLoadingUsers(true);
    adminApi.users({ role: roleFilter || undefined, search: debounced || undefined })
      .then(setUsers)
      .catch(() => setError('Impossible de charger les utilisateurs.'))
      .finally(() => setLoadingUsers(false));
  }, [roleFilter, debounced]);

  useEffect(loadStats, [loadStats]);
  useEffect(loadUsers, [loadUsers]);

  const update = async (u: AdminUser, data: Partial<AdminUser>, success: string) => {
    setError('');
    setMessage('');
    try {
      const updated = await adminApi.updateUser(u.id, data);
      setUsers(list => list.map(x => (x.id === updated.id ? updated : x)));
      setMessage(success);
      loadStats();
    } catch (err) {
      setError(describeError(err, 'Action impossible.'));
      loadUsers();
    }
  };

  const changeRole = (u: AdminUser, role: RoleCode) => {
    const label = ROLES.find(r => r.code === role)?.label;
    if (!window.confirm(`Attribuer le rôle « ${label} » à ${u.full_name} ?`)) return;
    update(u, { role }, `${u.full_name} est maintenant ${label}.`);
  };

  const toggleActive = (u: AdminUser) => {
    const activate = !u.is_active;
    if (!activate && !window.confirm(`Suspendre ${u.full_name} ? Cette personne ne pourra plus se connecter.`)) return;
    update(u, { is_active: activate }, activate ? `${u.full_name} a été réactivé.` : `${u.full_name} a été suspendu.`);
  };

  const remove = async (u: AdminUser) => {
    if (!window.confirm(`Supprimer définitivement ${u.full_name} et toutes ses données ? Cette action est irréversible.`)) return;
    try {
      await adminApi.deleteUser(u.id);
      setUsers(list => list.filter(x => x.id !== u.id));
      setMessage(`${u.full_name} a été supprimé.`);
      loadStats();
    } catch (err) {
      setError(describeError(err, 'Suppression impossible.'));
    }
  };

  return (
    <Layout>
      <div className="scope-ws">
        <div className="ws">
          <div className="ws-head">
            <div>
              <span className="eyebrow">Administration</span>
              <h2>Tableau de bord de la plateforme</h2>
              <p>Utilisateurs, mémoires, paiements et usage de l'IA.</p>
            </div>
            <button className="btn" onClick={() => { loadStats(); loadUsers(); }}>↻ Actualiser</button>
          </div>

          {stats && (
            <>
              <div className="stats">
                <div className="stat accent"><strong>{stats.users_total}</strong><span>Utilisateurs ({stats.users_active} actifs)</span></div>
                <div className="stat"><strong>{stats.projects_total}</strong><span>Mémoires créés</span></div>
                <div className="stat"><strong>{formatNumber(stats.revenue, 2)} €</strong><span>Revenus ({stats.payments_succeeded} paiements)</span></div>
                <div className="stat"><strong>{stats.conversion_rate} %</strong><span>Taux de conversion</span></div>
                <div className="stat"><strong>{formatNumber(stats.templates_revenue)} FCFA</strong><span>Modèles vendus ({stats.templates_sold})</span></div>
                <div className="stat"><strong>{stats.ai_tasks_total}</strong><span>Générations IA</span></div>
              </div>
              <div className="two-cols">
                <section className="panel">
                  <h3>Utilisateurs par rôle</h3>
                  <div className="bars">
                    {ROLES.map(r => (
                      <div className="bar-row" key={r.code}>
                        <span>{r.icon} {r.label}</span>
                        <span className="bar"><i style={{ width: `${pct(stats.users_by_role[r.code], stats.users_total)}%` }} /></span>
                        <span className="num">{stats.users_by_role[r.code] ?? 0}</span>
                      </div>
                    ))}
                  </div>
                </section>
                <section className="panel">
                  <h3>Mémoires par statut</h3>
                  <div className="bars">
                    {STATUS_KEYS.map(s => (
                      <div className="bar-row" key={s}>
                        <span>{PROJECT_STATUS_LABELS[s]}</span>
                        <span className="bar"><i style={{ width: `${pct(stats.projects_by_status[s], stats.projects_total)}%` }} /></span>
                        <span className="num">{stats.projects_by_status[s] ?? 0}</span>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            </>
          )}

          <div className="ws-head"><div><h2 style={{ fontSize: 20 }}>Gestion des utilisateurs</h2></div></div>

          <div className="toolbar">
            <div className="tabs" role="tablist">
              <button className={`tab${!roleFilter ? ' active' : ''}`} role="tab" aria-selected={!roleFilter} onClick={() => setRoleFilter('')}>Tous</button>
              {ROLES.map(r => (
                <button key={r.code} className={`tab${roleFilter === r.code ? ' active' : ''}`} role="tab"
                        aria-selected={roleFilter === r.code} onClick={() => setRoleFilter(r.code)}>{r.label}</button>
              ))}
            </div>
            <input className="search" type="search" placeholder="Nom, email, université..." value={search}
                   onChange={e => setSearch(e.target.value)} aria-label="Rechercher un utilisateur" />
          </div>

          {error && <div className="error">{error}</div>}
          {message && <div className="ok">{message}</div>}

          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Utilisateur</th><th>Rôle</th><th>Établissement</th><th className="num">Mémoires</th><th>Inscrit le</th><th>Statut</th><th /></tr>
              </thead>
              <tbody>
                {loadingUsers && <tr><td colSpan={7} className="muted">Chargement...</td></tr>}
                {!loadingUsers && !users.length && <tr><td colSpan={7} className="muted">Aucun utilisateur.</td></tr>}
                {!loadingUsers && users.map(u => (
                  <tr key={u.id}>
                    <td><strong style={{ color: 'var(--text-primary)' }}>{u.full_name}</strong><br /><span className="muted">{u.email}</span></td>
                    <td>
                      <select value={u.role} disabled={u.id === me?.id} aria-label={`Rôle de ${u.full_name}`}
                              onChange={e => changeRole(u, e.target.value as RoleCode)}>
                        {ROLES.map(r => <option key={r.code} value={r.code}>{r.label}</option>)}
                      </select>
                    </td>
                    <td>{u.university || '—'}<br /><span className="muted">{u.academic_title || (u.level ? LEVEL_LABELS[u.level] : '')}</span></td>
                    <td className="num">{u.projects_count}</td>
                    <td>{formatDate(u.created_at)}</td>
                    <td><span className={`badge ${u.is_active ? 'VALIDATED' : 'ARCHIVED'}`}>{u.is_active ? 'Actif' : 'Suspendu'}</span></td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {u.id === me?.id ? <span className="muted">vous</span> : (
                        <>
                          <button className={`btn${u.is_active ? ' warn' : ''}`} onClick={() => toggleActive(u)}>
                            {u.is_active ? 'Suspendre' : 'Réactiver'}
                          </button>{' '}
                          <button className="btn danger" onClick={() => remove(u)} aria-label={`Supprimer ${u.full_name}`}>🗑</button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  );
}
