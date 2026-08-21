import { Injectable, signal } from '@angular/core';

export interface Notification {
  id: number;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message: string;
  link?: string;
  read: boolean;
  created_at: Date;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private notifications = signal<Notification[]>([]);
  private idCounter = 0;

  getNotifications(): Notification[] {
    return this.notifications();
  }

  get unreadCount(): number {
    return this.notifications().filter(n => !n.read).length;
  }

  success(title: string, message: string, link?: string): void {
    console.log('✅ Notification SUCCÈS:', title, message);
    this.add({ type: 'success', title, message, link });
  }

  error(title: string, message: string, link?: string): void {
    console.log('❌ Notification ERREUR:', title, message);
    this.add({ type: 'error', title, message, link });
  }

  info(title: string, message: string, link?: string): void {
    console.log('ℹ️ Notification INFO:', title, message);
    this.add({ type: 'info', title, message, link });
  }

  warning(title: string, message: string, link?: string): void {
    console.log('⚠️ Notification AVERTISSEMENT:', title, message);
    this.add({ type: 'warning', title, message, link });
  }

  private add(notification: Omit<Notification, 'id' | 'read' | 'created_at'>): void {
    const id = ++this.idCounter;
    const newNotification: Notification = {
      ...notification,
      id,
      read: false,
      created_at: new Date()
    };

    this.notifications.update(list => [newNotification, ...list]);
    console.log('📋 Nombre de notifications:', this.notifications().length);

    // Auto-suppression après 10 secondes
    setTimeout(() => {
      this.remove(id);
      console.log('⏰ Notification supprimée automatiquement:', id);
    }, 10000);
  }

  remove(id: number): void {
    this.notifications.update(list => list.filter(n => n.id !== id));
  }

  markAsRead(id: number): void {
    this.notifications.update(list =>
      list.map(n => n.id === id ? { ...n, read: true } : n)
    );
  }

  markAllAsRead(): void {
    this.notifications.update(list =>
      list.map(n => ({ ...n, read: true }))
    );
  }

  clearAll(): void {
    this.notifications.set([]);
  }
}