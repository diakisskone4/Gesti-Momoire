import os
from openai import OpenAI
from django.conf import settings
from projects.models import Project

client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
# OpenRouter utilise des noms de modèles préfixés, ex: "openai/gpt-4"
AI_MODEL = os.environ.get('AI_MODEL', 'openai/gpt-4')

class AIService:
    @staticmethod
    def generate_plan(theme):
        prompt = f"""
        Vous êtes un assistant académique. Générez un plan détaillé pour un mémoire universitaire sur le thème suivant : {theme}.
        Le plan doit inclure :
        - Introduction
        - Plusieurs chapitres avec sections et sous-sections
        - Conclusion
        - Annexes suggérées
        - Références bibliographiques clés
        - Figures et tableaux recommandés
        Retournez le résultat au format JSON structuré avec les champs : chapters (liste d'objets avec title et children), references, appendices.
        """
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000
        )
        return response.choices[0].message.content

    @staticmethod
    def chat(message, project_id, user):
        # Contexte du projet pour personnaliser (optionnel)
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=project_id, user=user)
            except Project.DoesNotExist:
                project = None

        if project:
            system_prompt = f"Vous aidez un étudiant à rédiger son mémoire sur '{project.theme}'. Répondez de manière académique."
        else:
            system_prompt = "Vous aidez un étudiant à rédiger son mémoire. Répondez de manière académique."
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content