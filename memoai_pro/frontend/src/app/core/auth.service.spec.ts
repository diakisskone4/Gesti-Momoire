import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AuthService } from './auth.service';
import { API_URL } from './api';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuthService]
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should login successfully', () => {
    const mockResponse = {
      access: 'fake-access-token',
      refresh: 'fake-refresh-token',
      user: { id: 1, email: 'test@test.com' }
    };

    service.login('test@test.com', 'password').subscribe(response => {
      expect(response).toEqual(mockResponse);
    });

    const req = httpMock.expectOne(`${API_URL}/users/login/`);
    expect(req.request.method).toBe('POST');
    req.flush(mockResponse);
  });

  it('should logout', () => {
    const logoutSpy = spyOn(service, 'logout').and.callThrough();
    service.logout();
    expect(logoutSpy).toHaveBeenCalled();
  });

  it('should refresh token', () => {
    const mockResponse = { access: 'new-access-token' };
    const refreshToken = 'fake-refresh-token';

    service.refresh(refreshToken).subscribe(response => {
      expect(response).toEqual(mockResponse);
    });

    const req = httpMock.expectOne(`${API_URL}/users/refresh/`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ refresh: refreshToken });
    req.flush(mockResponse);
  });

  it('should get profile', () => {
    const mockUser = { id: 1, email: 'test@test.com', first_name: 'Test' };

    service.profile().subscribe(user => {
      expect(user).toEqual(mockUser);
    });

    const req = httpMock.expectOne(`${API_URL}/users/profile/`);
    expect(req.request.method).toBe('GET');
    req.flush(mockUser);
  });

  it('should check if user is logged in', () => {
    // Simuler un token dans localStorage
    localStorage.setItem('memoai_access', 'fake-token');
    expect(service.isLoggedIn()).toBe(true);
    
    localStorage.removeItem('memoai_access');
    expect(service.isLoggedIn()).toBe(false);
  });
});