"""
fix_mojibake.py
===============
Corrige o problema de encoding (mojibake) nos campos de texto do JSONL
gerado pelo DeepSeek-R1.

Causa do problema
-----------------
O modelo gerou texto com símbolos lógicos UTF-8 (∀ ∃ ∧ ∨ → ¬ etc.).
Esses bytes foram decodificados com um encoding não-padrão onde:
  - Bytes de continuação UTF-8 no intervalo 0x80–0x9F receberam +0xA2
    (ex: 0x88 → U+012A = Ī, em vez de continuar como 0x88)
  - Bytes 0xA0–0xBF foram mantidos como latin-1
Resultado: ∀ (E2 88 80) virou âĪĢ, → virou âĨĴ, ∧ virou âĪ§, etc.

Uso
---
    python fix_mojibake.py input.jsonl output.jsonl
    
    # Ou importe as funções:
    from fix_mojibake import fix_mojibake, fix_jsonl
"""

import json
import sys


def fix_mojibake(text: str) -> str:
    """
    Recebe uma string com mojibake e devolve a string corrigida.
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


def _fix_value(value):
    """Aplica fix_mojibake recursivamente em qualquer valor JSON."""
    if isinstance(value, str):
        return fix_mojibake(value)
    elif isinstance(value, list):
        return [_fix_value(v) for v in value]
    elif isinstance(value, dict):
        return {k: _fix_value(v) for k, v in value.items()}
    return value


def fix_jsonl(input_path: str, output_path: str, fields: list = None) -> int:
    """
    Lê o JSONL de input_path, corrige mojibake e grava em output_path.

    - Se fields=None, corrige TODOS os campos string de cada registro
      (detecta automaticamente, inclusive campos aninhados).
    - Se fields=['campo1', ...], corrige apenas os campos listados
      no nível raiz do objeto.

    Retorna o número de linhas processadas.
    """
    count = 0
    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)

            if fields is None:
                # Corrige tudo recursivamente
                obj = _fix_value(obj)
            else:
                # Corrige apenas os campos especificados
                for field in fields:
                    if field in obj and isinstance(obj[field], str):
                        obj[field] = fix_mojibake(obj[field])

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python fix_mojibake.py <input.jsonl> <output.jsonl>")
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]
    n = fix_jsonl(input_path, output_path)
    print(f"✓ {n} registros processados → {output_path}")