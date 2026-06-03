from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render

from estoque_inteligente.models import (
    ItemEstoque,
    RelatorioEstoque,
)


@login_required
def dashboard_home(request):

    itens_ativos = ItemEstoque.objects.filter(
        ativo=True
    )

    totais = itens_ativos.aggregate(

        total_itens=Count("id"),

        total_criticos=Count(
            "id",
            filter=Q(status="CRITICO"),
        ),

        total_atencao=Count(
            "id",
            filter=Q(status="ATENCAO"),
        ),

        total_normais=Count(
            "id",
            filter=Q(status="NORMAL"),
        ),

        total_sem_movimento=Count(
            "id",
            filter=Q(status="SEM_MOVIMENTO"),
        ),

        total_estoque_parado=Count(
            "id",
            filter=Q(status="ESTOQUE_PARADO"),
        ),

        valor_total_estoque=Sum("valor"),

        # ---------------------------------------------------
        # SOMAR APENAS CRÍTICOS E ATENÇÃO
        # ---------------------------------------------------

        total_sugerido_compra=Sum(
            "quantidade_sugerida",
            filter=Q(status__in=[
                "CRITICO",
                "ATENCAO",
            ]),
        ),
    )

    itens_por_status = (
        itens_ativos
        .values("status")
        .annotate(
            total=Count("id")
        )
        .order_by("status")
    )

    criticos_por_conta = (
        itens_ativos
        .filter(status="CRITICO")
        .values(
            "conta_codigo",
            "conta_descricao",
        )
        .annotate(
            total=Count("id")
        )
        .order_by("-total")[:10]
    )

    ultimos_relatorios = (
        RelatorioEstoque.objects
        .order_by("-data_envio")[:5]
    )

    contexto = {

        "total_relatorios":
            RelatorioEstoque.objects.count(),

        "total_itens":
            totais["total_itens"] or 0,

        "total_criticos":
            totais["total_criticos"] or 0,

        "total_atencao":
            totais["total_atencao"] or 0,

        "total_normais":
            totais["total_normais"] or 0,

        "total_sem_movimento":
            totais["total_sem_movimento"] or 0,

        "total_estoque_parado":
            totais["total_estoque_parado"] or 0,

        "valor_total_estoque":
            totais["valor_total_estoque"] or Decimal("0"),

        "total_sugerido_compra":
            totais["total_sugerido_compra"] or Decimal("0"),

        "itens_por_status":
            list(itens_por_status),

        "criticos_por_conta":
            criticos_por_conta,

        "ultimos_relatorios":
            ultimos_relatorios,
    }

    return render(
        request,
        "dashboard/index.html",
        contexto,
    )