import re
from decimal import Decimal

import pdfplumber
from django.db import transaction

from .models import ItemConsumoMaterial


PADRAO_CODIGO_MATERIAL = re.compile(
    r"^(?P<codigo>\d{9})\s*-\s*(?P<descricao>.*)$"
)

PADRAO_DATA_GERACAO = re.compile(
    r"(?P<data>\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})"
)

PADRAO_PERIODO = re.compile(
    r"Período:\s*(?P<inicio>\d{2}/\d{4})\s*a\s*(?P<fim>\d{2}/\d{4})"
)

PADRAO_MESES = re.compile(r"\d{4}/\d{2}")

NUMERO_INTEIRO = r"\d+(?:\.\d{3})*"


def limpar_linha(linha):
    linha = linha.replace("\xa0", " ")
    linha = linha.replace("\uFFFE", "")
    linha = linha.replace("￾", "")
    linha = re.sub(r"\s+", " ", linha)
    return linha.strip()


def normalizar_decimal(valor):
    valor = str(valor or "").strip()

    if not valor:
        return Decimal("0")

    valor = valor.replace(".", "")
    valor = valor.replace(",", ".")

    try:
        return Decimal(valor)
    except Exception:
        return Decimal("0")


def normalizar_inteiro(valor):
    valor = str(valor or "").strip()

    if not valor:
        return Decimal("0")

    valor = valor.replace(".", "")

    try:
        return Decimal(valor)
    except Exception:
        return Decimal("0")


def converter_periodo(valor):
    if not valor or "/" not in valor:
        return valor or ""

    mes, ano = valor.split("/")
    return f"{ano}/{mes}"


def linha_ignorada(linha):
    textos = [
        "Ministério Público Federal",
        "Procuradoria da República",
        "Coordenadoria de Administração",
        "Consumo Mensal de Material",
        "Órgão:",
        "Almoxarifado:",
        "Material 2025/",
        "AX0095-AX0095.jasper",
        "Página ",
        "O relatório não respeita",
        "O relatório retorna",
    ]

    return any(texto in linha for texto in textos)


def extrair_texto_pdf(caminho_pdf):
    textos = []

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text(
                x_tolerance=1,
                y_tolerance=3,
            ) or ""

            textos.append(texto)

    return "\n".join(textos)


def extrair_meses(texto):
    for linha in texto.splitlines():
        linha = limpar_linha(linha)

        if linha.startswith("Material ") and "2025/" in linha:
            meses = PADRAO_MESES.findall(linha)

            if meses:
                return meses[:12]

    meses = []

    for mes in PADRAO_MESES.findall(texto):
        if mes not in meses:
            meses.append(mes)

    return meses[:12]


def extrair_metadados(texto, meses):
    data_geracao = ""
    periodo_inicio = ""
    periodo_fim = ""
    orgao_codigo = ""
    orgao_descricao = ""
    almoxarifado_codigo = ""
    almoxarifado_descricao = ""

    match_data = PADRAO_DATA_GERACAO.search(texto)

    if match_data:
        data_geracao = match_data.group("data")

    match_periodo = PADRAO_PERIODO.search(texto)

    if match_periodo:
        periodo_inicio = converter_periodo(match_periodo.group("inicio"))
        periodo_fim = converter_periodo(match_periodo.group("fim"))
    elif meses:
        periodo_inicio = meses[0]
        periodo_fim = meses[-1]

    if "001 - MINISTÉRIO PÚBLICO FEDERAL" in texto:
        orgao_codigo = "001"
        orgao_descricao = "MINISTÉRIO PÚBLICO FEDERAL"

    if "0025 - ALMOXARIFADO PR/PE" in texto:
        almoxarifado_codigo = "0025"
        almoxarifado_descricao = "ALMOXARIFADO PR/PE"

    return {
        "data_geracao": data_geracao,
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim,
        "orgao_codigo": orgao_codigo,
        "orgao_descricao": orgao_descricao,
        "almoxarifado_codigo": almoxarifado_codigo,
        "almoxarifado_descricao": almoxarifado_descricao,
    }


def separar_blocos_de_itens(texto):
    blocos = []
    bloco_atual = []

    for linha in texto.splitlines():
        linha = limpar_linha(linha)

        if not linha:
            continue

        if linha_ignorada(linha):
            continue

        if PADRAO_CODIGO_MATERIAL.match(linha):
            if bloco_atual:
                blocos.append(" ".join(bloco_atual))

            bloco_atual = [linha]
        else:
            if bloco_atual:
                bloco_atual.append(linha)

    if bloco_atual:
        blocos.append(" ".join(bloco_atual))

    return blocos


def montar_regex_item(qtd_meses):
    meses = rf"(?P<meses>(?:{NUMERO_INTEIRO}\s+){{{qtd_meses}}})"

    return re.compile(
        rf"^(?P<codigo>\d{{9}})\s*-\s*"
        rf"(?P<descricao_antes>.*?)\s+"
        rf"{meses}"
        rf"(?P<unidade_medida>[A-ZÇ]{{1,5}})\s+"
        rf"(?P<total>{NUMERO_INTEIRO})\s+"
        rf"(?P<cmp>{NUMERO_INTEIRO},\d{{4}})\s+"
        rf"(?P<saldo_atual>{NUMERO_INTEIRO})"
        rf"\s*(?P<descricao_depois>.*)$"
    )


def parsear_bloco_item(bloco, meses, metadados):
    bloco = limpar_linha(bloco)

    regex = montar_regex_item(len(meses))
    match = regex.match(bloco)

    if not match:
        return None

    valores_meses = match.group("meses").split()

    consumos_mensais = {}

    for mes, valor in zip(meses, valores_meses):
        consumos_mensais[mes] = str(normalizar_inteiro(valor))

    descricao_partes = [
        match.group("descricao_antes"),
        match.group("descricao_depois"),
    ]

    material_descricao = limpar_linha(
        " ".join(
            parte.strip()
            for parte in descricao_partes
            if parte and parte.strip()
        )
    )

    return {
        "orgao_codigo": metadados["orgao_codigo"],
        "orgao_descricao": metadados["orgao_descricao"],
        "almoxarifado_codigo": metadados["almoxarifado_codigo"],
        "almoxarifado_descricao": metadados["almoxarifado_descricao"],
        "material_codigo": match.group("codigo"),
        "material_descricao": material_descricao,
        "unidade_medida": match.group("unidade_medida"),
        "periodo_inicio": metadados["periodo_inicio"],
        "periodo_fim": metadados["periodo_fim"],
        "data_geracao": metadados["data_geracao"],
        "consumos_mensais": consumos_mensais,
        "total": normalizar_inteiro(match.group("total")),
        "cmp": normalizar_decimal(match.group("cmp")),
        "saldo_atual": normalizar_inteiro(match.group("saldo_atual")),
    }


def atualizar_nome_relatorio_consumo_material(relatorio, metadados):
    periodo_inicio = metadados.get("periodo_inicio") or ""
    periodo_fim = metadados.get("periodo_fim") or ""
    data_geracao = metadados.get("data_geracao") or ""

    data_simples = ""

    if data_geracao:
        data_simples = data_geracao.split(" ")[0]

    partes = ["Consumo mensal de material"]

    if periodo_inicio and periodo_fim:
        partes.append(f"{periodo_inicio} a {periodo_fim}")

    if data_simples:
        partes.append(data_simples)

    relatorio.nome_original = " - ".join(partes)
    relatorio.save(update_fields=["nome_original"])


@transaction.atomic
def processar_relatorio_consumo_material(relatorio):
    texto = extrair_texto_pdf(relatorio.arquivo_pdf.path)

    meses = extrair_meses(texto)

    if not meses:
        raise ValueError(
            "Não foi possível identificar os meses do relatório."
        )

    metadados = extrair_metadados(texto, meses)
    blocos = separar_blocos_de_itens(texto)

    itens_criados = []
    blocos_nao_processados = []

    relatorio.itens_consumo_material.all().delete()

    for bloco in blocos:
        dados = parsear_bloco_item(
            bloco=bloco,
            meses=meses,
            metadados=metadados,
        )

        if not dados:
            blocos_nao_processados.append(bloco)
            continue

        item = ItemConsumoMaterial.objects.create(
            relatorio=relatorio,
            **dados,
        )

        itens_criados.append(item)

    relatorio.texto_extraido = texto
    relatorio.save(update_fields=["texto_extraido"])

    atualizar_nome_relatorio_consumo_material(relatorio, metadados)

    # if blocos_nao_processados:
    #     print("=" * 80)
    #     print("Blocos não processados no consumo mensal de material:")
    #     print(f"Total não processado: {len(blocos_nao_processados)}")

    #     for bloco in blocos_nao_processados[:30]:
    #         print("-" * 80)
    #         print(bloco)

    # print("=" * 80)
    # print(f"Itens identificados no PDF: {len(blocos)}")
    # print(f"Itens gravados no banco: {len(itens_criados)}")
    # print(f"Itens não processados: {len(blocos_nao_processados)}")

    return itens_criados