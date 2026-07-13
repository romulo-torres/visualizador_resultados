#!/usr/bin/env python3
"""
fix_labels.py — Extrai labels de \boxed{...} nos campos txt_* e corrige p_* correspondentes.

Uso:
    python3 fix_labels.py input.jsonl output.jsonl
"""

import json
import re
import sys
from pathlib import Path

# Mapeamento txt_* -> p_*
TXT_TO_P = {
    "txt_original":     "p_original",
    "txt_complex":      "p_complex",
    "txt_nl":           "p_nl",
    "txt_shuffled":     "p_shuffled",
    "txt_junto":        "p_junto",
    "txt_irrelevant":   "p_irrelevant",
    "txt_contradiction":"p_contradiction",
    "txt_negation":     "p_negation",
    "txt_missing":      "p_missing",
}

VALID_LABELS = {"True", "False", "Uncertain"}

def extract_boxed(text: str) -> str | None:
    """Extrai o valor dentro de \\boxed{...} ou \\boxed{Valor (sem fechar)."""
    if not text:
        return None
    # Tenta \boxed{Valor} com chave fechada
    m = re.search(r"\\boxed\{([^}]+)\}", text)
    if m:
        return m.group(1).strip()
    # Tenta \boxed{Valor sem fechar (fim de string)
    m = re.search(r"\\boxed\{(.+?)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None

def fix_jsonl(input_path: str, output_path: str):
    input_file = Path(input_path)
    output_file = Path(output_path)

    total = 0
    fixed = 0
    errors = 0  # campos onde ainda não foi possível extrair label
    error_details = []

    with input_file.open("r", encoding="utf-8") as fin, \
         output_file.open("w", encoding="utf-8") as fout:

        for lineno, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue

            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[LINHA {lineno}] JSON inválido, pulando: {e}")
                fout.write(line + "\n")
                continue

            for txt_field, p_field in TXT_TO_P.items():
                txt = record.get(txt_field)
                p   = record.get(p_field)

                if txt is None or p_field not in record:
                    continue  # campo não existe nesse registro

                extracted = extract_boxed(txt)

                if extracted and extracted in VALID_LABELS:
                    if p != extracted:
                        print(f"[ID {record.get('id','?')}] {p_field}: '{p}' -> '{extracted}'")
                        record[p_field] = extracted
                        fixed += 1
                else:
                    # Não conseguiu extrair ou valor inválido
                    errors += 1
                    error_details.append({
                        "id": record.get("id", "?"),
                        "field": p_field,
                        "current_p": p,
                        "extracted": extracted,
                        "txt_snippet": (txt or "")[-200:],  # últimos 200 chars
                    })

            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("\n" + "="*50)
    print(f"Total de registros processados : {total}")
    print(f"Labels corrigidas              : {fixed}")
    print(f"Campos com erro (sem label)    : {errors}")

    if error_details:
        print("\nDetalhes dos erros:")
        for e in error_details:
            print(f"  ID={e['id']} | campo={e['field']} | p_atual='{e['current_p']}' | extraído='{e['extracted']}'")
            print(f"    Trecho final do txt: ...{e['txt_snippet']!r}")

    print("="*50)
    print(f"Arquivo corrigido salvo em: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 fix_labels.py input.jsonl output.jsonl")
        sys.exit(1)
    fix_jsonl(sys.argv[1], sys.argv[2])