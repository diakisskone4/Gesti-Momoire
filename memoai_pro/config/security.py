"""En-têtes de sécurité ajoutés à toutes les réponses de l'API.

L'API ne renvoie que du JSON, des fichiers (exports, images) et l'administration Django :
- aucune page de l'API ne doit pouvoir exécuter de script ni être affichée dans un cadre ;
- les réponses authentifiées ne doivent pas rester dans un cache partagé (proxy, navigateur).
"""

API_CSP = "default-src 'none'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# Administration Django : ses propres feuilles de style et scripts uniquement.
ADMIN_CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
             "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'")
PERMISSIONS_POLICY = 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()'


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        from django.conf import settings
        self.get_response = get_response
        self.admin_prefix = '/' + settings.ADMIN_URL
        self.docs_prefixes = ('/swagger', '/redoc')

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path
        if path.startswith(self.docs_prefixes):
            return response  # Swagger (développement uniquement) charge ses propres scripts
        is_admin = path.startswith(self.admin_prefix) or path.startswith('/static/')
        response.headers.setdefault('Content-Security-Policy', ADMIN_CSP if is_admin else API_CSP)
        response.headers.setdefault('Permissions-Policy', PERMISSIONS_POLICY)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Cross-Origin-Resource-Policy', 'cross-origin' if not is_admin else 'same-origin')
        if request.headers.get('Authorization') or path.startswith(self.admin_prefix):
            response.headers.setdefault('Cache-Control', 'no-store')
        # Ne pas annoncer la technologie utilisée.
        for header in ('Server', 'X-Powered-By'):
            if header in response.headers:
                del response.headers[header]
        return response
