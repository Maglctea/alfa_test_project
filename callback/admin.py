from django.contrib import admin
from callback.models import Player, Game


class PlayerAdminInline(admin.TabularInline):
    """Inline widget for adding players in the game"""

    model = Game.players.through
    extra = 1


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """Class for viewing players in admin panel"""

    list_display = ('pk', 'name', 'email', 'created_at', 'updated_at')
    list_display_links = ('pk', 'name',)
    ordering = ('pk', 'name', 'email', 'created_at', 'updated_at')
    list_per_page = 30
    search_fields = ('name', 'email')


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Class for viewing games in admin panel"""
    fieldsets = [
        (
            None,
            {
                "fields": ["name", ],
            },
        ),
        (
            "Date param",
            {
                "fields": ['created_at', 'updated_at'],
            },
        )
    ]
    readonly_fields = ('created_at', 'updated_at')
    list_prefetch_related = ('players',)
    list_filter = ('created_at', 'updated_at')
    list_display = ('pk', 'name', 'players_', 'created_at', 'updated_at')
    list_display_links = ('pk', 'name',)
    ordering = ('pk', 'name', 'created_at', 'updated_at')
    list_per_page = 30
    search_fields = ('name',)
    inlines = (PlayerAdminInline,)

    def players_(self, obj):
        return [course.name for course in obj.players.all()]
