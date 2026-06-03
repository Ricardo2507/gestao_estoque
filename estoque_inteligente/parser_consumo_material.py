import re
from decimal import Decimal

import pdfplumber

from .models import ItemConsumoMaterial


MESES_REGEX = re.compile(r"20\d{2}/\d{2}")
ITEM_REGEX = re.compile(r"^(\d{6,})\s*-\s*(.+)")
NUMERO_REGEX = re.compile(r"^\d+(?:\.\d{3})*(?:,\d+)?$|^\d+(?:,\d+)?$")
UM_VALIDAS = {
    "UN", "KG", "PCT", "PC", "CX", "FR", "RO", "L", "BIS", "BL",
    "RL", "LT", "M", "MT", "GL", "PAR", "JG", "PÇ", "UND",
}


def normalizar_decimal(valor):
    if not valor:
        return Decimal("0")

    valor = str(valor).strip().replace(".", "").replace(",", ".")

    try:
        return Decimal(valor)
    except Exception:
        return Decimal("0")


def eh_numero(token):
    return bool(NUMERO_REGEX.fullmatch(token.strip()))


def eh_um(token):
    return token.strip().upper() in UM_VALIDAS


def extrair_periodo(texto):
    match = re.search(
        r"Período:\s*(\d{2}/\d{4}|\d{4}/\d{2})\s*a\s*(\d{2}/\d{4}|\d{4}/\d{2})",
        texto,
    )

    if not match:
        return "", ""

    return match.group(1), match.group(2)


def extrair_data_geracao(texto):
    match = re.search(r"\b\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\b", texto)

    if not match:
        return ""

    return match.group(0)


def extrair_orgao(texto):
    match = re.search(
        r"Órgão:\s*(\d+)\s*-\s*(.+?)(?:\s+Período:|\n|$)",
        texto,
        re.S,
    )

    if not match:
        return "", ""

    return match.group(1).strip(), " ".join(match.group(2).split())


def extrair_almoxarifado(texto):
    match = re.search(
        r"Almoxarifado:\s*(\d+)\s*-\s*(.+?)(?:\s+Período:|\n|$)",
        texto,
        re.S,
    )

    if not match:
        return "", ""

    return match.group(1).strip(), " ".join(match.group(2).split())


def linha_ignorada(linha):
    if not linha:
        return True

    prefixos = (
        "Ministério Público Federal",
        "Procuradoria da República",
        "Coordenadoria de Administração",
        "Consumo Mensal de Material",
        "Órgão:",
        "Almoxarifado:",
        "Período:",
        "Material 2025/",
        "AX0095",
        "* ",
    )

    return linha.startswith(prefixos)


def separar_item(texto_item):
    match = ITEM_REGEX.match(texto_item.strip())

    if not match:
        return None

    codigo = match.group(1).strip()
    restante = match.group(2).strip()
    partes = restante.split()

    # Estrutura final esperada:
    # 12 meses + U.M. + Total + CMP + Saldo Atual
    for indice_um in range(len(partes) - 4, 11, -1):
        um = partes[indice_um].upper()

        if not eh_um(um):
            continue

        if indice_um + 3 >= len(partes):
            continue

        total_token = partes[indice_um + 1]
        cmp_token = partes[indice_um + 2]
        saldo_token = partes[indice_um + 3]

        if not (
            eh_numero(total_token)
            and eh_numero(cmp_token)
            and eh_numero(saldo_token)
        ):
            continue

        valores_meses = partes[indice_um - 12:indice_um]

        if len(valores_meses) != 12:
            continue

        if not all(eh_numero(valor) for valor in valores_meses):
            continue

        descricao_partes = partes[:indice_um - 12]
        complemento_partes = partes[indice_um + 4:]

        descricao = " ".join(
            descricao_partes + complemento_partes
        ).strip()

        if not descricao:
            continue

        return {
            "codigo": codigo,
            "descricao": descricao,
            "valores_meses": valores_meses,
            "unidade_medida": um,
            "total": total_token,
            "cmp": cmp_token,
            "saldo_atual": saldo_token,
        }

    return None


def processar_relatorio_consumo_material(relatorio):
    itens_criados = []
    texto_completo = ""

    orgao_codigo = ""
    orgao_descricao = ""
    almoxarifado_codigo = ""
    almoxarifado_descricao = ""
    periodo_inicio = ""
    periodo_fim = ""
    data_geracao = ""
    meses = []

    with pdfplumber.open(relatorio.arquivo_pdf.path) as pdf:
        total_paginas = len(pdf.pages)

        for numero_pagina in range(total_paginas):
            page = pdf.pages[numero_pagina]

            try:
                texto = page.extract_text() or ""
            except Exception:
                texto = ""

            texto_completo += texto + "\n"

            if not data_geracao:
                data_geracao = extrair_data_geracao(texto)

            if not periodo_inicio:
                periodo_inicio, periodo_fim = extrair_periodo(texto)

            if not orgao_codigo:
                orgao_codigo, orgao_descricao = extrair_orgao(texto)

            if not almoxarifado_codigo:
                almoxarifado_codigo, almoxarifado_descricao = extrair_almoxarifado(texto)

            linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
            buffer_item = ""

            for linha in linhas:
                if linha.startswith("Material "):
                    meses_encontrados = MESES_REGEX.findall(linha)
                    if meses_encontrados:
                        meses = meses_encontrados
                    continue

                if linha_ignorada(linha):
                    continue

                if ITEM_REGEX.match(linha):
                    if buffer_item:
                        dados = separar_item(buffer_item)
                        if dados:
                            consumo_mensal = {}
                            for mes, valor in zip(meses, dados["valores_meses"]):
                                consumo_mensal[mes] = str(normalizar_decimal(valor))

                            item = ItemConsumoMaterial.objects.create(
                                relatorio=relatorio,
                                orgao_codigo=orgao_codigo,
                                orgao_descricao=orgao_descricao,
                                almoxarifado_codigo=almoxarifado_codigo,
                                almoxarifado_descricao=almoxarifado_descricao,
                                material_codigo=dados["codigo"],
                                material_descricao=dados["descricao"],
                                unidade_medida=dados["unidade_medida"],
                                periodo_inicio=periodo_inicio,
                                periodo_fim=periodo_fim,
                                data_geracao=data_geracao,
                                consumos_mensais=consumo_mensal,
                                total=normalizar_decimal(dados["total"]),
                                cmp=normalizar_decimal(dados["cmp"]),
                                saldo_atual=normalizar_decimal(dados["saldo_atual"]),
                            )
                            itens_criados.append(item)

                    buffer_item = linha

                elif buffer_item:
                    buffer_item += " " + linha

            if buffer_item:
                dados = separar_item(buffer_item)
                if dados:
                    consumo_mensal = {}
                    for mes, valor in zip(meses, dados["valores_meses"]):
                        consumo_mensal[mes] = str(normalizar_decimal(valor))

                    item = ItemConsumoMaterial.objects.create(
                        relatorio=relatorio,
                        orgao_codigo=orgao_codigo,
                        orgao_descricao=orgao_descricao,
                        almoxarifado_codigo=almoxarifado_codigo,
                        almoxarifado_descricao=almoxarifado_descricao,
                        material_codigo=dados["codigo"],
                        material_descricao=dados["descricao"],
                        unidade_medida=dados["unidade_medida"],
                        periodo_inicio=periodo_inicio,
                        periodo_fim=periodo_fim,
                        data_geracao=data_geracao,
                        consumos_mensais=consumo_mensal,
                        total=normalizar_decimal(dados["total"]),
                        cmp=normalizar_decimal(dados["cmp"]),
                        saldo_atual=normalizar_decimal(dados["saldo_atual"]),
                    )
                    itens_criados.append(item)

            try:
                page.close()
            except Exception:
                pass

            del page

    relatorio.texto_extraido = texto_completo
    relatorio.save(update_fields=["texto_extraido"])

    return itens_criados
