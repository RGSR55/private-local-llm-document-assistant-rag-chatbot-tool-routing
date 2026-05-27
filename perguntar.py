import json
import os
import sys
import requests
import numpy as np
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:3b"#qwen2.5:3b

TOP_K = 8
FINAL_K = 3
MAX_CHARS = 3000


# ---------------- EMBEDDING ----------------
def gerar_embedding(texto: str):
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": texto},
            timeout=100,
        )
        r.raise_for_status()

        vec = np.array(r.json()["embeddings"][0], dtype=np.float32)

        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    except Exception as e:
        print("❌ erro embedding:", e)
        return None


# ---------------- SEARCH ----------------
def procurar_chunks(pergunta, chunks, vetores, k):
    vec = gerar_embedding(pergunta)

    if vec is None:
        return []

    sims = vetores @ vec
  
    k = min(k, len(chunks))
    idx = np.argsort(sims)[::-1][:k]

    return [(chunks[i], float(sims[i])) for i in idx]


# ---------------- RERANK ----------------
def rerank(query, results):
    words = query.lower().split()

    for r in results:
        text = r["text"].lower()
        keyword_hits = sum(1 for w in words if w in text)

        r["final_score"] = r["score"] + (keyword_hits * 0.1)

    return sorted(results, key=lambda x: x["final_score"], reverse=True)


# ---------------- LIMPAR TEXTO ----------------
def limpar_texto(t):
    return t.replace("##", "").strip()


# ---------------- CONTEXTO ----------------
def construir_contexto(results):
    vistos = set()
    contextos = []

    for r in results:
        txt = limpar_texto(r["text"])

        if txt not in vistos:
            vistos.add(txt)
            contextos.append(txt)

    return contextos


def limitar_contexto(contextos):
    texto = ""
    for c in contextos:
        if len(texto) + len(c) > MAX_CHARS:
            break
        texto += c + "\n\n---\n\n"
    return texto


# ---------------- ANSWER ----------------
def gerar_resposta(pergunta, contextos):
    contexto_str = limitar_contexto(contextos)

    if not contexto_str.strip():
        print("❌ sem contexto relevante")
        return ""

    prompt = f"""
És um assistente interno da TechNova Lda.

Responde APENAS com base no contexto fornecido.

REGRAS IMPORTANTES:
- Usa apenas informação dos documentos
- Se não existir informação, responde exatamente:
"Não encontrei essa informação nos documentos."
- Não inventes
- Responde SEMPRE em português de Portugal
- Resposta curta e direta

CONTEXTO:
{contexto_str}

PERGUNTA:
{pergunta}

RESPOSTA:
"""

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 200
                }
            },
            stream=True,
            timeout=(10, 580)
        )

        resposta = ""

        for linha in r.iter_lines():
            if not linha:
                continue

            if isinstance(linha, bytes):
                linha = linha.decode("utf-8", errors="ignore")

            linha = linha.strip()

            if linha.startswith("data:"):
                linha = linha[5:].strip()

            if linha == "[DONE]":
                break

            try:
                data = json.loads(linha)
                token = data.get("response", "")

                resposta += token
                print(token, end="", flush=True)

            except json.JSONDecodeError:
                continue

        print()
        return resposta.strip()

    except Exception as e:
        print(f"❌ erro ao gerar resposta: {e}")
        return ""


# ---------------- MAIN ----------------
def main():
    if len(sys.argv) < 2:
        print("Uso: python perguntar.py 'pergunta'")
        return

    pergunta = " ".join(sys.argv[1:])

    # carregar dados
    chunks = json.loads(Path("chunks.json").read_text(encoding="utf-8", errors="ignore"))
    vetores = np.load("vectors.npy")

    print(f"\n❓ {pergunta}\n")

    # retrieval
    iniciais = procurar_chunks(pergunta, chunks, vetores, TOP_K)

    if not iniciais:
        print("❌ sem resultados")
        return

    results = []
    for c, s in iniciais:
        results.append({
            "text": c["text"],
            "source": c.get("source", "desconhecido"),
            "path": c.get("path", ""),
            "score": s
        })

    # rerank
    results = rerank(pergunta, results)

    # top resultados
    final = results[:FINAL_K]

    print("📚 Fontes consideradas:\n")
    for i, r in enumerate(final, 1):
        print(f"[{i}] ({r['final_score']:.3f}) {r['source']}")
        print(r["text"][:140] + "...\n")

    # construir contexto LIMPO e estável
    contextos = construir_contexto(final)

    print("🤖 Resposta:\n")
    print("─" * 60)

    resposta = gerar_resposta(pergunta, contextos)

    print("─" * 60)

    # 📌 fonte principal (a que mais contribuiu)
    if final:
        fonte_principal = final[0]

        print("📎 Referência:\n")
        print(f"[1] {fonte_principal['source']}")

        caminho = fonte_principal.get("path", "")

        if caminho and os.path.exists(caminho):
            #print(f"📂 caminho: {caminho}")
            uri = "file://" + os.path.abspath(caminho)
            print(f"\033]8;;{uri}\033\\📂 abrir ficheiro\033]8;;\033\\")
            print("\n")


            #try:
                # abrir normalmente
                #os.startfile(caminho)

            #except Exception as e:
                #print(f"⚠️ não foi possível abrir automaticamente: {e}")
        


if __name__ == "__main__":
    main()