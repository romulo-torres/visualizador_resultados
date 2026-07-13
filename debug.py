import json, re

def extract_boxed(text):
    if not text:
        return None
    m = re.search(r"\\boxed\{([^}]+)\}", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"\\boxed\{(.+?)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None

with open('llama.jsonl', 'r', encoding='utf-8') as f:
    r = json.loads(f.readline())

fields = ['txt_original','txt_complex','txt_nl','txt_missing']
for field in fields:
    val = r.get(field, '')
    extracted = extract_boxed(val)
    print(f'{field}: extraído={repr(extracted)}')
    # Mostrar bytes ao redor do \boxed para detectar encoding estranho
    idx = val.find('boxed')
    if idx > 0:
        chunk = val[idx-2:idx+15]
        print(f'  bytes ao redor: {chunk.encode("utf-8")}')