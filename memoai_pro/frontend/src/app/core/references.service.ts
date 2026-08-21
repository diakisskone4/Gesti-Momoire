import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from './api';

export interface Reference {
  id?: number;
  project: number;
  title: string;
  authors: string;
  year: number;
  journal?: string;
  doi?: string;
  isbn?: string;
  bibtex?: string;
  style?: string;
  created_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ReferencesService {
  private apiUrl = API_URL;

  constructor(private http: HttpClient) {}

  list(projectId: number): Observable<Reference[]> {
    return this.http.get<Reference[]>(`${this.apiUrl}/projects/references/?project_id=${projectId}`);
  }

  create(data: Partial<Reference>): Observable<Reference> {
    return this.http.post<Reference>(`${this.apiUrl}/projects/references/`, data);
  }

  update(id: number, data: Partial<Reference>): Observable<Reference> {
    return this.http.patch<Reference>(`${this.apiUrl}/projects/references/${id}/`, data);
  }

  delete(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/projects/references/${id}/`);
  }

  importByDOI(doi: string, projectId: number): Observable<Reference> {
    return this.http.post<Reference>(`${this.apiUrl}/projects/references/import_by_doi/`, {
      doi,
      project_id: projectId
    });
  }

  generateBibtex(id: number): Observable<{ bibtex: string }> {
    return this.http.get<{ bibtex: string }>(`${this.apiUrl}/projects/references/${id}/bibtex/`);
  }
}