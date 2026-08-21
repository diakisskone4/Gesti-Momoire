import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from './api';

@Injectable({ providedIn: 'root' })
export class AiService {
  constructor(private http: HttpClient) {}

  chat(message: string, projectId?: number): Observable<{response: string}> {
    return this.http.post<{response: string}>(`${API_URL}/ai/chat/`, {
      message,
      project_id: projectId ?? null
    });
  }

  verify(content: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`${API_URL}/ai/verify/`, { content });
  }

  reformulate(text: string, style = 'academic'): Observable<{result: string}> {
    return this.http.post<{result: string}>(`${API_URL}/ai/reformulate/`, { text, style });
  }

  summarize(text: string): Observable<{summary: string}> {
    return this.http.post<{summary: string}>(`${API_URL}/ai/summarize/`, { text });
  }

  translate(text: string, target_lang = 'en'): Observable<{translation: string}> {
    return this.http.post<{translation: string}>(`${API_URL}/ai/translate/`, { text, target_lang });
  }
}
