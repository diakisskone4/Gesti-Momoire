import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, errorMessage, onSessionExpired, request, tokens } from '../api/client';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

describe('errorMessage', () => {
  it('formate les erreurs de champs DRF avec des libellés français', () => {
    expect(errorMessage({ email: ['Adresse déjà utilisée.'], password2: ['Différent.'] }))
      .toBe('Email : Adresse déjà utilisée. · Confirmation : Différent.');
  });
  it('privilégie error puis detail', () => {
    expect(errorMessage({ error: 'Boom' })).toBe('Boom');
    expect(errorMessage({ detail: 'Non authentifié.' })).toBe('Non authentifié.');
  });
  it('ignore les pages HTML', () => {
    expect(errorMessage('<!DOCTYPE html>', 'fallback')).toBe('fallback');
  });
});

describe('request', () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it('envoie le jeton JWT', async () => {
    tokens.save('A1', 'R1');
    fetchMock.mockResolvedValueOnce(json(200, { ok: true }));
    await request('/users/profile/');
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer A1');
  });

  it('renouvelle le jeton après un 401 puis rejoue la requête', async () => {
    tokens.save('OLD', 'R1');
    fetchMock
      .mockResolvedValueOnce(json(401, { detail: 'expired' }))
      .mockResolvedValueOnce(json(200, { access: 'NEW', refresh: 'R2' }))
      .mockResolvedValueOnce(json(200, { id: 1 }));
    await expect(request('/users/profile/')).resolves.toEqual({ id: 1 });
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer NEW');
    expect(tokens.refresh()).toBe('R2');
  });

  it('termine la session si le renouvellement échoue', async () => {
    tokens.save('OLD', 'R1');
    const expired = vi.fn();
    onSessionExpired(expired);
    fetchMock
      .mockResolvedValueOnce(json(401, {}))
      .mockResolvedValueOnce(json(401, {}));
    await expect(request('/users/profile/')).rejects.toBeInstanceOf(ApiError);
    expect(expired).toHaveBeenCalled();
    expect(tokens.access()).toBeNull();
  });

  it("signale un serveur injoignable", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    await expect(request('/users/login/', { method: 'POST', body: {} })).rejects.toMatchObject({ status: 0 });
  });

  it('remonte le message d’erreur du backend', async () => {
    fetchMock.mockResolvedValueOnce(json(400, { error: 'Code invalide' }));
    await expect(request('/x/')).rejects.toMatchObject({ status: 400, message: 'Code invalide' });
  });
});
