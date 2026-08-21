import { Injectable, signal } from '@angular/core';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class OfflineService {
  isOnline = signal(navigator.onLine);
  isUpdateAvailable = signal(false);

  constructor(private swUpdate: SwUpdate) {
    // Surveiller l'état de la connexion
    window.addEventListener('online', () => this.isOnline.set(true));
    window.addEventListener('offline', () => this.isOnline.set(false));

    // Vérifier les mises à jour
    if (this.swUpdate.isEnabled) {
      this.swUpdate.versionUpdates
        .pipe(filter((evt): evt is VersionReadyEvent => evt.type === 'VERSION_READY'))
        .subscribe(() => {
          this.isUpdateAvailable.set(true);
        });
    }
  }

  // Vérifier si une mise à jour est disponible
  checkForUpdate(): void {
    if (this.swUpdate.isEnabled) {
      this.swUpdate.checkForUpdate().then(() => {
        console.log('✅ Mise à jour vérifiée');
      });
    }
  }

  // Appliquer la mise à jour
  applyUpdate(): void {
    if (this.swUpdate.isEnabled) {
      this.swUpdate.activateUpdate().then(() => {
        document.location.reload();
      });
    }
  }
}