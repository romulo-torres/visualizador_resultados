"""
fix_mojibake.py
===============
Corrige dois problemas nos campos de texto do JSONL gerado pelo DeepSeek-R1:

1. Tokens BPE visíveis (Ġ, Ċ, ĉ)
   - Ġ (U+0120) → espaço
   - Ċ (U+010A) → newline
   - ĉ (U+0109) → tab

2. Mojibake de símbolos lógicos UTF-8
   - âĪĢ → ∀    âĪ£ → ∃
   - âĪ§ → ∧    âĪ¨ → ∨
   - âĨĴ → →    âĨĵ → ↔
   - Â¬  → ¬    âŠ• → ⊕
   - âİ‡ → ↔    âĨĴ → →

Uso
---
    python fix_mojibake.py input.jsonl output.jsonl

Ou importe:
    from fix_mojibake import fix_all, fix_jsonl
"""

import json
import sys


# ==============================================================================
# 1. CORRECAO DE TOKENS BPE VISIVEIS
# ==============================================================================
def fix_bpe_tokens(text: str) -> str:
    text = text.replace("\u0120", " ")   # Ġ → espaço
    text = text.replace("\u010a", "\n")  # Ċ → newline
    text = text.replace("\u0109", "\t")  # ĉ → tab (raro)
    return text


# ==============================================================================
# 2. CORRECAO DE MOJIBAKE (bytes UTF-8 mal interpretados)
# ==============================================================================
def fix_mojibake(text: str) -> str:
    """
    Reconstrói caracteres UTF-8 corrompidos.

    Causa: bytes de continuação UTF-8 no intervalo 0x80–0x9F receberam +0xA2
    (ex: 0x88 → U+012A = Ī, em vez de continuar como 0x88).
    Bytes 0xA0–0xBF foram mantidos como latin-1.

    Exemplos:
        âĪĢ (E2 88 82 corrompido) → ∀
        âĨĴ (E2 86 92 corrompido) → →
        Â¬  (C2 AC corrompido)    → ¬
    """
    result = []
    i = 0
    while i < len(text):
        cp = ord(text[i])

        if 0xC0 <= cp <= 0xFF:
            leading_byte = cp

            if 0xC0 <= leading_byte <= 0xDF:
                n_cont = 1
            elif 0xE0 <= leading_byte <= 0xEF:
                n_cont = 2
            elif 0xF0 <= leading_byte <= 0xF7:
                n_cont = 3
            else:
                result.append(text[i])
                i += 1
                continue

            cont_bytes = []
            valid = True
            for k in range(1, n_cont + 1):
                if i + k >= len(text):
                    valid = False
                    break
                cont_cp = ord(text[i + k])
                if 0x0100 <= cont_cp <= 0x013F:
                    original_byte = cont_cp - 0xA2
                elif 0x00A0 <= cont_cp <= 0x00BF:
                    original_byte = cont_cp
                else:
                    valid = False
                    break

                if 0x80 <= original_byte <= 0xBF:
                    cont_bytes.append(original_byte)
                else:
                    valid = False
                    break

            if valid and len(cont_bytes) == n_cont:
                try:
                    decoded = bytes([leading_byte] + cont_bytes).decode("utf-8")
                    result.append(decoded)
                    i += 1 + n_cont
                    continue
                except UnicodeDecodeError:
                    pass

        result.append(text[i])
        i += 1

    return "".join(result)


# ==============================================================================
# 3. CORRECAO COMBINADA
# ==============================================================================
def fix_all(text: str) -> str:
    """Aplica BPE tokens primeiro, depois mojibake."""
    text = fix_bpe_tokens(text)
    text = fix_mojibake(text)
    return text


# ==============================================================================
# 4. APLICACAO RECURSIVA EM VALORES JSON
# ==============================================================================
def _fix_value(value, fields=None, _top_level=False):
    if isinstance(value, str):
        return fix_all(value)
    elif isinstance(value, list):
        return [_fix_value(v) for v in value]
    elif isinstance(value, dict):
        if fields is not None and _top_level:
            # Corrige apenas os campos especificados no nível raiz
            return {
                k: (fix_all(v) if k in fields and isinstance(v, str) else v)
                for k, v in value.items()
            }
        else:
            return {k: _fix_value(v) for k, v in value.items()}
    return value


# ==============================================================================
# 5. PROCESSAMENTO DO JSONL
# ==============================================================================
def fix_jsonl(input_path: str, output_path: str, fields: list = None) -> int:
    """
    Lê o JSONL de input_path, corrige e grava em output_path.

    - fields=None  → corrige TODOS os campos string recursivamente
    - fields=[...] → corrige apenas os campos listados no nível raiz
    
    Retorna o número de linhas processadas.
    """
    count = 0
    with open(input_path,  "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            obj = _fix_value(obj, fields=fields, _top_level=True)
            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1
    return count


# ==============================================================================
# 6. MAIN
# ==============================================================================
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python fix_mojibake.py <input.jsonl> <output.jsonl>")
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    # Apenas os campos de texto completo das respostas do modelo
    TEXT_FIELDS = [
        "txt_original",
        "txt_complex",
        "txt_nl",
        "txt_shuffled",
        "txt_junto",
        "txt_irrelevant",
        "txt_contradiction",
        "txt_negation",
        "txt_missing",
    ]

    print(f"📂 Input  : {input_path}")
    print(f"📂 Output : {output_path}")
    print(f"🔧 Campos : {TEXT_FIELDS}")

    n = fix_jsonl(input_path, output_path, fields=TEXT_FIELDS)
    print(f"✅ {n} registros processados → {output_path}")