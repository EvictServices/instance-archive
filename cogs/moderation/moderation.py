import asyncio
import re
import json
import discord

from contextlib import suppress
from datetime import timedelta
from io import BytesIO
from logging import getLogger
from textwrap import wrap
from time import perf_counter
from typing import Annotated, Callable, List, Literal, Optional, cast, Union
from zipfile import ZipFile
import humanize
from discord.ui import Button, View, button
import hashlib

from core.client import FlagConverter
import string
import random
from datetime import datetime, timedelta, timezone
import secrets

from .classes import ModConfig, Mod, ClearMod

from discord import (
    AuditLogAction,
    AuditLogEntry,
    Color,
    Embed,
    Emoji,
    File,
    Guild,
    HTTPException,
    Member,
    Message,
    NotFound,
    NotificationLevel,
    Object,
    PartialEmoji,
    RateLimited,
    Role,
    StageChannel,
    TextChannel,
    Thread,
    User,
    VoiceChannel,
    GuildSticker,
)
from discord.abc import GuildChannel
from discord.ext.commands import (
    hybrid_command,
    hybrid_group,
    BadArgument,
    BucketType,
    Cog,
    CommandError,
    Greedy,
    MaxConcurrency,
    Range,
    check,
    command,
    cooldown,
    group,
    has_permissions,
    max_concurrency,
    parameter,
    flag
)
from discord.utils import MISSING, format_dt, get, utcnow
from humanfriendly import format_timespan
from humanize import precisedelta
from xxhash import xxh64_hexdigest

import config
from cogs.config.extended.security.antinuke import Settings
from main import Evict
from tools import (
    convert_image,
    enlarge_emoji,
    quietly_delete,
    strip_roles,
    unicode_emoji,
    url_to_mime,
)
from core.client.context import Context
from tools.conversion import (
    Duration,
    PartialAttachment,
    StrictMember,
    StrictRole,
    StrictUser,
    TouchableMember,
    GoodRole,
)
from tools.formatter import codeblock, human_join, plural
from managers.paginator import Paginator
from tools.conversion.script import Script
from managers.paginator import Paginator

log = getLogger("evict/mod")
MASS_ROLE_CONCURRENCY = MaxConcurrency(1, per=BucketType.guild, wait=False)

FAKE_PERMISSIONS_TABLE = "fake_permissions"
fake_permissions = [
    "administrator",
    "ban_members",
    "kick_members",
    "manage_guild",
    "manage_channels",
    "manage_roles",
    "manage_messages",
    "view_audit_log",
    "manage_webhooks",
    "manage_expressions",
    "mute_members",
    "deafen_members",
    "move_members",
    "manage_nicknames",
    "mention_everyone",
    "view_guild_insights",
    "external_emojis",
    "moderate_members",
]

class WarnActionFlags(FlagConverter):
    threshold: Range[int, 1, 50] = flag(
        description="The number of warns needed to trigger this action"
    )
    duration: Optional[Duration] = flag(
        default=None,
        description="Duration for timeout/jail/ban actions"
    )

# class VerificationView(View):
#     def __init__(self):
#         super().__init__(timeout=None)

#     @discord.ui.button(label="Verify", style=discord.ButtonStyle.green, custom_id="verify_button")
#     async def verify_button(self, interaction: discord.Interaction, button: Button):
#         try:
#             member = interaction.guild.get_member(interaction.user.id)
#             settings = await interaction.client.db.fetchrow(
#                 "SELECT verify_role_id FROM verification.settings WHERE guild_id = $1",
#                 interaction.guild.id
#             )

#             if settings['verify_role_id'] in [role.id for role in member.roles]:
#                 return await interaction.response.send_message(
#                     "You are already verified!", ephemeral=True
#                 )

#             session_id = await interaction.client.get_cog('Moderation').create_verification_session(
#                 interaction.guild.id,
#                 interaction.user.id
#             )

#             try:
#                 embed = Embed(
#                     title="Verification Process",
#                     description="Click the button below to start verification",
#                     color=0x2F3136
#                 )
#                 embed.add_field(
#                     name="Time Limit",
#                     value="You have 30 minutes to complete verification"
#                 )

#                 verify_url = f"https://evict.bot/verify/{session_id}"
#                 await interaction.user.send(
#                     embed=embed,
#                     view=VerificationLinkView(verify_url)
#                 )

#                 await interaction.response.send_message(
#                     "Check your DMs for verification instructions!", ephemeral=True
#                 )

#             except discord.Forbidden:
#                 await interaction.response.send_message(
#                     "I couldn't DM you! Please enable DMs from server members.",
#                     ephemeral=True
#                 )

#         except Exception as e:
#             await interaction.response.send_message(
#                 "An error occurred. Please try again later.",
#                 ephemeral=True
#             )

# class VerificationLinkView(View):
#     def __init__(self, url: str):
#         super().__init__(timeout=None)
#         self.add_item(Button(label="Verify", url=url, style=discord.ButtonStyle.url))

# class SetupView(View):
#     def __init__(self, bot, ctx):
#         super().__init__(timeout=300)
#         self.bot = bot
#         self.ctx = ctx
#         self.level = None
#         self.channel = None
#         self.role = None

#     @discord.ui.select(
#         placeholder="Select Verification Level",
#         options=[
#             discord.SelectOption(label="Base", description="Basic verification methods"),
#             discord.SelectOption(label="Medium", description="Enhanced verification methods")
#         ]
#     )
#     async def select_level(self, interaction: discord.Interaction, select: discord.ui.Select):
#         if interaction.user.id != self.ctx.author.id:
#             return await interaction.response.send_message(
#                 "You cannot use this menu!", ephemeral=True
#             )

#         self.level = select.values[0].lower()
#         await interaction.response.defer()
#         await interaction.message.edit(
#             embed=Embed(
#                 title="Verification Setup",
#                 description=f"Level: **{select.values[0]}**\nChannel: {self.channel.mention if self.channel else 'Not Set'}\nRole: {self.role.mention if self.role else 'Not Set'}"
#             )
#         )

#     @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.blurple)
#     async def set_channel(self, interaction: discord.Interaction, button: Button):
#         if interaction.user.id != self.ctx.author.id:
#             return await interaction.response.send_message(
#                 "You cannot use this button!", ephemeral=True
#             )

#         await interaction.response.send_message(
#             "Please mention the channel where the verification message should be sent",
#             ephemeral=True
#         )

#         try:
#             message = await self.bot.wait_for(
#                 'message',
#                 timeout=30.0,
#                 check=lambda m: m.author == self.ctx.author and m.channel_mentions
#             )
#             self.channel = message.channel_mentions[0]
#             await message.delete()

#             await interaction.message.edit(
#                 embed=Embed(
#                     title="Verification Setup",
#                     description=f"Level: **{self.level}**\nChannel: {self.channel.mention if self.channel else 'Not Set'}\nRole: {self.role.mention if self.role else 'Not Set'}"
#                 )
#             )
#         except TimeoutError:
#             await interaction.followup.send("Setup timed out", ephemeral=True)

#     @discord.ui.button(label="Set Role", style=discord.ButtonStyle.blurple)
#     async def set_role(self, interaction: discord.Interaction, button: Button):
#         if interaction.user.id != self.ctx.author.id:
#             return await interaction.response.send_message(
#                 "You cannot use this button!", ephemeral=True
#             )

#         await interaction.response.send_message(
#             "Please mention the role to be given after verification",
#             ephemeral=True
#         )

#         try:
#             message = await self.bot.wait_for(
#                 'message',
#                 timeout=30.0,
#                 check=lambda m: m.author == self.ctx.author and m.role_mentions
#             )
#             self.role = message.role_mentions[0]
#             await message.delete()

#             await interaction.message.edit(
#                 embed=Embed(
#                     title="Verification Setup",
#                     description=f"Level: **{self.level}**\nChannel: {self.channel.mention if self.channel else 'Not Set'}\nRole: {self.role.mention if self.role else 'Not Set'}"
#                 )
#             )
#         except TimeoutError:
#             await interaction.followup.send("Setup timed out", ephemeral=True)

#     @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
#     async def save(self, interaction: discord.Interaction, button: Button):
#         if interaction.user.id != self.ctx.author.id:
#             return await interaction.response.send_message(
#                 "You cannot use this button!", ephemeral=True
#             )

#         if not all([self.level, self.channel, self.role]):
#             return await interaction.response.send_message(
#                 "Please set all options before saving!", ephemeral=True
#             )

#         await self.bot.db.execute(
#             """
#             INSERT INTO verification.settings
#             (guild_id, level, verify_channel_id, verify_role_id)
#             VALUES ($1, $2, $3, $4)
#             ON CONFLICT (guild_id)
#             DO UPDATE SET
#                 level = $2,
#                 verify_channel_id = $3,
#                 verify_role_id = $4
#             """,
#             self.ctx.guild.id, self.level, self.channel.id, self.role.id
#         )

#         verify_embed = Embed(
#             title="Server Verification",
#             description="Click the button below to verify your account",
#             color=0x2F3136
#         )
#         await self.channel.send(embed=verify_embed, view=VerificationView())

#         await interaction.response.send_message(
#             "Verification setup complete!", ephemeral=True
#         )
#         self.stop()


class ModStatsView(View):
    def __init__(self, bot, moderator_id):
        super().__init__()
        self.bot = bot
        self.moderator_id = moderator_id
        self._message_cache = {}

    @button(
        label="Details", style=discord.ButtonStyle.primary, custom_id="modstats_details"
    )
    async def modstats_details(self, button, interaction):
        detailed_stats = await self.bot.db.fetch(
            """
            SELECT action, COUNT(*) AS count
            FROM history.moderation
            WHERE moderator_id = $1
            GROUP BY action
        """,
            self.moderator_id,
        )

        details_embed = Embed(title="Detailed Moderation Stats")
        for stat in detailed_stats:
            details_embed.add_field(
                name=stat["action"], value=str(stat["count"]), inline=True
            )

        await interaction.response.send_message(embed=details_embed)


class Moderation(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "Moderation commands to make things easier."

    @property
    def actions(self) -> dict[str, str]:
        return {
            "guild_update": "updated server",
            "channel_create": "created channel",
            "channel_update": "updated channel",
            "channel_delete": "deleted channel",
            "overwrite_create": "created channel permission in",
            "overwrite_update": "updated channel permission in",
            "overwrite_delete": "deleted channel permission in",
            "kick": "kicked member",
            "member_prune": "pruned members in",
            "ban": "banned member",
            "unban": "unbanned member",
            "member_update": "updated member",
            "member_role_update": "updated member roles for",
            "member_disconnect": "disconnected member",
            "member_move": "moved member",
            "bot_add": "added bot",
            "role_create": "created role",
            "role_update": "updated role",
            "role_delete": "deleted role",
            "invite_create": "created invite",
            "invite_update": "updated invite",
            "invite_delete": "deleted invite",
            "webhook_create": "created webhook",
            "webhook_update": "updated webhook",
            "webhook_delete": "deleted webhook",
            "emoji_create": "created emoji",
            "emoji_update": "updated emoji",
            "emoji_delete": "deleted emoji",
            "message_delete": "deleted message by",
            "message_bulk_delete": "bulk deleted messages in",
            "message_pin": "pinned message by",
            "message_unpin": "unpinned message by",
            "integration_create": "created integration",
            "integration_update": "updated integration",
            "integration_delete": "deleted integration",
            "sticker_create": "created sticker",
            "sticker_update": "updated sticker",
            "sticker_delete": "deleted sticker",
            "thread_create": "created thread",
            "thread_update": "updated thread",
            "thread_delete": "deleted thread",
        }

    async def reconfigure_settings(
        self,
        guild: Guild,
        channel: TextChannel | Thread,
        new_channel: TextChannel | Thread,
    ) -> List[str]:
        """
        Update server wide settings for a channel.
        """

        reconfigured: List[str] = []
        config_map = {
            "System Channel": "system_channel",
            "Public Updates Channel": "public_updates_channel",
            "Rules Channel": "rules_channel",
            "AFK Channel": "afk_channel",
        }
        for name, attr in config_map.items():
            value = getattr(channel.guild, attr, None)
            if value == channel:
                await guild.edit(**{attr: new_channel})  # type: ignore
                reconfigured.append(name)

        for table in (
            "logging",
            "gallery",
            "timer.message",
            "timer.purge",
            "sticky_message",
            "welcome_message",
            "goodbye_message",
            "boost_message",
            ("disboard.config", "last_channel_id"),
            "level.notification",
            "commands.disabled",
            "fortnite.rotation",
            "alerts.twitch",
            "feeds.tiktok",
            "feeds.pinterest",
            "feeds.reddit",
        ):
            table_name = table if isinstance(table, str) else table[0]
            column = "channel_id" if isinstance(table, str) else table[1]
            result = await self.bot.db.execute(
                f"""
                UPDATE {table_name}
                SET {column} = $2
                WHERE {column} = $1
                """,
                channel.id,
                new_channel.id,
            )
            if result != "UPDATE 0":
                pretty_name = (
                    table_name.replace("_", " ")
                    .replace(".", " ")
                    .title()
                    .replace("Feeds Youtube", "YouTube Notifications")
                    .replace("Alerts Twitch", "Twitch Notifications")
                    .replace("Feeds Twitter", "Twitter Notifications")
                    .replace("Feeds Tiktok", "TikTok Notifications")
                    .replace("Feeds Pinterest", "Pinterest Notifications")
                    .replace("Feeds Reddit", "Subreddit Notifications")
                    .replace("Feeds Twitter", "Twitter Notifications")
                )
                reconfigured.append(pretty_name)

        return reconfigured

    def hardban_key(self, guild: Guild) -> str:
        return xxh64_hexdigest(f"hardban:{guild.id}")

    def restore_key(self, guild: Guild, member: Member) -> str:
        return xxh64_hexdigest(f"roles:{guild.id}:{member.id}")

    def forcenick_key(self, guild: Guild, member: Member) -> str:
        return xxh64_hexdigest(f"forcenick:{guild.id}:{member.id}")

    # @Cog.listener()
    # async def on_message_delete(self, message: Message):
    #    if (
    #        not message.guild
    #        or not isinstance(message.channel, TextChannel)
    #        or not isinstance(message.author, Member)
    #        or message.author.guild_permissions.administrator
    #    ):
    #        return

    #     if not await self.bot.redis.ratelimited(f"deletion:{message.author.id}", 5, 30):
    #         return

    #     channel = message.channel

    #     overwrite = channel.overwrites_for(message.author)
    #     overwrite.view_channel = False
    #     await channel.set_permissions(
    #        message.author,
    #        overwrite=overwrite,
    #     )
    #     await channel.send(f"{message.author.mention} was purging")

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.bot:
            return

        role_ids = [r.id for r in member.roles if r.is_assignable()]
        if role_ids:
            key = self.restore_key(member.guild, member)
            await self.bot.redis.set(key, role_ids, ex=3600)

    @Cog.listener("on_member_join")
    async def restore_roles(self, member: Member):
        key = self.restore_key(member.guild, member)
        role_ids = cast(
            Optional[List[int]],
            await self.bot.redis.get(key),
        )
        if not role_ids:
            return

        roles = [
            role
            for role_id in role_ids
            if (role := member.guild.get_role(role_id)) is not None
            and role.is_assignable()
            and role not in member.roles
        ]
        if not roles:
            return

        record = await self.bot.db.fetchrow(
            """
            SELECT
                reassign_roles,
                reassign_ignore_ids
            FROM settings
            WHERE guild_id = $1
            """,
            member.guild.id,
        )
        if not record or not record["reassign_roles"]:
            return

        roles = [role for role in roles if role.id not in record["reassign_ignore_ids"]]
        if not roles:
            return

        await self.bot.redis.delete(key)
        with suppress(HTTPException):
            await member.add_roles(*roles, reason="Restoration of previous roles")
            log.info(
                "Restored %s for %s (%s) in %s (%s).",
                format(plural(len(roles)), "role"),
                member,
                member.id,
                member.guild,
                member.guild.id,
            )

    @Cog.listener("on_member_join")
    async def hardban_event(self, member: Member):
        key = self.hardban_key(member.guild)
        if not await self.bot.redis.sismember(key, str(member.id)):
            return

        with suppress(HTTPException):
            await member.ban(reason="User is hard banned")

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User):
        key = self.hardban_key(guild)
        if not await self.bot.redis.sismember(key, str(user.id)):
            return

        with suppress(HTTPException):
            await guild.ban(user, reason="User is hard banned")

    @Cog.listener("on_member_join")
    async def autokick_event(self, member: Member):

        check = await self.bot.db.fetchrow(
            "SELECT user_id FROM autokick WHERE user_id = $1 AND guild_id = $2",
            member.id,
            member.guild.id,
        )
        reason_row = await self.bot.db.fetchrow(
            "SELECT reason FROM autokick WHERE user_id = $1 AND guild_id = $2",
            member.id,
            member.guild.id,
        )
        reason = reason_row["reason"] if reason_row else "No reason provided"

        if check:
            await member.kick(reason=f"autokicked | {reason}")

    @Cog.listener("on_member_update")
    async def forcenick_event(self, before: Member, after: Member):
        key = self.forcenick_key(before.guild, before)
        log.debug("key gen: %s", key)

        nickname = cast(Optional[str], await self.bot.redis.get(key))
        log.debug("redis fetched: %s", nickname)

        if not nickname or (nickname == after.display_name):
            log.debug("There is no nickname to set or nickname is already correct")
            return

        if await self.bot.redis.ratelimited(f"nick:{key}", limit=8, timespan=15):
            log.warning("Rate limit exceeded for key: %s, deleting key.", key)
            await self.bot.redis.delete(key)
            return

        with suppress(HTTPException):
            log.info(
                "Setting nickname for %s to %r in %s (%s).",
                after,
                nickname,
                after.guild,
                after.guild.id,
            )
            await after.edit(nick=nickname, reason="Forced nickname")

    @Cog.listener("on_audit_log_entry_member_update")
    async def forcenick_audit(self, entry: AuditLogEntry):
        if (
            not entry.user
            or not entry.target
            or not entry.user.bot
            or entry.user == self.bot.user
        ):
            return

        elif not isinstance(entry.target, Member):
            return

        key = self.forcenick_key(entry.guild, entry.target)
        if hasattr(entry.after, "nick"):
            removed = await self.bot.redis.delete(key)
            if removed:
                log.warning(
                    "Safely removed forced nickname for %s (%s) in %s (%s).",
                    entry.target,
                    entry.target.id,
                    entry.guild,
                    entry.guild.id,
                )

    async def do_removal(
        self,
        ctx: Context,
        amount: int,
        predicate: Callable[[Message], bool] = lambda _: True,
        *,
        before: Optional[Message] = None,
        after: Optional[Message] = None,
    ) -> List[Message]:
        """
        A helper function to do bulk message removal.
        """

        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            raise CommandError("I don't have permission to delete messages!")

        if not before:
            before = ctx.message

        def check(message: Message) -> bool:
            if message.created_at < (utcnow() - timedelta(weeks=2)):
                return False

            elif message.pinned:
                return False

            return predicate(message)

        await quietly_delete(ctx.message)
        messages = await ctx.channel.purge(
            limit=amount,
            check=check,
            before=before,
            after=after,
        )
        if not messages:
            raise CommandError("No messages were found, try a larger search?")

        return messages

    @command(hidden=True)
    @check(
        lambda ctx: bool(
            ctx.guild
            and ctx.guild.id in [892675627373699072]
            or ctx.author.id in config.CLIENT.OWNER_IDS
        )
    )
    async def me(self, ctx: Context, amount: int = 100):
        """
        Clean up your messages.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(
                message.author == ctx.author
                or (
                    message.reference
                    and isinstance(message.reference.resolved, Message)
                    and message.reference.resolved.author == ctx.author
                )
            ),
        )

    @hybrid_command(aliases=["bc"])
    @has_permissions(manage_messages=True)
    async def cleanup(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove bot invocations and messages from bots.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: (
                message.author.bot
                or message.content.startswith(
                    (ctx.clean_prefix, ",", ";", ".", "!", "$")
                )
            ),
        )

    @group(
        aliases=["prune", "rm", "c"],
        invoke_without_command=True,
    )
    @max_concurrency(1, BucketType.channel)
    @has_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: Context,
        user: Optional[
            Annotated[
                Member,
                StrictMember,
            ]
            | Annotated[
                User,
                StrictUser,
            ]
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ],
    ):
        """
        Remove messages which meet a criteria.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: message.author == user if user else True,
        )

    @purge.command(
        name="embeds",
        aliases=["embed"],
    )
    @has_permissions(manage_messages=True)
    async def purge_embeds(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have embeds.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.embeds),
        )

    @purge.command(
        name="files",
        aliases=["file"],
    )
    @has_permissions(manage_messages=True)
    async def purge_files(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have files.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.attachments),
        )

    @purge.command(
        name="images",
        aliases=["image"],
    )
    @has_permissions(manage_messages=True)
    async def purge_images(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have images.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.attachments or message.embeds),
        )

    @purge.command(
        name="stickers",
        aliases=["sticker"],
    )
    @has_permissions(manage_messages=True)
    async def purge_stickers(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have stickers.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.stickers),
        )

    @purge.command(
        name="voice",
        aliases=["vm"],
    )
    @has_permissions(manage_messages=True)
    async def purge_voice(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove voice messages.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: any(
                attachment.waveform for attachment in message.attachments
            ),
        )

    @purge.command(
        name="system",
        aliases=["sys"],
    )
    @has_permissions(manage_messages=True)
    async def purge_system(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove system messages.
        """

        await self.do_removal(ctx, amount, lambda message: message.is_system())

    @purge.command(
        name="mentions",
        aliases=["mention"],
    )
    @has_permissions(manage_messages=True)
    async def purge_mentions(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have mentions.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.mentions),
        )

    @purge.command(
        name="emojis",
        aliases=[
            "emotes",
            "emoji",
            "emote",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_emojis(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have custom emojis.
        """

        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and bool(custom_emoji.search(message.content)),
        )

    @purge.command(
        name="invites",
        aliases=[
            "invite",
            "inv",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_invites(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have invites.
        """

        invite_link = re.compile(
            r"(?:https?://)?discord(?:\.gg|app\.com/invite)/[a-zA-Z0-9]+/?"
        )

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and bool(invite_link.search(message.content)),
        )

    @purge.command(
        name="links",
        aliases=["link"],
    )
    @has_permissions(manage_messages=True)
    async def purge_links(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have links.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content) and "http" in message.content.lower(),
        )

    @purge.command(
        name="contains",
        aliases=["contain"],
    )
    @has_permissions(manage_messages=True)
    async def purge_contains(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 2],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which contain a substring.

        The substring must be at least 3 characters long.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and substring.lower() in message.content.lower(),
        )

    @purge.command(
        name="startswith",
        aliases=[
            "prefix",
            "start",
            "sw",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_startswith(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 3],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which start with a substring.

        The substring must be at least 3 characters long.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and message.content.lower().startswith(substring.lower()),
        )

    @purge.command(
        name="endswith",
        aliases=[
            "suffix",
            "end",
            "ew",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_endswith(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 3],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which end with a substring.

        The substring must be at least 3 characters long.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and message.content.lower().endswith(substring.lower()),
        )

    @purge.command(
        name="humans",
        aliases=["human"],
    )
    @has_permissions(manage_messages=True)
    async def purge_humans(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are not from a bot.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: not message.author.bot,
        )

    @purge.command(
        name="bots",
        aliases=["bot"],
    )
    @has_permissions(manage_messages=True)
    async def purge_bots(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are from a bot.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: message.author.bot,
        )

    @purge.command(
        name="webhooks",
        aliases=["webhook"],
    )
    @has_permissions(manage_messages=True)
    async def purge_webhooks(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are from a webhook.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.webhook_id),
        )

    @purge.command(name="before")
    @has_permissions(manage_messages=True)
    async def purge_before(
        self,
        ctx: Context,
        message: Optional[Message],
    ):
        """
        Remove messages before a target message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        if message.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            300,
            before=message,
        )

    @purge.command(
        name="after",
        aliases=["upto", "up"],
    )
    @has_permissions(manage_messages=True)
    async def purge_after(
        self,
        ctx: Context,
        message: Optional[Message],
    ):
        """
        Remove messages after a target message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        if message.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            300,
            after=message,
        )

    @purge.command(name="between")
    @has_permissions(manage_messages=True)
    async def purge_between(
        self,
        ctx: Context,
        start: Message,
        finish: Message,
    ):
        """
        Remove messages between two messages.
        """

        if start.channel != ctx.channel or finish.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            2000,
            after=start,
            before=finish,
        )

    @purge.command(
        name="except",
        aliases=[
            "besides",
            "schizo",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_except(
        self,
        ctx: Context,
        member: Member,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 500,
    ):
        """
        Remove messages not sent by a member.
        """

        await self.do_removal(ctx, amount, lambda message: message.author != member)

    @purge.command(
        name="reactions",
        aliases=["reaction", "react"],
    )
    @has_permissions(manage_messages=True)
    @max_concurrency(1, BucketType.channel)
    async def purge_reactions(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove reactions from messages.

        This command is by no means quick,
        therefore it will take a while to complete.
        """

        total_removed: int = 0
        async with ctx.typing():
            async for message in ctx.channel.history(limit=amount, before=ctx.message):
                if len(message.reactions):
                    total_removed += sum(
                        reaction.count for reaction in message.reactions
                    )
                    await message.clear_reactions()

        return await ctx.approve(
            f"Successfully  removed {plural(total_removed, md='`'):reaction}"
        )

    async def do_mass_role(
        self,
        ctx: Context,
        role: Role,
        predicate: Callable[[Member], bool] = lambda _: True,
        *,
        action: Literal["add", "remove"] = "add",
        failure_message: Optional[str] = None,
    ) -> Message:
        """
        A helper method to mass add or remove a role from members.
        """

        if not failure_message:
            failure_message = (
                f"Everyone you can manage already has {role.mention}!"
                if action == "add"
                else f"Nobody you can manage has {role.mention}!"
            )

        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)

        members = []
        for member in ctx.guild.members:
            if not predicate(member):
                continue

            if (role in member.roles) == (action == "add"):
                continue

            try:
                await TouchableMember(allow_author=True).check(ctx, member)
            except BadArgument:
                continue

            members.append(member)

        if not members:
            return await ctx.warn(failure_message)

        word = "to" if action == "add" else "from"

        pending_message = await ctx.neutral(
            f"Starting to **{action}** {role.mention} "
            f"{word} {plural(len(members), md='`'):member}...",
            f"This will take around **{format_timespan(len(members))}**",
        )

        failed: List[Member] = []
        try:
            async with ctx.typing():
                for member in members:
                    try:
                        if action == "add":
                            await member.add_roles(
                                role,
                                reason=f"Mass role {action} by {ctx.author}",
                            )
                        else:
                            await member.remove_roles(
                                role,
                                reason=f"Mass role {action} by {ctx.author}",
                            )

                    except HTTPException:
                        failed.append(member)
                        if len(failed) >= 10:
                            break

        finally:
            await quietly_delete(pending_message)

        result = [
            f"{action.title()[:5]}ed {role.mention} {word} {plural(len(members) - len(failed), md='`'):member}"
        ]
        if failed:
            result.append(
                f"Failed {action[:5]}ing {role.mention} {word} {plural(len(failed), md='`'):member}: {', '.join(member.mention for member in failed)}"
            )

        return await ctx.approve(*result)

    @group(
        aliases=["r"],
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def role(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: GoodRole,
    ) -> Message:
        """
        Add or remove a role from a member.
        """

        if role in member.roles:
            return await ctx.invoke(self.role_remove, member=member, role=role)

        return await ctx.invoke(self.role_add, member=member, role=role)

    @role.command(
        name="add",
        aliases=["grant"],
    )
    @has_permissions(manage_roles=True)
    async def role_add(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: GoodRole,
    ) -> Message:
        """
        Add a role to a member.
        """

        if role in member.roles:
            return await ctx.warn(f"{member.mention} already has {role.mention}!")

        reason = f"Added by {ctx.author.name} ({ctx.author.id})"

        await member.add_roles(role, reason=reason)

        try:
            await ModConfig.sendlogs(self.bot, "role add", ctx.author, member, reason)  # type: ignore
        except:
            pass

        return await ctx.approve(f"Added {role.mention} to {member.mention}")

    @role.command(
        name="remove",
        aliases=["rm"],
    )
    @has_permissions(manage_roles=True)
    async def role_remove(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: GoodRole,
    ) -> Message:
        """
        Remove a role from a member.
        """

        if role not in member.roles:
            return await ctx.warn(f"{member.mention} doesn't have {role.mention}!")

        reason = f"Removed by {ctx.author.name} ({ctx.author.id})"
        await member.remove_roles(role, reason=reason)

        try:
            await ModConfig.sendlogs(self.bot, "role remove", ctx.author, member, reason)  # type: ignore
        except:
            pass

        return await ctx.approve(f"Removed {role.mention} from {member.mention}")

    @role.command(
        name="restore",
        aliases=["re"],
    )
    @has_permissions(manage_roles=True)
    async def role_restore(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> Message:
        """
        Restore a member's previous roles.
        """

        key = self.restore_key(ctx.guild, member)
        role_ids = cast(
            Optional[List[int]],
            await self.bot.redis.getdel(key),
        )
        if not role_ids:
            return await ctx.warn(f"No roles to restore for {member.mention}!")

        roles = [
            role
            for role_id in role_ids
            if (role := ctx.guild.get_role(role_id)) is not None
            and role.is_assignable()
            and role not in member.roles
            and await StrictRole().check(ctx, role)
        ]
        if not roles:
            return await ctx.warn(f"{member.mention} doesn't have any previous roles!")

        try:
            await ModConfig.sendlogs(
                self.bot, "role restore", ctx.author, member, "No reason provided"
            )  # type: ignore
        except:
            pass

        await member.add_roles(
            *roles,
            reason=f"Restoration of previous roles by {ctx.author.name} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"Restored {human_join([role.mention for role in roles], final='and')} to {member.mention}"
        )

    @role.command(
        name="create",
        aliases=["make"],
    )
    @has_permissions(manage_roles=True)
    async def role_create(
        self,
        ctx: Context,
        color: Optional[Color] = None,
        hoist: Optional[bool] = None,
        *,
        name: Range[str, 1, 100],
    ) -> Message:
        """
        Create a role.
        """

        if len(ctx.guild.roles) >= 250:
            return await ctx.warn("This server has too many roles! (`250`)")

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.role
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "role")
        ):
            await strip_roles(
                ctx.author,
                dangerous=True,
                reason="Antinuke role threshold reached",
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **role creation**!",
                "Your **administrative permissions** have been revoked",
            )

        reason = f"Created by {ctx.author.name} ({ctx.author.id})"
        role = await ctx.guild.create_role(
            name=name,
            color=color or Color.default(),
            hoist=hoist or False,
            reason=reason,
        )

        return await ctx.approve(f"Successfully created {role.mention}")

    @role.command(
        name="delete",
        aliases=["del"],
    )
    @has_permissions(manage_roles=True)
    async def role_delete(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Optional[Message]:
        """
        Delete a role.
        """

        if role.members:
            await ctx.prompt(
                f"{role.mention} has {plural(len(role.members), md='`'):member}, are you sure you want to delete it?",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.role
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "role")
        ):
            await strip_roles(
                ctx.author,
                dangerous=True,
                reason="Antinuke role threshold reached",
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **role deletion**!",
                "Your **administrative permissions** have been revoked",
            )

        await role.delete()
        return await ctx.check()

    @role.command(
        name="color",
        aliases=["colour"],
    )
    @has_permissions(manage_roles=True)
    async def role_color(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        color: Color,
    ) -> Message:
        """
        Change a role's color.
        """

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(color=color, reason=reason)
        return await ctx.approve(f"Changed {role.mention}'s color to `{color}`")

    @role.command(name="rename", aliases=["name"])
    @has_permissions(manage_roles=True)
    async def role_rename(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        name: Range[str, 1, 100],
    ) -> None:
        """
        Change a role's name.
        """

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(name=name, reason=reason)
        return await ctx.check()

    @role.command(name="hoist")
    @has_permissions(manage_roles=True)
    async def role_hoist(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
    ) -> Message:
        """
        Toggle if a role should appear in the sidebar.
        """

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(hoist=not role.hoist, reason=reason)
        return await ctx.approve(
            f"{role.mention} is {'now' if role.hoist else 'no longer'} hoisted"
        )

    @role.command(name="mentionable")
    @has_permissions(manage_roles=True)
    async def role_mentionable(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
    ) -> Message:
        """
        Toggle if a role should be mentionable.
        """

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(mentionable=not role.mentionable, reason=reason)
        return await ctx.approve(
            f"{role.mention} is {'now' if role.mentionable else 'no longer'} mentionable"
        )

    @role.command(name="icon")
    @has_permissions(manage_roles=True)
    async def role_icon(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        icon: PartialEmoji | PartialAttachment | str = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Change a role's icon.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.warn(
                "Role icons are only available for **level 2** boosted servers!"
            )

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        if isinstance(icon, str) and icon in ("none", "remove", "delete"):
            if not role.display_icon:
                return await ctx.warn(f"{role.mention} doesn't have an icon!")

            await role.edit(display_icon=None, reason=reason)
            return await ctx.approve(f"Removed {role.mention}'s icon")

        buffer: bytes | str
        processing: Optional[Message] = None

        if isinstance(icon, str):
            buffer = icon
        elif isinstance(icon, PartialEmoji):
            buffer = await icon.read()
            if icon.animated:
                processing = await ctx.neutral(
                    "Converting animated emoji to a static image..."
                )
                buffer = await convert_image(buffer, "png")  # type: ignore

        elif icon.is_gif():
            processing = await ctx.neutral("Converting GIF to a static image...")
            buffer = await convert_image(icon.buffer, "png")  # type: ignore

        elif not icon.is_image():
            return await ctx.warn("The attachment must be an image!")

        else:
            buffer = icon.buffer

        if processing:
            await processing.delete(delay=0.5)

        await role.edit(
            display_icon=buffer,
            reason=reason,
        )
        return await ctx.approve(
            f"Changed {role.mention}'s icon to "
            + (
                f"[**image**]({icon.url})"
                if isinstance(icon, PartialAttachment)
                else f"**{icon}**"
            )
        )

    @role.group(
        name="all",
        aliases=["everyone"],
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_all(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to everyone.
        """

        return await self.do_mass_role(ctx, role)

    @role_all.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_all_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from everyone.
        """

        return await self.do_mass_role(
            ctx,
            role,
            action="remove",
        )

    @role.group(
        name="humans",
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_humans(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to all humans.
        """

        return await self.do_mass_role(
            ctx,
            role,
            lambda member: not member.bot,
        )

    @role_humans.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_humans_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from all humans.
        """

        return await self.do_mass_role(
            ctx,
            role,
            lambda member: not member.bot,
            action="remove",
        )

    @role.group(
        name="bots",
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_bots(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to all bots.
        """

        return await self.do_mass_role(
            ctx,
            role,
            lambda member: member.bot,
        )

    @role_bots.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_bots_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from all bots.
        """

        return await self.do_mass_role(
            ctx,
            role,
            lambda member: member.bot,
            action="remove",
        )

    @role.group(
        name="has",
        aliases=["with", "in"],
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_has(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        assign_role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to everyone with a role.
        """

        return await self.do_mass_role(
            ctx,
            assign_role,
            lambda member: role in member.roles,
        )

    @role_has.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_has_remove(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        remove_role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from everyone with a role.
        """

        return await self.do_mass_role(
            ctx,
            remove_role,
            lambda member: role in member.roles,
            action="remove",
        )

    @hybrid_group(
        aliases=["lock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def lockdown(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Prevent members from sending messages.
        """

        channel = cast(TextChannel | Thread, channel or ctx.channel)
        lock_role = ctx.guild.get_role(ctx.settings.lock_role_id) or ctx.guild.default_role

        if (
            isinstance(channel, Thread)
            and channel.locked
            or isinstance(channel, TextChannel)
            and channel.overwrites_for(lock_role).send_messages is False 
        ):
            return await ctx.warn(f"{channel.mention} is already locked!")

        if isinstance(channel, Thread):
            await channel.edit(
                locked=True,
                reason=f"{ctx.author.name} / {reason}",
            )
        else:
            overwrite = channel.overwrites_for(lock_role)
            overwrite.send_messages = False
            await channel.set_permissions(
                lock_role,
                overwrite=overwrite,
                reason=f"{ctx.author.name} / {reason}",
            )

        return await ctx.approve(f"Successfully locked down {channel.mention}")

    @lockdown.command(name="all")
    @has_permissions(manage_roles=True)
    @max_concurrency(1, BucketType.guild)
    @cooldown(1, 30, BucketType.guild)
    async def lockdown_all(
        self,
        ctx: Context,
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Prevent members from sending messages in all channels.
        """

        if not ctx.settings.lock_ignore:
            await ctx.prompt(
                "Are you sure you want to lock **ALL** channels?",
                "You haven't ignored any important channels yet",
            )

        initial_message = await ctx.neutral("Locking down all channels...")
        async with ctx.typing():
            start = perf_counter()
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.settings.lock_role).send_messages
                    is False
                    or channel in ctx.settings.lock_ignore
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.settings.lock_role)
                overwrite.send_messages = False
                await channel.set_permissions(
                    ctx.settings.lock_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author.name} / {reason} (SERVER LOCKDOWN)",
                )

        return await ctx.approve(
            f"Successfully locked down {plural(len(ctx.guild.text_channels) - len(ctx.settings.lock_ignore), md='`'):channel} in `{perf_counter() - start:.2f}s`",
            patch=initial_message,
        )

    @lockdown.command(name="role")
    @has_permissions(manage_roles=True)
    async def lockdown_role(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
                allow_default=True,
            ),
        ],
    ) -> Message:
        """
        Set the role which will be locked from sending messages.
        """

        await ctx.settings.update(lock_role_id=role.id)
        return await ctx.approve(f"Now locking {role.mention} from sending messages")

    @lockdown.group(
        name="ignore",
        aliases=["exempt"],
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def lockdown_ignore(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> Message:
        """
        Ignore a channel from being unintentionally locked.
        """

        if channel in ctx.settings.lock_ignore:
            return await ctx.warn(f"{channel.mention} is already being ignored!")

        ctx.settings.lock_ignore_ids.append(channel.id)
        await ctx.settings.update()
        return await ctx.approve(f"Now ignoring {channel.mention} from lockdown")

    @lockdown_ignore.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_roles=True)
    async def lockdown_ignore_remove(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> Message:
        """
        Remove a channel from being ignored.
        """

        if channel not in ctx.settings.lock_ignore:
            return await ctx.warn(f"{channel.mention} isn't being ignored!")

        ctx.settings.lock_ignore_ids.remove(channel.id)
        await ctx.settings.update()
        return await ctx.approve(f"No longer ignoring {channel.mention} from lockdown")

    @lockdown_ignore.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_roles=True)
    async def lockdown_ignore_list(self, ctx: Context) -> Message:
        """
        View all channels being ignored.
        """

        if not ctx.settings.lock_ignore:
            return await ctx.warn("No channels are being ignored!")

        paginator = Paginator(
            ctx,
            entries=[
                f"{channel.mention} (`{channel.id}`)"
                for channel in ctx.settings.lock_ignore
            ],
            embed=Embed(title="Ignored Channels"),
        )
        return await paginator.start()

    @hybrid_group(
        aliases=["unlock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def unlockdown(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Allow members to send messages.
        """

        channel = cast(TextChannel | Thread, channel or ctx.channel)
        if not isinstance(channel, (TextChannel | Thread)):
            return await ctx.warn("You can only unlock text channels!")

        if (
            isinstance(channel, Thread)
            and not channel.locked
            or isinstance(channel, TextChannel)
            and channel.overwrites_for(ctx.settings.lock_role).send_messages is True
        ):
            return await ctx.warn(f"{channel.mention} is already unlocked!")

        if isinstance(channel, Thread):
            await channel.edit(
                locked=False,
                reason=f"{ctx.author.name} / {reason}",
            )
        else:
            overwrite = channel.overwrites_for(ctx.settings.lock_role)
            overwrite.send_messages = True
            await channel.set_permissions(
                ctx.settings.lock_role,
                overwrite=overwrite,
                reason=f"{ctx.author.name} / {reason}",
            )

        return await ctx.approve(f"Successfully unlocked {channel.mention}")

    @unlockdown.command(name="all")
    @has_permissions(manage_roles=True)
    @max_concurrency(1, BucketType.guild)
    @cooldown(1, 30, BucketType.guild)
    async def unlockdown_all(
        self,
        ctx: Context,
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Allow members to send messages in all channels.
        """

        if not ctx.settings.lock_ignore:
            await ctx.prompt(
                "Are you sure you want to unlock **ALL** channels?",
                "You haven't ignored any important channels yet",
            )

        initial_message = await ctx.neutral("Unlocking all channels...")
        async with ctx.typing():
            start = perf_counter()
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.settings.lock_role).send_messages is True
                    or channel in ctx.settings.lock_ignore
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.settings.lock_role)
                overwrite.send_messages = True
                await channel.set_permissions(
                    ctx.settings.lock_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author.name} / {reason} (SERVER UNLOCKDOWN)",
                )

        return await ctx.approve(
            f"Successfully unlocked {plural(len(ctx.guild.text_channels) - len(ctx.settings.lock_ignore), md='`'):channel} in `{perf_counter() - start:.2f}s`",
            patch=initial_message,
        )

    @hybrid_command(aliases=["private", "priv"])
    @has_permissions(manage_roles=True)
    async def hide(
        self,
        ctx: Context,
        channel: Optional[TextChannel | VoiceChannel],
        target: Optional[Member | Role],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Hide a channel from a member or role.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, (TextChannel, VoiceChannel)):
            return await ctx.warn("You can only hide text & voice channels!")

        target = target or ctx.settings.lock_role

        if channel.overwrites_for(target).read_messages is False:
            return await ctx.warn(
                f"{channel.mention} is already hidden for {target.mention}!"
                if target != ctx.settings.lock_role
                else f"{channel.mention} is already hidden!"
            )

        overwrite = channel.overwrites_for(target)
        overwrite.read_messages = False
        await channel.set_permissions(
            target,
            overwrite=overwrite,
            reason=f"{ctx.author.name} / {reason}",
        )

        return await ctx.approve(
            f"{channel.mention} is now hidden for {target.mention}"
            if target != ctx.settings.lock_role
            else f"{channel.mention} is now hidden"
        )

    @hybrid_command(aliases=["unhide", "public"])
    @has_permissions(manage_roles=True)
    async def reveal(
        self,
        ctx: Context,
        channel: Optional[TextChannel | VoiceChannel],
        target: Optional[Member | Role],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Reveal a channel to a member or role.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, (TextChannel, VoiceChannel)):
            return await ctx.warn("You can only hide text & voice channels!")

        target = target or ctx.settings.lock_role

        if channel.overwrites_for(target).read_messages is True:
            return await ctx.warn(
                f"{channel.mention} is already revealed for {target.mention}!"
                if target != ctx.settings.lock_role
                else f"{channel.mention} is already revealed!"
            )

        overwrite = channel.overwrites_for(target)
        overwrite.read_messages = True
        await channel.set_permissions(
            target,
            overwrite=overwrite,
            reason=f"{ctx.author.name} / {reason}",
        )

        return await ctx.approve(
            f"{channel.mention} is now revealed for {target.mention}"
            if target != ctx.settings.lock_role
            else f"{channel.mention} is now revealed"
        )

    @hybrid_group(
        aliases=["slowmo", "slow"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def slowmode(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        delay: timedelta = parameter(
            converter=Duration(
                min=timedelta(seconds=0),
                max=timedelta(hours=6),
            ),
        ),
    ) -> Message:
        """
        Set the slowmode for a channel.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only set the slowmode for text channels!")

        if channel.slowmode_delay == delay.seconds:
            return await ctx.warn(
                f"{channel.mention} already has a slowmode of **{precisedelta(delay)}**!"
            )

        await channel.edit(slowmode_delay=delay.seconds)
        return await ctx.approve(
            f"Set the slowmode for {channel.mention} to **{precisedelta(delay)}**"
        )

    @slowmode.command(
        name="disable",
        aliases=["off"],
    )
    @has_permissions(manage_channels=True)
    async def slowmode_disable(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Disable slowmode for a channel.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only set the slowmode for text channels!")

        if channel.slowmode_delay == 0:
            return await ctx.warn(f"{channel.mention} already has slowmode disabled!")

        await channel.edit(slowmode_delay=0)
        return await ctx.approve(f"Disabled slowmode for {channel.mention}")

    @hybrid_command(aliases=["naughty", "sfw"])
    @has_permissions(manage_channels=True)
    async def nsfw(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Mark a channel as NSFW or SFW.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only mark text channels as NSFW!")

        await channel.edit(
            nsfw=not channel.is_nsfw(),
            reason=f"Changed by {ctx.author.name} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"Marked {channel.mention} as **{'NSFW' if channel.is_nsfw() else 'SFW'}**"
        )

    @hybrid_group(invoke_without_command=True)
    @has_permissions(manage_channels=True)
    async def topic(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        *,
        text: Range[str, 1, 1024],
    ) -> Message:
        """
        Set a channel's topic.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only set the topic for text channels!")

        try:
            await channel.edit(
                topic=text, reason=f"Changed by {ctx.author.name} ({ctx.author.id})"
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The channel is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn(
                f"Failed to set the topic for {channel.mention}!", codeblock(exc.text)
            )

        return await ctx.approve(f"Set the topic for {channel.mention} to `{text}`")

    @topic.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def topic_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Remove a channel's topic.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only remove the topic for text channels!")

        if not channel.topic:
            return await ctx.warn(f"{channel.mention} doesn't have a topic!")

        try:
            await channel.edit(
                topic="", reason=f"Changed by {ctx.author.name} ({ctx.author.id})"
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The channel is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn(
                f"Failed to remove the topic for {channel.mention}!",
                codeblock(exc.text),
            )

        return await ctx.approve(f"Removed the topic for {channel.mention}")

    @hybrid_group(invoke_without_command=True)
    @has_permissions(manage_channels=True)
    async def drag(
        self,
        ctx: Context,
        *members: Annotated[
            Member,
            TouchableMember,
        ],
        channel: Optional[VoiceChannel | StageChannel] = None,
    ) -> Message:
        """
        Drag member(s) to the voice channel.
        """

        if not channel:
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.warn("You aren't in a voice channel!")

            channel = ctx.author.voice.channel

        moved: int = 0
        for member in members:
            if member in channel.members:
                continue

            with suppress(HTTPException):
                await member.move_to(
                    channel,
                    reason=f"{ctx.author} dragged member",
                )

                moved += 1

        return await ctx.approve(
            f"Moved `{moved}`/`{len(members)}` member{'s' if moved != 1 else ''} to {channel.mention}"
        )

    @drag.command(
        name="all",
        aliases=["everyone"],
    )
    @has_permissions(manage_channels=True)
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 10, BucketType.member)
    async def drag_all(
        self,
        ctx: Context,
        *,
        channel: VoiceChannel | StageChannel,
    ) -> Message:
        """
        Move all members to another voice channel.
        """

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.warn("You aren't in a voice channel!")

        elif ctx.author.voice.channel == channel:
            return await ctx.warn(f"You're already connected to {channel.mention}!")

        members = ctx.author.voice.channel.members
        moved = 0
        for member in members:
            with suppress(HTTPException):
                await member.move_to(
                    channel,
                    reason=f"{ctx.author} moved all members",
                )

                moved += 1

        return await ctx.approve(
            f"Moved `{moved}`/`{len(members)}` member{'s' if moved != 1 else ''} to {channel.mention}"
        )

    @hybrid_command(aliases=["mvall"])
    @has_permissions(manage_channels=True)
    async def moveall(
        self,
        ctx: Context,
        *,
        channel: VoiceChannel | StageChannel,
    ) -> Message:
        """
        Move all members to another voice channel.
        This is an alias for the `drag all` command.
        """

        return await ctx.invoke(self.drag_all, channel=channel)

    @hybrid_command(
        description="view a list of the newest members", aliases=["newmembers"]
    )
    async def newusers(
        self,
        ctx: Context,
        *,
        amount: Range[int, 5, 100] = 10,
    ) -> Message:
        """
        View a list of the newest members.

        This is useful to check for suspicious members.
        The amount parameter is limited to 100 results.
        """

        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)

        members = sorted(
            ctx.guild.members,
            key=lambda member: (member.joined_at or ctx.guild.created_at),
            reverse=True,
        )[:amount]

        paginator = Paginator(
            ctx,
            entries=[
                f"{member.mention} joined {format_dt(member.joined_at or ctx.guild.created_at, 'R')}"
                for member in members
            ],
            embed=Embed(title="New Members"),
        )
        return await paginator.start()

    @command()
    @has_permissions(view_audit_log=True)
    async def audit(
        self,
        ctx: Context,
        user: Optional[Member | User],
        action: Optional[str],
    ) -> Message:
        """
        View server audit log entries.
        """

        _action = (action or "").lower().replace(" ", "_")
        if action and not self.actions.get(_action):
            return await ctx.warn(f"`{action}` isn't a valid action!")

        entries: List[str] = []
        async for entry in ctx.guild.audit_logs(
            limit=100,
            user=user or MISSING,
            action=getattr(AuditLogAction, _action, MISSING),
        ):
            target: Optional[str] = None
            if entry.target:
                with suppress(TypeError):
                    if isinstance(entry.target, GuildChannel):
                        target = f"[#{entry.target}]({entry.target.jump_url})"
                    elif isinstance(entry.target, Role):
                        target = f"@{entry.target}"
                    elif isinstance(entry.target, Object):
                        target = f"`{entry.target.id}`"
                    else:
                        target = str(entry.target)

            entries.append(
                f"**{entry.user}** {self.actions.get(entry.action.name, entry.action.name.replace('_', ' '))} "
                + (f"**{target}**" if target and "`" not in target else target or "")
            )

        if not entries:
            return await ctx.warn(
                "No **audit log** entries found"
                + (f" for **{user}**" if user else "")
                + (f" with action **{action}**" if action else "")
                + "!"
            )

        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title="Audit Log"),
        )
        return await paginator.start()

    @hybrid_command(aliases=["boot", "k"])
    @has_permissions(kick_members=True)
    @max_concurrency(1, BucketType.member)
    async def kick(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Kick a member from the server.
        """

        if member.premium_since:
            await ctx.prompt(
                f"Are you sure you want to **kick** {member.mention}?",
                "They are currently boosting the server!",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.kick
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "kick")
        ):
            await strip_roles(
                ctx.author, dangerous=True, reason="Antinuke kick threshold reached"
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **kicks**!",
                "Your **administrative permissions** have been revoked",
            )

        try:
            await ModConfig.sendlogs(self.bot, "kick", ctx.author, member, reason)  # type: ignore
        except:
            pass
        await member.kick(reason=f"{ctx.author} / {reason}")
        if ctx.settings.invoke_kick:
            script = Script(
                ctx.settings.invoke_kick,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        return await ctx.check()

    @hybrid_command(
        aliases=["hb"],
        description="hardban a user",
        example="@x 1d bot owner",
    )
    @has_permissions(ban_members=True)
    async def hardban(
        self,
        ctx: Context,
        user: Member | User,
        history: Range[int, 0, 7] = 0,  
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Permanently ban a user from the server.

        Only the server owner is able to unban them.
        Re-running this command will remove the hard ban.
        """

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.warn(
                "You must be a **trusted administrator** to use this command!"
            )

        key = self.hardban_key(ctx.guild)
        if await self.bot.redis.srem(key, str(user.id)):
            with suppress(NotFound):
                await ctx.guild.unban(
                    user, reason=f"Hard ban removed by {ctx.author} ({ctx.author.id})"
                )

            try:
                await ModConfig.sendlogs(self.bot, "hardunban", ctx.author, user, reason)  # type: ignore
            except:
                pass
            return await ctx.approve(f"Hard ban removed for **{user}**")

        await self.bot.redis.sadd(key, str(user.id))
        await ModConfig.sendlogs(self.bot, "hardban", ctx.author, user, reason)  # type: ignore
        await ctx.guild.ban(
            user,
            delete_message_days=history, 
            reason=f"{ctx.author} / {reason}",
        )
        if ctx.settings.invoke_ban:
            script = Script(
                ctx.settings.invoke_ban,
                [
                    ctx.guild,
                    ctx.channel,
                    user,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        return await ctx.check()

    @hybrid_command(
        name="hardbanlist", aliases=["ls"], description="check hardban list"
    )
    @has_permissions(ban_members=True)
    async def hardban_list(self, ctx: Context) -> Message:
        """
        View all hard banned users.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.warn(
                "You must be a **trusted administrator** to use this command!"
            )

        key = self.hardban_key(ctx.guild)
        if not await self.bot.redis.exists(key):
            return await ctx.warn("No users are hard banned!")

        user_ids = await self.bot.redis.smembers(key)
        paginator = Paginator(
            ctx,
            entries=[
                f"**{self.bot.get_user(int(user_id)) or 'Unkown User'}** (`{user_id}`)"
                for user_id in user_ids
            ],
            embed=Embed(title="Hard Banned Users"),
        )
        return await paginator.start()

    @hybrid_command(
        aliases=["massb"],
        brief="ban_members",
        description="mass ban members from your server",
        example="@x 1d bot owner",
    )
    @has_permissions(ban_members=True)
    async def massban(
        self,
        ctx: Context,
        users: Greedy[Member | User],
        history: Optional[Range[int, 0, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban multiple users from the server.

        This command is limited to 150 users at a time.
        If you want to hard ban users, add `--hardban` to the reason.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.warn(
                "You must be a **trusted administrator** to use this command!"
            )

        elif not users:
            return await ctx.warn("You need to provide at least one user!")

        elif len(users) > 150:
            return await ctx.warn("You can only ban up to **150 users** at a time!")

        elif len(users) > 5:
            await ctx.prompt(f"Are you sure you want to **ban** `{len(users)}` users?")

        if "--hardban" in reason:
            reason = reason.replace("--hardban", "").strip()
            key = self.hardban_key(ctx.guild)
            await self.bot.redis.sadd(key, *[str(user.id) for user in users])

        async with ctx.typing():
            for user in users:
                if isinstance(user, Member):
                    await TouchableMember().check(ctx, user)

                await ctx.guild.ban(
                    user,
                    delete_message_days=history or 0,
                    reason=f"{ctx.author} / {reason} (MASS BAN)",
                )

        try:
            await ModConfig.sendlogs(self.bot, "massban", ctx.author, users, reason)  # type: ignore
        except:
            pass
        return await ctx.check()

    @hybrid_command(
        aliases=["deport", "b"],
        description="ban members from your server",
        usage="[member]",
        example="@x 1d bot owner",
    )
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.member)
    async def ban(
        self,
        ctx: Context,
        user: Member | User,
        history: Optional[Range[int, 0, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban a user from the server.
        """

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

            if user.premium_since:

                await ctx.prompt(
                    f"Are you sure you want to **ban** {user.mention}?",
                    "They are currently boosting the server!",
                )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config.ban
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "ban")
        ):
            await strip_roles(
                ctx.author, dangerous=True, reason="Antinuke ban threshold reached"
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **bans**!",
                "Your **administrative permissions** have been revoked",
            )

        await ctx.guild.ban(
            user,
            delete_message_seconds=history * 86400 if history is not None else 0,
            reason=f"{ctx.author} / {reason}",
        )

        if ctx.settings.invoke_ban is not None:
            script = Script(
                ctx.settings.invoke_ban,
                [
                    ctx.guild,
                    ctx.channel,
                    user,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)
        try:
            await ModConfig.sendlogs(self.bot, "ban", ctx.author, user, reason)  # type: ignore
        except:
            pass
        return await ctx.check()

    @hybrid_command(example="@x 1d bot owner")
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.member)
    async def softban(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        history: Optional[Range[int, 1, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban then unban a member from the server.

        This is used to cleanup messages from the member.
        """

        if member.premium_since:
            await ctx.prompt(
                f"Are you sure you want to **ban** {member.mention}?",
                "They are currently boosting the server!",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config.ban
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "ban")
        ):
            await strip_roles(
                ctx.author, dangerous=True, reason="Antinuke ban threshold reached"
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **bans**!",
                "Your **administrative permissions** have been revoked",
            )

        try:
            await ModConfig.sendlogs(self.bot, "ban", ctx.author, user, reason)  # type: ignore
        except:
            pass
        await ctx.guild.ban(
            member,
            delete_message_days=history or 0,
            reason=f"{ctx.author} / {reason}",
        )
        await ctx.guild.unban(member)
        if ctx.settings.invoke_ban:
            script = Script(
                ctx.settings.invoke_ban,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        return await ctx.check()

    @hybrid_group(
        example="@x 1d bot owner",
        aliases=["pardon", "unb"],
        invoke_without_command=True,
    )
    @has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: Context,
        user: User,
        *,
        reason: str = "No reason provided",
    ):
        """
        Unban a user from the server.
        """

        key = self.hardban_key(ctx.guild)
        if await self.bot.redis.sismember(key, str(user.id)):
            config = await Settings.fetch(self.bot, ctx.guild)
            if not config.is_trusted(ctx.author):
                return await ctx.warn(
                    "You must be a **trusted administrator** to unban hard banned users!"
                )

            await self.bot.redis.srem(key, str(user.id))

        try:
            await ctx.guild.unban(user, reason=f"{ctx.author} / {reason}")
        except NotFound:
            return await ctx.warn("That user is not banned!")
        try:
            await ModConfig.sendlogs(self.bot, "unban", ctx.author, user, reason)  # type: ignore
        except:
            pass

        if ctx.settings.invoke_unban:
            script = Script(
                ctx.settings.invoke_unban,
                [
                    ctx.guild,
                    ctx.channel,
                    user,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        return await ctx.check()

    @unban.command(name="all")
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.guild)
    async def unban_all(self, ctx: Context) -> Optional[Message]:
        """
        Unban all banned users from the server.
        """

        key = self.hardban_key(ctx.guild)
        hardban_ids = await self.bot.redis.smembers(key)

        users = [
            entry.user
            async for entry in ctx.guild.bans()
            if str(entry.user.id) not in hardban_ids
        ]
        if not users:
            return await ctx.warn("There are no banned users!")

        await ctx.prompt(
            f"Are you sure you want to unban {plural(users, md='`'):user}?",
        )

        async with ctx.typing():
            for user in users:
                with suppress(HTTPException):
                    await ctx.guild.unban(
                        user, reason=f"{ctx.author} ({ctx.author.id}) / UNBAN ALL"
                    )

        return await ctx.check()

    @hybrid_group(
        example="@x bot owner",
        aliases=["nick", "n"],
        invoke_without_command=True,
    )
    @has_permissions(manage_nicknames=True)
    async def nickname(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        nickname: Range[str, 1, 32],
    ) -> Optional[Message]:
        """
        Change a member's nickname.
        """

        key = self.forcenick_key(ctx.guild, member)
        if await self.bot.redis.exists(key):
            return await ctx.warn(
                f"{member.mention} has a forced nickname!",
                f"Use `{ctx.prefix}nickname remove {member}` to reset it",
            )

        try:
            await ModConfig.sendlogs(self.bot, "nickname", ctx.author, member, "No reason provided")  # type: ignore
        except:
            pass
        await member.edit(
            nick=nickname,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.check()

    @nickname.command(
        example="@x",
        name="remove",
        aliases=["reset", "rm"],
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_remove(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> None:
        """
        Reset a member's nickname.
        """

        key = self.forcenick_key(ctx.guild, member)
        await self.bot.redis.delete(key)

        await member.edit(
            nick=None,
            reason=f"{ctx.author} ({ctx.author.id})",
        )

        try:
            await ModConfig.sendlogs(self.bot, "nickname remove", ctx.author, member, "None")  # type: ignore
        except:
            pass
        return await ctx.check()

    @nickname.group(
        example="@x bot owner",
        name="force",
        aliases=["lock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_force(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        nickname: Range[str, 1, 32],
    ) -> None:
        """
        Force a member's nickname.
        """

        key = self.forcenick_key(ctx.guild, member)
        await self.bot.redis.set(key, nickname)

        await member.edit(
            nick=nickname,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        try:
            await ModConfig.sendlogs(self.bot, "forcenick", ctx.author, member, "No reason provided")  # type: ignore
        except:
            pass
        return await ctx.check()

    @nickname_force.command(
        name="cancel",
        aliases=["stop"],
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_force_cancel(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> Optional[Message]:
        """
        Cancel a member's forced nickname.
        """

        key = self.forcenick_key(ctx.guild, member)
        if not await self.bot.redis.delete(key):
            return await ctx.warn(f"{member.mention} doesn't have a forced nickname!")

        await member.edit(
            nick=None,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        try:
            await ModConfig.sendlogs(self.bot, "forcenick remove", ctx.author, member, "No reason provided")  # type: ignore
        except:
            pass
        return await ctx.check()

    @hybrid_group(
        example="@x 1d bot owner",
        aliases=[
            "mute",
            "tmo",
            "to",
        ],
        invoke_without_command=True,
    )
    @has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        duration: timedelta = parameter(
            converter=Duration(
                min=timedelta(seconds=60),
                max=timedelta(days=27),
            ),
            default=timedelta(minutes=5),
        ),
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Timeout a member from the server.
        """

        await member.timeout(
            duration,
            reason=f"{ctx.author} / {reason}",
        )
        if ctx.settings.invoke_timeout:
            script = Script(
                ctx.settings.invoke_timeout,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                    (format_timespan(duration), "duration"),
                    (format_dt(utcnow() + duration, "R"), "expires"),
                    (str(int((utcnow() + duration).timestamp())), "expires_timestamp"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        try:
            await ModConfig.sendlogs(
                self.bot, "timeout", ctx.author, member, reason
            )  # , duration=duratio
        except:
            pass
        return await ctx.check()

    @timeout.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(moderate_members=True)
    async def timeout_list(self, ctx: Context) -> Message:
        """
        View all timed out members.
        """

        members = list(
            filter(
                lambda member: member.is_timed_out(),
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.warn("No members are currently timed out!")

        paginator = Paginator(
            ctx,
            entries=[
                f"{member.mention} - expires {format_dt(member.timed_out_until or utcnow(), 'R')}"
                for member in sorted(
                    members,
                    key=lambda member: member.timed_out_until or utcnow(),
                )
            ],
            embed=Embed(
                title="Timed Out Members",
            ),
        )
        return await paginator.start()

    @hybrid_group(
        example="@x bot owner",
        aliases=[
            "unmute",
            "untmo",
            "unto",
            "utmo",
            "uto",
        ],
        invoke_without_command=True,
    )
    @has_permissions(moderate_members=True)
    async def untimeout(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Lift a member's timeout.
        """

        if not member.is_timed_out():
            return await ctx.warn("That member isn't timed out!")

        await member.timeout(
            None,
            reason=f"{ctx.author} / {reason}",
        )
        if ctx.settings.invoke_untimeout:
            script = Script(
                ctx.settings.invoke_untimeout,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                await script.send(ctx)

        try:
            await ModConfig.sendlogs(self.bot, "untimeout", ctx.author, member, reason)  # type: ignore
        except:
            pass
        return await ctx.check()

    @untimeout.command(name="all")
    @max_concurrency(1, BucketType.guild)
    async def untimeout_all(self, ctx: Context) -> Optional[Message]:
        """
        Lift all timeouts.
        """

        members = list(
            filter(
                lambda member: member.is_timed_out(),
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.warn("No members are currently timed out!")

        async with ctx.typing():
            for member in members:
                with suppress(HTTPException):
                    await member.timeout(
                        None,
                        reason=f"{ctx.author} ({ctx.author.id}) lifted all timeouts",
                    )
        return await ctx.check()

    @group(
        aliases=["emote", "e", "jumbo"],
        invoke_without_command=True,
    )
    @has_permissions(manage_expressions=True)
    async def emoji(self, ctx: Context, emoji: PartialEmoji | str) -> Message:
        """
        Various emoji management commands.
        """

        if isinstance(emoji, str):
            url, name = unicode_emoji(emoji)
        else:
            url, name = emoji.url, emoji.name

        response = await self.bot.session.get(url)
        if not response.ok:
            return await ctx.send_help(ctx.command)

        buffer = await response.read()
        _, suffix = url_to_mime(url)

        image, suffix = await enlarge_emoji(buffer, suffix[1:])
        if not image:
            return await ctx.warn("There was an issue downloading that emoji!")

        try:
            return await ctx.send(
                file=File(
                    BytesIO(image),
                    filename=f"{name}.{suffix}",
                ),
            )
        except HTTPException:
            return await ctx.warn("The enlarged emoji was too large to send!")

    @emoji.group(
        name="add",
        aliases=[
            "create",
            "upload",
            "steal",
        ],
        invoke_without_command=True,
    )
    @has_permissions(manage_expressions=True)
    async def emoji_add(
        self,
        ctx: Context,
        image: PartialEmoji | PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
        *,
        name: Optional[Range[str, 2, 32]],
    ) -> Optional[Message]:
        """
        Add an emoji to the server.
        """

        if not image.url:
            return await ctx.send_help(ctx.command)

        elif len(ctx.guild.emojis) == ctx.guild.emoji_limit:
            return await ctx.warn("The server is at the **maximum** amount of emojis!")

        try:
            await ctx.guild.create_custom_emoji(
                name=name
                or (image.name if isinstance(image, PartialEmoji) else image.filename),
                image=(
                    await image.read()
                    if isinstance(image, PartialEmoji)
                    else image.buffer
                ),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn("Failed to create the emoji!", codeblock(exc.text))

        return await ctx.check()

    @emoji_add.command(
        name="reactions",
        aliases=[
            "reaction",
            "reacts",
            "react",
        ],
    )
    @has_permissions(manage_expressions=True)
    async def emoji_add_reactions(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Message:
        """
        Add emojis from the reactions on a message.
        """

        message = message or ctx.replied_message
        if not message:
            async for _message in ctx.channel.history(limit=25, before=ctx.message):
                if _message.reactions:
                    message = _message
                    break

        if not message:
            return await ctx.send_help(ctx.command)

        elif not message.reactions:
            return await ctx.warn("That message doesn't have any reactions!")

        added_emojis: List[Emoji] = []
        async with ctx.typing():
            for reaction in message.reactions:
                if not reaction.is_custom_emoji():
                    continue

                emoji = reaction.emoji
                if isinstance(emoji, str):
                    continue

                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=await emoji.read(),
                        reason=f"Created by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.warn(
                        f"Ratelimited after {plural(added_emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        patch=ctx.response,
                    )

                except HTTPException:
                    if (
                        len(ctx.guild.emojis) + len(added_emojis)
                        > ctx.guild.emoji_limit
                    ):
                        return await ctx.warn(
                            "The maximum amount of emojis has been reached!",
                            patch=ctx.response,
                        )

                    break

                added_emojis.append(emoji)

        return await ctx.approve(
            f"Added {plural(added_emojis, md='`'):emoji} to the server"
            + (
                f" (`{len(message.reactions) - len(added_emojis)}` failed)"
                if len(added_emojis) < len(message.reactions)
                else ""
            )
        )

    @emoji_add.command(
        name="many",
        aliases=["bulk", "batch"],
    )
    @has_permissions(manage_expressions=True)
    async def emoji_add_many(
        self,
        ctx: Context,
        *emojis: PartialEmoji,
    ) -> Message:
        """
        Add multiple emojis to the server.
        """

        if not emojis:
            return await ctx.send_help(ctx.command)

        elif len(emojis) > 50:
            return await ctx.warn("You can only add up to **50 emojis** at a time!")

        elif len(ctx.guild.emojis) + len(emojis) > ctx.guild.emoji_limit:
            return await ctx.warn(
                "The server doesn't have enough space for all the emojis!",
            )

        added_emojis: List[Emoji] = []
        async with ctx.typing():
            for emoji in emojis:
                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=await emoji.read(),
                        reason=f"Created by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.warn(
                        f"Ratelimited after {plural(added_emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        patch=ctx.response,
                    )

                except HTTPException:
                    if len(ctx.guild.emojis) + len(emojis) > ctx.guild.emoji_limit:
                        return await ctx.warn(
                            "The maximum amount of emojis has been reached!",
                            patch=ctx.response,
                        )

                    break

                added_emojis.append(emoji)

        return await ctx.approve(
            f"Added {plural(added_emojis, md='`'):emoji} to the server"
            + (
                f" (`{len(emojis) - len(added_emojis)}` failed)"
                if len(added_emojis) < len(emojis)
                else ""
            )
        )

    @emoji.command(
        name="rename",
        aliases=["name"],
    )
    @has_permissions(manage_expressions=True)
    async def emoji_rename(
        self,
        ctx: Context,
        emoji: Emoji,
        *,
        name: str,
    ) -> Message:
        """
        Rename an existing emoji.
        """

        if emoji.guild_id != ctx.guild.id:
            return await ctx.warn("That emoji is not in this server!")

        elif len(name) < 2:
            return await ctx.warn(
                "The emoji name must be at least **2 characters** long!"
            )

        name = name[:32].replace(" ", "_")
        await emoji.edit(
            name=name,
            reason=f"Updated by {ctx.author} ({ctx.author.id})",
        )

        return await ctx.approve(f"Renamed the emoji to **{name}**")

    @emoji.command(
        name="delete",
        aliases=["remove", "del"],
    )
    @has_permissions(manage_expressions=True)
    async def emoji_delete(
        self,
        ctx: Context,
        emoji: Emoji,
    ) -> Optional[Message]:
        """
        Delete an existing emoji.
        """

        if emoji.guild_id != ctx.guild.id:
            return await ctx.warn("That emoji is not in this server!")

        await emoji.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
        return await ctx.check()

    @emoji.group(
        name="archive",
        aliases=["zip"],
        invoke_without_command=True,
    )
    @has_permissions(manage_expressions=True)
    @cooldown(1, 30, BucketType.guild)
    async def emoji_archive(self, ctx: Context) -> Message:
        """
        Archive all emojis into a zip file.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.warn(
                "The server must have at least Level 2 to use this command!"
            )

        await ctx.neutral("Starting the archival process...")

        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, emoji in enumerate(ctx.guild.emojis):
                    name = f"{emoji.name}.{emoji.animated and 'gif' or 'png'}"
                    if name in zip.namelist():
                        name = (
                            f"{emoji.name}_{index}.{emoji.animated and 'gif' or 'png'}"
                        )

                    __buffer = await emoji.read()

                    zip.writestr(name, __buffer)

            buffer.seek(0)

        if ctx.response:
            with suppress(HTTPException):
                await ctx.response.delete()

        return await ctx.send(
            file=File(
                buffer,
                filename=f"{ctx.guild.name}_emojis.zip",
            ),
        )

    @emoji_archive.command(
        name="restore",
        aliases=["load"],
    )
    @has_permissions(manage_expressions=True)
    @max_concurrency(1, BucketType.guild)
    async def emoji_archive_restore(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Restore emojis from an archive.
        """

        if not attachment.is_archive():
            return await ctx.warn("The attachment must be a zip archive!")

        await ctx.neutral("Starting the restoration process...")

        emojis: List[Emoji] = []
        buffer = BytesIO(attachment.buffer)
        with ZipFile(buffer, "r") as zip:
            if len(zip.namelist()) > (ctx.guild.emoji_limit - len(ctx.guild.emojis)):
                return await ctx.warn(
                    "The server doesn't have enough space for all the emojis in the archive!",
                    patch=ctx.response,
                )

            for name in zip.namelist():
                if not name.endswith((".png", ".gif")):
                    continue

                name = name[:-4]
                if get(ctx.guild.emojis, name=name):
                    continue

                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=name[:-4],
                        image=zip.read(name),
                        reason=f"Archive loaded by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.warn(
                        f"Ratelimited after {plural(emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        patch=ctx.response,
                    )

                except HTTPException:
                    if len(ctx.guild.emojis) == ctx.guild.emoji_limit:
                        return await ctx.warn(
                            "The maximum amount of emojis has been reached!",
                            patch=ctx.response,
                        )

                    break

                emojis.append(emoji)

        if ctx.response:
            await quietly_delete(ctx.response)

        return await ctx.approve(
            f"Restored {plural(emojis, md='`'):emoji} from [`{attachment.filename}`]({attachment.url})"
        )

    @group(name="sticker", invoke_without_command=True)
    @has_permissions(manage_expressions=True)
    async def sticker(self, ctx: Context) -> Message:
        """
        Various sticker related commands.
        """

        return await ctx.send_help(ctx.command)

    @sticker.command(
        name="add",
        aliases=["create", "upload"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_add(
        self,
        ctx: Context,
        name: Optional[Range[str, 2, 32]],
    ) -> Optional[Message]:
        """
        Add a sticker to the server.
        """

        if not ctx.message.stickers or not (sticker := ctx.message.stickers[0]):
            return await ctx.send_help(ctx.command)

        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.warn(
                "The server is at the **maximum** amount of stickers!"
            )

        sticker = await sticker.fetch()
        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        try:
            await ctx.guild.create_sticker(
                name=name or sticker.name,
                description=sticker.description,
                emoji=sticker.emoji,
                file=File(BytesIO(await sticker.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn("Failed to create the sticker!", codeblock(exc.text))

        return await ctx.check()

    @sticker.command(
        name="steal",
        aliases=["grab"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_steal(
        self,
        ctx: Context,
        name: Optional[Range[str, 2, 32]] = None,
    ) -> Optional[Message]:
        """
        Steal a sticker from a message.
        """

        message: Optional[Message] = ctx.replied_message
        if not message:
            async for _message in ctx.channel.history(limit=25, before=ctx.message):
                if _message.stickers:
                    message = _message
                    break

        if not message:
            return await ctx.warn(
                "I couldn't find a message with a sticker in the past 25 messages!"
            )

        if not message.stickers:
            return await ctx.warn("That message doesn't have any stickers!")

        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.warn(
                "The server is at the **maximum** amount of stickers!"
            )

        sticker = await message.stickers[0].fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id == ctx.guild.id:
            return await ctx.warn("That sticker is already in this server!")

        try:
            await ctx.guild.create_sticker(
                name=name or sticker.name,
                description=sticker.description,
                emoji=sticker.emoji,
                file=File(BytesIO(await sticker.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn("Failed to create the sticker!", codeblock(exc.text))

        return await ctx.check()

    @sticker.command(
        name="rename",
        aliases=["name"],
        example="new sticker"
    )
    @has_permissions(manage_expressions=True)
    async def sticker_rename(
        self,
        ctx: Context,
        *,
        name: str,
    ) -> Message:
        """
        Rename an existing sticker.
        """

        sticker = None
        
        if ctx.message.stickers:
            sticker = ctx.message.stickers[0]
        
        elif ctx.replied_message and ctx.replied_message.stickers:
            sticker = ctx.replied_message.stickers[0]

        if not sticker:
            return await ctx.send_help(ctx.command)

        sticker = await sticker.fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id != ctx.guild.id:
            return await ctx.warn("That sticker is not in this server!")

        elif len(name) < 2:
            return await ctx.warn(
                "The sticker name must be at least **2 characters** long!"
            )

        name = name[:32]
        await sticker.edit(
            name=name,
            reason=f"Updated by {ctx.author} ({ctx.author.id})",
        )

        return await ctx.approve(f"Renamed the sticker to **{name}**")

    @sticker.command(
        name="delete",
        aliases=["remove", "del"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_delete(
        self,
        ctx: Context,
    ) -> Optional[Message]:
        """
        Delete an existing sticker.
        """

        if not (sticker := ctx.message.stickers[0]):
            return await ctx.send_help(ctx.command)

        sticker = await sticker.fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id != ctx.guild.id:
            return await ctx.warn("That sticker is not in this server!")

        await sticker.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
        return await ctx.check()

    @sticker.command(
        name="archive",
        aliases=["zip"],
    )
    @has_permissions(manage_expressions=True)
    @cooldown(1, 30, BucketType.guild)
    async def sticker_archive(self, ctx: Context) -> Message:
        """
        Archive all stickers into a zip file.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.warn(
                "The server must have at least Level 2 to use this command!"
            )

        await ctx.neutral("Starting the archival process...")

        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, sticker in enumerate(ctx.guild.stickers):
                    name = f"{sticker.name}.{sticker.format}"
                    if name in zip.namelist():
                        name = f"{sticker.name}_{index}.{sticker.format}"

                    __buffer = await sticker.read()

                    zip.writestr(name, __buffer)

            buffer.seek(0)

        if ctx.response:
            with suppress(HTTPException):
                await ctx.response.delete()

        return await ctx.send(
            file=File(
                buffer,
                filename=f"{ctx.guild.name}_stickers.zip",
            ),
        )

    @group(
        name="set",
        aliases=["edit"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set(self, ctx: Context) -> Message:
        """
        Various server related commands.
        """

        return await ctx.send_help(ctx.command)

    @guild_set.command(
        name="name",
        aliases=["n"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_name(
        self,
        ctx: Context,
        *,
        name: Range[str, 1, 100],
    ) -> Optional[Message]:
        """
        Change the server's name.
        """

        try:
            await ctx.guild.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id})",
            )
        except HTTPException:
            return await ctx.warn("Failed to change the server's name!")

        return await ctx.check()

    @guild_set.command(
        name="icon",
        aliases=[
            "pfp",
            "i",
        ],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_icon(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's icon.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await ctx.guild.edit(
            icon=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.check()

    @guild_set.command(
        name="splash",
        aliases=["background", "bg"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_splash(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's splash.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await ctx.guild.edit(
            splash=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.check()

    @guild_set.command(
        name="banner",
        aliases=["b"],
    )
    @check(lambda ctx: bool(ctx.guild and ctx.guild.premium_tier >= 2))
    @has_permissions(manage_guild=True)
    async def guild_set_banner(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's banner.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await ctx.guild.edit(
            banner=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.check()

    @guild_set.group(
        name="system",
        aliases=["sys"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> None:
        """
        Change the server's system channel.
        """

        await ctx.guild.edit(
            system_channel=channel,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.check()

    @guild_set_system.group(
        name="welcome",
        aliases=["welc"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_welcome(self, ctx: Context) -> Message:
        """
        Toggle integrated welcome messages.
        """

        flags = ctx.guild.system_channel_flags
        flags.join_notifications = not flags.join_notifications

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"{'Now' if flags.join_notifications else 'No longer'} sending integrated **welcome messages**"
        )

    @guild_set_system_welcome.command(
        name="sticker",
        aliases=["stickers", "wave"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_welcome_sticker(self, ctx: Context) -> Message:
        """
        Toggle replying with a welcome sticker.
        """

        flags = ctx.guild.system_channel_flags
        flags.join_notification_replies = not flags.join_notification_replies

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"{'Now' if flags.join_notification_replies else 'No longer'} adding a **welcome sticker**"
        )

    @guild_set_system.command(
        name="boost",
        aliases=["boosts"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_boost(self, ctx: Context) -> Message:
        """
        Toggle integrated boost messages.
        """

        flags = ctx.guild.system_channel_flags
        flags.premium_subscriptions = not flags.premium_subscriptions

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"{'Now' if flags.premium_subscriptions else 'No longer'} sending integrated **boost messages**"
        )

    @guild_set.command(
        name="notifications",
        aliases=["notis", "noti"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_notifications(
        self,
        ctx: Context,
        option: Literal["all", "mentions"],
    ) -> None:
        """
        Change the server's default notification settings.
        """

        await ctx.guild.edit(
            default_notifications=(
                NotificationLevel.all_messages
                if option == "all"
                else NotificationLevel.only_mentions
            ),
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.check()

    @command()
    @has_permissions(manage_channels=True)
    async def nuke(self, ctx: Context) -> Message:
        """
        Clone the current channel.
        This action is irreversable and will delete the channel.
        """

        channel = ctx.channel
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only nuke text channels!")

        await ctx.prompt(
            "Are you sure you want to **nuke** this channel?",
            "This action is **irreversable** and will delete the channel!",
        )

        new_channel = await channel.clone(
            reason=f"Nuked by {ctx.author} ({ctx.author.id})",
        )
        reconfigured = await self.reconfigure_settings(ctx.guild, channel, new_channel)
        await asyncio.gather(
            *[
                new_channel.edit(position=channel.position),
                channel.delete(reason=f"Nuked by {ctx.author} ({ctx.author.id})"),
            ]
        )

        embed = Embed(
            title="Channel Nuked",
            description=f"This channel has been nuked by {ctx.author.mention}",
        )
        if reconfigured:
            embed.add_field(
                name="**Reconfigured Settings**",
                value="" + "\n".join(reconfigured),
            )

        await new_channel.send(embed=embed)
        return await new_channel.send("first")

    @command()
    @has_permissions(manage_messages=True)
    async def pin(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Optional[Message]:
        """
        Pin a specific message.
        """

        message = message or ctx.replied_message
        if not message:
            async for message in ctx.channel.history(limit=1, before=ctx.message):
                break

        if not message:
            return await ctx.send_help(ctx.command)

        elif message.guild != ctx.guild:
            return await ctx.warn("The message must be in this server!")

        elif message.pinned:
            return await ctx.warn(
                f"That [`message`]({message.jump_url}) is already pinned!"
            )

        await message.pin(reason=f"{ctx.author} ({ctx.author.id})")

    @command()
    @has_permissions(manage_messages=True)
    async def unpin(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Optional[Message]:
        """
        Unpin a specific message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        elif message.guild != ctx.guild:
            return await ctx.warn("The message must be in this server!")

        elif not message.pinned:
            return await ctx.warn(
                f"That [`message`]({message.jump_url}) is not pinned!"
            )

        await message.unpin(reason=f"{ctx.author} ({ctx.author.id})")
        return await ctx.check()

    @command()
    @has_permissions(mention_everyone=True)
    async def pingall(self, ctx: Context) -> Optional[Message]:
        """
        Ping everyone individually.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.warn(
                "You must be a **trusted administrator** to use this command!"
            )

        elif (
            ctx.author.id not in self.bot.owner_ids
            and await self.bot.redis.ratelimited(f"ping:{ctx.guild.id}", 1, 86400)
        ):
            return await ctx.warn("This command can only be used **once per day**!")

        await ctx.prompt(
            "Are you sure you want to ping **everyone**?",
            "Each member will be pinged individually",
        )
        await ctx.message.delete()

        mentions = " ".join(m.mention for m in ctx.guild.members if not m.bot)
        for chunk in wrap(mentions, 1950):
            await ctx.send(chunk, delete_after=0.5)

    @Mod.is_mod_configured()
    @hybrid_command()
    @has_permissions(manage_channels=True)
    async def jail(
    self, ctx: Context, user: Member, *, reason: str = "No reason provided"
):
        """Jail a member."""

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

        # Check if the member is already jailed
        check = await self.bot.db.fetchrow(
            """SELECT * FROM jail 
            WHERE guild_id = $1 
            AND user_id = $2""",
            ctx.guild.id,
            user.id,
        )

        if check:
            return await ctx.warn(f"**{user.mention}** is already jailed!")

        # Ensure reason is provided
        if reason is None:
            reason = "No reason provided"

        # Get roles to be stored, ignoring the booster role
        roles = [
            r.id for r in user.roles 
            if r.name != "@everyone" and r.is_assignable() and not r.is_premium_subscriber()
        ]

        sql_as_text = json.dumps(roles)

        # Insert into the jail database
        await self.bot.db.execute(
            """INSERT INTO jail (guild_id, user_id, roles) VALUES ($1, $2, $3)""",
            ctx.guild.id,
            user.id,
            sql_as_text,
        )

        # Get the jail role
        chec = await self.bot.db.fetchrow(
            """SELECT * FROM mod 
            WHERE guild_id = $1""",
            ctx.guild.id,
        )

        roleid = chec["role_id"]

        try:
            jail_role = ctx.guild.get_role(roleid)
            new_roles = [r for r in user.roles if not r.is_assignable()]  # Keep non-assignable roles
            new_roles.append(jail_role)  # Add jail role

            await user.edit(roles=new_roles, reason=f"Jailed by {ctx.author} - {reason}")

            await ctx.approve(f"**{user}** got jailed - {reason}")

            # Log the jailing action
            try:
                await ModConfig.sendlogs(self.bot, "jail", ctx.author, user, reason)  # type: ignore
            except Exception as e:
                await ctx.warn(f"Failed to send logs for jail action: {str(e)}")

            # Notify the user in the designated channel
            c = ctx.guild.get_channel(int(chec["jail_id"]))
            if c:
                await c.send(
                    f"{user.mention}, you have been jailed! Wait for a staff member to unjail you and check direct messages if you have received one!"
                )
        except Exception as e:
            return await ctx.warn(f"There was a problem jailing **{user.mention}**: {str(e)}")

    @hybrid_command()
    @has_permissions(manage_guild=True)
    async def setme(self, ctx: Context):
        """Enable the jail system in your server."""

        check = await self.bot.db.fetchrow(
            """SELECT * FROM mod 
            WHERE guild_id = $1""",
            ctx.guild.id,
        )

        if check:
            return await ctx.warn(
                "The jail system is **already** enabled in this server!"
            )

        await ctx.typing()

        role = await ctx.guild.create_role(name="evict-jail")

        for channel in ctx.guild.channels:
            await channel.set_permissions(role, view_channel=False)

        overwrite = {
            role: discord.PermissionOverwrite(view_channel=True),
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }

        over = {ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False)}

        category = await ctx.guild.create_category(name="evict mod", overwrites=over)
        text = await ctx.guild.create_text_channel(
            name="mod-logs", overwrites=over, category=category
        )
        jai = await ctx.guild.create_text_channel(
            name="jail", overwrites=overwrite, category=category
        )

        await self.bot.db.execute(
            """INSERT INTO mod 
            VALUES ($1,$2,$3,$4)""",
            ctx.guild.id,
            text.id,
            jai.id,
            role.id,
        )

        await self.bot.db.execute("INSERT INTO cases VALUES ($1,$2)", ctx.guild.id, 0)
        return await ctx.approve("I have **enabled** the jail system!")

    @Mod.is_mod_configured()
    @hybrid_command()
    @has_permissions(manage_channels=True)
    async def unjail(self, ctx: Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Unjail a member."""
        
        jail_entry = await self.bot.db.fetchrow(
            """SELECT * FROM jail 
            WHERE guild_id = $1 
            AND user_id = $2""",
            ctx.guild.id,
            member.id,
        )

        if not jail_entry:
            return await ctx.warn(f"**{member.mention}** is not jailed!")

        mod_config = await self.bot.db.fetchrow(
            """SELECT * FROM mod 
            WHERE guild_id = $1""",
            ctx.guild.id
        )

        jail_role_id = mod_config["role_id"]
        jailed_roles_json = jail_entry["roles"]
        jailed_roles = json.loads(jailed_roles_json)
        jail_role = ctx.guild.get_role(jail_role_id)

        if not jail_role:
            return await ctx.warn("Could not find the jail role!")

        # roles_to_add = [
        #     ctx.guild.get_role(role_id)
        #     for role_id in jailed_roles
        #     if ctx.guild.get_role(role_id) and ctx.guild.get_role(role_id).is_assignable()
        # ]

        # if roles_to_add:
        #     try:
        #         await member.edit(
        #             roles=roles_to_add,
        #             reason=f"Unjailed by {ctx.author} - {reason}"
        #         )
        #     except discord.HTTPException as e:
        #         return await ctx.warn(f"Failed to restore roles: {str(e)}")

        try:
            await member.remove_roles(jail_role, reason=f"Unjailed by {ctx.author}")
        except discord.HTTPException as e:
            return await ctx.warn(f"Failed to remove jail role: {str(e)}")

        await self.bot.db.execute(
            """
            DELETE FROM jail 
            WHERE user_id = $1 
            AND guild_id = $2
            """,
            member.id,
            ctx.guild.id
        )

        await ctx.approve(f"Unjailed **{member.mention}**")

        try:
            await ModConfig.sendlogs(self.bot, "unjail", ctx.author, member, reason)
        except discord.HTTPException as e:
            await ctx.warn(f"Failed to send logs: {str(e)}")
        except Exception as e:
            await ctx.warn(f"Failed to send logs for unjail action: {str(e)}")

        if jail_role:
            try:
                await member.remove_roles(jail_role)
            except Exception as e:
                await ctx.warn(f"Failed to remove jail role from **{member.mention}**: {str(e)}")

    @Mod.is_mod_configured()
    @hybrid_command()
    @has_permissions(manage_guild=True)
    async def unsetme(self, ctx: Context):
        """Disable the jail system in your server."""

        check = await self.bot.db.fetchrow(
            """
            SELECT * FROM mod 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not check:
            return await ctx.warn("The jail system is **not** enabled in this server!")

        view = ClearMod(ctx)
        view.message = await ctx.send(
            view=view,
            embed=Embed(
                description=f"> Are you sure you want to disable jail?",
            ),
        )

    @has_permissions(guild_owner=True)
    @group(invoke_without_command=True, aliases=["fp"])
    async def fakepermissions(self, ctx: Context) -> Message:
        """Restrict moderators to only use evict for moderation."""
        return await ctx.send_help(ctx.command)

    @has_permissions(guild_owner=True)
    @fakepermissions.command(
        name="grant",
        aliases=["add"],
    )
    async def fakepermissions_grant(
        self, ctx: Context, role: Role, *, permissions: str
    ):
        """
        Add one or more fake permissions to a role.
        > Can use multiple permissions at once if seperated by a comma (,).
        > https://docs.evict.bot/configuration/fakepermissions
        """

        permissions_list = [perm.strip().lower() for perm in permissions.split(",")]

        # invalid_permissions = [perm for perm in permissions_list if perm not in map(str.lower, fake_permissions)]
        # if invalid_permissions:
        #     invalid_permissions_str = "\n".join(f"• `{perm}`" for perm in invalid_permissions)
        #     return await ctx.warn(f"Invalid permissions. Valid permissions are:\n{invalid_permissions_str}")

        invalid_permissions = [
            perm
            for perm in permissions_list
            if perm not in map(str.lower, fake_permissions)
        ]
        if invalid_permissions:
            # invalid_permissions_str = "\n".join(f"• `{perm}`" for perm in invalid_permissions)
            # valid_permissions_str = "\n".join(f"`{perm}`" for perm in fake_permissions)
            return await ctx.warn(
                f"Invalid permissions. Run ``{ctx.clean_prefix}fakepermissions permissions`` to view the list of valid permisions."
            )

        check = await self.bot.db.fetchrow(
            f"""
            SELECT permission 
            FROM {FAKE_PERMISSIONS_TABLE} 
            WHERE guild_id = $1 AND role_id = $2
            """,
            ctx.guild.id,
            role.id,
        )

        if check:
            perms = json.loads(check[0])
            already_has = [perm for perm in permissions_list if perm in perms]
            if already_has:
                already_has_str = ", ".join(f"`{perm}`" for perm in already_has)
                return await ctx.warn(
                    f"{role.mention} already has the fake permissions: {already_has_str}!"
                )

            perms.extend(permissions_list)

            await self.bot.db.execute(
                f"""
                UPDATE {FAKE_PERMISSIONS_TABLE} 
                SET permission = $1 
                WHERE guild_id = $2 
                AND role_id = $3
                """,
                json.dumps(perms),
                ctx.guild.id,
                role.id,
            )
        else:
            await self.bot.db.execute(
                f"""
                INSERT INTO {FAKE_PERMISSIONS_TABLE} 
                (guild_id, role_id, permission) 
                VALUES ($1, $2, $3)
                """,
                ctx.guild.id,
                role.id,
                json.dumps(permissions_list),
            )

        added_permissions_str = ", ".join(f"`{perm}`" for perm in permissions_list)
        return await ctx.approve(
            f"Added {added_permissions_str} to the {role.mention}'s fake permissions!"
        )

    @has_permissions(guild_owner=True)
    @fakepermissions.command(
        name="revoke",
        aliases=["remove"],
    )
    async def fakepermissions_remove(
        self, ctx: Context, role: Role, *, permissions: str
    ):
        """
        Remove one or more fake permissions from a role's fake permissions.
        > Can use multiple permissions at once if seperated by a comma (,).
        > https://docs.evict.bot/configuration/fakepermissions
        """

        permissions_list = [perm.strip().lower() for perm in permissions.split(",")]

        invalid_permissions = [
            perm
            for perm in permissions_list
            if perm not in map(str.lower, fake_permissions)
        ]
        if invalid_permissions:
            invalid_permissions_str = "\n".join(
                f"• `{perm}`" for perm in invalid_permissions
            )
            return await ctx.warn(
                f"Invalid permissions. Valid permissions are:\n{invalid_permissions_str}"
            )

        check = await self.bot.db.fetchrow(
            f"""
            SELECT permission 
            FROM {FAKE_PERMISSIONS_TABLE} 
            WHERE guild_id = $1 
            AND role_id = $2""",
            ctx.guild.id,
            role.id,
        )

        if not check:
            return await ctx.warn(
                f"There are no fake permissions associated with {role.mention}!"
            )

        perms = json.loads(check[0])

        removed_permissions = []
        for permission in permissions_list:
            if permission in perms:
                perms.remove(permission)
                removed_permissions.append(permission)

        if not removed_permissions:
            return await ctx.warn(
                f"{role.mention} does not have any of the specified fake permissions!"
            )

        if perms:
            await self.bot.db.execute(
                f"""
                UPDATE {FAKE_PERMISSIONS_TABLE} 
                SET permission = $1 
                WHERE guild_id = $2 
                AND role_id = $3""",
                json.dumps(perms),
                ctx.guild.id,
                role.id,
            )
        else:
            await self.bot.db.execute(
                f"DELETE FROM {FAKE_PERMISSIONS_TABLE} WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )

        removed_permissions_str = ", ".join(f"`{perm}`" for perm in removed_permissions)
        return await ctx.approve(
            f"Removed {removed_permissions_str} from the {role.mention}'s fake permissions!"
        )

    @fakepermissions.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(guild_owner=True)
    async def fakepermission_list(self, ctx: Context) -> Message:
        """
        View all fake permissions for the server.
        """

        records = await self.bot.db.fetch(
            """
                SELECT role_id, permission
                FROM fake_permissions
                WHERE guild_id = $1
                """,
            ctx.guild.id,
        )

        fake_permissions = []
        for record in records:
            role = ctx.guild.get_role(record["role_id"])
            if role:
                permissions = json.loads(record["permission"])
                for perm in permissions:
                    fake_permissions.append(f"{role.mention} (`{perm}`)")

        if not fake_permissions:
            return await ctx.warn("No fake permissions exist for this server!")

        paginator = Paginator(
            ctx,
            entries=fake_permissions,
            embed=Embed(title="Fake Permissions"),
        )

        return await paginator.start()

    @has_permissions(guild_owner=True)
    @fakepermissions.command(name="permissions", aliases=["perms"])
    async def fakepermissions_permissions(self, ctx: Context):
        """
        Get every valid permission that can be used for fake permissions.
        """

        embed = Embed(title="Valid Fake Permissions")
        embed.description = "\n".join(f"• `{perm}`" for perm in fake_permissions)

        paginator = Paginator(ctx, entries=[embed], embed=embed)

        return await paginator.start()

    @command()
    @has_permissions(manage_guild=True)
    async def modhistory(self, ctx: Context, moderator: Member = None):
        """View moderation history for a moderator."""
        moderator = moderator or ctx.author

        cases = await self.bot.db.fetch(
            """
            SELECT * FROM history.moderation 
            WHERE moderator_id = $1 AND guild_id = $2 
            ORDER BY case_id DESC
            """,
            moderator.id,
            ctx.guild.id,
        )

        if not cases:
            return await ctx.warn(
                f"No moderation history found for {moderator.mention}"
            )

        entries = []
        for case in cases:
            try:
                user = await self.bot.fetch_user(case["user_id"])
                user_str = f"{user} (`{user.id}`)"
            except:
                user_str = f"Unknown User (`{case['user_id']}`)"

            duration_str = (
                f"\nDuration: {humanize.naturaldelta(case['duration'])}"
                if case["duration"]
                else ""
            )
            timestamp = f"<t:{int(case['timestamp'].timestamp())}:f>"

            entries.append(
                f"**Case #{case['case_id']}**\n"
                f"Action: {case['action']}\n"
                f"User: {user_str}\n"
                f"Date: {timestamp}\n"
                f"Reason: {case['reason']}"
                f"{duration_str}"
            )

        total_pages = len(entries) // 3 + (1 if len(entries) % 3 else 0)
        embed = Embed(title=f"Mod history for {moderator}")
        embed.set_footer(text=f"{len(cases)} total cases")

        paginator = Paginator(
            ctx,
            entries=entries,
            per_page=3,
            embed=embed,
            hide_index=True,
        )
        return await paginator.start()

    @command()
    @has_permissions(manage_guild=True)
    async def history(self, ctx: Context, user: Member | User = None):
        """View moderation history for a user."""
        user = user or ctx.author

        cases = await self.bot.db.fetch(
            """
            SELECT * FROM history.moderation 
            WHERE user_id = $1 AND guild_id = $2 
            ORDER BY case_id DESC
            """,
            user.id,
            ctx.guild.id,
        )

        if not cases:
            return await ctx.warn(f"No moderation history found for {user.mention}")

        entries = []
        for case in cases:
            try:
                mod = await self.bot.fetch_user(case["moderator_id"])
                mod_str = f"{mod} (`{mod.id}`)"
            except:
                mod_str = f"Unknown Moderator (`{case['moderator_id']}`)"

            duration_str = (
                f"\nDuration: {humanize.naturaldelta(case['duration'])}"
                if case["duration"]
                else ""
            )
            timestamp = f"<t:{int(case['timestamp'].timestamp())}:f>"

            entries.append(
                f"**Case #{case['case_id']}**\n"
                f"Action: {case['action']}\n"
                f"Moderator: {mod_str}\n"
                f"Date: {timestamp}\n"
                f"Reason: {case['reason']}"
                f"{duration_str}"
            )

        total_pages = len(entries) // 3 + (1 if len(entries) % 3 else 0)
        embed = Embed(title=f"History for {user}")
        embed.set_footer(text=f"{len(cases)} total cases")

        paginator = Paginator(
            ctx,
            entries=entries,
            per_page=3,
            embed=embed,
            hide_index=True,
        )
        return await paginator.start()

    @command(aliases=["pic", "pictureperms", "picture"], example="#general @x")
    @has_permissions(manage_roles=True)
    async def picperms(
        self, ctx: Context, channel: Optional[TextChannel], user: Member
    ):
        """Toggle picture permissions for a user."""

        if channel is None:
            channel = ctx.channel

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

        perms = channel.permissions_for(user)
        pic_perms = perms.attach_files and perms.embed_links

        if pic_perms:
            await channel.set_permissions(user, attach_files=False, embed_links=False)
            await ctx.approve(
                f"Revoked picture permissions from {user.mention} in {channel.mention}!"
            )

        else:
            await channel.set_permissions(user, attach_files=True, embed_links=True)
            await ctx.approve(
                f"Granted picture permissions to {user.mention} in {channel.mention}!"
            )

    @hybrid_group(name="verify")
    @has_permissions(manage_guild=True)
    async def verify(self, ctx: Context) -> Optional[Message]:
        """
        Manage server verification settings
        """
        if ctx.invoked_subcommand is None:
            embed = Embed(
                title="Verification Settings",
                description=(
                    "Use the following commands to manage verification:\n"
                    "`verify setup` - Interactive setup\n"
                    "`verify enable` - Enable verification\n"
                    "`verify disable` - Disable verification\n"
                    "`verify level` - Set verification level\n"
                    "`verify logs` - Set log channel"
                ),
            )
            return await ctx.send(embed=embed)

    @verify.command(name="setup")
    @has_permissions(manage_guild=True)
    async def verify_setup(self, ctx: Context) -> Optional[Message]:
        """Setup verification message"""

        class SetupView(discord.ui.View):
            def __init__(self, bot, ctx):
                super().__init__(timeout=300)
                self.bot = bot
                self.ctx = ctx
                self.level = None
                self.channel = None
                self.role = None

            @discord.ui.select(
                placeholder="Select Verification Level",
                options=[
                    discord.SelectOption(
                        label="Base", description="Basic verification methods"
                    ),
                    discord.SelectOption(
                        label="Medium", description="Enhanced verification methods"
                    ),
                ],
            )
            async def select_level(
                self, interaction: discord.Interaction, select: discord.ui.Select
            ):
                if interaction.user.id != self.ctx.author.id:
                    return await interaction.response.send_message(
                        "You cannot use this menu!", ephemeral=True
                    )

                self.level = select.values[0].lower()
                await interaction.response.defer()
                await interaction.message.edit(
                    embed=Embed(
                        title="Verification Setup",
                        description=f"Level: **{select.values[0]}**\nChannel: {self.channel.mention if self.channel else 'Not Set'}\nRole: {self.role.mention if self.role else 'Not Set'}",
                    )
                )

            @discord.ui.button(label="Set Channel", style=discord.ButtonStyle.blurple)
            async def set_channel(
                self, interaction: discord.Interaction, button: Button
            ):
                if interaction.user.id != self.ctx.author.id:
                    return await interaction.response.send_message(
                        "You cannot use this button!", ephemeral=True
                    )

                await interaction.response.send_message(
                    "Please mention the channel where the verification message should be sent",
                    ephemeral=True,
                )

                try:
                    message = await self.bot.wait_for(
                        "message",
                        timeout=30.0,
                        check=lambda m: m.author == self.ctx.author
                        and m.channel_mentions,
                    )
                    self.channel = message.channel_mentions[0]
                    await message.delete()

                    await interaction.message.edit(
                        embed=Embed(
                            title="Verification Setup",
                            description=f"Level: **{self.level}**\nChannel: {self.channel.mention if self.channel else 'Not Set'}\nRole: {self.role.mention if self.role else 'Not Set'}",
                        )
                    )
                except TimeoutError:
                    await interaction.followup.send("Setup timed out", ephemeral=True)

            @discord.ui.button(label="Set Role", style=discord.ButtonStyle.blurple)
            async def set_role(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id != self.ctx.author.id:
                    return await interaction.response.send_message(
                        "You cannot use this button!", ephemeral=True
                    )

                await interaction.response.send_message(
                    "Please mention the role to be given after verification",
                    ephemeral=True,
                )

                try:
                    message = await self.bot.wait_for(
                        "message",
                        timeout=30.0,
                        check=lambda m: m.author == self.ctx.author and m.role_mentions,
                    )
                    self.role = message.role_mentions[0]
                    await message.delete()

                    await interaction.message.edit(
                        embed=Embed(
                            title="Verification Setup",
                            description=f"Level: **{self.level}**\nChannel: {self.channel.mention if self.channel else 'Not Set'}\nRole: {self.role.mention if self.role else 'Not Set'}",
                        )
                    )
                except TimeoutError:
                    await interaction.followup.send("Setup timed out", ephemeral=True)

            @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
            async def save(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id != self.ctx.author.id:
                    return await interaction.response.send_message(
                        "You cannot use this button!", ephemeral=True
                    )

                if not all([self.level, self.channel, self.role]):
                    return await interaction.response.send_message(
                        "Please set all options before saving!", ephemeral=True
                    )

                await self.bot.db.execute(
                    """
                    INSERT INTO verification.settings 
                    (guild_id, level, verify_channel_id, verify_role_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET 
                        level = $2,
                        verify_channel_id = $3,
                        verify_role_id = $4
                    """,
                    self.ctx.guild.id,
                    self.level,
                    self.channel.id,
                    self.role.id,
                )

                verify_embed = Embed(
                    title="Server Verification",
                    description="Click the button below to verify your account",
                    color=0x2F3136,
                )

                class VerifyView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=None)

                    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green)
                    async def verify(
                        self,
                        verify_interaction: discord.Interaction,
                        verify_button: Button,
                    ):
                        try:
                            session_id = secrets.token_hex(8)

                            await interaction.client.db.execute(
                                """
                                INSERT INTO verification.sessions 
                                (session_id, guild_id, user_id, expires_at)
                                VALUES ($1, $2, $3, $4)
                                """,
                                session_id,
                                interaction.guild.id,
                                interaction.user.id,
                                datetime.now(timezone.utc) + timedelta(minutes=30),
                            )

                            verify_embed = Embed(
                                title="Verification",
                                description=f"Please verify yourself at:\nhttps://evict.bot/verify/{session_id}",
                                color=0x2F3136,
                            )
                            await verify_interaction.user.send(embed=verify_embed)
                            await verify_interaction.response.send_message(
                                "Check your DMs!", ephemeral=True
                            )

                        except discord.Forbidden:
                            await verify_interaction.response.send_message(
                                "I couldn't DM you! Please enable DMs from server members.",
                                ephemeral=True,
                            )

                await self.channel.send(embed=verify_embed, view=VerifyView())
                await interaction.response.send_message(
                    "Verification setup complete!", ephemeral=True
                )
                self.stop()

        embed = Embed(
            title="Verification Setup",
            description="Level: Not Set\nChannel: Not Set\nRole: Not Set",
        )
        return await ctx.send(embed=embed, view=SetupView(self.bot, ctx))

    @verify.command(name="enable")
    @has_permissions(manage_guild=True)
    async def verify_enable(self, ctx: Context) -> Optional[Message]:
        """
        Enable the verification system
        """
        await self.bot.db.execute(
            """
            INSERT INTO verification.settings (guild_id, enabled)
            VALUES ($1, true)
            ON CONFLICT (guild_id) 
            DO UPDATE SET enabled = true
            """,
            ctx.guild.id,
        )
        return await ctx.approve("Verification system enabled")

    @verify.command(name="disable")
    @has_permissions(manage_guild=True)
    async def verify_disable(self, ctx: Context) -> Optional[Message]:
        """
        Disable the verification system
        """
        await self.bot.db.execute(
            """
            INSERT INTO verification.settings (guild_id, enabled)
            VALUES ($1, false)
            ON CONFLICT (guild_id) 
            DO UPDATE SET enabled = false
            """,
            ctx.guild.id,
        )
        return await ctx.approve("Verification system disabled")

    @verify.command(name="logs")
    @has_permissions(manage_guild=True)
    async def verify_logs(
        self, ctx: Context, channel: TextChannel
    ) -> Optional[Message]:
        """
        Set the verification logs channel
        """
        await self.bot.db.execute(
            """
            INSERT INTO verification.settings (guild_id, log_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) 
            DO UPDATE SET log_channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )
        return await ctx.approve(f"Verification logs will be sent to {channel.mention}")

    async def create_verification_session(
        self, guild_id: int, user_id: int, ip_address: str = None
    ) -> str:
        """Create a new verification session"""
        session_id = "".join(random.choices(string.ascii_letters + string.digits, k=12))
        expires_at = datetime.now(datetime.UTC) + timedelta(minutes=30)

        await self.bot.db.execute(
            """
            INSERT INTO verification.sessions 
            (session_id, guild_id, user_id, ip_address, expires_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            session_id,
            guild_id,
            user_id,
            ip_address,
            expires_at,
        )

        return session_id

    async def log_verification_event(
        self,
        guild_id: int,
        user_id: int,
        session_id: str,
        event_type: str,
        details: dict = None,
    ) -> None:
        """Log a verification event"""
        await self.bot.db.execute(
            """
            INSERT INTO verification.logs 
            (guild_id, user_id, session_id, event_type, details)
            VALUES ($1, $2, $3, $4, $5)
            """,
            guild_id,
            user_id,
            session_id,
            event_type,
            details,
        )

        settings = await self.bot.db.fetchrow(
            "SELECT log_channel_id FROM verification.settings WHERE guild_id = $1",
            guild_id,
        )

        if settings and settings["log_channel_id"]:
            channel = self.bot.get_channel(settings["log_channel_id"])
            if channel:
                user = self.bot.get_user(user_id)
                embed = Embed(
                    title="Verification Event",
                    description=f"User: {user.mention if user else user_id}\nEvent: {event_type}",
                    timestamp=datetime.utcnow(),
                )
                if details:
                    for key, value in details.items():
                        embed.add_field(name=key, value=str(value))
                await channel.send(embed=embed)

    @group(name="warn", invoke_without_command=True)
    @has_permissions(moderate_members=True)
    @Mod.is_mod_configured()
    async def warn(
        self,
        ctx: Context,
        member: Member,
        *,
        reason: str = "No reason provided"
    ) -> Message:
        """Warn a member."""
        
        if isinstance(member, Member):
            await TouchableMember().check(ctx, member)
        
        warn_count = await self.bot.db.fetchval(
            """
            SELECT COUNT(*) FROM history.moderation 
            WHERE guild_id = $1 AND user_id = $2 AND action = 'warn'
            """,
            ctx.guild.id, member.id
        )
        
        action = await self.bot.db.fetchrow(
            """
            SELECT action, threshold, duration 
            FROM warn_actions 
            WHERE guild_id = $1 AND threshold = $2
            """,
            ctx.guild.id, warn_count + 1
        )

        await ModConfig.sendlogs(
            self.bot,
            "warn",
            ctx.author,
            member,
            reason
        )

        if not action:
            return await ctx.approve(f"Warned {member.mention}")

        duration = timedelta(seconds=action['duration']) if action['duration'] else None
        
        if action['action'] == 'timeout':
            await member.timeout(duration, reason="Warn threshold reached")
        elif action['action'] == 'jail':
            pass
        elif action['action'] == 'ban':
            await member.ban(reason="Warn threshold reached", delete_message_days=0)
        elif action['action'] == 'softban':
            await member.ban(reason="Warn threshold reached", delete_message_days=7)
            await member.unban(reason="Softban complete")
        elif action['action'] == 'kick':
            await member.kick(reason="Warn threshold reached")

        await ModConfig.sendlogs(
            self.bot,
            action['action'],
            ctx.guild.me,
            member,
            "Warn threshold reached",
            duration
        )

        return await ctx.approve(
            f"Warned {member.mention} (Threshold reached: {action['action']})"
        )

    @warn.group(name="action", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def warn_action(self, ctx: Context) -> Message:
        """Manage automated warn actions."""
        return await ctx.send_help(ctx.command)

    @warn_action.command(name="add")
    @has_permissions(manage_guild=True)
    async def warn_action_add(
        self,
        ctx: Context,
        action: str,
        *,
        flags: WarnActionFlags
    ) -> Message:
        """Add an automated action for warn thresholds."""
        
        valid_actions = ["timeout", "jail", "ban", "softban", "kick"]
        action = action.lower()
        
        if action not in valid_actions:
            return await ctx.warn(
                f"Invalid action. Valid actions are: {', '.join(valid_actions)}"
            )
        
        await self.bot.db.execute(
            """
            INSERT INTO warn_actions (guild_id, threshold, action, duration)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, threshold) 
            DO UPDATE SET action = $3, duration = $4
            """,
            ctx.guild.id, flags.threshold, action, 
            int(flags.duration.total_seconds()) if flags.duration else None
        )

        return await ctx.approve(
            f"Set warn threshold {flags.threshold} to {action}" +
            (f" with duration {humanize.naturaldelta(flags.duration)}" if flags.duration else "")
        )

    @warn_action.command(name="remove")
    @has_permissions(manage_guild=True)
    async def warn_action_remove(
        self,
        ctx: Context,
        threshold: int
    ) -> Message:
        """Remove an automated action for a warn threshold."""
        
        deleted = await self.bot.db.execute(
            """
            DELETE FROM warn_actions 
            WHERE guild_id = $1 AND threshold = $2
            """,
            ctx.guild.id, threshold
        )
        
        if deleted == "DELETE 0":
            return await ctx.warn(f"No action configured for threshold {threshold}")
        
        return await ctx.approve(f"Removed action for threshold {threshold}")

    @warn_action.command(name="list")
    @has_permissions(manage_guild=True)
    async def warn_action_list(self, ctx: Context) -> Message:
        """List all configured warn actions."""
        
        actions = await self.bot.db.fetch(
            """
            SELECT threshold, action, duration 
            FROM warn_actions 
            WHERE guild_id = $1 
            ORDER BY threshold
            """,
            ctx.guild.id
        )
        
        if not actions:
            return await ctx.warn("No warn actions configured")

        embed = Embed(title="Warn Actions")
        
        for action in actions:
            duration = timedelta(seconds=action['duration']) if action['duration'] else None
            embed.add_field(
                name=f"Threshold: {action['threshold']}",
                value=f"Action: {action['action']}\n" +
                      (f"Duration: {humanize.naturaldelta(duration)}" if duration else ""),
                inline=True
            )

        return await ctx.send(embed=embed)

    @warn.command(name="remove", aliases=["delete", "del"])
    @has_permissions(moderate_members=True)
    async def warn_remove(
        self,
        ctx: Context,
        case_id: Range[int, 1, None],
        *,
        reason: str = "No reason provided"
    ) -> Message:
        """Remove a warning by case ID."""
        
        warn = await self.bot.db.fetchrow(
            """
            DELETE FROM history.moderation 
            WHERE guild_id = $1 AND case_id = $2 AND action = 'warn'
            RETURNING user_id
            """,
            ctx.guild.id, case_id
        )
        
        if not warn:
            return await ctx.warn(f"No warning found with case ID #{case_id}")
            
        try:
            user = await self.bot.fetch_user(warn['user_id'])
            user_text = f"{user.mention} (`{user.id}`)"
        except:
            user_text = f"`{warn['user_id']}`"

        await ModConfig.sendlogs(
            self.bot,
            "warn remove",
            ctx.author,
            user,
            f"#{case_id} removed. {reason}"
        )

        return await ctx.approve(f"Removed warning case #{case_id} from {user_text}")        
        
    # def _hash_message(self, content: str) -> str:
    #     """Create a hash of the message content for efficient comparison"""
    #     return hashlib.md5(content.lower().encode()).hexdigest()
        
    # async def _is_exempt(self, guild_id: int, user_id: int, channel_id: int) -> bool:
    #     """Check if user/channel is exempt from filter"""
    #     return await self.bot.db.fetchval(
    #         """
    #         SELECT EXISTS(
    #             SELECT 1 FROM spam.exempt
    #             WHERE guild_id = $1 
    #             AND (
    #                 (type = 'user' AND entity_id = $2) OR
    #                 (type = 'channel' AND entity_id = $3)
    #             )
    #         )
    #         """,
    #         guild_id, user_id, channel_id
    #     )
        
    # @group(name="spam", invoke_without_command=True)
    # @has_permissions(manage_messages=True)
    # async def spam(self, ctx):
    #     """Manage spam message filter"""
    #     await ctx.send_help(ctx.command)
        
    # @spam.command(name="toggle")
    # @has_permissions(manage_messages=True)
    # async def spam_toggle(self, ctx):
    #     """Toggle spam message filter"""
    #     status = await self.bot.db.fetchval(
    #         """
    #         INSERT INTO spam.config (guild_id, enabled)
    #         VALUES ($1, true)
    #         ON CONFLICT (guild_id) DO UPDATE
    #         SET enabled = NOT spam.config.enabled
    #         RETURNING enabled
    #         """,
    #         ctx.guild.id
    #     )
        
    #     await ctx.approve(f"Spam filter {'enabled' if status else 'disabled'}")
        
    # @spam.group(name="config")
    # @has_permissions(manage_messages=True)
    # async def spam_config(self, ctx):
    #     """Configure spam filter settings"""
    #     if ctx.invoked_subcommand is None:
    #         await ctx.send_help(ctx.command)
            
    # @spam_config.command(name="limit")
    # async def spam_config_limit(self, ctx, limit: int):
    #     """Set message spam limit"""
    #     if limit < 2:
    #         return await ctx.warn("Limit must be at least 2")
            
    #     await self.bot.db.execute(
    #         """
    #         INSERT INTO spam.config (guild_id, threshold)
    #         VALUES ($1, $2)
    #         ON CONFLICT (guild_id) DO UPDATE
    #         SET threshold = $2
    #         """,
    #         ctx.guild.id, limit
    #     )
        
    #     await ctx.approve(f"Spam limit set to {limit}")
        
    # @spam_config.command(name="timeout")
    # async def spam_config_timeout(self, ctx, duration: str):
    #     """Set timeout duration for spam offenders"""
    #     try:
    #         seconds = int(duration[:-1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[duration[-1]]
    #     except:
    #         return await ctx.warn("Invalid duration format. Use s/m/h/d (e.g. 1d)")
            
    #     await self.bot.db.execute(
    #         """
    #         INSERT INTO spam.config (guild_id, timeout_duration)
    #         VALUES ($1, $2)
    #         ON CONFLICT (guild_id) DO UPDATE
    #         SET timeout_duration = $2
    #         """,
    #         ctx.guild.id, seconds
    #     )
        
    #     await ctx.approve(f"Timeout duration set to {duration}")
        
    # @spam.group(name="exempt")
    # @has_permissions(manage_messages=True)
    # async def spam_exempt(self, ctx):
    #     """Manage filter exemptions"""
    #     if ctx.invoked_subcommand is None:
    #         await ctx.send_help(ctx.command)
            
    # @spam_exempt.command(name="add")
    # async def spam_exempt_add(
    #     self, 
    #     ctx, 
    #     entity: Union[Member, TextChannel, Role]
    # ):
    #     """Add user/channel/role exemption"""
    #     entity_type = {
    #         Member: "user",
    #         TextChannel: "channel",
    #         Role: "role"
    #     }[type(entity)]
        
    #     await self.bot.db.execute(
    #         """
    #         INSERT INTO spam.exempt (guild_id, entity_id, type)
    #         VALUES ($1, $2, $3)
    #         ON CONFLICT DO NOTHING
    #         """,
    #         ctx.guild.id, entity.id, entity_type
    #     )
        
    #     await ctx.approve(f"Added {entity_type} {entity.mention} to exemptions")
        
    # @spam_exempt.command(name="remove")
    # async def spam_exempt_remove(
    #     self,
    #     ctx,
    #     entity: Union[Member, TextChannel, Role]
    # ):
    #     """Remove user/channel/role exemption"""
    #     entity_type = {
    #         Member: "user",
    #         TextChannel: "channel", 
    #         Role: "role"
    #     }[type(entity)]
        
    #     await self.bot.db.execute(
    #         """
    #         DELETE FROM spam.exempt
    #         WHERE guild_id = $1 
    #         AND entity_id = $2
    #         AND type = $3
    #         """,
    #         ctx.guild.id, entity.id, entity_type
    #     )
        
    #     await ctx.approve(f"Removed {entity_type} {entity.mention} from exemptions")
        
    # @spam_exempt.command(name="list")
    # async def spam_exempt_list(self, ctx):
    #     """List all exemptions"""
    #     exemptions = await self.bot.db.fetch(
    #         """
    #         SELECT entity_id, type
    #         FROM spam.exempt
    #         WHERE guild_id = $1
    #         """,
    #         ctx.guild.id
    #     )
        
    #     if not exemptions:
    #         return await ctx.warn("No exemptions configured")
            
    #     embed = discord.Embed(title="Filter Exemptions")
        
    #     for type_name in ("user", "role", "channel"):
    #         entities = [
    #             ctx.guild.get_member(r['entity_id'])
    #             if type_name == "user"
    #             else ctx.guild.get_role(r['entity_id'])
    #             if type_name == "role"
    #             else ctx.guild.get_channel(r['entity_id'])
    #             for r in exemptions
    #             if r['type'] == type_name
    #         ]
            
    #         if entities:
    #             embed.add_field(
    #                 name=f"{type_name.title()}s",
    #                 value="\n".join(e.mention for e in entities if e),
    #                 inline=False
    #             )
                
    #     await ctx.send(embed=embed)
        
    # @Cog.listener()
    # async def on_message(self, message: discord.Message):
    #     if (
    #         message.author.bot
    #         or not message.guild
    #         or not message.content
    #         or len(message.content) < 5
    #     ):
    #         return
            
    #     config = await self.bot.db.fetchrow(
    #         """
    #         SELECT enabled, threshold, timeout_duration
    #         FROM spam.config
    #         WHERE guild_id = $1
    #         """,
    #         message.guild.id
    #     )
        
    #     if not config or not config['enabled']:
    #         return
            
    #     if await self._is_exempt(
    #         message.guild.id,
    #         message.author.id,
    #         message.channel.id
    #     ):
    #         return
            
    #     msg_hash = self._hash_message(message.content)
        
    #     count = await self.bot.db.fetchval(
    #         """
    #         INSERT INTO spam.messages (guild_id, user_id, message_hash)
    #         VALUES ($1, $2, $3)
    #         ON CONFLICT (guild_id, user_id, message_hash)
    #         DO UPDATE SET count = spam.messages.count + 1
    #         RETURNING count
    #         """,
    #         message.guild.id,
    #         message.author.id,
    #         msg_hash
    #     )
        
    #     if count >= config['threshold']:
    #         try:
    #             await message.delete()
                
    #             await ModConfig.sendlogs(
    #                 self.bot,
    #                 "spam filter",
    #                 message.guild.me, 
    #                 message.author,  
    #                 f"Repeated message {count} times: {message.content[:500]}"
    #             )
                
    #             if config['timeout_duration']:
    #                 duration = timedelta(seconds=config['timeout_duration'])
    #                 await message.author.timeout(
    #                     duration,
    #                     reason="Spam message filter"
    #                 )
                    
    #                 await ModConfig.sendlogs(
    #                     self.bot,
    #                     "timeout",
    #                     message.guild.me,
    #                     message.author,
    #                     "Automatic timeout from spam filter",
    #                 )
                    
    #         except discord.HTTPException:
    #             pass