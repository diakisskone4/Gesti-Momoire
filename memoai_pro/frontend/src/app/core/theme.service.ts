import { Injectable, signal, effect } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'memoai_theme';
  
  isDark = signal<boolean>(this.getStoredTheme());

  constructor() {
    this.applyTheme(this.isDark());
    
    effect(() => {
      this.applyTheme(this.isDark());
      localStorage.setItem(this.THEME_KEY, JSON.stringify(this.isDark()));
    });
  }

  toggleTheme(): void {
    this.isDark.update(value => !value);
  }

  private getStoredTheme(): boolean {
    const stored = localStorage.getItem(this.THEME_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return false;
      }
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  private applyTheme(isDark: boolean): void {
    if (isDark) {
      document.documentElement.classList.add('dark-theme');
    } else {
      document.documentElement.classList.remove('dark-theme');
    }
  }
}