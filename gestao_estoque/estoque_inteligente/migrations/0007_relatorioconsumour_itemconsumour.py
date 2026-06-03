# Generated for independent AX0126 consumption-by-UR reports

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("estoque_inteligente", "0006_itemestoque_ativo_alter_itemestoque_conta_codigo_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="RelatorioConsumoUR",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome_original", models.CharField(blank=True, max_length=255)),
                ("arquivo_pdf", models.FileField(upload_to="relatorios_consumo_ur/")),
                ("hash_arquivo", models.CharField(blank=True, db_index=True, max_length=64)),
                ("texto_extraido", models.TextField(blank=True)),
                ("data_envio", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Relatório de consumo por UR",
                "verbose_name_plural": "Relatórios de consumo por UR",
                "ordering": ["-data_envio"],
            },
        ),
        migrations.CreateModel(
            name="ItemConsumoUR",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("orgao_codigo", models.CharField(blank=True, db_index=True, max_length=20)),
                ("orgao_descricao", models.CharField(blank=True, max_length=255)),
                ("material_codigo", models.CharField(db_index=True, max_length=30)),
                ("material_descricao", models.TextField()),
                ("unidade_medida", models.CharField(blank=True, max_length=80)),
                ("periodo_inicio", models.CharField(blank=True, max_length=7)),
                ("periodo_fim", models.CharField(blank=True, max_length=7)),
                ("data_geracao", models.CharField(blank=True, max_length=30)),
                ("ur_codigo", models.CharField(db_index=True, max_length=30)),
                ("ur_descricao", models.CharField(max_length=255)),
                ("consumos_mensais", models.JSONField(blank=True, default=dict)),
                ("total", models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                ("cmp", models.DecimalField(decimal_places=4, default=0, max_digits=14)),
                (
                    "relatorio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itens_consumo",
                        to="estoque_inteligente.relatorioconsumour",
                    ),
                ),
            ],
            options={
                "verbose_name": "Item de consumo por UR",
                "verbose_name_plural": "Itens de consumo por UR",
                "ordering": ["material_codigo", "ur_codigo"],
                "indexes": [
                    models.Index(fields=["material_codigo", "ur_codigo"], name="estoque_int_material_2c9e42_idx"),
                    models.Index(fields=["ur_codigo", "material_codigo"], name="estoque_int_ur_codi_6d7f36_idx"),
                ],
            },
        ),
    ]
