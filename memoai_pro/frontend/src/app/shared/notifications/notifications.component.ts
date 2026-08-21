import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { NotificationService } from '../../core/notification.service';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="notifications-container">
      <div class="notifications-header">
        <h3>🔔 Notifications</h3>
        <div class="header-actions">
          <button 
            *ngIf="getNotifications().length > 0" 
            class="mark-all-btn"
            (click)="markAllAsRead()"
          >
            Tout marquer comme lu
          </button>
          <button 
            *ngIf="getNotifications().length > 0" 
            class="clear-all-btn"
            (click)="clearAll()"
          >
            ✕
          </button>
        </div>
      </div>

      <div *ngIf="getNotifications().length === 0" class="empty-state">
        <span class="empty-icon">📭</span>
        <p>Aucune notification</p>
      </div>

      <div *ngFor="let notification of getNotifications()" 
           class="notification-item"
           [class.unread]="!notification.read"
           [class]="'notification-' + notification.type"
           (click)="markAsRead(notification.id)"
      >
        <div class="notification-icon">
          <span *ngIf="notification.type === 'success'">✅</span>
          <span *ngIf="notification.type === 'error'">❌</span>
          <span *ngIf="notification.type === 'info'">ℹ️</span>
          <span *ngIf="notification.type === 'warning'">⚠️</span>
        </div>
        <div class="notification-content">
          <div class="notification-title">{{ notification.title }}</div>
          <div class="notification-message">{{ notification.message }}</div>
          <div class="notification-time">
            {{ notification.created_at | date:'dd/MM/yyyy HH:mm' }}
          </div>
          <a *ngIf="notification.link" 
             [routerLink]="notification.link"
             class="notification-link"
          >
            Voir →
          </a>
        </div>
        <button class="notification-close" (click)="remove(notification.id); $event.stopPropagation()">
          ✕
        </button>
      </div>
    </div>
  `,
  styles: [`
    .notifications-container {
      max-height: 500px;
      overflow-y: auto;
      background: var(--bg-card, #ffffff);
      border-radius: 16px;
      border: 1px solid var(--border-color, #e5eceb);
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
      padding: 16px;
      min-width: 350px;
      max-width: 400px;
    }

    .notifications-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color, #e5eceb);
      margin-bottom: 12px;
    }

    .notifications-header h3 {
      margin: 0;
      font-size: 16px;
      color: var(--text-primary, #173e3a);
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }

    .mark-all-btn {
      border: none;
      background: none;
      color: #0f766e;
      font-size: 12px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      transition: all 0.2s;
    }

    .mark-all-btn:hover {
      background: #e6f7f5;
    }

    .clear-all-btn {
      border: none;
      background: none;
      color: var(--text-muted, #748482);
      font-size: 14px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      transition: all 0.2s;
    }

    .clear-all-btn:hover {
      background: #fee2e2;
      color: #991b1b;
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

    .notification-item {
      display: flex;
      gap: 12px;
      padding: 12px 14px;
      border-radius: 10px;
      margin-bottom: 8px;
      cursor: pointer;
      transition: all 0.2s;
      position: relative;
      border: 1px solid transparent;
    }

    .notification-item:hover {
      background: var(--bg-hover, #f0f5f4);
    }

    .notification-item.unread {
      background: #f0f9f8;
      border-color: #a7f3d0;
    }

    .notification-item.unread::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 4px;
      height: 24px;
      background: #0f766e;
      border-radius: 0 4px 4px 0;
    }

    .notification-success { border-left: 4px solid #22c55e; }
    .notification-error { border-left: 4px solid #ef4444; }
    .notification-info { border-left: 4px solid #3b82f6; }
    .notification-warning { border-left: 4px solid #f59e0b; }

    .notification-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    .notification-content {
      flex: 1;
      min-width: 0;
    }

    .notification-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary, #173e3a);
    }

    .notification-message {
      font-size: 13px;
      color: var(--text-muted, #748482);
      margin-top: 2px;
    }

    .notification-time {
      font-size: 11px;
      color: var(--text-light, #9aa8a6);
      margin-top: 4px;
    }

    .notification-link {
      display: inline-block;
      margin-top: 6px;
      font-size: 12px;
      color: #0f766e;
      text-decoration: none;
      font-weight: 500;
    }

    .notification-link:hover {
      text-decoration: underline;
    }

    .notification-close {
      background: none;
      border: none;
      color: var(--text-muted, #748482);
      cursor: pointer;
      font-size: 14px;
      padding: 4px;
      border-radius: 4px;
      transition: all 0.2s;
      flex-shrink: 0;
    }

    .notification-close:hover {
      background: #fee2e2;
      color: #991b1b;
    }

    @media (max-width: 480px) {
      .notifications-container {
        min-width: auto;
        width: 100%;
        max-width: 100%;
        border-radius: 12px;
        padding: 12px;
      }
    }
  `]
})
export class NotificationsComponent {
  constructor(private notificationService: NotificationService) {}

  getNotifications() {
    return this.notificationService.getNotifications();
  }

  remove(id: number): void {
    this.notificationService.remove(id);
  }

  markAsRead(id: number): void {
    this.notificationService.markAsRead(id);
  }

  markAllAsRead(): void {
    this.notificationService.markAllAsRead();
  }

  clearAll(): void {
    this.notificationService.clearAll();
  }
}