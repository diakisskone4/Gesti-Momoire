import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { API_URL } from './api';
import { AuthResponse, User } from './models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly accessKey = 'memoai_access';
  private readonly refreshKey = 'memoai_refresh';
  private readonly userKey = 'memoai_user';

  readonly user = signal<User | null>(this.readUser());

  constructor(private http: HttpClient, private router: Router) {}

  login(email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${API_URL}/users/login/`, { email, password })
      .pipe(tap(res => this.saveSession(res)));
  }

  register(payload: {
    email: string;
    first_name: string;
    last_name: string;
    phone: string;
    password: string;
    password2: string;
    role: string;
    language: string;
  }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${API_URL}/users/register/`, payload)
      .pipe(tap(res => this.saveSession(res)));
  }

  refresh(refresh: string): Observable<{ access: string }> {
    return this.http.post<{ access: string }>(`${API_URL}/users/refresh/`, { refresh })
      .pipe(tap(res => localStorage.setItem(this.accessKey, res.access)));
  }

  profile(): Observable<User> {
    return this.http.get<User>(`${API_URL}/users/profile/`)
      .pipe(tap(user => this.setUser(user)));
  }

  logout(): void {
    const refresh = localStorage.getItem(this.refreshKey);
    if (refresh) {
      this.http.post(`${API_URL}/users/logout/`, { refresh }).subscribe({
        error: () => undefined
      });
    }
    localStorage.removeItem(this.accessKey);
    localStorage.removeItem(this.refreshKey);
    localStorage.removeItem(this.userKey);
    this.user.set(null);
    this.router.navigate(['/login']);
  }

  accessToken(): string | null {
    return localStorage.getItem(this.accessKey);
  }

  isLoggedIn(): boolean {
    return !!this.accessToken();
  }

  setUser(user: User): void {
    localStorage.setItem(this.userKey, JSON.stringify(user));
    this.user.set(user);
  }

  private saveSession(res: AuthResponse): void {
    localStorage.setItem(this.accessKey, res.access);
    localStorage.setItem(this.refreshKey, res.refresh);
    this.setUser(res.user);
  }

  private readUser(): User | null {
    try {
      const raw = localStorage.getItem(this.userKey);
      return raw ? JSON.parse(raw) as User : null;
    } catch {
      return null;
    }
  }
}
