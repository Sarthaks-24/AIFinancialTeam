from django.contrib import admin

from .models import Conversation, MemoryFact, Turn


class TurnInline(admin.TabularInline):
    model = Turn
    extra = 0
    readonly_fields = ("role", "specialist_name", "content", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "specialist", "started_at", "last_active_at")
    list_filter = ("specialist",)
    inlines = [TurnInline]


@admin.register(MemoryFact)
class MemoryFactAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "key", "created_at", "expires_at")
    list_filter = ("category",)
