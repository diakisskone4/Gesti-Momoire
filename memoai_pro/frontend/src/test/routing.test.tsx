import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { configure } from '@testing-library/react';

// Premier chargement des pages en lazy-loading : plus lent sous jsdom.
configure({ asyncUtilTimeout: 8000 });

import App from '../App';
import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';
import { ToastProvider } from '../context/ToastContext';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ThemeProvider><ToastProvider><AuthProvider><App /></AuthProvider></ToastProvider></ThemeProvider>
    </MemoryRouter>,
  );
}

function loginAs(role: string) {
  localStorage.setItem('memoai_access', 'token');
  localStorage.setItem('memoai_refresh', 'refresh');
  localStorage.setItem('memoai_user', JSON.stringify({ id: 1, email: 'a@b.c', first_name: 'Awa', last_name: 'Diallo', full_name: 'Awa Diallo', role }));
}

describe('routes', () => {
  beforeEach(() => {
    localStorage.clear();
    // Pas de backend pendant les tests : toute requête échoue immédiatement.
    vi.stubGlobal('fetch', () => Promise.reject(new TypeError('offline')));
  });

  it('affiche la connexion étudiante par défaut', async () => {
    renderAt('/');
    expect(await screen.findByRole('heading', { name: 'Connectez-vous' })).toBeInTheDocument();
    expect(screen.getByText('Bon retour')).toBeInTheDocument();
  });

  it('affiche la connexion du rôle choisi dans l’espace pro', async () => {
    renderAt('/pro/login/encadreur');
    expect(await screen.findByText('Connexion encadreur')).toBeInTheDocument();
  });

  it('redirige un rôle inconnu vers le portail pro', async () => {
    renderAt('/pro/login/pirate');
    expect(await screen.findByText('Quel est votre profil ?')).toBeInTheDocument();
  });

  it('protège les pages privées', async () => {
    renderAt('/admin');
    expect(await screen.findByRole('heading', { name: 'Connectez-vous' })).toBeInTheDocument();
  });

  it("renvoie un utilisateur connecté vers l'espace de son rôle", async () => {
    loginAs('JURY');
    renderAt('/admin');
    expect(await screen.findByRole('heading', { name: 'Mémoires à évaluer' })).toBeInTheDocument();
  });
});
