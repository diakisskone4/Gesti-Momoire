import { configure, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../context/AuthContext';
import { ThemeProvider } from '../context/ThemeContext';
import { ToastProvider } from '../context/ToastContext';
import { formatPrice } from '../lib/format';
import TemplatesPage from '../pages/student/TemplatesPage';

configure({ asyncUtilTimeout: 8000 });

const TEMPLATE = {
  slug: 'licence-classique', name: 'Mémoire de Licence — Classique', tagline: 'Format universitaire', description: '',
  level: 'LICENCE', level_label: 'Licence', domain: 'Toutes disciplines', cover_style: 'classique',
  cover_label: 'Classique universitaire', accent_color: '#0f766e', price: '5000.00', currency: 'XOF', owned: false,
  outline: [{ title: 'Introduction générale', type: 'chapter', sections: ['Problématique'] }], structure: null,
};

const json = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));

describe('formatPrice', () => {
  it('affiche les francs CFA', () => {
    expect(formatPrice('5000.00', 'XOF')).toMatch(/^5\s?000 FCFA$/u);
  });
});

describe('TemplatesPage', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('memoai_access', 't');
    localStorage.setItem('memoai_refresh', 'r');
    localStorage.setItem('memoai_user', JSON.stringify({ id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', full_name: 'A B', role: 'STUDENT' }));
  });

  it("affiche le prix et redirige vers SasPay à l'achat", async () => {
    const assign = vi.fn();
    vi.stubGlobal('location', { ...window.location, assign });
    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/modeles/licence-classique/purchase/') && init?.method === 'POST') {
        return json({ id: 7, checkout_url: 'https://pay.saspay.me/c/xyz', status: 'PENDING' }, 201);
      }
      if (url.includes('/cover/')) return json({ html: '<p>garde</p>' });
      if (url.includes('/modeles/achats/')) return json([]);
      if (url.includes('/modeles/')) return json([TEMPLATE]);
      return json({ count: 0 });
    }));

    render(
      <MemoryRouter initialEntries={['/modeles']}>
        <ThemeProvider><ToastProvider><AuthProvider><TemplatesPage /></AuthProvider></ToastProvider></ThemeProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText(TEMPLATE.name)).toBeInTheDocument();
    expect(screen.getAllByText(/(^|\D)5\s?000 FCFA/u).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: 'Acheter' }));
    await vi.waitFor(() => expect(assign).toHaveBeenCalledWith('https://pay.saspay.me/c/xyz'));
    vi.unstubAllGlobals();
  });
});
