"""Point d'entrée Vercel : toutes les requêtes (voir vercel.json) arrivent ici et sont confiées à Django."""
import os
import sys
from pathlib import Path

# Racine du backend (dossier memoai_pro) importable : config, users, projects...
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from config.wsgi import application  # noqa: E402

app = application
