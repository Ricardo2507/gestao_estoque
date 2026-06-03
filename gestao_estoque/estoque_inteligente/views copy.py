from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView

from .forms import RelatorioEstoqueForm
from .models import ItemEstoque, RelatorioEstoque
from .parser import processar_relatorio


class RelatorioUploadView(LoginRequiredMixin, CreateView):
    form_class = RelatorioEstoqueForm
    template_name = "estoque_inteligente/upload_relatorio.html"
    success_url = reverse_lazy("estoque_inteligente:relatorio_list")

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "Relatório enviado com sucesso.",
        )

        return response


class RelatorioListView(LoginRequiredMixin, ListView):
    model = RelatorioEstoque
    template_name = "estoque_inteligente/lista_relatorios.html"
    context_object_name = "relatorios"

    def get_queryset(self):
        return RelatorioEstoque.objects.all().order_by("-data_envio")


class RelatorioDetailView(LoginRequiredMixin, DetailView):
    model = RelatorioEstoque
    template_name = "estoque_inteligente/detalhe_relatorio.html"
    context_object_name = "relatorio"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        status = self.request.GET.get("status")

        # IMPORTANTE:
        # Mostrar apenas itens ativos.
        # Isso mantém a tela consistente com o dashboard.
        itens = self.object.itens.filter(ativo=True)

        if status:
            itens = itens.filter(status=status)

        context["itens"] = itens
        context["status_atual"] = status

        return context


def processar_itens_relatorio(request, pk):
    relatorio = get_object_or_404(RelatorioEstoque, pk=pk)

    if not relatorio.arquivo_pdf:
        messages.error(
            request,
            "Este relatório não possui arquivo PDF para processamento.",
        )
        return redirect(
            "estoque_inteligente:relatorio_detail",
            pk=pk,
        )

    if relatorio.itens.filter(ativo=True).exists():
        messages.warning(
            request,
            (
                "Este relatório já possui itens processados. "
                "Para reprocessar, exclua o relatório e envie novamente."
            ),
        )
        return redirect(
            "estoque_inteligente:relatorio_detail",
            pk=pk,
        )

    try:
        itens = processar_relatorio(relatorio)

        contas = (
            relatorio.itens
            .filter(ativo=True)
            .exclude(conta_codigo="")
            .values("conta_codigo", "conta_descricao")
            .distinct()
        )

        quantidade_contas = contas.count()

        data_formatada = relatorio.data_envio.strftime("%d/%m/%Y")

        if quantidade_contas == 1:
            conta = contas.first()

            descricao_conta = (
                conta["conta_descricao"]
                or conta["conta_codigo"]
            )

            relatorio.nome_original = (
                f"Posição de {descricao_conta} - "
                f"{data_formatada}"
            )

        elif quantidade_contas > 1:
            relatorio.nome_original = (
                f"Posição de diversas contas - "
                f"{data_formatada}"
            )

        relatorio.save(update_fields=["nome_original"])

        messages.success(
            request,
            (
                f"{len(itens)} itens processados com sucesso. "
                "Os dados anteriores das mesmas contas "
                "foram marcados como inativos."
            ),
        )

    except Exception as exc:
        messages.error(
            request,
            f"Erro ao processar itens do relatório: {exc}",
        )

    return redirect(
        "estoque_inteligente:relatorio_detail",
        pk=pk,
    )


def restaurar_itens_anteriores(contas_afetadas):
    for conta in contas_afetadas:

        relatorio_anterior = (
            RelatorioEstoque.objects
            .filter(itens__conta_codigo=conta)
            .distinct()
            .order_by("-data_envio", "-id")
            .first()
        )

        if not relatorio_anterior:
            continue

        ItemEstoque.objects.filter(
            relatorio=relatorio_anterior,
            conta_codigo=conta,
        ).update(ativo=True)


class RelatorioDeleteView(LoginRequiredMixin, DeleteView):
    model = RelatorioEstoque
    template_name = (
        "estoque_inteligente/"
        "confirmar_exclusao_relatorio.html"
    )

    success_url = reverse_lazy(
        "estoque_inteligente:relatorio_list"
    )

    context_object_name = "relatorio"

    def form_valid(self, form):
        self.object = self.get_object()

        arquivo_pdf_path = (
            self.object.arquivo_pdf.path
            if self.object.arquivo_pdf
            else None
        )

        contas_afetadas = list(
            self.object.itens
            .exclude(conta_codigo="")
            .values_list(
                "conta_codigo",
                flat=True,
            )
            .distinct()
        )

        self.object.itens.all().delete()

        self.object.delete()

        restaurar_itens_anteriores(contas_afetadas)

        if arquivo_pdf_path:
            try:
                Path(arquivo_pdf_path).unlink(
                    missing_ok=True
                )

            except Exception:
                messages.warning(
                    self.request,
                    (
                        "Relatório excluído e itens "
                        "anteriores restaurados, mas "
                        "não foi possível apagar o "
                        "arquivo PDF do disco."
                    ),
                )

                return redirect(self.success_url)

        messages.success(
            self.request,
            (
                "Relatório excluído e itens "
                "anteriores restaurados "
                "com sucesso."
            ),
        )

        return redirect(self.success_url)