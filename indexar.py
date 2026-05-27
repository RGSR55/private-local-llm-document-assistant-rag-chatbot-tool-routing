import json
import requests
import numpy as np
import hashlib
from pathlib import Path
from pypdf import PdfReader
from docx import Document
import pandas as pd
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
from email.utils import parseaddr

OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"

DOCS_PATH = Path("docs")
CHUNKS_FILE = "chunks.json"
VECTORS_FILE = "vectors.npy"
META_FILE = "index_metadata.json"


# ---------------- HASH ----------------
def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


# ---------------- METADATA ----------------
def carregar_metadata():
    if Path(META_FILE).exists():
        return json.loads(Path(META_FILE).read_text(encoding="utf-8"))
    return {}


def guardar_metadata(meta):
    Path(META_FILE).write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ---------------- PDF ----------------
def ler_pdf(path):
    
    reader = PdfReader(str(path))

    texto_total = []

    for i, page in enumerate(reader.pages):
        try:
            texto = page.extract_text()
        except Exception:
            texto = ""

        if texto:
            texto_total.append(texto)

        print(f"DEBUG page {i}: {len(texto or '')}")

    return "\n".join(texto_total).strip()

# ------------------- DOCX -------------
def ler_docx(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

# -------------------- CSV --------------
def ler_csv(path):
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8", sep=None, engine="python")
    except:
        df = pd.read_csv(path, dtype=str, encoding="latin-1", sep=None, engine="python")

    linhas = []

    for _, row in df.iterrows():
        linha = " | ".join(f"{col}: {row[col]}" for col in df.columns if pd.notna(row[col]))
        linhas.append(linha)

    return "\n".join(linhas)

#----------- Markdown --------------
def ler_md(path):
    texto = path.read_text(encoding="utf-8", errors="ignore")

    # remove símbolos markdown básicos
    texto = texto.replace("#", "")
    texto = texto.replace("*", "")
    texto = texto.replace("`", "")

    return texto

# ----------- EMAIL (.eml)-----------
def ler_eml(path):
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    subject = msg.get("subject", "")
    #sender = msg.get("from", "")
    raw_sender = msg.get("from", "")
    nome, email = parseaddr(raw_sender)
    sender = f"{nome} <{email}>" if nome else email

    date = msg.get("date", "")

    corpo = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()

            if content_type == "text/plain":
                corpo += part.get_content()
            elif content_type == "text/html":
                html = part.get_content()
                corpo += BeautifulSoup(html, "html.parser").get_text()
    else:
        corpo = msg.get_content()

    anexos = []
    for part in msg.iter_attachments():
        nome = part.get_filename()
        if nome:
            anexos.append(nome)

    return f"""
ASSUNTO: {subject}
REMETENTE: {sender}
DATA: {date}

CORPO:
{corpo}

ANEXOS: {", ".join(anexos)}
"""

# ---------------- CHUNKING ----------------
def chunk_texto(texto: str, tamanho=300, overlap=80):
    palavras = texto.split()
    chunks = []

    i = 0
    while i < len(palavras):
        chunk = palavras[i:i + tamanho]
        texto_chunk = " ".join(chunk).strip()

        if texto_chunk:  # evita chunks vazios
            chunks.append(texto_chunk)

        i += tamanho - overlap

    return chunks


# ---------------- EMBEDDINGS ----------------
def gerar_embedding(texto: str):
    if not texto or not texto.strip():
        return None

    texto = texto[:2000]

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": EMBED_MODEL,
                "prompt": texto
            },
            timeout=320
        )

        if r.status_code != 200:
            print("❌ HTTP error:", r.text)
            return None

        data = r.json()

        vec = data.get("embedding")

        if vec is None or len(vec) == 0:
            print("❌ embedding vazio:", data)
            return None

        vec = np.array(vec, dtype=np.float32)

        norm = np.linalg.norm(vec)

        if norm > 0:
            vec = vec / norm

        return vec

    except Exception as e:
        print("❌ erro embedding:", e)
        return None   

# -------------- Upload --------------
def indexar_documentos():
    print("📂 A ler documentos...")

    meta = carregar_metadata()
    novos_chunks = []

    # ---------------- LEITURA DOCUMENTOS ----------------
    for ficheiro in DOCS_PATH.glob("*"):
        if ficheiro.suffix.lower() not in [".txt", ".pdf", ".docx", ".csv", ".md", ".eml"]:
            continue

        h = file_hash(ficheiro)

        if str(ficheiro) in meta and meta[str(ficheiro)]["hash"] == h:
            continue

        print(f"⚙️ processar: {ficheiro.name}")
        suffix = ficheiro.suffix.lower()

        if suffix == ".txt":
            texto = ficheiro.read_text(encoding="utf-8", errors="ignore")

        elif suffix == ".pdf":
            texto = ler_pdf(ficheiro)

        elif suffix == ".docx":
            texto = ler_docx(ficheiro)

        elif suffix == ".csv":
            texto = ler_csv(ficheiro)

        elif suffix == ".md":
            texto = ler_md(ficheiro)

        elif suffix == ".eml":
            texto = ler_eml(ficheiro)

        else:
            texto = ""

        # 🔥 proteção contra ficheiros vazios
        if not texto or not texto.strip():
            print(f"⚠️ ficheiro vazio: {ficheiro.name}")
            meta[str(ficheiro)] = {
                "hash": h,
                "chunks": 0,
                "ok": False
            }
            continue

        chunks = chunk_texto(texto)

        if len(chunks) == 0:
            print(f"⚠️ sem chunks: {ficheiro.name}")
            meta[str(ficheiro)] = {
                "hash": h,
                "chunks": 0,
                "ok": False
            }
            continue

        for c in chunks:
            novos_chunks.append({
                "text": c,
                "source": ficheiro.name,
                "path": str(ficheiro.resolve())
            })

        # ⚠️ valor provisório (corrigido depois)
        meta[str(ficheiro)] = {
            "hash": h,
            "chunks": len(chunks),
            "ok": True
        }

    if not novos_chunks:
        return "Nada novo para indexar."

    # ---------------- EMBEDDINGS ----------------
    print("🧮 A gerar embeddings...")

    novos_vetores = []
    chunks_validos = []

    for i, chunk in enumerate(novos_chunks, 1):
        vec = gerar_embedding(chunk["text"])

        if vec is not None:
            novos_vetores.append(vec)
            chunks_validos.append(chunk)
        else:
            print(f"⚠️ chunk ignorado (embedding falhou)")

    # 🔥 garantir alinhamento
    novos_chunks = chunks_validos

    if len(novos_vetores) == 0:
        return "Erro: embeddings vazios"

    novos_vetores = np.array(novos_vetores, dtype=np.float32)

    # ---------------- LOAD EXISTENTE ----------------
    if Path(CHUNKS_FILE).exists():
        chunks_existentes = json.loads(Path(CHUNKS_FILE).read_text(encoding="utf-8"))
    else:
        chunks_existentes = []

    if Path(VECTORS_FILE).exists():
        vetores_existentes = np.load(VECTORS_FILE)
    else:
        vetores_existentes = np.empty((0, novos_vetores.shape[1]), dtype=np.float32)

    # 🔥 proteção contra corrupção do índice
    if len(chunks_existentes) != len(vetores_existentes):
        print("⚠️ desalinhamento detetado — reset índice")
        chunks_existentes = []
        vetores_existentes = np.empty((0, novos_vetores.shape[1]), dtype=np.float32)

    # ---------------- MERGE ----------------
    todos_chunks = chunks_existentes + novos_chunks
    todos_vetores = np.vstack([vetores_existentes, novos_vetores])

    # ---------------- CORRIGIR METADATA ----------------
    for ficheiro in DOCS_PATH.glob("*"):
        nome = ficheiro.name

        count_real = len([
            c for c in todos_chunks if c["source"] == nome
        ])

        if str(ficheiro) in meta:
            meta[str(ficheiro)]["chunks"] = count_real
            meta[str(ficheiro)]["ok"] = count_real > 0

    # ---------------- SAVE ----------------
    print("💾 A guardar índice...")

    Path(CHUNKS_FILE).write_text(
        json.dumps(todos_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    np.save(VECTORS_FILE, todos_vetores)

    guardar_metadata(meta)

    print("✅ Indexação concluída com sucesso!")

    return f"{len(novos_chunks)} chunks indexados com sucesso"

def remover_documento(nome_ficheiro):

    print(f"🗑️ Remover: {nome_ficheiro}")

    # ---------------- LOAD ----------------
    if not Path(CHUNKS_FILE).exists():
        return "Nada para remover"

    chunks = json.loads(Path(CHUNKS_FILE).read_text(encoding="utf-8"))
    vetores = np.load(VECTORS_FILE)

    # ---------------- FILTRAR ----------------
    novos_chunks = []
    novos_vetores = []

    for i, c in enumerate(chunks):
        if c["source"] != nome_ficheiro:
            novos_chunks.append(c)
            novos_vetores.append(vetores[i])

    if not novos_chunks:
        novos_vetores = np.empty((0, vetores.shape[1]), dtype=np.float32)
    else:
        novos_vetores = np.array(novos_vetores, dtype=np.float32)

    # ---------------- SAVE ----------------
    Path(CHUNKS_FILE).write_text(
        json.dumps(novos_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    np.save(VECTORS_FILE, novos_vetores)

    # ---------------- METADATA ----------------
    meta = carregar_metadata()

    for k in list(meta.keys()):
        if nome_ficheiro in k:
            del meta[k]

    guardar_metadata(meta)

    # ---------------- FICHEIRO FÍSICO ----------------
    path = DOCS_PATH / nome_ficheiro
    if path.exists():
        path.unlink()

    return f"{nome_ficheiro} removido completamente"

# ---------------- MAIN ----------------
def main():
    print("📂 A ler documentos...")

    meta = carregar_metadata()

    novos_chunks = []

    for ficheiro in DOCS_PATH.glob("*"):
        if ficheiro.suffix.lower() not in [".txt", ".pdf", ".docx", ".csv", ".md", ".eml"]:
            continue

        h = file_hash(ficheiro)

        if str(ficheiro) in meta and meta[str(ficheiro)]["hash"] == h:
            print(f"⏭️ ignorado: {ficheiro.name}")
            continue

        print(f"⚙️ processar: {ficheiro.name}")

        suffix = ficheiro.suffix.lower()

        if suffix == ".txt":
            texto = ficheiro.read_text(encoding="utf-8", errors="ignore")

        elif suffix == ".pdf":
            texto = ler_pdf(ficheiro)

        elif suffix == ".docx":
            texto = ler_docx(ficheiro)

        elif suffix == ".csv":
            texto = ler_csv(ficheiro)

        elif suffix == ".md":
            texto = ler_md(ficheiro)

        elif suffix == ".eml":
            texto = ler_eml(ficheiro)

        else:
            texto = ""

        chunks = chunk_texto(texto)

        if len(chunks) == 0:
            print("⚠️ ficheiro sem texto extraível:", ficheiro.name)
            continue

        for c in chunks:
            novos_chunks.append({
                "text": c,
                "source": ficheiro.name,
                "path": str(ficheiro.resolve())
            })

        meta[str(ficheiro)] = {
            "hash": h,
            "chunks": len(chunks),
            "ok": len(chunks) > 0
        }

    if not novos_chunks:
        print("✅ Nada novo para indexar.")
        return

    print(f"✂️ novos chunks: {len(novos_chunks)}")

    novos_vetores = []

    print("🧮 a gerar embeddings...")

    for i, chunk in enumerate(novos_chunks, 1):
        vec = gerar_embedding(chunk["text"])

        if vec is None:
            print("⚠️ chunk ignorado (sem embedding)")
            continue

        novos_vetores.append(vec)

        print(f"   [{i}/{len(novos_chunks)}] {chunk['source']}")

    if len(novos_vetores) == 0:
        print("❌ nenhum embedding válido gerado → abortar")
        return

    novos_vetores = np.array(novos_vetores, dtype=np.float32)

    # ---------------- LOAD EXISTENTE ----------------
    if Path(CHUNKS_FILE).exists():
        chunks_existentes = json.loads(Path(CHUNKS_FILE).read_text(encoding="utf-8"))
    else:
        chunks_existentes = []

    if Path(VECTORS_FILE).exists():
        vetores_existentes = np.load(VECTORS_FILE)
    else:
        vetores_existentes = np.empty((0, novos_vetores.shape[1]), dtype=np.float32)

    # ---------------- MERGE ----------------
    todos_chunks = chunks_existentes + novos_chunks
    todos_vetores = np.vstack([vetores_existentes, novos_vetores])

    # ---------------- SAVE ----------------
    print("💾 a guardar...")

    Path(CHUNKS_FILE).write_text(
        json.dumps(todos_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    np.save(VECTORS_FILE, todos_vetores)

    guardar_metadata(meta)

    print("✅ indexação concluída com sucesso!")


if __name__ == "__main__":
    main()