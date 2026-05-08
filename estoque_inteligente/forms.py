import hashlib

from django import forms

from .models import RelatorioEstoque


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
      
        hash_arquivo = calcular_hash_arquivo(arquivo)
      
        if RelatorioEstoque.objects.filter(hash_arquivo=hash_arquivo).exists():
          
            raise forms.ValidationError(
                "Este relatório já foi enviado anteriormente e não será duplicado."
            )

        self.hash_arquivo = hash_arquivo
        return arquivo

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.nome_original = self.cleaned_data["arquivo_pdf"].name
        instance.hash_arquivo = getattr(self, "hash_arquivo", "")
        self.ocr_error = ""

        if commit:
            instance.save()

        return instance