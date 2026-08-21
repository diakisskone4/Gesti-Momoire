import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

export interface Collaborator {
  id?: number;
  project: number;
  user: number;
  user_email?: string;
  user_name?: string;
  role: 'viewer' | 'editor' | 'owner';
  permissions: {
    can_edit: boolean;
    can_comment: boolean;
    can_export: boolean;
    can_share: boolean;
  };
  status: 'pending' | 'active' | 'revoked';
}

export interface ShareLink {
  token: string;
  project: number;
  permissions: {
    can_edit: boolean;
    can_comment: boolean;
    can_export: boolean;
  };
  expires_at: string | null;
  created_at: string;
  url: string;
}

@Injectable({
  providedIn: 'root'
})
export class CollaborationService {
  // Stockage simple en mémoire
  private collaborators: any[] = [];
  private shareLinks: any[] = [];
  private idCounter = 100;

  constructor() {
    console.log('🔧 CollaborationService initialisé');
  }

  listCollaborators(projectId: number): Observable<Collaborator[]> {
    console.log('📡 listCollaborators - projet:', projectId);
    const filtered = this.collaborators.filter(c => c.project === projectId);
    
    if (filtered.length === 0) {
      const user = JSON.parse(localStorage.getItem('memoai_user') || '{}');
      const owner = {
        id: 1,
        project: projectId,
        user: user.id || 1,
        user_email: user.email || 'vous@email.com',
        user_name: user.first_name ? `${user.first_name} ${user.last_name}` : 'Propriétaire',
        role: 'owner' as 'owner',
        permissions: { can_edit: true, can_comment: true, can_export: true, can_share: true },
        status: 'active' as 'active'
      };
      this.collaborators.push(owner);
      return of([owner]).pipe(delay(300));
    }
    
    return of(filtered).pipe(delay(300));
  }

  addCollaborator(projectId: number, email: string, role: string): Observable<Collaborator> {
    console.log('📡 addCollaborator - projet:', projectId, 'email:', email, 'role:', role);
    
    // Vérifier si existe déjà
    const existing = this.collaborators.find(c => c.project === projectId && c.user_email === email);
    if (existing) {
      console.warn('⚠️ Collaborateur déjà existant');
      return of(existing).pipe(delay(300));
    }

    const newCollaborator: Collaborator = {
      id: this.idCounter++,
      project: projectId,
      user: Math.floor(Math.random() * 1000) + 100,
      user_email: email,
      user_name: email.split('@')[0],
      role: role as 'viewer' | 'editor',
      permissions: { 
        can_edit: role === 'editor', 
        can_comment: true, 
        can_export: true, 
        can_share: false 
      },
      status: 'active'
    };

    this.collaborators.push(newCollaborator);
    console.log('✅ Collaborateur ajouté avec succès:', newCollaborator);
    console.log('📊 Total collaborateurs:', this.collaborators.length);
    
    return of(newCollaborator).pipe(delay(500));
  }

  removeCollaborator(id: number): Observable<any> {
    console.log('📡 removeCollaborator - id:', id);
    const index = this.collaborators.findIndex(c => c.id === id);
    if (index !== -1) {
      this.collaborators.splice(index, 1);
      console.log('✅ Collaborateur supprimé');
    }
    return of({ success: true }).pipe(delay(300));
  }

  updateCollaborator(id: number, data: Partial<Collaborator>): Observable<Collaborator> {
    const collab = this.collaborators.find(c => c.id === id);
    if (collab) {
      Object.assign(collab, data);
      return of(collab).pipe(delay(300));
    }
    return of({} as Collaborator).pipe(delay(300));
  }

  createShareLink(projectId: number, permissions: any): Observable<ShareLink> {
    console.log('📡 createShareLink - projet:', projectId);
    const token = 'share_' + Math.random().toString(36).substr(2, 9);
    const newLink: ShareLink = {
      token: token,
      project: projectId,
      permissions: permissions,
      expires_at: null,
      created_at: new Date().toISOString(),
      url: `http://localhost:4200/share/${token}`
    };
    this.shareLinks.push(newLink);
    console.log('✅ Lien créé:', newLink);
    return of(newLink).pipe(delay(500));
  }

  listShareLinks(projectId: number): Observable<ShareLink[]> {
    const filtered = this.shareLinks.filter(l => l.project === projectId);
    return of(filtered).pipe(delay(300));
  }

  deleteShareLink(token: string): Observable<any> {
    console.log('📡 deleteShareLink - token:', token);
    const index = this.shareLinks.findIndex(l => l.token === token);
    if (index !== -1) {
      this.shareLinks.splice(index, 1);
    }
    return of({ success: true }).pipe(delay(300));
  }

  revokeAllLinks(projectId: number): Observable<any> {
    console.log('📡 revokeAllLinks - projet:', projectId);
    this.shareLinks = this.shareLinks.filter(l => l.project !== projectId);
    return of({ success: true }).pipe(delay(300));
  }
}