from django.db import models
from users.models import User
from projects.models import Project

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    payment_method = models.CharField(max_length=50)  # stripe, paypal, mobile_money
    status = models.CharField(max_length=20, choices=(
        ('PENDING', 'En attente'),
        ('SUCCESS', 'Réussi'),
        ('FAILED', 'Échoué'),
        ('REFUNDED', 'Remboursé'),
    ), default='PENDING')
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    paypal_transaction_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)