import streamlit as st
import json
import re
import os

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    layout="wide",
    page_title="LLM Inspector",
    page_icon="🔬",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background: #0d0f14;
    color: #c8cdd8;
}
[data-testid="stSidebar"] {
    background: #111318 !important;
    border-right: 1px solid #1e2130;
}
[data-testid="stSidebar"] * { color: #8a90a0 !important; }
[data-testid="stSidebar"] .stRadio label:hover { color: #f5c842 !important; }
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] input:checked + div {
    background: #f5c842 !important;
    border-color: #f5c842 !important;
}
h1 { font-family: 'Syne', sans-serif !important; color: #f5f6f8 !important; letter-spacing: -1px; }
h2, h3 { font-family: 'Syne', sans-serif !important; color: #c8cdd8 !important; }
[data-testid="stMetric"] {
    background: #141720;
    border: 1px solid #1e2130;
    border-radius: 8px;
    padding: 14px 18px !important;
}
[data-testid="stMetricLabel"] { color: #555c72 !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1px; }
[data-testid="stMetricValue"] { color: #f5c842 !important; font-size: 22px !important; font-weight: 600; }
[data-testid="stMetricDelta"] { color: #4ecb8a !important; }
.badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 15px;
    letter-spacing: 1px;
}
.badge-true    { background: #0d2e1a; color: #4ecb8a; border: 1px solid #1a5c35; }
.badge-false   { background: #2e0d0d; color: #e05c5c; border: 1px solid #5c1a1a; }
.badge-unc     { background: #2a2310; color: #f5c842; border: 1px solid #5c4a15; }
.badge-err     { background: #1a1a2e; color: #7878c8; border: 1px solid #2e2e6e; }
/* classificacao de qualidade */
.qlabel {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}
.qlabel-correct { background: #0d2e1a; color: #4ecb8a; border: 1px solid #1a5c35; }
.qlabel-suspect { background: #2a1c00; color: #f5a623; border: 1px solid #7a5010; }
.qlabel-error   { background: #1a1a2e; color: #7878c8; border: 1px solid #2e2e6e; }
.resp-box {
    background: #0a0c10;
    border: 1px solid #1e2130;
    border-left: 3px solid #f5c842;
    border-radius: 6px;
    padding: 18px 20px;
    font-size: 13px;
    line-height: 1.7;
    max-height: 460px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    color: #b0b8cc;
}
.resp-box.suspect-box { border-left-color: #f5a623; }
.resp-box.error-box   { border-left-color: #7878c8; }
.override-box {
    background: #141720;
    border: 1px solid #f5c842;
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.cx-bar-bg  { background: #1e2130; border-radius: 4px; height: 8px; width: 100%; overflow: hidden; }
.cx-bar-fill { height: 8px; border-radius: 4px; transition: width .4s ease; }
.rank-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.rank-table th {
    background: #141720; color: #555c72; text-transform: uppercase;
    letter-spacing: 1px; font-size: 10px; padding: 10px 14px;
    border-bottom: 1px solid #1e2130; text-align: left;
}
.rank-table td { padding: 9px 14px; border-bottom: 1px solid #141720; color: #b0b8cc; vertical-align: middle; }
.rank-table tr:hover td { background: #13161f; }
.rank-table tr.current-row td { background: #1a1e2c; border-left: 3px solid #f5c842; }
.rank-medal { font-size: 16px; }
.rank-time-bar-bg { background: #1e2130; border-radius: 3px; height: 6px; width: 120px; display: inline-block; vertical-align: middle; overflow: hidden; }
.rank-time-bar-fill { height: 6px; border-radius: 3px; display: inline-block; }
.rank-correct { color: #4ecb8a; font-weight: 600; }
.rank-wrong   { color: #e05c5c; font-weight: 600; }
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    background: #141720 !important;
    border-color: #1e2130 !important;
    color: #c8cdd8 !important;
}
hr { border-color: #1e2130 !important; }
textarea {
    background: #0a0c10 !important;
    color: #b0b8cc !important;
    border-color: #1e2130 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
}
.stButton > button {
    background: #141720;
    border: 1px solid #f5c842;
    color: #f5c842;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    border-radius: 4px;
    transition: background .2s;
}
.stButton > button:hover { background: #1f2435; }
.bin-tag { display: inline-block; padding: 2px 10px; border-radius: 3px; font-size: 12px; font-weight: 600; margin-left: 6px; }
.q1 { background:#0d2e1a; color:#4ecb8a; }
.q2 { background:#1a2a10; color:#8ecb4e; }
.q3 { background:#2a2310; color:#f5c842; }
.q4 { background:#2e1010; color:#e07c5c; }
[data-baseweb="tab"] { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
.featured-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1px;
    background: #2a2310;
    color: #f5c842;
    border: 1px solid #5c4a15;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTES
# ============================================================
MAX_TOKENS_LLAMA = 32768   # limite usado na geração do llama.jsonl

OVERRIDE_FILE = "overrides.json"   # arquivo de overrides manuais

# IDs reprocessados manualmente (LLM sem "step by step" + LRM com teto maior
# de tokens), com log completo de prompt+resposta salvo por task.
FEATURED_IDS = [49, 53, 81, 84, 88, 126, 158, 166, 192, 200]

# Pastas onde ficam os logs de prompt+resposta gerados durante o rerun
# desses 10 IDs. Ajuste aqui (ou via sidebar) se a pasta de logs estiver em
# outro lugar relativo a onde o streamlit roda -- essas pastas foram criadas
# na maquina que rodou a geracao (deepseek-pibic) e podem precisar ser
# copiadas (scp/rsync) para onde este app roda.
PROMPT_LOG_DIR_DEFAULT_LLAMA = "logs_llm10ids"
PROMPT_LOG_DIR_DEFAULT_LRM   = "logs_rerun_10ids"


# ============================================================
# HELPERS — parsing e classificação
# ============================================================
def extrair_boxed(texto: str, is_reasoning: bool = True) -> str | None:
    """
    Retorna o label dentro de \\boxed{}.
    - Modelos reasoning (DeepSeek-R1): busca após </think>
    - Modelos instruct (LLaMA): busca no texto inteiro, sem depender de </think>
    """
    if is_reasoning:
        think_end   = texto.rfind("</think>")
        search_text = texto[think_end:] if think_end != -1 else texto
    else:
        # LLaMA não tem <think> — busca direto no texto completo
        search_text = texto

    matches = re.findall(r"\\boxed\{(.*?)\}", search_text, re.IGNORECASE)
    if matches:
        return matches[-1].strip().capitalize()
    return None


def classificar_qualidade(texto: str, tokens: int | None, max_tokens: int = MAX_TOKENS_LLAMA, is_reasoning: bool = False) -> str:
    """
    Classifica a qualidade do parsing:
      - 'correct' → contém \\boxed{label} válido
      - 'error'   → truncada (tokens >= max_tokens) ou sem nenhum label
      - 'suspect' → completa (não truncada) mas sem \\boxed{}
    """
    tem_boxed = extrair_boxed(texto, is_reasoning=is_reasoning) is not None
    truncada  = (tokens is not None) and (tokens >= max_tokens)

    if tem_boxed:
        return "correct"
    if truncada:
        return "error"
    return "suspect"


def badge_html(label: str) -> str:
    l = str(label).lower()
    if l == "true":   cls = "badge-true"
    elif l == "false": cls = "badge-false"
    elif l in ("uncertain", "uncertain"): cls = "badge-unc"
    else: cls = "badge-err"
    return f'<span class="badge {cls}">{str(label).upper()}</span>'


def qlabel_html(q: str) -> str:
    cls = {"correct": "qlabel-correct", "suspect": "qlabel-suspect", "error": "qlabel-error"}.get(q, "qlabel-error")
    icons = {"correct": "✓", "suspect": "⚠", "error": "✗"}
    return f'<span class="qlabel {cls}">{icons.get(q,"")} {q}</span>'


def bin_tag(val) -> str:
    if val is None: return ""
    q   = str(val).upper()
    cls = {"Q1": "q1", "Q2": "q2", "Q3": "q3", "Q4": "q4"}.get(q, "q1")
    return f'<span class="bin-tag {cls}">{q}</span>'


def bar(value: float, max_val: float, color: str) -> str:
    pct = min(100, int(value / max_val * 100)) if max_val > 0 else 0
    return (f'<div class="cx-bar-bg"><div class="cx-bar-fill" style="width:{pct}%;background:{color};"></div></div>')


def time_bar_html(value: float, max_val: float, color: str = "#f5c842") -> str:
    pct = min(100, int(value / max_val * 100)) if max_val > 0 else 0
    return (f'<div class="rank-time-bar-bg"><div class="rank-time-bar-fill" style="width:{pct}%;background:{color};"></div></div>')


# ============================================================
# HELPERS — logs de prompt (para os 10 IDs destacados)
# ============================================================
def extrair_secoes_log(conteudo: str):
    """
    Extrai (prompt, resposta) de um arquivo de log gerado por log_task_io
    (tanto a versao usada no pibic_v2.py/LRM quanto a versao usada no
    rerun_10ids_from_scratch.py/LLM -- os dois usam os mesmos marcadores
    'PROMPT ENVIADO' / 'RESPOSTA DO MODELO' + linhas de '=' e '-').
    """
    prompt_match = re.search(
        r"PROMPT ENVIADO.*?\n-{10,}\n(.*?)\n={10,}", conteudo, re.DOTALL
    )
    resposta_match = re.search(
        r"RESPOSTA DO MODELO.*?\n-{10,}\n(.*)$", conteudo, re.DOTALL
    )
    prompt   = prompt_match.group(1).strip() if prompt_match else None
    resposta = resposta_match.group(1).strip() if resposta_match else None
    return prompt, resposta


def carregar_log_prompt(item_id: int, tipo: str, log_dir: str):
    """Retorna (prompt, resposta, caminho_do_arquivo). prompt/resposta vem
    None se o arquivo nao existir ou nao puder ser parseado."""
    path = os.path.join(log_dir, f"id_{item_id}_task_{tipo}.log")
    if not os.path.exists(path):
        return None, None, path
    with open(path, "r", encoding="utf-8") as f:
        conteudo = f.read()
    prompt, resposta = extrair_secoes_log(conteudo)
    return prompt, resposta, path


# ============================================================
# OVERRIDES — persistência em arquivo local
# ============================================================
def carregar_overrides() -> dict:
    if os.path.exists(OVERRIDE_FILE):
        try:
            with open(OVERRIDE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def salvar_overrides(overrides: dict):
    with open(OVERRIDE_FILE, "w", encoding="utf-8") as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)


def override_key(item_id: int, tipo: str) -> str:
    return f"{item_id}__{tipo}"


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## 🔬 LLM Inspector")
    st.markdown("---")

    st.markdown("**Dataset**")
    arquivos_disponiveis = [
        f for f in ["deepseek_consertado.jsonl", "llama_labels.jsonl", "deepseek10.jsonl"]
        if os.path.exists(f)
    ]
    if not arquivos_disponiveis:
        st.error("Nenhum arquivo .jsonl encontrado.")
        st.stop()

    arquivo      = st.selectbox("Arquivo", arquivos_disponiveis, label_visibility="collapsed")
    is_llama     = "llama" in arquivo.lower()
    is_reasoning = not is_llama   # DeepSeek-R1 é reasoning; LLaMA instruct não é

    @st.cache_data
    def carregar(path):
        dados = []
        with open(path, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    dados.append(json.loads(linha))
        return dados

    dados = carregar(arquivo)
    ids   = [item["id"] for item in dados]

    st.markdown("---")

    # --- filtro de qualidade (só para llama) ---
    if is_llama:
        st.markdown("**Filtro de qualidade**")
        qualidades_disponiveis = ["correct", "suspect", "error"]
        q_filtro = st.multiselect(
            "Status parsing",
            qualidades_disponiveis,
            default=qualidades_disponiveis,
            key="q_f",
        )
    else:
        q_filtro = None

    st.markdown("**Filtros de complexidade**")
    nl_bins_disponiveis  = sorted({str(item.get("nl_bin", "")) for item in dados if item.get("nl_bin")})
    fol_bins_disponiveis = sorted({str(item.get("fol_bin", "")) for item in dados if item.get("fol_bin")})

    nl_filtro  = st.multiselect("NL bin",  nl_bins_disponiveis,  default=nl_bins_disponiveis,  key="nl_f")  if nl_bins_disponiveis  else []
    fol_filtro = st.multiselect("FOL bin", fol_bins_disponiveis, default=fol_bins_disponiveis, key="fol_f") if fol_bins_disponiveis else []

    st.markdown("**Ground truth**")
    gts       = sorted({str(item.get("gt", "")) for item in dados})
    gt_filtro = st.multiselect("Label", gts, default=gts, key="gt_f")

    # aplica filtros
    overrides = carregar_overrides()

    def item_qualidade(item, tipo="original") -> str:
        txt    = item.get(f"txt_{tipo}", "")
        tokens = item.get(f"tokens_{tipo}")
        return classificar_qualidade(txt, tokens)

    def item_ok(item):
        gt_ok  = str(item.get("gt", "")) in gt_filtro if gt_filtro else True
        nl_ok  = (not nl_filtro)  or (str(item.get("nl_bin",  "")) in nl_filtro)
        fol_ok = (not fol_filtro) or (str(item.get("fol_bin", "")) in fol_filtro)
        if is_llama and q_filtro is not None:
            q_ok = item_qualidade(item) in q_filtro
        else:
            q_ok = True
        return gt_ok and nl_ok and fol_ok and q_ok

    dados_filtrados = [d for d in dados if item_ok(d)]
    ids_filtrados   = [d["id"] for d in dados_filtrados]

    st.markdown("---")
    st.markdown("**⭐ Destaque**")
    apenas_destacados = st.checkbox(
        "Mostrar apenas os 10 exemplos com prompt salvo",
        value=False,
        key="dest_f",
    )
    if apenas_destacados:
        ids_filtrados = [i for i in ids_filtrados if i in FEATURED_IDS]

    with st.expander("⚙️ Pasta dos logs de prompt"):
        st.caption(
            "Os logs de prompt+resposta desses 10 IDs foram gerados na "
            "maquina que rodou a geracao. Se este app roda em outro lugar, "
            "copie as pastas para ca (ex.: `scp -r usuario@host:~/logs_llm10ids .`) "
            "e ajuste os caminhos abaixo se necessario."
        )
        log_dir_llama = st.text_input("Pasta (LLM / Llama)", value=PROMPT_LOG_DIR_DEFAULT_LLAMA)
        log_dir_lrm   = st.text_input("Pasta (LRM / DeepSeek)", value=PROMPT_LOG_DIR_DEFAULT_LRM)

    log_dir_atual = log_dir_llama if is_llama else log_dir_lrm

    st.markdown("---")
    st.markdown(f"**{len(dados_filtrados)}** / {len(dados)} exemplos")
    if apenas_destacados:
        st.markdown(f"**{len(ids_filtrados)}** / {len(FEATURED_IDS)} destacados (apos filtros)")

    if not ids_filtrados:
        st.warning("Nenhum exemplo com esses filtros.")
        st.stop()

    st.markdown("**Exemplo**")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        id_escolhido = st.selectbox(
            "ID",
            ids_filtrados,
            format_func=lambda x: f"⭐ {x}" if x in FEATURED_IDS else str(x),
            label_visibility="collapsed",
        )
    with col_b:
        idx_atual = ids_filtrados.index(id_escolhido)
        if st.button("▶", help="Próximo"):
            idx_atual    = (idx_atual + 1) % len(ids_filtrados)
            id_escolhido = ids_filtrados[idx_atual]

    st.markdown("**Perturbação**")
    item_test         = next((x for x in dados if x["id"] == id_escolhido), dados[0])
    tipos_disponiveis = [
        t for t in ["original", "complex", "nl", "missing", "shuffled", "junto", "irrelevant", "negation", "contradiction"]
        if f"txt_{t}" in item_test
    ] or ["original"]

    tipo = st.radio("Tipo", tipos_disponiveis, label_visibility="collapsed")


# ============================================================
# DADOS DO ITEM
# ============================================================
item   = next((x for x in dados if x["id"] == id_escolhido), None)
if item is None:
    st.error("Item não encontrado.")
    st.stop()

texto   = item.get(f"txt_{tipo}", "")
tempo   = item.get(f"time_{tipo}", 0) or 0
tps     = item.get(f"tps_{tipo}",  0) or 0
tokens  = item.get(f"tokens_{tipo}", 0) or 0
chars   = item.get(f"chars_{tipo}", len(texto))
words   = item.get(f"words_{tipo}", len(texto.split()))
gt      = item.get("gt", "—")
nl_wc   = item.get("nl_wc")
fol_tc  = item.get("fol_tc")
nl_bin  = item.get("nl_bin")
fol_bin = item.get("fol_bin")

# --- classificação de qualidade ---
qualidade      = classificar_qualidade(texto, tokens) if is_llama else "correct"
boxed_extraido = extrair_boxed(texto)

# --- override manual ---
ok_key   = override_key(id_escolhido, tipo)
override = overrides.get(ok_key)

# label efetivo: override > boxed > campo p_ > error
if override:
    pred_efetivo = override
elif boxed_extraido and boxed_extraido.capitalize() in ("True", "False", "Uncertain"):
    pred_efetivo = boxed_extraido.capitalize()
else:
    pred_efetivo = item.get(f"p_{tipo}", "Error")

acertou = str(pred_efetivo).lower() == str(gt).lower()

tem_prompt_log = id_escolhido in FEATURED_IDS


# ============================================================
# CABEÇALHO
# ============================================================
titulo_extra = " &nbsp; <span class='featured-badge'>⭐ destacado</span>" if tem_prompt_log else ""
st.markdown(f"# Exemplo `{id_escolhido}` — _{tipo}_{titulo_extra}", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
with c1:
    st.markdown(f"**Ground truth** &nbsp; {badge_html(str(gt))}", unsafe_allow_html=True)
with c2:
    label_src = " _(override)_" if override else (" _(boxed)_" if boxed_extraido else " _(fallback)_")
    st.markdown(f"**Predição**{label_src} &nbsp; {badge_html(str(pred_efetivo))}", unsafe_allow_html=True)
with c3:
    if is_llama:
        st.markdown(f"**Qualidade** &nbsp; {qlabel_html(qualidade)}", unsafe_allow_html=True)
with c4:
    acerto_txt = "✅ Correto" if acertou else "❌ Errado"
    st.markdown(f"**Resultado** &nbsp; `{acerto_txt}`")

st.markdown("---")


# ============================================================
# TABS
# ============================================================
tab_labels = ["📊 Métricas", "🧩 Complexidade", "🧠 Resposta", "⏱ Ranking"]
if tem_prompt_log:
    tab_labels.append("📝 Prompt")
if is_llama:
    tab_labels.append("✏️ Override")

tabs = st.tabs(tab_labels)
tab1, tab2, tab3, tab4 = tabs[0], tabs[1], tabs[2], tabs[3]

_idx_next  = 4
tab_prompt = None
if tem_prompt_log:
    tab_prompt = tabs[_idx_next]
    _idx_next += 1
tab5 = tabs[_idx_next] if is_llama else None


# ---------- TAB 1: Métricas ----------
with tab1:
    st.markdown("")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric("Tempo (s)", f"{tempo:.2f}")
    with m2: st.metric("Tokens / s", f"{tps:.1f}")
    with m3: st.metric("Tokens gerados", f"{int(tokens):,}" if tokens else "—")
    with m4: st.metric("Caracteres", f"{int(chars):,}" if chars else f"{len(texto):,}")
    with m5: st.metric("Palavras", f"{int(words):,}" if words else f"{len(texto.split()):,}")

    if is_llama:
        st.markdown("---")
        st.markdown("#### Diagnóstico de parsing")
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown(f"**\\\\boxed{{}}** encontrado: `{'Sim — ' + boxed_extraido if boxed_extraido else 'Não'}`")
        with d2:
            truncada = tokens and tokens >= MAX_TOKENS_LLAMA
            st.markdown(f"**Truncada**: `{'Sim (' + str(tokens) + ' tokens)' if truncada else 'Não'}`")
        with d3:
            st.markdown(f"**Override ativo**: `{'Sim — ' + override if override else 'Não'}`")

    if len(tipos_disponiveis) > 1:
        st.markdown("#### Comparação de tempo entre perturbações")
        comp = {t: float(v) for t in tipos_disponiveis if (v := item.get(f"time_{t}")) is not None}
        if comp:
            max_t = max(comp.values()) or 1
            for t, v in comp.items():
                destaque = " ← atual" if t == tipo else ""
                st.markdown(
                    f"`{t:<14}` {bar(v, max_t, '#f5c842' if t == tipo else '#2a3050')} &nbsp; **{v:.2f}s**{destaque}",
                    unsafe_allow_html=True,
                )
                st.markdown("")


# ---------- TAB 2: Complexidade ----------
with tab2:
    st.markdown("")
    if nl_wc is None and fol_tc is None:
        st.info("Dados de complexidade não encontrados.")
    else:
        NL_MAX, FOL_MAX = 180, 400
        cx1, cx2 = st.columns(2)
        with cx1:
            st.markdown("##### NL — linguagem natural")
            st.markdown(f"Contagem de palavras: **{nl_wc}** {bin_tag(nl_bin)}", unsafe_allow_html=True)
            st.markdown(bar(nl_wc or 0, NL_MAX, "#4ecb8a"), unsafe_allow_html=True)
            st.caption("Q1 = exemplos curtos · Q4 = exemplos longos")
        with cx2:
            st.markdown("##### FOL — lógica de primeira ordem")
            st.markdown(f"Tokens lógicos: **{fol_tc}** {bin_tag(fol_bin)}", unsafe_allow_html=True)
            st.markdown(bar(fol_tc or 0, FOL_MAX, "#7878c8"), unsafe_allow_html=True)
            st.caption("Q1 = fórmulas simples · Q4 = fórmulas complexas")

        st.markdown("---")
        st.markdown("##### Posição nos quartis")
        qcols = st.columns(4)
        cores = {"Q1": "#4ecb8a", "Q2": "#8ecb4e", "Q3": "#f5c842", "Q4": "#e07c5c"}
        for i, q in enumerate(["Q1", "Q2", "Q3", "Q4"]):
            with qcols[i]:
                cor = cores[q]
                for label_q, val_q in [("NL", nl_bin), ("FOL", fol_bin)]:
                    ativo  = str(val_q).upper() == q
                    border = f"2px solid {cor}" if ativo else "2px solid #1e2130"
                    color  = cor if ativo else "#333a50"
                    st.markdown(
                        f"""<div style="border:{border};border-radius:6px;padding:10px;
                        text-align:center;margin-bottom:8px;background:#0d0f14;">
                        <div style="font-size:11px;color:#555c72;text-transform:uppercase;letter-spacing:1px;">{label_q}</div>
                        <div style="font-size:18px;font-weight:700;color:{color};">{q}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )


# ---------- TAB 3: Resposta ----------
with tab3:
    st.markdown("")
    if not texto:
        st.warning("Sem texto gerado para esta combinação.")
    else:
        # classe visual depende da qualidade
        box_cls = {"correct": "", "suspect": " suspect-box", "error": " error-box"}.get(qualidade, "")
        if is_llama and qualidade != "correct":
            aviso = {
                "suspect": "⚠️  **Resposta suspeita** — completa mas sem `\\boxed{}`. Label pode estar no texto em outro formato.",
                "error":   "✗  **Resposta inválida** — truncada ou sem label detectável.",
            }.get(qualidade, "")
            st.markdown(aviso)

        st.markdown(f'<div class="resp-box{box_cls}">{texto}</div>', unsafe_allow_html=True)
        st.markdown("")
        if st.button("📋 Mostrar como código"):
            st.code(texto, language="text")


# ---------- TAB 4: Ranking de Tempo ----------
with tab4:
    st.markdown("")
    todos_tipos = [
        t for t in ["original", "complex", "nl", "missing", "shuffled", "junto", "irrelevant", "negation", "contradiction"]
        if any(f"time_{t}" in d for d in dados_filtrados)
    ]
    if not todos_tipos:
        st.warning("Nenhum campo `time_*` encontrado.")
    else:
        rc1, rc2, rc3 = st.columns([2, 2, 2])
        with rc1:
            tipo_rank = st.selectbox("Perturbação", todos_tipos,
                                     index=todos_tipos.index(tipo) if tipo in todos_tipos else 0, key="rank_tipo")
        with rc2:
            ordem = st.radio("Ordem", ["⬆ Crescente", "⬇ Decrescente"], horizontal=True, key="rank_ordem")
        with rc3:
            n_show = st.number_input("Top N (0 = todos)", min_value=0,
                                     max_value=len(dados_filtrados), value=min(50, len(dados_filtrados)), step=10)

        crescente = "Crescente" in ordem

        registros = []
        for d in dados_filtrados:
            t_val = d.get(f"time_{tipo_rank}")
            if t_val is None:
                continue
            txt_r  = d.get(f"txt_{tipo_rank}", "")
            tok_r  = d.get(f"tokens_{tipo_rank}")
            ok_r   = override_key(d["id"], tipo_rank)
            ov_r   = overrides.get(ok_r)
            boxed_r = extrair_boxed(txt_r)
            if ov_r:
                p_r = ov_r
            elif boxed_r and boxed_r.capitalize() in ("True", "False", "Uncertain"):
                p_r = boxed_r.capitalize()
            else:
                p_r = str(d.get(f"p_{tipo_rank}", "Error"))
            gt_r    = d.get("gt", "—")
            correto = str(p_r).lower() == str(gt_r).lower()
            qual_r  = classificar_qualidade(txt_r, tok_r) if is_llama else "correct"
            registros.append({
                "id": d["id"], "time": float(t_val), "pred": p_r,
                "gt": gt_r, "correto": correto, "tokens": tok_r,
                "tps": d.get(f"tps_{tipo_rank}"), "qualidade": qual_r,
            })

        registros.sort(key=lambda x: x["time"], reverse=not crescente)
        registros_show = registros[:n_show] if n_show else registros
        max_time  = max(r["time"] for r in registros) if registros else 1
        total     = len(registros)
        n_correct = sum(1 for r in registros if r["correto"])

        s1, s2, s3, s4 = st.columns(4)
        with s1: st.metric("Exemplos", total)
        with s2: st.metric("Acurácia", f"{100*n_correct/total:.1f}%" if total else "—")
        with s3: st.metric("Tempo médio", f"{sum(r['time'] for r in registros)/total:.2f}s" if total else "—")
        with s4: st.metric("Tempo máx", f"{max_time:.2f}s")

        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        linhas = []
        for i, r in enumerate(registros_show):
            is_cur   = r["id"] == id_escolhido
            row_cls  = "current-row" if is_cur else ""
            medal    = medals.get(i, "")
            cor_barra = "#4ecb8a" if r["correto"] else "#e05c5c"
            correto_html = '<span class="rank-correct">✓</span>' if r["correto"] else '<span class="rank-wrong">✗</span>'
            tps_str   = f"{r['tps']:.1f}" if r["tps"] else "—"
            tok_str   = f"{int(r['tokens']):,}" if r["tokens"] else "—"
            qual_html = qlabel_html(r["qualidade"]) if is_llama else ""
            estrela   = "⭐ " if r["id"] in FEATURED_IDS else ""
            linhas.append(f"""<tr class="{row_cls}">
                <td style="color:#555c72">{i+1}</td>
                <td class="rank-medal">{medal}</td>
                <td style="font-weight:600;color:{'#f5c842' if is_cur else '#c8cdd8'}">{'› ' if is_cur else ''}{estrela}{r['id']}</td>
                <td><span style="font-weight:600;color:#f5f6f8">{r['time']:.3f}s</span> &nbsp; {time_bar_html(r['time'],max_time,cor_barra)}</td>
                <td>{badge_html(r['gt'])}</td>
                <td>{badge_html(r['pred'])}</td>
                <td>{correto_html}</td>
                <td style="color:#555c72">{tok_str}</td>
                <td style="color:#555c72">{tps_str}</td>
                {'<td>' + qual_html + '</td>' if is_llama else ''}
            </tr>""")

        qual_th = "<th>Qualidade</th>" if is_llama else ""
        tabela  = f"""<table class="rank-table"><thead><tr>
            <th>#</th><th></th><th>ID</th><th>Tempo</th>
            <th>GT</th><th>Pred</th><th>✓</th><th>Tokens</th><th>tok/s</th>{qual_th}
        </tr></thead><tbody>{''.join(linhas)}</tbody></table>"""
        st.markdown(f'<div style="overflow-x:auto;max-height:600px;overflow-y:auto;">{tabela}</div>',
                    unsafe_allow_html=True)

        pos = next((i+1 for i, r in enumerate(registros) if r["id"] == id_escolhido), None)
        if pos and not any(r["id"] == id_escolhido for r in registros_show):
            st.caption(f"ℹ️ Exemplo `{id_escolhido}` está na posição **{pos}** de {total}.")


# ---------- TAB PROMPT: só para os 10 IDs destacados ----------
if tem_prompt_log and tab_prompt is not None:
    with tab_prompt:
        st.markdown("")
        prompt_txt, resposta_log, log_path = carregar_log_prompt(id_escolhido, tipo, log_dir_atual)

        if prompt_txt is None:
            st.warning(
                f"Log não encontrado em `{log_path}`.\n\n"
                "Confira se a pasta de logs foi copiada para este servidor "
                "(veja **⚙️ Pasta dos logs de prompt** na sidebar) e se o "
                "nome do arquivo bate com `id_<id>_task_<task>.log`."
            )
        else:
            st.markdown("##### Prompt enviado ao modelo")
            st.caption("Texto completo, já após `apply_chat_template` — exatamente o que foi tokenizado e enviado.")
            st.markdown(f'<div class="resp-box">{prompt_txt}</div>', unsafe_allow_html=True)
            st.markdown("")
            if st.button("📋 Mostrar prompt como código", key="prompt_code_btn"):
                st.code(prompt_txt, language="text")

            if resposta_log is not None:
                st.markdown("---")
                st.markdown("##### Resposta salva no log (para conferência)")
                st.caption("Deve ser idêntica à aba 🧠 Resposta — vem do mesmo arquivo de log.")
                with st.expander("Ver resposta do log"):
                    st.markdown(f'<div class="resp-box">{resposta_log}</div>', unsafe_allow_html=True)


# ---------- TAB 5 (ou 6): Override manual (só llama) ----------
if is_llama and tab5 is not None:
    with tab5:
        st.markdown("")
        st.markdown("### Override manual de label")
        st.markdown(
            "Use quando o parser falha mas a resposta contém o label de forma não-padrão. "
            "O override substitui a predição para fins de análise e é salvo em `overrides.json`."
        )

        st.markdown("---")

        # Info do estado atual
        i1, i2, i3 = st.columns(3)
        with i1:
            st.markdown(f"**\\\\boxed{{}} extraído:** `{boxed_extraido or 'Não encontrado'}`")
        with i2:
            st.markdown(f"**Qualidade:** {qlabel_html(qualidade)}", unsafe_allow_html=True)
        with i3:
            st.markdown(f"**Override atual:** `{override or 'Nenhum'}`")

        st.markdown("")

        # Seletor de label
        opcoes_label = ["True", "False", "Uncertain"]
        label_sel = st.radio(
            "Escolha o label correto",
            opcoes_label,
            index=opcoes_label.index(override) if override in opcoes_label else 0,
            horizontal=True,
            key="override_sel",
        )

        col_salvar, col_remover, col_vazio = st.columns([1, 1, 3])
        with col_salvar:
            if st.button("💾 Salvar override"):
                overrides_atuais = carregar_overrides()
                overrides_atuais[ok_key] = label_sel
                salvar_overrides(overrides_atuais)
                st.success(f"Override salvo: id={id_escolhido} tipo={tipo} → **{label_sel}**")
                st.rerun()

        with col_remover:
            if override and st.button("🗑 Remover override"):
                overrides_atuais = carregar_overrides()
                overrides_atuais.pop(ok_key, None)
                salvar_overrides(overrides_atuais)
                st.success("Override removido.")
                st.rerun()

        st.markdown("---")

        # Lista todos os overrides salvos
        todos_overrides = carregar_overrides()
        if todos_overrides:
            st.markdown("#### Overrides salvos")
            linhas_ov = []
            for k, v in sorted(todos_overrides.items()):
                partes = k.split("__")
                id_ov  = partes[0] if len(partes) > 0 else k
                tp_ov  = partes[1] if len(partes) > 1 else "—"
                linhas_ov.append(f"<tr><td>{id_ov}</td><td>{tp_ov}</td><td>{badge_html(v)}</td></tr>")
            tabela_ov = f"""<table class="rank-table"><thead><tr>
                <th>ID</th><th>Tipo</th><th>Label Override</th>
            </tr></thead><tbody>{''.join(linhas_ov)}</tbody></table>"""
            st.markdown(f'<div style="max-height:300px;overflow-y:auto;">{tabela_ov}</div>',
                        unsafe_allow_html=True)

            st.markdown("")
            if st.button("🗑 Limpar TODOS os overrides"):
                salvar_overrides({})
                st.success("Todos os overrides removidos.")
                st.rerun()
        else:
            st.info("Nenhum override salvo ainda.")


# ============================================================
# RODAPÉ — resumo de suspeitos (só llama)
# ============================================================
if is_llama:
    st.markdown("---")
    n_correct_all = sum(1 for d in dados_filtrados if classificar_qualidade(d.get("txt_original",""), d.get("tokens_original")) == "correct")
    n_suspect_all = sum(1 for d in dados_filtrados if classificar_qualidade(d.get("txt_original",""), d.get("tokens_original")) == "suspect")
    n_error_all   = sum(1 for d in dados_filtrados if classificar_qualidade(d.get("txt_original",""), d.get("tokens_original")) == "error")
    n_override_all = len(carregar_overrides())

    f1, f2, f3, f4 = st.columns(4)
    with f1: st.metric("✓ correct (original)",  n_correct_all)
    with f2: st.metric("⚠ suspect (original)",  n_suspect_all)
    with f3: st.metric("✗ error (original)",    n_error_all)
    with f4: st.metric("✏️ overrides salvos",    n_override_all)