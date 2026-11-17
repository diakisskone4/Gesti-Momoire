import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { onSessionExpired, tokens } from '../api/client';
import { authApi } from '../api/services';
import type { AuthResponse, RegisterPayload, User } from '../lib/models';
import { homeFor, loginPathFor, type RoleCode } from '../lib/roles';

const USER_KEY = 'memoai_user';

function readUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw && tokens.access() ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

function storeUser(user: User | null): void {
  try {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_KEY);
  } catch { /* ignore */ }
}

interface AuthState {
  user: User | null;
  isLoggedIn: boolean;
  homeRoute: string;
  hasRole: (...roles: RoleCode[]) => boolean;
  login: (email: string, password: string, role?: RoleCode) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => void;
  setUser: (user: User) => void;
  refreshProfile: () => Promise<User>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [user, setUserState] = useState<User | null>(readUser);

  const setUser = useCallback((u: User | null) => {
    storeUser(u);
    setUserState(u);
  }, []);

  // Après déconnexion, chacun revient à la page de connexion de SON espace.
  const endSession = useCallback((role?: string | null) => {
    tokens.clear();
    setUser(null);
    navigate(loginPathFor(role), { replace: true });
  }, [navigate, setUser]);

  // Jeton de rafraîchissement expiré : retour à la page de connexion.
  useEffect(() => {
    onSessionExpired(() => endSession(readUser()?.role));
  }, [endSession]);

  // Synchronise la session entre onglets.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === USER_KEY || e.key === 'memoai_access') setUserState(readUser());
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const saveSession = useCallback((res: AuthResponse) => {
    tokens.save(res.access, res.refresh);
    setUser(res.user);
    return res.user;
  }, [setUser]);

  const value = useMemo<AuthState>(() => ({
    user,
    isLoggedIn: !!user && !!tokens.access(),
    homeRoute: homeFor(user?.role),
    hasRole: (...roles) => !!user && roles.includes(user.role),
    login: (email, password, role) => authApi.login(email, password, role).then(saveSession),
    register: payload => authApi.register(payload).then(saveSession),
    logout: () => {
      const refresh = tokens.refresh();
      if (refresh) authApi.logout(refresh).catch(() => undefined);
      endSession(user?.role);
    },
    setUser,
    refreshProfile: () => authApi.profile().then(u => { setUser(u); return u; }),
  }), [user, saveSession, endSession, setUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth doit être utilisé dans <AuthProvider>');
  return ctx;
}
