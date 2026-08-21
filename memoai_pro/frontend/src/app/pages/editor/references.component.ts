import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ReferencesService, Reference } from '../../core/references.service';

@Component({
  selector: 'app-references-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3>📚 Bibliographie</h3>
          <button class="close-btn" (click)="close.emit()">✕</button>
        </div>

        <div class="modal-body">
          <!-- Import par DOI -->
          <div class="import-section">
            <h4>Importer par DOI</h4>
            <div class="import-row">
              <input
                type="text"
                [(ngModel)]="doiInput"
                placeholder="Ex: 10.1234/abcd.1234"
                class="doi-input"
              />
              <button class="btn-primary" (click)="importByDOI()" [disabled]="!doiInput || loading">
                {{ loading ? 'Import...' : '📥 Importer' }}
              </button>
            </div>
            <div *ngIf="importError" class="error-message">{{ importError }}</div>
          </div>

          <!-- Liste des références -->
          <div class="references-list">
            <div class="list-header">
              <h4>Références ({{ references.length }})</h4>
              <button class="btn-secondary" (click)="addManual()">➕ Ajouter manuelle</button>
            </div>

            <div *ngIf="references.length === 0" class="empty-state">
              <span class="empty-icon">📭</span>
              <p>Aucune référence bibliographique</p>
            </div>

            <div *ngFor="let ref of references" class="reference-item">
              <div class="ref-content">
                <div class="ref-header">
                  <strong>{{ ref.title }}</strong>
                  <div class="ref-actions">
                    <button class="btn-icon" (click)="editReference(ref)" title="Modifier">✏️</button>
                    <button class="btn-icon" (click)="generateBibtex(ref.id!)" title="BibTeX">📄</button>
                    <button class="btn-icon btn-delete" (click)="deleteReference(ref.id!)" title="Supprimer">🗑️</button>
                  </div>
                </div>
                <div class="ref-details">
                  <span>{{ ref.authors }}</span>
                  <span>{{ ref.year }}</span>
                  <span *ngIf="ref.journal">{{ ref.journal }}</span>
                  <span *ngIf="ref.doi" class="ref-doi">DOI: {{ ref.doi }}</span>
                </div>
                <div *ngIf="ref.bibtex" class="ref-bibtex">
                  <pre>{{ ref.bibtex }}</pre>
                </div>
              </div>
            </div>
          </div>

          <!-- Formulaire d'édition -->
          <div *ngIf="editingRef" class="edit-form">
            <h4>{{ editingRef.id ? 'Modifier' : 'Ajouter' }} une référence</h4>
            <div class="form-group">
              <label>Titre *</label>
              <input type="text" [(ngModel)]="editingRef.title" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Auteurs *</label>
                <input type="text" [(ngModel)]="editingRef.authors" placeholder="Dupont, J. et Martin, P." />
              </div>
              <div class="form-group">
                <label>Année *</label>
                <input type="number" [(ngModel)]="editingRef.year" />
              </div>
            </div>
            <div class="form-group">
              <label>Journal / Éditeur</label>
              <input type="text" [(ngModel)]="editingRef.journal" />
            </div>
            <div class="form-group">
              <label>DOI</label>
              <input type="text" [(ngModel)]="editingRef.doi" placeholder="10.1234/abcd.1234" />
            </div>
            <div class="edit-actions">
              <button class="btn-secondary" (click)="cancelEdit()">Annuler</button>
              <button class="btn-primary" (click)="saveReference()" [disabled]="!editingRef.title || !editingRef.authors || !editingRef.year">
                💾 Sauvegarder
              </button>
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
      max-width: 700px;
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

    .import-section {
      background: var(--bg-input, #f8fbfa);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 20px;
      border: 1px solid var(--border-color, #e5eceb);
    }

    .import-section h4 {
      margin: 0 0 10px 0;
      color: var(--text-primary, #173e3a);
      font-size: 14px;
    }

    .import-row {
      display: flex;
      gap: 10px;
    }

    .doi-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--border-color, #dce7e5);
      border-radius: 8px;
      background: var(--bg-secondary, #ffffff);
      color: var(--text-primary, #173e3a);
      font-size: 13px;
    }

    .doi-input:focus {
      outline: none;
      border-color: #0f766e;
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
    }

    .references-list {
      margin-top: 15px;
    }

    .list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .list-header h4 {
      margin: 0;
      color: var(--text-primary, #173e3a);
      font-size: 15px;
    }

    .reference-item {
      background: var(--bg-input, #f8fbfa);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 8px;
      border: 1px solid var(--border-color, #e5eceb);
      transition: all 0.2s;
    }

    .reference-item:hover {
      border-color: #0f766e;
    }

    .ref-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
    }

    .ref-header strong {
      color: var(--text-primary, #173e3a);
      font-size: 14px;
    }

    .ref-actions {
      display: flex;
      gap: 5px;
      flex-shrink: 0;
    }

    .btn-icon {
      background: none;
      border: none;
      padding: 4px 6px;
      cursor: pointer;
      border-radius: 4px;
      font-size: 14px;
      transition: all 0.2s;
      color: var(--text-muted, #748482);
    }

    .btn-icon:hover {
      background: var(--bg-hover, #eef7f5);
      color: var(--text-primary, #173e3a);
    }

    .btn-delete:hover {
      background: #fff1f2;
      color: #be123c;
    }

    .ref-details {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 5px;
      font-size: 12px;
      color: var(--text-muted, #748482);
    }

    .ref-doi {
      color: #0f766e;
      font-weight: 500;
    }

    .ref-bibtex {
      margin-top: 8px;
      padding: 8px 12px;
      background: var(--bg-secondary, #ffffff);
      border-radius: 6px;
      border: 1px solid var(--border-color, #e5eceb);
    }

    .ref-bibtex pre {
      margin: 0;
      font-size: 11px;
      color: var(--text-secondary, #39514e);
      white-space: pre-wrap;
      word-break: break-all;
    }

    .edit-form {
      margin-top: 20px;
      padding: 20px;
      background: var(--bg-input, #f8fbfa);
      border-radius: 12px;
      border: 1px solid var(--border-color, #e5eceb);
    }

    .edit-form h4 {
      margin: 0 0 15px 0;
      color: var(--text-primary, #173e3a);
      font-size: 15px;
    }

    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
    }

    .form-group {
      margin-bottom: 12px;
    }

    .form-group label {
      display: block;
      margin-bottom: 4px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary, #39514e);
    }

    .form-group input {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid var(--border-color, #dce7e5);
      border-radius: 8px;
      background: var(--bg-secondary, #ffffff);
      color: var(--text-primary, #173e3a);
      font-size: 13px;
      box-sizing: border-box;
    }

    .form-group input:focus {
      outline: none;
      border-color: #0f766e;
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
    }

    .edit-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 15px;
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      padding-top: 15px;
      border-top: 1px solid var(--border-color, #e5eceb);
      margin-top: 15px;
    }

    .btn-primary {
      border: none;
      border-radius: 8px;
      padding: 8px 16px;
      background: #0f766e;
      color: white;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-primary:hover:not(:disabled) {
      background: #0b625c;
      transform: translateY(-1px);
    }

    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-secondary {
      border: 1px solid var(--border-color, #dce7e5);
      border-radius: 8px;
      padding: 8px 16px;
      background: var(--bg-secondary, #ffffff);
      color: var(--text-secondary, #39514e);
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .btn-secondary:hover {
      border-color: #0f766e;
      color: #0f766e;
    }

    .error-message {
      margin-top: 8px;
      padding: 8px 12px;
      background: #fff1f2;
      color: #be123c;
      border-radius: 6px;
      font-size: 12px;
    }

    .empty-state {
      text-align: center;
      padding: 30px 20px;
      color: var(--text-muted, #748482);
    }

    .empty-icon {
      font-size: 32px;
      display: block;
      margin-bottom: 8px;
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

      .form-row {
        grid-template-columns: 1fr;
      }

      .import-row {
        flex-direction: column;
      }
    }
  `]
})
export class ReferencesModalComponent implements OnInit {
  @Input() projectId!: number;
  @Output() close = new EventEmitter<void>();
  @Output() referencesUpdated = new EventEmitter<Reference[]>();

  references: Reference[] = [];
  loading = false;
  importError = '';
  doiInput = '';
  editingRef: Partial<Reference> | null = null;

  constructor(private referencesService: ReferencesService) {}

  ngOnInit(): void {
    this.loadReferences();
  }

  loadReferences(): void {
    this.referencesService.list(this.projectId).subscribe({
      next: (refs) => {
        this.references = refs;
        this.referencesUpdated.emit(refs);
      },
      error: (err) => {
        console.error('❌ Erreur chargement références:', err);
      }
    });
  }

  importByDOI(): void {
    if (!this.doiInput) return;

    this.loading = true;
    this.importError = '';

    this.referencesService.importByDOI(this.doiInput, this.projectId).subscribe({
      next: (ref) => {
        this.references = [...this.references, ref];
        this.doiInput = '';
        this.loading = false;
        this.referencesUpdated.emit(this.references);
      },
      error: (err) => {
        this.importError = err.error?.error || 'Erreur lors de l\'import. Vérifiez le DOI.';
        this.loading = false;
      }
    });
  }

  addManual(): void {
    this.editingRef = {
      project: this.projectId,
      title: '',
      authors: '',
      year: new Date().getFullYear(),
      journal: '',
      doi: ''
    };
  }

  editReference(ref: Reference): void {
    this.editingRef = { ...ref };
  }

  cancelEdit(): void {
    this.editingRef = null;
  }

  saveReference(): void {
    if (!this.editingRef) return;

    const data = this.editingRef;

    if (data.id) {
      // Mise à jour
      this.referencesService.update(data.id, data).subscribe({
        next: (updated) => {
          this.references = this.references.map(r => r.id === updated.id ? updated : r);
          this.editingRef = null;
          this.referencesUpdated.emit(this.references);
        },
        error: (err) => {
          console.error('❌ Erreur mise à jour:', err);
        }
      });
    } else {
      // Création
      this.referencesService.create(data).subscribe({
        next: (created) => {
          this.references = [...this.references, created];
          this.editingRef = null;
          this.referencesUpdated.emit(this.references);
        },
        error: (err) => {
          console.error('❌ Erreur création:', err);
        }
      });
    }
  }

  deleteReference(id: number): void {
    if (!confirm('Supprimer cette référence ?')) return;

    this.referencesService.delete(id).subscribe({
      next: () => {
        this.references = this.references.filter(r => r.id !== id);
        this.referencesUpdated.emit(this.references);
      },
      error: (err) => {
        console.error('❌ Erreur suppression:', err);
      }
    });
  }

  generateBibtex(id: number): void {
    this.referencesService.generateBibtex(id).subscribe({
      next: (result) => {
        const ref = this.references.find(r => r.id === id);
        if (ref) {
          ref.bibtex = result.bibtex;
        }
      },
      error: (err) => {
        console.error('❌ Erreur génération BibTeX:', err);
      }
    });
  }
}