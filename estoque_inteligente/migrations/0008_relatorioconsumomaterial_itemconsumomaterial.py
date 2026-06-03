# Generated for independent AX0095 monthly material consumption reports

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("estoque_inteligente", "0007_relatorioconsumour_itemconsumour"),
    ]

    operations = [
        migrations.CreateModel(
            name="RelatorioConsumoMaterial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome_original", models.CharField(blank=True, max_length=255)),
                ("arquivo_pdf", models.FileField(upload_to="relatorios_consumo_material/")),
                ("hash_arquivo", models.CharField(blank=True, db_index=True, max_length=64)),
                ("texto_extraido", models.TextField(blank=True)),
                ("data_envio", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Relatório de consumo mensal de material",
                "verbose_name_plural": "Relatórios de consumo mensal de material",
                "ordering": ["-data_envio"],
            },
        ),
        migrations.CreateModel(
            name="ItemConsumoMaterial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("orgao_codigo", models.CharField(blank=True, db_index=True, max_length=20)),
                ("orgao_descricao", models.CharField(blank=True, max_length=255)),
                ("almoxarifado_codigo", models.CharField(blank=True, db_index=True, max_length=30)),
                ("almoxarifado_descricao", models.CharField(blank=True, max_length=255)),
                ("material_codigo", models.CharField(db_index=True, max_length=30)),
                ("material_descricao", models.TextField()),
                ("unidade_medida", models.CharField(blank=True, max_length=30)),
                ("periodo_inicio", models.CharField(blank=True, max_length=7)),
                ("periodo_fim", models.CharField(blank=True, max_length=7)),
                ("data_geracao", models.CharField(blank=True, max_length=30)),
                ("consumos_mensais", models.JSONField(blank=True, default=dict)),
                ("total", models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ("cmp", models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ("saldo_atual", models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                (
                    "relatorio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itens_consumo_material",
                        to="estoque_inteligente.relatorioconsumomaterial",
                    ),
                ),
            ],
            options={
                "verbose_name": "Item de consumo mensal de material",
                "verbose_name_plural": "Itens de consumo mensal de material",
                "ordering": ["material_codigo"],
                "indexes": [
                    models.Index(fields=["material_codigo"], name="estoque_int_material_0c59c5_idx"),
                    models.Index(fields=["almoxarifado_codigo", "material_codigo"], name="estoque_int_almoxar_6af43d_idx"),
                ],
            },
        ),
    ]
