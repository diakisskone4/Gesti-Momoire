import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import AiText from '../components/AiText';

const EXEMPLE = `Je peux vous accompagner sur plusieurs aspects :

- **Structurer votre travail** : plan, problématique, annonce du plan
- **Citations et références** : normes APA, Chicago, etc. *(références à vérifier vous-même)*

## Méthode
1. **Introduction** générale`;

describe('AiText', () => {
  it("affiche la réponse de l'IA sans aucun symbole Markdown", () => {
    const { container } = render(<AiText text={EXEMPLE} />);
    expect(container.textContent).not.toMatch(/\*|#/);
    const items = container.querySelectorAll('ul li');
    expect(items).toHaveLength(2);
    expect(items[0].querySelector('strong')?.textContent).toBe('Structurer votre travail');
    expect(container.querySelector('ol li')?.textContent).toBe('Introduction générale');
  });
});
