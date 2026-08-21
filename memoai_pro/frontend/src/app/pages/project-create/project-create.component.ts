import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { LayoutComponent } from '../../layout/layout.component';
import { ProjectsService } from '../../core/projects.service';

import { Project } from '../../core/models';


@Component({
  standalone: true,

  selector: 'app-project-create',

  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    LayoutComponent
  ],

  templateUrl: './project-create.component.html',

  styleUrl: './project-create.component.css'
})
export class ProjectCreateComponent {

  // ============================================================
  // FORMULAIRE
  // ============================================================

  f: {
    title: string;

    theme: string;

    level: 'LICENCE' | 'MASTER' | 'DOCTORAT';

    university: string;

    faculty: string;

    department: string;

    field_of_study: string;

    option: string;

    academic_year: string;

    country: string;

    city: string;

    language: string;

    desired_pages: number;

  } = {

    title: '',

    theme: '',

    level: 'MASTER',

    university: '',

    faculty: '',

    department: '',

    field_of_study: '',

    option: '',

    academic_year: '2026-2027',

    country: 'Mali',

    city: 'Bamako',

    language: 'fr',

    desired_pages: 50

  };


  // ============================================================
  // ÉTAT
  // ============================================================

  loading = false;

  error = '';


  // ============================================================
  // CONSTRUCTEUR
  // ============================================================

  constructor(
    private service: ProjectsService,
    private router: Router
  ) {}


  // ============================================================
  // CRÉER LE MÉMOIRE
  // ============================================================

  submit(): void {

    this.error = '';

    // Protection contre double clic
    if (this.loading) {
      return;
    }

    this.loading = true;


    // On crée une copie du formulaire
    const projectData: Partial<Project> = {

      title: this.f.title,

      theme: this.f.theme,

      level: this.f.level,

      university: this.f.university,

      faculty: this.f.faculty,

      department: this.f.department,

      field_of_study: this.f.field_of_study,

      option: this.f.option,

      academic_year: this.f.academic_year,

      country: this.f.country,

      city: this.f.city,

      language: this.f.language,

      desired_pages: this.f.desired_pages

    };


    console.log(
      'Données envoyées au backend :',
      projectData
    );


    this.service.create(projectData).subscribe({

      // ========================================================
      // SUCCÈS
      // ========================================================

      next: (project: Project) => {

        console.log(
          'Mémoire créé :',
          project
        );

        this.loading = false;


        // Vérification de l'ID
        if (project.id === undefined) {

          this.error =
            'Le mémoire a été créé mais son identifiant est introuvable.';

          return;
        }


        // Aller vers l'éditeur
        this.router.navigate([
          '/projects',
          project.id,
          'editor'
        ]);

      },


      // ========================================================
      // ERREUR
      // ========================================================

      error: (error) => {

        console.error(
          'Erreur création mémoire :',
          error
        );

        this.loading = false;

        this.error =
          this.formatError(error?.error) ||
          'Impossible de créer le mémoire. Vérifiez les informations saisies.';

      }

    });

  }


  // ============================================================
  // FORMATAGE DES ERREURS DJANGO
  // ============================================================

  private formatError(error: unknown): string {

    if (!error) {
      return '';
    }


    if (typeof error === 'string') {
      return error;
    }


    if (typeof error === 'object') {

      return Object.entries(
        error as Record<string, unknown>
      )

        .map(([key, value]) => {

          if (Array.isArray(value)) {

            return `${key}: ${value.join(', ')}`;

          }

          return `${key}: ${String(value)}`;

        })

        .join(' | ');

    }


    return String(error);
  }

}