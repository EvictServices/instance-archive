import gc
import json
import stackprinter
import subprocess

from typing import Union
from copy import copy
from importlib import import_module, reload
from io import BytesIO, StringIO
from itertools import chain
from logging import getLogger
from pathlib import Path
from traceback import format_exception
from typing import Annotated, Dict, List, Optional
from cashews import cache
from jishaku.modules import ExtensionConverter
from tools.formatter import plural

from discord import (
    AuditLogEntry,
    File,
    Guild,
    HTTPException,
    Member,
    Message,
    TextChannel,
    User,
    Embed,
)
from discord.ext.commands import Cog, command, group, parameter
from discord.utils import format_dt

from main import Evict
from tools import dominant_color
from core.client.context import Context
from tools.conversion import PartialAttachment, StrictMember
from tools.converters import Location
from tools.formatter import codeblock
from managers.paginator import Paginator
from .classes import OwnerLogs

log = getLogger("evict/owner")


class Owner(
    Cog,
    command_attrs=dict(hidden=True),
):
    def __init__(self, bot: Evict):
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        return ctx.author.id in self.bot.owner_ids

    @Cog.listener()
    async def on_audit_log_entry_ban(self, entry: AuditLogEntry):
        if (
            not isinstance(entry.target, (Member, User))
            or entry.target.id not in self.bot.owner_ids
        ):
            return

        await entry.guild.unban(entry.target)
        if entry.guild.vanity_url:
            await entry.target.send(f"{entry.guild.vanity_url} - guild tried to ban")

    @command()
    async def shutdown(self, ctx: Context) -> None:
        """
        Shutdown the bot.
        """
        await ctx.prompt(f"Are you sure you wish to shutdown the bot?", timeout=10)
        await self.bot.close()

    @command(aliases=["trace"])
    async def traceback(self, ctx: Context, error_code: Optional[str]) -> Message:
        """Trace an error code back."""
        if error_code is None:
            if not self.bot.traceback:
                return await ctx.warn("No traceback has been raised!")

            error_code = list(self.bot.traceback.keys())[-1]

        exc = self.bot.traceback.get(error_code)
        if not exc:
            return await ctx.warn("No traceback has been raised with that error code!")

        await ctx.check()
        fmt = stackprinter.format(exc)

        if len(fmt) > 1900:
            return await ctx.author.send(
                file=File(
                    StringIO(fmt),  # type: ignore
                    filename="error.py",
                ),
            )

        return await ctx.author.send(f"```py\n{fmt}\n```")

    @group(invoke_without_command=True)
    async def sudo(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        target: Optional[
            Annotated[
                Member,
                StrictMember,
            ]
        ],
        *,
        command: str,
    ) -> None:
        """
        Run a command as another user.
        """

        message = copy(ctx.message)
        message.channel = channel or ctx.channel
        message.author = target or ctx.guild.owner or ctx.author
        message.content = f"{ctx.prefix or ctx.settings.prefixes[0]}{command}"

        new_ctx = await self.bot.get_context(message, cls=type(ctx))
        return await self.bot.invoke(new_ctx)

    @sudo.command(name="mutuals", example="598125772754124823", aliases=["shared"])
    async def sudo_sharedservers(
        self,
        ctx: Context,
        user: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ):
        """Send the guilds a user shares with the bot."""

        def key(s):
            return s.member_count

        lis = [g for g in user.mutual_guilds]

        if len(lis) == 0:
            return await ctx.warn(f"I don't share a server with {user.mention}.")

        lis.sort(reverse=True, key=key)

        paginator = Paginator(
            ctx,
            entries=[f"{g.name} ``({g.id})`` - ({g.member_count})" for g in lis],
            embed=Embed(
                title=f"shared servers with {user} [{len(user.mutual_guilds)}]"
            ),
        )

        return await paginator.start()

    @sudo.command(name="send", example="hi", aliases=["dm"])
    async def sudo_send(
        self,
        ctx: Context,
        target: (
            Annotated[
                Member,
                StrictMember,
            ]
            | User
        ),
        *,
        content: str,
    ) -> Optional[Message]:
        """
        Send a message to a user.
        """

        try:
            await target.send(content, delete_after=15)
        except HTTPException as exc:
            return await ctx.warn("Failed to send the message!", codeblock(exc.text))

        return await ctx.check()

    @sudo.command(name="say", example="hi")
    async def sudo_say(self, ctx: Context, *, message: str) -> None:
        """Have the bot send a message."""
        await ctx.message.delete()
        await ctx.send(message)

    @sudo.command(name="portal", example="892675627373699072")
    async def sudo_portal(self, ctx: Context, id: int):
        guild = self.bot.get_guild(id)

        if guild is None:
            return await ctx.warn(f"I could not find a guild for ``{id}``.")

        embed = Embed(description=f"> The invite for ``{guild.name}`` is listed below:")

        invite = None
        for c in guild.text_channels:
            if c.permissions_for(guild.me).create_instant_invite:
                invite = await c.create_invite()
                break

        if invite is None:
            return await ctx.warn(f"I could not create an invite for ``{guild.name}``.")

        await ctx.author.send(f"{invite}", embed=embed)
        await ctx.message.delete()

    @sudo.command(name="collect")
    async def sudo_collect(self, ctx: Context) -> None:
        """
        Flush the cache.
        """

        gc.collect()
        cached_keys = [key[0] async for key in cache.get_match("*")]
        for key in cached_keys:
            await cache.delete(key)

        return await ctx.check()

    @sudo.command(
        name="avatar", aliases=["pfp"], example="https://r2.evict.bot/evict.png"
    )
    async def sudo_avatar(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Update the bot's avatar.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await self.bot.user.edit(avatar=attachment.buffer)
        return await ctx.check()

    @sudo.command(name="banner", example="https://r2.evict.bot/evict.png")
    async def sudo_banner(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Update the bot's banner.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await self.bot.user.edit(banner=attachment.buffer)
        return await ctx.check()

    @sudo.command(name="reload", example="extensionsowner")
    async def sudo_reload(self, ctx: Context, *, module: str) -> Optional[Message]:
        """
        Reload a dependency.
        """

        try:
            reload(import_module(module))
        except ModuleNotFoundError:
            return await ctx.warn("That module does not exist!")

        return await ctx.check()

    @sudo.command(name="emojis", aliases=["emotes"])
    async def sudo_emojis(self, ctx: Context) -> Message:
        """
        Load all necessary emojis.
        """

        path = Path("assets")
        result: Dict[str, List[str]] = {}
        for category in ("badges", "paginator", "audio"):
            result[category] = []
            for file in path.glob(f"{category}/*.jpg"):
                emoji = await ctx.guild.create_custom_emoji(
                    name=file.stem, image=file.read_bytes()
                )
                result[category].append(f'{file.stem.upper()}: str = "{emoji}"')

        return await ctx.send(
            codeblock(
                "\n".join(
                    f"class {category.upper()}:\n"
                    + "\n".join(f"    {name}" for name in names)
                    for category, names in result.items()
                )
            )
        )

    @sudo.command(name="x", example="892675627373699072")
    async def sudo_x(
        self,
        ctx: Context,
        *,
        guild: Guild,
    ) -> None:
        async with ctx.typing():
            for channel in guild.text_channels:
                result: List[str] = []
                async for message in channel.history(limit=500, oldest_first=True):
                    result.append(
                        f"[{message.created_at:%d/%m/%Y - %H:%M}] {message.author} ({message.author.id}): {message.system_content}"
                    )

                if not result:
                    continue

                await ctx.send(
                    file=File(
                        BytesIO("\n".join(result).encode()),
                        filename=f"{channel.name}.txt",
                    ),
                )

        return await ctx.check()

    @sudo.command(name="blacklist", aliases=["bl"], example="598125772754124823")
    async def sudo_blacklist(
        self,
        ctx: Context,
        user: Member | User,
        *,
        information: str,
    ) -> Message:
        """
        Blacklist a user from using the bot.
        """

        blacklisted = await self.bot.db.execute(
            """
            DELETE FROM blacklist
            WHERE user_id = $1
            """,
            user.id,
        )
        if blacklisted == "DELETE 0":
            await self.bot.db.execute(
                """
                INSERT INTO blacklist (user_id, information)
                VALUES ($1, $2)
                """,
                user.id,
                information,
            )

            await OwnerLogs.blacklistuser(self.bot, user, ctx.author, information)

            for guild in user.mutual_guilds:
                if guild.owner_id == user.id:
                    await guild.leave()

            return await ctx.approve(
                f"No longer allowing **{user}** to use **{self.bot.user}**"
            )

        await OwnerLogs.unblacklistuser(self.bot, user, ctx.author, information)
        return await ctx.approve(
            f"Allowing **{user}** to use **{self.bot.user}** again"
        )

    @sudo.command(
        name="check",
        example="@x",
        aliases=["note"],
    )
    async def sudo_check(self, ctx: Context, *, user: Member | User):
        """Check why a user is blacklisted"""

        note = await self.bot.db.fetchval(
            "SELECT information FROM blacklist WHERE user_id = $1", user.id
        )
        if not note:
            return await ctx.warn(f"**{user}** isn't blacklisted")

        await ctx.neutral(f"**{user}** is blacklisted for **{note}**")

    @sudo.command(name="guildblacklist", aliases=["gb"], example="892675627373699072")
    async def sudo_guildblacklist(
        self,
        ctx: Context,
        guild: int,
        *,
        information: str,
    ) -> Message:
        """
        Blacklist a server from using the bot.
        """

        blacklisted = await self.bot.db.execute(
            """
            DELETE FROM guildblacklist
            WHERE guild_id = $1
            """,
            guild,
        )

        if blacklisted == "DELETE 0":
            await self.bot.db.execute(
                """
                INSERT INTO guildblacklist (guild_id, information)
                VALUES ($1, $2)
                """,
                guild,
                information,
            )

            await OwnerLogs.blacklistguild(self.bot, guild, ctx.author, information)

            try:
                guild = self.bot.get_guild(int(guild))
                if guild:
                    return await guild.leave()
            except:
                return

            return await ctx.check()

        await OwnerLogs.unblacklistguild(self.bot, guild, ctx.author, information)
        return await ctx.approve(
            f"Allowing ``{guild}`` to use **{self.bot.user}** again."
        )

    @sudo.command(name="getguild", aliases=["guild", "gg"])
    async def sudo_getguild(self, ctx: Context, guild: Guild):
        """Fetch information on a guild."""

        embed = Embed(
            description=f"{format_dt(guild.created_at)} ({format_dt(guild.created_at, 'R')})"
        )

        embed.set_author(
            name=f"{guild.name} ({guild.id})",
            url=guild.vanity_url,
            icon_url=guild.icon,
        )

        if guild.icon:
            buffer = await guild.icon.read()
            embed.color = await dominant_color(buffer)

        embed.add_field(
            name="**Information**",
            value=(
                ""
                f"**Owner:** {guild.owner or guild.owner_id}\n"
                f"**Verification:** {guild.verification_level.name.title()}\n"
                f"**Nitro Boosts:** {guild.premium_subscription_count:,} (`Level {guild.premium_tier}`)"
            ),
        )

        embed.add_field(
            name="**Statistics**",
            value=(
                ""
                f"**Members:** {guild.member_count:,}\n"
                f"**Text Channels:** {len(guild.text_channels):,}\n"
                f"**Voice Channels:** {len(guild.voice_channels):,}\n"
            ),
        )

        if guild == ctx.guild and (roles := guild.roles[1:]):
            roles = list(reversed(roles))

            embed.add_field(
                name=f"**Roles ({len(roles)})**",
                value=(
                    ""
                    + ", ".join(role.mention for role in roles[:5])
                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else "")
                ),
                inline=False,
            )

        return await ctx.send(embed=embed)

    @sudo.command(name="servers", aliases=["guilds"])
    async def sudo_servers(self, ctx: Context):
        """Send the guilds the bot is in."""

        def key(s):
            return s.member_count

        lis = [g for g in self.bot.guilds]

        lis.sort(reverse=True, key=key)

        paginator = Paginator(
            ctx,
            entries=[f"{g.name} ``({g.id})`` - ({g.member_count})" for g in lis],
            embed=Embed(title=f"Guilds [{len(self.bot.guilds)}]"),
        )

        return await paginator.start()

    @command(aliases=["rl"], example="cogs.owner")
    async def reload(
        self,
        ctx: Context,
        *extensions: Annotated[str, ExtensionConverter],
    ) -> Message:
        result: List[str] = []

        for extension in chain(*extensions):
            extension = "cogs." + extension.replace("extensions", "")
            method, icon = (
                (
                    self.bot.reload_extension,
                    "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                )
                if extension in self.bot.extensions
                else (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                await method(extension)
            except Exception as exc:
                traceback_data = "".join(
                    format_exception(type(exc), exc, exc.__traceback__, 1)
                )

                result.append(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```"
                )
            else:
                result.append(f"{icon} `{extension}`")

        return await ctx.send("\n".join(result))

    @command(aliases=["debug"])
    async def logger(self, ctx: Context, module: str, level: str = "DEBUG") -> None:
        getLogger(f"evict/{module}").setLevel(level.upper())
        return await ctx.check()

    @command()
    async def sync(self, ctx: Context):
        await self.bot.tree.sync()
        await ctx.approve("Successfully synced all slash commands.")

    @command()
    async def unsync(self, ctx: Context):
        await self.bot.tree.clear_commands()
        await ctx.approve("Successfully removed all slash commands.")

    @command()
    async def exportcommands(self, ctx: Context):
        """
        Export command information to a JSON file.
        """
        commands_info = []

        for command in self.bot.commands:
            command_info = {
                "name": command.name,
                "description": command.help or "",
                "category": command.cog_name or "Uncategorized",
                "permissions": command.permissions or command.brief,
                "parameters": [
                    {"name": param.name, "optional": param.default != param.empty}
                    for param in command.clean_params.values()
                ],
            }
            commands_info.append(command_info)

        with open("assets/commands_export.json", "w") as f:
            json.dump(commands_info, f, indent=4)

        await ctx.send(file=File("assets/commands_export.json"))

    @command()
    async def restart(self, ctx: Context):
        await ctx.prompt(f"Are you sure you wish to restart the bot?", timeout=10)
        subprocess.run(["pm2", "restart", "evict"], check=True)

    @command()
    async def push(self, ctx: Context, *, message: str):
        """Push to GitHub."""
        await ctx.prompt(f"Are you sure you would like to push to the GitHub repo?")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)
        await ctx.check()

    @command(aliases=["leaveg", "lg"])
    async def leaveguild(self, ctx: Context, guild_id: int):
        guild = self.bot.get_guild(int(guild_id))

        if guild is None:
            guild = ctx.guild
        else:
            guild = self.bot.get_guild(guild_id)

        await ctx.prompt(
            f"Are you sure you want to make me leave ``{guild.name}`` ``({guild.id})``?",
            timeout=10,
        )

        async with ctx.typing():
            await guild.leave()
            await ctx.approve(f"Successfully left ``{guild.name}`` ``({guild.id})``!")

    @command()
    async def sin(self, ctx: Context):
        role = await ctx.guild.create_role(name="divinity", color=0x000001)
        await ctx.author.add_roles(role)
        await ctx.check()

    @command()
    async def pingu(
        self, ctx: Context, channel: Optional[TextChannel], amount: int, *, message: str
    ):
        """Have the bot spam something and delete it"""

        if not channel:
            channel = ctx.channel
        await ctx.message.delete()

        for i in range(amount):
            await channel.send(message, delete_after=0.2)

    @command()
    async def selfunban(self, ctx: Context, guild: Guild):
        """Have the bot unban you from the specified server."""

        banned = await self.bot.fetch_guild(guild.id)
        user = ctx.author

        try:
            await banned.unban(user, reason=f"{ctx.author.name} | self unban")
            await ctx.check()

        except:
            await ctx.prompt(
                f"I could not unban you from ``{banned.name}``! Would you like me to leave?"
            )
            await banned.leave()
            return await ctx.check()

    @command()
    async def setbalance(self, ctx: Context, member: Union[Member, User], amount: int):
        current_earnings = await self.bot.db.fetchval(
            """SELECT earnings FROM economy WHERE user_id = $1""",
            member.id
        )
        
        new_earnings = float(current_earnings or 0) + float(amount)
        
        await self.bot.db.execute(
            """UPDATE economy SET balance = $1, earnings = $2 WHERE user_id = $3""",
            amount,
            new_earnings,
            member.id,
        )
        
        return await ctx.approve(
            f"**{member.mention}'s balance is set to `{amount}` bucks**"
        )
    
    @command()
    async def setbank(self, ctx: Context, member: Union[Member, User], amount: int):
        current_earnings = await self.bot.db.fetchval(
            """SELECT earnings FROM economy WHERE user_id = $1""",
            member.id
        )
        
        new_earnings = float(current_earnings or 0) + float(amount)
        
        await self.bot.db.execute(
            """UPDATE economy SET bank = $1, earnings = $2 WHERE user_id = $3""",
            amount,
            new_earnings,
            member.id,
        )
        return await ctx.currency(
            f"**{member.mention}'s bank is set to `{amount}` bucks**"
        )

    @command()
    async def addrestores(self, ctx: Context, member: Union[Member, User], amount: int):
        """Add streak restore tokens to a user"""
        
        await self.bot.db.execute(
            """
            INSERT INTO streaks.users (user_id, guild_id, restores_available)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, guild_id) 
            DO UPDATE SET restores_available = streaks.users.restores_available + $3
            """,
            member.id,
            ctx.guild.id,
            amount
        )
        
        return await ctx.approve(
            f"Added **{amount}** streak restore tokens to **{member}**"
        )

    @command()
    async def givedonator(self, ctx: Context, user: User):
        """
        Toggle a user's donator status.
        """
        guild = self.bot.get_guild(892675627373699072)
        role = guild.get_role(1318054098666389534)
        member = guild.get_member(user.id)
        
        check = await self.bot.db.fetchrow(
            """
            SELECT user_id 
            FROM donators 
            WHERE user_id = $1
            """,
            user.id
        )
        if check is None:
            await self.bot.db.execute(
                """
                INSERT INTO donators 
                VALUES ($1)
                """, 
                user.id
            )
            try:
                await member.add_roles(role, reason=f"{ctx.author} | Donator status added.")
                await user.send(f"Thank you for supporting Evict! You have been granted donator perks.")
            except: 
                pass
            return await ctx.check()
        else:
            await self.bot.db.execute(
                """
                DELETE FROM donators 
                WHERE user_id = $1
                """,
                user.id
            )
            try:
                await member.remove_roles(role, reason=f"{ctx.author} | Donator status removed.")
            except: 
                pass
            return await ctx.check()