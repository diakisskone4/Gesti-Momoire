// Les 5 acteurs du système (cahier des charges §2).

export type RoleCode = 'STUDENT' | 'SUPERVISOR' | 'CO_SUPERVISOR' | 'JURY' | 'ADMIN';

export interface RoleDef {
  code: RoleCode;
  /** Segment d'URL de l'espace : /encadreur/login, /jury/register... */
  slug: string;
  label: string;
  icon: string;
  description: string;
  /** Page d'accueil après connexion. */
  home: string;
}

export const ROLES: RoleDef[] = [
  {
    code: 'STUDENT', slug: 'etudiant', label: 'Étudiant', icon: '🎓', home: '/dashboard',
    description: "Rédigez votre mémoire avec l'IA, gérez votre bibliographie et exportez le document final.",
  },
  {
    code: 'SUPERVISOR', slug: 'encadreur', label: 'Encadreur', icon: '🧑‍🏫', home: '/supervision',
    description: "Suivez l'avancement de vos étudiants, commentez et validez leurs mémoires.",
  },
  {
    code: 'CO_SUPERVISOR', slug: 'co-encadreur', label: 'Co-encadreur', icon: '🤝', home: '/supervision',
    description: "Co-supervisez un mémoire avec les mêmes droits que l'encadreur.",
  },
  {
    code: 'JURY', slug: 'jury', label: 'Jury', icon: '⚖️', home: '/jury',
    description: 'Consultez les mémoires finalisés, commentez et validez en phase de soutenance.',
  },
  {
    code: 'ADMIN', slug: 'admin', label: 'Administrateur', icon: '🛡️', home: '/admin',
    description: "Gérez les utilisateurs, les rôles et supervisez l'activité de la plateforme.",
  },
];

/** Rôles qui ont chacun leur propre espace de connexion (hors étudiant). */
export const STAFF_ROLES = ROLES.filter(r => r.code !== 'STUDENT');
export const REVIEWER_ROLES: RoleCode[] = ['SUPERVISOR', 'CO_SUPERVISOR', 'JURY'];

/** Chaque rôle a son propre espace, sans lien vers les autres :
 *  étudiant /login, encadreur /encadreur/login, co-encadreur /co-encadreur/login, jury /jury/login, admin /admin/login. */
export const loginPath = (role: RoleDef) => (role.code === 'STUDENT' ? '/login' : `/${role.slug}/login`);
export const registerPath = (role: RoleDef) => (role.code === 'STUDENT' ? '/register' : `/${role.slug}/register`);
export const forgotPath = (role: RoleDef) =>
  (role.code === 'STUDENT' ? '/mot-de-passe-oublie' : `/${role.slug}/mot-de-passe-oublie`);
export const roleBySlug = (slug?: string | null) => ROLES.find(r => r.slug === slug);
export const roleByCode = (code?: string | null) => ROLES.find(r => r.code === code);
export const homeFor = (code?: string | null) => roleByCode(code)?.home ?? '/login';
/** Page de connexion de l'espace d'un rôle (étudiant par défaut). */
export const loginPathFor = (code?: string | null) => loginPath(roleByCode(code) ?? ROLES[0]);

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Brouillon',
  IN_PROGRESS: 'En cours de rédaction',
  REVIEW: 'En relecture',
  VALIDATED: 'Validé',
  ARCHIVED: 'Archivé',
  COMPLETED: 'Terminé',
};

export const LEVEL_LABELS: Record<string, string> = { LICENCE: 'Licence', MASTER: 'Master', DOCTORAT: 'Doctorat' };

export const ACADEMIC_TITLES = [
  'Professeur', 'Maître de conférences', 'Docteur', 'Maître-assistant', 'Assistant', 'Chercheur', 'Professionnel',
];
