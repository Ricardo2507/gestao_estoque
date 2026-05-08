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