import asyncio
import json
import os
from multiprocessing import Manager
from typing import Literal

import discord
from discord import Embed, app_commands
from discord.ui import Button, ChannelSelect, Modal, RoleSelect, TextInput, View
from discord.utils import get
from dotenv import load_dotenv

from bot.utils.greet import create_banner
from bot.utils.logger import log
from config.shared import bot_stats  # Import shared variables

load_dotenv()

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError(
        "Discord TOKEN is not set. Please check your environment variable or .env file."
    )

CONFIG_FILE = "./config/guild_config.json"


# Load or initialize the configuration file
def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


guild_config = load_config()


def owner_only(interaction: discord.Interaction) -> bool:
    # Allow the command only if run in a guild and by the guild owner.
    return (
        interaction.guild is not None
        and interaction.user.id == interaction.guild.owner_id
    )


class MyClient(discord.Client):

    def __init__(self, stats, intents: discord.Intents, activity: discord.Activity):
        super().__init__(intents=intents, activity=activity)
        self.tree = app_commands.CommandTree(self)
        self.stats = stats
        self.ready_event = None

    async def setup_hook(self):
        # Sync slash commands
        await self.tree.sync()
        # Start the stats updater
        self.loop.create_task(self.update_stats())
        # Add a scheduled task to check reaction role integrity every 86400 seconds (1 day)
        self.loop.create_task(self.check_reaction_roles_integrity())

    async def check_reaction_roles_integrity(self):
        await self.wait_until_ready()
        while True:
            updated = False
            for guild_id, config in list(guild_config.items()):
                rr_config = config.get("reaction_roles", {})
                for channel_key, messages in list(rr_config.items()):
                    channel = self.get_channel(int(channel_key))
                    if channel is None:
                        # Remove entire channel entry if channel no longer exists
                        del guild_config[guild_id]["reaction_roles"][channel_key]
                        updated = True
                        continue
                    for message_key in list(messages.keys()):
                        try:
                            await channel.fetch_message(int(message_key))
                        except (discord.NotFound, discord.Forbidden):
                            # Message no longer exists; remove from config
                            del guild_config[guild_id]["reaction_roles"][channel_key][
                                message_key
                            ]
                            updated = True
                    # Clean up empty channel entries
                    if not guild_config[guild_id]["reaction_roles"][channel_key]:
                        del guild_config[guild_id]["reaction_roles"][channel_key]
                        updated = True
            if updated:
                save_config(guild_config)
            await asyncio.sleep(86400)  # run every 86400 seconds (1 day)

    async def update_stats(self):
        while True:
            self.stats["guild_count"] = len(self.guilds)  # Update guild count
            await asyncio.sleep(10)  # Update every 10 seconds

    async def on_ready(self):
        print(f"Ready ~ !! Logged in as {self.user.name}.")
        # Initialize default configs for new guilds
        for guild in self.guilds:
            if str(guild.id) not in guild_config:
                guild_config[str(guild.id)] = {
                    "greetings": True,
                    "welcome_channel": {
                        "channel_id": (
                            guild.system_channel.id if guild.system_channel else None
                        ),
                        "message_template": {
                            "user": "Heyo {member.mention} ~ <:haro:1326811765928890450> Welcome to **{guild.name}** !",
                            "bot": "Beep boob, boop beep ~ {member.mention} just appeared ! <:hallo:1327313451999035415>",
                        },
                    },
                    "goodbye_channel": {
                        "channel_id": (
                            guild.system_channel.id if guild.system_channel else None
                        ),
                        "message_template": {
                            "user": '{member.mention} just said a "Goodbye" ~ <:aquacry:1326968634886848623> !\n\nWe hope you had a great time in **{guild.name}** !',
                            "bot": "Beep boop-... ~ {member.mention} just disappeared ! <:that_hurts:1355670982190432296>",
                        },
                    },
                }
                save_config(guild_config)

            await self.notify_missing_channels(guild)

        # Update guild count immediately on startup
        self.stats["guild_count"] = len(self.guilds)
        self.ready_event.set()

    async def on_guild_join(self, guild: discord.Guild):
        self.stats["guild_count"] = len(self.guilds)
        if str(guild.id) not in guild_config:
            guild_config[str(guild.id)] = {
                "greetings": True,
                "welcome_channel": {
                    "channel_id": (
                        guild.system_channel.id if guild.system_channel else None
                    ),
                    "message_template": {
                        "user": "Heyo {member.mention} ~ <:haro:1326811765928890450> Welcome to **{guild.name}** !",
                        "bot": "Beep boob, boop beep ~ {member.mention} just appeared ! <:hallo:1327313451999035415>",
                    },
                },
                "goodbye_channel": {
                    "channel_id": (
                        guild.system_channel.id if guild.system_channel else None
                    ),
                    "message_template": {
                        "user": '{member.mention} just said a "Goodbye" ~ <:aquacry:1326968634886848623> !\n\nWe hope you had a great time in **{guild.name}** !',
                        "bot": "Beep boop-... ~ {member.mention} just disappeared ! <:that_hurts:1355670982190432296>",
                    },
                },
            }
            save_config(guild_config)

        await self.notify_missing_channels(guild)

    async def notify_missing_channels(self, guild: discord.Guild):
        guild_id = str(guild.id)
        config = guild_config.get(guild_id, {})
        welcome_channel_id = config.get("welcome_channel", {}).get("channel_id")
        goodbye_channel_id = config.get("goodbye_channel", {}).get("channel_id")
        # If system channel exists, update config if channels are missing.
        if guild.system_channel:
            if not welcome_channel_id:
                config["welcome_channel"]["channel_id"] = guild.system_channel.id
                save_config(guild_config)
            if not goodbye_channel_id:
                config["goodbye_channel"]["channel_id"] = guild.system_channel.id
                save_config(guild_config)
            # If now both are set, do nothing further.
            if (
                config["welcome_channel"]["channel_id"]
                and config["goodbye_channel"]["channel_id"]
            ):
                return
        # Otherwise, send warning message.
        message = (
            "Heyo ~ ! It seems that no system channel was found, and no welcome/goodbye channels are set.\n\n"
            "Please set the system channel from **Server Settings -> Engagement -> System Message Channel** "
            "or use `/set_welcome_channel` and/or `/set_goodbye_channel` commands to configure them.\n\n"
            "If you would like to disable these greetings, you can use `/greetings` command and select `Disable` option."
        )
        if guild.system_channel:
            await guild.system_channel.send(message)
        else:
            owner = guild.owner
            if owner:
                try:
                    await owner.send(
                        f"Hello from {self.user.name} in **{guild.name}**!\n\n{message}"
                    )
                    return
                except discord.Forbidden:
                    print(f"Could not DM the owner of {guild.name}.")
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(message)
                    break

    async def on_guild_remove(self, guild: discord.Guild):
        self.stats["guild_count"] = len(self.guilds)
        guild_id = str(guild.id)
        if guild_id in guild_config:
            del guild_config[guild_id]
            save_config(guild_config)

    async def on_member_join(self, member: discord.Member):
        guild_id = str(member.guild.id)
        config = guild_config.get(guild_id, {})

        if not config.get("greetings"):
            return

        welcome_config = config.get("welcome_channel", {})
        channel_id = welcome_config.get("channel_id")
        channel = self.get_channel(channel_id)
        auto_roles = config.get("auto_roles", {})
        user_auto_roles = auto_roles.get("users", [])
        bot_auto_roles = auto_roles.get("bots", [])

        if channel:
            await member.display_avatar.save("./assets/user_pfp.png")
            img = discord.File(create_banner(member.display_name))
            template = welcome_config.get("message_template", {})
            msg = template.get("bot" if member.bot else "user", "Welcome!")
            await channel.send(msg.format(member=member), file=img)

            guild = self.get_guild(member.guild.id)

            if not member.bot and user_auto_roles:
                for role in user_auto_roles:
                    await member.add_roles(guild.get_role(role))

            if member.bot and bot_auto_roles:
                for role in bot_auto_roles:
                    await member.add_roles(guild.get_role(role))

    async def on_member_remove(self, member: discord.Member):
        guild_id = str(member.guild.id)
        config = guild_config.get(guild_id, {})

        if not config.get("greetings"):
            return

        goodbye_config = config.get("goodbye_channel", {})
        channel_id = goodbye_config.get("channel_id")
        channel = self.get_channel(channel_id)

        if channel:
            await member.display_avatar.save("./assets/user_pfp.png")
            img = discord.File(create_banner(member.display_name, leave=True))
            template = goodbye_config.get("message_template", {})
            msg = template.get("bot" if member.bot else "user", "Goodbye!")
            await channel.send(msg.format(member=member), file=img)

    async def on_raw_reaction_add(self, payload):
        guild_id = str(payload.guild_id)
        config = guild_config.get(guild_id, {})
        reaction_roles_config = config.get("reaction_roles", {})
        # Ensure channel_id and message_id are used as string keys
        channel_key = str(payload.channel_id)
        message_key = str(payload.message_id)
        channel_config = reaction_roles_config.get(channel_key, {})
        if channel_config and message_key in channel_config:
            guild = self.get_guild(payload.guild_id)
            # Use the string representation of emoji as stored
            role_id = channel_config.get(message_key, {}).get(str(payload.emoji))
            if role_id:
                role = guild.get_role(int(role_id))
                member = guild.get_member(payload.user_id)
                if role and member:
                    await member.add_roles(role)

    async def on_raw_reaction_remove(self, payload):
        guild_id = str(payload.guild_id)
        config = guild_config.get(guild_id, {})
        reaction_roles_config = config.get("reaction_roles", {})
        channel_key = str(payload.channel_id)
        message_key = str(payload.message_id)
        channel_config = reaction_roles_config.get(channel_key, {})
        if channel_config and message_key in channel_config:
            guild = self.get_guild(payload.guild_id)
            role_id = channel_config.get(message_key, {}).get(str(payload.emoji))
            if role_id:
                role = guild.get_role(int(role_id))
                member = guild.get_member(payload.user_id)
                if role and member:
                    await member.remove_roles(role)

    async def on_message_delete(self, message: discord.Message):
        # If the deleted message was a reaction role message, remove it from config.
        guild_id = str(message.guild.id)
        config = guild_config.get(guild_id, {})
        rr_config = config.get("reaction_roles", {})
        channel_key = str(message.channel.id)
        message_key = str(message.id)
        if channel_key in rr_config and message_key in rr_config[channel_key]:
            del guild_config[guild_id]["reaction_roles"][channel_key][message_key]
            # Remove empty channel entries.
            if not guild_config[guild_id]["reaction_roles"][channel_key]:
                del guild_config[guild_id]["reaction_roles"][channel_key]
            save_config(guild_config)

    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        honey = guild_config.get(str(message.guild.id), {}).get("honey_pot")
        if honey and message.channel.id == honey.get("channel_id"):
            allow_owner = honey.get("allow_owner", False)
            if allow_owner and message.author.id == message.guild.owner_id:
                return
            try:
                # Ban the user
                await message.guild.ban(message.author, reason="Honey pot triggered")
                # Forward message details to moderation channel if configured
                mod_channel_id = guild_config.get(str(message.guild.id), {}).get(
                    "honey_pot_mod_channel"
                )
                if mod_channel_id:
                    mod_channel = self.get_channel(mod_channel_id)
                    if mod_channel:
                        embed = Embed(
                            title="Honey Pot Alert",
                            description=(
                                f"User {message.author.mention} triggered the honey pot in "
                                f"{message.channel.mention}."
                            ),
                            color=0xFF0000,
                        )
                        embed.add_field(
                            name="Message Content",
                            value=message.content or "No content",
                            inline=False,
                        )
                        embed.set_footer(
                            text=f"User ID: {message.author.id} | Channel ID: {message.channel.id}"
                        )
                        await mod_channel.send(embed=embed)
                # Delete message
                await message.delete()
            except Exception as e:
                print(f"Error handling honey pot for {message.author}: {e}")

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        config = guild_config.get(str(channel.guild.id), {})
        honey = config.get("honey_pot")
        if honey and honey.get("channel_id") == channel.id:
            del config["honey_pot"]
            save_config(guild_config)


activity = discord.Activity(
    name="萌え萌えキュン ♡(⸝⸝> ᴗ•⸝⸝)", type=discord.ActivityType.streaming
)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = MyClient(bot_stats, intents, activity)


@client.tree.command(name="ping", description="Check the bot's response time.")
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000)  # Convert to milliseconds
    await interaction.response.send_message(
        f"Pong! 🏓 | Response time: {latency}ms", ephemeral=True
    )


@client.tree.command(
    name="greetings",
    description="Enable or Disable welcome and goodbye messages sent when a member joins the server.",
)
@app_commands.describe(action="Enable or Disable welcome and goodbye greetings.")
@app_commands.choices(
    action=[
        app_commands.Choice(name="Enable", value="true"),
        app_commands.Choice(name="Disable", value="false"),
    ]
)
@app_commands.check(owner_only)
async def greetings(interaction: discord.Interaction, action: app_commands.Choice[str]):
    guild_id = str(interaction.guild_id)
    if guild_id in guild_config:
        guild_config[guild_id]["greetings"] = True if action.value == "true" else False
        save_config(guild_config)

    await interaction.response.send_message(
        f"Greeting messages has been {action.name.lower()}d.", ephemeral=True
    )


@client.tree.context_menu(name="greet_member")
@app_commands.check(owner_only)
async def greet_member(interaction: discord.Interaction, member: discord.Member):
    guild_id = str(interaction.guild_id)
    config = guild_config.get(guild_id, {})

    if not config.get("greetings"):
        await interaction.response.send_message(
            "Greetings are disabled for this server.", ephemeral=True
        )

    welcome_config = config.get("welcome_channel", {})
    channel_id = welcome_config.get("channel_id")
    channel = client.get_channel(channel_id)
    auto_roles = config.get("auto_roles", {})
    user_auto_roles = auto_roles.get("users", [])
    bot_auto_roles = auto_roles.get("bots", [])

    if channel:
        await interaction.response.send_message(
            f"Greeted {member.mention} successfully!\nIt may take some time for me to send message.",
            ephemeral=True,
        )

        await member.display_avatar.save("./assets/user_pfp.png")
        img = discord.File(create_banner(member.display_name))
        template = welcome_config.get("message_template", {})
        msg = template.get("bot" if member.bot else "user", "Welcome!")
        await channel.send(msg.format(member=member, guild=interaction.guild), file=img)

        guild = interaction.guild

        if not member.bot and user_auto_roles:
            for role in user_auto_roles:
                await member.add_roles(guild.get_role(role))

        if member.bot and bot_auto_roles:
            for role in bot_auto_roles:
                await member.add_roles(guild.get_role(role))

    else:
        await interaction.response.send_message(
            "Could not find the welcome channel.", ephemeral=True
        )


@client.tree.command(
    name="set_welcome_channel",
    description="Set the channel for sending welcome greetings for new members.",
)
@app_commands.describe(channel="The channel to send welcome greeting messages.")
@app_commands.check(owner_only)
async def set_greeting_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    guild_id = str(interaction.guild_id)
    if guild_id in guild_config:
        guild_config[guild_id]["welcome_channel"]["channel_id"] = channel.id
        save_config(guild_config)
    await interaction.response.send_message(
        f"Welcome greeting channel set to {channel.mention}", ephemeral=True
    )


@client.tree.command(
    name="set_goodbye_channel",
    description="Set the channel for sending goodbye messages when a member leaves.",
)
@app_commands.describe(channel="The channel to send goodbye messages.")
@app_commands.check(owner_only)
async def set_goodbye_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
    guild_id = str(interaction.guild_id)
    if guild_id in guild_config:
        guild_config[guild_id]["goodbye_channel"]["channel_id"] = channel.id
        save_config(guild_config)
    await interaction.response.send_message(
        f"Goodbye message channel set to {channel.mention}", ephemeral=True
    )


@client.tree.command(
    name="reaction_roles", description="Create or manage reaction roles."
)
@app_commands.check(owner_only)
async def reaction_roles(interaction: discord.Interaction):
    view = ReactionRoleMainView()
    await interaction.response.send_message(
        "Click a button below to create or manage reaction roles:",
        view=view,
    )


class ReactionRoleMainView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(
        label="Create Reaction Role",
        style=discord.ButtonStyle.primary,
    )
    async def create_reaction_role(
        self, interaction: discord.Interaction, button: Button
    ):
        await interaction.response.edit_message(
            content="Click the button below to enter the reaction role message.\nYou can enter plain text (Markdown supported) or paste JSON from [Discohook](https://discohook.org/)'s JSON Data Editor.",
            view=CreateMessageView(),
        )

    @discord.ui.button(
        label="Manage Reaction Roles",
        style=discord.ButtonStyle.secondary,
    )
    async def manage_reaction_roles(
        self, interaction: discord.Interaction, button: Button
    ):
        guid_id = str(interaction.guild_id)
        config = guild_config.get(guid_id, {})
        reaction_roles_ = config.get("reaction_roles", {})

        if not reaction_roles_ or not any(reaction_roles_.values()):
            await interaction.response.edit_message(
                content="No reaction roles are currently set.",
                view=None,
            )
            return

        # Flatten all messages into a list of (channel_id, message_id)
        rr_list = []
        for channel_id, messages in reaction_roles_.items():
            for msg_id in messages:
                rr_list.append((channel_id, msg_id))

        await interaction.response.edit_message(
            content="Select a reaction role message to manage:",
            view=ReactionRoleListView(rr_list),
        )


class ReactionRoleListView(View):
    def __init__(self, rr_list):
        super().__init__(timeout=300)
        self.rr_list = rr_list
        for channel_id, msg_id in rr_list:
            # Set label at creation time
            label = self._get_label(channel_id, msg_id)
            self.add_item(ReactionRoleMessageButton(channel_id, msg_id, label=label))

    def _get_label(self, channel_id, msg_id):
        # Try to get channel name and message preview from config
        channel_name = f"#{channel_id}"
        preview = ""
        # Try to get channel name from the global client if possible
        channel = None
        try:
            # This import is safe here because client is defined globally
            from __main__ import client

            for guild in client.guilds:
                ch = guild.get_channel(int(channel_id))
                if ch:
                    channel = ch
                    break
        except Exception:
            pass
        if channel and hasattr(channel, "name"):
            channel_name = f"#{channel.name}"
        # Try to get preview from config
        for guild_id, config in guild_config.items():
            rrdata = (
                config.get("reaction_roles", {}).get(channel_id, {}).get(msg_id, {})
            )
            msg_content = rrdata.get("_raw_content")
            if msg_content:
                try:
                    data = json.loads(msg_content)
                    if isinstance(data, dict):
                        if data.get("content"):
                            preview = data["content"][:40]
                        elif (
                            data.get("embeds")
                            and isinstance(data["embeds"], list)
                            and data["embeds"]
                        ):
                            embed = data["embeds"][0]
                            preview = embed.get("title", "")[:40]
                    else:
                        preview = str(data)[:40]
                except Exception:
                    preview = str(msg_content)[:40]
                break
        if not preview:
            preview = "(no content)"
        return f"{channel_name}: {preview}"


class ReactionRoleMessageButton(Button):
    def __init__(self, channel_id, msg_id, label=None):
        super().__init__(
            label=label or "Loading...",
            style=discord.ButtonStyle.secondary,
            custom_id=f"rrmsg_{channel_id}_{msg_id}",
        )
        self.channel_id = channel_id
        self.msg_id = msg_id

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(int(self.channel_id))
        if not channel:
            await interaction.response.send_message(
                "Channel not found.", ephemeral=True
            )
            return
        # Try to get preview from config
        preview = ""
        guid_id = str(interaction.guild_id)
        config = guild_config.get(guid_id, {})
        rrdata = (
            config.get("reaction_roles", {})
            .get(self.channel_id, {})
            .get(self.msg_id, {})
        )
        msg_content = rrdata.get("_raw_content")
        if msg_content:
            try:
                data = json.loads(msg_content)
                if isinstance(data, dict):
                    if data.get("content"):
                        preview = data["content"][:40]
                    elif (
                        data.get("embeds")
                        and isinstance(data["embeds"], list)
                        and data["embeds"]
                    ):
                        embed = data["embeds"][0]
                        preview = embed.get("title", "")[:40]
                else:
                    preview = str(data)[:40]
            except Exception:
                preview = str(msg_content)[:40]
        else:
            try:
                msg = await channel.fetch_message(int(self.msg_id))
                if msg.content:
                    preview = msg.content[:40]
                elif msg.embeds:
                    preview = (
                        msg.embeds[0].title[:40] if msg.embeds[0].title else "(embed)"
                    )
                else:
                    preview = "(no content)"
            except Exception:
                preview = "(unavailable)"
        channel_name = (
            f"#{channel.name}" if hasattr(channel, "name") else f"#{self.channel_id}"
        )
        self.label = f"{channel_name}: {preview}"
        await interaction.response.edit_message(
            content=f"Selected message in <#{self.channel_id}> ([Jump](https://discord.com/channels/{interaction.guild.id}/{self.channel_id}/{self.msg_id})).\nWhat would you like to do?",
            view=ReactionRoleEditView(self.channel_id, self.msg_id),
        )


class ReactionRoleEditView(View):
    def __init__(self, channel_id, msg_id):
        super().__init__(timeout=300)
        self.channel_id = channel_id
        self.msg_id = msg_id

    @discord.ui.button(label="Edit Message", style=discord.ButtonStyle.primary, row=0)
    async def edit(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(
            ReactionRoleEditModal(self.channel_id, self.msg_id)
        )

    @discord.ui.button(label="Delete Message", style=discord.ButtonStyle.danger, row=0)
    async def delete(self, interaction: discord.Interaction, button: Button):
        channel = interaction.guild.get_channel(int(self.channel_id))
        if not channel:
            await interaction.response.send_message(
                "Channel not found.", ephemeral=True
            )
            return
        try:
            msg = await channel.fetch_message(int(self.msg_id))
            await msg.delete()
        except Exception:
            await interaction.response.send_message(
                "Message not found or already deleted.", ephemeral=True
            )
            return
        # Remove from config
        guid_id = str(interaction.guild_id)
        if guid_id in guild_config:
            rr = guild_config[guid_id].get("reaction_roles", {})
            if self.channel_id in rr and self.msg_id in rr[self.channel_id]:
                del rr[self.channel_id][self.msg_id]
                if not rr[self.channel_id]:
                    del rr[self.channel_id]
                save_config(guild_config)
        await interaction.response.edit_message(
            content="Reaction role message deleted.", view=None
        )

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: Button):
        guid_id = str(interaction.guild_id)
        config = guild_config.get(guid_id, {})
        reaction_roles_ = config.get("reaction_roles", {})
        rr_list = []
        for channel_id, messages in reaction_roles_.items():
            for msg_id in messages:
                rr_list.append((channel_id, msg_id))
        await interaction.response.edit_message(
            content="Select a reaction role message to manage:",
            view=ReactionRoleListView(rr_list),
        )


class ReactionRoleEditModal(Modal, title="Edit Reaction Role Message"):
    def __init__(self, channel_id, msg_id):
        super().__init__()
        self.channel_id = channel_id
        self.msg_id = msg_id
        # Load the saved message content from config
        self.default_content = ""
        for guild_id, config in guild_config.items():
            rr = config.get("reaction_roles", {}).get(channel_id, {})
            if (
                msg_id in rr
                and isinstance(rr[msg_id], dict)
                and rr[msg_id].get("_raw_content")
            ):
                self.default_content = rr[msg_id]["_raw_content"]
                break
        self.message_input = TextInput(
            label="Message Content",
            placeholder="Enter plain text (Markdown supported) or paste JSON from Discohook's JSON Data Editor.",
            style=discord.TextStyle.paragraph,
            required=True,
            default=self.default_content[:4000] if self.default_content else None,
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        content_raw = self.message_input.value.strip()
        try:
            data = json.loads(content_raw)
            content = data.get("content", None)
            embeds_data = data.get("embeds", [])
            embed = (
                Embed.from_dict(embeds_data[0])
                if embeds_data and isinstance(embeds_data, list) and embeds_data[0]
                else None
            )
        except Exception:
            content = content_raw
            embed = None
        channel = interaction.guild.get_channel(int(self.channel_id))
        if not channel:
            await interaction.response.send_message(
                "Channel not found.", ephemeral=True
            )
            return
        try:
            msg = await channel.fetch_message(int(self.msg_id))
            await msg.edit(content=content, embed=embed)
            # Save the new content to config
            guid_id = str(interaction.guild_id)
            if guid_id in guild_config:
                rr = guild_config[guid_id].get("reaction_roles", {})
                if self.channel_id in rr and self.msg_id in rr[self.channel_id]:
                    if isinstance(rr[self.channel_id][self.msg_id], dict):
                        rr[self.channel_id][self.msg_id]["_raw_content"] = content_raw
                    else:
                        rr[self.channel_id][self.msg_id] = {"_raw_content": content_raw}
                    save_config(guild_config)
        except Exception:
            await interaction.response.send_message(
                "Failed to edit message.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content="Reaction role message updated!", view=None
        )


class CreateMessageView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Enter Message", style=discord.ButtonStyle.primary)
    async def enter_message(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ReactionRoleMessageModal())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="Reaction role creation canceled.",
            view=None,
        )


class ReactionRoleMessageModal(Modal, title="Enter Reaction Role Message"):
    def __init__(self):
        super().__init__()
        self.message_input = TextInput(
            label="Message Content",
            placeholder=(
                "Enter plain text (Markdown supported) or paste JSON from Discohook's JSON Data Editor."
            ),
            style=discord.TextStyle.paragraph,
            required=True,
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        content_raw = self.message_input.value.strip()
        try:
            data = json.loads(content_raw)
            # Support full Discohook payload
            content = data.get("content", None)
            embeds_data = data.get("embeds", [])
            embed = (
                Embed.from_dict(embeds_data[0])
                if embeds_data and isinstance(embeds_data, list) and embeds_data[0]
                else None
            )
        except json.JSONDecodeError:
            content = content_raw
            embed = None

        # You could pass the raw message_input (content_raw) along,
        # or you can even pass a tuple (content, embed) if needed.
        view = ReactionRoleChannelSelectView(content_raw)
        await interaction.response.edit_message(
            content="Select the channel where the reaction role message will be sent.",
            view=view,
        )


class ReactionRoleChannelSelectView(View):
    def __init__(self, message_content):
        super().__init__(timeout=300)
        self.message_content = message_content
        self.channel_id = None
        self.channel_select = ChannelSelect(
            placeholder="Select a text channel",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )
        self.cancel_button = Button(label="Cancel", style=discord.ButtonStyle.danger)

        self.channel_select.callback = self.channel_selected_callback
        self.cancel_button.callback = self.cancel_callback

        self.add_item(self.channel_select)
        self.add_item(self.cancel_button)

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Reaction role creation canceled.",
            view=None,
        )

    async def channel_selected_callback(self, interaction: discord.Interaction):
        if self.channel_select.values:
            self.channel_id = self.channel_select.values[0].id
            # Pass an empty accumulator dictionary.
            view = ReactionRoleRoleSelectView(
                self.message_content, str(self.channel_id), accum={}
            )
            await interaction.response.edit_message(
                content=f"Channel selected: <#{self.channel_id}>.\nNow select a role to associate with an emoji.",
                view=view,
            )
        else:
            await interaction.response.edit_message(
                content="No channel selected. Please try again.", view=None
            )


class ReactionRoleRoleSelectView(View):
    def __init__(self, message_content, channel_id, accum=None):
        super().__init__(timeout=300)
        self.message_content = message_content
        # Use channel_id as string.
        self.channel_id = channel_id
        self.accum = accum if accum is not None else {}
        self.role_select = RoleSelect(
            placeholder="Select a role",
            min_values=1,
            max_values=1,
        )
        self.cancel_button = Button(label="Cancel", style=discord.ButtonStyle.danger)

        self.role_select.callback = self.role_selected_callback
        self.cancel_button.callback = self.cancel_callback

        self.add_item(self.role_select)
        self.add_item(self.cancel_button)

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Reaction role creation canceled.",
            view=None,
        )

    async def role_selected_callback(self, interaction: discord.Interaction):
        if not self.role_select.values:
            view = ReactionRoleRoleSelectView(
                message_content="No role selected. Please try again",
                channel_id=self.channel_id,
                accum=self.accum,
            )
            await interaction.response.edit_message(
                content="No role selected. Please try again.", view=view
            )
            return
        # Use role ID as int then convert to str for saving later.
        role_id = str(self.role_select.values[0].id)
        if role_id in list(self.accum.values()):
            view = ReactionRoleRoleSelectView(
                message_content="You already selected this role! Please select another role.",
                channel_id=self.channel_id,
                accum=self.accum,
            )
            await interaction.response.edit_message(
                content="You already selected this role! Please select another role.",
                view=view,
            )
            return

        await interaction.response.edit_message(
            content=f"Role selected: <@&{role_id}>.\nPlease react to *this message* with the emoji you want to associate.",
            view=None,
        )

        def check(reaction, user):
            return (
                user == interaction.user
                and reaction.message.id == interaction.message.id
                and reaction.emoji
            )

        try:
            reaction, _ = await client.wait_for("reaction_add", check=check, timeout=60)
            await interaction.message.clear_reactions()
            emoji = reaction.emoji
            # Use str(emoji) as JSON key.
            emoji_key = str(emoji)
            if isinstance(emoji, str) or (emoji.is_custom_emoji() and emoji.guild_id):
                # Instead of saving config now, update our accum dictionary.
                self.accum[emoji_key] = role_id
                # Now pass the updated accum to the summary view.
                view = ReactionRoleSummaryView(
                    self.message_content, self.channel_id, accum=self.accum
                )

                emoji_role_pairs = ""
                for emoji, role in self.accum.items():
                    emoji_role_pairs += f"\n{emoji} - <@&{role}>"
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    content=f"Emoji-role pair(s) added:\n{emoji_role_pairs}",
                    view=view,
                )
            else:
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    content="Invalid emoji. Please try again with a valid emoji.",
                    view=None,
                )
        except asyncio.TimeoutError:
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content="You took too long to react. Please try again.",
                view=None,
            )


class ReactionRoleSummaryView(View):
    def __init__(self, message_content, channel_id, accum):
        super().__init__(timeout=300)
        self.message_content = message_content
        self.channel_id = channel_id
        self.accum = accum  # This dict stores emoji: role_id pairs.

    @discord.ui.button(label="Add More Roles", style=discord.ButtonStyle.primary)
    async def add_more_roles(self, interaction: discord.Interaction, button: Button):
        # Pass the current accumulator forward.
        view = ReactionRoleRoleSelectView(
            self.message_content, self.channel_id, accum=self.accum
        )
        await interaction.response.edit_message(
            content="Select another role to associate with an emoji.",
            view=view,
        )

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: Button):
        channel = interaction.client.get_channel(int(self.channel_id))
        if not channel:
            await interaction.response.edit_message(
                content="Invalid channel. Please try again.", view=None
            )
            return
        try:
            data = json.loads(self.message_content)
            if isinstance(data, dict):
                content = data.get("content", None)
                embeds_data = data.get("embeds", [])
                embed = (
                    Embed.from_dict(embeds_data[0])
                    if embeds_data and isinstance(embeds_data, list) and embeds_data[0]
                    else None
                )
            else:
                content = self.message_content
                embed = None
        except json.JSONDecodeError:
            content = self.message_content
            embed = None
        sent_message = await channel.send(content=content, embed=embed)
        # Automatically add each emoji from accumulator as reaction.
        for emoji in self.accum.keys():
            try:
                await sent_message.add_reaction(emoji)
            except discord.HTTPException:
                print(f"Failed to add reaction: {emoji}")
        guild_id = str(interaction.guild_id)
        msg_id = str(sent_message.id)
        if guild_id not in guild_config:
            guild_config[guild_id] = {"reaction_roles": {}}
        if str(self.channel_id) not in guild_config[guild_id].get("reaction_roles", {}):
            guild_config[guild_id].setdefault("reaction_roles", {})[
                str(self.channel_id)
            ] = {}
        # Save both the emoji-role mapping and the raw content
        guild_config[guild_id]["reaction_roles"][str(self.channel_id)][msg_id] = {
            **self.accum,
            "_raw_content": self.message_content,
        }
        save_config(guild_config)
        await interaction.response.edit_message(
            content=f"Reaction role message sent in <#{self.channel_id}>.",
            view=None,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="Reaction role creation canceled.",
            view=None,
        )


# Modal for updating message templates via a form with placeholder guides added in input placeholders
class TemplateUpdateModal(Modal, title="Update Message Template"):
    def __init__(self, guild_id: str, template_type: str):
        super().__init__()
        self.guild_id = guild_id
        self.template_type = template_type  # "welcome_channel" or "goodbye_channel"
        curr_conf = guild_config.get(guild_id, {}).get(template_type, {})
        current_user = curr_conf.get("message_template", {}).get("user", "")
        current_bot = curr_conf.get("message_template", {}).get("bot", "")
        placeholder_info = (
            "(e.g. {member.mention}, {member.display_name}, {guild.name})"
        )
        self.user_template = TextInput(
            label="User Template",
            placeholder=f"Enter user template... {placeholder_info}",
            default=current_user,
            style=discord.TextStyle.paragraph,
            required=True,
        )
        self.add_item(self.user_template)
        self.bot_template = TextInput(
            label="Bot Template (Leave blank to keep current)",
            placeholder=f"Enter bot template... {placeholder_info}",
            default=current_bot,
            style=discord.TextStyle.paragraph,
            required=False,
        )
        self.add_item(self.bot_template)

    async def on_submit(self, interaction: discord.Interaction):
        new_user = self.user_template.value.strip()
        new_bot = self.bot_template.value.strip()
        guild_id = self.guild_id
        template_type = self.template_type
        curr_conf = guild_config.get(guild_id, {}).get(template_type, {})
        current_bot = curr_conf.get("message_template", {}).get("bot", "")
        if not new_bot:
            new_bot = current_bot
        if guild_id not in guild_config:
            guild_config[guild_id] = {}
        if template_type not in guild_config[guild_id]:
            guild_config[guild_id][template_type] = {}
        guild_config[guild_id][template_type]["message_template"] = {
            "user": new_user,
            "bot": new_bot,
        }
        save_config(guild_config)
        embed = Embed(
            title="Message Template Updated",
            description=(
                f"Template Type: **{'Welcome' if template_type=='welcome_channel' else 'Goodbye'}**\n\n"
                f"User Template:\n```{new_user}```\n"
                f"Bot Template:\n```{new_bot}```"
            ),
            color=0xF28A8A,
        )
        # Instead of editing the previous message, send a new ephemeral message.
        await interaction.response.send_message(embed=embed, ephemeral=True)


# View to show current template guide and a button to edit it
class TemplateEditView(View):
    def __init__(self, guild_id: str, template_type: str):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.template_type = template_type

    @discord.ui.button(label="Edit Template", style=discord.ButtonStyle.primary)
    async def edit_template(self, interaction: discord.Interaction, button: Button):
        modal = TemplateUpdateModal(
            guild_id=self.guild_id, template_type=self.template_type
        )
        await interaction.response.send_modal(modal)


@client.tree.command(
    name="message_template",
    description="Customize your server's welcome or goodbye message.",
)
@app_commands.describe(type="Choose which message to customize")
@app_commands.choices(
    type=[
        app_commands.Choice(name="Welcome Message", value="welcome_channel"),
        app_commands.Choice(name="Goodbye Message", value="goodbye_channel"),
    ]
)
@app_commands.check(owner_only)
async def message_template(
    interaction: discord.Interaction, type: app_commands.Choice[str]
):
    guild_id = str(interaction.guild.id)
    template_type = type.value
    curr_conf = guild_config.get(guild_id, {}).get(template_type, {})
    current_user = curr_conf.get("message_template", {}).get("user", "Not set")
    current_bot = curr_conf.get("message_template", {}).get("bot", "Not set")

    guide_text = (
        f"**Current {'Welcome' if template_type=='welcome_channel' else 'Goodbye'} Message:**\n"
        f"User version: ```{current_user}```\n"
        f"Bot version: ```{current_bot}```\n\n"
        "**Tips:**\n"
        "`{member.mention}` – to mention a new member\n"
        "`{member.display_name}` – for their name\n"
        "`{guild.name}` – for your server's name\n"
        "`<#channel_id>` – to mention a channel\n"
        "`<@&role_id>` – to mention a role"
    )
    embed = Embed(
        title="Current Message Settings",
        description=guide_text,
        color=0xF28A8A,
    )
    view = TemplateEditView(guild_id=guild_id, template_type=template_type)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@client.tree.command(
    name="add_reaction_role", description="Add a reaction role to an existing message."
)
@app_commands.describe(
    channel="Channel containing the message",
    message_id="ID of the message",
    emoji="Emoji to add (e.g., 😀 or <:custom:123456789>)",
    role="Role to assign when reacted",
)
@app_commands.check(owner_only)
async def add_reaction_role(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message_id: str,
    emoji: str,
    role: discord.Role,
):
    await interaction.response.defer(
        ephemeral=True
    )  # Defer early to acknowledge interaction
    guild_id = str(interaction.guild.id)
    try:
        msg = await channel.fetch_message(int(message_id))
    except Exception as e:
        await interaction.followup.send(f"Error fetching message: {e}", ephemeral=True)
        return
    try:
        await msg.add_reaction(emoji)
    except Exception as e:
        await interaction.followup.send(f"Error adding reaction: {e}", ephemeral=True)
        return

    if guild_id not in guild_config:
        guild_config[guild_id] = {}
    guild_config[guild_id].setdefault("reaction_roles", {})
    channel_key = str(channel.id)
    guild_config[guild_id]["reaction_roles"].setdefault(channel_key, {})
    message_key = message_id
    # Merge new emoji-role pair into the dictionary, preserving existing pairs if any.
    existing = guild_config[guild_id]["reaction_roles"][channel_key].get(
        message_key, {}
    )
    existing[str(emoji)] = str(role.id)
    guild_config[guild_id]["reaction_roles"][channel_key][message_key] = existing
    save_config(guild_config)

    await interaction.followup.send(
        f"Successfully added reaction role: {emoji} ➡️ {role.mention} on message ID {message_id} in {channel.mention}.",
        ephemeral=True,
    )


@client.tree.command(
    name="honey_pot",
    description="Setup channel to trap compromised accounts. Sending message there will get them banned immediately.",
)
@app_commands.describe(
    channel="Select a public text channel for honey pot deployment",
    allow_owner="Allow the server owner to send messages in this channel (default: not allowed)",
    mod_channel="Optional: Select a channel to receive honey pot alerts",
)
@app_commands.check(owner_only)
async def honey_pot(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    allow_owner: bool = False,
    mod_channel: discord.TextChannel = None,
):
    perms = channel.permissions_for(interaction.guild.default_role)
    if not perms.send_messages:
        await interaction.response.send_message(
            "The selected channel is not public (everyone cannot send messages).",
            ephemeral=True,
        )
        return
    guild_id = str(interaction.guild.id)
    if guild_id not in guild_config:
        guild_config[guild_id] = {}
    if "honey_pot" not in guild_config[str(guild_id)]:
        guild_config[str(guild_id)]["honey_pot"] = {}
    guild_config[guild_id]["honey_pot"] = {
        "channel_id": channel.id,
        "allow_owner": allow_owner,
        "honey_pot_mod_channel": mod_channel.id if mod_channel else None,
    }
    save_config(guild_config)
    try:
        await channel.send(
            "# <a:warn:1355807146851176519>DO NOT POST HERE<a:warn:1355807146851176519>\n\n\n"
            "This channel is a honeypot for compromised accounts. If you send anything here, "
            "you WILL BE BANNED immediately.\n\nYes, I AM SERIOUS ~ <:ganyu_huh:1355807607075373056> !!"
        )
    except Exception as e:
        print(f"Error sending message in honey pot channel: {e}")
    await interaction.response.send_message(
        f"Honey pot channel set to {channel.mention}. Alerts forwarded to {mod_channel.mention if mod_channel else 'none'}.",
        ephemeral=True,
    )


@client.tree.command(
    name="auto_roles",
    description="Automatically assign role(s) to users or bot users on join.",
)
@app_commands.describe(type="Choose which user type to assign roles automatically.")
@app_commands.choices(
    type=[
        app_commands.Choice(name="Bot", value="bots"),
        app_commands.Choice(name="User", value="users"),
    ]
)
@app_commands.check(owner_only)
async def auto_bot_role(
    interaction: discord.Interaction, type: app_commands.Choice[str]
):
    guild_id = str(interaction.guild.id)
    user_type = type.value
    curr_conf = guild_config.get(guild_id, {}).get("auto_roles", {})
    current_user_roles = curr_conf.get("users", [])
    current_bot_roles = curr_conf.get("bots", [])

    view = AutobotRoleSelectView(
        message_content=f"Select roles to automatically assign to {user_type} when they join the server:",
        channel_id=interaction.channel.id,
        user_type=user_type,
        accum={"users": current_user_roles, "bots": current_bot_roles},
    )
    await interaction.response.send_message(
        f"Select a role to automatically assign to {user_type} when they join the server:",
        view=view,
        ephemeral=True,
    )


class AutobotRoleSelectView(View):
    def __init__(self, message_content, channel_id, user_type, accum=None):
        super().__init__(timeout=300)
        self.message_content = message_content
        self.channel_id = channel_id
        self.user_type = user_type
        self.accum = accum if accum is not None else {"users": [], "bots": []}
        self.role_select = RoleSelect(
            placeholder="Select a role",
            min_values=1,
            max_values=1,
        )
        self.cancel_button = Button(label="Cancel", style=discord.ButtonStyle.danger)

        self.role_select.callback = self.role_selected_callback
        self.cancel_button.callback = self.cancel_callback

        self.add_item(self.role_select)
        self.add_item(self.cancel_button)

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Auto roles creation canceled.",
            view=None,
        )

    async def role_selected_callback(self, interaction: discord.Interaction):
        if not self.role_select.values:
            view = AutobotRoleSelectView(
                message_content=f"Select roles to automatically assign to {self.user_type} when they join the server:",
                channel_id=interaction.channel.id,
                user_type=self.user_type,
                accum=self.accum,
            )
            await interaction.response.edit_message(
                content="No role selected. Please try again.", view=view
            )
            return

        role_id = self.role_select.values[0].id
        if role_id in self.accum[self.user_type]:
            view = AutobotRoleSelectView(
                message_content=f"This role has already been assigned to `{self.user_type}`. Please choose another role:",
                channel_id=interaction.channel.id,
                user_type=self.user_type,
                accum=self.accum,
            )
            await interaction.response.edit_message(
                content=f"This role has already been assigned to `{self.user_type}`. Please choose another role:",
                view=view,
            )
            return

        self.accum[self.user_type].append(role_id)

        selected_roles = ""
        for role in self.accum[self.user_type]:
            selected_roles += f"\n<@&{role}>"

        # Now pass the updated accum to the summary view.
        view = AutobotRoleSummaryView(
            self.message_content,
            self.channel_id,
            user_type=self.user_type,
            accum=self.accum,
        )
        await interaction.response.edit_message(
            content=f"Following role(s) are selected for `{self.user_type}`:\n{selected_roles}",
            view=view,
        )


class AutobotRoleSummaryView(View):
    def __init__(self, message_content, channel_id, user_type, accum):
        super().__init__(timeout=300)
        self.message_content = message_content
        self.channel_id = channel_id
        self.user_type = user_type
        self.accum = accum  # This dictionary stores role_ids for users and bots

    @discord.ui.button(label="Add More Roles", style=discord.ButtonStyle.primary)
    async def add_more_roles(self, interaction: discord.Interaction, button: Button):
        # Pass the current accumulator forward.
        view = AutobotRoleSelectView(
            self.message_content,
            self.channel_id,
            user_type=self.user_type,
            accum=self.accum,
        )
        await interaction.response.edit_message(
            content=f"Select another role to automatically assign {self.user_type} when they join the server:",
            view=view,
        )

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: Button):
        guild_id = str(interaction.guild_id)
        if guild_id not in guild_config:
            guild_config[guild_id] = {"auto_roles": {}}
        guild_config[guild_id]["auto_roles"] = self.accum
        save_config(guild_config)
        await interaction.response.edit_message(
            content="Auto role(s) configured successfully.",
            view=None,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="Auto bot role creation canceled.",
            view=None,
        )


def run_bot_with_event(ready_event, client):
    log()
    bot = client
    bot.ready_event = ready_event
    bot.run(TOKEN, log_handler=None)
