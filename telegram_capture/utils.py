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


def _sanitize_surrogates(obj):
    r"""
    Elimina surrogates sueltos (U+D800..U+DFFF) de strings en la estructura.

    json.loads acepta escapes \uXXXX de surrogates incompletos (p. ej. un
    "\ud83d" sin su mitad baja) y produce str con caracteres que no tienen
    representación UTF-8. SQLite (y cualquier codificación UTF-8) falla al
    guardarlos con UnicodeEncodeError.
    """
    if isinstance(obj, str):
        return "".join(ch for ch in obj if not 0xD800 <= ord(ch) <= 0xDFFF)
    if isinstance(obj, list):
        return [_sanitize_surrogates(item) for item in obj]
    if isinstance(obj, dict):
        return {
            _sanitize_surrogates(key): _sanitize_surrogates(value)
            for key, value in obj.items()
        }
    return obj


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
        parsed = json.loads(json_str)
        # Sanear surrogates sueltos que el LLM pudo generar en escapes \uXXXX
        return _sanitize_surrogates(parsed)
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