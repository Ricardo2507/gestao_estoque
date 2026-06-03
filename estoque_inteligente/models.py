from django.db import models


class RelatorioEstoque(models.Model):
    nome_original = models.CharField(max_length=255, blank=True)
    arquivo_pdf = models.FileField(upload_to="relatorios_estoque/")
    hash_arquivo = models.CharField(max_length=64, blank=True, db_index=True)
    texto_extraido = models.TextField(blank=True)
    data_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_original or f"Relatório {self.pk}"


class ItemEstoque(models.Model):
    STATUS_CHOICES = [
        ("CRITICO", "Crítico"),
        ("ATENCAO", "Atenção"),
        ("NORMAL", "Normal"),
        ("SEM_MOVIMENTO", "Sem movimento"),
        ("ESTOQUE_PARADO", "Estoque parado"),
    ]

    relatorio = models.ForeignKey(
        RelatorioEstoque,
        on_delete=models.CASCADE,
        related_name="itens",
    )

    ativo = models.BooleanField(default=True, db_index=True)

    conta_codigo = models.CharField(max_length=30, blank=True, db_index=True)
    conta_descricao = models.CharField(max_length=255, blank=True)

    numero_item = models.PositiveIntegerField()
    codigo_material = models.CharField(max_length=20)
    descricao = models.TextField()
    unidade_medida = models.CharField(max_length=20, blank=True)
    finalidade_compra = models.CharField(max_length=100, blank=True)

    cmm = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ce = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estoque = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    preco_medio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="SEM_MOVIMENTO",
        db_index=True,
    )

    quantidade_sugerida = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    class Meta:
        ordering = ["conta_codigo", "numero_item"]

    def __str__(self):
        return f"{self.conta_codigo} - {self.numero_item} - {self.codigo_material}"
    
class RelatorioConsumoUR(models.Model):
    nome_original = models.CharField(max_length=255, blank=True)
    arquivo_pdf = models.FileField(upload_to="relatorios_consumo_ur/")
    hash_arquivo = models.CharField(max_length=64, blank=True, db_index=True)
    texto_extraido = models.TextField(blank=True)
    data_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_original or f"Relatório Consumo UR {self.pk}"


class ItemConsumoUR(models.Model):
    relatorio = models.ForeignKey(
        RelatorioConsumoUR,
        on_delete=models.CASCADE,
        related_name="itens_consumo",
    )

    material_codigo = models.CharField(max_length=20, db_index=True)
    material_descricao = models.TextField()
    unidade_medida = models.CharField(max_length=30, blank=True)

    periodo_inicio = models.CharField(max_length=7, blank=True)
    periodo_fim = models.CharField(max_length=7, blank=True)

    ur_codigo = models.CharField(max_length=20, db_index=True)
    ur_descricao = models.CharField(max_length=255)

    consumos_mensais = models.JSONField(default=dict, blank=True)

    total = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    cmp = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        ordering = ["material_codigo", "ur_codigo"]

    def __str__(self):
        return f"{self.material_codigo} - {self.ur_codigo}"
    
class RelatorioConsumoMaterial(models.Model):
    nome_original = models.CharField(max_length=255, blank=True)
    arquivo_pdf = models.FileField(upload_to="relatorios_consumo_material/")
    hash_arquivo = models.CharField(max_length=64, blank=True, db_index=True)
    texto_extraido = models.TextField(blank=True)
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Relatório de consumo mensal de material"
        verbose_name_plural = "Relatórios de consumo mensal de material"
        ordering = ["-data_envio"]

    def __str__(self):
        return self.nome_original or f"Consumo mensal de material {self.pk}"


class ItemConsumoMaterial(models.Model):
    relatorio = models.ForeignKey(
        RelatorioConsumoMaterial,
        on_delete=models.CASCADE,
        related_name="itens_consumo_material",
    )

    orgao_codigo = models.CharField(max_length=20, blank=True, db_index=True)
    orgao_descricao = models.CharField(max_length=255, blank=True)

    almoxarifado_codigo = models.CharField(max_length=30, blank=True, db_index=True)
    almoxarifado_descricao = models.CharField(max_length=255, blank=True)

    material_codigo = models.CharField(max_length=30, db_index=True)
    material_descricao = models.TextField()
    unidade_medida = models.CharField(max_length=30, blank=True)

    periodo_inicio = models.CharField(max_length=7, blank=True)
    periodo_fim = models.CharField(max_length=7, blank=True)
    data_geracao = models.CharField(max_length=30, blank=True)

    consumos_mensais = models.JSONField(default=dict, blank=True)

    total = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cmp = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    saldo_atual = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    class Meta:
        verbose_name = "Item de consumo mensal de material"
        verbose_name_plural = "Itens de consumo mensal de material"
        ordering = ["material_codigo"]
        indexes = [
            models.Index(
                fields=["material_codigo"],
                name="idx_mat_consumo_mat",
            ),
            models.Index(
                fields=["almoxarifado_codigo", "material_codigo"],
                name="idx_almox_mat",
            ),
        ]

    def __str__(self):
        return f"{self.material_codigo} - {self.material_descricao}"