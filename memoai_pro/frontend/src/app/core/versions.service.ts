import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from './api';

export interface Version {
  id?: number;
  chapter: number;
  version_number: number;
  title: string;
  content: string;
  status: string;
  created_at: string;
  created_by: string;
}

@Injectable({
  providedIn: 'root'
})
export class VersionsService {
  private apiUrl = API_URL;

  constructor(private http: HttpClient) {}

  list(chapterId: number): Observable<Version[]> {
    return this.http.get<Version[]>(`${this.apiUrl}/projects/versions/?chapter=${chapterId}`);
  }

  get(id: number): Observable<Version> {
    return this.http.get<Version>(`${this.apiUrl}/projects/versions/${id}/`);
  }

  restore(versionId: number, chapterId: number): Observable<Version> {
    return this.http.post<Version>(`${this.apiUrl}/projects/versions/${versionId}/restore/`, {
      chapter_id: chapterId
    });
  }

  compare(versionId1: number, versionId2: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/projects/versions/compare/${versionId1}/${versionId2}/`);
  }
}