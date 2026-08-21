import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {

  const auth = inject(AuthService);

  const token = auth.accessToken();

  // Les requêtes publiques n'ont pas besoin du JWT
  if (
    !token ||
    req.url.includes('/users/login/') ||
    req.url.includes('/users/register/') ||
    req.url.includes('/users/refresh/')
  ) {
    return next(req);
  }

  // Ajouter automatiquement le JWT
  const authReq = req.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`
    }
  });

  return next(authReq);
};