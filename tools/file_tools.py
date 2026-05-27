# =========================
# FICHEIRO: tools/file_tools.py
# =========================

from pathlib import Path


DOCS_PATH = Path("docs")


# -------------------------
# LISTAR DOCUMENTOS
# -------------------------

def listar_documentos():

    """
    Lista documentos da pasta docs/
    """

    try:

        DOCS_PATH.mkdir(exist_ok=True)

        ficheiros = []

        for f in DOCS_PATH.iterdir():

            if f.is_file():

                ficheiros.append(f.name)

        if not ficheiros:

            return "Não existem documentos."

        return "\n".join(
            f"📄 {f}"
            for f in sorted(ficheiros)
        )

    except Exception as e:

        return f"ERRO: {e}"


# -------------------------
# LER DOCUMENTO
# -------------------------

def ler_documento(nome_ficheiro: str):

    """
    Lê conteúdo de ficheiro.
    """

    try:

        caminho = DOCS_PATH / nome_ficheiro

        if not caminho.exists():

            return (
                f"ERRO: ficheiro "
                f"'{nome_ficheiro}' não existe."
            )

        if caminho.stat().st_size > 500_000:

            return (
                "ERRO: ficheiro demasiado grande."
            )

        extensao = caminho.suffix.lower()

        # TXT / MD / CSV
        if extensao in [
            ".txt",
            ".md",
            ".csv",
            ".eml"

        ]:


            return caminho.read_text(
                encoding="utf-8",
                errors="ignore"
            )
    except:
       
        return (
            "ERRO: não foi possível "
            "ler o ficheiro."
        )