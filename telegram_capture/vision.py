import base64
import httpx
import asyncio
from .utils import parse_llm_json

OLLAMA_URL = "http://localhost:11434"
LLAMA_URL = "http://localhost:8080"
# LLMMODEL = "gemma4:e4b"
# LLMMODEL = "gemma-4-E4B-it-UD-Q4_K_XL.gguf"
LLMMODEL = "models/gemma-4-E4B-it-UD-Q4_K_XL/gemma-4-E4B-it-UD-Q4_K_XL.gguf"
OCRMODEL = "maternion/LightOnOCR-2:latest"
PROMPT_OCR = "Extract all text visible in this image. Preserve the structure. If there is no text, say 'No text found'."

PROMPT_GET_DIRECTION = """Extract all locations mentioned in the text below.

Rules:
- A location is a place: country, city, state, neighborhood, street, or address.
- List each location once, separated by commas.
- Normalize obvious abbreviations (e.g. "c.a." -> "Caracas", "Mcia." -> "Maracaibo"), but never invent places.
- If the same place appears twice, list it once.
- If no location appears, respond exactly: No location found
"""

PROMPT_GET_PROFESSION = """Extract all professions mentioned in the text below.

Rules:
- A profession is a job, trade, or occupation (e.g. "doctor", "cocinero", "electrician").
- Normalize obvious misspellings or abbreviations (e.g. "prog." -> "programador"), but never invent professions.
- List each profession once, separated by commas.
- If the same profession appears twice, list it once.
- If no profession appears, respond exactly: No profession found
"""

PROMPT_GET_CONTACT_INFO = """Extract fisical locations and professions from the text below.

Return ONLY JSON with exactly these keys:
{"locations": ["..."], "professions": ["..."]}

Rules:
- A fisical location is a fisical place: country, city, state, neighborhood, street, or fisical address.
- A fisical location is not a digital location like: web direction, file direction, ip direction.
- A profession is a job, trade, or occupation (e.g. "doctor", "cocinero", "electrician").
- List each item once, , separated by commas, in the language of the text. Never invent.
- If no profession appears, add exactly: No profession found to professions.
- If no locations appears, add exactly: No location found to locations.
"""
PROMPT_GET_ALL_INFO = """
- Extract all text visible in this image. Preserve the structure. If there is no text, say 'No text found'. 

-Then extract locations and professions from the image.

Return ONLY JSON with exactly these keys:
{"imagen_text":"...","locations": ["..."], "professions": ["..."]}

Rules:
- A location is a place: country, city, state, neighborhood, street, or address.
- A profession is a job, trade, or occupation (e.g. "doctor", "cocinero", "electrician").
- List each item once, , separated by commas, in the language of the text. Never invent.
- If no profession appears, add exactly: No profession found to professions.
- If no locations appears, add exactly: No location found to locations.
"""

TIMEOUT = 220


def format_milliseconds(nanoseconds: int) -> str:
    """
    Converts a duration in nanoseconds into a human-readable string format (HH:MM:SS.mmm).

    Args:
        nanoseconds: The duration in nanoseconds (integer).

    Returns:
        A string representing the duration in the format "HH:MM:SS.mmm".
    """
    if nanoseconds < 0:
        raise ValueError("Input must be a non-negative integer.")

    # Convert nanoseconds to total seconds
    total_seconds = nanoseconds / 1_000

    # Calculate hours, minutes, seconds, and remaining milliseconds
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds % 60) * 1000)

    # Format the output string
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


async def is_ollama_running() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{LLAMA_URL}/models")
            return r.status_code == 200
    except Exception:
        return False


def encode_image_base64(image_path: str) -> str:
    try:
        with open(image_path, "rb") as f:
            print(f.readable())
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        raise e


async def extract_text_from_image(image_path: str) -> tuple[str | None, str | None]:
    try:
        b64 = encode_image_base64(image_path)
        payload2 = {
            "model": OCRMODEL,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT_OCR,
                    "images": [b64],
                }
            ],
            "stream": False,
            "keep_live":"60m",
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload2)
            r.raise_for_status()
            result = r.json()
            content2 = result["message"]["content"]
            print(format_milliseconds(result["total_duration"]))
            return content2.strip(), None
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text}"
    except FileNotFoundError:
        return "No such file or directory: " + image_path, None
    except Exception as e:
        return None, str(e)

async def extract_all_text_from_image(image_path: str) -> tuple[dict | None, str | None]:
    try:
        b64 = encode_image_base64(image_path)
        payload2 = {
            "model": LLMMODEL,
            "messages": [
                {
                    "role": "user",
			        "content": [
				        { "type": "text", "text": PROMPT_GET_ALL_INFO},
				        { "type": "image_url", "image_url": { "url": b64 }}
                    ]
                }
            ],
            "stream": False,
            "keep_live": "60m",
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{LLAMA_URL}/v1/chat/completions", json=payload2)
            r.raise_for_status()
            result = r.json()
            content2 = result["choices"][0]["message"]["content"]
            content2json = parse_llm_json(content2)
            # print(format_milliseconds(result["total_duration"]))
            print(format_milliseconds(result['timings']['prompt_ms']))

            content2json["locations"] = (
                ",".join(content2json["locations"])
                if content2json["locations"][0] != "No location found"
                else None
            )
            content2json["professions"] = (
                ",".join(content2json["professions"])
                if content2json["professions"][0] != "No profession found"
                else None
            )
            print(content2json)
            return content2json, None
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text}"
    except FileNotFoundError:
        extracted_text = dict()
        extracted_text["imagen_text"] = "No such file or directory: " + image_path
        extracted_text["professions"] = None
        extracted_text["locations"] = None
        return  extracted_text, None
    except Exception as e:
        return None, str(e)
    
async def extract_location_text(text: str) -> tuple[str | None, str | None]:
    try:
        payload2 = {
            "model": LLMMODEL,
            "messages": [
                {
                    "role": "sytem",
                    "content": PROMPT_GET_DIRECTION,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            "stream": False,
            "keep_live": "60m",
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload2)
            r.raise_for_status()
            result = r.json()
            content2 = result["message"]["content"]
            print(format_milliseconds(result["total_duration"]))
            return (
                content2.strip() if content2.strip() != "No location found" else None,
                None,
            )
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return None, str(e)


async def extract_location_profession_info_text(text: str) -> tuple[dict | None, str | None]:
    try:
        payload2 = {
            "model": LLMMODEL,
            "messages": [
                {
                    "role": "system",
                    "content": PROMPT_GET_CONTACT_INFO,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            "stream": False,
            "keep_live": "60m",
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{LLAMA_URL}/v1/chat/completions", json=payload2)
            r.raise_for_status()
            result = r.json()
            print(result.__str__())
            # content2 = result["message"]["content"]
            content2 = result["choices"][0]["message"]["content"]
            content2json = parse_llm_json(content2)
            # print(format_milliseconds(result["total_duration"]))
            print(format_milliseconds(result['timings']['prompt_ms']))

            content2json["locations"] = (
                ",".join(content2json["locations"])
                if content2json["locations"][0] != "No location found"
                else None
            )
            content2json["professions"] = (
                ",".join(content2json["professions"])
                if content2json["professions"][0] != "No profession found"
                else None
            )
            print(content2json)
            return content2json, None
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return None, str(e)


if __name__ == "__main__":
    # from database import get_database, close_database

    try:

        # db = asyncio.run(get_database())
        print("aqui estoy")
        conten = asyncio.run(extract_location_profession_info_text("""**¡Oportunidad de Empleo en Caracas!** 💅

**Puesto:** Manicurista
**Empresa:** Cut's Barber Shop
**Ubicación:** Centro Comercial El Recreo, nivel C3

**Requisitos:**
- Experiencia comprobable.
- Manejo de técnicas (Gel, Acrílico, etc.).
- Excelente atención al cliente.

**Postulación:**
Envía tu CV o portafolio al correo electrónico: **cutsbarberia@gmail.com** (o por mensaje directo a la empresa)."""))
        channel_id = "@rrhh_Venezuela"
        message_id = "223447"
        print("aqui estoy")
        # result = asyncio.run(
        #     extract_contact_info_text("""

        #     ¿Quieres trabajar con nosotros?

        #     # SE SOLICITA

        #     ## PIZZERO

        #     - ✅ Tener entre 21 y 50 años
        #     - ✅ Experiencia comprobable
        #     - ✅ Movilidad propia

        #     Llamanos o escríbenos al 04129625636.

        #     ![image](image_1.png)


        #     Note: The image of the pizza is referenced as a placeholder since actual image extraction is not possible in this format. In a real Markdown document, you would replace `image_placeholder` with the actual image path or URL.

        #     """)
        #         )

        # asyncio.run(
        #     db.update_profession_location(
        #         channel_id, message_id, result[0]["professions"], result[0]["locations"]
        #     )
        # )
    except Exception as e:
        print(e)
    #     asyncio.run(close_database())
    # asyncio.run(close_database())
