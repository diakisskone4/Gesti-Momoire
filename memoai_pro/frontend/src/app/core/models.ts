// ============================================================
// UTILISATEUR
// ============================================================

export interface User {
  id?: number;
  email: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  role?: string;
  language?: string;
  username?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}


// ============================================================
// AUTHENTIFICATION
// ============================================================

export interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
}


// ============================================================
// PROJET / MÉMOIRE
// ============================================================

export interface Project {
  id?: number;
  user?: number;
  folder?: number | null;
  title: string;
  theme?: string;
  level?: 'LICENCE' | 'MASTER' | 'DOCTORAT';
  university?: string;
  faculty?: string;
  department?: string;
  field_of_study?: string;
  option?: string;
  laboratory?: string;
  country?: string;
  city?: string;
  academic_year?: string;
  language?: string;
  desired_pages?: number;
  status?: string;
  is_favorite?: boolean;
  tags?: string;
  created_at?: string;
  updated_at?: string;
  archived_at?: string | null;
  export_allowed?: boolean;
  chapters?: Chapter[];
}


// ============================================================
// CHAPITRE
// ============================================================

export interface Chapter {
  id?: number;
  project: number;
  parent?: number | null;
  order: number;
  title: string;
  content: string;
  type: string;
  status: 'draft' | 'review' | 'validated';
  version: number;
  created_at?: string;
  updated_at?: string;
  children?: Chapter[];
}


// ============================================================
// DOSSIER
// ============================================================

export interface Folder {
  id?: number;
  name: string;
  parent?: number | null;
  created_at?: string;
}


// ============================================================
// RÉFÉRENCE BIBLIOGRAPHIQUE
// ============================================================

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
}