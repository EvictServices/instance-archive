import secrets
import os
import importlib
import glob
import asyncpg
import time
import jishaku
import jishaku.flags
import config
import asyncio
import discord_ios

from contextlib import suppress
from datetime import datetime
from pathlib import Path
from core.client import database
from pomice import NodePool
from collections.abc import Mapping
from typing import Any, Collection, Dict, Optional, cast
from humanfriendly import format_timespan
from colorama import Fore, Style
from aiohttp import ClientSession, TCPConnector
from asyncpraw import Reddit as RedditClient
from cashews import cache

from core.client.browser import BrowserHandler
from core.client.context import Context, Redis
from core.client import logging
from core.client.generation import process_image_effect
from core.client.database import Database, Settings
from core.client.help import EvictHelp

from cogs.config.extended.roles.dynamicrolebutton import DynamicRoleButton
from cogs.config.extended.ticket.ticket import DeleteTicket

from tools.conversion.embed1 import EmbedScript
from tools.translator import Translator
from tools.formatter import human_join, plural

from multiprocessing import Pool, cpu_count

from managers.parser.TagScript.exceptions import EmbedParseError, TagScriptError

from discord.ext import commands
from discord.message import Message
from discord.utils import utcnow

from dotenv import load_dotenv
load_dotenv()

from discord import (
    AllowedMentions,
    AuditLogEntry,
    ChannelType,
    ClientUser,
    Forbidden,
    Guild,
    HTTPException,
    Intents,
    Interaction,
    Invite,
    Member,
    MessageType,
    NotFound,
    PartialMessageable,
    StageChannel,
    TextChannel,
    User,
    VoiceState,
    Activity,
    ActivityType,
    Embed,
)

from discord.ext.commands import (
    BadFlagArgument,
    BadInviteArgument,
    BadLiteralArgument,
    BadUnionArgument,
    BucketType,
    ChannelNotFound,
    CheckFailure,
    CommandError,
    CommandInvokeError,
    CommandNotFound,
    CommandOnCooldown,
    CooldownMapping,
    DisabledCommand,
    FlagError,
    MaxConcurrencyReached,
    MemberNotFound,
    MessageNotFound,
    MissingFlagArgument,
    MissingPermissions,
    MissingRequiredArgument,
    MissingRequiredAttachment,
    MissingRequiredFlag,
    NotOwner,
    RangeError,
    RoleNotFound,
    TooManyFlags,
    UserNotFound,
)

cache.setup("mem://")

Mapping.register(asyncpg.Record)

jishaku.Flags.HIDE = True
jishaku.Flags.RETAIN = True
jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.FORCE_PAGINATOR = True

log = logging.getLogger(__name__)

async def getprefix(bot, message):
    if not message.guild:
        return os.getenv("BOT_PREFIX", ";")

    check = await bot.db.fetchrow(
        """
        SELECT * FROM selfprefix 
        WHERE user_id = $1
        """, 
        message.author.id
    )
    if check:
        selfprefix = check["prefix"]

    res = await bot.db.fetchrow(
        """
        SELECT * FROM prefix 
        WHERE guild_id = $1
        """, 
        message.guild.id
    )
    if res:
        guildprefix = res["prefix"]
    else:
        guildprefix = os.getenv("BOT_PREFIX", ";")

    if not check and res:
        selfprefix = res["prefix"]
    elif not check and not res:
        selfprefix = os.getenv("BOT_PREFIX", ";")

    return guildprefix, selfprefix


class Evict(commands.AutoShardedBot):
    session: ClientSession
    uptime: datetime
    traceback: Dict[str, Exception]
    global_cooldown: CooldownMapping
    owner_ids: Collection[int]
    database: Database
    redis: Redis
    user: ClientUser
    reddit: RedditClient
    version: str = "3.0"
    user_agent: str = f"Evict (DISCORD BOT/{version})"
    browser: BrowserHandler
    voice_join_times = {}
    voice_update_task = None

    def __init__(self, *args, **kwargs):
        async def get_activity_settings():
            try:
                async with asyncpg.create_pool(
                    config.DATABASE.DSN,
                    ssl=False,
                    command_timeout=60,
                    max_inactive_connection_lifetime=60
                ) as pool:
                    activity_data = await pool.fetchrow('SELECT * FROM bot_activity')
                    return activity_data or {
                        'activity_type': 'streaming',
                        'activity_text': '🔗 discord.gg/evict',
                        'activity_url': 'https://twitch.tv/evictbot'
                    }
            except Exception as e:
                log.error(f"Database connection error: {e}")
                return {
                    'activity_type': 'streaming',
                    'activity_text': '🔗 discord.gg/evict',
                    'activity_url': 'https://twitch.tv/evictbot'
                }

        activity_data = asyncio.run(get_activity_settings())
        
        activity_type = getattr(ActivityType, activity_data['activity_type'].lower(), ActivityType.streaming)
        
        super().__init__(
            *args,
            **kwargs,
            intents=Intents(
                guilds=True,
                members=True,
                messages=True,
                reactions=True,
                presences=True,
                moderation=True,
                voice_states=True,
                message_content=True,
                emojis_and_stickers=True,
            ),
            allowed_mentions=AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
            command_prefix=getprefix,
            help_command=EvictHelp(),
            case_insensitive=True,
            max_messages=1500,
            activity=Activity(
                type=activity_type,
                name=activity_data['activity_text'],
                url=activity_data['activity_url'],
            ),
        )
        self.translator = Translator(self)  
        
        self.traceback = {}
        self.global_cooldown = CooldownMapping.from_cooldown(2, 3, BucketType.user)
        self.add_check(self.check_global_cooldown)
        self.uptime2 = time.time()
        self.embed_build = EmbedScript()
        self.cache = cache(self)
        self.process_pool = Pool(processes=max(1, cpu_count() - 1))

        self.guild_ratelimit_10s = CooldownMapping.from_cooldown(
            config.RATELIMITS.PER_10S, 10, BucketType.guild
        )
        self.guild_ratelimit_30s = CooldownMapping.from_cooldown(
            config.RATELIMITS.PER_30S, 30, BucketType.guild
        )
        self.guild_ratelimit_1m = CooldownMapping.from_cooldown(
            config.RATELIMITS.PER_1M, 60, BucketType.guild
        )

    @property
    def db(self) -> Database:
        return self.database

    @property
    def owner(self) -> User:
        return self.get_user(self.owner_ids[0])  # type: ignore

    def get_message(self, message_id: int) -> Optional[Message]:
        return self._connection._get_message(message_id)

    async def get_or_fetch_user(self, user_id: int) -> User:
        return self.get_user(user_id) or await self.fetch_user(user_id)

    def run(self) -> None:
        log.info("Starting the bot...")

        super().run(
            config.DISCORD.TOKEN,
            reconnect=True,
            log_handler=None,
        )

    async def close(self) -> None:
        try:
            if self.voice_update_task:
                self.voice_update_task.cancel()
            
            if hasattr(self, 'browser') and self.browser:
                try:
                    await self.browser.cleanup()
                except Exception as e:
                    log.warning(f"Error cleaning up browser: {e}")
            
            if hasattr(self, 'session'):
                await self.session.close()
            
            if hasattr(self, 'process_pool'):
                self.process_pool.close()
                self.process_pool.join()
                
            await super().close()
            
        except Exception as e:
            log.error(f"Error during shutdown: {e}")
            raise

    async def on_ready(self) -> None:

        channel_id = config.LOGGER.STATUS_LOGGER
        channel = self.get_channel(channel_id)

        embed = Embed(
            description=f"Evict is now online with **{len(self.guilds)}** total guilds and **{len(self.users)}** total users.",
            color=config.COLORS.NEUTRAL,
        )

        try:
            await channel.send(embed=embed)
        except:
            return

        if hasattr(self, "uptime"):
            return

        log.info(
            f"Connected as {Fore.LIGHTCYAN_EX}{Style.BRIGHT}{self.user}{Fore.RESET} ({Fore.LIGHTRED_EX}{self.user.id}{Fore.RESET})."
        )
        self.uptime = utcnow()
        await self.browser.init()
        await self.wait_until_ready()
        await self.load_extensions()
        await self.connect_nodes()

    async def on_command(self, ctx: Context) -> None:
        if not ctx.guild:
            return
            
        await self.db.execute(
            """
            INSERT INTO statistics.daily 
                (guild_id, date, member_id, messages_sent)
            VALUES 
                ($1, CURRENT_DATE, $2, 0)
            ON CONFLICT (guild_id, date, member_id) DO UPDATE SET 
                messages_sent = statistics.daily.messages_sent
            """,
            ctx.guild.id,
            ctx.author.id
        )

        await self.db.execute(
            """
            INSERT INTO invoke_history.commands 
            (guild_id, user_id, command_name, category, timestamp)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.command.qualified_name,
            ctx.command.cog_name or "No Category",
        )

        log.info(
            "%s (%s) used %s in %s (%s)",
            ctx.author.name,
            ctx.author.id,
            ctx.command.qualified_name,
            ctx.guild.name,
            ctx.guild.id,
        )

        channel_id = config.LOGGER.COMMAND_LOGGER
        channel = self.get_channel(channel_id)

        embed = Embed(
            description=(
                f"Text command `{ctx.command.qualified_name}` has been ran in "
                f"`{ctx.guild.name}` (`{ctx.guild.id}`) in {ctx.channel.mention} (`{ctx.channel.id}`) by "
                f"`{ctx.author.name}` (`{ctx.author.id}`) with message id: "
                f"`{ctx.message.id}`"
            ),
            color=config.COLORS.NEUTRAL,
        )

        try:
            await channel.send(embed=embed)
        except:
            log.error("Failed to send command log; channel not found.")

    async def setup_hook(self) -> None:
        try:
            self.session = ClientSession(
                headers={"User-Agent": self.user_agent},
                connector=TCPConnector(ssl=False),
            )
            self.browser = BrowserHandler()
            self.add_dynamic_items(DynamicRoleButton)
            self.add_view(DeleteTicket())
            self.database = await database.connect()
            REDIS_URL = f"redis://:{config.REDIS.PASSWORD}@{config.REDIS.HOST}:{config.REDIS.PORT}"
            self.redis = await Redis.from_url(REDIS_URL)
            
            await self.db.execute("""
                INSERT INTO instance_info 
                    (owner_id, owner_username, owner_email) 
                VALUES 
                    ($1, $2, $3)
                ON CONFLICT (owner_id)
                DO UPDATE SET 
                    owner_username = EXCLUDED.owner_username,
                    owner_email = EXCLUDED.owner_email,
                    updated_at = CURRENT_TIMESTAMP
            """, 
                int(os.getenv("INSTANCE_OWNER_ID")),
                os.getenv("INSTANCE_OWNER_USERNAME"),
                os.getenv("INSTANCE_OWNER_EMAIL")
            )
            
            await self.load_patches()
            self.voice_update_task = self.loop.create_task(self.update_voice_times())
            
            for guild in self.guilds:
                for vc in guild.voice_channels:
                    for member in vc.members:
                        if not member.bot:
                            self.voice_join_times[member.id] = time.time()

            await self.translator.setup()
            
            try:
                await self.browser.init()
            except Exception as e:
                log.warning(f"Browser initialization failed: {e}")
                log.info("Some features requiring browser functionality may be limited")
            
        except Exception as e:
            log.error(f"Error in setup_hook: {e}")
            raise

    async def connect_nodes(self) -> None:
        for _ in range(config.LAVALINK.NODE_COUNT):
            identifier = "evict"
            try:
                await NodePool().create_node(
                    bot=self,  # type: ignore
                    host="127.0.0.1",
                    port=config.LAVALINK.PORT,
                    password=config.LAVALINK.PASSWORD,
                    secure=False,
                    identifier=identifier,
                    spotify_client_id=config.AUTHORIZATION.SPOTIFY.CLIENT_ID,
                    spotify_client_secret=config.AUTHORIZATION.SPOTIFY.CLIENT_SECRET,
                )
                log.info(f"Successfully connected to node {identifier}")
            except Exception as e:
                log.error(f"Failed to connect to node {identifier}: {e}")

    async def load_extensions(self) -> None:
        await self.load_extension("jishaku")
        for feature in Path("cogs").iterdir():
            if feature.is_dir() and (feature / "__init__.py").is_file():
                try:
                    await self.load_extension(".".join(feature.parts))
                except Exception as exc:
                    log.exception(
                        f"Failed to load extension {feature.name}.", exc_info=exc
                    )

    async def load_patches(self) -> None:
        for module in glob.glob("managers/patches/**/*.py", recursive=True):
            if module.endswith("__init__.py"):
                continue
            module_name = (
                module.replace(os.path.sep, ".").replace("/", ".").replace(".py", "")
            )
            try:
                importlib.import_module(module_name)
                log.info(f"Patched: {module}")
            except (ModuleNotFoundError, ImportError) as e:
                log.error(f"Error importing {module_name}: {e}")

    async def log_traceback(self, ctx: Context, exc: Exception) -> Message:
        """
        Store an Exception in memory.
        This is used for future reference.
        """

        log.exception(
            "Unexpected exception occurred in %s.",
            ctx.command.qualified_name,
            exc_info=exc,
        )

        key = secrets.token_urlsafe(54)
        self.traceback[key] = exc

        return await ctx.warn(
            f"Command `{ctx.command.qualified_name}` raised an exception. Please try again later.",
            content=f"`{key}`",
        )

    async def on_command_error(self, ctx: Context, exc: CommandError) -> Any:
        channel = ctx.channel
        if not (
            channel.permissions_for(channel.guild.me).send_messages
            and channel.permissions_for(channel.guild.me).embed_links
        ):
            return

        if isinstance(
            exc,
            (
                CommandNotFound,
                DisabledCommand,
                NotOwner,
            ),
        ):
            return

        elif isinstance(
            exc,
            (
                MissingRequiredArgument,
                MissingRequiredAttachment,
                BadLiteralArgument,
            ),
        ):
            return await ctx.send_help(ctx.command)

        elif isinstance(exc, TagScriptError):
            if isinstance(exc, EmbedParseError):
                return await ctx.warn(
                    "Something is wrong with your **script**!",
                    *exc.args,
                )

        elif isinstance(exc, FlagError):
            if isinstance(exc, TooManyFlags):
                return await ctx.warn(
                    f"You specified the **{exc.flag.name}** flag more than once!"
                )

            elif isinstance(exc, BadFlagArgument):
                try:
                    annotation = exc.flag.annotation.__name__
                except AttributeError:
                    annotation = exc.flag.annotation.__class__.__name__

                return await ctx.warn(
                    f"Failed to cast **{exc.flag.name}** to `{annotation}`!",
                    *(
                        [
                            "Make sure you provide **on** or **off** for `Status` flags!",
                        ]
                        if annotation == "Status"
                        else []
                    ),
                )

            elif isinstance(exc, MissingRequiredFlag):
                return await ctx.warn(f"You must specify the **{exc.flag.name}** flag!")

            elif isinstance(exc, MissingFlagArgument):
                return await ctx.warn(
                    f"You must specify a value for the **{exc.flag.name}** flag!"
                )

        if isinstance(exc, CommandInvokeError):
            return await ctx.warn(exc.original)

        elif isinstance(exc, MaxConcurrencyReached):
            if ctx.command.qualified_name in ("lastfm set", "lastfm index"):
                return

            return await ctx.warn(
                f"This command can only be used **{plural(exc.number):time}**"
                f" per **{exc.per.name}** concurrently!",
                delete_after=5,
            )

        elif isinstance(exc, CommandOnCooldown):
            if exc.retry_after > 30:
                return await ctx.warn(
                    "This command is currently on cooldown!",
                    f"Try again in **{format_timespan(exc.retry_after)}**",
                )

            return await ctx.message.add_reaction("⏰")

        elif isinstance(exc, BadUnionArgument):
            if exc.converters == (Member, User):
                return await ctx.warn(
                    f"No **{exc.param.name}** was found matching **{ctx.current_argument}**!",
                    "If the user is not in this server, try using their **ID** instead",
                )

            elif exc.converters == (Guild, Invite):
                return await ctx.warn(
                    f"No server was found matching **{ctx.current_argument}**!",
                )

            else:
                return await ctx.warn(
                    f"Casting **{exc.param.name}** to {human_join([f'`{c.__name__}`' for c in exc.converters])} failed!",
                )

        elif isinstance(exc, MemberNotFound):
            return await ctx.warn(
                f"No **member** was found matching **{exc.argument}**!"
            )

        elif isinstance(exc, UserNotFound):
            return await ctx.warn(f"No **user** was found matching `{exc.argument}`!")

        elif isinstance(exc, RoleNotFound):
            return await ctx.warn(f"No **role** was found matching **{exc.argument}**!")

        elif isinstance(exc, ChannelNotFound):
            return await ctx.warn(
                f"No **channel** was found matching **{exc.argument}**!"
            )

        elif isinstance(exc, BadInviteArgument):
            return await ctx.warn("Invalid **invite code** provided!")

        elif isinstance(exc, MessageNotFound):
            return await ctx.warn(
                "The provided **message** was not found!",
                "Try using the **message URL** instead",
            )

        elif isinstance(exc, RangeError):
            label = ""
            if exc.minimum is None and exc.maximum is not None:
                label = f"no more than `{exc.maximum}`"
            elif exc.minimum is not None and exc.maximum is None:
                label = f"no less than `{exc.minimum}`"
            elif exc.maximum is not None and exc.minimum is not None:
                label = f"between `{exc.minimum}` and `{exc.maximum}`"

            if label and isinstance(exc.value, str):
                label += " characters"

            return await ctx.warn(f"The input must be {label}!")

        elif isinstance(exc, MissingPermissions):
            permissions = human_join(
                [f"`{permission}`" for permission in exc.missing_permissions],
                final="and",
            )
            _plural = "s" if len(exc.missing_permissions) > 1 else ""

            return await ctx.warn(
                f"You're missing the {permissions} permission{_plural}!"
            )

        elif isinstance(exc, CommandError):
            if not isinstance(exc, (CheckFailure, Forbidden)) and isinstance(
                exc, (HTTPException, NotFound)
            ):
                if "Unknown Channel" in exc.text:
                    return

                return await ctx.warn(exc.text.capitalize())

            origin = getattr(exc, "original", exc)
            with suppress(TypeError):
                if any(
                    forbidden in origin.args[-1]
                    for forbidden in (
                        "global check",
                        "check functions",
                        "Unknown Channel",
                    )
                ):
                    return

            return await ctx.warn(*origin.args)

        else:
            return await ctx.send_help(ctx.command)

    async def get_context(
        self,
        origin: Message | Interaction,
        /,
        *,
        cls=Context,
    ) -> Context:
        context = await super().get_context(origin, cls=cls)
        context.settings = await Settings.fetch(self, context.guild)

        return context

    async def check_global_cooldown(self, ctx: Context) -> bool:
        if ctx.author.id in self.owner_ids:
            return True

        bucket = self.global_cooldown.get_bucket(ctx.message)
        if bucket:
            retry_after = bucket.update_rate_limit()
            if retry_after:
                raise CommandOnCooldown(bucket, retry_after, BucketType.user)

        return True

    async def process_commands(self, message: Message) -> None:
        if not message.guild or message.author.bot:
            return

        channel = message.channel
        if not (
            channel.permissions_for(message.guild.me).send_messages
            and channel.permissions_for(message.guild.me).embed_links
            and channel.permissions_for(message.guild.me).attach_files
        ):
            return

        blacklisted = cast(
            bool,
            await self.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM blacklist
                    WHERE user_id = $1
                )
                """,
                message.author.id,
            ),
        )
        if blacklisted:
            return

        ctx = await self.get_context(message)
        if (
            ctx.invoked_with
            and isinstance(message.channel, PartialMessageable)
            and message.channel.type != ChannelType.private
        ):
            log.warning(
                "Discarded a command message (ID: %s) with PartialMessageable channel: %r.",
                message.id,
                message.channel,
            )
        else:
            await self.invoke(ctx)

        if not ctx.valid:
            self.dispatch("message_without_command", ctx)

    async def on_message(self, message: Message) -> None:
        if message.guild and not message.author.bot:
            if not await self.check_guild_ratelimit(message):
                return
                
            await self.db.execute(
                """
                INSERT INTO statistics.daily 
                    (guild_id, date, member_id, messages_sent)
                VALUES 
                    ($1, CURRENT_DATE, $2, 1)
                ON CONFLICT (guild_id, date, member_id) DO UPDATE SET 
                    messages_sent = statistics.daily.messages_sent + 1
                """,
                message.guild.id,
                message.author.id
            )
            
            await self.db.execute(
                """
                INSERT INTO statistics.daily_channels 
                    (guild_id, channel_id, date, messages_sent)
                VALUES 
                    ($1, $2, CURRENT_DATE, 1)
                ON CONFLICT (guild_id, channel_id, date) DO UPDATE SET 
                    messages_sent = statistics.daily_channels.messages_sent + 1
                """,
                message.guild.id,
                message.channel.id
            )

        if (
            message.guild
            and message.guild.system_channel_flags.premium_subscriptions
            and message.type in (
                MessageType.premium_guild_subscription,
                MessageType.premium_guild_tier_1,
                MessageType.premium_guild_tier_2,
                MessageType.premium_guild_tier_3,
            )
        ):
            self.dispatch("member_boost", message.author)

        return await super().on_message(message)

    async def on_message_edit(self, before: Message, after: Message) -> None:
        self.dispatch("member_activity", after.channel, after.author)
        if before.content == after.content:
            return

        if after.guild and not after.author.bot:
            if not await self.check_guild_ratelimit(after):
                return

        return await self.process_commands(after)

    async def on_typing(
        self,
        channel: TextChannel,
        user: Member | User,
        when: datetime,
    ) -> None:
        if isinstance(user, Member):
            self.dispatch("member_activity", channel, user)

    async def on_member_update(self, before: Member, after: Member) -> None:
        if after.guild.system_channel_flags.premium_subscriptions:
            return

        if not before.premium_since and after.premium_since:
            self.dispatch("member_boost", after)

        elif before.premium_since and not after.premium_since:
            self.dispatch("member_unboost", before)

    async def process_image(self, buffer, effect_type, **kwargs):
        """
        Wrapper for process pool execution.
        """
        try:
            return await self.loop.run_in_executor(
                None,
                self.process_pool.apply,
                process_image_effect,
                (buffer, effect_type),
                kwargs
            )
        except Exception as e:
            log.error(f"Image processing error: {e}")
            raise

    async def on_member_remove(self, member: Member) -> None:
        if member == self.user:
            return

        if member.premium_since:
            self.dispatch("member_unboost", member)

    async def on_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState,
    ):
        """
        Make sure the bot is a Stage Channel speaker.
        """

        if member.bot:
            if (
                member == self.user
                and after.suppress
                and after.channel
                and before.channel != after.channel
                and isinstance(after.channel, StageChannel)
            ):
                with suppress(HTTPException):
                    await member.edit(suppress=False)
            return

        if before.channel is None and after.channel is not None:
            self.voice_join_times[member.id] = time.time()

        elif before.channel is not None and after.channel is None:
            self.voice_join_times.pop(member.id, None)

    async def on_audit_log_entry_create(self, entry: AuditLogEntry):
        if not self.is_ready():
            return

        event = f"audit_log_entry_{entry.action.name}"
        self.dispatch(event, entry)

    async def notify(self, guild: Guild, *args, **kwargs) -> Optional[Message]:
        """
        Send a message to the first available channel.
        """

        if (
            guild.system_channel
            and guild.system_channel.permissions_for(guild.me).send_messages
        ):
            try:
                return await guild.system_channel.send(*args, **kwargs)
            except HTTPException:
                return

        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    return await channel.send(*args, **kwargs)
                except HTTPException:
                    break

    async def update_voice_times(self):
        await self.wait_until_ready()
        while not self.is_closed():
            current_time = time.time()
            
            for guild in self.guilds:
                voice_members = {}
                
                for vc in guild.voice_channels:
                    for member in vc.members:
                        if not member.bot:
                            if member.id not in self.voice_join_times:
                                self.voice_join_times[member.id] = current_time
                                continue
                                
                            join_time = self.voice_join_times[member.id]
                            minutes = int((current_time - join_time) / 60)
                            
                            if minutes > 0:
                                voice_members[member.id] = minutes
                                self.voice_join_times[member.id] = current_time
                
                if voice_members:
                    total_minutes = sum(voice_members.values())
                    await self.db.execute(
                        """
                        INSERT INTO statistics.daily (guild_id, voice_minutes)
                        VALUES ($1, $2)
                        ON CONFLICT (guild_id, date) 
                        DO UPDATE SET voice_minutes = statistics.daily.voice_minutes + $2
                        """,
                        guild.id,
                        total_minutes
                    )
            
            await asyncio.sleep(30)

    async def check_guild_ratelimit(self, message) -> bool:
        if not message.guild:
            return True
            
        bucket_10s = self.guild_ratelimit_10s.get_bucket(message)
        bucket_30s = self.guild_ratelimit_30s.get_bucket(message) 
        bucket_1m = self.guild_ratelimit_1m.get_bucket(message)

        retry_after = bucket_10s.update_rate_limit() or bucket_30s.update_rate_limit() or bucket_1m.update_rate_limit()
        
        return not bool(retry_after)

    async def update_activity(self, activity_type: str = None, text: str = None, url: str = None):
        """
        Updates the bot's activity in both database and real-time.
        """
        if activity_type or text or url:
            update_parts = []
            values = []
            i = 1

            if activity_type:
                update_parts.append(f"activity_type = ${i}")
                values.append(activity_type)
                i += 1
            if text:
                update_parts.append(f"activity_text = ${i}")
                values.append(text)
                i += 1
            if url:
                update_parts.append(f"activity_url = ${i}")
                values.append(url)
                i += 1

            query = f"UPDATE bot_activity SET {', '.join(update_parts)}"
            await self.db.execute(query, *values)

        activity_data = await self.db.fetchrow('SELECT * FROM bot_activity')
        
        activity_type = getattr(ActivityType, activity_data['activity_type'].lower(), ActivityType.streaming)
        await self.change_presence(
            activity=Activity(
                type=activity_type,
                name=activity_data['activity_text'],
                url=activity_data['activity_url']
            )
        )

if __name__ == "__main__":
    bot = Evict(
        description=config.CLIENT.DESCRIPTION,
        owner_ids=config.CLIENT.OWNER_IDS,
    )
    bot.run()