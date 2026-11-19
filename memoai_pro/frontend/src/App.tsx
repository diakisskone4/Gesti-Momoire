import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes, useParams } from 'react-router-dom';

import { GuestOnly, RequireAuth } from './components/Guards';
import { useAuth } from './context/AuthContext';
import { STAFF_ROLES, forgotPath, loginPath, registerPath, roleBySlug } from './lib/roles';

const LoginPage = lazy(() => import('./pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/student/DashboardPage'));
const ProjectsPage = lazy(() => import('./pages/student/ProjectsPage'));
const ProjectCreatePage = lazy(() => import('./pages/student/ProjectCreatePage'));
const AssistantPage = lazy(() => import('./pages/student/AssistantPage'));
const TemplatesPage = lazy(() => import('./pages/student/TemplatesPage'));
const EditorPage = lazy(() => import('./pages/editor/EditorPage'));
const SupervisionPage = lazy(() => import('./pages/staff/SupervisionPage'));
const AdminPage = lazy(() => import('./pages/staff/AdminPage'));
const TrashPage = lazy(() => import('./pages/student/TrashPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const ForgotPasswordPage = lazy(() => import('./pages/auth/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('./pages/auth/ResetPasswordPage'));
const SharedPage = lazy(() => import('./pages/SharedPage'));

function Home() {
  const auth = useAuth();
  return <Navigate to={auth.isLoggedIn ? auth.homeRoute : '/login'} replace />;
}

const guest = (el: JSX.Element) => <GuestOnly>{el}</GuestOnly>;

/** Anciennes adresses /pro/login/:role et /pro/register/:role (liens déjà envoyés) → nouvel espace du rôle. */
function LegacyStaffRedirect({ mode }: { mode: 'login' | 'register' }) {
  const role = roleBySlug(useParams().role);
  if (!role || role.code === 'STUDENT') return <Navigate to="/" replace />;
  return <Navigate to={mode === 'login' ? loginPath(role) : registerPath(role)} replace />;
}

export default function App() {
  return (
    <Suspense fallback={<div className="page-loading" role="status">Chargement…</div>}>
      <Routes>
        <Route path="/" element={<Home />} />

        {/* Chaque rôle a son propre espace de connexion / inscription, sans lien vers les autres. */}
        <Route path="/login" element={guest(<LoginPage roleCode="STUDENT" />)} />
        <Route path="/register" element={guest(<RegisterPage roleCode="STUDENT" />)} />
        <Route path="/mot-de-passe-oublie" element={guest(<ForgotPasswordPage roleCode="STUDENT" />)} />
        <Route path="/reinitialiser-mot-de-passe" element={<ResetPasswordPage />} />
        {STAFF_ROLES.map(r => (
          <Route key={`${r.code}-login`} path={loginPath(r)} element={guest(<LoginPage key={r.code} roleCode={r.code} />)} />
        ))}
        {STAFF_ROLES.map(r => (
          <Route key={`${r.code}-forgot`} path={forgotPath(r)} element={guest(<ForgotPasswordPage key={r.code} roleCode={r.code} />)} />
        ))}
        {STAFF_ROLES.map(r => (
          <Route key={`${r.code}-register`} path={registerPath(r)} element={guest(<RegisterPage key={r.code} roleCode={r.code} />)} />
        ))}
        <Route path="/pro/login/:role" element={<LegacyStaffRedirect mode="login" />} />
        <Route path="/pro/register/:role" element={<LegacyStaffRedirect mode="register" />} />

        {/* Étudiant */}
        <Route path="/dashboard" element={<RequireAuth roles={['STUDENT']}><DashboardPage /></RequireAuth>} />
        <Route path="/projects" element={<RequireAuth roles={['STUDENT']}><ProjectsPage /></RequireAuth>} />
        <Route path="/projects/new" element={<RequireAuth roles={['STUDENT']}><ProjectCreatePage /></RequireAuth>} />
        <Route path="/projects/:id/editor" element={<RequireAuth roles={['STUDENT']}><EditorPage /></RequireAuth>} />
        <Route path="/modeles" element={<RequireAuth roles={['STUDENT']}><TemplatesPage /></RequireAuth>} />
        <Route path="/assistant" element={<RequireAuth roles={['STUDENT']}><AssistantPage /></RequireAuth>} />
        <Route path="/corbeille" element={<RequireAuth roles={['STUDENT']}><TrashPage /></RequireAuth>} />

        {/* Encadreur / co-encadreur, jury, administrateur */}
        <Route path="/supervision" element={
          <RequireAuth roles={['SUPERVISOR', 'CO_SUPERVISOR']}><SupervisionPage key="supervised" scope="supervised" /></RequireAuth>
        } />
        <Route path="/jury" element={<RequireAuth roles={['JURY']}><SupervisionPage key="jury" scope="jury" /></RequireAuth>} />
        <Route path="/admin" element={<RequireAuth roles={['ADMIN']}><AdminPage /></RequireAuth>} />

        {/* Commun */}
        <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
        <Route path="/share/:token" element={<SharedPage />} />

        <Route path="*" element={<Home />} />
      </Routes>
    </Suspense>
  );
}
