import { Component, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../core/auth.service';
import { ThemeService } from '../core/theme.service';
import { NotificationService } from '../core/notification.service';
import { NotificationsComponent } from '../shared/notifications/notifications.component';

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    RouterLinkActive,
    NotificationsComponent
  ],
  templateUrl: './layout.component.html',
  styleUrls: ['./layout.component.css']
})
export class LayoutComponent {
  showNotifications = false;

  constructor(
    public auth: AuthService,
    public themeService: ThemeService,
    public notificationService: NotificationService
  ) {}

  initials = computed(() => {
    const u = this.auth.user();
    return (`${u?.first_name?.[0] ?? ''}${u?.last_name?.[0] ?? ''}`).toUpperCase() || 'M';
  });

  roleLabel = computed(() => {
    const role = this.auth.user()?.role ?? '';
    const labels: Record<string, string> = {
      STUDENT: 'Étudiant',
      SUPERVISOR: 'Encadreur',
      CO_SUPERVISOR: 'Co-encadreur',
      JURY: 'Membre du jury',
      ADMIN: 'Administrateur'
    };
    return labels[role] ?? role ?? 'Utilisateur';
  });

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  logout(): void {
    if (confirm('Êtes-vous sûr de vouloir vous déconnecter ?')) {
      this.auth.logout();
    }
  }

  toggleNotifications(): void {
    this.showNotifications = !this.showNotifications;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    if (!target.closest('.notification-wrapper')) {
      this.showNotifications = false;
    }
  }
}