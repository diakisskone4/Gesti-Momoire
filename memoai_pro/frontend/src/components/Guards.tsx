import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { loginPathFor, type RoleCode } from '../lib/roles';

/** Page réservée aux utilisateurs connectés (et éventuellement à certains rôles). */
export function RequireAuth({ roles, children }: { roles?: RoleCode[]; children: ReactNode }) {
  const auth = useAuth();
  // Page d'un espace réservé (jury, admin...) : renvoi vers la connexion de CET espace.
  if (!auth.isLoggedIn) return <Navigate to={loginPathFor(roles?.[0])} replace />;
  if (roles && !auth.hasRole(...roles)) return <Navigate to={auth.homeRoute} replace />;
  return <>{children}</>;
}

/** Pages de connexion / inscription : un utilisateur connecté va dans son espace. */
export function GuestOnly({ children }: { children: ReactNode }) {
  const auth = useAuth();
  return auth.isLoggedIn ? <Navigate to={auth.homeRoute} replace /> : <>{children}</>;
}
