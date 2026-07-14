
import base64
import httpx
import asyncio

OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma4:e4b"
FASTMODEL = "maternion/LightOnOCR-2:latest"
PROMPT = "Extract all text visible in this image. Preserve the structure. If there is no text, say 'No text found'."
TIMEOUT = 220


def format_milliseconds(nanoseconds: int) -> str:
    """
    Converts a duration in nanoseconds into a human-readable string format (HH:MM:SS.mmm).

    Args:
        nanoseconds: The duration in nanoseconds (integer).

    Returns:
        A string representing the duration in the format "HH:MM:SS.mmm".
    """
    if not isinstance(nanoseconds, int) or nanoseconds < 0:
        raise ValueError("Input must be a non-negative integer.")

    # Convert nanoseconds to total seconds
    total_seconds = nanoseconds / 1_000_000_000

    # Calculate hours, minutes, seconds, and remaining milliseconds
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds % 60) * 1000)

    # Format the output string
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


async def quie() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


def encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        print(f.readable())
        return base64.b64encode(f.read()).decode("utf-8")


async def extract_text_from_image(image_path: str) -> tuple[str | None, str | None]:
    try:
        b64 = encode_image_base64(image_path)
        payload2 = {
            "model": FASTMODEL,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
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
            #print(content2.strip())
            return content2.strip(), None
    except httpx.HTTPStatusError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return None, str(e)
    
if __name__ == "__main__":
    result = asyncio.run(
     extract_text_from_image("C:\\Users\\Public\\Documents\\Programacion\\telegram back\\downloads\\rrhh_Venezuela\\20260630\\216135_20260630.jpg")
    )