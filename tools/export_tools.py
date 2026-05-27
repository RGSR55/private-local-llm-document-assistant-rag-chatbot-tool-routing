# =========================
# FICHEIRO: tools/export_tools.py
# =========================

from pathlib import Path
from datetime import datetime


def exportar_txt(conteudo: str, nome: str = None):

    pasta = Path("exports")
    pasta.mkdir(exist_ok=True)

    if not nome:
        nome = datetime.now().strftime("resposta_%Y%m%d_%H%M%S")

    caminho = pasta / f"{nome}.txt"

    caminho.write_text(
        conteudo,
        encoding="utf-8"
    )

    return str(caminho)