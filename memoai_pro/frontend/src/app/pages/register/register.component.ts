import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  standalone: true,
  selector: 'app-register',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
  <div class="auth-page">
    <div class="visual"><div class="visual-inner"><span class="pill">✦ REJOIGNEZ MEMOAI</span><h1>Donnez vie à votre<br><em>projet académique.</em></h1><p>Un espace moderne pour structurer votre mémoire, collaborer avec vos encadreurs et travailler avec l'IA.</p></div></div>
    <div class="form-side"><div class="form-box">
      <a class="back" routerLink="/login">← Retour à la connexion</a>
      <span class="eyebrow">NOUVEAU COMPTE</span><h2>Créer un compte</h2><p class="sub">Commencez gratuitement votre projet.</p>
      <form (ngSubmit)="submit()">
        <div class="grid"><label>Prénom<input [(ngModel)]="first_name" name="first_name" required></label><label>Nom<input [(ngModel)]="last_name" name="last_name" required></label></div>
        <label>Email<input type="email" [(ngModel)]="email" name="email" required></label>
        <label>Téléphone<input [(ngModel)]="phone" name="phone" placeholder="+223 ..."></label>
        <div class="grid"><label>Mot de passe<input type="password" [(ngModel)]="password" name="password" required minlength="8"></label><label>Confirmation<input type="password" [(ngModel)]="password2" name="password2" required></label></div>
        <div class="error" *ngIf="error">{{error}}</div>
        <button class="primary" [disabled]="loading">{{loading ? 'Création...' : 'Créer mon compte →'}}</button>
      </form>
      <p class="bottom">Déjà inscrit ? <a routerLink="/login">Se connecter</a></p>
    </div></div>
  </div>
  `,
  styles: [`
    .auth-page{min-height:100vh;display:grid;grid-template-columns:1.05fr .95fr;background:#fff}.visual{background:radial-gradient(circle at 75% 20%,#1c6b62 0,#0a3c37 40%,#062b28 100%);color:#fff}.visual-inner{max-width:560px;padding:12vh 10%}.pill{padding:8px 12px;border:1px solid #ffffff25;border-radius:30px;font-size:10px;letter-spacing:2px;color:#a9e5dd}.visual h1{font-size:48px;line-height:1.05;margin:28px 0 20px;letter-spacing:-2px}.visual h1 em{color:#5eead4;font-style:normal}.visual p{color:#c4e3df;line-height:1.8}.form-side{display:grid;place-items:center;padding:35px}.form-box{width:min(500px,100%)}.back{display:inline-block;color:#70807f;text-decoration:none;font-size:12px;margin-bottom:35px}.eyebrow{font-size:10px;letter-spacing:2px;color:#0f766e;font-weight:800}.form-box h2{font-size:34px;margin:8px 0;color:#143d38}.sub{color:#70807f}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.form-box label{display:block;color:#334b48;font-size:12px;font-weight:700;margin:13px 0}.form-box input{width:100%;box-sizing:border-box;margin-top:7px;padding:13px;border:1px solid #dce5e4;border-radius:10px;outline:none}.primary{width:100%;margin-top:10px;padding:14px;border:0;border-radius:11px;background:#0f766e;color:#fff;font-weight:800;cursor:pointer}.error{padding:11px;background:#fff1f2;color:#be123c;border-radius:9px;font-size:12px}.bottom{text-align:center;color:#788886;font-size:12px}.bottom a{color:#0f766e;font-weight:800}@media(max-width:800px){.visual{display:none}}@media(max-width:550px){.grid{grid-template-columns:1fr}}
  `]
})
export class RegisterComponent {
  email=''; first_name=''; last_name=''; phone=''; password=''; password2=''; loading=false; error='';
  constructor(private auth: AuthService, private router: Router) {}
  submit() {
    this.error='';
    if(this.password !== this.password2){this.error='Les mots de passe ne correspondent pas.';return;}
    this.loading=true;
    this.auth.register({email:this.email.trim(),first_name:this.first_name.trim(),last_name:this.last_name.trim(),phone:this.phone,password:this.password,password2:this.password2,role:'STUDENT',language:'fr'}).subscribe({
      next:()=>{this.loading=false;this.router.navigate(['/dashboard']);},
      error:err=>{this.loading=false;this.error=this.formatError(err?.error)||'Impossible de créer le compte.';}
    });
  }
  private formatError(e: unknown): string {
    if(!e) return '';
    if(typeof e==='string') return e;
    if(typeof e==='object') return Object.entries(e as Record<string,unknown>).map(([k,v])=>`${k}: ${Array.isArray(v)?v.join(', '):String(v)}`).join(' | ');
    return String(e);
  }
}
