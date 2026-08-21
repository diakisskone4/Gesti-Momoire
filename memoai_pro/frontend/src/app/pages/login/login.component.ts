import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  standalone: true,
  selector: 'app-login',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
  <div class="auth-page">
    <div class="visual">
      <div class="visual-inner">
        <span class="pill">✦ MEMOAI PRO</span>
        <h1>Construisez un mémoire<br><em>plus intelligent.</em></h1>
        <p>Organisez vos idées, rédigez vos chapitres et utilisez l'intelligence artificielle pour améliorer votre travail universitaire.</p>
        <div class="quote">“Votre assistant académique, de la première idée jusqu'à la version finale.”</div>
      </div>
    </div>
    <div class="form-side">
      <div class="form-box">
        <div class="mobile-logo">M</div>
        <span class="eyebrow">BIENVENUE</span>
        <h2>Connexion</h2>
        <p class="sub">Connectez-vous à votre espace MemoAI Pro.</p>

        <form (ngSubmit)="submit()">
          <label>Email
            <input type="email" [(ngModel)]="email" name="email" placeholder="vous@universite.com" required>
          </label>
          <label>Mot de passe
            <input type="password" [(ngModel)]="password" name="password" placeholder="••••••••" required>
          </label>
          <div class="error" *ngIf="error">{{ error }}</div>
          <button class="primary" [disabled]="loading">{{ loading ? 'Connexion...' : 'Se connecter →' }}</button>
        </form>

        <p class="bottom">Vous n'avez pas encore de compte ? <a routerLink="/register">Créer un compte</a></p>
      </div>
    </div>
  </div>
  `,
  styles: [`
    .auth-page{min-height:100vh;display:grid;grid-template-columns:1.05fr .95fr;background:#fff}.visual{background:radial-gradient(circle at 75% 20%,#1c6b62 0,#0a3c37 40%,#062b28 100%);color:#fff;position:relative;overflow:hidden}.visual:after{content:"";position:absolute;width:460px;height:460px;border:1px solid #5eead455;border-radius:50%;right:-180px;bottom:-180px;box-shadow:0 0 0 70px #5eead412,0 0 0 140px #5eead408}.visual-inner{max-width:560px;padding:12vh 10%;position:relative;z-index:1}.pill{display:inline-block;padding:8px 12px;border:1px solid #ffffff25;background:#ffffff0c;border-radius:30px;font-size:10px;letter-spacing:2px;color:#a9e5dd}.visual h1{font-size:52px;line-height:1.05;margin:28px 0 20px;letter-spacing:-2px}.visual h1 em{color:#5eead4;font-style:normal}.visual p{max-width:500px;line-height:1.8;color:#c4e3df;font-size:15px}.quote{margin-top:60px;border-left:3px solid #fbbf24;padding:14px 18px;color:#e4f4f2;font-size:13px;max-width:430px}.form-side{display:grid;place-items:center;padding:40px}.form-box{width:min(410px,100%)}.mobile-logo{display:none}.eyebrow{font-size:10px;letter-spacing:2px;color:#0f766e;font-weight:800}.form-box h2{font-size:36px;margin:8px 0;color:#143d38}.sub{color:#70807f;margin-bottom:30px}.form-box label{display:block;color:#334b48;font-size:12px;font-weight:700;margin:17px 0}.form-box input{width:100%;box-sizing:border-box;margin-top:8px;padding:14px;border:1px solid #dce5e4;border-radius:11px;outline:none;font:inherit;background:#fbfdfd}.form-box input:focus{border-color:#0f766e;box-shadow:0 0 0 4px #0f766e12}.primary{width:100%;margin-top:12px;padding:15px;border:0;border-radius:11px;background:#0f766e;color:white;font-weight:800;cursor:pointer;box-shadow:0 10px 24px #0f766e25}.primary:disabled{opacity:.6}.error{padding:11px;background:#fff1f2;color:#be123c;border-radius:9px;font-size:12px}.bottom{text-align:center;color:#788886;font-size:12px;margin-top:24px}.bottom a{color:#0f766e;font-weight:800;text-decoration:none}@media(max-width:800px){.auth-page{grid-template-columns:1fr}.visual{display:none}.mobile-logo{display:grid;place-items:center;width:44px;height:44px;border-radius:13px;background:#0f766e;color:#fff;font-weight:900;margin-bottom:30px}.form-side{padding:28px}}
  `]
})
export class LoginComponent {
  email = ''; password = ''; loading = false; error = '';
  constructor(private auth: AuthService, private router: Router) {}
  submit() {
    this.error = ''; this.loading = true;
    this.auth.login(this.email.trim(), this.password).subscribe({
      next: () => { this.loading = false; this.router.navigate(['/dashboard']); },
      error: err => { this.loading = false; this.error = err?.error?.error || 'Email ou mot de passe incorrect.'; }
    });
  }
}
