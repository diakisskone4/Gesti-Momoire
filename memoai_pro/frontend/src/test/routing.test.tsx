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

  it('donne à chaque rôle sa propre page de connexion', async () => {
    renderAt('/encadreur/login');
    expect(await screen.findByText('Connexion encadreur')).toBeInTheDocument();
  });

  it.each([
    ['/login', '/register'],
    ['/register', '/login'],
    ['/encadreur/login', '/encadreur/register'],
    ['/co-encadreur/register', '/co-encadreur/login'],
    ['/jury/login', '/jury/register'],
    ['/admin/register', '/admin/login'],
  ])("la page %s ne montre aucun lien vers l'espace d'un autre rôle", async (path, sibling) => {
    renderAt(path);
    await screen.findByRole('navigation', { name: 'Connexion ou inscription' });
    const own = new Set([path, sibling]);
    const links = screen.getAllByRole('link').map(a => a.getAttribute('href'));
    expect(links.filter(href => !own.has(href ?? ''))).toEqual([]);
    expect(screen.queryByText(/enseignants|Changer de profil|Vous n'êtes pas étudiant|Vous êtes étudiant/i)).toBeNull();
  });

  it('redirige les anciennes adresses /pro vers le nouvel espace', async () => {
    renderAt('/pro/login/jury');
    expect(await screen.findByText('Connexion jury')).toBeInTheDocument();
  });

  it('ne révèle aucun espace pour un rôle inconnu', async () => {
    renderAt('/pro/login/pirate');
    expect(await screen.findByRole('heading', { name: 'Connectez-vous' })).toBeInTheDocument();
    expect(screen.getByText('Bon retour')).toBeInTheDocument();
  });

  it("protège les pages privées en renvoyant vers la connexion de l'espace concerné", async () => {
    renderAt('/admin');
    expect(await screen.findByText('Connexion administrateur')).toBeInTheDocument();
  });

  it("renvoie un utilisateur connecté vers l'espace de son rôle", async () => {
    loginAs('JURY');
    renderAt('/admin');
    expect(await screen.findByRole('heading', { name: 'Mémoires à évaluer' })).toBeInTheDocument();
  });
});
