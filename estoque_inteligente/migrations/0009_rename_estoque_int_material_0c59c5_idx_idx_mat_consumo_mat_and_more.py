from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("estoque_inteligente", "0008_relatorioconsumomaterial_itemconsumomaterial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER INDEX IF EXISTS estoque_int_material_0c59c5_idx "
                        "RENAME TO idx_mat_consumo_mat;"
                    ),
                    reverse_sql=(
                        "ALTER INDEX IF EXISTS idx_mat_consumo_mat "
                        "RENAME TO estoque_int_material_0c59c5_idx;"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER INDEX IF EXISTS estoque_int_almoxar_6af43d_idx "
                        "RENAME TO idx_almox_mat;"
                    ),
                    reverse_sql=(
                        "ALTER INDEX IF EXISTS idx_almox_mat "
                        "RENAME TO estoque_int_almoxar_6af43d_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.RenameIndex(
                    model_name="itemconsumomaterial",
                    old_name="estoque_int_material_0c59c5_idx",
                    new_name="idx_mat_consumo_mat",
                ),
                migrations.RenameIndex(
                    model_name="itemconsumomaterial",
                    old_name="estoque_int_almoxar_6af43d_idx",
                    new_name="idx_almox_mat",
                ),
            ],
        ),
    ]