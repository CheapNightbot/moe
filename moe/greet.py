from PIL import Image, ImageFont, ImageDraw

BG_IMG = "./moe/assets/welcome.png"
USER_PFP_IMG = "./moe/assets/user_pfp.png"


def create_banner(user_name):
    with Image.open(BG_IMG).convert("RGBA") as img:
        pfp = Image.open(USER_PFP_IMG).convert("RGBA")
        pfp = pfp.resize((480, 480))

        img.paste(pfp, (275, 255), pfp)

        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("./moe/assets/FunnelDisplay-Regular.ttf", 69)

        draw.text((280, 850), user_name, (219, 82, 117), font=font)
        img.save("./moe/assets/wel-come.png")
