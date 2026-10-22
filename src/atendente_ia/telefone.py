"""Normalização de telefones brasileiros para comparar o WhatsApp com o cadastro do ERP."""

import re


def normalizar(numero: str | None) -> str:
    """Devolve só DDD + número (10 ou 11 dígitos), sem +55, espaços ou símbolos.

    Celulares antigos sem o 9 inicial (8 dígitos após o DDD) ganham o 9,
    porque o WhatsApp sempre informa o número no formato atual.
    """
    if not numero:
        return ""
    digitos = re.sub(r"\D", "", numero)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    digitos = digitos.lstrip("0")
    if len(digitos) == 10 and digitos[2] in "6789":
        digitos = digitos[:2] + "9" + digitos[2:]
    return digitos


def iguais(a: str | None, b: str | None) -> bool:
    na, nb = normalizar(a), normalizar(b)
    return bool(na) and na == nb
