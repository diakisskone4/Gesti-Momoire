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

  it("affiche le prix et redirige vers Jɛmɛnipay à l'achat", async () => {
    const assign = vi.fn();
    vi.stubGlobal('location', { ...window.location, assign });
    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/modeles/licence-classique/purchase/') && init?.method === 'POST') {
        return json({ id: 7, provider: 'jemeni', checkout_url: 'https://jemeni.net/sandbox/pay/xyz', status: 'PENDING' }, 201);
      }
      if (url.includes('/cover/')) return json({ html: '<p>garde</p>' });
      if (url.includes('/modeles/achats/')) return json([]);
      if (url.includes('/modeles/paiement/')) return json({ mode: 'jemeni' });
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
    await vi.waitFor(() => expect(assign).toHaveBeenCalledWith('https://jemeni.net/sandbox/pay/xyz'));
    vi.unstubAllGlobals();
  });

  it('paie par mobile money : numéro affiché, référence déclarée, achat en vérification', async () => {
    const purchase = {
      id: 9, provider: 'mobile_money', status: 'PENDING', template_name: TEMPLATE.name, amount: '5000.00', currency: 'XOF',
      operator: '', payer_phone: '', transaction_reference: '', review_note: '', checkout_url: '',
    };
    const declared = vi.fn();
    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/purchase/')) return json(purchase, 201);
      if (url.includes('/achats/9/declare/')) {
        const body = JSON.parse(String(init?.body));
        declared(body);
        return json({ ...purchase, status: 'SUBMITTED', operator: body.operator, payer_phone: '76123456', transaction_reference: 'PP123456' });
      }
      if (url.includes('/cover/')) return json({ html: '<p>garde</p>' });
      if (url.includes('/modeles/achats/')) return json([]);
      if (url.includes('/modeles/paiement/')) {
        return json({ mode: 'mobile_money', holder: '', operators: [
          { code: 'orange', label: 'Orange Money', ussd: '#144#', steps: 'Composez #144#.', number: '70000001', number_display: '70 00 00 01' },
          { code: 'moov', label: 'Moov Money', ussd: '*166#', steps: 'Composez *166#.', number: '60000002', number_display: '60 00 00 02' },
        ] });
      }
      if (url.includes('/modeles/')) return json([TEMPLATE]);
      return json({ count: 0 });
    }));

    render(
      <MemoryRouter initialEntries={['/modeles']}>
        <ThemeProvider><ToastProvider><AuthProvider><TemplatesPage /></AuthProvider></ToastProvider></ThemeProvider>
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Acheter' }));
    fireEvent.click(await screen.findByRole('radio', { name: 'Moov Money' }));
    expect(screen.getByText('60 00 00 02')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: 'Orange Money' }));
    expect(screen.queryByText('60 00 00 02')).not.toBeInTheDocument();
    expect(screen.getByText('70 00 00 01')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Composer #144#' })).toHaveAttribute('href', 'tel:%23144%23');
    fireEvent.change(screen.getByLabelText(/Votre numéro/), { target: { value: '76 12 34 56' } });
    fireEvent.change(screen.getByLabelText(/Référence/), { target: { value: 'PP123456' } });
    fireEvent.click(screen.getByRole('button', { name: "J'ai payé" }));
    expect(await screen.findByText('Paiement en vérification')).toBeInTheDocument();
    expect(declared).toHaveBeenCalledWith({ operator: 'orange', phone: '76 12 34 56', reference: 'PP123456' });
    vi.unstubAllGlobals();
  });
});
