from __future__ import annotations

import re
import datetime
from typing import cast, Optional

from managers.paginator import Paginator
from cashews import cache
from discord import AuditLogEntry, Message, TextChannel, Embed, Interaction, Member
from discord.ext.commands import (
    group,
    has_permissions,
    Cog,
    command,
)

from config import CLIENT
from main import Evict
from asyncpg import UniqueViolationError
from core.client.context import Context
from tools.formatter import vowel
from tools.parser import Script

from .extended import Extended
from tools.conversion.embed1 import EmbedScript
from managers.patches.permissions import donator

import boto3
import time
from logging import getLogger

log = getLogger("evict/mod")

poj_cache = {}


class Config(Extended, Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "AntiNuke, image-only, boosterroles, vanityroles, etc..."

    @group(invoke_without_command=True)
    async def prefix(self, ctx: Context) -> Message:
        """
        View the current server prefixes.
        """
        guild = await self.bot.db.fetch(
            """
            SELECT DISTINCT prefix 
            FROM prefix 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
    
        prefix = [record['prefix'] for record in guild]
        await ctx.neutral(f"The servers prefix is {', '.join(f'`{p}`' for p in prefix)}")

    @prefix.command(name="set", example=";")
    @has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: Context, prefix: str) -> Message:
        """
        Set the server prefix.
        """
        if len(prefix) > 3:
            return await ctx.warn("Uh oh! The prefix is too long")
        
        check = await self.bot.db.fetchrow(
            "SELECT * FROM prefix WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if check:
            await self.bot.db.execute(
                "UPDATE prefix SET prefix = $1 WHERE guild_id = $2",
                prefix,
                ctx.guild.id
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO prefix (guild_id, prefix) VALUES ($1, $2)",
                ctx.guild.id,
                prefix
            )
        
        await self.bot.redis.delete(f"prefix:{ctx.guild.id}")
        
        return await ctx.approve(f"Guild prefix changed to `{prefix}`")

    @command(example="x")
    async def selfprefix(self, ctx: Context, prefix: str):
        """
        Set a custom prefix for yourself.
        """
        if len(prefix) > 3 and prefix.lower() != "none":
            return await ctx.warn("Uh oh! The prefix is too long")

        if prefix.lower() == "none":

            check = await self.bot.db.fetchrow(
                """
                SELECT * FROM 
                selfprefix 
                WHERE user_id = {}
                """.format
                (ctx.author.id)
            )
            if check is not None:

                await self.bot.db.execute(
                    """
                    DELETE FROM selfprefix 
                    WHERE user_id = {}
                    """.format
                    (ctx.author.id)
                )
                return await ctx.approve("I have **removed** your self prefix.")

            elif check is None:
                return await ctx.warn("You **don't** have a self prefix.")
        else:
            result = await self.bot.db.fetchrow(
                """
                SELECT * FROM 
                selfprefix WHERE 
                user_id = {}
                """.format
                (ctx.author.id)
            )
            if result is not None:
                await self.bot.db.execute(
                    """
                    UPDATE selfprefix 
                    SET prefix = $1 
                    WHERE user_id = $2
                    """,
                    prefix,
                    ctx.author.id,
                )

            elif result is None:
                await self.bot.db.execute(
                    """
                    INSERT INTO 
                    selfprefix 
                    VALUES ($1, $2)
                    """, 
                    ctx.author.id, 
                    prefix
                )

            return await ctx.approve(f"I have **set** your self prefix to `{prefix}`.")

    @group(invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke(self, ctx: Context) -> Message:
        """
        Set custom moderation invoke messages.

        Accepts the `moderator` and `reason` variables.
        """

        return await ctx.send_help(ctx.command)

    @invoke.group(name="kick", invoke_without_command=True, example="{user.mention} was kicked for {reason}")
    @has_permissions(manage_guild=True)
    async def invoke_kick(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the kick invoke message.
        """
        await ctx.settings.update(invoke_kick=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **kick** message",
            f"Use `{ctx.clean_prefix}invoke kick remove` to remove it",
        )

    @invoke_kick.command(
        name="remove",
        aliases=["delete", "del", "rm"]
    )
    @has_permissions(manage_guild=True)
    async def invoke_kick_remove(self, ctx: Context) -> Message:
        """
        Remove the kick invoke message.
        """

        await ctx.settings.update(invoke_kick=None)
        return await ctx.approve("Removed the **kick** invoke message")

    @invoke.group(name="ban", invoke_without_command=True, example="{user.mention} was banned for {reason}")
    @has_permissions(manage_guild=True)
    async def invoke_ban(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the ban invoke message.
        """

        await ctx.settings.update(invoke_ban=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **ban** message",
            f"Use `{ctx.clean_prefix}invoke ban remove` to remove it",
        )

    @invoke_ban.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def invoke_ban_remove(self, ctx: Context) -> Message:
        """
        Remove the ban invoke message.
        """

        await ctx.settings.update(invoke_ban=None)
        return await ctx.approve("Removed the **ban** invoke message")

    @invoke.group(name="unban", invoke_without_command=True, example="{user.mention} was unbanned for {reason}")
    @has_permissions(manage_guild=True)
    async def invoke_unban(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the unban invoke message.
        """

        await ctx.settings.update(invoke_unban=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **unban** message",
            f"Use `{ctx.clean_prefix}invoke unban remove` to remove it",
        )

    @invoke_unban.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def invoke_unban_remove(self, ctx: Context) -> Message:
        """
        Remove the unban invoke message.
        """

        await ctx.settings.update(invoke_unban=None)
        return await ctx.approve("Removed the **unban** invoke message")

    @invoke.group(name="timeout", invoke_without_command=True, example="{user.mention} was timed out for {duration} ({expires})")
    @has_permissions(manage_guild=True)
    async def invoke_timeout(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the timeout invoke message.

        Accepts the `duration` and `expires` variables.
        """

        await ctx.settings.update(invoke_timeout=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **timeout** message",
            f"Use `{ctx.clean_prefix}invoke timeout remove` to remove it",
        )

    @invoke_timeout.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def invoke_timeout_remove(self, ctx: Context) -> Message:
        """
        Remove the timeout invoke message.
        """

        await ctx.settings.update(invoke_timeout=None)
        return await ctx.approve("Removed the **timeout** invoke message")

    @invoke.group(name="untimeout", invoke_without_command=True, example="{user.mention} was untimed out")
    @has_permissions(manage_guild=True)
    async def invoke_untimeout(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the untimeout invoke message.
        """

        await ctx.settings.update(invoke_untimeout=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **untimeout** message",
            f"Use `{ctx.clean_prefix}invoke untimeout remove` to remove it",
        )

    @invoke_untimeout.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_remove(self, ctx: Context) -> Message:
        """
        Remove the untimeout invoke message.
        """

        await ctx.settings.update(invoke_untimeout=None)
        return await ctx.approve("Removed the **untimeout** invoke message")

    @invoke.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_dm(self, ctx: Context) -> Message:
        """
        Configure DM notifications for moderation actions.
        """
        return await ctx.send_help(ctx.command)

    @invoke_dm.command(name="toggle", example="ban")
    @has_permissions(manage_guild=True)
    async def invoke_dm_toggle(self, ctx: Context, action: str) -> Message:
        """
        Toggle DM notifications for a specific action.
        Available actions: ban, unban, kick, jail, unjail, mute, unmute, warn, timeout, untimeout, antinuke_ban, antinuke_kick, antinuke_strip, antiraid_ban, antiraid_kick, antiraid_timeout, antiraid_strip, role_add, role_remove
        """
        valid_actions = [
            "ban", "unban", "kick", "jail", "unjail", 
            "mute", "unmute", "warn", "timeout", "untimeout",
            "antinuke_ban", "antinuke_kick", "antinuke_strip",
            "antiraid_ban", "antiraid_kick", "antiraid_timeout", "antiraid_strip",
            "role_add", "role_remove" 
        ]
        
        action = action.lower()
        if action not in valid_actions:
            return await ctx.warn(
                f"Invalid action. Choose from: {', '.join(f'`{a}`' for a in valid_actions)}"
            )

        exists = await self.bot.db.fetchval(
            "SELECT EXISTS(SELECT 1 FROM mod WHERE guild_id = $1)",
            ctx.guild.id
        )
        
        if exists:
            await self.bot.db.execute(
                f"UPDATE mod SET dm_{action} = CASE WHEN dm_{action} = 'true' THEN 'false' ELSE 'true' END WHERE guild_id = $1",
                ctx.guild.id
            )
        else:
            await self.bot.db.execute(
                f"INSERT INTO mod (guild_id, dm_{action}, dm_enabled) VALUES ($1, 'true', true)",
                ctx.guild.id
            )
        
        new_state = await self.bot.db.fetchval(
            f"SELECT dm_{action} = 'true' FROM mod WHERE guild_id = $1",
            ctx.guild.id
        )
        
        state = "enabled" if new_state else "disabled"
        return await ctx.approve(f"{state.title()} DM notifications for {action}")

    @invoke_dm.command(name="view", example="ban")
    @has_permissions(manage_guild=True)
    async def invoke_dm_view(self, ctx: Context, action: str = None) -> Message:
        """View current DM message for an action or list all configured actions."""
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1", 
            ctx.guild.id
        )
        
        if not settings:
            return await ctx.warn("No DM messages configured")

        if not action:
            configured = []
            for col in settings.keys():
                if col.startswith("dm_") and col != "dm_enabled" and settings[col]:
                    configured.append(f"`{col[3:]}`")
            
            if not configured:
                return await ctx.warn("No custom DM messages configured")
            return await ctx.approve(f"Configured DM messages for: {', '.join(configured)}")

        action = action.lower()
        message = settings.get(f"dm_{action}")
        if not message:
            return await ctx.approve(f"Using default DM message for {action}")
        return await ctx.approve(f"Current {action} DM message:\n```\n{message}\n```")

    @invoke_dm.command(name="set", example="[ban] [{user.mention} was banned for {reason}]")
    @has_permissions(manage_guild=True)
    async def invoke_dm_set(self, ctx: Context, action: str, *, script: Optional[Script] = None) -> Message:
        """
        Set a custom DM message for an action.
        Available actions: ban, unban, kick, jail, unjail, mute, unmute, warn, timeout, untimeout, antinuke_ban, antinuke_kick, antinuke_strip, antiraid_ban, antiraid_kick, antiraid_timeout, antiraid_strip
        """
        valid_actions = [
            "ban", "unban", "kick", "jail", "unjail", 
            "mute", "unmute", "warn", "timeout", "untimeout",
            "antinuke_ban", "antinuke_kick", "antinuke_strip",
            "antiraid_ban", "antiraid_kick", "antiraid_timeout", "antiraid_strip"
        ]
        
        action = action.lower()
        if action not in valid_actions:
            return await ctx.warn(
                f"Invalid action. Choose from: {', '.join(f'`{a}`' for a in valid_actions)}"
            )

        if not script:
            await self.bot.db.execute(
                "UPDATE mod SET dm_" + action + " = NULL WHERE guild_id = $1",
                ctx.guild.id
            )
            return await ctx.approve(f"Reset to default DM message for {action}")

        exists = await self.bot.db.fetchval(
            "SELECT EXISTS(SELECT 1 FROM mod WHERE guild_id = $1)",
            ctx.guild.id
        )
        
        if exists:
            await self.bot.db.execute(
                f"UPDATE mod SET dm_{action} = $1 WHERE guild_id = $2",
                script.template,
                ctx.guild.id
            )
        else:
            await self.bot.db.execute(
                f"INSERT INTO mod (guild_id, dm_{action}, dm_enabled) VALUES ($1, $2, true)",
                ctx.guild.id,
                script.template
            )

        return await ctx.approve(f"Updated {action} DM message")

    @group(invoke_without_command=True, aliases=["poj"])
    async def pingonjoin(self, ctx: Context):
        await ctx.send_help(ctx.command)

    @pingonjoin.command(
        name="add",
        example="#general",
    )
    @has_permissions(manage_guild=True)
    async def poj_add(self, ctx: Context, *, channel: TextChannel):
        """Ping new members when they join your server."""

        check = await self.bot.db.fetchrow(
            "SELECT * FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        if check is not None:
            return await ctx.warning(
                f"The channel {channel.mention} is **already** added as a ping on join channel."
            )

        elif check is None:
            await self.bot.db.execute(
                "INSERT INTO pingonjoin VALUES ($1,$2)", channel.id, ctx.guild.id
            )
        return await ctx.approve(f"I will now ping new members in {channel.mention}.")

    @pingonjoin.command(
        name="remove", 
        example="#general"
    )
    @has_permissions(manage_guild=True)
    async def poj_remove(self, ctx: Context, *, channel: TextChannel = None):
        """Remove the ping on join channel."""

        if channel is not None:

            check = await self.bot.db.fetchrow(
                "SELECT * FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id,
                channel.id,
            )
            if check is None:
                return await ctx.warn(
                    f"The channel {channel.mention} is **not** added as an pingonjoin channel."
                )

            elif check is not None:
                await self.bot.db.execute(
                    "DELETE FROM pingonjoin WHERE guild_id = $1 AND channel_id = $2",
                    ctx.guild.id,
                    channel.id,
                )
            return await ctx.approve(
                f"I will not ping new members in {channel.mention}."
            )

        check = await self.bot.db.fetch(
            "SELECT * FROM pingonjoin WHERE guild_id = {}".format(ctx.guild.id)
        )
        if check is None:
            return await ctx.warn("There is no channel added.")

        elif check is not None:
            await self.bot.db.execute(
                "DELETE FROM pingonjoin WHERE guild_id = {}".format(ctx.guild.id)
            )

        return await ctx.approve("I will **not** ping new members in any channel.")

    @Cog.listener("on_member_join")
    async def pingonjoin_listener(self, member: Member):
        if member.bot:
            return
        
        cache_key = f"poj:{member.guild.id}"
        channels = await self.bot.redis.get(cache_key)
        
        if not channels:
            records = await self.bot.db.fetch(
                "SELECT channel_id FROM pingonjoin WHERE guild_id = $1",
                member.guild.id
            )
            channels = [record['channel_id'] for record in records]
            await self.bot.redis.set(cache_key, channels, ex=60)

        recent_joins = [
            m for m in member.guild.members
            if (datetime.datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds() < 180
        ]

        for channel_id in channels:
            if channel := member.guild.get_channel(int(channel_id)):
                try:
                    if len(recent_joins) < 10:
                        await channel.send(member.mention, delete_after=6)
                    else:
                        if not poj_cache.get(str(channel.id)):
                            poj_cache[str(channel.id)] = []
                        poj_cache[str(channel.id)].append(member.mention)
                        if len(poj_cache[str(channel.id)]) >= 10:
                            await channel.send(" ".join(poj_cache[str(channel.id)]), delete_after=6)
                            poj_cache[str(channel.id)] = []
                except:
                    continue

    @group(invoke_without_command=True)
    async def tag(self, ctx: Context, *, name: str = None) -> Message:
        """
        Create and manage custom tags.
        If no subcommand is given, searches for and displays the requested tag.
        """
        if not name:
            return await ctx.send_help(ctx.command)
            
        record = await self.bot.db.fetchrow(
            """
            SELECT original 
            FROM tag_aliases 
            WHERE guild_id = $1 AND LOWER(alias) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        if record:
            name = record['original']
            
        record = await self.bot.db.fetchrow(
            """
            SELECT template, owner_id 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")

        script = Script(
            record["template"],
            [ctx.guild, ctx.author, ctx.channel],
        )
        
        await self.bot.db.execute(
            """
            UPDATE tags 
            SET uses = uses + 1 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        return await script.send(ctx, normal=True)

    @tag.command(name="create", example="welcome Welcome to evict!")
    @has_permissions(manage_messages=True)
    async def tag_create(self, ctx: Context, name: str, *, template: str) -> Message:
        """Create a new tag."""
        if len(name) > 32:
            return await ctx.warn("Tag name cannot be longer than 32 characters!")
            
        if name.lower() in ctx.command.root_parent.all_commands:
            return await ctx.warn("That tag name is reserved for a subcommand!")

        try:
            script = Script(template, [ctx.guild, ctx.author, ctx.channel])
        except Exception as e:
            return await ctx.warn(f"Invalid template: {e}")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO tags (guild_id, name, owner_id, template)
                VALUES ($1, $2, $3, $4)
                """,
                ctx.guild.id, name, ctx.author.id, template
            )
        except UniqueViolationError:
            return await ctx.warn(f"A tag named `{name}` already exists!")

        return await ctx.approve(f"Created tag `{name}`")

    @tag.command(name="edit", example="welcome Welcome to our amazing evict!")
    @has_permissions(manage_messages=True)
    async def tag_edit(self, ctx: Context, name: str, *, template: str) -> Message:
        """Edit an existing tag."""
        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only edit tags you own!")

        try:
            script = Script(template, [ctx.guild, ctx.author, ctx.channel])
        except Exception as e:
            return await ctx.warn(f"Invalid template: {e}")

        await self.bot.db.execute(
            """
            UPDATE tags 
            SET template = $3 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name, template
        )

        return await ctx.approve(f"Updated tag `{name}`")

    @tag.command(name="delete", aliases=["remove"], example="welcome")
    @has_permissions(manage_messages=True)
    async def tag_delete(self, ctx: Context, *, name: str) -> Message:
        """Delete a tag."""
        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only delete tags you own!")

        await self.bot.db.execute(
            """
            DELETE FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )

        return await ctx.approve(f"Deleted tag `{name}`")

    @tag.command(name="info", example="welcome")
    @has_permissions(manage_messages=True)
    async def tag_info(self, ctx: Context, *, name: str) -> Message:
        """View information about a tag."""
        record = await self.bot.db.fetchrow(
            """
            SELECT name, owner_id, uses, created_at, template
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")

        aliases = await self.bot.db.fetch(
            """
            SELECT alias 
            FROM tag_aliases 
            WHERE guild_id = $1 AND LOWER(original) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        owner = ctx.guild.get_member(record['owner_id'])
        owner_text = owner.mention if owner else f"Unknown User ({record['owner_id']})"
        
        embed = Embed(title=f"Tag Information: {record['name']}")
        embed.add_field(name="Owner", value=owner_text, inline=True)
        embed.add_field(name="Uses", value=f"{record['uses']:,}", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(record['created_at'].timestamp())}:R>", inline=True)
        
        if aliases:
            embed.add_field(
                name="Aliases", 
                value=", ".join(f"`{alias['alias']}`" for alias in aliases),
                inline=False
            )
            
        embed.add_field(name="Content", value=f"```\n{record['template']}\n```", inline=False)
        
        return await ctx.send(embed=embed)

    @tag.command(name="list", aliases=["all"])
    @has_permissions(manage_messages=True)
    async def tag_list(self, ctx: Context) -> Message:
        """List all tags in the server."""
        records = await self.bot.db.fetch(
            """
            SELECT name, uses 
            FROM tags 
            WHERE guild_id = $1 
            ORDER BY uses DESC
            """,
            ctx.guild.id
        )
        
        if not records:
            return await ctx.warn("No tags found in this server!")

        entries = [f"`{r['name']}` ({r['uses']:,} uses)" for r in records]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title=f"Tags in {ctx.guild.name}"),
            per_page=20
        )
        return await paginator.start()

    @tag.command(name="alias", example="welcome hey")
    @has_permissions(manage_messages=True)
    async def tag_alias(self, ctx: Context, name: str, alias: str) -> Message:
        """Create an alias for a tag."""
        if len(alias) > 32:
            return await ctx.warn("Alias cannot be longer than 32 characters!")

        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only create aliases for tags you own!")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO tag_aliases (guild_id, alias, original)
                VALUES ($1, $2, $3)
                """,
                ctx.guild.id, alias, name
            )
        except UniqueViolationError:
            return await ctx.warn(f"An alias named `{alias}` already exists!")

        return await ctx.approve(f"Created alias `{alias}` for tag `{name}`")

    @tag.command(name="search", example="welcome")
    @has_permissions(manage_messages=True)
    async def tag_search(self, ctx: Context, *, query: str) -> Message:
        """Search for tags."""
        records = await self.bot.db.fetch(
            """
            SELECT name, uses 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) LIKE LOWER($2)
            ORDER BY uses DESC
            """,
            ctx.guild.id,
            f"%{query}%"
        )
        
        if not records:
            return await ctx.warn(f"No tags found matching `{query}`!")

        entries = [f"`{r['name']}` ({r['uses']:,} uses)" for r in records]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title=f"Tags matching '{query}'"),
            per_page=10
        )
        return await paginator.start()

    @tag.command(name="raw", example="welcome")
    @has_permissions(manage_messages=True)
    async def tag_raw(self, ctx: Context, *, name: str) -> Message:
        """Show the raw content of a tag."""
        record = await self.bot.db.fetchrow(
            """
            SELECT template 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")

        return await ctx.send(f"```\n{record['template']}\n```")

    @tag.command(name="transfer", example="welcome @user")
    @has_permissions(manage_messages=True)
    async def tag_transfer(self, ctx: Context, name: str, *, member: Member) -> Message:
        """Transfer ownership of a tag to another user."""
        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id 
            FROM tags 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only transfer tags you own!")
            
        if member.bot:
            return await ctx.warn("You cannot transfer tags to bots!")

        await self.bot.db.execute(
            """
            UPDATE tags 
            SET owner_id = $3 
            WHERE guild_id = $1 AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name, member.id
        )

        return await ctx.approve(f"Transferred tag `{name}` to {member.mention}")