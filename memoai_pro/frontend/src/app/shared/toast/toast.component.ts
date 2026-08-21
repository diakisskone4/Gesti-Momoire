import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService } from '../../core/notification.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container">
      <div 
        *ngFor="let notification of notificationService.getNotifications()"
        class="toast"
        [class]="'toast-' + notification.type"
        (click)="notificationService.remove(notification.id)"
      >
        <div class="toast-icon">
          <span *ngIf="notification.type === 'success'">✅</span>
          <span *ngIf="notification.type === 'error'">❌</span>
          <span *ngIf="notification.type === 'info'">ℹ️</span>
          <span *ngIf="notification.type === 'warning'">⚠️</span>
        </div>
        <div class="toast-content">
          <span class="toast-message">{{ notification.message }}</span>
        </div>
        <button class="toast-close" (click)="notificationService.remove(notification.id); $event.stopPropagation()">
          ✕
        </button>
      </div>
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 400px;
      width: 100%;
    }

    .toast {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      border-radius: 12px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
      cursor: pointer;
      animation: slideIn 0.3s ease;
      transition: all 0.3s ease;
    }

    .toast:hover {
      transform: translateX(-4px);
    }

    .toast-success {
      border-left: 4px solid #22c55e;
    }

    .toast-error {
      border-left: 4px solid #ef4444;
    }

    .toast-info {
      border-left: 4px solid #3b82f6;
    }

    .toast-warning {
      border-left: 4px solid #f59e0b;
    }

    .toast-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    .toast-content {
      flex: 1;
    }

    .toast-message {
      font-size: 14px;
      color: var(--text-primary);
      font-weight: 500;
    }

    .toast-close {
      background: none;
      border: none;
      font-size: 16px;
      color: var(--text-muted);
      cursor: pointer;
      padding: 4px;
      border-radius: 4px;
      transition: all 0.2s;
    }

    .toast-close:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    @keyframes slideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }

    @media (max-width: 480px) {
      .toast-container {
        top: 10px;
        right: 10px;
        left: 10px;
        max-width: none;
        width: auto;
      }
    }
  `]
})
export class ToastComponent {
  constructor(public notificationService: NotificationService) {}
}