import { Component, Input, Output, EventEmitter, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { CollaborationService, Collaborator, ShareLink } from '../../core/collaboration.service';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-collaboration-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3>👥 Collaboration</h3>
          <button class="close-btn" (click)="close.emit()">✕</button>
        </div>

        <div class="modal-body">
          <div class="tabs">
            <button class="tab" [class.active]="activeTab === 'collaborators'" (click)="activeTab = 'collaborators'">
              👤 Collaborateurs
            </button>
            <button class="tab" [class.active]="activeTab === 'links'" (click)="activeTab = 'links'">
              🔗 Liens de partage
            </button>
          </div>

          <div *ngIf="activeTab === 'collaborators'" class="tab-content">
            <div *ngIf="successMessage" class="success-message">
              ✅ {{ successMessage }}
            </div>

            <div *ngIf="errorMessage" class="error-message">
              ❌ {{ errorMessage }}
            </div>

            <div class="add-collaborator">
              <input
                type="email"
                [(ngModel)]="newCollaboratorEmail"
                placeholder="Email du collaborateur"
                class="email-input"
                [disabled]="loading"
              />
              <select [(ngModel)]="newCollaboratorRole" class="role-select" [disabled]="loading">
                <option value="viewer">👁️ Lecteur</option>
                <option value="editor">✏️ Éditeur</option>
              </select>
              <button class="btn-primary" (click)="addCollaborator()" [disabled]="!newCollaboratorEmail || loading">
                {{ loading ? '⏳ Ajout...' : '➕ Ajouter' }}
              </button>
            </div>

            <!-- Liste des collaborateurs -->
            <div *ngFor="let collab of collaborators" class="collaborator-item">
              <div class="collab-info">
                <div class="collab-avatar">
                  {{ getInitials(collab.user_name || collab.user_email || '') }}
                </div>
                <div class="collab-details">
                  <strong>{{ collab.user_name || collab.user_email }}</strong>
                  <span>{{ collab.user_email }}</span>
                </div>
              </div>
              <div class="collab-actions">
                <span class="role-badge" [class]="'role-' + collab.role">
                  {{ getRoleLabel(collab.role) }}
                </span>
                <span class="status-badge" [class]="'status-' + collab.status">
                  {{ getStatusLabel(collab.status) }}
                </span>
                <button
                  *ngIf="collab.role !== 'owner'"
                  class="btn-icon btn-delete"
                  (click)="removeCollaborator(collab.id!)"
                  title="Retirer"
                >
                  🗑️
                </button>
              </div>
            </div>

            <div *ngIf="collaborators.length === 0 && !loading" class="empty-state">
              <span class="empty-icon">👤</span>
              <p>Aucun collaborateur</p>
            </div>
          </div>

          <div *ngIf="activeTab === 'links'" class="tab-content">
            <div *ngIf="successMessage" class="success-message">
              ✅ {{ successMessage }}
            </div>

            <div *ngIf="errorMessage" class="error-message">
              ❌ {{ errorMessage }}
            </div>

            <div class="create-link">
              <div class="link-permissions">
                <label>
                  <input type="checkbox" [(ngModel)]="linkPermissions.can_edit" />
                  Peut modifier
                </label>
                <label>
                  <input type="checkbox" [(ngModel)]="linkPermissions.can_comment" />
                  Peut commenter
                </label>
                <label>
                  <input type="checkbox" [(ngModel)]="linkPermissions.can_export" />
                  Peut exporter
                </label>
              </div>
              <button class="btn-primary" (click)="createShareLink()">
                🔗 Générer un lien
              </button>
            </div>

            <div *ngIf="shareLinks.length === 0" class="empty-state">
              <span class="empty-icon">🔗</span>
              <p>Aucun lien de partage</p>
            </div>

            <div *ngFor="let link of shareLinks" class="link-item">
              <div class="link-info">
                <span class="link-url">{{ link.url }}</span>
                <div class="link-permissions-badge">
                  <span *ngIf="link.permissions.can_edit">✏️</span>
                  <span *ngIf="link.permissions.can_comment">💬</span>
                  <span *ngIf="link.permissions.can_export">📤</span>
                </div>
                <span *ngIf="link.expires_at" class="link-expires">
                  Expire le {{ link.expires_at | date:'dd/MM/yyyy' }}
                </span>
              </div>
              <button class="btn-icon btn-delete" (click)="deleteShareLink(link.token)">
                🗑️
              </button>
            </div>

            <button
              *ngIf="shareLinks.length > 0"
              class="btn-secondary"
              (click)="revokeAllLinks()"
              style="margin-top: 12px;"
            >
              🔒 Révoquer tous les liens
            </button>
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
      max-width: 650px;
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

    .success-message {
      background: #d1fae5;
      color: #065f46;
      padding: 10px 14px;
      border-radius: 8px;
      margin-bottom: 12px;
      font-size: 13px;
      animation: slideDown 0.3s ease;
      border: 1px solid #a7f3d0;
    }

    .error-message {
      background: #fee2e2;
      color: #991b1b;
      padding: 10px 14px;
      border-radius: 8px;
      margin-bottom: 12px;
      font-size: 13px;
      animation: slideDown 0.3s ease;
      border: 1px solid #fca5a5;
    }

    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--border-color, #e5eceb);
      padding-bottom: 8px;
    }

    .tab {
      padding: 8px 16px;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      color: var(--text-muted, #748482);
      border-radius: 8px;
      transition: all 0.2s;
    }

    .tab:hover {
      background: var(--bg-hover, #f0f5f4);
      color: var(--text-primary, #173e3a);
    }

    .tab.active {
      background: #e6f7f5;
      color: #0f766e;
    }

    .add-collaborator {
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }

    .email-input {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--border-color, #dce7e5);
      border-radius: 8px;
      background: var(--bg-input, #fbfdfd);
      color: var(--text-primary, #173e3a);
      font-size: 13px;
      min-width: 150px;
    }

    .email-input:focus {
      outline: none;
      border-color: #0f766e;
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
    }

    .role-select {
      padding: 10px 14px;
      border: 1px solid var(--border-color, #dce7e5);
      border-radius: 8px;
      background: var(--bg-input, #fbfdfd);
      color: var(--text-primary, #173e3a);
      font-size: 13px;
    }

    .collaborator-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 14px;
      background: var(--bg-input, #f8fbfa);
      border-radius: 10px;
      margin-bottom: 8px;
      border: 1px solid var(--border-color, #e5eceb);
    }

    .collab-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .collab-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #0f766e;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 14px;
      flex-shrink: 0;
    }

    .collab-details strong {
      display: block;
      font-size: 13px;
      color: var(--text-primary, #173e3a);
    }

    .collab-details span {
      font-size: 12px;
      color: var(--text-muted, #748482);
    }

    .collab-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .role-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 20px;
      text-transform: uppercase;
    }

    .role-owner { background: #d1fae5; color: #065f46; }
    .role-editor { background: #dbeafe; color: #1e40af; }
    .role-viewer { background: #f1f5f4; color: #70807f; }

    .status-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 20px;
      text-transform: uppercase;
    }

    .status-pending { background: #fef3c7; color: #92400e; }
    .status-active { background: #d1fae5; color: #065f46; }
    .status-revoked { background: #fecdd3; color: #be123c; }

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
      background: var(--bg-hover, #f0f5f4);
      color: var(--text-primary, #173e3a);
    }

    .btn-delete:hover {
      background: #fff1f2;
      color: #be123c;
    }

    .btn-primary {
      border: none;
      border-radius: 8px;
      padding: 10px 20px;
      background: #0f766e;
      color: white;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s ease;
      white-space: nowrap;
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

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      padding-top: 15px;
      border-top: 1px solid var(--border-color, #e5eceb);
      margin-top: 15px;
    }

    .link-permissions {
      display: flex;
      gap: 16px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    .link-permissions label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: var(--text-secondary, #39514e);
      cursor: pointer;
    }

    .link-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 14px;
      background: var(--bg-input, #f8fbfa);
      border-radius: 10px;
      margin-bottom: 8px;
      border: 1px solid var(--border-color, #e5eceb);
    }

    .link-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .link-url {
      font-size: 13px;
      color: #0f766e;
      font-weight: 500;
    }

    .link-permissions-badge {
      display: flex;
      gap: 6px;
      font-size: 12px;
    }

    .link-expires {
      font-size: 11px;
      color: var(--text-muted, #748482);
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

      .add-collaborator {
        flex-direction: column;
      }

      .collaborator-item {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }

      .collab-actions {
        width: 100%;
        justify-content: flex-start;
      }

      .link-permissions {
        flex-direction: column;
        gap: 8px;
      }
    }
  `]
})
export class CollaborationModalComponent implements OnInit {
  @Input() projectId!: number;
  @Output() close = new EventEmitter<void>();

  activeTab: 'collaborators' | 'links' = 'collaborators';
  loading = false;
  
  successMessage = '';
  errorMessage = '';

  collaborators: Collaborator[] = [];
  newCollaboratorEmail = '';
  newCollaboratorRole: 'viewer' | 'editor' = 'viewer';

  shareLinks: ShareLink[] = [];
  linkPermissions = {
    can_edit: false,
    can_comment: true,
    can_export: true
  };

  constructor(
    private collaborationService: CollaborationService,
    private authService: AuthService,
    private cdr: ChangeDetectorRef  // ✅ Ajouter ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadCollaborators();
    this.loadShareLinks();
  }

  loadCollaborators(): void {
    this.loading = true;
    this.collaborationService.listCollaborators(this.projectId).subscribe({
      next: (collabs) => {
        console.log('✅ Collaborateurs chargés:', collabs);
        this.collaborators = collabs;
        this.loading = false;
        this.cdr.detectChanges();  // ✅ Forcer la mise à jour
      },
      error: (err) => {
        console.error('❌ Erreur chargement collaborateurs:', err);
        this.errorMessage = 'Impossible de charger les collaborateurs.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  loadShareLinks(): void {
    this.collaborationService.listShareLinks(this.projectId).subscribe({
      next: (links) => {
        this.shareLinks = links;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('❌ Erreur chargement liens:', err);
      }
    });
  }

  addCollaborator(): void {
    if (!this.newCollaboratorEmail) {
      this.errorMessage = 'Veuillez entrer un email.';
      this.cdr.detectChanges();
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(this.newCollaboratorEmail)) {
      this.errorMessage = 'Email invalide.';
      this.cdr.detectChanges();
      return;
    }

    console.log('📧 Tentative d\'ajout:', this.newCollaboratorEmail);
    this.loading = true;
    this.successMessage = '';
    this.errorMessage = '';
    this.cdr.detectChanges();

    this.collaborationService.addCollaborator(
      this.projectId,
      this.newCollaboratorEmail,
      this.newCollaboratorRole
    ).subscribe({
      next: (collab) => {
        console.log('✅ Collaborateur ajouté:', collab);
        this.collaborators = [...this.collaborators, collab];
        this.newCollaboratorEmail = '';
        this.loading = false;
        this.successMessage = `✅ ${collab.user_email} a été ajouté comme ${this.getRoleLabel(collab.role)} !`;
        this.cdr.detectChanges();
        
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.detectChanges();
        }, 5000);
      },
      error: (err) => {
        console.error('❌ Erreur ajout collaborateur:', err);
        this.loading = false;
        this.errorMessage = err.message || 'Impossible d\'ajouter ce collaborateur.';
        this.cdr.detectChanges();
        
        setTimeout(() => {
          this.errorMessage = '';
          this.cdr.detectChanges();
        }, 5000);
      }
    });
  }

  removeCollaborator(id: number): void {
    if (!confirm('Retirer ce collaborateur ?')) return;

    this.collaborationService.removeCollaborator(id).subscribe({
      next: () => {
        this.collaborators = this.collaborators.filter(c => c.id !== id);
        this.successMessage = '✅ Collaborateur retiré avec succès !';
        this.cdr.detectChanges();
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.detectChanges();
        }, 3000);
      },
      error: (err) => {
        console.error('❌ Erreur suppression:', err);
        this.errorMessage = 'Impossible de retirer ce collaborateur.';
        this.cdr.detectChanges();
        setTimeout(() => {
          this.errorMessage = '';
          this.cdr.detectChanges();
        }, 3000);
      }
    });
  }

  createShareLink(): void {
    this.collaborationService.createShareLink(
      this.projectId,
      this.linkPermissions
    ).subscribe({
      next: (link) => {
        this.shareLinks = [...this.shareLinks, link];
        this.successMessage = '✅ Lien de partage créé et copié !';
        navigator.clipboard.writeText(link.url).then(() => {
          console.log('✅ Lien copié');
        });
        this.cdr.detectChanges();
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.detectChanges();
        }, 5000);
      },
      error: (err) => {
        console.error('❌ Erreur création lien:', err);
        this.errorMessage = 'Impossible de créer le lien de partage.';
        this.cdr.detectChanges();
        setTimeout(() => {
          this.errorMessage = '';
          this.cdr.detectChanges();
        }, 3000);
      }
    });
  }

  deleteShareLink(token: string): void {
    if (!confirm('Supprimer ce lien ?')) return;

    this.collaborationService.deleteShareLink(token).subscribe({
      next: () => {
        this.shareLinks = this.shareLinks.filter(l => l.token !== token);
        this.successMessage = '✅ Lien supprimé !';
        this.cdr.detectChanges();
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.detectChanges();
        }, 3000);
      },
      error: (err) => {
        console.error('❌ Erreur suppression lien:', err);
        this.errorMessage = 'Impossible de supprimer ce lien.';
        this.cdr.detectChanges();
        setTimeout(() => {
          this.errorMessage = '';
          this.cdr.detectChanges();
        }, 3000);
      }
    });
  }

  revokeAllLinks(): void {
    if (!confirm('Révoquer tous les liens de partage ?')) return;

    this.collaborationService.revokeAllLinks(this.projectId).subscribe({
      next: () => {
        this.shareLinks = [];
        this.successMessage = '✅ Tous les liens ont été révoqués !';
        this.cdr.detectChanges();
        setTimeout(() => {
          this.successMessage = '';
          this.cdr.detectChanges();
        }, 3000);
      },
      error: (err) => {
        console.error('❌ Erreur révocation:', err);
        this.errorMessage = 'Impossible de révoquer les liens.';
        this.cdr.detectChanges();
        setTimeout(() => {
          this.errorMessage = '';
          this.cdr.detectChanges();
        }, 3000);
      }
    });
  }

  getInitials(name: string): string {
    if (!name) return '?';
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return `${parts[0].charAt(0)}${parts[1].charAt(0)}`.toUpperCase();
    }
    return name.charAt(0).toUpperCase();
  }

  getRoleLabel(role: string): string {
    const labels: Record<string, string> = {
      'owner': 'Propriétaire',
      'editor': 'Éditeur',
      'viewer': 'Lecteur'
    };
    return labels[role] || role;
  }

  getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      'pending': 'En attente',
      'active': 'Actif',
      'revoked': 'Révoqué'
    };
    return labels[status] || status;
  }
}