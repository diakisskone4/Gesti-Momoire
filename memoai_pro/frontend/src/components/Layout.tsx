import { useEffect, useRef, useState, type ReactNode } from 'react';
import PullToRefresh from './PullToRefresh';
import { Link, NavLink, useLocation } from 'react-router-dom';
import {
  Bell, BookOpen, FilePlus2, LayoutDashboard, LayoutTemplate, LogOut, Menu, Moon, Scale, ShieldCheck, Sparkles, Sun,
  Trash2, UserRound, Users, X, type LucideIcon,
} from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { initials } from '../lib/format';
import { roleByCode } from '../lib/roles';
import { InstallButton } from '../pwa/PwaPrompts';
import Logo from './Logo';
import NotificationsPanel, { useUnreadCount } from './NotificationsPanel';
import '../styles/layout.css';

interface NavItem { path: string; icon: LucideIcon; label: string; short: string; }

const PROFILE: NavItem = { path: '/profile', icon: UserRound, label: 'Mon profil', short: 'Profil' };

const NAV: Record<string, NavItem[]> = {
  STUDENT: [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord', short: 'Accueil' },
    { path: '/projects', icon: BookOpen, label: 'Mes mémoires', short: 'Mémoires' },
    { path: '/projects/new', icon: FilePlus2, label: 'Nouveau mémoire', short: 'Nouveau' },
    { path: '/modeles', icon: LayoutTemplate, label: 'Modèles de mémoire', short: 'Modèles' },
    { path: '/assistant', icon: Sparkles, label: 'Assistant IA', short: 'Assistant' },
    { path: '/corbeille', icon: Trash2, label: 'Corbeille', short: 'Corbeille' },
  ],
  SUPERVISOR: [{ path: '/supervision', icon: Users, label: 'Mémoires encadrés', short: 'Encadrés' }],
  CO_SUPERVISOR: [{ path: '/supervision', icon: Users, label: 'Mémoires co-encadrés', short: 'Co-encadrés' }],
  JURY: [{ path: '/jury', icon: Scale, label: 'Mémoires à évaluer', short: 'À évaluer' }],
  ADMIN: [{ path: '/admin', icon: ShieldCheck, label: 'Administration', short: 'Admin' }],
};

const HEADLINES: Record<string, string> = {
  STUDENT: 'Votre mémoire, plus simple à construire.',
  SUPERVISOR: 'Suivez et validez le travail de vos étudiants.',
  CO_SUPERVISOR: 'Co-supervisez les mémoires qui vous sont confiés.',
  JURY: 'Évaluez les mémoires en phase de soutenance.',
  ADMIN: 'Supervisez la plateforme MemoAI Pro.',
};

/** `onRefresh` : sur téléphone, tirer la page vers le bas recharge ses données (comme une application). */
export default function Layout({ children, onRefresh }: { children: ReactNode; onRefresh?: () => unknown }) {
  const { user, logout, homeRoute } = useAuth();
  const { isDark, toggle } = useTheme();
  const location = useLocation();
  const [showNotifications, setShowNotifications] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const { count, refresh } = useUnreadCount();

  const role = user?.role ?? 'STUDENT';
  const roleLabel = roleByCode(role)?.label ?? 'Utilisateur';
  const mainItems = NAV[role] ?? NAV.STUDENT;
  const navItems = [...mainItems, PROFILE];
  // Barre d'onglets mobile : 5 entrées au maximum, le profil reste accessible par l'avatar.
  const tabItems = mainItems.length >= 4 ? mainItems.slice(0, 5) : navItems;

  // Le tiroir de navigation se referme à chaque changement de page.
  useEffect(() => { setDrawerOpen(false); setShowNotifications(false); }, [location.pathname]);

  // Les bandeaux flottants (installation, mise à jour) se placent au-dessus de la barre d'onglets.
  useEffect(() => {
    document.documentElement.classList.add('has-bottom-nav');
    return () => document.documentElement.classList.remove('has-bottom-nav');
  }, []);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setDrawerOpen(false);
    document.addEventListener('keydown', onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
    };
  }, [drawerOpen]);

  useEffect(() => {
    if (!showNotifications) return;
    const onClick = (e: MouseEvent) => {
      if (!wrapperRef.current?.contains(e.target as Node)) setShowNotifications(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setShowNotifications(false);
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [showNotifications]);

  const confirmLogout = () => {
    if (window.confirm('Êtes-vous sûr de vouloir vous déconnecter ?')) logout();
  };

  return (
    <div className="scope-layout">
      <div className={`app-shell${drawerOpen ? ' drawer-open' : ''}`}>
        <aside className="sidebar" id="app-sidebar" aria-label="Menu">
          <div className="sidebar-head">
            <Link className="brand" to={homeRoute}>
              <Logo size={38} className="brand-mark" />
              <span><strong>MemoAI</strong><small>PRO</small></span>
            </Link>
            <button type="button" className="drawer-close" onClick={() => setDrawerOpen(false)} aria-label="Fermer le menu">
              <X size={20} />
            </button>
          </div>

          <span className="nav-label">Navigation</span>
          <nav className="nav" aria-label="Navigation principale">
            {navItems.map(item => (
              <NavLink key={item.path} to={item.path} end className={({ isActive }) => (isActive ? 'active' : '')}>
                <item.icon size={18} strokeWidth={1.9} aria-hidden="true" /> <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="sidebar-bottom">
            <InstallButton className="sidebar-btn install-btn" />
            <button className="sidebar-btn theme-toggle" type="button" onClick={toggle}>
              {isDark ? <><Sun size={16} /> Mode clair</> : <><Moon size={16} /> Mode sombre</>}
            </button>
            <button className="sidebar-btn logout" type="button" onClick={confirmLogout}><LogOut size={16} /> Déconnexion</button>
          </div>
        </aside>

        <div className="sidebar-backdrop" onClick={() => setDrawerOpen(false)} aria-hidden="true" />

        <main className="main">
          <header className="topbar">
            <button type="button" className="menu-btn" onClick={() => setDrawerOpen(true)}
                    aria-label="Ouvrir le menu" aria-controls="app-sidebar" aria-expanded={drawerOpen}>
              <Menu size={22} />
            </button>
            <Link className="topbar-brand" to={homeRoute} aria-label="MemoAI Pro — accueil">
              <Logo size={32} className="brand-mark" />
              <strong>MemoAI</strong>
            </Link>
            <div className="topbar-title">
              <span className="eyebrow">ESPACE {roleLabel.toUpperCase()}</span>
              <h1>{HEADLINES[role] ?? HEADLINES.STUDENT}</h1>
            </div>
            <div className="topbar-actions">
              <button type="button" className="icon-btn theme-quick" onClick={toggle}
                      aria-label={isDark ? 'Passer en mode clair' : 'Passer en mode sombre'} title={isDark ? 'Mode clair' : 'Mode sombre'}>
                {isDark ? <Sun size={19} strokeWidth={1.9} /> : <Moon size={19} strokeWidth={1.9} />}
              </button>
              <div className="notification-wrapper" ref={wrapperRef}>
                <button className="icon-btn notification-btn" type="button" title="Notifications"
                        aria-expanded={showNotifications} aria-label={`Notifications (${count} non lues)`}
                        onClick={() => setShowNotifications(s => !s)}>
                  <Bell size={19} strokeWidth={1.9} />
                  {count > 0 && <span className="notification-badge">{count > 99 ? '99+' : count}</span>}
                </button>
                {showNotifications && (
                  <div className="notification-dropdown">
                    <NotificationsPanel onChange={refresh} onNavigate={() => setShowNotifications(false)} />
                  </div>
                )}
              </div>
              <Link className="top-avatar" to="/profile" aria-label="Mon profil" title="Mon profil">{initials(user)}</Link>
            </div>
          </header>

          <section className="layout-content">
            {onRefresh && <PullToRefresh onRefresh={onRefresh} />}
            <div className="page-enter" key={location.pathname}>{children}</div>
          </section>
        </main>

        <nav className="bottom-nav" aria-label="Navigation rapide">
          {tabItems.map(item => (
            <NavLink key={item.path} to={item.path} end
                     className={({ isActive }) => `tab${isActive ? ' active' : ''}${item.path === '/projects/new' ? ' tab-cta' : ''}`}>
              <span className="tab-icon"><item.icon size={21} strokeWidth={1.9} aria-hidden="true" /></span>
              <span className="tab-label">{item.short}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
