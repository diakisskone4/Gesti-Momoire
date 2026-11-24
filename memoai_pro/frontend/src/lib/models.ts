import type { RoleCode } from './roles';

export type Level = 'LICENCE' | 'MASTER' | 'DOCTORAT';
export type ProjectStatus = 'DRAFT' | 'IN_PROGRESS' | 'REVIEW' | 'VALIDATED' | 'ARCHIVED' | 'COMPLETED';

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone?: string;
  photo?: string | null;
  role: RoleCode;
  language?: string;
  university?: string;
  faculty?: string;
  department?: string;
  student_number?: string;
  level?: '' | Level;
  academic_title?: string;
  speciality?: string;
  email_verified?: boolean;
  two_factor_enabled?: boolean;
  created_at?: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface RegisterPayload {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  password: string;
  password2: string;
  role: RoleCode;
  language: string;
  university: string;
  faculty: string;
  department: string;
  student_number: string;
  level: '' | Level;
  academic_title: string;
  speciality: string;
  admin_code: string;
}

export interface Chapter {
  id: number;
  project: number;
  parent: number | null;
  order: number;
  title: string;
  content: string | null;
  type: string;
  status: 'draft' | 'review' | 'validated';
  version: number;
  created_at?: string;
  updated_at?: string;
  children?: Chapter[];
}

export interface Project {
  id: number;
  user: number;
  folder?: number | null;
  title: string;
  theme?: string | null;
  level: Level;
  university?: string | null;
  faculty?: string | null;
  department?: string | null;
  field_of_study?: string | null;
  option?: string | null;
  laboratory?: string | null;
  country?: string | null;
  city?: string | null;
  academic_year?: string | null;
  language?: string;
  desired_pages?: number;
  status: ProjectStatus;
  status_label?: string;
  is_favorite?: boolean;
  tags?: string | null;
  created_at: string;
  updated_at: string;
  archived_at?: string | null;
  submitted_at?: string | null;
  validated_at?: string | null;
  review_comment?: string;
  export_allowed?: boolean;
  chapters: Chapter[];
  supervisor: number | null;
  co_supervisor: number | null;
  jury: number[];
  owner?: User;
  supervisor_detail?: User | null;
  co_supervisor_detail?: User | null;
  jury_detail?: User[];
  my_role?: 'OWNER' | 'SUPERVISOR' | 'CO_SUPERVISOR' | 'JURY' | 'ADMIN' | null;
  template?: number | null;
  template_detail?: { slug: string; name: string; cover_style: string; paid?: boolean } | null;
}

export type ProjectInput = Partial<Omit<Project, 'id' | 'chapters' | 'owner'>>;

export interface Reference {
  id: number;
  project: number;
  title: string;
  authors: string;
  year: number;
  journal?: string | null;
  doi?: string | null;
  isbn?: string | null;
  bibtex?: string | null;
  style?: string;
  created_at?: string;
}

export interface Collaborator {
  id: number;
  project: number;
  user: number;
  user_email: string;
  user_name: string;
  role: 'viewer' | 'editor' | 'owner';
  status: 'pending' | 'active' | 'revoked';
  can_edit: boolean;
  can_comment: boolean;
  can_export: boolean;
  can_share: boolean;
  invited_at: string;
}

export interface ShareLink {
  token: string;
  project: number;
  can_edit: boolean;
  can_comment: boolean;
  can_export: boolean;
  expires_at: string | null;
  created_at: string;
  url: string;
}

export interface Comment {
  id: number;
  user: Pick<User, 'id' | 'email' | 'full_name' | 'role'>;
  project: number | null;
  chapter: number | null;
  parent: number | null;
  content: string;
  resolved: boolean;
  replies: Comment[];
  created_at: string;
}

export interface AppNotification {
  id: number;
  actor_name: string | null;
  verb: string;
  target_type: string;
  target_id: number;
  description: string;
  read: boolean;
  created_at: string;
}

export interface AiTask {
  ai_task_id: number;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  error: string | null;
}

export interface AdminUser extends User {
  is_active: boolean;
  projects_count: number;
}

export interface AdminStats {
  users_total: number;
  users_active: number;
  users_by_role: Record<string, number>;
  projects_total: number;
  projects_by_status: Record<string, number>;
  payments_total: number;
  payments_succeeded: number;
  revenue: number;
  conversion_rate: number;
  ai_tasks_total: number;
  templates_sold: number;
  templates_revenue: number;
}

export interface TemplateOutlineItem { title: string; type: string; sections: string[]; }
export interface TemplateStructureItem {
  title: string; type: string; guidance: string; sections: { title: string; guidance: string }[];
}

export interface MemoirTemplate {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  level: '' | Level;
  level_label: string;
  domain: string;
  cover_style: string;
  cover_label: string;
  accent_color: string;
  price: string;
  currency: string;
  /** Modèle à 0 FCFA, disponible pour tous sans paiement. */
  is_free?: boolean;
  owned: boolean;
  outline: TemplateOutlineItem[];
  structure: TemplateStructureItem[] | null;
}

export type OperatorCode = 'orange' | 'moov' | 'wave';

export interface TemplatePurchase {
  id: number;
  template_slug: string;
  template_name: string;
  status: 'PENDING' | 'SUBMITTED' | 'PAID' | 'FAILED' | 'CANCELLED';
  provider: 'mobile_money' | 'jemeni' | 'jemeni_test' | 'saspay';
  operator: OperatorCode | '';
  payer_phone: string;
  submitted_at: string | null;
  review_note: string;
  amount: string;
  currency: string;
  amount_charged: string | null;
  checkout_url: string;
  transaction_reference: string;
  created_at: string;
  paid_at: string | null;
}

/** Moyens de paiement : mobile money direct (numéro d'encaissement) ou page Jɛmɛnipay. */
export interface PaymentOptions {
  mode: 'mobile_money' | 'jemeni';
  holder?: string;
  operators?: { code: OperatorCode; label: string; ussd: string; steps: string; number: string; number_display: string }[];
}

export interface PaymentMessage {
  id: number;
  operator: OperatorCode;
  text: string;
  amount: string | null;
  received_at: string;
  purchase: number | null;
}

export interface AdminPayment extends TemplatePurchase {
  buyer_name: string;
  buyer_email: string;
  suggestions: PaymentMessage[];
  automatic: boolean;
}

export interface PaymentDevice {
  id: number;
  name: string;
  is_active: boolean;
  last_seen_at: string | null;
  created_at: string;
}
