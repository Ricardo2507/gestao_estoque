import hashlib

import pdfplumber

from django import forms
from django.core.exceptions import ValidationError

from .models import RelatorioConsumoUR, RelatorioEstoque


CODIGO_RELATORIO_VALIDO = "AX0003.P-AX0003P"


def calcular_hash_arquivo(arquivo):
    sha256 = hashlib.sha256()

    for chunk in arquivo.chunks():
        sha256.update(chunk)

    arquivo.seek(0)

    return sha256.hexdigest()


class RelatorioEstoqueForm(forms.ModelForm):

    class Meta:
        model = RelatorioEstoque
        fields = ["arquivo_pdf"]

    def clean_arquivo_pdf(self):

        arquivo = self.cleaned_data["arquivo_pdf"]

        # -----------------------------------------
        # VALIDAR EXTENSÃO
        # -----------------------------------------

        if not arquivo.name.lower().endswith(".pdf"):

            raise ValidationError(
                "Envie apenas arquivos PDF."
            )

        # -----------------------------------------
        # VALIDAR HASH DUPLICADO
        # -----------------------------------------

        hash_arquivo = calcular_hash_arquivo(arquivo)

        if RelatorioEstoque.objects.filter(
            hash_arquivo=hash_arquivo
        ).exists():

            raise ValidationError(
                "Este relatório já foi enviado anteriormente e não será duplicado."
            )

        # -----------------------------------------
        # VALIDAR ESTRUTURA DO PDF
        # -----------------------------------------

        try:

            texto_pdf = ""

            with pdfplumber.open(arquivo) as pdf:

                for page in pdf.pages[:3]:

                    texto_pdf += (
                        page.extract_text() or ""
                    )

        except Exception:

            raise ValidationError(
                "Não foi possível ler o PDF enviado."
            )

        # -----------------------------------------
        # VALIDAR CÓDIGO DO RELATÓRIO
        # -----------------------------------------

        if CODIGO_RELATORIO_VALIDO not in texto_pdf:

            raise ValidationError(
                "Relatório inválido. "
                "Envie apenas o relatório oficial "
                "de posição de estoque "
                "(AX0003.P-AX0003P)."
            )

        # -----------------------------------------
        # RESETAR PONTEIRO DO ARQUIVO
        # -----------------------------------------

        arquivo.seek(0)

        self.hash_arquivo = hash_arquivo

        return arquivo

    def save(self, commit=True):

        instance = super().save(commit=False)

        instance.nome_original = (
            self.cleaned_data["arquivo_pdf"].name
        )

        instance.hash_arquivo = getattr(
            self,
            "hash_arquivo",
            "",
        )

        self.ocr_error = ""

        if commit:
            instance.save()

        return instance

CODIGO_RELATORIO_CONSUMO_UR_VALIDO = "AX0126-AX0126.jasper"


class RelatorioConsumoURForm(forms.ModelForm):

    class Meta:
        model = RelatorioConsumoUR
        fields = ["arquivo_pdf"]

    def clean_arquivo_pdf(self):
        arquivo = self.cleaned_data["arquivo_pdf"]

        if not arquivo.name.lower().endswith(".pdf"):
            raise ValidationError("Envie apenas arquivos PDF.")

        hash_arquivo = calcular_hash_arquivo(arquivo)

        if RelatorioConsumoUR.objects.filter(hash_arquivo=hash_arquivo).exists():
            raise ValidationError(
                "Este relatório de consumo por UR já foi enviado anteriormente."
            )

        try:
            texto_pdf = ""
            with pdfplumber.open(arquivo) as pdf:
                for page in pdf.pages[:3]:
                    texto_pdf += page.extract_text() or ""
        except Exception:
            raise ValidationError("Não foi possível ler o PDF enviado.")

        if CODIGO_RELATORIO_CONSUMO_UR_VALIDO not in texto_pdf:
            raise ValidationError(
                "Relatório inválido. Envie apenas o relatório oficial de "
                "Consumo Mensal de Material por Unidade Requisitante "
                "(AX0126-AX0126.jasper)."
            )

        arquivo.seek(0)
        self.hash_arquivo = hash_arquivo
        return arquivo

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.nome_original = self.cleaned_data["arquivo_pdf"].name
        instance.hash_arquivo = getattr(self, "hash_arquivo", "")

        if commit:
            instance.save()

        return instance
