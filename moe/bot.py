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
        self.tree = app_commands.CommandTree(self)

    # Don't need to sync command everytime.
    # Use when you make changes to slash command itself.
    # async def setup_hook(self) -> None:
    #     await self.tree.sync()
    #     print("Slash commands synced!")


activity = discord.Activity(name="Conversations..", type=discord.ActivityType.listening)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = MyClient(intents=intents, activity=activity)


@client.event
async def on_ready():
    print(f"Ready ~ !! Logged in as {client.user.name}.")
    print("----------------------------")


@client.event
async def on_message(msg: discord.Message):
    if msg.author.id == client.user.id:
        return

    if client.user.mentioned_in(msg):
        await msg.reply("<a:moe:1326858320409006145> ?", mention_author=True)


@client.event
async def on_memeber_join(member: discord.Member):
    guild = member.guild

    if guild.system_channel:
        await member.display_avatar.save("./moe/assets/user_pfp.png")
        img = discord.File(
            create_banner(member.author.display_name),
            filename="welcome_to_the_server.png",
        )

        embed = discord.Embed(
            title=f"Heyo {member.mention} ~ <:haro:1326811765928890450> ! ",
            description=f"Welcome to **{guild.name}** !\n\nPlease read & agree to the <#1191391912372994128> in order to gain access to the full server.",
        )
        embed.set_image(url="attachment://welcome_to_the_server.png")

        await guild.system_channel.send(file=img, embed=embed)


def main():
    client.run(token=TOKEN, log_handler=None)
