# =========================
# FICHEIRO: tools/math_tools.py
# =========================

def calcular(expressao: str):

    permitidos = set(
        "0123456789+-*/()., "
    )

    if not set(expressao).issubset(permitidos):
        return "Expressão inválida."

    try:

        resultado = eval(
            expressao,
            {"__builtins__": {}},
            {}
        )

        return str(resultado)

    except Exception as e:
        return f"ERRO: {e}"