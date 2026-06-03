from django import template

register = template.Library()


@register.filter
def get_item(dicionario, chave):
    if not dicionario:
        return ""

    return dicionario.get(chave, "")