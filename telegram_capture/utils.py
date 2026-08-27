import json
import re

# Escapes válidos en JSON según RFC 8259
_VALID_JSON_ESCAPES = {
    '"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'
}

def _fix_invalid_escapes(s: str) -> str:
    """
    Escapa backslashes que no forman parte de secuencias de escape JSON válidas.
    Convierte \m -> \\m, \a -> \\a, etc. pero deja \n, \t, \\, \", \\uXXXX intactos.
    """
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            next_char = s[i + 1]
            # Si es escape válido (incluyendo \uXXXX), lo dejamos como está
            if next_char in _VALID_JSON_ESCAPES:
                if next_char == 'u' and i + 5 < len(s):
                    # \uXXXX - consumir 6 chars (\u + 4 hex)
                    result.append(s[i:i+6])
                    i += 6
                    continue
                else:
                    # Escape simple válido (\n, \t, \\, \", etc.)
                    result.append(s[i:i+2])
                    i += 2
                    continue
            # Escape inválido: escapamos el backslash
            result.append(' ')
            i += 1
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def parse_llm_json(content: str) -> dict:
    # Saca los fences ```json ... ``` y cualquier ruido
    try:
        content = re.sub(r"```(?:json)?", "", content).strip()
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"No JSON object in response: {content[:200]}")
        json_str = content[start : end + 1]
        # Sanear escapes inválidos antes de parsear
        json_str = _fix_invalid_escapes(json_str)
        return json.loads(json_str)
    except Exception as e:
        print(e)
        raise e

def is_arabic(text: str, threshold: float = 0.1) -> bool:
    """Retorna True si el texto contiene caracteres del bloque Unicode árabe."""
    if not text:
        return False

    arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06ff')
    # Si más del 10% de los caracteres son árabes, lo consideramos texto en árabe
    return (arabic_chars / len(text)) > threshold