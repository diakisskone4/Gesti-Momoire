import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { GuestOnly, RequireAuth } from './components/Guards';
import { useAuth } from './context/AuthContext';

const LoginPage = lazy(() => import('./pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'));
const StaffPortalPage = lazy(() => import('./pages/auth/StaffPortalPage'));
const DashboardPage = lazy(() => import('./pages/student/DashboardPage'));
const ProjectsPage = lazy(() => import('./pages/student/ProjectsPage'));
const ProjectCreatePage = lazy(() => import('./pages/student/ProjectCreatePage'));
const AssistantPage = lazy(() => import('./pages/student/AssistantPage'));
const TemplatesPage = lazy(() => import('./pages/student/TemplatesPage'));
const EditorPage = lazy(() => import('./pages/editor/EditorPage'));
const SupervisionPage = lazy(() => import('./pages/staff/SupervisionPage'));
const AdminPage = lazy(() => import('./pages/staff/AdminPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const SharedPage = lazy(() => import('./pages/SharedPage'));

function Home() {
  const auth = useAuth();
  return <Navigate to={auth.isLoggedIn ? auth.homeRoute : '/login'} replace />;
}

const guest = (el: JSX.Element) => <GuestOnly>{el}</GuestOnly>;

export default function App() {
  return (
    <Suspense fallback={<div className="page-loading" role="status">Chargement…</div>}>
      <Routes>
        <Route path="/" element={<Home />} />

        {/* Espace étudiant : connexion / inscription */}
        <Route path="/login" element={guest(<LoginPage />)} />
        <Route path="/register" element={guest(<RegisterPage />)} />

        {/* Espace enseignants & administration */}
        <Route path="/pro" element={guest(<StaffPortalPage mode="login" />)} />
        <Route path="/pro/register" element={guest(<StaffPortalPage mode="register" />)} />
        <Route path="/pro/login/:role" element={guest(<LoginPage />)} />
        <Route path="/pro/register/:role" element={guest(<RegisterPage />)} />

        {/* Étudiant */}
        <Route path="/dashboard" element={<RequireAuth roles={['STUDENT']}><DashboardPage /></RequireAuth>} />
        <Route path="/projects" element={<RequireAuth roles={['STUDENT']}><ProjectsPage /></RequireAuth>} />
        <Route path="/projects/new" element={<RequireAuth roles={['STUDENT']}><ProjectCreatePage /></RequireAuth>} />
        <Route path="/projects/:id/editor" element={<RequireAuth roles={['STUDENT']}><EditorPage /></RequireAuth>} />
        <Route path="/modeles" element={<RequireAuth roles={['STUDENT']}><TemplatesPage /></RequireAuth>} />
        <Route path="/assistant" element={<RequireAuth roles={['STUDENT']}><AssistantPage /></RequireAuth>} />

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
