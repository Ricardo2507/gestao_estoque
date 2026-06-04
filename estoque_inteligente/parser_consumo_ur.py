import re
from decimal import Decimal

import pdfplumber

from .models import ItemConsumoUR


MESES_REGEX = re.compile(r"20\d{2}/\d{2}")
UR_REGEX = re.compile(r"^(\d{4})\s*-\s*(.+)")
NUMERO_REGEX = re.compile(r"^\d+(?:\.\d{3})*(?:,\d+)?$")


def normalizar_decimal(valor):
    if not valor:
        return Decimal("0")

    valor = str(valor).strip()
    valor = valor.replace(".", "")
    valor = valor.replace(",", ".")

    try:
        return Decimal(valor)
    except Exception:
        return Decimal("0")


def extrair_material(linha):
    match = re.search(
        r"Material:\s*(\d{6,})\s*-\s*(.+?)\s+UM:\s*([A-Z]+)",
        linha,
    )

    if not match:
        return "", "", ""

    return (
        match.group(1).strip(),
        match.group(2).strip(),
        match.group(3).strip(),
    )


def extrair_periodo(linha):
    match = re.search(
        r"Período:\s*(\d{4}/\d{2})\s*a\s*(\d{4}/\d{2})",
        linha,
    )

    if not match:
        return "", ""

    return match.group(1), match.group(2)


def separar_linha_ur(linha_ur):
    match = UR_REGEX.match(linha_ur)

    if not match:
        return "", "", []

    ur_codigo = match.group(1).strip()
    restante = match.group(2).strip()
    partes = restante.split()

    posicao_primeiro_numero = None

    for posicao, parte in enumerate(partes):
        if NUMERO_REGEX.fullmatch(parte):
            posicao_primeiro_numero = posicao
            break

    if posicao_primeiro_numero is None:
        return ur_codigo, restante, []

    descricao = " ".join(
        partes[:posicao_primeiro_numero]
    ).strip()

    valores = [
        parte
        for parte in partes[posicao_primeiro_numero:]
        if NUMERO_REGEX.fullmatch(parte)
    ]

    return ur_codigo, descricao, valores


def linha_complemento_ur(linha):
    if not linha:
        return False

    if UR_REGEX.match(linha):
        return False

    if linha.startswith("*"):
        return False

    if "AX0126" in linha:
        return False

    if linha.startswith("Ministério Público Federal"):
        return False

    if linha.startswith("Procuradoria da República"):
        return False

    if linha.startswith("Coordenadoria de Administração"):
        return False

    if linha.startswith("Consumo Mensal"):
        return False

    if linha.startswith("Órgão:"):
        return False

    if linha.startswith("Material:"):
        return False

    if linha.startswith("U.R."):
        return False

    if linha.startswith("Período:"):
        return False

    if linha.startswith("UM:"):
        return False

    if all(NUMERO_REGEX.fullmatch(parte) for parte in linha.split()):
        return False

    return True


def limpar_descricao_ur(descricao):
    descricao = re.sub(r"\s+", " ", descricao or "").strip()

    while descricao.endswith(" 0"):
        descricao = descricao[:-2].strip()

    return descricao


def calcular_total_consumo(consumo_mensal):
    total = Decimal("0")

    for valor in consumo_mensal.values():
        total += normalizar_decimal(valor)

    return total


def processar_relatorio_consumo_ur(relatorio):
    itens_criados = []
    texto_completo = ""

    material_codigo = ""
    material_descricao = ""
    unidade_medida = ""
    periodo_inicio = ""
    periodo_fim = ""
    meses = []

    relatorio.itens_consumo.all().delete()

    with pdfplumber.open(relatorio.arquivo_pdf.path) as pdf:

        for page in pdf.pages:
            texto = page.extract_text() or ""
            texto_completo += texto + "\n"

            linhas = [
                linha.strip()
                for linha in texto.splitlines()
                if linha.strip()
            ]

            indice = 0

            while indice < len(linhas):
                linha = linhas[indice]

                if "Período:" in linha:
                    inicio, fim = extrair_periodo(linha)

                    if inicio:
                        periodo_inicio = inicio
                        periodo_fim = fim

                if "Material:" in linha:
                    codigo, descricao, um = extrair_material(linha)

                    if codigo:
                        material_codigo = codigo
                        material_descricao = descricao
                        unidade_medida = um

                if linha.startswith("U.R."):
                    meses = MESES_REGEX.findall(linha)

                match_ur = UR_REGEX.match(linha)

                if not match_ur:
                    indice += 1
                    continue

                ur_codigo, ur_descricao, valores = separar_linha_ur(linha)

                complemento = ""

                proximo_indice = indice + 1

                if proximo_indice < len(linhas):
                    proxima_linha = linhas[proximo_indice].strip()

                    if linha_complemento_ur(proxima_linha):
                        complemento = proxima_linha
                        indice += 1

                if complemento:
                    ur_descricao = f"{ur_descricao} {complemento}".strip()

                ur_descricao = limpar_descricao_ur(ur_descricao)

                if not meses:
                    indice += 1
                    continue

                if len(valores) < len(meses) + 1:
                    indice += 1
                    continue

                consumo_mensal = {}

                valores_meses = valores[:len(meses)]

                for mes, valor in zip(meses, valores_meses):
                    consumo_mensal[mes] = str(normalizar_decimal(valor))

                # Correção importante:
                # O PDF às vezes quebra totais grandes, por exemplo:
                # 1.159,000
                # 0
                #
                # Nesses casos o parser antigo gravava como total apenas
                # o último mês, como 130, em vez de 1159.
                #
                # Para garantir consistência, o total passa a ser sempre
                # calculado pela soma dos 12 meses.
                total = calcular_total_consumo(consumo_mensal)

                # O CMP continua sendo lido do último número da linha,
                # pois ele não sofre o mesmo problema prático observado.
                cmp = normalizar_decimal(valores[-1])

                item = ItemConsumoUR.objects.create(
                    relatorio=relatorio,
                    material_codigo=material_codigo,
                    material_descricao=material_descricao,
                    unidade_medida=unidade_medida,
                    periodo_inicio=periodo_inicio,
                    periodo_fim=periodo_fim,
                    ur_codigo=ur_codigo,
                    ur_descricao=ur_descricao,
                    consumos_mensais=consumo_mensal,
                    total=total,
                    cmp=cmp,
                )

                itens_criados.append(item)

                indice += 1

    relatorio.texto_extraido = texto_completo
    relatorio.save(update_fields=["texto_extraido"])

    return itens_criados