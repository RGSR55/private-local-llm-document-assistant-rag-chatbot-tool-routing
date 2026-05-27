# =========================
# FICHEIRO: tools/date_tools.py
# =========================

from datetime import datetime
from zoneinfo import ZoneInfo
import re


# -------------------------
# MESES PT
# -------------------------

MESES = {

    "janeiro":1,
    "fevereiro":2,
    "março":3,
    "abril":4,
    "maio":5,
    "junho":6,
    "julho":7,
    "agosto":8,
    "setembro":9,
    "outubro":10,
    "novembro":11,
    "dezembro":12

}


# -------------------------
# HORA / DATA ATUAL
# -------------------------

def get_current_time(
    timezone="Europe/Lisbon"
):

    try:

        tz = ZoneInfo(
            timezone
        )

        agora = datetime.now(
            tz
        )

        return agora.strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )

    except Exception as e:

        return f"ERRO: {e}"


# -------------------------
# CONVERTER DATA PT
# -------------------------

def converter_data_pt(
    dia,
    mes,
    ano
):

    mes_num = MESES.get(
        mes.lower()
    )

    if not mes_num:

        return None

    return (
        f"{ano}-"
        f"{mes_num:02d}-"
        f"{int(dia):02d}"
    )


# -------------------------
# EXTRAIR DATA
# -------------------------

def extrair_data(
    texto: str
):

    texto = texto.lower()

    # ----------------------
    # CASO PRIORITÁRIO:
    #
    # "...com termo em
    # 19 de janeiro de 2027"
    # ----------------------

    padrao_termo = (

        r"(?:com\s+)?"
        r"termo(?:\s+em)?"
        r".{0,80}?"
        r"(\d{1,2})\s+de\s+"
        r"([a-zç]+)\s+de\s+"
        r"(\d{4})"

    )

    m = re.search(
        padrao_termo,
        texto,
        re.IGNORECASE |
        re.DOTALL
    )

    if m:

        return converter_data_pt(
            *m.groups()
        )


    # ----------------------
    # SEGUNDA OPÇÃO:
    #
    # entra em vigor
    # ----------------------

    padrao_inicio = (

        r"entra\s+em\s+vigor"
        r".{0,80}?"
        r"(\d{1,2})\s+de\s+"
        r"([a-zç]+)\s+de\s+"
        r"(\d{4})"

    )

    m = re.search(
        padrao_inicio,
        texto,
        re.IGNORECASE |
        re.DOTALL
    )

    if m:

        return converter_data_pt(
            *m.groups()
        )


    # ----------------------
    # FORMATO ISO
    #
    # 2027-01-19
    # ----------------------

    m = re.search(
        r"(\d{4}-\d{2}-\d{2})",
        texto
    )

    if m:

        return m.group(1)


    # ----------------------
    # FORMATO PT
    #
    # 19/01/2027
    # ----------------------

    m = re.search(
        r"(\d{2}/\d{2}/\d{4})",
        texto
    )

    if m:

        data = datetime.strptime(
            m.group(1),
            "%d/%m/%Y"
        )

        return data.strftime(
            "%Y-%m-%d"
        )


    # ----------------------
    # FALLBACK:
    #
    # última data encontrada
    # ----------------------

    datas = re.findall(

        r"(\d{1,2})\s+de\s+"
        r"([a-zç]+)\s+de\s+"
        r"(\d{4})",

        texto,

        re.IGNORECASE

    )

    if datas:

        ultima = datas[-1]

        return converter_data_pt(
            *ultima
        )

    return None


# -------------------------
# CALCULAR DIAS
# -------------------------

def calcular_dias_ate_data(
    data_str
):

    try:

        alvo = datetime.strptime(
            data_str,
            "%Y-%m-%d"
        ).date()

        hoje = datetime.now().date()

        dias = (
            alvo-hoje
        ).days

        if dias < 0:

            return (
                f"O prazo já expirou "
                f"há {-dias} dias."
            )

        elif dias == 0:

            return (
                "O prazo termina hoje."
            )

        else:

            return (
                f"Faltam {dias} dias."
            )

    except Exception as e:

        return (
            f"ERRO: {e}"
        )


# -------------------------
# TESTE
# -------------------------

if __name__ == "__main__":

    texto = """

    CLÁUSULA SEGUNDA

    O Contrato a celebrar
    entra em vigor
    no dia 20 de janeiro de 2026

    e com termo em
    19 de janeiro de 2027

    """

    data = extrair_data(
        texto
    )

    print(
        "Data encontrada:"
    )

    print(
        data
    )

    print(
        calcular_dias_ate_data(
            data
        )
    )