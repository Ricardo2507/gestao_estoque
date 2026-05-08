import re
from decimal import Decimal, InvalidOperation, ROUND_CEILING

import pdfplumber

from .models import ItemEstoque


STATUS_CRITICO = "CRITICO"
STATUS_ATENCAO = "ATENCAO"
STATUS_NORMAL = "NORMAL"
STATUS_SEM_MOVIMENTO = "SEM_MOVIMENTO"
STATUS_ESTOQUE_PARADO = "ESTOQUE_PARADO"


def limpar_texto(valor):
    if valor is None:
        return ""

    valor = str(valor)
    valor = valor.replace("\n", " ")
    valor = re.sub(r"\s+", " ", valor)
    return valor.strip()


def para_decimal(valor):
    valor = limpar_texto(valor)

    if not valor:
        return Decimal("0")

    valor = valor.replace("R$", "").strip()

    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    elif re.match(r"^\d{1,3}\.\d{3}$", valor):
        valor = valor.replace(".", "")

    try:
        return Decimal(valor)
    except InvalidOperation:
        return Decimal("0")


def detectar_status(cmm, ce, estoque):
    if estoque == 0 and cmm > 0:
        return STATUS_CRITICO

    if ce > 0 and ce <= 30:
        return STATUS_CRITICO

    if ce > 30 and ce <= 90:
        return STATUS_ATENCAO

    if ce > 90:
        return STATUS_NORMAL

    if cmm == 0 and estoque == 0:
        return STATUS_SEM_MOVIMENTO

    if cmm == 0 and estoque > 0:
        return STATUS_ESTOQUE_PARADO

    return STATUS_SEM_MOVIMENTO


def calcular_quantidade_sugerida(cmm, estoque):
    quantidade = (cmm * Decimal("3")) - estoque

    if quantidade <= 0:
        return Decimal("0")

    return quantidade.quantize(Decimal("1"), rounding=ROUND_CEILING)


def separar_codigo_descricao(material):
    material = limpar_texto(material)
    match = re.match(r"^(\d{6,12})\s*-\s*(.+)$", material)

    if match:
        return match.group(1), limpar_texto(match.group(2))

    return "", material


def extrair_conta_de_texto(texto):
    texto = limpar_texto(texto)

    match = re.search(
        r"Conta:\s*(\d{6,20})\s*-\s*(.+?)(?:Item\s+Material|$)",
        texto,
        flags=re.IGNORECASE,
    )

    if match:
        return limpar_texto(match.group(1)), limpar_texto(match.group(2))

    match = re.search(
        r"\b(\d{6,20})\s*-\s*(MAT\..+?)(?:Item\s+Material|Total|$)",
        texto,
        flags=re.IGNORECASE,
    )

    if match:
        return limpar_texto(match.group(1)), limpar_texto(match.group(2))

    return "", ""


def linha_eh_item(row):
    if not row:
        return False

    primeiro = limpar_texto(row[0])
    return bool(re.match(r"^\d{1,3}$", primeiro))


def linha_eh_cabecalho_ou_total(row):
    texto = " ".join(limpar_texto(celula) for celula in row).upper()

    termos_ignorar = [
        "ITEM MATERIAL",
        "TOTAL POR CONTA",
        "TOTAL GERAL",
        "CMM -",
        "CE -",
        "PR. MÉDIO",
        "RESÍDUO",
        "PÁGINA",
        "AX0003",
        "MINISTÉRIO PÚBLICO FEDERAL",
        "PROCURADORIA DA REPÚBLICA",
        "COORDENADORIA DE ADMINISTRAÇÃO",
        "POSIÇÃO DO ESTOQUE",
        "RESUMO DA POSIÇÃO",
        "ÓRGÃO:",
        "U.G.:",
        "ALMOXARIFADO:",
        "CONTA:",
    ]

    return any(termo in texto for termo in termos_ignorar)


def normalizar_row(row):
    row = [limpar_texto(celula) for celula in row]

    while len(row) < 11:
        row.append("")

    return row[:11]


def extrair_conta_da_pagina(page):
    texto_pagina = page.extract_text() or ""
    return extrair_conta_de_texto(texto_pagina)


def extrair_itens_com_pdfplumber(caminho_pdf):
    itens = []

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 3,
        "min_words_vertical": 1,
        "min_words_horizontal": 1,
        "text_tolerance": 3,
    }

    conta_codigo_atual = ""
    conta_descricao_atual = ""

    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            conta_codigo_pagina, conta_descricao_pagina = extrair_conta_da_pagina(page)

            if conta_codigo_pagina:
                conta_codigo_atual = conta_codigo_pagina
                conta_descricao_atual = conta_descricao_pagina

            tabelas = page.extract_tables(table_settings=table_settings)

            for tabela in tabelas:
                for row in tabela:
                    if not row:
                        continue

                    row = normalizar_row(row)

                    if linha_eh_cabecalho_ou_total(row):
                        continue

                    if not linha_eh_item(row):
                        continue

                    numero_item = int(limpar_texto(row[0]))
                    material = limpar_texto(row[1])
                    unidade_medida = limpar_texto(row[3])
                    finalidade_compra = limpar_texto(row[4])

                    cmm = para_decimal(row[5])
                    ce = para_decimal(row[6])
                    preco_medio = para_decimal(row[8])
                    estoque = para_decimal(row[9])
                    valor = para_decimal(row[10])

                    codigo_material, descricao = separar_codigo_descricao(material)

                    status = detectar_status(cmm, ce, estoque)
                    quantidade_sugerida = calcular_quantidade_sugerida(cmm, estoque)

                    itens.append(
                        {
                            "conta_codigo": conta_codigo_atual,
                            "conta_descricao": conta_descricao_atual,
                            "numero_item": numero_item,
                            "codigo_material": codigo_material,
                            "descricao": descricao,
                            "unidade_medida": unidade_medida,
                            "finalidade_compra": finalidade_compra,
                            "cmm": cmm,
                            "ce": ce,
                            "preco_medio": preco_medio,
                            "estoque": estoque,
                            "valor": valor,
                            "status": status,
                            "quantidade_sugerida": quantidade_sugerida,
                        }
                    )

    return itens


def processar_relatorio(relatorio):
    if not relatorio.arquivo_pdf:
        raise ValueError("Relatório não possui arquivo PDF.")

    caminho_pdf = relatorio.arquivo_pdf.path
    itens_extraidos = extrair_itens_com_pdfplumber(caminho_pdf)

    if not itens_extraidos:
        raise ValueError(
            "Nenhuma tabela foi extraída com pdfplumber. "
            "O PDF pode estar como imagem pura."
        )

    contas_do_novo_relatorio = {
        item["conta_codigo"]
        for item in itens_extraidos
        if item["conta_codigo"]
    }

    if contas_do_novo_relatorio:
        ItemEstoque.objects.filter(
            conta_codigo__in=contas_do_novo_relatorio,
            ativo=True,
        ).update(ativo=False)

    relatorio.itens.all().delete()

    objetos = []

    for dados in itens_extraidos:
        objetos.append(
            ItemEstoque(
                relatorio=relatorio,
                ativo=True,
                conta_codigo=dados["conta_codigo"],
                conta_descricao=dados["conta_descricao"],
                numero_item=dados["numero_item"],
                codigo_material=dados["codigo_material"],
                descricao=dados["descricao"],
                unidade_medida=dados["unidade_medida"],
                finalidade_compra=dados["finalidade_compra"],
                cmm=dados["cmm"],
                ce=dados["ce"],
                estoque=dados["estoque"],
                preco_medio=dados["preco_medio"],
                valor=dados["valor"],
                status=dados["status"],
                quantidade_sugerida=dados["quantidade_sugerida"],
            )
        )

    ItemEstoque.objects.bulk_create(objetos, batch_size=500)

    return objetos