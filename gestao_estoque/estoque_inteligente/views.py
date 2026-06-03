from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView

from .forms import RelatorioEstoqueForm
from .models import ItemEstoque, RelatorioEstoque
from .parser import processar_relatorio


class RelatorioUploadView(LoginRequiredMixin, CreateView):
    model = RelatorioEstoque
    form_class = RelatorioEstoqueForm
    template_name = "estoque_inteligente/upload_relatorio.html"

    def form_valid(self, form):
        self.object = form.save()

        try:
            itens = processar_relatorio(self.object)

            atualizar_nome_relatorio(self.object)

            messages.success(
                self.request,
                f"Relatório enviado e {len(itens)} itens processados com sucesso.",
            )

            return redirect(
                "estoque_inteligente:relatorio_detail",
                pk=self.object.pk,
            )

        except Exception as exc:
            messages.error(
                self.request,
                f"Erro ao processar relatório: {exc}",
            )

            return redirect(
                "estoque_inteligente:relatorio_list"
            )

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Erro ao enviar relatório."
        )

        return super().form_invalid(form)


class RelatorioListView(LoginRequiredMixin, ListView):
    model = RelatorioEstoque
    template_name = "estoque_inteligente/lista_relatorios.html"
    context_object_name = "relatorios"

    def get_queryset(self):
        return (
            RelatorioEstoque.objects
            .all()
            .order_by("-data_envio")
        )

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

    if relatorio.itens.exists():
        messages.warning(
            request,
            "Este relatório já possui itens processados.",
        )
        return redirect(
            "estoque_inteligente:relatorio_detail",
            pk=pk,
        )

    try:
        itens = processar_relatorio(relatorio)
        atualizar_nome_relatorio(relatorio)

        messages.success(
            request,
            f"{len(itens)} itens processados com sucesso.",
        )

    except Exception as exc:
        messages.error(
            request,
            f"Erro ao processar relatório: {exc}",
        )

    return redirect(
        "estoque_inteligente:relatorio_detail",
        pk=pk,
    )

class RelatorioDetailView(LoginRequiredMixin, DetailView):
    model = RelatorioEstoque
    template_name = "estoque_inteligente/detalhe_relatorio.html"
    context_object_name = "relatorio"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        status = self.request.GET.get("status")

        itens = self.object.itens.all()

        if status:
            itens = itens.filter(status=status)

        context["itens"] = itens
        context["status_atual"] = status

        return context


def atualizar_nome_relatorio(relatorio):
    contas = (
        relatorio.itens
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


def restaurar_itens_anteriores(pares_afetados):
    for conta_codigo, codigo_material in pares_afetados:

        ItemEstoque.objects.filter(
            conta_codigo=conta_codigo,
            codigo_material=codigo_material,
        ).update(ativo=False)

        item_anterior = (
            ItemEstoque.objects
            .filter(
                conta_codigo=conta_codigo,
                codigo_material=codigo_material,
            )
            .order_by(
                "-relatorio__data_envio",
                "-relatorio_id",
                "-id",
            )
            .first()
        )

        if not item_anterior:
            continue

        ItemEstoque.objects.filter(
            relatorio=item_anterior.relatorio,
            conta_codigo=conta_codigo,
            codigo_material=codigo_material,
        ).update(ativo=True)


class RelatorioDeleteView(LoginRequiredMixin, DeleteView):
    model = RelatorioEstoque
    template_name = "estoque_inteligente/confirmar_exclusao_relatorio.html"
    success_url = reverse_lazy("estoque_inteligente:relatorio_list")
    context_object_name = "relatorio"

    def form_valid(self, form):
        self.object = self.get_object()

        arquivo_pdf_path = (
            self.object.arquivo_pdf.path
            if self.object.arquivo_pdf
            else None
        )

        pares_afetados = list(
            self.object.itens
            .exclude(conta_codigo="")
            .exclude(codigo_material="")
            .values_list(
                "conta_codigo",
                "codigo_material",
            )
            .distinct()
        )

        with transaction.atomic():

            self.object.itens.all().delete()

            self.object.delete()

            restaurar_itens_anteriores(
                pares_afetados
            )

        if arquivo_pdf_path:
            try:
                Path(
                    arquivo_pdf_path
                ).unlink(
                    missing_ok=True
                )

            except Exception:
                messages.warning(
                    self.request,
                    (
                        "Relatório excluído e itens "
                        "anteriores restaurados, "
                        "mas não foi possível apagar "
                        "o PDF do disco."
                    ),
                )

                return redirect(
                    self.success_url
                )

        messages.success(
            self.request,
            (
                "Relatório excluído e itens "
                "anteriores restaurados "
                "com sucesso."
            ),
        )

        return redirect(
            self.success_url
        )

from .forms import RelatorioConsumoURForm
from .models import RelatorioConsumoUR
from .parser_consumo_ur import processar_relatorio_consumo_ur


class ConsumoURUploadView(LoginRequiredMixin, CreateView):
    model = RelatorioConsumoUR
    form_class = RelatorioConsumoURForm
    template_name = "estoque_inteligente/consumo_ur/upload.html"

    def form_valid(self, form):
        self.object = form.save()

        try:
            itens = processar_relatorio_consumo_ur(self.object)
            atualizar_nome_relatorio_consumo_ur(self.object)

            messages.success(
                self.request,
                f"Relatório de consumo por UR enviado e {len(itens)} linhas processadas com sucesso.",
            )

            return redirect(
                "estoque_inteligente:consumo_ur_detail",
                pk=self.object.pk,
            )

        except Exception as exc:
            messages.error(
                self.request,
                f"Erro ao processar relatório de consumo por UR: {exc}",
            )
            return redirect("estoque_inteligente:consumo_ur_list")

    def form_invalid(self, form):
        messages.error(self.request, "Erro ao enviar relatório de consumo por UR.")
        return super().form_invalid(form)


class ConsumoURListView(LoginRequiredMixin, ListView):
    model = RelatorioConsumoUR
    template_name = "estoque_inteligente/consumo_ur/lista.html"
    context_object_name = "relatorios"

    def get_queryset(self):
        return RelatorioConsumoUR.objects.all().order_by("-data_envio")


class ConsumoURDetailView(LoginRequiredMixin, DetailView):
    model = RelatorioConsumoUR
    template_name = "estoque_inteligente/consumo_ur/detalhe.html"
    context_object_name = "relatorio"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        material = self.request.GET.get("material", "").strip()
        ur = self.request.GET.get("ur", "").strip()

        itens = self.object.itens_consumo.all()

        if material:
            itens = itens.filter(material_codigo=material)

        if ur:
            itens = itens.filter(ur_codigo=ur)

        meses = []
        primeiro_item = self.object.itens_consumo.first()
        if primeiro_item:
            meses = list(primeiro_item.consumos_mensais.keys())

        context["itens"] = itens
        context["meses"] = meses
        context["material_atual"] = material
        context["ur_atual"] = ur
        context["materiais"] = (
            self.object.itens_consumo
            .values("material_codigo", "material_descricao")
            .distinct()
            .order_by("material_codigo")
        )
        context["urs"] = (
            self.object.itens_consumo
            .values("ur_codigo", "ur_descricao")
            .distinct()
            .order_by("ur_codigo")
        )

        return context


class ConsumoURDeleteView(LoginRequiredMixin, DeleteView):
    model = RelatorioConsumoUR
    template_name = "estoque_inteligente/consumo_ur/confirmar_exclusao.html"
    success_url = reverse_lazy("estoque_inteligente:consumo_ur_list")
    context_object_name = "relatorio"

    def form_valid(self, form):
        self.object = self.get_object()
        arquivo_pdf_path = self.object.arquivo_pdf.path if self.object.arquivo_pdf else None

        with transaction.atomic():
            self.object.itens_consumo.all().delete()
            self.object.delete()

        if arquivo_pdf_path:
            try:
                Path(arquivo_pdf_path).unlink(missing_ok=True)
            except Exception:
                messages.warning(
                    self.request,
                    "Relatório excluído, mas não foi possível apagar o PDF do disco.",
                )
                return redirect(self.success_url)

        messages.success(self.request, "Relatório de consumo por UR excluído com sucesso.")
        return redirect(self.success_url)


def atualizar_nome_relatorio_consumo_ur(relatorio):
    primeiro = relatorio.itens_consumo.first()
    data_formatada = relatorio.data_envio.strftime("%d/%m/%Y")

    if primeiro:
        relatorio.nome_original = (
            f"Consumo por UR - {primeiro.periodo_inicio} a {primeiro.periodo_fim} - {data_formatada}"
        )
        relatorio.save(update_fields=["nome_original"])
