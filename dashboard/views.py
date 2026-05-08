from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import render

from estoque_inteligente.models import ItemEstoque, RelatorioEstoque


def dashboard_home(request):
    #import pdb; pdb.set_trace()
    itens_ativos = ItemEstoque.objects.filter(ativo=True)

    total_relatorios = RelatorioEstoque.objects.count()
    total_itens = itens_ativos.count()

    total_criticos = itens_ativos.filter(status="CRITICO").count()
    total_atencao = itens_ativos.filter(status="ATENCAO").count()
    total_normais = itens_ativos.filter(status="NORMAL").count()
    total_sem_movimento = itens_ativos.filter(status="SEM_MOVIMENTO").count()
    total_estoque_parado = itens_ativos.filter(status="ESTOQUE_PARADO").count()

    valor_total_estoque = itens_ativos.aggregate(
        total=Sum("valor")
    )["total"] or Decimal("0")

    total_sugerido_compra = itens_ativos.aggregate(
        total=Sum("quantidade_sugerida")
    )["total"] or Decimal("0")

    itens_por_status = (
        itens_ativos
        .values("status")
        .annotate(total=Count("id"))
        .order_by("status")
    )

    criticos_por_conta = (
        itens_ativos
        .filter(status="CRITICO")
        .values("conta_codigo", "conta_descricao")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    ultimos_relatorios = RelatorioEstoque.objects.order_by("-data_envio")[:5]

    contexto = {
        "total_relatorios": total_relatorios,
        "total_itens": total_itens,
        "total_criticos": total_criticos,
        "total_atencao": total_atencao,
        "total_normais": total_normais,
        "total_sem_movimento": total_sem_movimento,
        "total_estoque_parado": total_estoque_parado,
        "valor_total_estoque": valor_total_estoque,
        "total_sugerido_compra": total_sugerido_compra,
        "itens_por_status": list(itens_por_status),
        "criticos_por_conta": criticos_por_conta,
        "ultimos_relatorios": ultimos_relatorios,
    }

    return render(request, "dashboard/index.html", contexto)