import streamlit as st
import os
import re
from pathlib import Path

from indexar import remover_documento
from indexar import main as indexar_main

from agent_core import executar_agente

os.environ["PYTHONUNBUFFERED"] = "1"

st.set_page_config(
    page_title="Assistente de Documentos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CSS ----------------

st.markdown("""
<style>

/* Container */
.block-container {
    max-width: 1200px;
    padding-top: 2rem;
}

/* Chat */
.stChatMessage {
    max-width: 900px;
    margin-left: auto;
    margin-right: auto;
}

/* Input */
[data-testid="stChatInput"] {
    max-width: 900px;
    margin: auto;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    min-width: 280px;
    max-width: 600px;
}

/* Título */
h1 {
    font-size: 2.2rem;
    margin-bottom: 0.3rem;
}

/* Espaçamento */
main {
    padding-top: 1rem;
}

/* Chat moderno */
.stChatMessage div {
    border-radius: 12px;
}

/* User */
[data-testid="stChatMessage-user"] {
    background-color: #f1f5f9;
}

/* Assistant */
[data-testid="stChatMessage-assistant"] {
    background-color: #ffffff;
}

mark {
    background-color: #ffe58f;
    padding: 2px;
    border-radius: 4px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------

if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = []

if "chat" not in st.session_state:
    st.session_state.chat = []

# ---------------- PASTAS ----------------

docs_path = Path("docs")
docs_path.mkdir(exist_ok=True)

exports_path = Path("exports")
exports_path.mkdir(exist_ok=True)

# ---------------- SIDEBAR ----------------

with st.sidebar:

    st.header("📤 Upload de Documentos")

    uploaded_files = st.file_uploader(
        "Arrasta ficheiros",
        type=["pdf", "txt", "docx", "csv", "md", "eml"],
        accept_multiple_files=True
    )

    current_files = [f.name for f in uploaded_files] if uploaded_files else []

    # ---------------- REMOVER ----------------

    removidos = set(st.session_state.uploaded_docs) - set(current_files)

    for nome in removidos:

        ficheiro_path = docs_path / nome

        if ficheiro_path.exists():
            ficheiro_path.unlink()

        remover_documento(nome)

        st.session_state.uploaded_docs.remove(nome)

        st.warning(f"🗑️ Ficheiro removido: {nome}")
        st.toast(f"Removido: {nome}")

    # ---------------- NOVOS ----------------

    novos = False

    for file in uploaded_files or []:

        destino = docs_path / file.name

        if not destino.exists():

            with open(destino, "wb") as f:
                f.write(file.read())

            st.session_state.uploaded_docs.append(file.name)

            novos = True

    # ---------------- INDEXAÇÃO ----------------

    if novos:

        st.success("✅ Upload concluído")

        with st.spinner("📚 A indexar documentos..."):
            indexar_main()

        st.success("✅ Indexação concluída!")
        st.toast("Indexação pronta 🚀")

    # ---------------- DOCUMENTOS ----------------

    st.divider()

    st.subheader("📁 Documentos carregados")

    if st.session_state.uploaded_docs:

        for doc in st.session_state.uploaded_docs:
            st.markdown(f"📄 {doc}")

    else:
        st.caption("Sem documentos carregados.")

# ---------------- MAIN ----------------

st.title("🔍 Assistente de Documentos Internos")
st.caption(
    "Pesquisa inteligente com RAG + Tool Calling"
)

# ---------------- FUNÇÕES AUX ----------------

def extrair_excerto_relevante(texto, pergunta):

    frases = re.split(r'(?<=[.!?]) +', texto)

    pergunta_palavras = set(
        re.findall(r"\w+", pergunta.lower())
    )

    melhor_frase = ""
    melhor_score = 0

    for frase in frases:

        palavras = set(
            re.findall(r"\w+", frase.lower())
        )

        score = len(pergunta_palavras & palavras)

        if score > melhor_score:

            melhor_score = score
            melhor_frase = frase

    return melhor_frase if melhor_frase else texto[:300]


def destacar_palavras_na_frase(frase, pergunta):

    palavras = re.findall(
        r"\w+",
        pergunta.lower()
    )

    for palavra in set(palavras):

        if len(palavra) < 3:
            continue

        regex = re.compile(
            rf"({re.escape(palavra)})",
            re.IGNORECASE
        )

        frase = regex.sub(
            r"<mark>\1</mark>",
            frase
        )

    return frase

# ---------------- HISTÓRICO ----------------

for i, msg in enumerate(st.session_state.chat):

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])

        # ---------------- FONTE ----------------

        if msg.get("fonte"):

            fonte = msg["fonte"]
            
            
            st.markdown("#### Fonte utilizada")

            st.markdown(
                f"📄 {fonte['source']}"
            )

            if (
                fonte.get("path")
                and Path(fonte["path"]).exists()
            ):

                if st.button(
                    "📂 Abrir ficheiro",
                    key=f"btn_hist_{i}"
                ):

                    os.startfile(fonte["path"])

        # ---------------- DOWNLOAD ----------------

        if msg.get("ficheiro"):

            ficheiro = msg["ficheiro"]

            if Path(ficheiro).exists():

                with open(ficheiro, "rb") as f:

                    st.download_button(
                        label="⬇️ Download ficheiro",
                        data=f,
                        file_name=Path(ficheiro).name,
                        key=f"download_hist_{i}"
                    )

# ---------------- INPUT ----------------

pergunta = st.chat_input(
    "💬 Escreve a tua pergunta..."
)

# ---------------- NOVA PERGUNTA ----------------

if pergunta:

    # ---------------- USER ----------------

    st.session_state.chat.append({
        "role": "user",
        "content": pergunta
    })

    with st.chat_message("user"):
        st.markdown(pergunta)

    # ---------------- ASSISTANT ----------------

    with st.chat_message("assistant"):

        with st.spinner("🤖 A processar..."):

            try:

                resultado = executar_agente(pergunta)

                resposta = resultado["resposta"]

                fontes = resultado["fontes"]

                ficheiro = resultado["ficheiro"]

                fonte = fontes[0] if fontes else None

            except Exception as e:

                resposta = f"❌ Erro: {e}"

                fonte = None
                ficheiro = None

        # ---------------- RESPOSTA ----------------

        st.markdown(resposta)

        # ---------------- DOWNLOAD ----------------

        if ficheiro and Path(ficheiro).exists():

            st.success("📁 Resposta exportada")

            with open(ficheiro, "rb") as f:

                st.download_button(
                    label="⬇️ Download",
                    data=f,
                    file_name=Path(ficheiro).name,
                    key=f"download_new_{len(st.session_state.chat)}"
                )

        # ---------------- FONTE ----------------

        if fonte:

            st.markdown("### 📚 Fonte utilizada")

            st.markdown(
                f"📄 {fonte['source']}"
            )

            if (
                fonte.get("path")
                and Path(fonte["path"]).exists()
            ):

                if st.button(
                    "📂 Abrir ficheiro",
                    key=f"btn_new_{len(st.session_state.chat)}"
                ):

                    os.startfile(fonte["path"])

            st.markdown("### 🔍 Excerto relevante")

            excerto = extrair_excerto_relevante(
                fonte["text"],
                pergunta
            )

            texto_destacado = destacar_palavras_na_frase(
                excerto,
                pergunta
            )

            st.markdown(
                f"""
                <div style="
                    padding:10px;
                    border-radius:10px;
                    background:#f5f5f5
                ">
                {texto_destacado}
                </div>
                """,
                unsafe_allow_html=True
            )

    # ---------------- GUARDAR HISTÓRICO ----------------

    st.session_state.chat.append({

        "role": "assistant",

        "content": resposta,

        "fonte": {
            "source": fonte.get("source"),
            "path": fonte.get("path")
        } if fonte else None,

        "ficheiro": ficheiro
    })