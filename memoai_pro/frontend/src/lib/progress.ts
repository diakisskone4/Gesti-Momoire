import { wordCount } from './format';
import type { Chapter, Project } from './models';

const PLACEHOLDER = /^\s*(\[(Conseil du modèle|Sous-parties prévues)[^\]]*\]\s*)*$/s;
const NON_WRITTEN_TYPES = new Set(['preliminary', 'back']);
export const WORDS_PER_PAGE = 300;

/** Chapitre vide ou ne contenant qu'un conseil de modèle (pas encore rédigé). */
export function isPlaceholder(content?: string | null): boolean {
  return !content || PLACEHOLDER.test(content);
}

export function writtenWords(chapters: Chapter[]): number {
  return chapters.reduce((sum, c) => sum + (isPlaceholder(c.content) ? 0 : wordCount(c.content)), 0);
}

export interface ProjectProgress {
  words: number;
  targetWords: number;
  percent: number;
  chaptersTotal: number;
  chaptersStarted: number;
  emptyBlocks: number;
}

/** Avancement d'un mémoire : mots rédigés par rapport à l'objectif de pages, chapitres entamés. */
export function projectProgress(project: Project): ProjectProgress {
  const chapters = project.chapters ?? [];
  const words = writtenWords(chapters);
  const targetWords = Math.max(project.desired_pages ?? 40, 1) * WORDS_PER_PAGE;
  const main = chapters.filter(c => c.parent === null && !NON_WRITTEN_TYPES.has(c.type));
  const started = main.filter(c => !isPlaceholder(c.content)
    || chapters.some(s => s.parent === c.id && !isPlaceholder(s.content))).length;
  const emptyBlocks = chapters.filter(c => !NON_WRITTEN_TYPES.has(c.type) && isPlaceholder(c.content)).length;
  return {
    words,
    targetWords,
    percent: Math.min(100, Math.round((words / targetWords) * 100)),
    chaptersTotal: main.length,
    chaptersStarted: started,
    emptyBlocks,
  };
}
