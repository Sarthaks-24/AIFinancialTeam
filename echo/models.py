from django.conf import settings
from django.db import models
from agents.models import Organization


class Conversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="echo_conversations",
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    # Legacy conversations retain their originating specialist. New sessions
    # use turns for specialist attribution instead of treating it as a boundary.
    specialist = models.CharField(max_length=100, blank=True, default="")
    title = models.CharField(max_length=255, blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "archived_at", "-last_active_at"]),
        ]

    def __str__(self):
        return f"{self.specialist} · user {self.user_id}"


class Turn(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        SPECIALIST = "specialist", "Specialist"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="turns",
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    specialist_name = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} @ {self.created_at:%Y-%m-%d %H:%M}"


class MemoryFact(models.Model):
    class Category(models.TextChoices):
        PREFERENCE = "preference", "Preference"
        ORG_CONTEXT = "org_context", "Org Context"
        PRIOR_FINDING = "prior_finding", "Prior Finding"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="echo_facts",
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    category = models.CharField(max_length=40, choices=Category.choices)
    key = models.CharField(max_length=200)
    value = models.TextField()
    source_turn = models.ForeignKey(
        Turn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "category", "key"]),
        ]

    def __str__(self):
        return f"{self.category}:{self.key}"
