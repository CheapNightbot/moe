from PIL import Image, ImageDraw, ImageFont


def create_banner(user_name, leave=False):

    BG_IMG = "./assets/welcome.png"
    USER_PFP_IMG = "./assets/user_pfp.png"
    GREET = "./assets/welcome_to_the_sever.png"

    if leave:
        BG_IMG = "./assets/goodbye.png"
        GREET = "./assets/a_good_bye.png"

    with Image.open(BG_IMG).convert("RGBA") as img:
        pfp = Image.open(USER_PFP_IMG).convert("RGBA")
        pfp = pfp.resize((480, 480))

        mask = Image.new("L", pfp.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 480, 480), fill=255)
        pfp.putalpha(mask)

        img.paste(pfp, (272, 252), pfp)

        draw = ImageDraw.Draw(img)

        font = ImageFont.truetype("./assets/fonts/SourceHanSansHW-VF.ttf", 80)
        text_width = draw.textlength(user_name, font=font)
        x = (img.width - text_width) / 2

        draw.text((x, 850), user_name, (219, 82, 117), font=font)
        img.save(GREET, format="PNG")

    return GREET
