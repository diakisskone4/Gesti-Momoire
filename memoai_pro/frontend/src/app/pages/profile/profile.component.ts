import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { LayoutComponent } from '../../layout/layout.component';
import { AuthService } from '../../core/auth.service';
import { User } from '../../core/models';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LayoutComponent
  ],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  user: User | null = null;
  loading = true;
  saving = false;
  message = '';
  error = '';
  editMode = false;

  profileForm: Partial<User> = {
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    language: 'fr'
  };

  languages = [
    { value: 'fr', label: 'Français' },
    { value: 'en', label: 'English' },
    { value: 'es', label: 'Español' },
    { value: 'ar', label: 'العربية' }
  ];

  constructor(
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef  // ✅ Ajouter ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    console.log('🔍 ProfileComponent initialisé');
    this.loadProfile();
  }

  loadProfile(): void {
    console.log('🔄 Chargement du profil...');
    this.loading = true;
    this.error = '';
    
    this.authService.profile().subscribe({
      next: (user) => {
        console.log('✅ Profil chargé:', user);
        
        if (user) {
          this.user = user;
          this.profileForm = { ...user };
          this.loading = false;
        } else {
          this.loading = false;
          this.error = 'Impossible de charger le profil.';
        }
        
        this.cdr.detectChanges();  // ✅ Forcer la détection de changement
        console.log('✅ loading =', this.loading);
      },
      error: (err) => {
        console.error('❌ Erreur chargement profil:', err);
        this.error = err.error?.message || 'Impossible de charger votre profil.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  toggleEditMode(): void {
    this.editMode = !this.editMode;
    if (!this.editMode) {
      this.profileForm = { ...this.user };
    }
    this.message = '';
    this.error = '';
  }

  saveProfile(): void {
    if (!this.profileForm.email) {
      this.error = 'L\'email est obligatoire.';
      return;
    }

    this.saving = true;
    this.message = '';
    this.error = '';

    const data: any = {
      first_name: this.profileForm.first_name || '',
      last_name: this.profileForm.last_name || '',
      email: this.profileForm.email,
      phone: this.profileForm.phone || '',
      language: this.profileForm.language || 'fr'
    };

    this.authService.updateProfile(data).subscribe({
      next: (updated) => {
        console.log('✅ Profil mis à jour:', updated);
        this.user = updated;
        this.profileForm = { ...updated };
        this.saving = false;
        this.editMode = false;
        this.message = 'Profil mis à jour avec succès !';
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('❌ Erreur mise à jour:', err);
        this.error = err.error?.message || 'Impossible de mettre à jour le profil.';
        this.saving = false;
        this.cdr.detectChanges();
      }
    });
  }

  logout(): void {
    if (confirm('Êtes-vous sûr de vouloir vous déconnecter ?')) {
      this.authService.logout();
    }
  }

  changePassword(): void {
    this.router.navigate(['/profile/change-password']);
  }

  get userInitials(): string {
    if (!this.user) return 'U';
    const first = this.user.first_name?.charAt(0) || '';
    const last = this.user.last_name?.charAt(0) || '';
    return (first + last) || this.user.email?.charAt(0) || 'U';
  }

  get fullName(): string {
    if (!this.user) return 'Utilisateur';
    if (this.user.first_name && this.user.last_name) {
      return `${this.user.first_name} ${this.user.last_name}`;
    }
    return this.user.email || 'Utilisateur';
  }

  refresh(): void {
    this.loadProfile();
  }
}