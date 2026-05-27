import re
import requests
from pathlib import Path
from tools.csv_query_tools import processar_csv_query
from tools.rag_tools import pesquisar_documentos
from tools.date_tools import (
    get_current_time,
    extrair_data,
    calcular_dias_ate_data
)
from tools.export_tools import exportar_txt
from tools.math_tools import calcular

from tools.file_tools import (
    listar_documentos,
    ler_documento
)

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen2.5:3b"#qwen2.5:3b


# --------------------------
# ROUTER
# --------------------------
def precisa_listar_docs(pergunta):

    p = pergunta.lower()

    triggers = [
        "listar documentos",
        "lista documentos",
        "que documentos existem",
        "mostrar documentos",
        "mostra ficheiros",
        "lista ficheiros",
        "listar ficheiros",
        "lista de ficheiros"
    ]

    return any(t in p for t in triggers)


def precisa_ler_documento(pergunta):

    p = pergunta.lower()

    triggers = [
        "resume o ficheiro",
        "resume este ficheiro",
        "ler documento",
        "conteúdo do ficheiro",
        "faz um resumo",
        "analisa o ficheiro"
        "abre o ficheiro"
        "resumo do ficheiro"
    ]

    return any(t in p for t in triggers)

def extrair_nome_ficheiro(pergunta):

    match = re.search(
        r'([^\s]+\.(txt|md|csv|pdf|docx|eml))',
        pergunta,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None

def extrair_expressao(pergunta):

    expr = pergunta.lower()

    substituicoes = {
        " vezes ": "*",
        " x ": "*",
        " multiplicado por ": "*",

        " mais ": "+",
        " menos ": "-",

        " dividido por ": "/",
        " sobre ": "/",
    }

    for texto, op in substituicoes.items():
        expr = expr.replace(texto, op)

    resultados = re.findall(
        r"[\d+\-*/().,\s]+",
        expr
    )

    # remove vazios/espaços
    resultados = [
        x.strip()
        for x in resultados
        if x.strip()
    ]

    if resultados:
        return resultados[-1]

    return None
def precisa_hora(pergunta):

    triggers = [
        "que dia é hoje",
        "que horas são",
        "data atual",
        "hora atual"
    ]

    p = pergunta.lower()

    return any(t in p for t in triggers)


def precisa_calculo(pergunta):

    return bool(
        re.search(
            r"\d+\s*[\+\-\*/x]\s*\d+|"
            r"\d+\s+(mais|menos|vezes|dividido por|multiplicado por|sobre)\s+\d+",
            pergunta.lower()
        )
    )


def precisa_exportar(pergunta):

    p = pergunta.lower()

    return (
        "exporta" in p
        or "guardar em txt" in p
        or "gera ficheiro" in p
    )


# --------------------------
# LLM
# --------------------------

def gerar_resposta_rag(
    pergunta,
    contexto
):

    prompt = f"""
És um assistente interno da empresa.

Responde APENAS usando o contexto.

REGRAS:
- Se encontrares valores explícitos, responde diretamente
- Se existirem tabelas ou dados estruturados, interpreta-os.
- Não inventar
- Português europeu
- Resposta curta

Se não souberes:
"Não encontrei essa informação nos documentos."

CONTEXTO:
{contexto}

PERGUNTA:
{pergunta}

RESPOSTA:
"""

    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }
    )

    r.raise_for_status()

    return r.json()["response"]


# --------------------------
# MAIN
# --------------------------

def executar_agente(pergunta):

    # ----------------------
    # HORA
    # ----------------------

    if precisa_hora(pergunta):

        resposta = get_current_time()

        return {
            "resposta": f"Data e hora atuais: {resposta}",
            "fontes": [],
            "ficheiro": None
        }

    # ----------------------
    # CÁLCULO
    # ----------------------

    if precisa_calculo(pergunta):

        expr = extrair_expressao(pergunta)

        if expr:

            expr = expr.replace(",", ".")

            resultado = calcular(expr)

            return {
                "resposta": f"Resultado: {resultado}",
                "fontes": [],
                "ficheiro": None
            }
    # ----------------------
# LISTAR DOCUMENTOS
# ----------------------

    if precisa_listar_docs(pergunta):

        resultado = listar_documentos()

        return {
            "resposta": resultado,
            "fontes": [],
            "ficheiro": None
        }


    # ----------------------
    # LER / RESUMIR FICHEIRO
    # ----------------------

    if precisa_ler_documento(pergunta):

        nome = extrair_nome_ficheiro(pergunta)

        if not nome:

            return {
                "resposta": (
                    "Indica o nome do ficheiro."
                ),
                "fontes": [],
                "ficheiro": None
            }

        conteudo = ler_documento(nome)

        if conteudo.startswith("ERRO"):

            return {
                "resposta": conteudo,
                "fontes": [],
                "ficheiro": None
            }

        prompt = f"""
    Resume o seguinte documento.

    REGRAS:
    - Português europeu
    - NÃO inventar informação
    - NÃO inferir nada que não esteja explícito

    FORMATO:
    
    Resumo:
    [Resumo inicial de forma sucinta que permita ter a ideia geral sem perder informação relevante.]
    
    Pontos Principais:
    [Informações que merecem relevância]
    - ponto
    - ponto
    - ponto

    Ao resumir emails identifica:

    - objetivo
    - pontos principais
    - datas
    - ações


    DOCUMENTO:
    {conteudo}

    RESUMO:
    """

        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2
                }
            }
        )

        resumo = r.json()["response"]

        ficheiro = None

        if precisa_exportar(pergunta):

            ficheiro = exportar_txt(
                resumo,
                nome=f"resumo_{Path(nome).stem}"
            )

        return {
            "resposta": resumo,
            "fontes": [],
            "ficheiro": ficheiro
        }

# ----------------------
# CSV ESTRUTURADO
# ----------------------

    resposta_csv = processar_csv_query(
        pergunta
    )

    if resposta_csv:

        return {
            "resposta": resposta_csv,
            "fontes": [
                {
                    "source": "contas-2025.csv",
                    "text": resposta_csv,
                    "score": 1.0
                }
            ],
            "ficheiro": None
        }
        # ----------------------
    # RAG AUTOMÁTICO
    # ----------------------

    rag = pesquisar_documentos(pergunta)

    contexto = rag["texto_contexto"]

    fontes = rag["fontes"]

    # sem resultados
    if not contexto:

        return {
            "resposta": (
                "Não encontrei essa informação "
                "nos documentos."
            ),
            "fontes": [],
            "ficheiro": None
        }

    # ----------------------
    # DETEÇÃO DE DATAS
    # ----------------------

    info_data = ""

    pergunta_lower = pergunta.lower()

    quer_prazo = any(
        x in pergunta_lower
        for x in [

            "quantos dias",
            "faltam",
            "termina",
            "término",
            "vigência",
            "prazo"

        ]
    )

    if quer_prazo:

        data = extrair_data(
            contexto
        )

        if data:

            dias = calcular_dias_ate_data(
                data
            )

            info_data = (
                f"\n\nData encontrada:"
                f"{data}\n"
                f"{dias}"
            )

    # ----------------------
    # GERAR RESPOSTA
    # ----------------------
    resposta = gerar_resposta_rag(
        pergunta,
        contexto + info_data
    )

    # ----------------------
    # TRANCAR FONTES
    # ----------------------

    resposta_normalizada = (
        resposta
        .lower()
        .strip()
    )

    mensagens_sem_resultado = [

        "não encontrei essa informação nos documentos",
        "Não consegui confirmar a fonte correta",
        "não encontrei essa informação",
        "não sei",
        "sem informação disponível"

    ]

    if any(
        x in resposta_normalizada
        for x in mensagens_sem_resultado
    ):

        fontes = []

        contexto = ""

    ficheiro = None
    # ----------------------
    # EXPORTAR
    # ----------------------

    if precisa_exportar(pergunta):

        ficheiro = exportar_txt(
            resposta
        )

    return {
        "resposta": resposta,
        "fontes": fontes,
        "ficheiro": ficheiro
    }