from pathlib import Path
from difflib import get_close_matches

DOCS_PATH = Path("docs")


def resolver_nome_documento(texto_utilizador):

    ficheiros = [
        f.name
        for f in DOCS_PATH.iterdir()
        if f.is_file()
    ]

    if not ficheiros:
        return None

    texto = texto_utilizador.lower()

    # match direto parcial
    for f in ficheiros:

        nome = f.lower()

        if nome in texto:
            return f

        stem = Path(nome).stem

        if stem in texto:
            return f

    # fuzzy match
    matches = get_close_matches(
        texto,
        ficheiros,
        n=1,
        cutoff=0.4
    )

    if matches:
        return matches[0]

    return None