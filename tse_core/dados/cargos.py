"""
Mapa de códigos de cargo TSE ↔ nome legível.
Cobre municipais (Prefeito/Vereador) e deixa os demais mapeados
para escalabilidade futura (cargos estaduais/federais).
"""

CARGOS: dict[str, str] = {
    "1":  "Presidente",
    "2":  "Vice-Presidente",
    "3":  "Governador",
    "4":  "Vice-Governador",
    "5":  "Senador",
    "6":  "Deputado Federal",
    "7":  "Deputado Estadual",
    "8":  "Deputado Distrital",
    "11": "Prefeito",
    "12": "Vice-Prefeito",
    "13": "Vereador",
}

_ALIASES: dict[str, str] = {
    "prefeito": "11",
    "vice-prefeito": "12",
    "vereador": "13",
    "deputado estadual": "7",
    "deputado federal": "6",
    "senador": "5",
    "governador": "3",
    "presidente": "1",
}


def resolver_cargo(texto: str) -> str | None:
    """Resolve texto livre para código TSE. Retorna None se não reconhecido."""
    chave = texto.strip().lower()
    if chave in CARGOS:
        return chave
    return _ALIASES.get(chave)
