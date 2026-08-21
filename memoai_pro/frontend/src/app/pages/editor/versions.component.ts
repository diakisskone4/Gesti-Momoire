import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { VersionsService, Version } from '../../core/versions.service';

@Component({
  selector: 'app-versions-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3>📜 Historique des versions</h3>
          <button class="close-btn" (click)="close.emit()">✕</button>
        </div>

        <div class="modal-body">
          <div *ngIf="loading" class="loading-state">
            <div class="spinner"></div>
            <p>Chargement de l'historique...</p>
          </div>

          <div *ngIf="!loading && versions.length === 0" class="empty-state">
            <span class="empty-icon">📭</span>
            <p>Aucune version disponible</p>
          </div>

          <div *ngFor="let version of versions" class="version-item">
            <div class="version-header">
              <div class="version-info">
                <span class="version-number">Version {{ version.version_number }}</span>
                <span class="version-date">{{ version.created_at | date:'dd/MM/yyyy HH:mm' }}</span>
              </div>
              <div class="version-actions">
                <button class="btn-primary" (click)="restoreVersion(version.id!)" title="Restaurer">
                  ↩️ Restaurer
                </button>
                <button class="btn-secondary" (click)="viewVersion(version.id!)" title="Voir">
                  👁️ Voir
                </button>
              </div>
            </div>
            <div class="version-details">
              <strong>{{ version.title }}</strong>
              <p>{{ version.content | slice:0:150 }}...</p>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" (click)="close.emit()">Fermer</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      animation: fadeIn 0.2s ease;
    }

    .modal-content {
      background: var(--bg-card, #ffffff);
      border-radius: 17px;
      padding: 30px;
      max-width: 600px;
      width: 90%;
      max-height: 90vh;
      overflow-y: auto;
      animation: slideUp 0.3s ease;
      border: 1px solid var(--border-color, #e5eceb);
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .modal-header h3 {
      margin: 0;
      color: var(--text-primary, #173e3a);
      font-size: 20px;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: var(--text-muted, #748482);
      transition: color 0.2s;
    }

    .close-btn:hover {
      color: #be123c;
    }

    .loading-state {
      text-align: center;
      padding: 40px 20px;
      color: var(--text-muted, #748482);
    }

    .loading-state .spinner {
      width: 40px;
      height: 40px;
      margin: 0 auto 20px;
      border: 4px solid var(--border-color, #e5eceb);
      border-top-color: #0f766e;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .empty-state {
      text-align: center;
      padding: 40px 20px;
      color: var(--text-muted, #748482);
    }

    .empty-icon {
      font-size: 48px;
      display: block;
      margin-bottom: 12px;
    }

    .version-item {
      background: var(--bg-input, #f8fbfa);
      border: 1px solid var(--border-color, #e5eceb);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 12px;
      transition: all 0.2s;
    }

    .version-item:hover {
      border-color: #0f766e;
      box-shadow: var(--shadow-hover, 0 4px 12px rgba(0,0,0,0.08));
    }

    .version-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      flex-wrap: wrap;
      gap: 10px;
    }

    .version-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .version-number {
      font-weight: 700;
      color: #0f766e;
      font-size: 14px;
    }

    .version-date {
      font-size: 12px;
      color: var(--text-muted, #748482);
    }

    .version-actions {
      display: flex;
      gap: 8px;
    }

    .version-details strong {
      display: block;
      color: var(--text-primary, #173e3a);
      font-size: 14px;
      margin-bottom: 4px;
    }

    .version-details p {
      margin: 0;
      color: var(--text-muted, #748482);
      font-size: 13px;
      line-height: 1.5;
    }

    .btn-primary {
      border: none;
      border-radius: 8px;
      padding: 6px 14px;
      background: #0f766e;
      color: white;
      font-weight: 600;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-primary:hover {
      background: #0b625c;
      transform: translateY(-1px);
    }

    .btn-secondary {
      border: 1px solid var(--border-color, #dce7e5);
      border-radius: 8px;
      padding: 6px 14px;
      background: var(--bg-secondary, #ffffff);
      color: var(--text-secondary, #39514e);
      font-weight: 600;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-secondary:hover {
      border-color: #0f766e;
      color: #0f766e;
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      padding-top: 15px;
      border-top: 1px solid var(--border-color, #e5eceb);
      margin-top: 15px;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes slideUp {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    @media (max-width: 600px) {
      .modal-content {
        padding: 20px;
        width: 95%;
      }

      .version-header {
        flex-direction: column;
        align-items: flex-start;
      }

      .version-actions {
        width: 100%;
      }

      .version-actions button {
        flex: 1;
        text-align: center;
      }
    }
  `]
})
export class VersionsModalComponent implements OnInit {
  @Input() chapterId!: number;
  @Input() chapterTitle: string = '';
  @Output() close = new EventEmitter<void>();
  @Output() versionRestored = new EventEmitter<{ version: Version; chapterId: number }>();

  versions: Version[] = [];
  loading = true;

  constructor(private versionsService: VersionsService) {}

  ngOnInit(): void {
    this.loadVersions();
  }

  loadVersions(): void {
    this.loading = true;
    this.versionsService.list(this.chapterId).subscribe({
      next: (versions) => {
        this.versions = versions;
        this.loading = false;
      },
      error: (err) => {
        console.error('❌ Erreur chargement versions:', err);
        this.loading = false;
      }
    });
  }

  restoreVersion(versionId: number): void {
    if (!confirm(`Restaurer la version ${this.versions.find(v => v.id === versionId)?.version_number} ?`)) {
      return;
    }

    this.versionsService.restore(versionId, this.chapterId).subscribe({
      next: (version) => {
        console.log('✅ Version restaurée:', version);
        this.versionRestored.emit({ version, chapterId: this.chapterId });
        this.close.emit();
      },
      error: (err) => {
        console.error('❌ Erreur restauration:', err);
        alert('Impossible de restaurer cette version.');
      }
    });
  }

  viewVersion(versionId: number): void {
    // Ouvrir une vue de la version
    console.log('👁️ Voir la version:', versionId);
    // Implémenter la vue de version
  }
}