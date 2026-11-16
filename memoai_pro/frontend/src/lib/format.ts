import type { User } from './models';

const dateFmt = new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
const dateTimeFmt = new Intl.DateTimeFormat('fr-FR', {
  day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
});
const numberFmt = new Intl.NumberFormat('fr-FR');

export function formatDate(value?: string | null): string {
  if (!value) return '';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? '' : dateFmt.format(d);
}

export function formatDateTime(value?: string | Date | null): string {
  if (!value) return '';
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? '' : dateTimeFmt.format(d);
}

export function formatNumber(n: number, maxDecimals = 0): string {
  return maxDecimals ? n.toLocaleString('fr-FR', { maximumFractionDigits: maxDecimals }) : numberFmt.format(n);
}

export function timeAgo(value?: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "À l'instant";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `Il y a ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Il y a ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `Il y a ${days} jour${days > 1 ? 's' : ''}`;
  return formatDate(value);
}

export function initials(u?: Pick<User, 'first_name' | 'last_name' | 'email'> | null): string {
  if (!u) return '?';
  const value = `${u.first_name?.[0] ?? ''}${u.last_name?.[0] ?? ''}`.toUpperCase();
  return value || u.email?.[0]?.toUpperCase() || '?';
}

export function wordCount(text?: string | null): number {
  const trimmed = (text ?? '').trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

/** Déclenche le téléchargement d'un Blob dans le navigateur. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** 15500 → « 15 500 FCFA » */
export function formatPrice(amount: string | number, currency = 'XOF'): string {
  const value = Number(amount).toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  return currency === 'XOF' || currency === 'XAF' ? `${value} FCFA` : `${value} ${currency}`;
}
