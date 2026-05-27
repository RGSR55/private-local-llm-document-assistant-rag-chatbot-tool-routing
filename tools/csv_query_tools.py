import pandas as pd
from pathlib import Path
import unicodedata

DOCS_PATH = Path("docs")


# -------------------------
# NORMALIZAÇÃO
# -------------------------

def normalizar(txt):

    if txt is None:
        return ""

    txt = str(txt).lower().strip()

    txt = ''.join(
        c for c in unicodedata.normalize('NFD', txt)
        if unicodedata.category(c) != 'Mn'
    )

    return txt


MESES = [
    "janeiro",
    "fevereiro",
    "marco",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro"
]


# -------------------------
# PROCESSAMENTO CSV
# -------------------------

def processar_csv_query(pergunta):

    pergunta = normalizar(pergunta)

    ficheiro = DOCS_PATH / "contas-2025.csv"

    if not ficheiro.exists():
        return None

    try:

        df = pd.read_csv(ficheiro)

        # normaliza meses
        if "Mes" in df.columns:
            coluna_mes = "Mes"
        elif "Mês" in df.columns:
            coluna_mes = "Mês"
        else:
            return None

        df["Mes_norm"] = (
            df[coluna_mes]
            .astype(str)
            .apply(normalizar)
        )

        # converter numéricos
        cols = [
            "Receita",
            "Despesas",
            "Impostos",
            "Lucro_Liquido",
            "Capital_Final",
            "Capital_Inicial"
        ]

        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(
                    df[c],
                    errors="coerce"
                )

        # --------------------
        # MAIOR LUCRO
        # --------------------

        if "maior lucro" in pergunta:

            linha = df.loc[
                df["Lucro_Liquido"].idxmax()
            ]

            return (
                f"Mês com maior lucro: "
                f"{linha[coluna_mes]} "
                f"{linha['Ano']} "
                f"→ {linha['Lucro_Liquido']}"
            )

        # --------------------
        # MENOR LUCRO
        # --------------------

        if "menor lucro" in pergunta:

            linha = df.loc[
                df["Lucro_Liquido"].idxmin()
            ]

            return (
                f"Mês com menor lucro: "
                f"{linha[coluna_mes]} "
                f"{linha['Ano']} "
                f"→ {linha['Lucro_Liquido']}"
            )

        # --------------------
        # CONSULTAS MENSAIS
        # --------------------

        for mes in MESES:

            if mes in pergunta:

                linha = df[
                    df["Mes_norm"] == mes
                ]

                if linha.empty:
                    return None

                linha = linha.iloc[0]

                if "receita" in pergunta:

                    return (
                        f"Receita de "
                        f"{linha[coluna_mes]} "
                        f"{linha['Ano']}: "
                        f"{linha['Receita']}"
                    )

                if "despesas" in pergunta:

                    return (
                        f"Despesas de "
                        f"{linha[coluna_mes]} "
                        f"{linha['Ano']}: "
                        f"{linha['Despesas']}"
                    )

                if "impostos" in pergunta:

                    return (
                        f"Impostos de "
                        f"{linha[coluna_mes]} "
                        f"{linha['Ano']}: "
                        f"{linha['Impostos']}"
                    )

                if "lucro" in pergunta:

                    return (
                        f"Lucro líquido de "
                        f"{linha[coluna_mes]} "
                        f"{linha['Ano']}: "
                        f"{linha['Lucro_Liquido']}"
                    )

                if "capital final" in pergunta:

                    return (
                        f"Capital final de "
                        f"{linha[coluna_mes]} "
                        f"{linha['Ano']}: "
                        f"{linha['Capital_Final']}"
                    )

        return None

    except Exception as e:

        return (
            f"Erro CSV: {e}"
        )