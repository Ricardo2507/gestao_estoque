from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .models import (
    ItemConsumoMaterial,
    ItemEstoque,
    RelatorioConsumoMaterial,
    RelatorioEstoque,
)


def decimal_seguro(valor):
    try:
        return Decimal(str(valor or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def calcular_cobertura_meses(estoque, cmp):
    estoque = decimal_seguro(estoque)
    cmp = decimal_seguro(cmp)

    if cmp <= 0:
        return None

    return estoque / cmp


def classificar_prioridade(status, estoque, cmp, quantidade_sugerida):
    estoque = decimal_seguro(estoque)
    cmp = decimal_seguro(cmp)
    quantidade_sugerida = decimal_seguro(quantidade_sugerida)
    cobertura = calcular_cobertura_meses(estoque, cmp)

    if status == "CRITICO":
        return "ALTA"

    if quantidade_sugerida > 0 and status in ["ATENCAO", "NORMAL"]:
        return "MEDIA"

    if cobertura is not None and cobertura <= 1:
        return "ALTA"

    if cobertura is not None and cobertura <= 2:
        return "MEDIA"

    if status == "ATENCAO":
        return "MEDIA"

    return "BAIXA"


class ConsultaPrioridadeCompraView(LoginRequiredMixin, TemplateView):
    """
    Consulta gerencial sem alteração de estrutura.

    Cruza a posição atual de estoque com o último relatório de consumo mensal
    de material, usando o código do material como chave.

    A consulta evita operações pesadas:
    - usa apenas itens ativos da última posição de estoque;
    - usa apenas itens do último relatório de consumo mensal;
    - carrega os dados com .values(), reduzindo objetos em memória;
    - faz o relacionamento em dicionário Python, adequado ao volume atual.
    """

    template_name = "estoque_inteligente/consultas_gerenciais/prioridade_compra.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        busca = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        prioridade = self.request.GET.get("prioridade", "").strip()
        somente_com_consumo = self.request.GET.get("somente_com_consumo", "") == "1"

        ultimo_relatorio_estoque = (
            RelatorioEstoque.objects
            .order_by("-data_envio", "-id")
            .first()
        )

        ultimo_relatorio_consumo = (
            RelatorioConsumoMaterial.objects
            .order_by("-data_envio", "-id")
            .first()
        )

        itens_estoque = ItemEstoque.objects.filter(ativo=True)

        if ultimo_relatorio_estoque:
            itens_estoque = itens_estoque.filter(relatorio=ultimo_relatorio_estoque)

        if busca:
            itens_estoque = itens_estoque.filter(descricao__icontains=busca)

        if status:
            itens_estoque = itens_estoque.filter(status=status)

        itens_estoque = list(
            itens_estoque.values(
                "codigo_material",
                "descricao",
                "unidade_medida",
                "conta_codigo",
                "conta_descricao",
                "estoque",
                "cmm",
                "ce",
                "preco_medio",
                "valor",
                "status",
                "quantidade_sugerida",
            ).order_by("status", "codigo_material")
        )

        codigos = [item["codigo_material"] for item in itens_estoque]

        consumo_por_material = {}

        if ultimo_relatorio_consumo and codigos:
            consumos = (
                ItemConsumoMaterial.objects
                .filter(
                    relatorio=ultimo_relatorio_consumo,
                    material_codigo__in=codigos,
                )
                .values(
                    "material_codigo",
                    "total",
                    "cmp",
                    "saldo_atual",
                )
            )

            consumo_por_material = {
                item["material_codigo"]: item
                for item in consumos
            }

        linhas = []

        for item in itens_estoque:
            codigo = item["codigo_material"]
            consumo = consumo_por_material.get(codigo, {})

            consumo_total = decimal_seguro(consumo.get("total"))
            cmp_consumo = decimal_seguro(consumo.get("cmp"))
            saldo_consumo = decimal_seguro(consumo.get("saldo_atual"))

            if somente_com_consumo and consumo_total <= 0:
                continue

            cobertura_meses = calcular_cobertura_meses(
                item["estoque"],
                cmp_consumo,
            )

            prioridade_calculada = classificar_prioridade(
                item["status"],
                item["estoque"],
                cmp_consumo,
                item["quantidade_sugerida"],
            )

            if prioridade and prioridade_calculada != prioridade:
                continue

            linhas.append(
                {
                    "codigo_material": codigo,
                    "descricao": item["descricao"],
                    "unidade_medida": item["unidade_medida"],
                    "conta_codigo": item["conta_codigo"],
                    "conta_descricao": item["conta_descricao"],
                    "estoque": item["estoque"],
                    "cmm": item["cmm"],
                    "ce": item["ce"],
                    "preco_medio": item["preco_medio"],
                    "valor": item["valor"],
                    "status": item["status"],
                    "quantidade_sugerida": item["quantidade_sugerida"],
                    "consumo_total": consumo_total,
                    "cmp_consumo": cmp_consumo,
                    "saldo_consumo": saldo_consumo,
                    "cobertura_meses": cobertura_meses,
                    "prioridade": prioridade_calculada,
                }
            )

        ordem_prioridade = {
            "ALTA": 0,
            "MEDIA": 1,
            "BAIXA": 2,
        }

        linhas.sort(
            key=lambda linha: (
                ordem_prioridade.get(linha["prioridade"], 9),
                linha["codigo_material"],
            )
        )

        context["linhas"] = linhas
        context["busca"] = busca
        context["status_atual"] = status
        context["prioridade_atual"] = prioridade
        context["somente_com_consumo"] = somente_com_consumo
        context["ultimo_relatorio_estoque"] = ultimo_relatorio_estoque
        context["ultimo_relatorio_consumo"] = ultimo_relatorio_consumo
        context["total_linhas"] = len(linhas)
        context["total_alta"] = sum(1 for linha in linhas if linha["prioridade"] == "ALTA")
        context["total_media"] = sum(1 for linha in linhas if linha["prioridade"] == "MEDIA")
        context["total_baixa"] = sum(1 for linha in linhas if linha["prioridade"] == "BAIXA")

        return context
