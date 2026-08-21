import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ProjectsService } from '../../core/projects.service';

@Component({
  selector: 'app-export-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule
  ],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3>📄 Exporter le mémoire</h3>
          <button class="close-btn" (click)="close.emit()">✕</button>
        </div>

        <div class="modal-body">
          <p>Choisissez le format d'export :</p>

          <div class="format-options">
            <div 
              class="format-option"
              [class.selected]="selectedFormat === 'docx'"
              (click)="selectedFormat = 'docx'"
            >
              <span class="format-icon">📝</span>
              <span class="format-name">Word (DOCX)</span>
              <span class="format-desc">Format éditable</span>
            </div>

            <div 
              class="format-option"
              [class.selected]="selectedFormat === 'pdf'"
              (click)="selectedFormat = 'pdf'"
            >
              <span class="format-icon">📄</span>
              <span class="format-name">PDF</span>
              <span class="format-desc">Format universel</span>
            </div>

            <div 
              class="format-option"
              [class.selected]="selectedFormat === 'html'"
              (click)="selectedFormat = 'html'"
            >
              <span class="format-icon">🌐</span>
              <span class="format-name">HTML</span>
              <span class="format-desc">Pour le web</span>
            </div>
          </div>

          <div class="export-options">
            <label>
              <input type="checkbox" [(ngModel)]="includeChapters" />
              Inclure les chapitres
            </label>
            <label>
              <input type="checkbox" [(ngModel)]="includeBibliography" />
              Inclure la bibliographie
            </label>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" (click)="close.emit()">Annuler</button>
          <button class="btn-primary" (click)="export()" [disabled]="loading">
            {{ loading ? 'Export en cours...' : '📥 Exporter' }}
          </button>
        </div>

        <div *ngIf="error" class="error-message">
          ⚠ {{ error }}
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
      background: white;
      border-radius: 17px;
      padding: 30px;
      max-width: 500px;
      width: 90%;
      max-height: 90vh;
      overflow-y: auto;
      animation: slideUp 0.3s ease;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .modal-header h3 {
      margin: 0;
      color: #173e3a;
      font-size: 20px;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: #748482;
      transition: color 0.2s;
    }

    .close-btn:hover {
      color: #be123c;
    }

    .modal-body p {
      color: #748482;
      margin-bottom: 15px;
    }

    .format-options {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 10px;
      margin-bottom: 20px;
    }

    .format-option {
      border: 2px solid #e5eceb;
      border-radius: 12px;
      padding: 15px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .format-option:hover {
      border-color: #0f766e;
      transform: translateY(-2px);
    }

    .format-option.selected {
      border-color: #0f766e;
      background: #f0f9f8;
    }

    .format-icon {
      display: block;
      font-size: 28px;
      margin-bottom: 5px;
    }

    .format-name {
      display: block;
      font-weight: 600;
      color: #173e3a;
      font-size: 14px;
    }

    .format-desc {
      display: block;
      font-size: 11px;
      color: #748482;
    }

    .export-options {
      display: flex;
      gap: 20px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    .export-options label {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #39514e;
      font-size: 13px;
      cursor: pointer;
    }

    .export-options input[type="checkbox"] {
      width: 18px;
      height: 18px;
      accent-color: #0f766e;
      cursor: pointer;
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      padding-top: 15px;
      border-top: 1px solid #f0f5f4;
    }

    .btn-primary {
      border: none;
      border-radius: 9px;
      padding: 10px 20px;
      background: #0f766e;
      color: white;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-primary:hover:not(:disabled) {
      background: #0b625c;
      transform: translateY(-1px);
    }

    .btn-primary:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .btn-secondary {
      border: 1px solid #dce7e5;
      border-radius: 9px;
      padding: 10px 20px;
      background: white;
      color: #39514e;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-secondary:hover {
      border-color: #0f766e;
      color: #0f766e;
    }

    .error-message {
      margin-top: 15px;
      padding: 10px;
      background: #fff1f2;
      color: #be123c;
      border-radius: 9px;
      font-size: 13px;
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

      .format-options {
        grid-template-columns: 1fr;
      }

      .export-options {
        flex-direction: column;
        gap: 10px;
      }

      .modal-footer {
        flex-direction: column;
      }

      .modal-footer button {
        width: 100%;
      }
    }
  `]
})
export class ExportModalComponent {
  @Input() projectId!: number;
  @Input() projectTitle: string = '';
  @Output() close = new EventEmitter<void>();
  @Output() exported = new EventEmitter<{ format: string; url: string }>();

  selectedFormat: string = 'docx';
  includeChapters: boolean = true;
  includeBibliography: boolean = true;
  loading = false;
  error = '';

  constructor(private projectsService: ProjectsService) {}

  export(): void {
    this.loading = true;
    this.error = '';

    const data = {
      format: this.selectedFormat,
      include_chapters: this.includeChapters,
      include_bibliography: this.includeBibliography
    };

    this.projectsService.exportProject(this.projectId, data).subscribe({
      next: (response) => {
        console.log('✅ Export réussi:', response);
        this.loading = false;
        
        // Si c'est un blob, créer un lien de téléchargement
        if (response instanceof Blob) {
          const url = window.URL.createObjectURL(response);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${this.projectTitle}.${this.selectedFormat}`;
          a.click();
          window.URL.revokeObjectURL(url);
        }
        
        this.exported.emit({ format: this.selectedFormat, url: response.url || '' });
        this.close.emit();
      },
      error: (err) => {
        console.error('❌ Erreur export:', err);
        this.error = err.error?.message || 'Impossible d\'exporter le mémoire.';
        this.loading = false;
      }
    });
  }
}