import type { ReactNode } from 'react';

/**
 * Affichage professionnel d'un texte produit par l'IA : paragraphes, listes à puces ou numérotées,
 * libellés « Titre : explication » mis en valeur typographiquement — sans aucun symbole Markdown.
 * Le serveur retire déjà la mise en forme Markdown ; ce nettoyage est un filet de sécurité.
 */
export function stripMarkdown(text: string): string {
  return text
    .replace(/^\s*```.*$/gm, '')
    .replace(/^\s*([-*_])(\s*\1){2,}\s*$/gm, '')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/^(\s*)[-*+]\s+/gm, '$1• ')
    .replace(/\[([^\]\n]+)\]\((https?:\/\/[^)\s]+)\)/g, '$1 ($2)')
    .replace(/(\*\*|__)(?=\S)([\s\S]+?)(?<=\S)\1/g, '$2')
    .replace(/(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])/g, '$1')
    .replace(/`([^`\n]+)`/g, '$1')
    .replace(/\*\*/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const BULLET = /^\s*•\s+/;
const NUMBERED = /^\s*(\d+)[.)]\s+/;
// « Structurer votre travail : plan, problématique » → libellé mis en valeur
const LABELLED = /^([^:.!?]{2,60}?)\s?:\s+(.+)$/;

function itemContent(text: string): ReactNode {
  const m = text.match(LABELLED);
  return m ? <><strong>{m[1]}</strong> : {m[2]}</> : text;
}

type Block = { kind: 'p'; lines: string[] } | { kind: 'ul' | 'ol'; items: string[]; start: number };

function toBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  for (const line of stripMarkdown(text).split('\n')) {
    const last = blocks[blocks.length - 1];
    if (!line.trim()) {
      blocks.push({ kind: 'p', lines: [] });
      continue;
    }
    const bullet = line.match(BULLET);
    const numbered = line.match(NUMBERED);
    if (bullet || numbered) {
      const kind = bullet ? 'ul' : 'ol';
      const item = line.replace(bullet ? BULLET : NUMBERED, '');
      if (last && last.kind === kind) last.items.push(item);
      else blocks.push({ kind, items: [item], start: numbered ? Number(numbered[1]) : 1 });
      continue;
    }
    if (last && last.kind === 'p') last.lines.push(line.trim());
    else blocks.push({ kind: 'p', lines: [line.trim()] });
  }
  return blocks.filter(b => (b.kind === 'p' ? b.lines.length > 0 : b.items.length > 0));
}

export default function AiText({ text, className = '' }: { text: string; className?: string }) {
  return (
    <div className={`ai-text ${className}`}>
      {toBlocks(text).map((b, i) => {
        if (b.kind === 'p') return <p key={i}>{b.lines.join(' ')}</p>;
        const items = b.items.map((it, j) => <li key={j}>{itemContent(it)}</li>);
        return b.kind === 'ul' ? <ul key={i}>{items}</ul> : <ol key={i} start={b.start}>{items}</ol>;
      })}
    </div>
  );
}
