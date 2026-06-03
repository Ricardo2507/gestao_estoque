from decimal import Decimal, ROUND_HALF_UP
from django import template

register = template.Library()


@register.filter
def decimal_virgula(valor):
    if valor is None:
        return "0,00"

    try:
        valor = Decimal(valor)
    except Exception:
        return "0,00"

    return f"{valor:.2f}".replace(".", ",")


@register.filter
def inteiro(valor):
    if valor is None:
        return "0"

    try:
        valor = Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    except Exception:
        return "0"

    return str(int(valor))

@register.filter
def get_item(dicionario, chave):
    if not isinstance(dicionario, dict):
        return "0"
    return dicionario.get(chave, "0")


@register.filter
def decimal4_virgula(valor):
    if valor is None:
        return "0,0000"

    try:
        valor = Decimal(valor)
    except Exception:
        return "0,0000"

    return f"{valor:.4f}".replace(".", ",")
