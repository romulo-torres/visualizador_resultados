"""
cria_tabela_llm_lrm.py
=======================
Versão combinada de cria_tabela_lrm.py: em vez de analisar um único arquivo
(só o LRM = DeepSeek-R1-Distill), este script carrega DOIS arquivos --
  - LLM  = meta-llama/Llama-3.1-8B-Instruct  (ex.: llama_labels.jsonl)
  - LRM  = deepseek-ai/DeepSeek-R1-Distill-Llama-8B (ex.: deepseek_consertado.jsonl)
e roda o mesmo conjunto de diagnósticos/tabelas para os dois, lado a lado,
sempre que fizer sentido comparar.

IMPORTANTE (mesma ressalva do script original): os dois arquivos usados aqui
correspondem à temperatura 0.6. Nenhum dos dois contém a coluna "T=0" das
tabelas do paper. Portanto este script recalcula/confere as colunas
"LLM, T=0.6" e "LRM, T=0.6" das Tabelas 2 e 3 -- não as colunas de T=0.

O que ele faz, para cada arquivo (LLM e LRM):
  1) Diagnóstico geral (nº de exemplos, campos, distribuição de gt/bins).
  2) Acurácia por transformação -- IMPRESSA LADO A LADO (LLM vs LRM) numa
     tabela só, já que essa é a comparação que normalmente importa.
  3) Verificação de predições idênticas entre transformações (bug de
     pipeline), separada por modelo.
  4) Teste de McNemar (Original vs. cada perturbação), separado por modelo
     -- usado para o '*' nas colunas de GANHO da Tabela 1 do paper.
  5) Teste de McNemar PAREADO entre LLM e LRM, para cada campo_pred, usando
     o mesmo id -- usado para o '*' nas colunas de ACURÁCIA (LLM ou LRM) da
     Tabela 1 do paper (indica se a diferença entre os dois modelos, na
     mesma condição, é estatisticamente significativa).
  6) Tabela por tercis de nl_wc e por bins Q1-Q4 (nl_bin / fol_bin) --
     também impressa lado a lado (LLM vs LRM) quando os dois arquivos têm os
     mesmos IDs (o que deveria ser o caso, pois ambos vêm do mesmo FOLIO).

Uso:
    python3 cria_tabela_llm_lrm.py llama_labels.jsonl deepseek_consertado.jsonl

Se você não passar argumentos, ele tenta os nomes padrão abaixo
(DEFAULT_LLM_PATH / DEFAULT_LRM_PATH).
"""

import json
import sys
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import chi2, binomtest


DEFAULT_LLM_PATH = "llama_labels.jsonl"
DEFAULT_LRM_PATH = "deepseek_consertado.jsonl"

CAMPOS_PRED = [
    "p_original", "p_nl", "p_shuffled", "p_junto", "p_irrelevant",
    "p_missing", "p_complex", "p_contradiction", "p_negation",
]

NOMES_LEGIVEIS = {
    "p_original": "Original",
    "p_nl": "Linguagem Natural",
    "p_shuffled": "Premissas Embaralhadas",
    "p_junto": "Premissas Juntas (AND)",
    "p_irrelevant": "Ruído Irrelevante",
    "p_missing": "Premissa Faltante",
    "p_complex": "Duplicação de Premissas",
    "p_contradiction": "Contradição Injetada",
    "p_negation": "Negação Conclusão",
}

# Valores antigos que estavam hardcoded no LaTeX (coluna "LRM, T=0.6").
# Não temos valores antigos equivalentes para a coluna "LLM, T=0.6" -- se
# você tiver esses números, preencha aqui para habilitar a comparação.
VALORES_ANTIGOS_LRM = {
    "p_original": 36.45,
    "p_nl": 41.38,
    "p_shuffled": 40.39,
    "p_junto": 36.45,
    "p_irrelevant": 30.05,
    "p_missing": 3.94,
    "p_complex": 35.96,
    "p_contradiction": 24.63,
    "p_negation": 34.98,
}
VALORES_ANTIGOS_LLM = None  # ex.: {"p_original": 45.0, ...} se voce tiver

# ==============================================================================
# PLANILHA DE VALIDACAO (relevant_premise_validation.xlsx)
# ==============================================================================
DEFAULT_VALIDATION_XLSX = "../codigos_pibic/relevant_premise_validation.xlsx"

def load_proven_missing(xlsx_path):
    """Le a planilha de validacao manual e retorna {dataset_idx: new_label}
    -- so para as linhas com relevant_found == True. new_label e o gabarito
    correto na task 'missing' apos remover aquela premissa (normalmente
    'Uncertain', mas lido dinamicamente, sem assumir isso fixo no codigo)."""
    df = pd.read_excel(xlsx_path)
    obrigatorias = {"dataset_idx", "relevant_found", "new_label"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ValueError(
            f"A planilha {xlsx_path} nao tem as colunas esperadas: {faltando}. "
            f"Colunas encontradas: {list(df.columns)}"
        )
    sub = df[df["relevant_found"] == True]
    return {int(row["dataset_idx"]): row["new_label"] for _, row in sub.iterrows()}


# Preenchido de verdade em main(), a partir da planilha.
PROVEN_NEW_LABEL = {}


def invert_label(gt):
    """Inverte o rotulo logico: True<->False, Uncertain fica Uncertain."""
    mapping = {"True": "False", "False": "True", "Uncertain": "Uncertain"}
    return mapping.get(gt, gt)


def gt_efetivo(row, campo_pred):
    """Retorna o gt a ser usado na avaliacao. Igual ao gt original, exceto:
      - p_missing nos ids com premissa comprovadamente removida (planilha)
        -> new_label da planilha (normalmente 'Uncertain').
      - p_negation em TODOS os ids -> inverte o gt (True<->False).
      - p_contradiction em TODOS os ids -> 'Uncertain'."""
    gt = row.get("gt")
    if campo_pred == "p_missing":
        idx = row.get("id")
        if idx in PROVEN_NEW_LABEL:
            return PROVEN_NEW_LABEL[idx]
        return gt
    if campo_pred == "p_negation":
        return invert_label(gt)
    if campo_pred == "p_contradiction":
        return "Uncertain"
    return gt


# ==============================================================================
# CARREGAMENTO
# ==============================================================================
def carregar(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ==============================================================================
# DIAGNOSTICO GERAL (por modelo)
# ==============================================================================
def diagnostico_geral(recs, label):
    print("=" * 70)
    print(f"DIAGNÓSTICO GERAL DO ARQUIVO -- {label}")
    print("=" * 70)
    print(f"Número de exemplos (linhas): {len(recs)}")

    campos_p = [k for k in recs[0] if k.startswith("p_")]
    print(f"Campos de predição encontrados: {campos_p}")

    gt = Counter(r["gt"] for r in recs)
    print(f"\nDistribuição do gold label (gt): {dict(gt)}")

    for campo in ["nl_bin", "fol_bin"]:
        if campo in recs[0]:
            print(f"Distribuição de {campo}: {dict(Counter(r[campo] for r in recs))}")


# ==============================================================================
# ACURACIA
# ==============================================================================
def acuracia(recs, campo_pred):
    c = tot = 0
    for r in recs:
        p = r.get(campo_pred)
        if p is None or p == "SKIP":
            continue
        tot += 1
        if p == gt_efetivo(r, campo_pred):
            c += 1
    return c, tot, (100 * c / tot if tot else float("nan"))


def acuracia_geral_combinada(recs_llm, recs_lrm):
    print("\n" + "=" * 70)
    print("ACURÁCIA POR TRANSFORMAÇÃO -- LLM vs LRM (T=0.6), LADO A LADO")
    print("=" * 70)

    header = (
        f"  {'Transformação':<26s}"
        f"{'n_LLM':>7s}{'acc_LLM':>10s}{'ant_LLM':>10s}"
        f"{'n_LRM':>7s}{'acc_LRM':>10s}{'ant_LRM':>10s}{'diff_LRM':>10s}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    for campo in CAMPOS_PRED:
        nome = NOMES_LEGIVEIS.get(campo, campo)

        c_llm, n_llm, pct_llm = acuracia(recs_llm, campo)
        c_lrm, n_lrm, pct_lrm = acuracia(recs_lrm, campo)

        ant_llm = VALORES_ANTIGOS_LLM.get(campo) if VALORES_ANTIGOS_LLM else None
        ant_lrm = VALORES_ANTIGOS_LRM.get(campo) if VALORES_ANTIGOS_LRM else None
        diff_lrm = (pct_lrm - ant_lrm) if ant_lrm is not None else float("nan")

        ant_llm_str = f"{ant_llm:6.2f}" if ant_llm is not None else "   n/d"
        ant_lrm_str = f"{ant_lrm:6.2f}" if ant_lrm is not None else "   n/d"
        diff_str = f"{diff_lrm:+6.2f}" if not np.isnan(diff_lrm) else "   n/d"

        print(
            f"  {nome:<26s}"
            f"{n_llm:>7d}{pct_llm:>9.2f}%{ant_llm_str:>10s}"
            f"{n_lrm:>7d}{pct_lrm:>9.2f}%{ant_lrm_str:>10s}{diff_str:>10s}"
        )

    print(
        "\n'ant_LLM'/'ant_LRM' = valores antigos do LaTeX (n/d = não "
        "disponível). 'diff_LRM' = diferença acc_LRM - ant_LRM em pontos "
        "percentuais.\nSem valores antigos para LLM, então diff_LLM não é "
        "mostrado -- preencha VALORES_ANTIGOS_LLM no topo do script se tiver."
    )


# ==============================================================================
# PREDICOES IDENTICAS (bug de pipeline) -- por modelo
# ==============================================================================
def checar_predicoes_identicas(recs, label):
    print("\n" + "=" * 70)
    print(f"VERIFICANDO PREDIÇÕES IDÊNTICAS ENTRE TRANSFORMAÇÕES -- {label}")
    print("=" * 70)

    df = pd.DataFrame(recs)
    encontrou_alerta = False

    for campo_a, campo_b in combinations(CAMPOS_PRED, 2):
        if campo_a not in df.columns or campo_b not in df.columns:
            continue
        serie_a = df[campo_a]
        serie_b = df[campo_b]

        n_comparaveis = int(((serie_a != "SKIP") & (serie_b != "SKIP")).sum())
        if n_comparaveis == 0:
            continue

        iguais = int(
            ((serie_a == serie_b) & (serie_a != "SKIP") & (serie_b != "SKIP")).sum()
        )
        pct_igual = 100 * iguais / n_comparaveis

        if pct_igual == 100.0:
            encontrou_alerta = True
            print(
                f"  [ALERTA] {campo_a} == {campo_b} em TODAS as "
                f"{n_comparaveis} linhas comparáveis (100.00% idênticas)."
            )
        elif pct_igual >= 95.0:
            encontrou_alerta = True
            print(
                f"  [suspeito] {campo_a} vs {campo_b}: {iguais}/{n_comparaveis} "
                f"linhas idênticas ({pct_igual:.2f}%). Vale investigar."
            )

    if not encontrou_alerta:
        print(
            "  Nenhum par de transformações tem predições excessivamente "
            "parecidas (limite: >=95%). Nenhum indício de duplicação."
        )


# ==============================================================================
# MCNEMAR -- por modelo (Original vs. cada perturbação)
# ==============================================================================
def mcnemar_manual(b, c, correcao_continuidade=True):
    n_disc = b + c
    if n_disc == 0:
        return 0.0, 1.0

    if n_disc < 25:
        res = binomtest(b, n_disc, 0.5)
        return float("nan"), res.pvalue

    if correcao_continuidade:
        estat = (abs(b - c) - 1) ** 2 / n_disc
    else:
        estat = (b - c) ** 2 / n_disc
    p_valor = 1 - chi2.cdf(estat, df=1)
    return estat, p_valor


def teste_mcnemar_geral(recs, label, campo_base="p_original", alfa=0.05):
    print("\n" + "=" * 70)
    print(f"TESTE DE MCNEMAR -- {label} ({campo_base} vs. cada perturbação)")
    print("=" * 70)

    df = pd.DataFrame(recs)
    base = df[campo_base]

    # gt_base: gt efetivo para a coluna base (normalmente p_original, que
    # nunca tem ajuste -- mas calculado de forma generica de qualquer jeito)
    gt_base = df.apply(lambda r: gt_efetivo(r, campo_base), axis=1)

    resultado = {}

    for campo in CAMPOS_PRED:
        if campo == campo_base or campo not in df.columns:
            continue

        pert = df[campo]
        validos = (base != "SKIP") & (pert != "SKIP")
        n = int(validos.sum())
        if n == 0:
            continue

        # gt_pert: gt efetivo para a perturbacao em questao -- diferente do
        # gt normal apenas para p_missing (ids da planilha), p_negation
        # (inverte True<->False em todos os ids) e p_contradiction (vira
        # 'Uncertain' em todos os ids). Para as demais, e igual ao gt.
        gt_pert = df.apply(lambda r: gt_efetivo(r, campo), axis=1)

        base_ok = (base[validos] == gt_base[validos])
        pert_ok = (pert[validos] == gt_pert[validos])

        b = int((base_ok & ~pert_ok).sum())
        c = int((~base_ok & pert_ok).sum())

        estat, p = mcnemar_manual(b, c)
        sig = p < alfa
        sig_str = "*" if sig else " "

        acc_base = 100 * base_ok.mean()
        acc_pert = 100 * pert_ok.mean()
        ganho = 100 * (acc_pert - acc_base) / acc_base if acc_base else float("nan")

        nome = NOMES_LEGIVEIS.get(campo, campo)
        estat_str = "  exato " if np.isnan(estat) else f"{estat:7.3f}"
        print(
            f"  {nome:26s} n={n:4d}  acc_orig={acc_base:6.2f}%  "
            f"acc_pert={acc_pert:6.2f}%  ganho={ganho:+6.1f}%  "
            f"b={b:3d} c={c:3d}  estat={estat_str}  p={p:.4f} {sig_str}"
        )

        resultado[campo] = (b, c, estat, p, sig)

    print(f"\n(*) p < {alfa}: diferença estatisticamente significativa (McNemar).")
    return resultado


# ==============================================================================
# MCNEMAR -- PAREADO ENTRE LLM E LRM (mesma condição, mesmo id)
# ==============================================================================
def teste_mcnemar_llm_vs_lrm(recs_llm, recs_lrm, alfa=0.05):
    """McNemar pareado LLM vs LRM, para cada campo_pred, usando o mesmo id.
    b = LLM acerta e LRM erra | c = LRM acerta e LLM erra.

    Usado para decidir o '*' nas colunas de ACURÁCIA da Tabela 1 do paper
    (diferente do '*' nas colunas de GANHO, que vem de teste_mcnemar_geral
    -- Original vs. Perturbação, dentro do mesmo modelo).

    Retorna {campo_pred: (b, c, estat, p, sig_bool)}.
    """
    print("\n" + "=" * 70)
    print("TESTE DE MCNEMAR -- LLM vs. LRM (pareado por id, mesmo campo_pred)")
    print("=" * 70)

    df_llm = pd.DataFrame(recs_llm)
    df_lrm = pd.DataFrame(recs_lrm)

    resultado = {}

    for campo in CAMPOS_PRED:
        if campo not in df_llm.columns or campo not in df_lrm.columns:
            continue

        # gt efetivo calculado separadamente em cada df (mesma regra em
        # gt_efetivo; ids devem ser os mesmos nos dois arquivos, pois ambos
        # vem do mesmo FOLIO, entao da no mesmo resultado)
        tmp_llm = df_llm.copy()
        tmp_lrm = df_lrm.copy()
        tmp_llm["_gt_efetivo"] = tmp_llm.apply(lambda r: gt_efetivo(r, campo), axis=1)
        tmp_lrm["_gt_efetivo"] = tmp_lrm.apply(lambda r: gt_efetivo(r, campo), axis=1)

        merged = tmp_llm[["id", campo, "_gt_efetivo"]].merge(
            tmp_lrm[["id", campo, "_gt_efetivo"]],
            on="id", suffixes=("_llm", "_lrm")
        )

        validos = (merged[f"{campo}_llm"] != "SKIP") & (merged[f"{campo}_lrm"] != "SKIP")
        sub = merged[validos]
        n = len(sub)
        if n == 0:
            continue

        correct_llm = sub[f"{campo}_llm"] == sub["_gt_efetivo_llm"]
        correct_lrm = sub[f"{campo}_lrm"] == sub["_gt_efetivo_lrm"]

        b = int((correct_llm & ~correct_lrm).sum())   # LLM acerta, LRM erra
        c = int((~correct_llm & correct_lrm).sum())   # LRM acerta, LLM erra

        estat, p = mcnemar_manual(b, c)
        sig = p < alfa
        sig_str = "*" if sig else " "

        acc_llm = 100 * correct_llm.mean()
        acc_lrm = 100 * correct_lrm.mean()

        nome = NOMES_LEGIVEIS.get(campo, campo)
        estat_str = "  exato " if np.isnan(estat) else f"{estat:7.3f}"
        print(
            f"  {nome:26s} n={n:4d}  acc_LLM={acc_llm:6.2f}%  "
            f"acc_LRM={acc_lrm:6.2f}%  b={b:3d} c={c:3d}  "
            f"estat={estat_str}  p={p:.4f} {sig_str}"
        )

        resultado[campo] = (b, c, estat, p, sig)

    print(
        f"\n(*) p < {alfa}: diferença estatisticamente significativa entre "
        "LLM e LRM (McNemar pareado).\nConvenção sugerida p/ LaTeX: se "
        "sig=True, colocar '*' na acurácia do modelo com MAIOR acurácia "
        "nessa linha (não no ganho)."
    )
    return resultado


# ==============================================================================
# TABELAS POR TAMANHO -- por modelo, e combinada (LLM+LRM lado a lado)
# ==============================================================================
def tabela_por_tercis(recs, label, campo_wc="nl_wc", campo_pred="p_original"):
    print("\n" + "=" * 70)
    print(f"TABELA POR TERCIS DE {campo_wc} -- {label} (campo_pred={campo_pred})")
    print("=" * 70)

    df = pd.DataFrame(recs)
    df = df[df[campo_pred] != "SKIP"].copy()
    df["tercil"], bins = pd.qcut(df[campo_wc], 3, retbins=True, labels=False)

    for t in sorted(df["tercil"].unique()):
        sub = df[df["tercil"] == t]
        lo, hi = sub[campo_wc].min(), sub[campo_wc].max()
        acertos = (sub[campo_pred] == sub["gt"]).sum()
        n = len(sub)
        print(
            f"  Tercil {t+1}: faixa {lo}-{hi} palavras | "
            f"n={n} | acurácia={100*acertos/n:.2f}%"
        )
    print(f"\n  (cortes reais dos tercis: {bins.round(1).tolist()})")


def tabela_por_bins_existentes(recs, label, campo_pred="p_original"):
    print("\n" + "=" * 70)
    print(f"TABELA POR BINS Q1-Q4 (nl_bin / fol_bin) -- {label} (campo_pred={campo_pred})")
    print("=" * 70)
    df = pd.DataFrame(recs)
    df = df[df[campo_pred] != "SKIP"].copy()

    print("Usando nl_bin (baseado em nl_wc, nº de palavras):")
    for b in ["Q1", "Q2", "Q3", "Q4"]:
        sub = df[df["nl_bin"] == b]
        if len(sub) == 0:
            continue
        lo, hi = sub["nl_wc"].min(), sub["nl_wc"].max()
        acertos = (sub[campo_pred] == sub["gt"]).sum()
        n = len(sub)
        print(f"  {b}: faixa {lo}-{hi} palavras | n={n} | acurácia={100*acertos/n:.2f}%")

    print("\nUsando fol_bin (baseado em fol_tc, nº de tokens da FOL):")
    for b in ["Q1", "Q2", "Q3", "Q4"]:
        sub = df[df["fol_bin"] == b]
        if len(sub) == 0:
            continue
        lo, hi = sub["fol_tc"].min(), sub["fol_tc"].max()
        acertos = (sub[campo_pred] == sub["gt"]).sum()
        n = len(sub)
        print(f"  {b}: faixa {lo}-{hi} tokens FOL | n={n} | acurácia={100*acertos/n:.2f}%")


def tabela_combinada_por_bins(recs_llm, recs_lrm, campo_pred="p_original"):
    """Junta os dois arquivos pelo 'id' e mostra LLM vs LRM lado a lado,
    por bin de nl_bin e fol_bin. Só funciona bem se os dois arquivos vierem
    do mesmo FOLIO (mesmos ids, mesmos bins) -- o que é o caso aqui."""
    print("\n" + "=" * 70)
    print(f"TABELA COMBINADA LLM vs LRM POR BIN (campo_pred={campo_pred})")
    print("=" * 70)

    df_llm = pd.DataFrame(recs_llm)[["id", "nl_bin", "fol_bin", "nl_wc", "fol_tc", "gt", campo_pred]]
    df_lrm = pd.DataFrame(recs_lrm)[["id", campo_pred]]

    merged = df_llm.merge(df_lrm, on="id", suffixes=("_LLM", "_LRM"))

    if not merged["nl_bin"].equals(merged["nl_bin"]):
        pass  # placeholder -- bins vem do df_llm, ok por definicao

    print("Por nl_bin (nº de palavras):")
    for b in ["Q1", "Q2", "Q3", "Q4"]:
        sub = merged[merged["nl_bin"] == b]
        if len(sub) == 0:
            continue
        sub_llm = sub[sub[f"{campo_pred}_LLM"] != "SKIP"]
        sub_lrm = sub[sub[f"{campo_pred}_LRM"] != "SKIP"]
        acc_llm = 100 * (sub_llm[f"{campo_pred}_LLM"] == sub_llm["gt"]).mean() if len(sub_llm) else float("nan")
        acc_lrm = 100 * (sub_lrm[f"{campo_pred}_LRM"] == sub_lrm["gt"]).mean() if len(sub_lrm) else float("nan")
        print(
            f"  {b}: n={len(sub):3d} | "
            f"LLM: n={len(sub_llm):3d} acc={acc_llm:6.2f}% | "
            f"LRM: n={len(sub_lrm):3d} acc={acc_lrm:6.2f}%"
        )

    print("\nPor fol_bin (nº de tokens FOL):")
    for b in ["Q1", "Q2", "Q3", "Q4"]:
        sub = merged[merged["fol_bin"] == b]
        if len(sub) == 0:
            continue
        sub_llm = sub[sub[f"{campo_pred}_LLM"] != "SKIP"]
        sub_lrm = sub[sub[f"{campo_pred}_LRM"] != "SKIP"]
        acc_llm = 100 * (sub_llm[f"{campo_pred}_LLM"] == sub_llm["gt"]).mean() if len(sub_llm) else float("nan")
        acc_lrm = 100 * (sub_lrm[f"{campo_pred}_LRM"] == sub_lrm["gt"]).mean() if len(sub_lrm) else float("nan")
        print(
            f"  {b}: n={len(sub):3d} | "
            f"LLM: n={len(sub_llm):3d} acc={acc_llm:6.2f}% | "
            f"LRM: n={len(sub_lrm):3d} acc={acc_lrm:6.2f}%"
        )


# ==============================================================================
# GERAÇÃO DA LINHA LATEX (Tabela 1) COM OS DOIS TIPOS DE '*'
# ==============================================================================
def gerar_linhas_latex_tabela1(recs_llm, recs_lrm, sig_ganho_llm, sig_ganho_lrm, sig_llm_vs_lrm):
    """Monta as linhas da Tabela 1 (comparação de acurácia e ganho) já com
    os dois tipos de '*' aplicados nos lugares certos:
      - '*' na ACURÁCIA do modelo vencedor (LLM ou LRM), se sig_llm_vs_lrm
        indicar diferença estatisticamente significativa entre os modelos
        naquela condição.
      - '*' no GANHO de cada modelo, se sig_ganho_llm / sig_ganho_lrm
        indicar diferença estatisticamente significativa entre Original e
        aquela perturbação, dentro do mesmo modelo.
    Imprime as linhas prontas para colar no corpo do \\begin{tabular} do
    LaTeX (ajuste separador decimal vírgula/ponto conforme o \\sisetup)."""
    print("\n" + "=" * 70)
    print("LINHAS LATEX -- TABELA 1 (Acurácia + Ganho, com '*' nos dois tipos)")
    print("=" * 70)

    c_orig_llm, n_orig_llm, acc_orig_llm = acuracia(recs_llm, "p_original")
    c_orig_lrm, n_orig_lrm, acc_orig_lrm = acuracia(recs_lrm, "p_original")

    for campo in CAMPOS_PRED:
        nome = NOMES_LEGIVEIS.get(campo, campo)
        _, _, acc_llm = acuracia(recs_llm, campo)
        _, _, acc_lrm = acuracia(recs_lrm, campo)

        # '*' na acuracia: no modelo com maior acc, se diferenca LLM-vs-LRM for significativa
        marca_llm = ""
        marca_lrm = ""
        if campo in sig_llm_vs_lrm and sig_llm_vs_lrm[campo][4]:
            if acc_llm >= acc_lrm:
                marca_llm = "*"
            else:
                marca_lrm = "*"

        if campo == "p_original":
            ganho_llm_str = "{--}"
            ganho_lrm_str = "{--}"
        else:
            ganho_llm = 100 * (acc_llm - acc_orig_llm) / acc_orig_llm if acc_orig_llm else float("nan")
            ganho_lrm = 100 * (acc_lrm - acc_orig_lrm) / acc_orig_lrm if acc_orig_lrm else float("nan")
            sig_g_llm = sig_ganho_llm.get(campo, (None, None, None, None, False))[4]
            sig_g_lrm = sig_ganho_lrm.get(campo, (None, None, None, None, False))[4]
            ganho_llm_str = f"{ganho_llm:+.1f}{'*' if sig_g_llm else ''}"
            ganho_lrm_str = f"{ganho_lrm:+.1f}{'*' if sig_g_lrm else ''}"

        acc_llm_str = f"{acc_llm:.1f}{marca_llm}"
        acc_lrm_str = f"{acc_lrm:.1f}{marca_lrm}"

        print(
            f"{nome} & {acc_llm_str} & \\textbf{{{acc_lrm_str}}} & "
            f"{ganho_llm_str} & {ganho_lrm_str} \\\\"
        )


# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    llm_path  = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LLM_PATH
    lrm_path  = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_LRM_PATH
    xlsx_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VALIDATION_XLSX

    print(f"Arquivo LLM (Llama-3.1-8B-Instruct): {llm_path}")
    print(f"Arquivo LRM (DeepSeek-R1-Distill):    {lrm_path}")
    print(f"Planilha de validacao (missing):      {xlsx_path}\n")

    PROVEN_NEW_LABEL = load_proven_missing(xlsx_path)
    print(f"✅ {len(PROVEN_NEW_LABEL)} ids com premissa relevante confirmada "
          f"(relevant_found=True)\n")

    recs_llm = carregar(llm_path)
    recs_lrm = carregar(lrm_path)

    diagnostico_geral(recs_llm, "LLM (Llama-3.1-8B-Instruct)")
    diagnostico_geral(recs_lrm, "LRM (DeepSeek-R1-Distill)")

    acuracia_geral_combinada(recs_llm, recs_lrm)

    checar_predicoes_identicas(recs_llm, "LLM")
    checar_predicoes_identicas(recs_lrm, "LRM")

    sig_ganho_llm = teste_mcnemar_geral(recs_llm, "LLM")
    sig_ganho_lrm = teste_mcnemar_geral(recs_lrm, "LRM")

    sig_llm_vs_lrm = teste_mcnemar_llm_vs_lrm(recs_llm, recs_lrm)

    tabela_por_tercis(recs_llm, "LLM", campo_wc="nl_wc")
    tabela_por_tercis(recs_lrm, "LRM", campo_wc="nl_wc")

    tabela_por_bins_existentes(recs_llm, "LLM")
    tabela_por_bins_existentes(recs_lrm, "LRM")

    tabela_combinada_por_bins(recs_llm, recs_lrm, campo_pred="p_original")

    gerar_linhas_latex_tabela1(recs_llm, recs_lrm, sig_ganho_llm, sig_ganho_lrm, sig_llm_vs_lrm)

    print(
        "\n\nLEMBRETE: os dois arquivos usados aqui sao T=0.6. Para "
        "completar as Tabelas 2 e 3 do paper (colunas T=0), sao "
        "necessarios os arquivos equivalentes rodados em T=0 para os dois "
        "modelos."
    )