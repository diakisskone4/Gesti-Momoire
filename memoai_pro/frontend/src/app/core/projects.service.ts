import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { Project, Chapter } from './models';

@Injectable({
  providedIn: 'root'
})
export class ProjectsService {

  private apiUrl = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  list(): Observable<Project[]> {
    console.log('📡 Appel API: GET /projects/projects/');
    return this.http.get<Project[]>(`${this.apiUrl}/projects/projects/`);
  }

  get(id: number): Observable<Project> {
    return this.http.get<Project>(`${this.apiUrl}/projects/projects/${id}/`);
  }

  create(data: Partial<Project>): Observable<Project> {
    return this.http.post<Project>(`${this.apiUrl}/projects/projects/`, data);
  }

  update(id: number, data: Partial<Project>): Observable<Project> {
    return this.http.patch<Project>(`${this.apiUrl}/projects/projects/${id}/`, data);
  }

  delete(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/projects/projects/${id}/`);
  }

  chapters(projectId: number): Observable<Chapter[]> {
    return this.http.get<Chapter[]>(`${this.apiUrl}/projects/chapters/?project=${projectId}`);
  }

  createChapter(data: Partial<Chapter>): Observable<Chapter> {
    return this.http.post<Chapter>(`${this.apiUrl}/projects/chapters/`, data);
  }

  updateChapter(id: number, data: Partial<Chapter>): Observable<Chapter> {
    return this.http.patch<Chapter>(`${this.apiUrl}/projects/chapters/${id}/`, data);
  }

  deleteChapter(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/projects/chapters/${id}/`);
  }

  exportProject(projectId: number, data: any): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/projects/projects/${projectId}/export/`,
      data,
      { responseType: 'blob' as 'json' }
    );
  }

  generatePlan(projectId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/ai/generate-plan/`, { project_id: projectId });
  }
}