# =========================
# FICHEIRO: tools/rag_tools.py
# =========================

import json
import numpy as np
from pathlib import Path

from perguntar import (
    procurar_chunks,
    rerank,
    construir_contexto
)

TOP_K = 8
FINAL_K = 3


def pesquisar_documentos(pergunta: str):

    chunks = json.loads(
        Path("chunks.json").read_text(
            encoding="utf-8",
            errors="ignore"
        )
    )

    vetores = np.load("vectors.npy")

    iniciais = procurar_chunks(
        pergunta,
        chunks,
        vetores,
        TOP_K
    )

    if not iniciais:
        return {
            "contextos": [],
            "fontes": [],
            "texto_contexto": ""
        }

    results = []

    for c, s in iniciais:
        results.append({
            "text": c["text"],
            "source": c.get("source", ""),
            "path": c.get("path", ""),
            "score": s
        })

    results = rerank(pergunta, results)

    final = results[:FINAL_K]

    contextos = construir_contexto(final)

    contexto_str = "\n\n---\n\n".join(contextos)

    return {
        "contextos": contextos,
        "fontes": final,
        "texto_contexto": contexto_str
    }