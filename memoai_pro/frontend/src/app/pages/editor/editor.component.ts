import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { LayoutComponent } from '../../layout/layout.component';
import { ProjectsService } from '../../core/projects.service';
import { Project, Chapter } from '../../core/models';
import { ExportModalComponent } from './export.component';
import { ReferencesModalComponent } from './references.component';
import { CollaborationModalComponent } from './collaboration.component';
import { Reference } from '../../core/references.service';
import { NotificationService } from '../../core/notification.service';

@Component({
  selector: 'app-editor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    LayoutComponent,
    ExportModalComponent,
    ReferencesModalComponent,
    CollaborationModalComponent
  ],
  templateUrl: './editor.component.html',
  styleUrls: ['./editor.component.css']
})
export class EditorComponent implements OnInit {
  project: Project | null = null;
  chapters: Chapter[] = [];
  selected: Chapter | null = null;
  loading = true;
  saving = false;
  generatingPlan = false;
  message = '';
  error = '';
  projectId = 0;
  showExportModal = false;
  showReferencesModal = false;
  showCollaborationModal = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    public projects: ProjectsService,
    private cdr: ChangeDetectorRef,
    private notificationService: NotificationService
  ) {}

  ngOnInit(): void {
    console.log('📝 EditorComponent initialisé');
    
    this.route.paramMap.subscribe(params => {
      const id = Number(params.get('id'));
      console.log('📌 ID du projet:', id);
      
      if (!id || Number.isNaN(id)) {
        console.error('❌ ID invalide');
        this.router.navigate(['/projects']);
        return;
      }

      this.projectId = id;
      this.loadProjectAndChapters();
    });
  }

  loadProjectAndChapters(): void {
    console.log('🔄 Début du chargement pour le projet:', this.projectId);
    this.loading = true;
    this.error = '';
    this.message = '';

    forkJoin({
      project: this.projects.get(this.projectId),
      chapters: this.projects.chapters(this.projectId)
    }).subscribe({
      next: (result) => {
        console.log('✅ Données reçues:', result);
        console.log('✅ Nombre de chapitres:', result.chapters?.length || 0);
        
        this.project = result.project;
        this.chapters = result.chapters || [];
        
        if (this.chapters.length > 0) {
          console.log('✅ Liste des chapitres:', this.chapters.map(c => c.title));
          this.selected = this.chapters[0];
          console.log('✅ Chapitre sélectionné:', this.selected);
        } else {
          console.warn('⚠️ Aucun chapitre trouvé pour ce projet');
        }
        
        this.loading = false;
        this.cdr.detectChanges();
        console.log('✅ Chargement terminé, loading =', this.loading);
      },
      error: (err) => {
        console.error('❌ Erreur de chargement:', err);
        this.error = 'Impossible de charger le mémoire.';
        this.loading = false;
        this.cdr.detectChanges();
        this.notificationService.error(
          'Erreur de chargement',
          'Impossible de charger le mémoire. Veuillez réessayer.'
        );
      }
    });
  }

  selectChapter(chapter: Chapter): void {
    console.log('📖 Chapitre sélectionné:', chapter);
    this.selected = chapter;
    this.message = '';
    this.error = '';
  }

  addChapter(): void {
    if (!this.projectId) {
      console.error('❌ Pas de projet ID');
      return;
    }

    const order = this.chapters.length + 1;
    const chapter: Partial<Chapter> = {
      project: this.projectId,
      parent: null,
      order: order,
      title: `Chapitre ${order}`,
      content: '',
      type: 'chapter',
      status: 'draft',
      version: 1
    };

    console.log('📝 Création du chapitre:', chapter);

    this.projects.createChapter(chapter).subscribe({
      next: (created: Chapter) => {
        console.log('✅ Chapitre créé:', created);
        this.chapters = [...this.chapters, created];
        this.selected = created;
        this.message = 'Chapitre créé avec succès.';
        this.error = '';
        this.cdr.detectChanges();
        this.notificationService.success(
          'Chapitre créé',
          `"${created.title}" a été créé avec succès`
        );
        console.log('✅ Liste des chapitres mise à jour:', this.chapters.map(c => c.title));
      },
      error: (err: any) => {
        console.error('❌ Erreur création chapitre:', err);
        this.error = err.error?.message || 'Impossible de créer le chapitre.';
        this.message = '';
        this.cdr.detectChanges();
        this.notificationService.error(
          'Erreur de création',
          'Impossible de créer le chapitre. Veuillez réessayer.'
        );
      }
    });
  }

  saveChapter(): void {
    if (!this.selected || this.selected.id === undefined) {
      console.warn('⚠️ Aucun chapitre sélectionné');
      return;
    }

    this.saving = true;
    this.message = '';
    this.error = '';

    const chapterId = this.selected.id;
    
    const data: any = {
      title: this.selected.title,
      content: this.selected.content,
    };

    if (this.selected.status) {
      data.status = this.selected.status;
    }

    if (this.selected.type) {
      data.type = this.selected.type;
    }

    console.log(`✏️ Sauvegarde du chapitre ${chapterId}:`, data);

    this.projects.updateChapter(chapterId, data).subscribe({
      next: (updated: Chapter) => {
        console.log('✅ Chapitre sauvegardé:', updated);
        this.selected = updated;
        this.chapters = this.chapters.map(chapter =>
          chapter.id === updated.id ? updated : chapter
        );
        this.saving = false;
        this.message = 'Chapitre sauvegardé avec succès.';
        this.error = '';
        this.cdr.detectChanges();
        this.notificationService.success(
          'Chapitre sauvegardé',
          `"${updated.title}" a été sauvegardé avec succès`
        );
      },
      error: (err: any) => {
        console.error('❌ Erreur sauvegarde chapitre:', err);
        this.saving = false;
        
        if (err.error) {
          if (typeof err.error === 'object') {
            const errors = Object.values(err.error).join(', ');
            this.error = `Erreur: ${errors}`;
          } else {
            this.error = err.error.message || 'Impossible de sauvegarder le chapitre.';
          }
        } else {
          this.error = 'Impossible de sauvegarder le chapitre.';
        }
        
        this.cdr.detectChanges();
        this.notificationService.error(
          'Erreur de sauvegarde',
          'Impossible de sauvegarder le chapitre. Veuillez réessayer.'
        );
      }
    });
  }

  generatePlan(): void {
    if (!this.project || this.project.id === undefined) {
      return;
    }

    this.generatingPlan = true;
    this.message = '';
    this.error = '';

    const projectId = this.project.id;

    this.projects.generatePlan(projectId).subscribe({
      next: (response: unknown) => {
        console.log('✅ Plan généré:', response);
        this.generatingPlan = false;
        this.message = 'La génération du plan a été lancée avec succès.';
        this.loadProjectAndChapters();
        this.cdr.detectChanges();
        this.notificationService.info(
          'Plan en cours de génération',
          'Le plan de votre mémoire est en cours de génération par l\'IA'
        );
      },
      error: (err: any) => {
        console.error('❌ Erreur génération plan:', err);
        this.generatingPlan = false;
        this.error = err.error?.message || 'Impossible de générer le plan.';
        this.cdr.detectChanges();
        this.notificationService.error(
          'Erreur de génération',
          'Impossible de générer le plan. Veuillez réessayer.'
        );
      }
    });
  }

  renameChapter(): void {
    if (!this.selected || this.selected.id === undefined) {
      return;
    }

    const title = window.prompt('Nouveau titre du chapitre :', this.selected.title);

    if (title === null || title.trim() === '') {
      return;
    }

    this.selected.title = title.trim();
    this.saveChapter();
  }

  backToProjects(): void {
    this.router.navigate(['/projects']);
  }

  refreshChapters(): void {
    console.log('🔄 Rechargement des chapitres...');
    this.projects.chapters(this.projectId).subscribe({
      next: (chapters) => {
        console.log('✅ Chapitres rechargés:', chapters);
        this.chapters = chapters;
        if (this.chapters.length > 0 && !this.selected) {
          this.selected = this.chapters[0];
        }
        this.cdr.detectChanges();
        this.notificationService.success(
          'Chapitres rechargés',
          `${chapters.length} chapitre(s) chargé(s)`
        );
      },
      error: (err) => {
        console.error('❌ Erreur rechargement:', err);
        this.notificationService.error(
          'Erreur de rechargement',
          'Impossible de recharger les chapitres.'
        );
      }
    });
  }

  // ==========================================
  // EXPORT
  // ==========================================

  openExportModal(): void {
    this.showExportModal = true;
  }

  onExportClose(): void {
    this.showExportModal = false;
  }

  onExportSuccess(event: { format: string; url: string }): void {
    console.log('✅ Export réussi:', event);
    this.message = `Mémoire exporté en ${event.format.toUpperCase()}`;
    this.notificationService.success(
      'Export réussi',
      `Le mémoire a été exporté en ${event.format.toUpperCase()}`
    );
  }

  // ==========================================
  // BIBLIOGRAPHIE
  // ==========================================

  openReferencesModal(): void {
    this.showReferencesModal = true;
  }

  onReferencesClose(): void {
    this.showReferencesModal = false;
  }

  onReferencesUpdated(references: Reference[]): void {
    console.log('📚 Références mises à jour:', references);
    this.message = `${references.length} référence(s) enregistrée(s)`;
    this.cdr.detectChanges();
    this.notificationService.success(
      'Bibliographie mise à jour',
      `${references.length} référence(s) enregistrée(s)`
    );
  }

  // ==========================================
  // COLLABORATION
  // ==========================================

  openCollaborationModal(): void {
    this.showCollaborationModal = true;
  }

  onCollaborationClose(): void {
    this.showCollaborationModal = false;
  }
}