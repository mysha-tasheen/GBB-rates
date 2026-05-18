from django.contrib import admin

from apps.agents.models import Agent, AgentApiKey


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("company_name", "phone", "is_active", "created_at")
    search_fields = ("company_name", "user__email")


@admin.register(AgentApiKey)
class AgentApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "agent", "is_active", "expires_at", "last_used_at")
    search_fields = ("name", "key", "agent__company_name")
    readonly_fields = ("key", "created_at", "last_used_at")
