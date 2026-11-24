from decimal import Decimal

from django.conf import settings
from django.db import models

from . import jemeni


class MemoirTemplate(models.Model):
    """Modèle de mémoire vendu sur la plateforme : page de garde + plan type commenté."""

    LEVEL_CHOICES = [('', 'Tous niveaux'), ('LICENCE', 'Licence'), ('MASTER', 'Master'), ('DOCTORAT', 'Doctorat')]
    COVER_CHOICES = [
        ('classique', 'Classique universitaire'),
        ('moderne', 'Moderne à bandeau'),
        ('elegant', 'Élégant à double cadre'),
        ('these', 'Thèse doctorale'),
        ('minimaliste', 'Minimaliste'),
        ('institutionnel', 'Institutionnel'),
    ]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=150)
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    domain = models.CharField(max_length=150, blank=True)
    cover_style = models.CharField(max_length=30, choices=COVER_CHOICES, default='classique')
    accent_color = models.CharField(max_length=7, default='#0f766e')
    # [{"title", "type", "guidance", "sections": [{"title", "guidance"}]}]
    structure = models.JSONField(default=list)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('5000'))
    currency = models.CharField(max_length=3, default='XOF')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'modèle de mémoire'
        verbose_name_plural = 'modèles de mémoire'

    def __str__(self):
        return self.name

    @property
    def is_free(self):
        """Modèle à 0 FCFA : disponible pour tous les étudiants, sans paiement."""
        return self.price <= 0

    def is_owned_by(self, user):
        return self.is_free or TemplatePurchase.valid().filter(template=self, user=user).exists()


class TemplatePurchase(models.Model):
    """Achat d'un modèle via Jɛmɛnipay (page de paiement hébergée) ; « saspay » : anciens achats."""

    PENDING, PAID, FAILED, CANCELLED = 'PENDING', 'PAID', 'FAILED', 'CANCELLED'
    STATUS_CHOICES = [(PENDING, 'En attente'), (PAID, 'Payé'), (FAILED, 'Échoué'), (CANCELLED, 'Annulé')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='template_purchases')
    template = models.ForeignKey(MemoirTemplate, on_delete=models.PROTECT, related_name='purchases')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='XOF')
    provider = models.CharField(max_length=20, default='jemeni')
    checkout_session_id = models.CharField(max_length=64, blank=True, db_index=True)
    checkout_url = models.URLField(max_length=500, blank=True)
    transaction_id = models.CharField(max_length=64, blank=True, db_index=True)
    transaction_reference = models.CharField(max_length=100, blank=True, db_index=True)
    amount_charged = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'achat de modèle'
        verbose_name_plural = 'achats de modèles'
        # Pas de contrainte d'unicité sur les achats payés : un paiement réellement encaissé
        # doit toujours être enregistré. Les doublons sont évités en amont (session réutilisée).

    def __str__(self):
        return f'{self.user} — {self.template} ({self.status})'

    @classmethod
    def valid(cls):
        """Achats payés qui donnent droit au modèle. Les paiements simulés (bac à sable) ne comptent
        qu'en développement, avec les clés de test ; jamais en production."""
        purchases = cls.objects.filter(status=cls.PAID)
        return purchases if jemeni.test_mode_allowed() else purchases.exclude(provider=jemeni.PROVIDER_TEST)
