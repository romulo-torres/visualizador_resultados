import streamlit as st
import json
import re

st.set_page_config(layout="wide")

st.title("🔍 Visualizador de Respostas LLM")

# ===== carregar JSONL =====
dados = []
with open("dados.jsonl", "r", encoding="utf-8") as f:
    for linha in f:
        dados.append(json.loads(linha))

# ===== selecionar exemplo =====
ids = [item["id"] for item in dados]
id_escolhido = st.selectbox(
    "Escolha o exemplo", 
    ids,
    index=0
    )

item = next(x for x in dados if x["id"] == id_escolhido)

# ===== selecionar tipo =====
tipo = st.selectbox(
    "Tipo de perturbação",
    ["original", "complex", "nl", "missing"],
    index=0
)

# ===== pegar dados =====
texto = item[f"txt_{tipo}"]
tempo = item.get(f"time_{tipo}", 0)
tps = item.get(f"tps_{tipo}", 0)

# ===== extrair resposta final =====
def extrair_boxed(texto):
    matches = re.findall(r"\\boxed\{(.*?)\}", texto)
    return matches[-1] if matches else "Não encontrado"

resposta_final = extrair_boxed(texto)

# ===== métricas de texto =====
num_chars = len(texto)
num_palavras = len(texto.split())
num_tokens_aprox = len(re.findall(r"\w+|\S", texto))  # aproximação

# ===== layout =====
st.subheader("📌 Ground Truth")
st.write(item["gt"])

st.subheader("📦 Resposta final do modelo")
st.write(resposta_final)

# ===== métricas =====
st.subheader("📊 Métricas")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("⏱ Tempo (s)", f"{tempo:.4f}")
    st.metric("⚡ Tokens/s", f"{tps:.2f}")

with col2:
    st.metric("🔤 Caracteres", num_chars)
    st.metric("📝 Palavras", num_palavras)

with col3:
    st.metric("🤖 Tokens (aprox)", num_tokens_aprox)

# ===== resposta completa =====
st.subheader("🧠 Resposta completa")
st.text_area("", texto, height=400, disabled=True)