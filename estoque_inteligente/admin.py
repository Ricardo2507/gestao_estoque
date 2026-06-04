from django.contrib import admin

from .models import (
    RelatorioEstoque,
    ItemEstoque,
    RelatorioConsumoMaterial,
    ItemConsumoMaterial,
    RelatorioConsumoUR,
    ItemConsumoUR,
)


@admin.register(RelatorioEstoque)
class RelatorioEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome_original",
        "data_envio",
    )
    search_fields = ("nome_original",)
    ordering = ("-data_envio",)


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_material",
        "descricao",
        "estoque",
        "status",
        "quantidade_sugerida",
    )

    search_fields = (
        "codigo_material",
        "descricao",
    )

    list_filter = (
        "status",
        "ativo",
    )

    list_per_page = 50


@admin.register(RelatorioConsumoMaterial)
class RelatorioConsumoMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome_original",
        "data_envio",
    )

    search_fields = (
        "nome_original",
    )

    ordering = ("-data_envio",)


@admin.register(ItemConsumoMaterial)
class ItemConsumoMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "material_codigo",
        "material_descricao",
        "total",
        "cmp",
        "saldo_atual",
    )

    search_fields = (
        "material_codigo",
        "material_descricao",
    )

    list_per_page = 50


@admin.register(RelatorioConsumoUR)
class RelatorioConsumoURAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome_original",
        "data_envio",
    )

    search_fields = (
        "nome_original",
    )

    ordering = ("-data_envio",)


@admin.register(ItemConsumoUR)
class ItemConsumoURAdmin(admin.ModelAdmin):
    list_display = (
        "material_codigo",
        "ur_codigo",
        "ur_descricao",
        "total",
        "cmp",
    )

    search_fields = (
        "material_codigo",
        "material_descricao",
        "ur_codigo",
        "ur_descricao",
    )

    list_filter = (
        "ur_codigo",
    )

    list_per_page = 50