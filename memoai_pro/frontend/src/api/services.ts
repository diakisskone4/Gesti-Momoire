import { request } from './client';
import type {
  AdminStats, AdminUser, AiTask, AppNotification, AuthResponse, Chapter, Collaborator, Comment, MemoirTemplate, Project,
  ProjectInput, Reference, RegisterPayload, ShareLink, TemplatePurchase, User,
} from '../lib/models';
import type { RoleCode } from '../lib/roles';

export type Scope = 'mine' | 'supervised' | 'jury';

export const authApi = {
  login: (email: string, password: string, role?: RoleCode) =>
    request<AuthResponse>('/users/login/', { method: 'POST', body: { email, password, role } }),
  register: (payload: RegisterPayload) =>
    request<AuthResponse>('/users/register/', { method: 'POST', body: payload }),
  logout: (refresh: string) => request('/users/logout/', { method: 'POST', body: { refresh } }),
  profile: () => request<User>('/users/profile/'),
  updateProfile: (data: Partial<User>) => request<User>('/users/profile/', { method: 'PUT', body: data }),
  changePassword: (old_password: string, new_password: string) =>
    request<{ status: string; access?: string; refresh?: string }>(
      '/users/change-password/', { method: 'POST', body: { old_password, new_password } },
    ),
  /** Mot de passe oublié : envoie un lien de réinitialisation à l'adresse email du compte. */
  requestPasswordReset: (email: string) =>
    request<{ message: string }>('/users/password-reset/', { method: 'POST', body: { email } }),
  confirmPasswordReset: (uid: string, token: string, new_password: string) =>
    request<{ message: string; role: string }>('/users/password-reset/confirm/', {
      method: 'POST', body: { uid, token, new_password },
    }),
  directory: (role: string, search = '') => request<User[]>('/users/directory/', { params: { role, search } }),
};

export const projectsApi = {
  list: (scope?: Scope, archived = false) =>
    request<Project[]>('/projects/projects/', { params: { scope, archived: archived ? 1 : undefined } }),
  get: (id: number) => request<Project>(`/projects/projects/${id}/`),
  create: (data: ProjectInput) => request<Project>('/projects/projects/', { method: 'POST', body: data }),
  update: (id: number, data: ProjectInput) => request<Project>(`/projects/projects/${id}/`, { method: 'PATCH', body: data }),
  remove: (id: number) => request(`/projects/projects/${id}/`, { method: 'DELETE' }),
  submitReview: (id: number) => request<Project>(`/projects/projects/${id}/submit_review/`, { method: 'POST', body: {} }),
  review: (id: number, decision: 'approve' | 'request_changes', comment = '') =>
    request<Project>(`/projects/projects/${id}/review/`, { method: 'POST', body: { decision, comment } }),
  archive: (id: number) => request<Project>(`/projects/projects/${id}/archive/`, { method: 'POST', body: {} }),
  restore: (id: number) => request<Project>(`/projects/projects/${id}/restore/`, { method: 'POST', body: {} }),
  export: (id: number, format: string, include_chapters: boolean, include_bibliography: boolean) =>
    request<Response>(`/projects/projects/${id}/export/`, {
      method: 'POST', body: { format, include_chapters, include_bibliography }, raw: true,
    }),
  generatePlan: (projectId: number) =>
    request<AiTask>('/ai/generate-plan/', { method: 'POST', body: { project_id: projectId } }),
  aiTask: (taskId: number) => request<AiTask>(`/ai/task/${taskId}/`),
};

export const chaptersApi = {
  list: (projectId: number) => request<Chapter[]>('/projects/chapters/', { params: { project: projectId } }),
  create: (data: Partial<Chapter>) => request<Chapter>('/projects/chapters/', { method: 'POST', body: data }),
  update: (id: number, data: Partial<Chapter>) => request<Chapter>(`/projects/chapters/${id}/`, { method: 'PATCH', body: data }),
  remove: (id: number) => request(`/projects/chapters/${id}/`, { method: 'DELETE' }),
  /** Rédaction par l'IA d'un chapitre (intro + sections vides), du résumé ou des sigles. */
  generateContent: (id: number) =>
    request<{ written: number; chapters: Chapter[] }>(`/projects/chapters/${id}/generate_content/`, { method: 'POST', body: {} }),
};

export interface UploadedImage { id: number; width: number; height: number; size: number; marker: string }

/** Figures des mémoires : le texte d'un chapitre les référence par une ligne « [Figure:ID | légende] ». */
export const imagesApi = {
  upload: (project: number, data: string, caption: string) =>
    request<UploadedImage>('/projects/images/', { method: 'POST', body: { project, data, caption } }),
  file: (id: number) => request<Response>(`/projects/images/${id}/`, { raw: true }),
  remove: (id: number) => request(`/projects/images/${id}/`, { method: 'DELETE' }),
};

export type TrashKind = 'project' | 'chapter' | 'reference';
export interface TrashItem {
  kind: TrashKind; id: number; title: string; details: string;
  project_id: number; project_title: string; deleted_at: string; purge_at: string;
}

/** Corbeille : éléments supprimés, restaurables pendant `retention_days` jours. */
export const trashApi = {
  list: () => request<{ retention_days: number; items: TrashItem[] }>('/projects/trash/'),
  restore: (kind: TrashKind, id: number) =>
    request<{ status: string; title: string }>('/projects/trash/restore/', { method: 'POST', body: { kind, id } }),
  remove: (kind: TrashKind, id: number) => request('/projects/trash/delete/', { method: 'POST', body: { kind, id } }),
  empty: () => request('/projects/trash/empty/', { method: 'POST', body: {} }),
};

export const referencesApi = {
  list: (projectId: number) => request<Reference[]>('/projects/references/', { params: { project_id: projectId } }),
  create: (data: Partial<Reference>) => request<Reference>('/projects/references/', { method: 'POST', body: data }),
  update: (id: number, data: Partial<Reference>) =>
    request<Reference>(`/projects/references/${id}/`, { method: 'PATCH', body: data }),
  remove: (id: number) => request(`/projects/references/${id}/`, { method: 'DELETE' }),
  importByDoi: (doi: string, projectId: number) =>
    request<Reference>('/projects/references/import_by_doi/', { method: 'POST', body: { doi, project_id: projectId } }),
  bibtex: (id: number) => request<{ bibtex: string }>(`/projects/references/${id}/bibtex/`),
};

export const collaborationApi = {
  collaborators: (projectId: number) => request<Collaborator[]>('/projects/collaborators/', { params: { project: projectId } }),
  addCollaborator: (projectId: number, email: string, role: 'viewer' | 'editor') =>
    request<Collaborator>('/projects/collaborators/', { method: 'POST', body: { project: projectId, email, role } }),
  updateCollaborator: (id: number, role: 'viewer' | 'editor') =>
    request<Collaborator>(`/projects/collaborators/${id}/`, { method: 'PATCH', body: { role } }),
  removeCollaborator: (id: number) => request(`/projects/collaborators/${id}/`, { method: 'DELETE' }),
  shareLinks: (projectId: number) => request<ShareLink[]>('/projects/share-links/', { params: { project: projectId } }),
  createShareLink: (projectId: number, permissions: { can_comment: boolean; can_export: boolean }) =>
    request<ShareLink>('/projects/share-links/', { method: 'POST', body: { project: projectId, permissions } }),
  deleteShareLink: (token: string) => request(`/projects/share-links/${token}/`, { method: 'DELETE' }),
  revokeAll: (projectId: number) => request('/projects/share-links/revoke_all/', { method: 'POST', body: { project: projectId } }),
  comments: (projectId: number) => request<Comment[]>('/projects/comments/', { params: { project_id: projectId } }),
  addComment: (data: { project?: number; chapter?: number; parent?: number; content: string }) =>
    request<Comment>('/projects/comments/', { method: 'POST', body: data }),
  resolveComment: (id: number, resolved: boolean) =>
    request(`/projects/comments/${id}/${resolved ? 'resolve' : 'unresolve'}/`, { method: 'POST', body: {} }),
};

export const notificationsApi = {
  list: () => request<AppNotification[]>('/notifications/'),
  unreadCount: () => request<{ count: number }>('/notifications/unread_count/'),
  markRead: (id: number) => request<AppNotification>(`/notifications/${id}/mark_read/`, { method: 'POST', body: {} }),
  markAllRead: () => request('/notifications/mark_all_read/', { method: 'POST', body: {} }),
  remove: (id: number) => request(`/notifications/${id}/`, { method: 'DELETE' }),
};

export const aiApi = {
  chat: (message: string, projectId?: number | null) =>
    request<{ response: string }>('/ai/chat/', { method: 'POST', body: { message, project_id: projectId ?? null } }),
  reformulate: (text: string, style = 'academic') =>
    request<{ result: string }>('/ai/reformulate/', { method: 'POST', body: { text, style } }),
  summarize: (text: string) => request<{ summary: string }>('/ai/summarize/', { method: 'POST', body: { text } }),
  translate: (text: string, target_lang = 'en') =>
    request<{ translation: string }>('/ai/translate/', { method: 'POST', body: { text, target_lang } }),
  verify: (content: string) => request<VerifyResult>('/ai/verify/', { method: 'POST', body: { content } }),
};

export interface VerifyResult {
  score: number;
  summary: string;
  issues: { type: string; excerpt: string; explanation: string; suggestion: string }[];
}

export const adminApi = {
  stats: () => request<AdminStats>('/users/admin/stats/'),
  users: (filters: { role?: string; search?: string }) => request<AdminUser[]>('/users/admin/users/', { params: filters }),
  updateUser: (id: number, data: Partial<AdminUser>) =>
    request<AdminUser>(`/users/admin/users/${id}/`, { method: 'PATCH', body: data }),
  deleteUser: (id: number) => request(`/users/admin/users/${id}/`, { method: 'DELETE' }),
};

export const modelesApi = {
  list: () => request<MemoirTemplate[]>('/modeles/'),
  get: (slug: string) => request<MemoirTemplate>(`/modeles/${slug}/`),
  cover: (slug: string) => request<{ html: string }>(`/modeles/${slug}/cover/`),
  purchase: (slug: string) => request<TemplatePurchase>(`/modeles/${slug}/purchase/`, { method: 'POST', body: {} }),
  apply: (slug: string, projectId: number) =>
    request<{ project_id: number; chapters_created: number }>(`/modeles/${slug}/apply/`, { method: 'POST', body: { project_id: projectId } }),
  purchases: () => request<TemplatePurchase[]>('/modeles/achats/'),
  verify: (purchaseId: number) => request<TemplatePurchase>(`/modeles/achats/${purchaseId}/verify/`, { method: 'POST', body: {} }),
  projectCover: (projectId: number) => request<{ html: string }>(`/modeles/projects/${projectId}/cover/`),
};
