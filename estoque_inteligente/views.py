from pathlib import Path

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView

from .forms import RelatorioEstoqueForm
from .models import RelatorioEstoque
from .parser import processar_relatorio

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

class RelatorioUploadView(LoginRequiredMixin, CreateView):
   
    form_class = RelatorioEstoqueForm  #Diz ao Django qual formulário (definido no seu arquivo forms.py) deve ser usado nesta página. 
    template_name = "estoque_inteligente/upload_relatorio.html" # Define o caminho do arquivo HTML que será exibido para o usuário. É a "cara" da sua página.
    success_url = reverse_lazy("estoque_inteligente:relatorio_list") #success_url: É o endereço para onde o usuário será enviado após o upload dar certo.
    #reverse_lazy: É uma função de "espera". Ela diz ao Django: "Não tente 
    # descobrir o link agora, espere até que o sistema de URLs esteja totalmente carregado e 
    # o formulário seja enviado com sucesso".
    
    def form_valid(self, form):
        # import pdb; pdb.set_trace() # Para aqui ao abrir o link
        response = super().form_valid(form)
        messages.success(self.request, "Relatório enviado com sucesso.")
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
        itens = self.object.itens.all()

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
        return redirect("estoque_inteligente:relatorio_detail", pk=pk)

    if relatorio.itens.exists():
        messages.warning(
            request,
            "Este relatório já possui itens processados. Para reprocessar, exclua o relatório e envie novamente.",
        )
        return redirect("estoque_inteligente:relatorio_detail", pk=pk)

    try:
        itens = processar_relatorio(relatorio)

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
            descricao_conta = conta["conta_descricao"] or conta["conta_codigo"]
            relatorio.nome_original = f"Posição de {descricao_conta} - {data_formatada}"
        elif quantidade_contas > 1:
            relatorio.nome_original = f"Posição de diversas contas - {data_formatada}"

        relatorio.save(update_fields=["nome_original"])

        messages.success(
            request,
            f"{len(itens)} itens processados com sucesso. Os dados anteriores das mesmas contas foram marcados como inativos.",
        )

    except Exception as exc:
        messages.error(
            request,
            f"Erro ao processar itens do relatório: {exc}",
        )

    return redirect("estoque_inteligente:relatorio_detail", pk=pk)


class RelatorioDeleteView(DeleteView):
    model = RelatorioEstoque
    template_name = "estoque_inteligente/confirmar_exclusao_relatorio.html"
    success_url = reverse_lazy("estoque_inteligente:relatorio_list")
    context_object_name = "relatorio"

    def form_valid(self, form):
        self.object = self.get_object()
        arquivo_pdf_path = self.object.arquivo_pdf.path if self.object.arquivo_pdf else None

        response = super().form_valid(form)

        if arquivo_pdf_path:
            try:
                Path(arquivo_pdf_path).unlink(missing_ok=True)
            except Exception:
                messages.warning(
                    self.request,
                    "Relatório excluído, mas não foi possível apagar o arquivo PDF do disco.",
                )
            else:
                messages.success(
                    self.request,
                    "Relatório e arquivo PDF excluídos com sucesso.",
                )
                return response

        messages.success(self.request, "Relatório excluído com sucesso.")
        return response