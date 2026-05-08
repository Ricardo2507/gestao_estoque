from django.contrib import admin

from .models import RelatorioEstoque


@admin.register(RelatorioEstoque)
class RelatorioEstoqueAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_original', 'data_envio')
    search_fields = ('nome_original',)
