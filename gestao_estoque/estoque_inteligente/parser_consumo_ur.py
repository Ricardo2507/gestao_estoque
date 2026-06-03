import re
from decimal import Decimal, InvalidOperation

import pdfplumber
from django.db import transaction

from .models import ItemConsumoUR


CODIGO_RELATORIO_CONSUMO_UR = "AX0126-AX0126.jasper"


def limpar_texto(valor):
    return " ".join(str(valor or "").replace("\n", " ").split()).strip()


def para_decimal(valor):
    texto = limpar_texto(valor)
    if not texto:
        return Decimal("0")

    texto = texto.replace(".", "").replace(",", ".")

    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def separar_codigo_descricao(texto):
    texto = limpar_texto(texto)
    match = re.match(r"^(\d+)\s*-\s*(.+)$", texto)
    if not match:
        return "", texto

    return match.group(1).strip(), match.group(2).strip()


def separar_ur(texto):
    texto = limpar_texto(texto)
    match = re.match(r"^(\d+)\s*-\s*(.+)$", texto)
    if not match:
        return "", texto

    return match.group(1).strip(), match.group(2).strip()


def extrair_metadados_pagina(page):
    texto = page.extract_text() or ""

    orgao_codigo = ""
    orgao_descricao = ""
    material_codigo = ""
    material_descricao = ""
    unidade_medida = ""
    periodo_inicio = ""
    periodo_fim = ""
    data_geracao = ""

    match_data = re.search(r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", texto)
    if match_data:
        data_geracao = match_data.group(1)

    match_orgao = re.search(
        r"Órgão:\s*(\d+)\s*-\s*(.+?)\s+Período:",
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    if match_orgao:
        orgao_codigo = limpar_texto(match_orgao.group(1))
        orgao_descricao = limpar_texto(match_orgao.group(2))

    match_periodo = re.search(
        r"Período:\s*(\d{4}/\d{2})\s*a\s*(\d{4}/\d{2})",
        texto,
        re.IGNORECASE,
    )
    if match_periodo:
        periodo_inicio = match_periodo.group(1)
        periodo_fim = match_periodo.group(2)

    match_material = re.search(
        r"Material:\s*(\d+)\s*-\s*(.+?)\s+UM:\s*(.+?)(?:\n|U\.R\.)",
        texto,
        re.IGNORECASE | re.DOTALL,
    )
    if match_material:
        material_codigo = limpar_texto(match_material.group(1))
        material_descricao = limpar_texto(match_material.group(2))
        unidade_medida = limpar_texto(match_material.group(3))

    return {
        "orgao_codigo": orgao_codigo,
        "orgao_descricao": orgao_descricao,
        "material_codigo": material_codigo,
        "material_descricao": material_descricao,
        "unidade_medida": unidade_medida,
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim,
        "data_geracao": data_geracao,
    }


def extrair_itens_consumo_ur(caminho_pdf):
    itens = []

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 3,
        "text_tolerance": 3,
    }

    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            metadados = extrair_metadados_pagina(page)

            if not metadados["material_codigo"]:
                continue

            tabelas = page.extract_tables(table_settings=table_settings)

            for tabela in tabelas:
                if not tabela or len(tabela) < 2:
                    continue

                cabecalho = [limpar_texto(c) for c in tabela[0]]
                if not cabecalho or cabecalho[0].upper() != "U.R.":
                    continue

                meses = cabecalho[1:-2]

                for row in tabela[1:]:
                    if not row or len(row) < 4:
                        continue

                    row = [limpar_texto(c) for c in row]
                    ur_codigo, ur_descricao = separar_ur(row[0])

                    if not ur_codigo:
                        continue

                    consumos = {}
                    for indice, mes in enumerate(meses, start=1):
                        consumos[mes] = str(para_decimal(row[indice] if indice < len(row) else "0"))

                    itens.append(
                        {
                            **metadados,
                            "ur_codigo": ur_codigo,
                            "ur_descricao": ur_descricao,
                            "consumos_mensais": consumos,
                            "total": para_decimal(row[-2]),
                            "cmp": para_decimal(row[-1]),
                        }
                    )

    return itens


def processar_relatorio_consumo_ur(relatorio):
    itens_extraidos = extrair_itens_consumo_ur(relatorio.arquivo_pdf.path)

    with transaction.atomic():
        relatorio.itens_consumo.all().delete()

        objetos = [
            ItemConsumoUR(relatorio=relatorio, **item)
            for item in itens_extraidos
        ]

        ItemConsumoUR.objects.bulk_create(objetos, batch_size=500)

    return itens_extraidos
