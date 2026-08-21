import { Component, OnInit, AfterViewInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';

import { LayoutComponent } from '../../layout/layout.component';
import { ProjectsService } from '../../core/projects.service';
import { AuthService } from '../../core/auth.service';
import { Project } from '../../core/models';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LayoutComponent
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit, AfterViewInit {
  @ViewChild('statusChart') statusChartRef!: ElementRef;
  @ViewChild('progressChart') progressChartRef!: ElementRef;

  projects: Project[] = [];
  loading = true;
  error = '';
  
  stats = {
    total: 0,
    draft: 0,
    inProgress: 0,
    completed: 0,
    totalChapters: 0,
    totalWords: 0
  };
  
  recentProjects: Project[] = [];
  recentActivity: { date: Date; message: string; type: string }[] = [];

  private statusChart: Chart | null = null;
  private progressChart: Chart | null = null;

  constructor(
    private projectsService: ProjectsService,
    public authService: AuthService,
    private router: Router
  ) {}

  get userName(): string {
    const user = this.authService.user();
    if (!user) return 'Utilisateur';
    if (user.first_name && user.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    return user.email || 'Utilisateur';
  }

  getInitials(): string {
    const user = this.authService.user();
    if (!user) return 'U';
    const first = user.first_name?.charAt(0) || '';
    const last = user.last_name?.charAt(0) || '';
    return (first + last) || user.email?.charAt(0) || 'U';
  }

  getGreeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Bonjour';
    if (hour < 18) return 'Bon après-midi';
    return 'Bonsoir';
  }

  ngOnInit(): void {
    this.loadDashboard();
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.initCharts();
    }, 500);
  }

  loadDashboard(): void {
    this.loading = true;
    this.error = '';

    this.projectsService.list().subscribe({
      next: (projects) => {
        console.log('✅ Projets chargés:', projects);
        this.projects = projects;
        this.calculateStats(projects);
        this.recentProjects = projects.slice(0, 4);
        this.generateRecentActivity(projects);
        this.loading = false;
        
        setTimeout(() => {
          this.initCharts();
        }, 300);
      },
      error: (err) => {
        console.error('❌ Erreur chargement:', err);
        this.error = 'Impossible de charger le tableau de bord.';
        this.loading = false;
      }
    });
  }

  calculateStats(projects: Project[]): void {
    this.stats.total = projects.length;
    this.stats.draft = projects.filter(p => p.status === 'DRAFT' || p.status === 'draft').length;
    this.stats.inProgress = projects.filter(p => p.status === 'IN_PROGRESS' || p.status === 'in_progress').length;
    this.stats.completed = projects.filter(p => p.status === 'COMPLETED' || p.status === 'completed').length;

    let totalChapters = 0;
    let totalWords = 0;

    projects.forEach(project => {
      if (project.chapters) {
        totalChapters += project.chapters.length;
        project.chapters.forEach(chapter => {
          if (chapter.content) {
            totalWords += chapter.content.split(/\s+/).length;
          }
        });
      }
    });

    this.stats.totalChapters = totalChapters;
    this.stats.totalWords = totalWords;
  }

  generateRecentActivity(projects: Project[]): void {
    this.recentActivity = [];
    
    projects.slice(0, 5).forEach(project => {
      if (project.updated_at) {
        this.recentActivity.push({
          date: new Date(project.updated_at),
          message: `📝 "${project.title}" a été mis à jour`,
          type: 'update'
        });
      }
      if (project.created_at) {
        this.recentActivity.push({
          date: new Date(project.created_at),
          message: `📄 "${project.title}" a été créé`,
          type: 'create'
        });
      }
    });

    this.recentActivity.sort((a, b) => b.date.getTime() - a.date.getTime());
    this.recentActivity = this.recentActivity.slice(0, 5);
  }

  initCharts(): void {
    if (!this.statusChartRef || !this.progressChartRef) return;

    if (this.statusChart) {
      this.statusChart.destroy();
      this.statusChart = null;
    }
    if (this.progressChart) {
      this.progressChart.destroy();
      this.progressChart = null;
    }

    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--text-primary') || '#173e3a';
    const mutedColor = getComputedStyle(document.documentElement).getPropertyValue('--text-muted') || '#748482';
    const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--border-color') || '#e5eceb';
    const cardColor = getComputedStyle(document.documentElement).getPropertyValue('--bg-card') || '#ffffff';

    // ✅ Graphique des statuts - CORRIGÉ
    this.statusChart = new Chart(this.statusChartRef.nativeElement, {
      type: 'doughnut',
      data: {
        labels: ['Brouillon', 'En cours', 'Terminé'],
        datasets: [{
          data: [
            this.stats.draft || 1,
            this.stats.inProgress || 1,
            this.stats.completed || 1
          ],
          backgroundColor: ['#70807f', '#3b82f6', '#22c55e'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: textColor,
              font: {
                size: 12,
                weight: 'normal'  // ✅ Changé de '500' à 'normal'
              },
              padding: 16
            }
          }
        },
        cutout: '65%'
      }
    });

    // ✅ Graphique d'évolution - CORRIGÉ
    this.progressChart = new Chart(this.progressChartRef.nativeElement, {
      type: 'line',
      data: {
        labels: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun'],
        datasets: [{
          label: 'Mots écrits',
          data: [
            0,
            Math.round(this.stats.totalWords * 0.2),
            Math.round(this.stats.totalWords * 0.4),
            Math.round(this.stats.totalWords * 0.6),
            Math.round(this.stats.totalWords * 0.8),
            this.stats.totalWords || 0
          ],
          borderColor: '#0f766e',
          backgroundColor: 'rgba(15, 118, 110, 0.1)',
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#0f766e',
          pointBorderColor: cardColor,
          pointBorderWidth: 2,
          pointRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: textColor,
              font: {
                size: 12,
                weight: 'normal'  // ✅ Changé de '500' à 'normal'
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { color: mutedColor },
            grid: { color: borderColor }
          },
          x: {
            ticks: { color: mutedColor },
            grid: { color: borderColor }
          }
        }
      }
    });
  }

  getStatusLabel(status: string): string {
    const labels: { [key: string]: string } = {
      'DRAFT': 'Brouillon',
      'draft': 'Brouillon',
      'IN_PROGRESS': 'En cours',
      'in_progress': 'En cours',
      'REVIEW': 'En révision',
      'review': 'En révision',
      'COMPLETED': 'Terminé',
      'completed': 'Terminé'
    };
    return labels[status] || status;
  }

  getStatusClass(status: string): string {
    const classes: { [key: string]: string } = {
      'DRAFT': 'status-draft',
      'draft': 'status-draft',
      'IN_PROGRESS': 'status-progress',
      'in_progress': 'status-progress',
      'REVIEW': 'status-review',
      'review': 'status-review',
      'COMPLETED': 'status-completed',
      'completed': 'status-completed'
    };
    return classes[status] || '';
  }

  openProject(id: number): void {
    this.router.navigate(['/projects', id, 'editor']);
  }

  createProject(): void {
    this.router.navigate(['/projects/new']);
  }
}