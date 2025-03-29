import os

from dotenv import load_dotenv

load_dotenv()

import discord
from discord import app_commands

from .greet import create_banner
from .logger import log

TOKEN = os.getenv("TOKEN")


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents, activity: discord.Activity):
        super().__init__(intents=intents, activity=activity)
        self.role_msg_id = 1326954222339489885
        self.reaction_roles = {"✅": 1195788288477376673}

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f"Ready ~ !! Logged in as {self.user.name}.")
        print("\n----------------------------")
        print(f"{self.user.name} GUILDS:\n")
        guild_count = 0

        for guild in self.guilds:
            guild_count += 1
            print(f"{guild_count}. {guild.name}")

        print(f"\n{self.user.name} is in {guild_count} guild(s).")
        print("\n----------------------------\n")

    async def on_message(self, msg: discord.Message):
        if msg.author.id == self.user.id:
            return

        if client.user.mentioned_in(msg):
            await msg.reply("<a:moe:1326858320409006145> ?", mention_author=True)

    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        if guild.system_channel:
            await member.display_avatar.save("./moe/assets/user_pfp.png")
            img = discord.File(create_banner(member.display_name))
            msg = f"Heyo {member.mention} ~ <:haro:1326811765928890450> Welcome to **{guild.name}** !\n\nPlease read & agree to the <#1191391912372994128> in order to gain access to the full server."

            if member.bot:
                msg = f"Beep boob, boop beep ~ {member.mention} just appeared ! <:hallo:1327313451999035415>"
                await member.add_roles(guild.get_role(1327308523167809616))

            await guild.system_channel.send(msg, file=img)

    async def on_member_remove(self, member: discord.Member):
        guild = member.guild

        if guild.system_channel:
            await member.display_avatar.save("./moe/assets/user_pfp.png")
            img = discord.File(create_banner(member.display_name, leave=True))
            msg = f'{member.mention} just said a "Goodbye" ~ <:aquacry:1326968634886848623> !\n\nWe hope you had a great time in **{guild.name}** !'
            await guild.system_channel.send(msg, file=img)

    async def on_raw_reaction_add(self, payload):
        if payload.message_id == self.role_msg_id:
            guild = self.get_guild(payload.guild_id)

            if payload.emoji.name != "✅":
                msg = guild.get_channel(payload.channel_id).get_partial_message(payload.message_id)
                emoji = self.get_emoji(payload.emoji.id) if payload.emoji.id else payload.emoji.name
                await msg.remove_reaction(emoji, guild.get_member(payload.user_id))
                return

            role_id = self.reaction_roles.get(payload.emoji.name)
            if role_id:
                role = guild.get_role(role_id)
                member = guild.get_member(payload.user_id)
                if role and member:
                    await member.add_roles(role)

    async def on_raw_reaction_remove(self, payload):
        if payload.message_id == self.role_msg_id:
            guild = self.get_guild(payload.guild_id)
            role_id = self.reaction_roles.get(payload.emoji.name)

            if role_id:
                role = guild.get_role(role_id)
                member = guild.get_member(payload.user_id)
                if role and member:
                    await member.remove_roles(role)


activity = discord.Activity(name="萌え萌えキュン ♡(⸝⸝> ᴗ•⸝⸝)", type=discord.ActivityType.streaming)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = MyClient(intents=intents, activity=activity)


def main():
    log()
    client.run(token=TOKEN, log_handler=None)
