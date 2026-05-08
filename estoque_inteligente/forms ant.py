import logging
import os

from django import forms
from pdf2image import convert_from_path
import pytesseract

from .models import RelatorioEstoque

logger = logging.getLogger(__name__)

TESSERACT_CMD = r"E:\tesseract\tesseract.exe"
TESSDATA_DIR = r"E:\tesseract\tessdata"
POPPLER_PATH = r"E:\Poppler\poppler-25.12.0\Library\bin"


class RelatorioEstoqueForm(forms.ModelForm):
    class Meta:
        model = RelatorioEstoque
        fields = ["arquivo_pdf"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.nome_original = self.cleaned_data["arquivo_pdf"].name
        self.ocr_error = ""

        if commit:
            instance.save()

            texto_extraido, erro_ocr = self._extrair_texto_pdf(
                instance.arquivo_pdf.path
            )

            instance.texto_extraido = texto_extraido
            instance.save(update_fields=["texto_extraido"])

            self.ocr_error = erro_ocr

        return instance

    def _extrair_texto_pdf(self, caminho_pdf):
        try:
            if not os.path.exists(TESSERACT_CMD):
                return (
                    "",
                    f"Tesseract não encontrado em: {TESSERACT_CMD}",
                )

            if not os.path.exists(TESSDATA_DIR):
                return (
                    "",
                    f"Diretório tessdata não encontrado em: {TESSDATA_DIR}",
                )

            if not os.path.exists(os.path.join(TESSDATA_DIR, "por.traineddata")):
                return (
                    "",
                    f"Arquivo por.traineddata não encontrado em: {TESSDATA_DIR}",
                )

            if not os.path.exists(POPPLER_PATH):
                return (
                    "",
                    f"Poppler não encontrado em: {POPPLER_PATH}",
                )

            if not os.path.exists(caminho_pdf):
                return "", "Arquivo PDF não encontrado para OCR."

            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
            os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

            imagens = convert_from_path(
                caminho_pdf,
                poppler_path=POPPLER_PATH,
                dpi=300,
            )

            textos = []

            for imagem in imagens:
                texto_pagina = pytesseract.image_to_string(
                    imagem,
                    lang="por",
                    config="--psm 6",
                )
                textos.append(texto_pagina or "")

            texto_final = "\n\n".join(textos).strip()

            if not texto_final:
                return "", "OCR executado, mas nenhum texto foi reconhecido no PDF."

            return texto_final, ""

        except Exception as exc:
            logger.exception("Falha ao extrair texto por OCR do arquivo %s", caminho_pdf)
            return "", f"OCR falhou: {exc}"