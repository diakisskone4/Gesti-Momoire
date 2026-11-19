"""Appels IA pour les fonctions du cahier des charges (§3.5, §3.7).

Fournisseur choisi par AI_PROVIDER : "openrouter" (API compatible OpenAI) ou "anthropic" (API Claude)."""
import json
import logging
import re
import time
from functools import lru_cache

import anthropic
import openai
from django.conf import settings
from django.core.cache import cache

from projects.models import Project

logger = logging.getLogger(__name__)

# Modèles qui acceptent le repli automatique côté serveur en cas de refus.
FALLBACK_MODELS = {'claude-opus-5-5', 'claude-opus-5', 'claude-fable-5-1', 'claude-sonnet-5-5'}

ACADEMIC_SYSTEM = (
    "Vous êtes l'assistant académique de MemoAI Pro. Vous aidez des étudiants à rédiger "
    "leur mémoire ou leur thèse universitaire. Répondez en français sauf demande contraire, "
    "dans un registre académique clair. N'inventez jamais de références : si vous citez un "
    "ouvrage ou un article, signalez qu'il doit être vérifié par l'étudiant.\n\n"
    "Présentation : rédigez en texte brut, en paragraphes soignés, sans aucune mise en forme "
    "Markdown (pas d'astérisques, de dièses, de tirets de liste ni de texte en gras ou en italique). "
    "Pour une énumération, utilisez une liste numérotée simple (1., 2., 3.) ou des phrases, "
    "sauf si la demande impose explicitement un autre format."
)


# Mise en forme Markdown que les modèles ajoutent malgré la consigne : retirée avant affichage.
_MD_FENCE = re.compile(r'^\s*```.*$', re.MULTILINE)
_MD_HEADING = re.compile(r'^\s{0,3}#{1,6}\s+', re.MULTILINE)
_MD_RULE = re.compile(r'^\s*([-*_])(\s*\1){2,}\s*$', re.MULTILINE)
_MD_QUOTE = re.compile(r'^\s*>\s?', re.MULTILINE)
_MD_BULLET = re.compile(r'^(\s*)[-*+•]\s+', re.MULTILINE)
_MD_BOLD = re.compile(r'(\*\*|__)(?=\S)(.+?)(?<=\S)\1', re.DOTALL)
_MD_ITALIC_STAR = re.compile(r'(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])')
_MD_ITALIC_UNDERSCORE = re.compile(r'(?<![\w_])_(?=\S)([^_\n]+?)(?<=\S)_(?![\w_])')
_MD_CODE = re.compile(r'`([^`\n]+)`')
_MD_LINK = re.compile(r'\[([^\]\n]+)\]\((https?://[^)\s]+)\)')


def clean_ai_text(text):
    """Texte professionnel sans symboles Markdown : « **Plan** : … » → « Plan : … »,
    « - item » → « • item », titres « ## … » → simple ligne. Les mentions entre crochets
    ([source à compléter]) et les listes numérotées (1., 2.) sont conservées."""
    if not text:
        return text
    text = _MD_FENCE.sub('', text)
    text = _MD_RULE.sub('', text)
    text = _MD_HEADING.sub('', text)
    text = _MD_QUOTE.sub('', text)
    text = _MD_BULLET.sub(lambda m: m.group(1) + '• ', text)
    text = _MD_LINK.sub(r'\1 (\2)', text)
    for _ in range(2):  # gras imbriqué dans de l'italique, ou l'inverse
        text = _MD_BOLD.sub(r'\2', text)
        text = _MD_ITALIC_STAR.sub(r'\1', text)
        text = _MD_ITALIC_UNDERSCORE.sub(r'\1', text)
    text = _MD_CODE.sub(r'\1', text)
    text = text.replace('**', '')
    text = re.sub(r'[ \t]+\n', '\n', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _clean_strings(value):
    """Nettoie récursivement les textes d'une réponse JSON (plan, relecture)."""
    if isinstance(value, str):
        return clean_ai_text(value)
    if isinstance(value, list):
        return [_clean_strings(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean_strings(v) for k, v in value.items()}
    return value


class AIError(Exception):
    """Erreur IA à présenter telle quelle à l'utilisateur."""

    def __init__(self, message, status=502, retry_after=None):
        super().__init__(message)
        self.status = status
        # Délai conseillé (secondes) avant de réessayer, renvoyé dans l'en-tête Retry-After.
        self.retry_after = retry_after


def translate_openrouter_error(e):
    """Convertit une erreur OpenRouter en AIError présentable à l'utilisateur."""
    if isinstance(e, openai.APIStatusError):
        if e.status_code == 402:
            return AIError("Le service IA est temporairement indisponible (crédit OpenRouter épuisé). Contactez l'administrateur.", 503)
        if e.status_code in (401, 403):
            return AIError("Le service IA est mal configuré (clé API invalide). Contactez l'administrateur.", 503)
        if e.status_code == 429:
            return AIError('Trop de requêtes IA en peu de temps. Réessayez dans un instant.', 429)
        if e.status_code >= 500:
            return AIError('Le service IA est surchargé. Réessayez dans quelques instants.', 503)
        return AIError('La requête IA a été rejetée. Réessayez avec un texte plus court.', 502)
    if isinstance(e, openai.APIConnectionError):
        return AIError('Le service IA est injoignable. Réessayez plus tard.', 502)
    return AIError("Erreur inattendue du service IA.", 502)


def translate_api_error(e):
    """Convertit une erreur de l'API Claude en AIError présentable à l'utilisateur."""
    if isinstance(e, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return AIError("Le service IA est mal configuré (clé API invalide). Contactez l'administrateur.", 503)
    if isinstance(e, anthropic.RateLimitError):
        return AIError('Trop de requêtes IA en peu de temps. Réessayez dans un instant.', 429)
    if isinstance(e, anthropic.APIStatusError):
        # Un solde insuffisant arrive en 402 (billing_error) ou en 400 dont seul
        # le message mentionne le crédit : on vérifie les deux.
        if e.status_code == 402 or e.type == 'billing_error' or 'credit balance' in str(e.message).lower():
            return AIError("Le service IA est temporairement indisponible (crédit API épuisé). Contactez l'administrateur.", 503)
        if e.status_code >= 500:
            return AIError('Le service IA est surchargé. Réessayez dans quelques instants.', 503)
        return AIError('La requête IA a été rejetée. Réessayez avec un texte plus court.', 502)
    if isinstance(e, anthropic.APIConnectionError):
        return AIError('Le service IA est injoignable. Réessayez plus tard.', 502)
    return AIError("Erreur inattendue du service IA.", 502)


@lru_cache(maxsize=1)
def _client():
    if not settings.ANTHROPIC_API_KEY:
        raise AIError("Le service IA n'est pas configuré (ANTHROPIC_API_KEY manquante).", 503)
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


@lru_cache(maxsize=1)
def _openrouter_client():
    if not settings.OPENAI_API_KEY:
        raise AIError("Le service IA n'est pas configuré (OPENAI_API_KEY manquante).", 503)
    # max_retries=1 : en cas de saturation, mieux vaut passer vite au modèle suivant
    # que d'attendre les ré-essais du SDK sur le même modèle.
    return openai.OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL, max_retries=1, timeout=120)


def _extract_json(text):
    """Isole l'objet JSON d'une réponse (le modèle peut l'entourer de texte ou de ```)."""
    start, end = text.find('{'), text.rfind('}')
    try:
        if start == -1 or end < start:
            raise ValueError('aucun objet JSON')
        json.loads(text[start:end + 1])
    except ValueError:
        logger.error('Réponse IA non JSON : %.300s', text)
        raise AIError("La réponse de l'IA est mal formée. Réessayez.", 502)
    return text[start:end + 1]


# Erreurs pour lesquelles on essaie le modèle suivant : saturation (429), panne du fournisseur (5xx),
# délai dépassé (408) ou modèle retiré du catalogue OpenRouter (404).
RETRYABLE_STATUSES = {404, 408, 429, 500, 502, 503, 504}


# Un modèle qui vient de répondre 429 est mis en pause : on ne gaspille pas le quota
# quotidien des modèles gratuits OpenRouter (50 requêtes/jour) à le réinterroger aussitôt.
MODEL_COOLDOWN_SECONDS = 90
DAILY_QUOTA_KEY = 'ai:openrouter:daily-quota-reached'
DAILY_QUOTA_MESSAGE = (
    "Le quota quotidien du service IA gratuit est atteint. Réessayez plus tard "
    "(l'administrateur peut ajouter du crédit OpenRouter pour lever cette limite)."
)


def _cooldown_key(model):
    return f'ai:openrouter:cooldown:{model}'


def _openrouter_models():
    """Modèle principal puis modèles de secours, sans doublon. Les modèles saturés
    récemment passent en dernier : ils ne sont essayés que si tous les autres échouent."""
    seen, models = set(), []
    for model in [settings.AI_MODEL, *settings.AI_FALLBACK_MODELS]:
        if model and model not in seen:
            seen.add(model)
            models.append(model)
    cooling = cache.get_many([_cooldown_key(m) for m in models])
    return sorted(models, key=lambda m: _cooldown_key(m) in cooling)


def _is_daily_quota_error(e):
    """OpenRouter signale l'épuisement du quota gratuit par un 429 « free-models-per-day »."""
    text = f'{e.message} {e.body}'.lower()
    return 'per-day' in text or 'per day' in text


def _seconds_until_reset(e, default=3600):
    """Délai avant la remise à zéro du quota (en-tête X-RateLimit-Reset, en millisecondes)."""
    try:
        reset_ms = int(e.response.headers.get('X-RateLimit-Reset'))
    except (TypeError, ValueError, AttributeError):
        return default
    return max(60, min(int(reset_ms / 1000 - time.time()), 24 * 3600))


def _ask_openrouter(prompt, system, schema, max_tokens, allow_truncated=False):
    """Interroge les modèles un par un : si l'un est saturé ou indisponible, on passe au suivant."""
    if schema:
        system += (
            "\n\nRépondez UNIQUEMENT avec un objet JSON valide, sans texte autour, "
            f"conforme à ce schéma JSON :\n{json.dumps(schema, ensure_ascii=False)}"
        )
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}]
    quota_reset_at = cache.get(DAILY_QUOTA_KEY)
    if quota_reset_at:
        raise AIError(DAILY_QUOTA_MESSAGE, 429, retry_after=max(60, int(quota_reset_at - time.time())))

    models = _openrouter_models()
    try:
        return _try_openrouter_models(models, messages, schema, max_tokens, allow_truncated)
    except _AllSaturated as first_failure:
        # Saturation passagère côté fournisseur (« retry shortly ») : une seconde chance
        # après une courte pause, sur le premier modèle saturé uniquement.
        time.sleep(settings.AI_SATURATION_RETRY_DELAY)
        try:
            return _try_openrouter_models(first_failure.models[:1], messages, schema, max_tokens, allow_truncated)
        except _AllSaturated:
            raise AIError("Les modèles IA sont saturés en ce moment (forte demande sur les modèles gratuits). "
                          "Réessayez dans une minute.", 429, retry_after=60) from None


class _AllSaturated(Exception):
    """Tous les modèles ont échoué et au moins un était saturé (429)."""

    def __init__(self, models):
        super().__init__('saturated')
        self.models = models


def _try_openrouter_models(models, messages, schema, max_tokens, allow_truncated):
    last_error = None
    saturated = []
    for model in models:
        # Les modèles gratuits ne réservent pas de crédit : on laisse de la place
        # aux modèles qui « réfléchissent » avant de répondre.
        tokens = max(max_tokens, 8000) if model.endswith(':free') else max_tokens
        try:
            response = _openrouter_client().chat.completions.create(
                model=model, messages=messages, temperature=0.4, max_tokens=tokens,
            )
        except openai.APIStatusError as e:
            if e.status_code == 429 and _is_daily_quota_error(e):
                delay = _seconds_until_reset(e)
                logger.error('OpenRouter: quota quotidien des modèles gratuits atteint (remise à zéro dans %ss).', delay)
                cache.set(DAILY_QUOTA_KEY, time.time() + delay, delay)
                raise AIError(DAILY_QUOTA_MESSAGE, 429, retry_after=delay) from e
            if e.status_code in RETRYABLE_STATUSES:
                logger.warning('OpenRouter: %s indisponible (%s), modèle suivant.', model, e.status_code)
                if e.status_code == 429:
                    saturated.append(model)
                    cache.set(_cooldown_key(model), True, MODEL_COOLDOWN_SECONDS)
                last_error = e
                continue
            logger.error('OpenRouter API error (%s): %s', model, e)
            raise translate_openrouter_error(e) from e
        except openai.APIConnectionError as e:
            logger.warning('OpenRouter: %s injoignable, modèle suivant.', model)
            last_error = e
            continue

        choice = response.choices[0] if getattr(response, 'choices', None) else None
        text = (choice.message.content or '').strip() if choice else ''
        if not text:
            # Réponse vide ou erreur du fournisseur dans une réponse 200.
            logger.warning('OpenRouter: réponse vide de %s, modèle suivant.', model)
            last_error = AIError("Le modèle IA n'a pas répondu. Réessayez dans un instant.", 502)
            continue
        if choice.finish_reason == 'length' and not allow_truncated:
            last_error = AIError("La réponse de l'IA est trop longue. Réduisez la taille du texte envoyé.", 422)
            if schema:  # JSON tronqué : inutilisable, on tente le modèle suivant
                logger.warning('OpenRouter: réponse JSON tronquée de %s, modèle suivant.', model)
                continue
            raise last_error
        if not schema:
            return text
        try:
            return _extract_json(text)
        except AIError as e:
            last_error = e
            continue

    if saturated:
        raise _AllSaturated(saturated)
    if isinstance(last_error, AIError):
        raise last_error
    raise translate_openrouter_error(last_error) if last_error else AIError("Aucun modèle IA n'est configuré.", 503)


def _ask(prompt, *, system=ACADEMIC_SYSTEM, effort=None, schema=None, openrouter_max_tokens=1500, allow_truncated=False):
    """Envoie un message au fournisseur IA configuré et renvoie le texte de la réponse.
    `openrouter_max_tokens` reste bas : OpenRouter réserve ce plafond sur le crédit à chaque appel."""
    if settings.AI_PROVIDER == 'openrouter':
        return _ask_openrouter(prompt, system, schema, openrouter_max_tokens, allow_truncated)

    model = settings.AI_MODEL
    output_config = {}
    if effort:
        output_config['effort'] = effort
    if schema:
        output_config['format'] = {'type': 'json_schema', 'schema': schema}

    kwargs = {
        'model': model,
        'max_tokens': 16000,
        'system': system,
        'messages': [{'role': 'user', 'content': prompt}],
    }
    if output_config:
        kwargs['output_config'] = output_config
    if model in FALLBACK_MODELS:
        kwargs['betas'] = ['server-side-fallback-2026-07-01']
        kwargs['fallbacks'] = 'default'

    try:
        response = _client().beta.messages.create(**kwargs)
    except anthropic.APIError as e:
        logger.error('Claude API error: %s', e)
        raise translate_api_error(e) from e

    if response.stop_reason == 'refusal':
        raise AIError("L'IA a refusé de traiter cette demande. Reformulez votre texte.", 422)
    if response.stop_reason == 'max_tokens' and not allow_truncated:
        raise AIError('La réponse de l\'IA est trop longue. Réduisez la taille du texte envoyé.', 422)
    return ''.join(block.text for block in response.content if block.type == 'text')


CHAPTER_MARKER = re.compile(r'^\s*#{2,4}\s*(INTRODUCTION[^\n]*|SECTION\s+(\d+)[^\n]*)$', re.IGNORECASE | re.MULTILINE)


def parse_chapter_text(text, section_count):
    """Découpe la réponse de write_chapter selon les lignes « ### INTRODUCTION » / « ### SECTION n »."""
    result = {'intro': '', 'sections': {}}
    matches = list(CHAPTER_MARKER.finditer(text))
    if not matches:
        if section_count == 0:
            result['intro'] = text.strip()
            return result
        raise AIError("La réponse de l'IA n'a pas le format attendu. Réessayez.", 502)
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        if not body:
            continue
        if match.group(2):
            number = int(match.group(2))
            if 1 <= number <= section_count:
                result['sections'][number] = body
        else:
            result['intro'] = body
    return result


def _str_list(description):
    return {'type': 'array', 'description': description, 'items': {'type': 'string'}}


PLAN_SCHEMA = {
    'type': 'object',
    'properties': {
        'chapters': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'order': {'type': 'integer'},
                    'sections': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'title': {'type': 'string'},
                                'subsections': _str_list('Titres des sous-sections'),
                            },
                            'required': ['title', 'subsections'],
                            'additionalProperties': False,
                        },
                    },
                },
                'required': ['title', 'order', 'sections'],
                'additionalProperties': False,
            },
        },
        'figures': _str_list('Figures, graphiques et illustrations recommandés'),
        'tables': _str_list('Tableaux recommandés'),
        'references': _str_list('Références suggérées, à vérifier par l\'étudiant'),
        'appendices': _str_list('Annexes suggérées (questionnaires, guides d\'entretien...)'),
        'glossary': _str_list('Termes du glossaire'),
    },
    'required': ['chapters', 'figures', 'tables', 'references', 'appendices', 'glossary'],
    'additionalProperties': False,
}

VERIFY_SCHEMA = {
    'type': 'object',
    'properties': {
        'score': {'type': 'integer', 'description': 'Qualité scientifique globale de 0 à 100'},
        'summary': {'type': 'string'},
        'issues': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'type': {'type': 'string', 'enum': ['incoherence', 'affirmation_sans_source', 'imprecision', 'style']},
                    'excerpt': {'type': 'string', 'description': 'Passage concerné, cité mot pour mot'},
                    'explanation': {'type': 'string'},
                    'suggestion': {'type': 'string'},
                },
                'required': ['type', 'excerpt', 'explanation', 'suggestion'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['score', 'summary', 'issues'],
    'additionalProperties': False,
}

REFORMULATION_STYLES = {
    'academic': 'un style académique soutenu',
    'simple': 'un style plus simple et plus clair, sans perdre la précision',
    'formal': 'un style formel et concis',
}

LANGUAGES = {'fr': 'français', 'en': 'anglais', 'es': 'espagnol', 'ar': 'arabe', 'pt': 'portugais', 'de': 'allemand'}


class AIService:
    @staticmethod
    def generate_plan(theme, context='', guide=''):
        """Plan complet du mémoire (§3.5). Renvoie une chaîne JSON conforme à PLAN_SCHEMA.
        `guide` : structure du modèle de mémoire acheté, que le plan doit respecter."""
        prompt = (
            f"Générez le plan détaillé d'un mémoire universitaire sur le thème suivant :\n"
            f"<theme>{theme}</theme>\n"
        )
        if context:
            prompt += f"\n<contexte>{context}</contexte>\n"
        if guide:
            prompt += (
                "\nRespectez la structure type suivante (organisation et logique des chapitres), "
                "en remplaçant les titres génériques par des titres précis et propres au thème :\n"
                f"<structure_type>{guide}</structure_type>\n"
            )
        prompt += (
            "\nLe plan comprend une introduction générale, plusieurs chapitres avec sections et "
            "sous-sections, une conclusion générale, ainsi que les figures, tableaux, références, "
            "annexes et termes de glossaire recommandés. Soyez concis : 3 à 6 chapitres, 2 à 4 sections "
            "par chapitre, 0 à 3 sous-sections par section, et au plus 5 éléments dans chacune des listes "
            "figures, tableaux, références, annexes et glossaire. N'incluez pas les pages liminaires "
            "(dédicace, remerciements, résumé), ni la bibliographie, ni les annexes dans les chapitres."
        )
        plan = json.loads(_ask(prompt, schema=PLAN_SCHEMA, openrouter_max_tokens=3000))
        return json.dumps(_clean_strings(plan), ensure_ascii=False)

    @staticmethod
    def write_chapter(context, chapter_title, chapter_guidance, sections, words_per_section, language='fr',
                      include_intro=True, already_written=''):
        """Rédige un chapitre : introduction du chapitre (si `include_intro`) puis chaque section demandée.
        `sections` : [(titre, consigne)] — seulement les sections encore vides lors d'une reprise.
        `already_written` : sections déjà rédigées du chapitre, pour assurer la continuité.
        Renvoie {'intro': str, 'sections': {numéro: str}} (numéros dans l'ordre de `sections`)."""
        lang = LANGUAGES.get(language, 'français')
        prompt = (
            f"Rédigez en {lang} le contenu du chapitre suivant d'un mémoire universitaire.\n"
            f"<memoire>{context}</memoire>\n"
            f"<chapitre>{chapter_title}</chapitre>\n"
        )
        if chapter_guidance:
            prompt += f"<consigne_chapitre>{chapter_guidance}</consigne_chapitre>\n"
        if already_written:
            prompt += (f"<deja_redige>{already_written}</deja_redige>\n"
                       "Ces parties du chapitre sont déjà rédigées : ne les répétez pas, poursuivez dans leur continuité.\n")
        prompt += "\nRespectez EXACTEMENT ce format, avec ces lignes de titre et rien d'autre autour :\n"
        if include_intro:
            prompt += "### INTRODUCTION DU CHAPITRE\n(un paragraphe de 80 à 150 mots qui annonce le chapitre)\n"
        for i, (title, hint) in enumerate(sections, start=1):
            prompt += f"### SECTION {i} — {title}" + (f" (consigne : {hint})" if hint else '') + "\n"
            prompt += f"(environ {words_per_section} mots)\n"
        prompt += (
            "\nRègles : style académique, paragraphes développés et argumentés, pas de listes à puces "
            "sauf si nécessaire, pas de titre markdown supplémentaire. N'inventez jamais de références "
            "bibliographiques ni de chiffres précis : quand une source ou une donnée est nécessaire, écrivez "
            "[source à compléter] ou [donnée à vérifier]."
        )
        text = _ask(prompt, openrouter_max_tokens=6000, allow_truncated=True)
        result = parse_chapter_text(text, len(sections))
        result['intro'] = clean_ai_text(result['intro'])
        result['sections'] = {n: clean_ai_text(body) for n, body in result['sections'].items()}
        return result

    @staticmethod
    def write_abstract(context, text, language='fr'):
        """Résumé du mémoire (avec mots-clés) puis sa traduction anglaise (Abstract, Keywords)."""
        lang = LANGUAGES.get(language, 'français')
        prompt = (
            f"Rédigez en {lang} le résumé du mémoire universitaire ci-dessous, à partir de son contenu réel.\n"
            f"<memoire>{context}</memoire>\n<texte>{text}</texte>\n\n"
            "Format attendu, sans aucune mise en forme Markdown :\n"
            "Un paragraphe de 200 à 300 mots : contexte, objectif, méthodologie, principaux résultats, conclusion.\n"
            "Une ligne « Mots-clés : » suivie de 4 à 6 mots-clés séparés par des virgules.\n"
            "Une ligne « Abstract »\nLa traduction anglaise fidèle du résumé.\n"
            "Une ligne « Keywords: » suivie des mots-clés en anglais.\n\n"
            "N'ajoutez aucun résultat, chiffre ou référence qui ne figure pas dans le texte."
        )
        return clean_ai_text(_ask(prompt, openrouter_max_tokens=2500))

    @staticmethod
    def list_acronyms(text):
        """Sigles et abréviations du mémoire : ceux employés dans le texte et ceux des organismes cités en toutes lettres."""
        result = clean_ai_text(_ask(
            "Établissez la liste des sigles et abréviations de ce mémoire. Relevez :\n"
            "1. les sigles et abréviations employés dans le texte (ex. ONG, PIB, etc.) ;\n"
            "2. les sigles officiels des organismes, institutions, programmes et notions cités en toutes lettres "
            "(ex. « Banque centrale des États de l'Afrique de l'Ouest » donne BCEAO).\n"
            "Écrivez une ligne par sigle, au format « SIGLE : signification complète », par ordre alphabétique, "
            "sans autre texte. Si la signification n'est pas certaine, ajoutez « [à vérifier] ». "
            f"S'il n'y en a vraiment aucun, répondez seulement AUCUN.\n\n<texte>{text}</texte>",
            openrouter_max_tokens=1500,
        ))
        return '' if result.strip().upper().rstrip('.') == 'AUCUN' else result

    @staticmethod
    def list_tables_figures(context, text, language='fr'):
        """Liste des tableaux et figures : ceux du texte, complétés par ceux que le mémoire devrait comporter."""
        lang = LANGUAGES.get(language, 'français')
        prompt = (
            f"Établissez en {lang} la liste des tableaux et figures du mémoire universitaire ci-dessous.\n"
            f"<memoire>{context}</memoire>\n<texte>{text}</texte>\n\n"
            "1. Relevez les tableaux et figures mentionnés dans le texte (« Tableau 1 », « Figure 2 », graphiques, "
            "schémas, cartes, organigrammes) avec leur titre.\n"
            "2. S'il y en a peu ou pas, proposez les tableaux et figures que ce mémoire devrait comporter d'après sa "
            "méthodologie et ses résultats, en ajoutant « [à produire] » à la fin de leur ligne.\n\n"
            "Format exact, sans aucune mise en forme Markdown ni autre texte :\n"
            "Liste des tableaux\nTableau 1 : titre\nTableau 2 : titre\n\n"
            "Liste des figures\nFigure 1 : titre\nFigure 2 : titre\n\n"
            "Numérotez de façon continue dans chaque liste. N'inventez aucune donnée chiffrée."
        )
        return clean_ai_text(_ask(prompt, openrouter_max_tokens=1500))

    @staticmethod
    def write_annexes(context, guidance, text, language='fr'):
        """Annexes rédigeables à partir de la méthodologie (questionnaire, guide d'entretien, grille...)."""
        lang = LANGUAGES.get(language, 'français')
        prompt = (
            f"Rédigez en {lang} les annexes du mémoire universitaire ci-dessous.\n"
            f"<memoire>{context}</memoire>\n"
            + (f"<annexes_prevues>{guidance}</annexes_prevues>\n" if guidance else '')
            + f"<texte>{text}</texte>\n\n"
            "Pour chaque annexe utile au mémoire (questionnaire d'enquête, guide d'entretien, grille d'observation, "
            "fiche de collecte...), écrivez une ligne « Annexe N : titre » puis son contenu complet et directement "
            "utilisable (questions numérotées, rubriques, consignes), cohérent avec la méthodologie décrite dans le texte. "
            "Pour les documents qui ne peuvent pas être rédigés (autorisations, documents internes, états financiers, "
            "cartes, photos), écrivez seulement la ligne « Annexe N : titre » suivie de "
            "« [Document à insérer : description] ». N'inventez aucun chiffre ni résultat."
        )
        return clean_ai_text(_ask(prompt, openrouter_max_tokens=5000, allow_truncated=True))

    @staticmethod
    def chat(message, project_id, user):
        system = ACADEMIC_SYSTEM
        if project_id:
            project = Project.objects.filter(id=project_id, user=user).first()
            if project:
                system += f"\n\nL'étudiant travaille sur un mémoire de niveau {project.level} intitulé « {project.title} »"
                system += f", sur le thème : {project.theme}." if project.theme else '.'
        return clean_ai_text(_ask(message, system=system))

    @staticmethod
    def verify(content):
        """IA scientifique : incohérences et affirmations sans source (§3.7)."""
        return _clean_strings(json.loads(_ask(
            "Relisez ce passage de mémoire comme un relecteur scientifique exigeant. Relevez les "
            "incohérences, les affirmations qui nécessiteraient une source, les imprécisions et "
            "les problèmes de style académique. Si le texte ne pose pas de problème, renvoyez une "
            f"liste vide.\n\n<texte>{content}</texte>",
            effort='high',
            schema=VERIFY_SCHEMA,
            openrouter_max_tokens=2000,
        )))

    @staticmethod
    def reformulate(text, style='academic'):
        style_label = REFORMULATION_STYLES.get(style, REFORMULATION_STYLES['academic'])
        return clean_ai_text(_ask(
            f"Reformulez le texte suivant dans {style_label}, en conservant son sens et sa langue. "
            f"Renvoyez uniquement le texte reformulé.\n\n<texte>{text}</texte>",
            effort='low',
        ))

    @staticmethod
    def summarize(text):
        return clean_ai_text(_ask(
            "Résumez le texte suivant en un paragraphe académique qui conserve les idées clés. "
            f"Renvoyez uniquement le résumé.\n\n<texte>{text}</texte>",
            effort='low',
        ))

    @staticmethod
    def translate(text, target_lang='en'):
        language = LANGUAGES.get(target_lang, target_lang)
        return clean_ai_text(_ask(
            f"Traduisez le texte suivant en {language}, dans un registre académique. "
            f"Renvoyez uniquement la traduction.\n\n<texte>{text}</texte>",
            effort='low',
        ))
