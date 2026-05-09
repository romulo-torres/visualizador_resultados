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

# ============================================================
# CSS — estética "terminal científico": fundo escuro, mono, acentos âmbar
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=Syne:wght@400;700;800&display=swap');

/* ---- raiz ---- */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background: #0d0f14;
    color: #c8cdd8;
}

/* ---- sidebar ---- */
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

/* ---- título principal ---- */
h1 { font-family: 'Syne', sans-serif !important; color: #f5f6f8 !important; letter-spacing: -1px; }
h2, h3 { font-family: 'Syne', sans-serif !important; color: #c8cdd8 !important; }

/* ---- metric cards ---- */
[data-testid="stMetric"] {
    background: #141720;
    border: 1px solid #1e2130;
    border-radius: 8px;
    padding: 14px 18px !important;
}
[data-testid="stMetricLabel"] { color: #555c72 !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1px; }
[data-testid="stMetricValue"] { color: #f5c842 !important; font-size: 22px !important; font-weight: 600; }
[data-testid="stMetricDelta"] { color: #4ecb8a !important; }

/* ---- badges de resultado ---- */
.badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 15px;
    letter-spacing: 1px;
}
.badge-true  { background: #0d2e1a; color: #4ecb8a; border: 1px solid #1a5c35; }
.badge-false { background: #2e0d0d; color: #e05c5c; border: 1px solid #5c1a1a; }
.badge-unc   { background: #2a2310; color: #f5c842; border: 1px solid #5c4a15; }
.badge-err   { background: #1a1a2e; color: #7878c8; border: 1px solid #2e2e6e; }

/* ---- painel de texto ---- */
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

/* ---- barra de complexidade ---- */
.cx-bar-bg {
    background: #1e2130;
    border-radius: 4px;
    height: 8px;
    width: 100%;
    overflow: hidden;
}
.cx-bar-fill {
    height: 8px;
    border-radius: 4px;
    transition: width .4s ease;
}

/* ---- ranking table ---- */
.rank-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.rank-table th {
    background: #141720;
    color: #555c72;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 10px;
    padding: 10px 14px;
    border-bottom: 1px solid #1e2130;
    text-align: left;
}
.rank-table td {
    padding: 9px 14px;
    border-bottom: 1px solid #141720;
    color: #b0b8cc;
    vertical-align: middle;
}
.rank-table tr:hover td { background: #13161f; }
.rank-table tr.current-row td { background: #1a1e2c; border-left: 3px solid #f5c842; }
.rank-medal { font-size: 16px; }
.rank-time-bar-bg {
    background: #1e2130;
    border-radius: 3px;
    height: 6px;
    width: 120px;
    display: inline-block;
    vertical-align: middle;
    overflow: hidden;
}
.rank-time-bar-fill {
    height: 6px;
    border-radius: 3px;
    display: inline-block;
}
.rank-correct { color: #4ecb8a; font-weight: 600; }
.rank-wrong   { color: #e05c5c; font-weight: 600; }

/* ---- selectbox / number_input ---- */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    background: #141720 !important;
    border-color: #1e2130 !important;
    color: #c8cdd8 !important;
}

/* ---- divider ---- */
hr { border-color: #1e2130 !important; }

/* ---- text_area ---- */
textarea {
    background: #0a0c10 !important;
    color: #b0b8cc !important;
    border-color: #1e2130 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
}

/* ---- botão ---- */
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

/* ---- tag de bin ---- */
.bin-tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 600;
    margin-left: 6px;
}
.q1 { background:#0d2e1a; color:#4ecb8a; }
.q2 { background:#1a2a10; color:#8ecb4e; }
.q3 { background:#2a2310; color:#f5c842; }
.q4 { background:#2e1010; color:#e07c5c; }

/* tab labels */
[data-baseweb="tab"] { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================
def badge_html(label: str) -> str:
    l = label.lower()
    if l == "true":
        cls = "badge-true"
    elif l == "false":
        cls = "badge-false"
    elif l == "uncertain":
        cls = "badge-unc"
    else:
        cls = "badge-err"
    return f'<span class="badge {cls}">{label.upper()}</span>'


def extrair_boxed(texto: str) -> str:
    matches = re.findall(r"\\boxed\{(.*?)\}", texto)
    return matches[-1].strip() if matches else "Não encontrado"


def bin_tag(val) -> str:
    if val is None:
        return ""
    q = str(val).upper()
    cls = {"Q1": "q1", "Q2": "q2", "Q3": "q3", "Q4": "q4"}.get(q, "q1")
    return f'<span class="bin-tag {cls}">{q}</span>'


def bar(value: float, max_val: float, color: str) -> str:
    pct = min(100, int(value / max_val * 100)) if max_val > 0 else 0
    return (
        f'<div class="cx-bar-bg">'
        f'<div class="cx-bar-fill" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )


def time_bar_html(value: float, max_val: float, color: str = "#f5c842") -> str:
    pct = min(100, int(value / max_val * 100)) if max_val > 0 else 0
    return (
        f'<div class="rank-time-bar-bg">'
        f'<div class="rank-time-bar-fill" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )


# ============================================================
# SIDEBAR — controles
# ============================================================
with st.sidebar:
    st.markdown("## 🔬 LLM Inspector")
    st.markdown("---")

    # --- dataset ---
    st.markdown("**Dataset**")
    arquivos_disponiveis = [
        f for f in ["dados.jsonl", "dados2.jsonl", "dados_llama-instruct.jsonl", "dados_llama-instruct-original.jsonl"]
        if os.path.exists(f)
    ]
    if not arquivos_disponiveis:
        st.error("Nenhum arquivo .jsonl encontrado.")
        st.stop()

    arquivo = st.selectbox("Arquivo", arquivos_disponiveis, label_visibility="collapsed")

    # --- carregar dados ---
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
    ids = [item["id"] for item in dados]

    st.markdown("---")

    # --- filtro por complexidade ---
    st.markdown("**Filtros de complexidade**")

    nl_bins_disponiveis = sorted({str(item.get("nl_bin", "")) for item in dados if item.get("nl_bin")})
    fol_bins_disponiveis = sorted({str(item.get("fol_bin", "")) for item in dados if item.get("fol_bin")})

    if nl_bins_disponiveis:
        nl_filtro = st.multiselect("NL bin (quartil)", nl_bins_disponiveis, default=nl_bins_disponiveis, key="nl_f")
    else:
        nl_filtro = []

    if fol_bins_disponiveis:
        fol_filtro = st.multiselect("FOL bin (quartil)", fol_bins_disponiveis, default=fol_bins_disponiveis, key="fol_f")
    else:
        fol_filtro = []

    # --- filtro por ground truth ---
    st.markdown("**Ground truth**")
    gts = sorted({str(item.get("gt", "")) for item in dados})
    gt_filtro = st.multiselect("Label", gts, default=gts, key="gt_f")

    # --- aplicar filtros ---
    def item_ok(item):
        gt_ok = str(item.get("gt", "")) in gt_filtro if gt_filtro else True
        nl_ok = (not nl_filtro) or (str(item.get("nl_bin", "")) in nl_filtro)
        fol_ok = (not fol_filtro) or (str(item.get("fol_bin", "")) in fol_filtro)
        return gt_ok and nl_ok and fol_ok

    dados_filtrados = [d for d in dados if item_ok(d)]
    ids_filtrados = [d["id"] for d in dados_filtrados]

    st.markdown("---")
    st.markdown(f"**{len(dados_filtrados)}** / {len(dados)} exemplos")

    if not ids_filtrados:
        st.warning("Nenhum exemplo com esses filtros.")
        st.stop()

    # --- seleção de ID ---
    st.markdown("**Exemplo**")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        id_escolhido = st.selectbox("ID", ids_filtrados, label_visibility="collapsed")
    with col_b:
        idx_atual = ids_filtrados.index(id_escolhido)
        if st.button("▶", help="Próximo"):
            idx_atual = (idx_atual + 1) % len(ids_filtrados)
            id_escolhido = ids_filtrados[idx_atual]

    # --- tipo de perturbação ---
    st.markdown("**Perturbação**")
    tipos_disponiveis = []
    item_test = next((x for x in dados if x["id"] == id_escolhido), dados[0])
    for t in ["original", "complex", "nl", "missing", "shuffled", "junto", "irrelevant", "negation", "contradiction"]:
        if f"txt_{t}" in item_test:
            tipos_disponiveis.append(t)

    if not tipos_disponiveis:
        tipos_disponiveis = ["original"]

    tipo = st.radio("Tipo", tipos_disponiveis, label_visibility="collapsed")


# ============================================================
# DADOS DO ITEM SELECIONADO
# ============================================================
item = next((x for x in dados if x["id"] == id_escolhido), None)
if item is None:
    st.error("Item não encontrado.")
    st.stop()

texto    = item.get(f"txt_{tipo}", "")
tempo    = item.get(f"time_{tipo}", 0) or 0
tps      = item.get(f"tps_{tipo}", 0) or 0
tokens   = item.get(f"tokens_{tipo}", 0) or 0
chars    = item.get(f"chars_{tipo}", len(texto))
words    = item.get(f"words_{tipo}", len(texto.split()))
pred     = item.get(f"p_{tipo}", extrair_boxed(texto))
gt       = item.get("gt", "—")

nl_wc    = item.get("nl_wc")
fol_tc   = item.get("fol_tc")
nl_bin   = item.get("nl_bin")
fol_bin  = item.get("fol_bin")

acertou  = str(pred).lower() == str(gt).lower()


# ============================================================
# CABEÇALHO
# ============================================================
st.markdown(f"# Exemplo `{id_escolhido}` — _{tipo}_")

c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    st.markdown(f"**Ground truth** &nbsp; {badge_html(str(gt))}", unsafe_allow_html=True)
with c2:
    st.markdown(f"**Predição** &nbsp; {badge_html(str(pred))}", unsafe_allow_html=True)
with c3:
    acerto_txt = "✅ Correto" if acertou else "❌ Errado"
    st.markdown(f"**Resultado** &nbsp; `{acerto_txt}`")

st.markdown("---")


# ============================================================
# TABS: Métricas | Complexidade | Resposta completa | Ranking de Tempo
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Métricas de geração",
    "🧩 Complexidade",
    "🧠 Resposta completa",
    "⏱ Ranking de Tempo",
])

# ---------- TAB 1: Métricas de geração ----------
with tab1:
    st.markdown("")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Tempo (s)", f"{tempo:.2f}")
    with m2:
        st.metric("Tokens / s", f"{tps:.1f}")
    with m3:
        st.metric("Tokens gerados", f"{int(tokens):,}" if tokens else "—")
    with m4:
        st.metric("Caracteres", f"{int(chars):,}" if chars else f"{len(texto):,}")
    with m5:
        st.metric("Palavras", f"{int(words):,}" if words else f"{len(texto.split()):,}")

    # Comparação entre tipos disponíveis (se houver mais de 1)
    if len(tipos_disponiveis) > 1:
        st.markdown("#### Comparação de tempo entre perturbações")
        comp = {}
        for t in tipos_disponiveis:
            v = item.get(f"time_{t}")
            if v is not None:
                comp[t] = float(v)
        if comp:
            max_t = max(comp.values()) or 1
            for t, v in comp.items():
                pct = int(v / max_t * 100)
                destaque = " ← atual" if t == tipo else ""
                st.markdown(
                    f"`{t:<14}` {bar(v, max_t, '#f5c842' if t == tipo else '#2a3050')} "
                    f"&nbsp; **{v:.2f}s**{destaque}",
                    unsafe_allow_html=True,
                )
                st.markdown("")

# ---------- TAB 2: Complexidade ----------
with tab2:
    st.markdown("")

    if nl_wc is None and fol_tc is None:
        st.info("Dados de complexidade não encontrados neste arquivo. "
                "Execute o pipeline com `build_complexity_map()` para gerar `nl_wc`, `fol_tc`, `nl_bin`, `fol_bin`.")
    else:
        cx1, cx2 = st.columns(2)

        # referências para barras (percentis máximos aproximados do FOLIO validation)
        NL_MAX  = 180
        FOL_MAX = 400

        with cx1:
            st.markdown("##### NL — linguagem natural")
            st.markdown(
                f"Contagem de palavras: **{nl_wc}** "
                f"{bin_tag(nl_bin)}",
                unsafe_allow_html=True,
            )
            st.markdown(bar(nl_wc or 0, NL_MAX, "#4ecb8a"), unsafe_allow_html=True)
            st.caption(f"Q1 = exemplos curtos · Q4 = exemplos longos")

        with cx2:
            st.markdown("##### FOL — lógica de primeira ordem")
            st.markdown(
                f"Tokens lógicos: **{fol_tc}** "
                f"{bin_tag(fol_bin)}",
                unsafe_allow_html=True,
            )
            st.markdown(bar(fol_tc or 0, FOL_MAX, "#7878c8"), unsafe_allow_html=True)
            st.caption(f"Q1 = fórmulas simples · Q4 = fórmulas complexas")

        st.markdown("---")
        st.markdown("##### Posição nos quartis")
        qcols = st.columns(4)
        for i, q in enumerate(["Q1", "Q2", "Q3", "Q4"]):
            with qcols[i]:
                nl_ativo  = str(nl_bin).upper()  == q
                fol_ativo = str(fol_bin).upper() == q
                cores = {
                    "Q1": "#4ecb8a", "Q2": "#8ecb4e",
                    "Q3": "#f5c842", "Q4": "#e07c5c"
                }
                cor = cores[q]
                border_nl  = f"2px solid {cor}" if nl_ativo  else "2px solid #1e2130"
                border_fol = f"2px solid {cor}" if fol_ativo else "2px solid #1e2130"

                st.markdown(
                    f"""<div style="border:{border_nl};border-radius:6px;padding:10px;
                    text-align:center;margin-bottom:8px;background:#0d0f14;">
                    <div style="font-size:11px;color:#555c72;text-transform:uppercase;letter-spacing:1px;">NL</div>
                    <div style="font-size:18px;font-weight:700;color:{cor if nl_ativo else '#333a50'};">{q}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""<div style="border:{border_fol};border-radius:6px;padding:10px;
                    text-align:center;background:#0d0f14;">
                    <div style="font-size:11px;color:#555c72;text-transform:uppercase;letter-spacing:1px;">FOL</div>
                    <div style="font-size:18px;font-weight:700;color:{cor if fol_ativo else '#333a50'};">{q}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

# ---------- TAB 3: Resposta completa ----------
with tab3:
    st.markdown("")

    if not texto:
        st.warning("Sem texto gerado para esta combinação.")
    else:
        st.markdown(
            f'<div class="resp-box">{texto}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")

        bcol1, bcol2 = st.columns([1, 4])
        with bcol1:
            if st.button("📋 Copiar (código)"):
                st.code(texto, language="text")


# ---------- TAB 4: Ranking de Tempo ----------
with tab4:
    st.markdown("")

    # Detectar todos os tipos disponíveis no dataset inteiro
    todos_tipos = []
    for t in ["original", "complex", "nl", "missing", "shuffled", "junto", "irrelevant", "negation", "contradiction"]:
        if any(f"time_{t}" in d for d in dados_filtrados):
            todos_tipos.append(t)

    if not todos_tipos:
        st.warning("Nenhum campo `time_*` encontrado nos dados filtrados.")
    else:
        # Controles do ranking
        rc1, rc2, rc3 = st.columns([2, 2, 2])
        with rc1:
            tipo_rank = st.selectbox(
                "Perturbação",
                todos_tipos,
                index=todos_tipos.index(tipo) if tipo in todos_tipos else 0,
                key="rank_tipo",
            )
        with rc2:
            ordem = st.radio(
                "Ordem",
                ["⬆ Crescente (mais rápido)", "⬇ Decrescente (mais lento)"],
                horizontal=True,
                key="rank_ordem",
            )
        with rc3:
            n_show = st.number_input(
                "Exibir top N (0 = todos)",
                min_value=0,
                max_value=len(dados_filtrados),
                value=min(50, len(dados_filtrados)),
                step=10,
                key="rank_n",
            )

        crescente = "Crescente" in ordem

        # Montar lista ordenada
        registros = []
        for d in dados_filtrados:
            t_val = d.get(f"time_{tipo_rank}")
            if t_val is not None:
                p_val = d.get(f"p_{tipo_rank}", extrair_boxed(d.get(f"txt_{tipo_rank}", "")))
                gt_val = d.get("gt", "—")
                correto = str(p_val).lower() == str(gt_val).lower()
                registros.append({
                    "id":      d["id"],
                    "time":    float(t_val),
                    "pred":    str(p_val),
                    "gt":      str(gt_val),
                    "correto": correto,
                    "tokens":  d.get(f"tokens_{tipo_rank}"),
                    "tps":     d.get(f"tps_{tipo_rank}"),
                })

        if not registros:
            st.warning(f"Nenhum exemplo com `time_{tipo_rank}` nos dados filtrados.")
        else:
            registros.sort(key=lambda x: x["time"], reverse=not crescente)

            if n_show and n_show > 0:
                registros_show = registros[:n_show]
            else:
                registros_show = registros

            max_time = max(r["time"] for r in registros)
            total = len(registros)
            n_corretos = sum(1 for r in registros if r["correto"])

            # Sumário
            s1, s2, s3, s4 = st.columns(4)
            with s1:
                st.metric("Exemplos com dados", total)
            with s2:
                st.metric("Acurácia", f"{100*n_corretos/total:.1f}%" if total else "—")
            with s3:
                tempo_medio = sum(r["time"] for r in registros) / total if total else 0
                st.metric("Tempo médio (s)", f"{tempo_medio:.2f}")
            with s4:
                st.metric("Tempo máx (s)", f"{max_time:.2f}")

            st.markdown("")

            # Medalhas para top 3
            medals = {0: "🥇", 1: "🥈", 2: "🥉"}

            # Construir tabela HTML
            linhas = []
            for i, r in enumerate(registros_show):
                is_current = (r["id"] == id_escolhido)
                row_class  = "current-row" if is_current else ""
                medal      = medals.get(i, "") if crescente else medals.get(total - 1 - (total - len(registros_show) + i), "")
                if not crescente:
                    medal = medals.get(i, "")

                cor_barra = "#4ecb8a" if r["correto"] else "#e05c5c"
                barra_html = time_bar_html(r["time"], max_time, cor_barra)

                correto_html = (
                    '<span class="rank-correct">✓</span>'
                    if r["correto"]
                    else '<span class="rank-wrong">✗</span>'
                )

                tps_str    = f"{r['tps']:.1f}" if r["tps"] else "—"
                tokens_str = f"{int(r['tokens']):,}" if r["tokens"] else "—"
                rank_num   = i + 1

                linhas.append(
                    f"""<tr class="{row_class}">
                        <td style="color:#555c72;width:40px;">{rank_num}</td>
                        <td style="width:28px;" class="rank-medal">{medal}</td>
                        <td style="font-weight:600;color:{'#f5c842' if is_current else '#c8cdd8'};">
                            {'› ' if is_current else ''}{r['id']}
                        </td>
                        <td>
                            <span style="font-weight:600;color:#f5f6f8;">{r['time']:.3f}s</span>
                            &nbsp; {barra_html}
                        </td>
                        <td>{badge_html(r['gt'])}</td>
                        <td>{badge_html(r['pred'])}</td>
                        <td>{correto_html}</td>
                        <td style="color:#555c72;">{tokens_str}</td>
                        <td style="color:#555c72;">{tps_str}</td>
                    </tr>"""
                )

            tabela_html = f"""
            <table class="rank-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th></th>
                        <th>ID</th>
                        <th>Tempo</th>
                        <th>GT</th>
                        <th>Pred</th>
                        <th>✓</th>
                        <th>Tokens</th>
                        <th>tok/s</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(linhas)}
                </tbody>
            </table>
            """

            st.markdown(
                f'<div style="overflow-x:auto;max-height:600px;overflow-y:auto;">{tabela_html}</div>',
                unsafe_allow_html=True,
            )

            if is_current_in_range := any(r["id"] == id_escolhido for r in registros_show):
                pass
            else:
                # Mostrar posição do exemplo atual mesmo fora do range exibido
                pos = next((i + 1 for i, r in enumerate(registros) if r["id"] == id_escolhido), None)
                if pos:
                    st.caption(f"ℹ️ O exemplo atual `{id_escolhido}` está na posição **{pos}** de {total} (fora do top {n_show} exibido).")