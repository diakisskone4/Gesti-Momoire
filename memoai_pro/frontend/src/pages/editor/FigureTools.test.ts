import { describe, expect, it } from 'vitest';

import { figuresIn, insertLine, removeFigure } from './FigureTools';

describe('figures dans le texte', () => {
  it('insère la figure sur sa propre ligne après la ligne du curseur', () => {
    const text = 'Premier paragraphe.\nSecond paragraphe.';
    expect(insertLine(text, 5, '[Figure:3 | Carte]')).toBe('Premier paragraphe.\n[Figure:3 | Carte]\nSecond paragraphe.');
    expect(insertLine('', 0, '[Figure:3]')).toBe('[Figure:3]\n');
    expect(insertLine('Texte', 5, '[Figure:4]')).toBe('Texte\n[Figure:4]\n');
  });

  it('retrouve et retire les figures', () => {
    const text = 'A\n[Figure:3 | Carte du Mali]\nB\n[Figure:7]';
    expect(figuresIn(text).map(f => [f.id, f.caption])).toEqual([[3, 'Carte du Mali'], [7, '']]);
    expect(removeFigure(text, 3)).toBe('A\nB\n[Figure:7]');
  });
});
