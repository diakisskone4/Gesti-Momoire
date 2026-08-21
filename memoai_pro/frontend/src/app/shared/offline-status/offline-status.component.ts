import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OfflineService } from '../../core/offline.service';

@Component({
  selector: 'app-offline-status',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="!offlineService.isOnline()" class="offline-banner">
      <span>📡</span>
      <span>Vous êtes hors ligne. Les modifications seront sauvegardées localement.</span>
      <button (click)="retryConnection()">🔄 Réessayer</button>
    </div>

    <div *ngIf="offlineService.isUpdateAvailable()" class="update-banner">
      <span>🔄</span>
      <span>Une nouvelle version est disponible !</span>
      <button (click)="applyUpdate()">🔄 Mettre à jour</button>
    </div>
  `,
  styles: [`
    .offline-banner {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: #f59e0b;
      color: #1a1a1a;
      padding: 12px 24px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      gap: 12px;
      z-index: 9999;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
      animation: slideUp 0.3s ease;
      max-width: 90%;
    }

    .update-banner {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      background: #0f766e;
      color: white;
      padding: 12px 24px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      gap: 12px;
      z-index: 9999;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
      animation: slideUp 0.3s ease;
      max-width: 90%;
    }

    .offline-banner button,
    .update-banner button {
      background: white;
      border: none;
      border-radius: 8px;
      padding: 6px 16px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      color: #0f766e;
    }

    .offline-banner button:hover,
    .update-banner button:hover {
      transform: scale(1.05);
    }

    @keyframes slideUp {
      from { opacity: 0; transform: translate(-50%, 20px); }
      to { opacity: 1; transform: translate(-50%, 0); }
    }

    @media (max-width: 600px) {
      .offline-banner,
      .update-banner {
        flex-direction: column;
        text-align: center;
        padding: 16px;
        bottom: 10px;
        width: 90%;
      }
    }
  `]
})
export class OfflineStatusComponent {
  constructor(public offlineService: OfflineService) {}

  retryConnection(): void {
    window.location.reload();
  }

  applyUpdate(): void {
    this.offlineService.applyUpdate();
  }
}