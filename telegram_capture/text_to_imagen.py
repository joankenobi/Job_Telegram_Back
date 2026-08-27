import textwrap
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
from .utils import is_arabic
import sys
from .database import get_database, close_database
from .models import Message
from .media import get_folder_for_message

def reshape_arabic(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


async def message_text_to_image(
    args
):

    if not args.channels:
        print("Error: --text_to_img requires --channel")
        sys.exit(1)

    db = await get_database()

    rows: list[Message]= await db.get_only_text_messages(args.channels,args.limit)

    for row in rows:
        path = get_folder_for_message(message=row)
        create_job_post(row.message_text, path)
    close_database()

def create_job_post(
    message_text: str, output_path: str, lang: str = "auto"
):
    # Detectar el idioma si viene en 'auto'
    if lang == "auto":
        lang = "ar" if is_arabic(message_text) else "en"

    width, height = 1080, 1080
    image = Image.new("RGB", (width, height), color=(18, 30, 49))
    draw = ImageDraw.Draw(image)

    # Cargar fuentes según plataforma
    title_font = ImageFont.truetype("c:/Windows/Fonts/arial.ttf", 60)
    body_font = ImageFont.truetype("c:/Windows/Fonts/arial.ttf", 36) if lang == "ar" else ImageFont.truetype("c:\\Windows\\Fonts\\SEGUIEMJ.TTF", 36)
    

    # Tratamiento según idioma
    if lang == "ar":
        # ÁRABE: Alineación Derecha (RTL)
        title_text = reshape_arabic("وظيفة شاغرة")
        draw.text(
            (1000, 80),
            title_text,
            fill=(0, 180, 216),
            font=title_font,
            anchor="ra",
        )

        lines = textwrap.wrap(message_text, width=45)
        y = 200
        for line in lines:
            arabic_line = reshape_arabic(line)
            draw.text(
                (1000, y),
                arabic_line,
                fill=(255, 255, 255),
                font=body_font,
                anchor="ra",
            )
            y += 50
    else:
        # INGLÉS / LATINO: Alineación Izquierda (LTR)
        draw.text(
            (80, 80),
            "JOB OFFER",
            fill=(0, 180, 216),
            font=title_font,
            anchor="la",
        )

        lines = textwrap.wrap(message_text, width=50)
        y = 200
        for line in lines:
            draw.text(
                (80, y),
                line,
                fill=(255, 255, 255),
                font=body_font,
                anchor="la",
            )
            y += 50

    image.save(output_path + ".jpg")

if __name__ == "__main__":
    message_text_to_image()