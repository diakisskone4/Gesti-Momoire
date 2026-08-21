import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { LayoutComponent } from '../../layout/layout.component';
import { ProjectsService } from '../../core/projects.service';
import { Project } from '../../core/models';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LayoutComponent
  ],
  templateUrl: './projects.component.html',
  styleUrls: ['./projects.component.css']
})
export class ProjectsComponent implements OnInit {
  projects: Project[] = [];
  filteredProjects: Project[] = [];
  loading = true;
  error = '';
  searchTerm = '';

  constructor(
    private projectsService: ProjectsService,
    private router: Router,
    private cdr: ChangeDetectorRef  // ✅ Ajouter ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    console.log('🔍 ProjectsComponent initialisé');
    this.loadProjects();
  }

  loadProjects(): void {
    console.log('🔄 Chargement des projets...');
    this.loading = true;
    this.error = '';
    
    this.projectsService.list().subscribe({
      next: (projects) => {
        console.log('✅ Projets chargés:', projects);
        console.log('📊 Nombre de projets:', projects?.length || 0);
        
        if (projects && Array.isArray(projects)) {
          this.projects = projects;
          this.filteredProjects = [...projects];
          this.loading = false;
        } else {
          this.projects = [];
          this.filteredProjects = [];
          this.loading = false;
          console.warn('⚠️ Aucun projet reçu');
        }
        
        this.cdr.detectChanges();  // ✅ Forcer la détection de changement
        console.log('✅ loading =', this.loading);
        console.log('✅ Nombre de projets affichés:', this.filteredProjects.length);
      },
      error: (err) => {
        console.error('❌ Erreur chargement projets:', err);
        this.error = err.error?.message || 'Impossible de charger vos mémoires.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  filterProjects(): void {
    if (!this.searchTerm.trim()) {
      this.filteredProjects = [...this.projects];
      return;
    }

    const term = this.searchTerm.toLowerCase();
    this.filteredProjects = this.projects.filter(project =>
      project.title?.toLowerCase().includes(term) ||
      (project.theme && project.theme.toLowerCase().includes(term))
    );
  }

  createProject(): void {
    this.router.navigate(['/projects/new']);
  }

  openProject(id: number): void {
    if (id) {
      this.router.navigate(['/projects', id, 'editor']);
    }
  }

  deleteProject(id: number): void {
    if (!id) return;
    if (confirm('Êtes-vous sûr de vouloir supprimer ce mémoire ?')) {
      this.projectsService.delete(id).subscribe({
        next: () => {
          this.projects = this.projects.filter(p => p.id !== id);
          this.filteredProjects = this.filteredProjects.filter(p => p.id !== id);
        },
        error: (err) => {
          console.error('❌ Erreur suppression:', err);
          this.error = 'Impossible de supprimer le mémoire.';
        }
      });
    }
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
    return labels[status] || status || 'Brouillon';
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
    return classes[status] || 'status-draft';
  }

  refresh(): void {
    this.loadProjects();
  }
}