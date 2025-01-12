from PIL import Image, ImageDraw, ImageFont
from langdetect import detect


def create_banner(user_name, leave=False):

    BG_IMG = "./moe/assets/welcome.png"
    USER_PFP_IMG = "./moe/assets/user_pfp.png"
    GREET = "./moe/assets/welcome_to_the_sever.png"

    if leave:
        BG_IMG = "./moe/assets/goodbye.png"
        GREET = "./moe/assets/a_good_bye.png"

    with Image.open(BG_IMG).convert("RGBA") as img:
        pfp = Image.open(USER_PFP_IMG).convert("RGBA")
        pfp = pfp.resize((480, 480))

        mask = Image.new("L", pfp.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 480, 480), fill=255)
        pfp.putalpha(mask)

        img.paste(pfp, (272, 252), pfp)

        draw = ImageDraw.Draw(img)

        font_en = ImageFont.truetype("./static/fonts/Murecho/static/Murecho-Regular.ttf", 69)
        font_jp = ImageFont.truetype("./static/fonts/Kaisei_Decol/KaiseiDecol-Regular.ttf", 75)
        font_kr = ImageFont.truetype("./static/fonts/Dongle/Dongle-Regular.ttf", 120)

        username_lang = detect(user_name)
        if username_lang == "ja":
            font = font_jp
        elif username_lang == "ko":
            font = font_kr
        else:
            font = font_en

        text_width = draw.textlength(user_name, font=font)
        x = (img.width - text_width) / 2

        draw.text((x, 850), user_name, (219, 82, 117), font=font)
        img.save(GREET, format="PNG")

    return GREET
