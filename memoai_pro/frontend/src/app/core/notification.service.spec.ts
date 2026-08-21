import { TestBed } from '@angular/core/testing';
import { NotificationService } from './notification.service';

describe('NotificationService', () => {
  let service: NotificationService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(NotificationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should add a success notification', () => {
    service.success('Test', 'Test message');
    expect(service.getNotifications().length).toBe(1);
    expect(service.getNotifications()[0].type).toBe('success');
    expect(service.getNotifications()[0].title).toBe('Test');
  });

  it('should add an error notification', () => {
    service.error('Error', 'Error message');
    expect(service.getNotifications().length).toBe(1);
    expect(service.getNotifications()[0].type).toBe('error');
  });

  it('should mark notification as read', () => {
    service.success('Test', 'Test message');
    const id = service.getNotifications()[0].id;
    service.markAsRead(id);
    // ✅ Remplacer .toBeTrue() par .toBe(true)
    expect(service.getNotifications()[0].read).toBe(true);
  });

  it('should remove notification', () => {
    service.success('Test', 'Test message');
    const id = service.getNotifications()[0].id;
    service.remove(id);
    expect(service.getNotifications().length).toBe(0);
  });

  it('should clear all notifications', () => {
    service.success('Test1', 'Message1');
    service.success('Test2', 'Message2');
    service.clearAll();
    expect(service.getNotifications().length).toBe(0);
  });

  it('should count unread notifications', () => {
    service.success('Test1', 'Message1');
    service.success('Test2', 'Message2');
    expect(service.unreadCount).toBe(2);
    service.markAllAsRead();
    expect(service.unreadCount).toBe(0);
  });
});