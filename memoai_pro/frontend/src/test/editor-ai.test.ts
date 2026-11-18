import { describe, expect, it } from 'vitest';

import type { Chapter } from '../lib/models';
import { aiWritingQueue } from '../pages/editor/EditorPage';

let nextId = 1;
const ch = (title: string, type: string, content = '', parent: number | null = null): Chapter =>
  ({ id: nextId++, project: 1, parent, order: nextId, title, content, type, status: 'draft', version: 1 });

describe("Rédiger le mémoire avec l'IA", () => {
  it('rédige tout le plan sauf la dédicace, les remerciements et le texte déjà écrit', () => {
    const dedicace = ch('Dédicace', 'preliminary', '[Conseil du modèle : quelques lignes]');
    const remerciements = ch('Remerciements', 'preliminary');
    const resume = ch('Résumé', 'preliminary', '[Conseil du modèle : 200 à 300 mots]');
    const sigles = ch('Sigles et abréviations', 'preliminary');
    const liste = ch('Liste des tableaux et figures', 'preliminary');
    const intro = ch('Introduction générale', 'chapter');
    const chap1 = ch('Chapitre 1 : Revue de la littérature', 'chapter', 'Intro écrite par moi.');
    const sec11 = ch('Fondements théoriques', 'section', 'Écrit par moi.', chap1.id);
    const chap2 = ch('Chapitre 2 : Méthodologie', 'chapter', 'Intro écrite par moi.');
    ch('Modèle conceptuel', 'section', '[Sous-parties prévues : variables]', chap2.id);
    const biblio = ch('Bibliographie', 'back');

    const queue = aiWritingQueue([dedicace, remerciements, resume, sigles, liste, intro, chap1, sec11, chap2, biblio]
      .concat(ch('Modèle conceptuel', 'section', '', chap2.id)));
    const titles = queue.map(c => c.title);

    expect(titles).toEqual(['Introduction générale', 'Chapitre 2 : Méthodologie', 'Résumé', 'Sigles et abréviations']);
    expect(titles).not.toContain('Dédicace');
    expect(titles).not.toContain('Remerciements');
    expect(titles).not.toContain('Chapitre 1 : Revue de la littérature'); // entièrement rédigé
  });
});
