from django.contrib import admin

from .models import (
    ItemConsumoUR,
    ItemEstoque,
    RelatorioConsumoUR,
    RelatorioEstoque,
)


@admin.register(RelatorioEstoque)
class RelatorioEstoqueAdmin(admin.ModelAdmin):
    list_display = ("id", "nome_original", "data_envio")
    search_fields = ("nome_original",)


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "conta_codigo",
        "numero_item",
        "codigo_material",
        "status",
        "ativo",
    )
    list_filter = ("status", "ativo", "conta_codigo")
    search_fields = ("codigo_material", "descricao", "conta_descricao")


@admin.register(RelatorioConsumoUR)
class RelatorioConsumoURAdmin(admin.ModelAdmin):
    list_display = ("id", "nome_original", "data_envio")
    search_fields = ("nome_original",)


@admin.register(ItemConsumoUR)
class ItemConsumoURAdmin(admin.ModelAdmin):
    list_display = (
        "material_codigo",
        "material_descricao",
        "ur_codigo",
        "ur_descricao",
        "total",
        "cmp",
    )
    list_filter = ("ur_codigo", "periodo_inicio", "periodo_fim")
    search_fields = (
        "material_codigo",
        "material_descricao",
        "ur_codigo",
        "ur_descricao",
    )
