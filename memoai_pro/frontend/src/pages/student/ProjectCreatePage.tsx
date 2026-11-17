import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { describeError } from '../../api/client';
import { authApi, modelesApi, projectsApi } from '../../api/services';
import Layout from '../../components/Layout';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import type { Level, MemoirTemplate, User } from '../../lib/models';
import '../../styles/project-create.css';

interface Form {
  title: string; theme: string; level: Level; university: string; faculty: string; department: string;
  field_of_study: string; option: string; academic_year: string; country: string; city: string;
  language: string; desired_pages: number;
}

function currentAcademicYear(): string {
  const now = new Date();
  const start = now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
  return `${start}-${start + 1}`;
}

const personLabel = (u: User, extra?: string) =>
  [u.academic_title, u.full_name].filter(Boolean).join(' ') + (extra ? ` · ${extra}` : '');

export default function ProjectCreatePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [f, setF] = useState<Form>(() => ({
    title: '', theme: '', level: (user?.level || 'MASTER') as Level,
    university: user?.university ?? '', faculty: user?.faculty ?? '', department: user?.department ?? '',
    field_of_study: '', option: '', academic_year: currentAcademicYear(),
    country: 'Mali', city: 'Bamako', language: 'fr', desired_pages: 50,
  }));
  const [supervisors, setSupervisors] = useState<User[]>([]);
  const [coSupervisors, setCoSupervisors] = useState<User[]>([]);
  const [juryMembers, setJuryMembers] = useState<User[]>([]);
  const [supervisorId, setSupervisorId] = useState<number | null>(null);
  const [coSupervisorId, setCoSupervisorId] = useState<number | null>(null);
  const [juryIds, setJuryIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchParams] = useSearchParams();
  const [ownedTemplates, setOwnedTemplates] = useState<MemoirTemplate[]>([]);
  const [templateSlug, setTemplateSlug] = useState(searchParams.get('modele') ?? '');

  useEffect(() => {
    authApi.directory('SUPERVISOR').then(setSupervisors).catch(() => undefined);
    authApi.directory('SUPERVISOR,CO_SUPERVISOR').then(setCoSupervisors).catch(() => undefined);
    authApi.directory('JURY').then(setJuryMembers).catch(() => undefined);
    modelesApi.list().then(list => {
      const owned = list.filter(t => t.owned);
      setOwnedTemplates(owned);
      setTemplateSlug(slug => (owned.some(t => t.slug === slug) ? slug : ''));
      const preset = owned.find(t => t.slug === searchParams.get('modele'));
      if (preset?.level) setF(prev => ({ ...prev, level: preset.level as Level }));
    }).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const bind = (key: keyof Form) => ({
    name: key,
    value: f[key],
    onChange: (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setF(prev => ({ ...prev, [key]: key === 'desired_pages' ? Number(e.target.value) : e.target.value })),
  });

  const toggleJury = (id: number) => setJuryIds(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setError('');
    setLoading(true);
    try {
      const project = await projectsApi.create({
        ...f, supervisor: supervisorId, co_supervisor: coSupervisorId, jury: [...juryIds],
      });
      if (templateSlug) {
        try {
          await modelesApi.apply(templateSlug, project.id);
          toast.success('Mémoire créé', 'Le plan et la page de garde du modèle ont été ajoutés.');
        } catch (err) {
          toast.warning('Mémoire créé sans le modèle', describeError(err));
        }
      } else {
        toast.success('Mémoire créé', "Générez maintenant son plan avec l'IA ou appliquez un modèle.");
      }
      navigate(`/projects/${project.id}/editor`);
    } catch (err) {
      setLoading(false);
      setError(describeError(err, 'Impossible de créer le mémoire. Vérifiez les informations saisies.'));
    }
  };

  return (
    <Layout>
      <div className="scope-create">
        <div className="head">
          <Link className="back-link" to="/projects">← Mes mémoires</Link>
          <span className="eyebrow">NOUVEAU PROJET</span>
          <h2>Créer votre mémoire</h2>
          <p>Renseignez les informations essentielles. Vous pourrez les modifier plus tard.</p>
        </div>

        <form className="form" onSubmit={submit}>
          <section className="form-section">
            <div className="section-title">
              <div className="section-number">01</div>
              <div><h3>Informations générales</h3><p>Présentez les informations principales de votre mémoire.</p></div>
            </div>
            <div className="grid">
              <label>Titre du mémoire <span className="required">*</span>
                <input type="text" {...bind('title')} required maxLength={255} placeholder="Ex. Impact de l'IA sur l'éducation" />
              </label>
              <label>Niveau <span className="required">*</span>
                <select {...bind('level')} required>
                  <option value="LICENCE">Licence</option>
                  <option value="MASTER">Master</option>
                  <option value="DOCTORAT">Doctorat</option>
                </select>
              </label>
            </div>
            <label>Thème / problématique <span className="required">*</span>
              <textarea {...bind('theme')} rows={5} required maxLength={255}
                        placeholder="Décrivez votre sujet et votre problématique (l'IA s'en sert pour générer le plan)..." />
            </label>
          </section>

          <section className="form-section">
            <div className="section-title">
              <div className="section-number">02</div>
              <div><h3>Parcours académique</h3><p>Indiquez votre établissement et votre domaine d'étude.</p></div>
            </div>
            <div className="grid">
              <label>Université <span className="required">*</span>
                <input type="text" {...bind('university')} required placeholder="Ex. Université de Bamako" />
              </label>
              <label>Faculté <span className="required">*</span>
                <input type="text" {...bind('faculty')} required placeholder="Ex. Faculté des Sciences" />
              </label>
              <label>Département <span className="required">*</span>
                <input type="text" {...bind('department')} required placeholder="Ex. Informatique" />
              </label>
              <label>Domaine d'étude <span className="required">*</span>
                <input type="text" {...bind('field_of_study')} required placeholder="Ex. Génie logiciel" />
              </label>
              <label>Option
                <input type="text" {...bind('option')} placeholder="Ex. Intelligence artificielle" />
              </label>
              <label>Année académique <span className="required">*</span>
                <input type="text" {...bind('academic_year')} required placeholder="2026-2027" pattern="\d{4}-\d{4}" />
              </label>
            </div>
          </section>

          <section className="form-section">
            <div className="section-title">
              <div className="section-number">03</div>
              <div><h3>Paramètres du mémoire</h3><p>Configurez les paramètres de génération de votre mémoire.</p></div>
            </div>
            <div className="grid">
              <label>Pays <span className="required">*</span><input type="text" {...bind('country')} required /></label>
              <label>Ville <span className="required">*</span><input type="text" {...bind('city')} required /></label>
              <label>Pages souhaitées
                <input type="number" {...bind('desired_pages')} min={10} max={500} />
                <small>Minimum recommandé : 10 pages</small>
              </label>
              <label>Langue
                <select {...bind('language')}>
                  <option value="fr">Français</option>
                  <option value="en">English</option>
                </select>
              </label>
            </div>
          </section>

          <section className="form-section">
            <div className="section-title">
              <div className="section-number">✦</div>
              <div>
                <h3>Modèle de mémoire (facultatif)</h3>
                <p>Un modèle ajoute un plan commenté et une page de garde aux normes, incluse dans vos exports.</p>
              </div>
            </div>
            {ownedTemplates.length > 0 ? (
              <label>Modèle
                <select value={templateSlug} onChange={e => setTemplateSlug(e.target.value)}>
                  <option value="">— Sans modèle (plan généré par l'IA) —</option>
                  {ownedTemplates.map(t => <option key={t.slug} value={t.slug}>{t.name}</option>)}
                </select>
              </label>
            ) : (
              <p className="hint">Vous n'avez pas encore de modèle. <Link to="/modeles">Découvrir les modèles →</Link></p>
            )}
          </section>

          <section className="form-section">
            <div className="section-title">
              <div className="section-number">04</div>
              <div>
                <h3>Encadrement et jury</h3>
                <p>Choisissez les enseignants inscrits sur MemoAI Pro qui suivront votre mémoire. Vous pourrez les modifier plus tard.</p>
              </div>
            </div>
            <div className="grid">
              <label>Encadreur
                <select value={supervisorId ?? ''} onChange={e => setSupervisorId(e.target.value ? Number(e.target.value) : null)}>
                  <option value="">— Aucun pour l'instant —</option>
                  {supervisors.map(u => <option key={u.id} value={u.id}>{personLabel(u, u.university)}</option>)}
                </select>
              </label>
              <label>Co-encadreur
                <select value={coSupervisorId ?? ''} onChange={e => setCoSupervisorId(e.target.value ? Number(e.target.value) : null)}>
                  <option value="">— Aucun —</option>
                  {coSupervisors.map(u => (
                    <option key={u.id} value={u.id} disabled={u.id === supervisorId}>{personLabel(u, u.university)}</option>
                  ))}
                </select>
              </label>
            </div>

            {juryMembers.length > 0 && (
              <fieldset className="jury-list">
                <legend>Membres du jury</legend>
                {juryMembers.map(u => (
                  <label className="check" key={u.id}>
                    <input type="checkbox" checked={juryIds.has(u.id)} onChange={() => toggleJury(u.id)} />
                    {personLabel(u, u.speciality)}
                  </label>
                ))}
              </fieldset>
            )}

            {!supervisors.length && !coSupervisors.length && (
              <p className="hint">
                Aucun encadreur n'est encore inscrit. Demandez au vôtre de créer son compte encadreur sur MemoAI Pro.
              </p>
            )}
          </section>

          {error && (
            <div className="error" role="alert"><span className="error-icon">!</span><span>{error}</span></div>
          )}

          <div className="actions">
            <Link to="/projects" className="cancel">Annuler</Link>
            <button type="submit" className="primary" disabled={loading}>
              {loading ? 'Création en cours...' : 'Créer le mémoire →'}
            </button>
          </div>
        </form>
      </div>
    </Layout>
  );
}
