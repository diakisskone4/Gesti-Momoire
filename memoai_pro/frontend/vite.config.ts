/// <reference types="vitest" />
import { readFileSync } from 'node:fs';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Génère /sw.js au build : le service worker reçoit la liste exacte des fichiers
 * à pré-cacher (noms versionnés par Vite) et un numéro de version unique, ce qui
 * déclenche la proposition de mise à jour chez les utilisateurs à chaque déploiement.
 */
function pwaServiceWorker(): Plugin {
  const publicFiles = [
    '/', '/index.html', '/boot.css', '/brand/memoai-mark.png', '/manifest.webmanifest', '/favicon.ico',
    '/icons/icon-192x192.png', '/icons/icon-512x512.png', '/icons/maskable-192x192.png',
    '/icons/maskable-512x512.png', '/icons/apple-touch-icon.png', '/icons/favicon-32x32.png',
  ];
  return {
    name: 'pwa-service-worker',
    apply: 'build',
    generateBundle(_options, bundle) {
      const assets = Object.keys(bundle)
        .filter(file => /\.(js|css|woff2?|png|svg|jpg|webp)$/.test(file))
        .map(file => `/${file}`);
      const template = readFileSync(new URL('./src/pwa/sw-template.js', import.meta.url), 'utf-8');
      const source = template
        .replace('__BUILD_VERSION__', Date.now().toString(36))
        .replace('__PRECACHE_URLS__', JSON.stringify([...publicFiles, ...assets], null, 2));
      this.emitFile({ type: 'asset', fileName: 'sw.js', source });
    },
  };
}

export default defineConfig({
  plugins: [react(), pwaServiceWorker()],
  server: { port: 5173, strictPort: true, host: true },
  preview: { port: 4173, host: true },
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'], css: false, testTimeout: 20000, globals: true },
});
