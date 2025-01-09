import os

from dotenv import load_dotenv

load_dotenv()

import discord
from discord import app_commands
from .greet import create_banner

TOKEN = os.getenv("TOKEN")


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, activity: discord.Activity):
        super().__init__(intents=intents, activity=activity)

    async def on_ready(self):
        print(f"Ready ~ !! Logged in as {client.user.name}.")
        print("----------------------------")

    async def on_message(self, msg: discord.Message):
        if msg.author.id == client.user.id:
            return

        if client.user.mentioned_in(msg):
            await msg.reply("<a:moe:1326858320409006145> ?", mention_author=True)

    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        if guild.system_channel:
            await member.display_avatar.save("./moe/assets/user_pfp.png")
            img = discord.File(create_banner(member.display_name))
            msg = f"Heyo {member.mention} ~ <:haro:1326811765928890450> Welcome to **{guild.name}** !\n\nPlease read & agree to the <#1191391912372994128> in order to gain access to the full server."
            await guild.system_channel.send(msg, file=img)

    async def on_member_remove(self, member: discord.Member):
        guild = member.guild

        if guild.system_channel:
            await member.display_avatar.save("./moe/assets/user_pfp.png")
            img = discord.File(create_banner(member.display_name, leave=True))
            msg = f'{member.mention} just said a "Goodbye" ~ <:aquacry:1326968634886848623> !\n\nWe hope you had a great time in **{guild.name}** !'
            await guild.system_channel.send(msg, file=img)


activity = discord.Activity(name="Conversations..", type=discord.ActivityType.listening)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = MyClient(intents=intents, activity=activity)


def main():
    client.run(token=TOKEN, log_handler=None)
