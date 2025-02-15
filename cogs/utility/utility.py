import re
import textwrap
import unicodedata
import time

from datetime import datetime
from hashlib import sha1, sha224, sha256, sha384, sha512
from re import Pattern, compile
from io import BytesIO
from typing import Annotated, Dict, List, Optional, cast
from urllib.parse import quote_plus
import random
import base64
from types import SimpleNamespace
import os

from aiohttp import FormData

import dateparser
import cv2
import numpy
from nudenet import NudeDetector
from bs4 import BeautifulSoup
from dateutil.tz import gettz
from discord import (
    User,
    Guild,
    Embed,
    File,
    HTTPException,
    Member,
    Message,
    RawReactionActionEvent,
    TextChannel,
    Thread,
    Attachment,
)
from discord.ext.commands import (
    BucketType,
    Cog,
    clean_content,
    command,
    cooldown,
    group,
    has_permissions,
    parameter,
    hybrid_group,
    hybrid_command,
    Range,
    flag,
)
from discord.utils import format_dt, utcnow
from humanize import ordinal

# from shazamio import Serialize as ShazamSerialize
# from shazamio import Shazam as ShazamClient
from xxhash import xxh32_hexdigest, xxh64_hexdigest, xxh128_hexdigest
from typing import Annotated, List, Literal, Optional, Union, Dict
from yarl import URL
from itertools import zip_longest
from dataclasses import dataclass

import config
import discord
import io
import aiohttp
import decimal

from cogs.social.models import YouTubeVideo
from config import AUTHORIZATION
from main import Evict

from tools import dominant_color
from core.client.context import Context
from tools.conversion import PartialAttachment, Timezone
from tools.formatter import codeblock, human_join, shorten
from managers.paginator import Paginator
from tools.conversion.script import Script
from cogs.utility.handlers.embeds import EmbedScript, EmbedJson
from managers.patches.permissions import donator

from .extended import Extended
from .models.google import Google, GoogleTranslate
from .handlers import EmbedBuilding

from logging import getLogger

from datetime import datetime, timezone
import asyncio
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from discord.ext import tasks

from core.client import FlagConverter

log = getLogger("evict/utility")

IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
STICKER_KB = 512
STICKER_DIM = 320
STICKER_EMOJI = "😶"
MISSING_EMOJIS = "cant find emojis or stickers in that message."
MISSING_REFERENCE = "reply to a message with this command to steal an emoji."
MESSAGE_FAIL = "i couldn't grab that message."
UPLOADED_BY = "uploaded by"
STICKER_DESC = "stolen sticker"
STICKER_FAIL = "failed to upload sticker"
STICKER_SUCCESS = "uploaded sticker"
EMOJI_SUCCESS = "uploaded emoji"
STICKER_SLOTS = "this server doesn't have any more space for stickers."
EMOJI_FAIL = "failed to upload"
EMOJI_SLOTS = "this server doesn't have any more space for emojis."
INVALID_EMOJI = "invalid emoji or emoji ID."
STICKER_TOO_BIG = f"stickers may only be up to {STICKER_KB} KB and {STICKER_DIM}x{STICKER_DIM} pixels."
STICKER_ATTACHMENT = ""

LINKVERTISE_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:linkvertise\.com|link-target\.net)/(?P<id>\d+)/(?P<name>[a-zA-Z0-9-]+)(?:\?o=sharing)?"
)

class ScreenshotFlags(FlagConverter):
    wait: Range[int, 0, 10] = flag(
        default=0,
        description="Seconds to wait before screenshot (max 10)",
    )
    full_page: bool = flag(
        default=False,
        description="Whether to capture the full page",
    )


@dataclass(init=True, order=True, frozen=True)
class StolenEmoji:
    animated: bool
    name: str
    id: int

    @property
    def url(self):
        return f"https://cdn.discordapp.com/emojis/{self.id}.{'gif' if self.animated else 'png'}"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, StolenEmoji) and self.id == other.id


class Utility(Extended, Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "Utility commands to enhance functionality."
        # self.locks = defaultdict(asyncio.Lock)
        # self.shazamio = ShazamClient()
        self.nude_detector = NudeDetector()
        self.auto_media.start()
        self._cache = {}
        self._cache_times = {}

    def _get_cache(self, key: str):
        """Get a value from cache if not expired"""
        if key in self._cache:
            if time.time() < self._cache_times[key]:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._cache_times[key]
        return None

    def _set_cache(self, key: str, value, expire: int = 300):
        """Set a value in cache with expiration"""
        self._cache[key] = value
        self._cache_times[key] = time.time() + expire

    def cog_unload(self):
        self.auto_media.cancel()

    @tasks.loop(seconds=60)
    async def auto_media(self):
        """Auto-post media to configured channels."""
        records = await self.bot.db.fetch(
            """
            SELECT guild_id, channel_id, type, category
            FROM auto.media
            """
        )

        for record in records:
            try:
                guild = self.bot.get_guild(record['guild_id'])
                if not guild:
                    continue

                channel = guild.get_channel(record['channel_id'])
                if not channel:
                    continue

                media_type = record['type']
                category = record['category']

                base_url = f"https://cdn.evict.bot/random/{media_type}s"
                if category != "random":
                    base_url = f"{base_url}/{category}"

                async with self.bot.session.get(f"{base_url}?token=01k6qYnoSwTG552I") as resp:
                    if resp.status != 200:
                        continue
                    
                    data = await resp.json()
                    
                    async with self.bot.session.get(data['url']) as img_resp:
                        if img_resp.status != 200:
                            continue
                            
                        image_data = await img_resp.read()
                        
                        color = await dominant_color(io.BytesIO(image_data))
                        
                        file_hash = data['url'].split('/')[-1].split('.')[0]
                        file_ext = data['format_type']
                        file = discord.File(
                            io.BytesIO(image_data), 
                            filename=f"evict-{file_hash}.{file_ext}"
                        )
                        
                        embed = Embed(color=color, title="Powered by Evict", url=f"{config.CLIENT.INVITE_URL}")
                        embed.set_image(url=f"attachment://evict-{file_hash}.{file_ext}")
                        
                        filename_without_ext = data['filename'].split('.')[0]
                        embed.set_footer(
                            text=f"{data['category']} • id: {filename_without_ext} • /avreport • discord.gg/evict"
                        )
                        
                        await channel.send(embed=embed, file=file)

            except Exception as e:
                log.error(f"Error in auto_media task: {e}")
                continue

    @auto_media.before_loop
    async def before_auto_media(self):
        await self.bot.wait_until_ready()

    @staticmethod
    def get_emojis(content: str) -> Optional[List[StolenEmoji]]:
        results = re.findall(r"<(a?):(\w+):(\d{10,20})>", content)
        return [StolenEmoji(*result) for result in results]

    @staticmethod
    def available_emoji_slots(guild: discord.Guild, animated: bool):
        current_emojis = len([em for em in guild.emojis if em.animated == animated])
        return guild.emoji_limit - current_emojis

    async def steal_ctx(
        self, ctx: Context
    ) -> Optional[List[Union[StolenEmoji, discord.StickerItem]]]:
        reference = ctx.message.reference
        if not reference:
            await ctx.warn(
                "Reply to a message with this command to steal an emoji, or run ``emoji add``."
            )
            return None
        message = await ctx.channel.fetch_message(reference.message_id)
        if not message:
            await ctx.warn("I couldn't fetch that message.")
            return None
        if message.stickers:
            return message.stickers
        if not (emojis := self.get_emojis(message.content)):
            await ctx.warn("Can't find emojis or stickers in that message.")
            return None
        return emojis

    @Cog.listener("on_message_without_command")
    async def linkvertise_listener(self, ctx: Context) -> Optional[Message]:
        match = LINKVERTISE_PATTERN.search(ctx.message.content)
        if not match:
            return

        async with ctx.typing():
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="bypass.pm",
                    path="/bypass2",
                    query={"url": match.group()},
                ),
                proxy=config.CLIENT.WARP,
            )
            data = await response.json()
            if not data.get("success"):
                return await ctx.warn(
                    "Failed to get **Linkvertise** destination!", delete_after=5
                )

            return await ctx.send(data["destination"])

    @Cog.listener("on_raw_reaction_add")
    async def quote_listener(
        self,
        payload: RawReactionActionEvent,
    ) -> Optional[Message]:
        record = await self.bot.db.fetchrow(
            """
            SELECT channel_id, embeds
            FROM quoter
            WHERE guild_id = $1
            AND emoji = $2
            """,
            payload.guild_id,
            str(payload.emoji),
        )
        if not record:
            return

        guild = payload.guild_id and self.bot.get_guild(payload.guild_id)
        if not guild or guild.me.is_timed_out():
            return

        payload_channel = guild.get_channel_or_thread(payload.channel_id)
        if not isinstance(payload_channel, (TextChannel, Thread)):
            return

        channel = cast(Optional[TextChannel], guild.get_channel(record["channel_id"]))
        if not channel:
            return

        message = self.bot.get_message(payload.message_id)
        if not message:
            try:
                message = await payload_channel.fetch_message(payload.message_id)
            except HTTPException:
                return

        if message.embeds and message.embeds[0].type != "image":
            embed = message.embeds[0]
        else:
            embed = Embed(color=message.author.color)

        embed.description = embed.description or ""
        embed.timestamp = message.created_at
        embed.set_author(
            name=message.author,
            icon_url=message.author.display_avatar,
            url=message.jump_url,
        )

        if message.content:
            embed.description += f"\n{message.content}"

        if message.attachments:
            attachment = message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.proxy_url)

        files: List[File] = []
        for attachment in message.attachments:
            if (
                not attachment.content_type
                or attachment.content_type.startswith("image")
                or attachment.size > guild.filesize_limit
                or not attachment.filename.endswith(
                    ("mp4", "mp3", "mov", "wav", "ogg", "webm")
                )
            ):
                continue

            file = await attachment.to_file()
            files.append(file)

        embed.set_footer(
            text=f"#{message.channel}/{message.guild or 'Unknown Guild'}",
            icon_url=message.guild.icon if message.guild else None,
        )

        if not record["embeds"] and files:
            return await channel.send(files=files)

        return await channel.send(
            embed=embed,
            files=files,
        )

    @Cog.listener("on_guild_update")
    async def vanity_tracker(self, before: Guild, after: Guild):
        """Listener for the vanity tracker."""

        if before.vanity_url_code != after.vanity_url_code:

            for guild in self.bot.guilds:
                channel_id = await self.bot.db.fetchval(
                    """
                    SELECT vanity_channel_id 
                    FROM tracker 
                    WHERE guild_id = $1
                    """,
                    guild.id,
                )

                if channel_id:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        if after.vanity_url_code:
                            await channel.send(
                                f"Vanity ``{after.vanity_url_code}`` is now available"
                            )

        if before.vanity_url_code:

            tracking_data = await self.bot.db.fetchrow(
                """
                SELECT user_ids
                FROM track.vanity
                WHERE vanity = $1
                """,
                before.vanity_url_code.lower(),
            )

            if tracking_data and tracking_data["user_ids"]:

                for user_id in tracking_data["user_ids"]:
                    try:
                        user = self.bot.get_user(user_id)
                        log.info(f"Attempting to DM user {user_id}: {user}")

                        if user:
                            embed = Embed(
                                description=f"The vanity `{before.vanity_url_code}` you have set to track with **evict** is now available.\n> {config.EMOJIS.CONTEXT.WARN} You are receiving this message because you have setup vanity tracking with **evict**",
                            )
                            await user.send(embed=embed)
                    except Exception as e:
                        log.error(f"Failed to send DM to user {user_id}: {e}")
                        continue

    @Cog.listener("on_user_update")
    async def username_tracker(self, before: User, after: User):
        """Listener for the vanity tracker."""

        current_timestamp = int(time.time())
        future_timestamp = current_timestamp + (14 * 24 * 60 * 60)
        discord_timestamp = f"<t:{future_timestamp}:R>"

        name_key = xxh64_hexdigest("tracker")

        if before.name != after.name:
            for guild in self.bot.guilds:
                channel_id = await self.bot.db.fetchval(
                    """
                    SELECT username_channel_id 
                    FROM tracker 
                    WHERE guild_id = $1
                    """,
                    guild.id,
                )

                if channel_id:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        if await self.bot.redis.ratelimited(name_key, 3, 2):
                            await asyncio.sleep(2)
                            await channel.send(
                                    f"Username ``{before.name}`` will be available {discord_timestamp}")

        tracking_data = await self.bot.db.fetchrow(
            """
            SELECT user_ids
            FROM track.username
            WHERE username = $1
            """,
            before.name.lower(),
        )

        if tracking_data and tracking_data["user_ids"]:
            for user_id in tracking_data["user_ids"]:
                try:
                    user = self.bot.get_user(user_id)
                    if user:
                        embed = Embed(
                            description=f"The username `{before.name}` you have set to track with **evict** is now available.\n> {config.EMOJIS.CONTEXT.WARN} You are receiving this message because you have setup username tracking with **evict**",
                        )
                        await user.send(embed=embed)
                except Exception:
                    continue

    @Cog.listener("on_message_without_command")
    async def afk_listener(self, ctx: Context) -> Optional[Message]:
        if left_at := cast(
            Optional[datetime],
            await self.bot.db.fetchval(
                """
                DELETE FROM afk
                WHERE user_id = $1
                RETURNING left_at
                """,
                ctx.author.id,
            ),
        ):
            return await ctx.neutral(
                f"Welcome back, you left {format_dt(left_at, 'R')}",
                reference=ctx.message,
            )

        if len(ctx.message.mentions) == 1:
            user = ctx.message.mentions[0]
            
            rate_key = xxh64_hexdigest(f"{ctx.channel.id}:{user.id}")
            
            if await self.bot.redis.ratelimited(rate_key, 6, 60):
                return

            if record := await self.bot.db.fetchrow(
                """
                SELECT status, left_at
                FROM afk
                WHERE user_id = $1
                """,
                user.id,
            ):
                return await ctx.neutral(
                    f"{user.mention} is currently AFK: **{record['status']}** - {format_dt(record['left_at'], 'R')}",
                    reference=ctx.message,
                )

    @hybrid_command(example="be back soon", aliases=["away"])
    async def afk(
        self,
        ctx: Context,
        *,
        status: str = "AFK",
    ) -> Optional[Message]:
        """
        Set an AFK status.
        """
        await self.bot.db.execute(
                """
                INSERT INTO afk (user_id, status)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET status = EXCLUDED.status
                """,
                ctx.author.id,
                status,
            )
            
        return await ctx.approve(f"You're now **AFK** with the status **{status}**")

    @hybrid_command(
        example="en te amo",
        name="translate",
        aliases=[
            "translation",
            "tr",
        ],
    )
    async def translate(
        self,
        ctx: Context,
        destination: Annotated[
            str,
            Optional[GoogleTranslate],
        ] = "en",
        *,
        text: Annotated[
            Optional[str],
            clean_content,
        ] = None,
    ) -> Message:
        """
        Translate text with Google Translate.
        This is an alias for the `google translate` command.
        """

        return await self.google_translate(
            ctx,
            destination=destination,
            text=text,
        )

    @command(
        aliases=[
            "rimg",
            "sauce",
        ]
    )
    async def reverse(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Reverse search an image on Google.
        This is an alias for the `google reverse` command.
        """

        return await self.google_reverse(ctx, attachment=attachment)

    @hybrid_group(
        example="divinity",
        aliases=["g", "ddg"],
        invoke_without_command=True,
    )
    @cooldown(3, 60, BucketType.user)
    async def google(self, ctx: Context, *, query: str) -> Message:
        """
        Search a query on Google.
        """

        async with ctx.typing():
            data = await Google.search(
                self.bot.session,
                query,
            )
            if not data.results:
                return await ctx.warn(f"No results found for **{query}**!")

        fields: List[dict] = []
        embed = Embed(
            title=(
                f"{data.header}"
                + (f" - {data.description}" if data.description else "")
                if data.header
                else f"Google Search - {query}"
            ),
        )
        if panel := data.panel:
            if panel.source:
                embed.url = panel.source.url

            embed.description = shorten(panel.description, 200)

            for item in panel.items:
                if not embed.description:
                    embed.description = ""

                embed.description += f"\n> **{item.name}:** `{item.value}`"

        for result in data.results:
            if any(result.title in field["name"] for field in fields):
                continue

            snippet = result.snippet or (".." if not result.tweets else "")
            for highlight in result.highlights:
                snippet = snippet.replace(highlight, f"**{highlight}**")

            fields.append(
                dict(
                    name=f"**{result.title}**",
                    value=(
                        f"**{result.url.split('?', 1)[0]}**\n{shorten(snippet, 200)}"
                        + (
                            "\n"
                            if result.extended_links or result.tweets and snippet
                            else ""
                        )
                        + "\n".join(
                            [
                                f"> [`{extended.title}`]({extended.url}): {textwrap.shorten(extended.snippet or '...', 46, placeholder='..')}"
                                for extended in result.extended_links
                            ]
                        )
                        + "\n".join(
                            [
                                f"> [`{textwrap.shorten(tweet.text, 46, placeholder='..')}`]({tweet.url}) **{tweet.footer}**"
                                for tweet in result.tweets[:3]
                            ]
                        )
                    ),
                    inline=False,
                )
            )

        paginator = Paginator(
            ctx,
            entries=fields,
            embed=embed,
            per_page=3,
        )
        return await paginator.start()

    @google.command(
        example="en te amo",
        name="translate",
        aliases=[
            "translation",
            "tr",
        ],
    )
    async def google_translate(
        self,
        ctx: Context,
        destination: Annotated[
            str,
            Optional[GoogleTranslate],
        ] = "en",
        *,
        text: Annotated[
            Optional[str],
            clean_content,
        ] = None,
    ) -> Message:
        """
        Translate text with Google Translate.
        """

        if not text:
            reply = ctx.replied_message
            if reply and reply.content:
                text = reply.clean_content
            else:
                return await ctx.send_help(ctx.command)

        async with ctx.typing():
            result = await GoogleTranslate.translate(
                self.bot.session,
                text,
                target=destination,
            )

        embed = Embed(title="Google Translate")
        embed.add_field(
            name=f"**{result.source_language} to {result.target_language}**",
            value=result.translated,
            inline=False,
        )

        return await ctx.send(embed=embed)

    @google.command(
        example="jake paul",
        name="youtube",
        aliases=["yt"],
    )
    async def google_youtube(self, ctx: Context, *, query: str) -> Message:
        """
        Search a query on YouTube.
        """

        async with ctx.typing():
            results = await YouTubeVideo.search(self.bot.session, query)
            if not results:
                return await ctx.warn(f"No videos found for **{query}**!")

            paginator = Paginator(
                ctx,
                entries=[result.url for result in results],
            )
            return await paginator.start()

    @google.command(
        name="reverse",
        aliases=["rimg", "sauce"],
    )
    @cooldown(1, 10, BucketType.user)
    async def google_reverse(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Reverse search an image on Google.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        async with ctx.typing():
            classes: Dict[str, str | Pattern[str]] = {
                "description": compile("VwiC3b yXK7lf"),
                "result": "srKDX cvP2Ce",
                "related": "fKDtNb",
            }
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="www.google.com",
                    path="/searchbyimage",
                    query={
                        "safe": "off" if ctx.channel.is_nsfw() else "on",
                        "sbisrc": "tg",
                        "image_url": attachment.url,
                    },
                ),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
                        "Gecko/20100101 Firefox/111.0"
                    )
                },
            )
            content = await response.text()

            data = BeautifulSoup(content, "lxml")
            related = data.find("a", class_=classes["related"])
            results = data.findAll("div", class_=classes["result"])
            if not related or not results:
                return await ctx.warn(
                    f"No results were found for [`{attachment.filename}`]({attachment.url})!"
                )

        embed = Embed(
            title="Reverse Image Search",
            description=f"*`{related.text}`*",
        )
        embed.set_thumbnail(url=attachment.url)
        if stats := data.find("div", id="result-stats"):
            embed.set_footer(text=stats.text)

        for result in results[:3]:
            link = result.a.get("href")
            title = result.find("h3").text
            description = (
                result.find("div", class_=classes["description"])
                .findAll("span")[-1]
                .text
            )

            embed.add_field(
                name=title,
                value=f"[`{shorten(description, 65)}`]({link})",
                inline=False,
            )

        return await ctx.send(embed=embed)

        # @command(
        #     aliases=["recognize", "find"]
        # )
        # @max_concurrency(1, wait=True)
        # @cooldown(1, 5, BucketType.guild)
        # async def shazam(
        # self,
        # ctx: Context,
        # attachment: PartialAttachment = parameter(
        #    default=PartialAttachment.fallback,
        # ),
        # ) -> Message:
        """
        Recognize a song from an attachment.
        """

    #  if not attachment.is_video() and not attachment.is_audio():
    #     return await ctx.warn("The attachment must be a video!")

    # async with ctx.typing():
    #     data = await self.shazamio.recognize_song(attachment.buffer)
    #     output = ShazamSerialize.full_track(data)

    # if not (track := output.track):
    # return await ctx.warn(
    #     f"No tracks were found from [`{attachment.filename}`]({attachment.url})!"
    #  )

    # return await ctx.approve(
    # f"Found [**{track.title}**]({track.shazam_url}) "
    #  f"by [*`{track.subtitle}`*]({URL(f'https://google.com/search?q={track.subtitle}')})"
    # )

    @donator()
    @hybrid_command(
        example="what time is it in new zealand", aliases=["ai", "ask", "gemini"]
    )
    async def chatgpt(self, ctx: Context, *, question: str) -> Optional[Message]:
        """
        Ask AI a question.
        """

        async with ctx.typing():
            response = await self.bot.session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": question}]
                }
            )

            if response.status != 200:
                return await ctx.warn("Failed to get a response from OpenAI API!")

            data = await response.json()
            if not data.get("choices"):
                return await ctx.warn("No response was found for that question!")

            await ctx.send(data["choices"][0]["message"]["content"])

    @hybrid_command(aliases=["w"])
    async def wolfram(
        self,
        ctx: Context,
        *,
        question: str,
    ) -> Message:
        """
        Solve a question with Wolfram Alpha.
        """

        async with ctx.typing():
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="api.wolframalpha.com",
                    path="/v1/result",
                    query={
                        "i": question,
                        "appid": AUTHORIZATION.WOLFRAM,
                    },
                ),
            )
            if not response.ok:
                return await ctx.warn("No solution was found for that question!")

            content = await response.read()

        return await ctx.send(content.decode("utf-8"))

    @hybrid_command(aliases=["char"])
    async def charinfo(self, ctx: Context, *, characters: str) -> Message:
        """
        View unicode characters.
        """

        def to_string(char: str):
            digit = f"{ord(char):x}"
            name = unicodedata.name(char, "Unknown")

            return f"[`\\U{digit:>08}`](http://www.fileformat.info/info/unicode/char/{digit}): {name}"

        paginator = Paginator(
            ctx,
            entries=list(map(to_string, characters)),
            embed=Embed(
                title="Character Information",
            ),
            per_page=5,
            counter=False,
        )
        return await paginator.start()

    @hybrid_group(
        name="hash",
        invoke_without_command=True,
    )
    async def _hash(self, ctx: Context) -> Message:
        """
        Hash a string with a given algorithm.
        """

        hash_methods = human_join(
            [
                f"`{command.name}`"
                for command in sorted(
                    self._hash.commands,
                    key=lambda command: command.name,
                    reverse=True,
                )
            ]
        )

        return await ctx.neutral(
            f"Please specify a valid hash algorithm to use!\n{hash_methods}"
        )

    @_hash.command(name="xxh32")
    async def _hash_xxh32(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the XXH32 algorithm.
        """

        hashed = xxh32_hexdigest(text)

        embed = Embed(
            title="XXH32 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="xxh64")
    async def _hash_xxh64(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the XXH64 algorithm.
        """

        hashed = xxh64_hexdigest(text)

        embed = Embed(
            title="XXH64 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="xxh128")
    async def _hash_xxh128(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the XXH128 algorithm.
        """

        hashed = xxh128_hexdigest(text)

        embed = Embed(
            title="XXH128 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha1")
    async def _hash_sha1(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA1 algorithm.
        """

        hashed = sha1(text.encode()).hexdigest()

        embed = Embed(
            title="SHA1 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha224")
    async def _hash_sha224(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA224 algorithm.
        """

        hashed = sha224(text.encode()).hexdigest()

        embed = Embed(
            title="SHA224 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha256")
    async def _hash_sha256(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA256 algorithm.
        """

        hashed = sha256(text.encode()).hexdigest()

        embed = Embed(
            title="SHA256 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha384")
    async def _hash_sha384(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA384 algorithm.
        """

        hashed = sha384(text.encode()).hexdigest()

        embed = Embed(
            title="SHA384 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha512")
    async def _hash_sha512(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA512 algorithm.
        """

        hashed = sha512(text.encode()).hexdigest()

        embed = Embed(
            title="SHA512 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @hybrid_group(
        aliases=["bday", "bd"],
        invoke_without_command=True,
    )
    async def birthday(
        self,
        ctx: Context,
        *,
        member: Member = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View your birthday.
        """

        birthday = cast(
            Optional[datetime],
            await self.bot.db.fetchval(
                """
                SELECT birthday
                FROM birthdays
                WHERE user_id = $1
                """,
                member.id,
            ),
        )
        if not birthday:
            if member == ctx.author:
                return await ctx.warn(
                    "You haven't set your birthday yet!",
                    f"Use `{ctx.clean_prefix}birthday set <date>` to set it",
                )

            return await ctx.warn(f"**{member}** hasn't set their birthday yet!")

        current = utcnow()
        next_birthday = current.replace(
            year=current.year + 1,
            month=birthday.month,
            day=birthday.day,
        )
        if next_birthday.day == current.day and next_birthday.month == current.month:
            phrase = "**today**, happy birthday! 🎊"
        elif (
            next_birthday.day + 1 == current.day
            and next_birthday.month == current.month
        ):
            phrase = "**tomorrow**, happy early birthday! 🎊"
        else:
            days_until_birthday = (next_birthday - current).days
            if days_until_birthday > 365:
                next_birthday = current.replace(
                    year=current.year,
                    month=birthday.month,
                    day=birthday.day,
                )
                days_until_birthday = (next_birthday - current).days

            phrase = f"**{next_birthday.strftime('%B')} {ordinal(next_birthday.day)}**, that's {format_dt(next_birthday, 'R')}"

        return await ctx.neutral(
            f"Your birthday is {phrase}"
            if member == ctx.author
            else f"**{member}**'s birthday is {phrase}"
        )

    @birthday.command(example="jan 13", name="set")
    async def birthday_set(
        self,
        ctx: Context,
        *,
        date: str,
    ) -> Message:
        """
        Set your birthday
        """

        birthday = dateparser.parse(date)
        if not birthday:
            return await ctx.warn(f"Date not found for **{date}**")

        await self.bot.db.execute(
            """
            INSERT INTO birthdays (user_id, birthday)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET birthday = EXCLUDED.birthday
            """,
            ctx.author.id,
            birthday,
        )
        return await ctx.approve(
            f"Your birthday has been set to **{birthday:%B} {ordinal(birthday.strftime('%-d'))}**"
        )

    @hybrid_group(
        aliases=["time", "tz"],
        invoke_without_command=True,
    )
    async def timezone(
        self,
        ctx: Context,
        *,
        member: Member = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View your local time.
        """

        timezone = cast(
            Optional[str],
            await self.bot.db.fetchval(
                """
                SELECT timezone
                FROM timezones
                WHERE user_id = $1
                """,
                member.id,
            ),
        )
        if not timezone:
            if member == ctx.author:
                return await ctx.warn(
                    "You haven't set your timezone yet!",
                    f"Use `{ctx.clean_prefix}timezone set <location>` to set it",
                )

            return await ctx.warn(f"**{member}** hasn't set their timezone yet!")

        timestamp = utcnow().astimezone(gettz(timezone))
        return await ctx.neutral(
            f"It's currently **{timestamp.strftime('%B %d, %I:%M %p')}** "
            + ("for you" if member == ctx.author else f"for {member.mention}")
        )

    @timezone.command(example="indianapolis", name="set")
    async def timezone_set(
        self,
        ctx: Context,
        *,
        timezone: Annotated[
            str,
            Timezone,
        ],
    ) -> Message:
        """
        Set your local timezone.
        """

        await self.bot.db.execute(
            """
            INSERT INTO timezones (user_id, timezone)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET timezone = EXCLUDED.timezone
            """,
            ctx.author.id,
            timezone,
        )
        return await ctx.approve(f"Your timezone has been set to `{timezone}`")

    @hybrid_group()
    async def variables(self, ctx: Context):
        await ctx.neutral("Variables are not currently up, see temporary variables: https://docs.greed.best/overview/variables")

    @command(aliases=["parse", "ce"], example="{embed}$v{description: @x}")
    @has_permissions(manage_messages=True)
    async def embed(self, ctx: Context, *, script: EmbedScript) -> Message:
        """
        Parse a script into an embed.
        """

        if script is None:
            if ctx.message.attachments:
                script = await EmbedJson.embed_json(
                    ctx.author, ctx.message.attachments[0]
                )
            else:
                return await ctx.send_help(ctx.command)

        await ctx.send(**script)

    @command(example="1287575466152300566", aliases=["embedcode", "ec"])
    async def copyembed(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Message:
        """
        Copy a script from a message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        script = Script.from_message(message)
        if not script:
            return await ctx.warn(
                f"That [`message`]({message.jump_url}) doesn't have any content!"
            )

        return await ctx.send(codeblock(script.template))

    @group(
        aliases=["quoter"],
        invoke_without_command=True,
    )
    async def quote(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Message:
        """
        Repost a message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        channel_id = await self.bot.db.fetchval(
            """SELECT channel_id 
            FROM quoter WHERE 
            guild_id = $1""",
            ctx.guild.id,
        )

        if not channel_id:
            return await ctx.warn("Quoting channel not set for this server.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.warn("The quoting channel does not exist.")

        if not channel.permissions_for(ctx.author).view_channel:
            return await ctx.warn("You don't have access to that channel!")

        if message.embeds and message.embeds[0].type != "image":
            embed = message.embeds[0]
        else:
            embed = Embed(color=message.author.color)

        embed.description = embed.description or ""
        embed.timestamp = message.created_at
        embed.set_author(
            name=str(message.author),
            icon_url=message.author.display_avatar.url,
            url=message.jump_url,
        )

        if message.content:
            embed.description += f"\n{message.content}"

        files: List[File] = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.proxy_url)
            elif (
                attachment.size <= ctx.guild.filesize_limit
                and attachment.filename.endswith(
                    ("mp4", "mp3", "mov", "wav", "ogg", "webm")
                )
            ):
                file = await attachment.to_file()
                files.append(file)

        embed.set_footer(
            text=f"#{message.channel.name}/{message.guild.name if message.guild else 'Unknown Guild'}",
            icon_url=message.guild.icon.url if message.guild else None,
        )

        await ctx.check()
        return await channel.send(
            embed=embed,
            files=files,
        )

    @quote.command(name="channel")
    @has_permissions(manage_messages=True)
    async def quote_channel(self, ctx: Context, *, channel: TextChannel) -> Message:
        """
        Set the quote relay channel.
        """

        await self.bot.db.execute(
            """
            INSERT INTO quoter (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET channel_id = EXCLUDED.channel_id
            """,
            ctx.guild.id,
            channel.id,
        )
        return await ctx.approve(f"Now relaying quoted messages to {channel.mention}")

    @quote.command(name="emoji", aliases=["set"])
    @has_permissions(manage_messages=True)
    async def quote_emoji(self, ctx: Context, emoji: str) -> Message:
        """
        Set the quote emoji to detect.
        """

        try:
            await ctx.message.add_reaction(emoji)
        except (HTTPException, TypeError):
            return await ctx.warn(
                f"I'm not able to use **{emoji}**",
                "Try using an emoji from this server",
            )

        await self.bot.db.execute(
            """
            INSERT INTO quoter (guild_id, emoji)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET emoji = EXCLUDED.emoji
            """,
            ctx.guild.id,
            emoji,
        )
        return await ctx.approve(f"Now watching for {emoji} on messages")

    @quote.command(name="embeds", aliases=["embed"])
    @has_permissions(manage_messages=True)
    async def quote_embeds(self, ctx: Context) -> Message:
        """
        Toggle if quoted messages will have an embed.
        """

        status = cast(
            bool,
            await self.bot.db.fetchval(
                """
                INSERT INTO quoter (guild_id)
                VALUES ($1)
                ON CONFLICT (guild_id)
                DO UPDATE SET embeds = NOT quoter.embeds
                RETURNING embeds
                """,
                ctx.guild.id,
            ),
        )

        return await ctx.approve(
            f"{'Now' if status else 'No longer'} displaying **embeds** for relayed messages"
        )

    @command(
        example="divinity",
        aliases=[
            "dictionary",
            "define",
            "urban",
            "ud",
        ],
    )
    async def urbandictionary(
        self,
        ctx: Context,
        *,
        word: str,
    ) -> Message:
        """
        Define a word with Urban Dictionary.
        """

        async with ctx.typing():
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="api.urbandictionary.com",
                    path="/v0/define",
                    query={
                        "term": word,
                    },
                ),
            )
            data = await response.json()
            if not data["list"]:
                return await ctx.warn(f"No definitions found for **{word}**!")

        embeds: List[Embed] = []
        for result in data["list"]:
            embed = Embed(
                url=result["permalink"],
                title=result["word"],
                description=re.sub(
                    r"\[(.*?)\]",
                    lambda m: f"[{m[1]}](https://www.urbandictionary.com/define.php?term={quote_plus(m[1])})",
                    result["definition"],
                )[:4096],
            )

            embed.add_field(
                name="**Example**",
                value=re.sub(
                    r"\[(.*?)\]",
                    lambda m: f"[{m[1]}](https://www.urbandictionary.com/define.php?term={quote_plus(m[1])})",
                    result["example"],
                )[:1024],
            )
            embeds.append(embed)

        paginator = Paginator(
            ctx,
            entries=embeds,
        )
        return await paginator.start()

    @command(aliases=["dom", "hex"])
    async def dominant(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Extract the dominant color from an image.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        color = await dominant_color(attachment.buffer)
        image_url = f"https://place-hold.it/250x250/{str(color).strip('#')}?text=%20"
        return await ctx.neutral(
            f"The dominant color is [**{color}**]({image_url})",
            color=color,
        )

    @command()
    async def upload(
        self,
        ctx: Context,
        attachment: Attachment = parameter(
            default=lambda ctx: (
                ctx.message.attachments[0] if ctx.message.attachments else None
            ),
        ),
    ) -> Message:
        """
        Upload a file to Kraken Files.
        """

        if not attachment:
            return await ctx.warn("No attachment found!")

        async with ctx.typing():
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="krakenfiles.com",
                    path="/api/server/available",
                ),
            )
            data = await response.json()

            if not data["data"]:
                return await ctx.warn(
                    "No available servers to upload file. Try again later!"
                )

            buffer = await attachment.read()

            server = data["data"]
            form = FormData(
                {
                    "file": buffer,
                    "filename": attachment.filename,
                    "serverAccessToken": server["serverAccessToken"],
                }
            )
            response = await self.bot.session.post(
                server["url"],
                data=form,
                headers={"X-AUTH-TOKEN": config.AUTHORIZATION.KRAKEN},
            )
            data = await response.json()
            if not data["data"]:
                return await ctx.warn(
                    "Please try again, the serverAccessToken has already been used!"
                )

            return await ctx.neutral(data["data"]["url"])

    @command(aliases=["ss"])
    @cooldown(1, 5, BucketType.guild)
    async def screenshot(
        self, 
        ctx: Context, 
        url: str, 
        *, 
        flags: ScreenshotFlags
    ) -> Message:
        """
        Capture a screenshot of a webpage and perform content moderation.
        """
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        async with ctx.typing():
            async with ctx.bot.browser.borrow_page() as page:
                await page.emulate_media(color_scheme="dark")
                await page.goto(
                    url, 
                    timeout=60000, 
                    wait_until="load",
                )
                if flags.wait > 0:
                    await asyncio.sleep(flags.wait)
                screenshot = await page.screenshot(full_page=flags.full_page)
                await page.close()

        nparr = numpy.frombuffer(screenshot, numpy.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        result = self.nude_detector.detect(img)

        if result:
            return await ctx.warn(
                "The screenshot contains potentially unsafe content and cannot be displayed."
            )

        return await ctx.send(
            file=File(BytesIO(screenshot), filename="evict-screenshot.png")
        )

    @command()
    @has_permissions(manage_messages=True)
    async def embedsetup(self, ctx: Context):
        """Create an embed using buttons and return an embed code"""
        embed = Embed(description="Create an embed")
        view = EmbedBuilding(ctx)
        return await ctx.send(embed=embed, view=view)

    @command(
        description="reply to a message to steal an emoji or sticker",
    )
    @has_permissions(manage_expressions=True)
    async def steal(self, ctx: Context, *names: str):
        "Reply to a message to steal an emoji or sticker."

        if not (emojis := await self.steal_ctx(ctx)):
            return

        if isinstance(emojis[0], discord.StickerItem):
            if len(ctx.guild.stickers) >= ctx.guild.sticker_limit:
                return await ctx.warn("there are no more sticker slots.")

            sticker = emojis[0]
            fp = io.BytesIO()

            try:
                await sticker.save(fp)
                await ctx.guild.create_sticker(
                    name=sticker.name,
                    description=STICKER_DESC,
                    emoji=STICKER_EMOJI,
                    file=discord.File(fp),
                    reason=f"uploaded by {ctx.author}",
                )

            except Exception as error:
                return await ctx.warn(
                    f"{STICKER_FAIL}, {type(error).__name__}: {error}"
                )
            return await ctx.approve(f"{STICKER_SUCCESS}: {sticker.name}")

        names = ["".join(re.findall(r"\w+", name)) for name in names]
        names = [name if len(name) >= 2 else None for name in names]
        emojis = list(dict.fromkeys(emojis))

        async with aiohttp.ClientSession() as session:
            for emoji, name in zip_longest(emojis, names):
                if not self.available_emoji_slots(ctx.guild, emoji.animated):
                    return await ctx.warn(EMOJI_SLOTS)
                if not emoji:
                    break
                try:
                    async with session.get(emoji.url) as resp:
                        image = io.BytesIO(await resp.read()).read()
                    added = await ctx.guild.create_custom_emoji(
                        name=name or emoji.name,
                        image=image,
                        reason=f"uploaded by {ctx.author}",
                    )
                except Exception as error:
                    return await ctx.warn(
                        f"{EMOJI_FAIL} {emoji.name}, {type(error).__name__}: {error}"
                    )
                try:
                    await ctx.message.add_reaction(added)
                except:
                    pass

    @group(invoke_without_command=True)
    async def notify(self, ctx: Context):
        """Manage notifications for vanities and usernames."""
        await ctx.send_help(ctx.command)

    @notify.command(name="add")
    async def notify_add(
        self, ctx: Context, type: Literal["vanity", "username"], desired: str
    ):
        """Add a notification for a vanity or username."""

        desired = desired.lower().strip()
        table = f"track.{type}"

        confirmation_message = (
            f"Are you sure you would like evict to notify you if the {type} `{desired}` is available?\n"
            f"> By agreeing, you allow evict to send you a direct message if the set {type} is available"
        )

        confirmed = await ctx.prompt(confirmation_message)

        if not confirmed:
            return await ctx.neutral("Notification setup cancelled.")

        await self.bot.db.execute(
            f"""
            INSERT INTO {table} ({type}, user_ids)
            VALUES ($1, ARRAY[$2]::BIGINT[])
            ON CONFLICT ({type}) 
            DO UPDATE SET user_ids = 
                CASE 
                    WHEN $2 = ANY({table}.user_ids) THEN {table}.user_ids
                    ELSE array_append({table}.user_ids, $2::BIGINT)
                END
            """,
            desired,
            ctx.author.id,
        )

        await ctx.approve(
            f"You will be notified if the {type} `{desired}` becomes available."
        )

    @notify.command(name="list")
    async def notify_list(self, ctx: Context):
        """List your active notifications."""

        vanities = await self.bot.db.fetch(
            """
            SELECT vanity
            FROM track.vanity
            WHERE $1 = ANY(user_ids)
            """,
            ctx.author.id,
        )

        usernames = await self.bot.db.fetch(
            """
            SELECT username
            FROM track.username
            WHERE $1 = ANY(user_ids)
            """,
            ctx.author.id,
        )

        if not vanities and not usernames:
            return await ctx.warn("You don't have any active notifications.")

        embed = discord.Embed(title="Your Active Notifications")

        if vanities:
            vanity_list = ", ".join(f"`{v['vanity']}`" for v in vanities)
            embed.add_field(name="Vanities", value=vanity_list, inline=True)

        if usernames:
            username_list = ", ".join(f"`{u['username']}`" for u in usernames)
            embed.add_field(name="Usernames", value=username_list, inline=True)

        await ctx.send(embed=embed)

    @notify.command(name="remove")
    async def notify_remove(
        self, ctx: Context, type: Literal["vanity", "username"], desired: str
    ):
        """Remove a notification for a vanity or username."""

        desired = desired.lower().strip()
        table = f"track.{type}"

        result = await self.bot.db.execute(
            f"""
            UPDATE {table}
            SET user_ids = array_remove(user_ids, $2::BIGINT)
            WHERE {type} = $1 AND $2 = ANY(user_ids)
            """,
            desired,
            ctx.author.id,
        )

        await self.bot.db.execute(
            f"""
            DELETE FROM {table} 
            WHERE array_length(user_ids, 1) IS NULL
            """
        )

        if result == "UPDATE 0":
            return await ctx.warn(f"You weren't tracking the {type} `{desired}`.")

        await ctx.approve(f"Removed notification for {type} `{desired}`.")

    @group(name="tracker", invoke_without_command=True)
    async def tracker(self, ctx: Context):
        await ctx.send_help(ctx.command)

    @tracker.group(name="vanity", invoke_without_command=True)
    async def tracker_vanity(self, ctx: Context):
        """Send available vanities to a specified channel."""
        await ctx.send_help(ctx.command)

    @has_permissions(manage_channels=True)
    @tracker_vanity.command(name="channel")
    async def tracker_vanity_channel(
        self, ctx: Context, channel: Optional[TextChannel]
    ):
        """Send available vanities to a specified channel."""

        if channel is None:
            channel = ctx.channel

        await self.bot.db.execute(
            """
            INSERT INTO tracker (guild_id, vanity_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET vanity_channel_id = EXCLUDED.vanity_channel_id
            """,
            ctx.guild.id,
            channel.id,
        )

        await ctx.approve(f"Now sending available vanities to {ctx.channel.mention}.")

    @has_permissions(manage_channels=True)
    @tracker_vanity.command(name="remove")
    async def tracker_vanity_remove(self, ctx: Context):
        """Remove the vanity tracking."""

        channel_id = await self.bot.db.fetchval(
            """
            SELECT vanity_channel_id 
            FROM tracker 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if channel_id is None:
            await ctx.warn("There is no vanity tracker set for this guild!")
            return

        await self.bot.db.execute(
            """
            UPDATE tracker
            SET vanity_channel_id = NULL 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        await ctx.approve("Removed the vanity tracker!")

    @tracker.group(name="usernames", aliases=["users"], invoke_without_command=True)
    async def tracker_usernames(self, ctx: Context):
        """Send available usernames to a specified channel."""
        await ctx.send_help(ctx.command)

    @has_permissions(manage_channels=True)
    @tracker_usernames.command(name="channel")
    async def tracker_usernames_channel(
        self, ctx: Context, channel: Optional[TextChannel]
    ):
        """Send available usernames to a specified channel."""

        if channel is None:
            channel = ctx.channel

        await self.bot.db.execute(
            """
            INSERT INTO tracker (guild_id, username_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET username_channel_id = EXCLUDED.username_channel_id
            """,
            ctx.guild.id,
            channel.id,
        )

        await ctx.approve(f"Now sending available usernames to {ctx.channel.mention}.")

    @has_permissions(manage_channels=True)
    @tracker_usernames.command(name="remove")
    async def tracker_username_remove(self, ctx: Context):
        """Remove the username tracking."""

        channel_id = await self.bot.db.fetchval(
            """
            SELECT username_channel_id 
            FROM tracker 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if channel_id is None:
            await ctx.warn("There is no username tracker set for this guild!")
            return

        await self.bot.db.execute(
            """
            UPDATE tracker
            SET username_channel_id = NULL 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        await ctx.approve("Removed the username tracker!")

    @group(invoke_without_command=True)
    async def profile(self, ctx: Context):
        """Profile media management commands."""
        return await ctx.send_help(ctx.command)

    @has_permissions(manage_guild=True)
    @profile.command(name="add")
    async def profile_add(self, ctx: Context, channel: TextChannel, media_type: str, category: str):
        """
        Set up automatic media for a channel.
        """
        media_type = media_type.lower()
        category = category.lower()

        if media_type in ("pfp", "pfps", "avatars", "avs"):
            media_type = "pfp"
            valid_categories = ["random", "anime", "cats", "egirls", "girls", "boys"]
        elif media_type in ("banner", "banners"):
            media_type = "banner"
            valid_categories = ["random", "anime", "cute", "imsg", "mix"]
            banner_case_map = {
                "anime": "Anime",
                "cute": "Cute",
                "imsg": "Imsg",
                "mix": "Mix",
                "random": "random"
            }
        else:
            return await ctx.warn("Invalid media type. Choose `banner` or `pfp`.")

        if category not in valid_categories:
            categories = ", ".join(f"`{c}`" for c in valid_categories)
            return await ctx.warn(f"Invalid category for {media_type}. Choose from: {categories}")

        if media_type == "banner":
            category = banner_case_map[category]

        await self.bot.db.execute(
            """
            INSERT INTO auto.media (guild_id, channel_id, type, category)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, channel_id, type)
            DO UPDATE SET category = EXCLUDED.category
            """,
            ctx.guild.id,
            channel.id,
            media_type,
            category
        )

        return await ctx.approve(f"Now sending automatic {media_type}s with category **{category}** to {channel.mention}")

    @profile.command(name="remove")
    async def profile_remove(self, ctx: Context, channel: TextChannel, media_type: str):
        """
        Remove automatic media from a channel.
        """
        media_type = media_type.lower()
        
        if media_type in ("pfp", "pfps", "avatars", "avs"):
            media_type = "pfp"
        elif media_type in ("banner", "banners"):
            media_type = "banner"
        else:
            return await ctx.warn("Invalid media type. Choose `banner` or `pfp`.")

        result = await self.bot.db.execute(
            """
            DELETE FROM auto.media
            WHERE guild_id = $1 AND channel_id = $2 AND type = $3
            """,
            ctx.guild.id,
            channel.id,
            media_type
        )

        if result == "DELETE 0":
            return await ctx.warn(f"No {media_type} automation found for {channel.mention}")

        return await ctx.approve(f"Removed {media_type} automation from {channel.mention}")

    @profile.command(name="list")
    async def profile_list(self, ctx: Context):
        """
        List all automatic media configurations.
        """
        data = await self.bot.db.fetch(
            """
            SELECT channel_id, type, category
            FROM auto.media
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        if not data:
            return await ctx.warn("No automatic media configurations found.")

        entries = []
        for record in data:
            channel = ctx.guild.get_channel(record['channel_id'])
            if channel:
                entries.append(
                    f"{channel.mention}: **{record['type']}** ({record['category']})"
                )

        embed = discord.Embed(
            title="Automatic Media Configurations",
            description="\n".join(entries) if entries else "No active configurations"
        )

        return await ctx.send(embed=embed)

    @hybrid_command()
    async def avreport(self, ctx: Context, image_id: str, category: str):
        """Report an inappropriate image."""
        report_channel = self.bot.get_channel(1309178072657821808)
        if not report_channel:
            return await ctx.warn("Report channel not found.")

        embed = discord.Embed(
            title="Image Report",
            description=f"Image ID: `{image_id}`\nCategory: `{category}`",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="Reporter Information",
            value=f"User: {ctx.author} (`{ctx.author.id}`)\nGuild: {ctx.guild.name} (`{ctx.guild.id}`)"
        )
        
        embed.set_footer(text=f"Reported at {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        await report_channel.send(embed=embed)
        return await ctx.approve("Image has been reported to the staff team.")

    @group(aliases=["tra"], invoke_without_command=True)
    async def transcribe(self, ctx: Context) -> Message:
        """
        Transcribe audio from a file or message.
        """
        try:
            from pydub.utils import which

            if which("ffmpeg") is None or which("ffprobe") is None:
                return await ctx.warn(
                    "There was an ffmpeg error, please contact the developers."
                )

            attachment = None
            if ctx.message.attachments:
                attachment = ctx.message.attachments[0]
            elif ctx.replied_message and ctx.replied_message.attachments:
                attachment = ctx.replied_message.attachments[0]

            if not attachment:
                return await ctx.send_help(ctx.command)

            if not (
                attachment.filename.endswith((".mp3", ".wav", ".ogg", ".m4a"))
                or (
                    attachment.content_type
                    and "audio/ogg" in attachment.content_type
                    and attachment.filename.startswith("voice-message-")
                )
            ):
                return await ctx.warn("The file must be an audio file!")

            if attachment.size > 15_000_000:  # 15 mb cuh
                return await ctx.warn("The file must be under 15MB!")

            duration = await self.get_audio_duration(attachment.url)
            if duration > 90:  # 1:30
                return await ctx.warn(
                    "The audio must be under 1 minute and 30 seconds!"
                )

            async with ctx.typing():
                try:
                    transcript = await self.transcribe_audio(attachment.url)
                    return await ctx.approve(f"{transcript}")
                except Exception as e:
                    return await ctx.warn(f"Failed to transcribe audio: {e}")

        except Exception as e:
            return await ctx.warn(f"An error occurred: {e}")

    @transcribe.command(name="add")
    @has_permissions(manage_guild=True)
    async def transcribe_add(self, ctx: Context, channel: TextChannel) -> Message:
        """
        Add a channel for auto-transcription.
        """
        count = await self.bot.db.fetchval(
            """
            SELECT COUNT(*)
            FROM transcribe.channels
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if count >= 5:
            return await ctx.warn("You can only have 5 auto-transcribe channels!")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO transcribe.channels (guild_id, channel_id)
                VALUES ($1, $2)
                """,
                ctx.guild.id,
                channel.id,
            )
            return await ctx.approve(
                f"Added {channel.mention} to auto-transcribe channels!"
            )
        except Exception:
            return await ctx.warn(
                f"{channel.mention} is already an auto-transcribe channel!"
            )

    @transcribe.command(name="remove")
    @has_permissions(manage_guild=True)
    async def transcribe_remove(self, ctx: Context, channel: TextChannel) -> Message:
        """
        Remove a channel from auto-transcription.
        """
        deleted = await self.bot.db.execute(
            """
            DELETE FROM transcribe.channels
            WHERE guild_id = $1 AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )

        if not deleted:
            return await ctx.warn(
                f"{channel.mention} is not an auto-transcribe channel!"
            )

        return await ctx.approve(
            f"Removed {channel.mention} from auto-transcribe channels!"
        )

    @transcribe.command(name="list")
    async def transcribe_list(self, ctx: Context) -> Message:
        """
        List all auto-transcribe channels.
        """
        channels = await self.bot.db.fetch(
            """
            SELECT channel_id
            FROM transcribe.channels
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not channels:
            return await ctx.warn("No auto-transcribe channels set!")

        return await ctx.neutral(
            "Auto-transcribe channels:\n"
            + "\n".join(
                f"> {self.bot.get_channel(record['channel_id']).mention}"
                for record in channels
            )
        )

    @transcribe.command(name="clear")
    @has_permissions(manage_guild=True)
    async def transcribe_clear(self, ctx: Context) -> Message:
        """
        Clear all auto-transcribe channels.
        """
        if not await ctx.prompt(
            "Are you sure you want to clear all auto-transcribe channels?"
        ):
            return await ctx.warn("Action cancelled.")

        await self.bot.db.execute(
            """
            DELETE FROM transcribe.channels
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        return await ctx.approve("Cleared all auto-transcribe channels!")

    async def get_audio_duration(self, url: str) -> float:
        """Get duration of audio file in seconds and trim silence."""
        async with self.bot.session.get(url) as resp:
            if resp.status != 200:
                raise ValueError("Failed to download audio file")

            data = await resp.read()
            with io.BytesIO(data) as bio:
                audio = await asyncio.to_thread(AudioSegment.from_file, bio)

                chunks = await asyncio.to_thread(
                    lambda: detect_nonsilent(
                        audio,
                        min_silence_len=500,
                        silence_thresh=-40,
                    )
                )

                if not chunks:
                    return 0

                non_silent_audio = AudioSegment.empty()
                for start, end in chunks:
                    non_silent_audio += audio[start:end]

                return len(non_silent_audio) / 1000

    async def transcribe_audio(self, url: str) -> str:
        """Transcribe audio file using Whisper API."""
        async with self.bot.session.get(url) as resp:
            if resp.status != 200:
                raise ValueError("Failed to download audio file")

            data = await resp.read()
            with io.BytesIO(data) as bio:
                audio = await asyncio.to_thread(AudioSegment.from_file, bio)

                chunks = await asyncio.to_thread(
                    lambda: detect_nonsilent(
                        audio,
                        min_silence_len=500,
                        silence_thresh=-40,
                    )
                )

                if not chunks:
                    return "No speech detected in audio."

                non_silent_audio = AudioSegment.empty()
                for start, end in chunks:
                    non_silent_audio += audio[start:end]

                output = io.BytesIO()
                await asyncio.to_thread(
                    lambda: non_silent_audio.export(output, format="mp3")
                )
                output.seek(0)

                form = FormData()
                form.add_field(
                    "file", output, filename="audio.mp3", content_type="audio/mp3"
                )
                form.add_field("model", "whisper-1")

            async with self.bot.session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}"},
                data=form,
            ) as resp:
                if resp.status != 200:
                    raise ValueError("Failed to transcribe audio")

                result = await resp.json()
                return result["text"]

    @Cog.listener("on_message")
    async def auto_transcribe(self, message: Message):
        try:
            from pydub.utils import which

            if which("ffmpeg") is None or which("ffprobe") is None:
                return
        except Exception:
            return

        if not message.guild or not message.attachments:
            return

        channel_ids = await self.bot.db.fetch(
            """
            SELECT channel_id
            FROM transcribe.channels
            WHERE guild_id = $1
            """,
            message.guild.id,
        )

        if not channel_ids or message.channel.id not in [
            r["channel_id"] for r in channel_ids
        ]:
            return

        rate_limit = await self.bot.db.fetchrow(
            """
            SELECT last_used, uses 
            FROM transcribe.rate_limit
            WHERE guild_id = $1 AND channel_id = $2
            """,
            message.guild.id,
            message.channel.id,
        )

        now = datetime.now(timezone.utc)
        if rate_limit:
            if (now - rate_limit["last_used"]).total_seconds() < 60:
                if rate_limit["uses"] >= 3:
                    return
                await self.bot.db.execute(
                    """
                    UPDATE transcribe.rate_limit
                    SET uses = uses + 1
                    WHERE guild_id = $1 AND channel_id = $2
                    """,
                    message.guild.id,
                    message.channel.id,
                )
            else:
                await self.bot.db.execute(
                    """
                    UPDATE transcribe.rate_limit
                    SET last_used = $3, uses = 1
                    WHERE guild_id = $1 AND channel_id = $2
                    """,
                    message.guild.id,
                    message.channel.id,
                    now,
                )
        else:
            await self.bot.db.execute(
                """
                INSERT INTO transcribe.rate_limit (guild_id, channel_id)
                VALUES ($1, $2)
                """,
                message.guild.id,
                message.channel.id,
            )

        for attachment in message.attachments:
            if not (
                attachment.filename.endswith((".mp3", ".wav", ".ogg", ".m4a"))
                or (
                    attachment.content_type
                    and "audio/ogg" in attachment.content_type
                    and attachment.filename.startswith("voice-message-")
                )
            ):
                continue

            if attachment.size > 15_000_000:
                continue

            try:
                duration = await self.get_audio_duration(attachment.url)
                if duration > 90:
                    continue

                transcript = await self.transcribe_audio(attachment.url)
                await message.reply(f"{transcript}")
            except Exception:
                continue

    @group(name="wordstats", aliases=["ws"], invoke_without_command=True)
    async def wordstats(self, ctx: Context):
        """
        View word statistics for this server.
        """
        await ctx.send_help(ctx.command)

    @wordstats.command(name="topchatters", example="lol")
    async def wordstats_topchatters(
        self, 
        ctx: Context,
        word: Optional[str] = None
    ) -> Message:
        """
        Shows members who have sent the most messages.
        If a word is provided, shows who uses that word the most.
        """
        if word:
            data = await self.bot.db.fetch(
                """
                SELECT user_id, count
                FROM stats.word_usage
                WHERE guild_id = $1 AND word = $2
                ORDER BY count DESC
                LIMIT 25
                """,
                ctx.guild.id,
                word.lower()
            )
            
            if not data:
                return await ctx.warn(f"No one has used the word **{word}** yet!")
                
            embed = Embed(title=f"Top users of '{word}'")
            entries = [
                f"{ctx.guild.get_member(record['user_id']).mention}: **{record['count']:,}** times"
                for record in data
            ]
            
        else:
            data = await self.bot.db.fetch(
                """
                SELECT user_id, SUM(count) as total
                FROM stats.word_usage
                WHERE guild_id = $1
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 25
                """,
                ctx.guild.id
            )
            
            if not data:
                return await ctx.warn("No word statistics available yet!")
                
            embed = Embed(title="Top Chatters")
            entries = [
                f"{ctx.guild.get_member(record['user_id']).mention}: **{record['total']:,}** words"
                for record in data
            ]

        paginator = Paginator(
            ctx,
            entries=entries,
            embed=embed,
            per_page=10
        )
        return await paginator.start()

    @wordstats.command(name="topratio")
    async def wordstats_topratio(self, ctx: Context) -> Message:
        """
        Shows members with the highest ratio of unique words to total words.
        Only includes members with at least 1000 total words.
        """
        data = await self.bot.db.fetch(
            """
            WITH user_stats AS (
                SELECT 
                    user_id,
                    COUNT(DISTINCT word) as unique_words,
                    SUM(count) as total_words
                FROM stats.word_usage
                WHERE guild_id = $1
                GROUP BY user_id
                HAVING SUM(count) >= 1000
            )
            SELECT 
                user_id,
                unique_words,
                total_words,
                ROUND(CAST(unique_words AS DECIMAL) / total_words * 100, 2) as ratio
            FROM user_stats
            ORDER BY ratio DESC
            LIMIT 25
            """,
            ctx.guild.id
        )
        
        if not data:
            return await ctx.warn("No users have enough words to calculate ratios yet!")
            
        embed = Embed(title="Top Word Variety Ratios")
        entries = [
            f"{ctx.guild.get_member(record['user_id']).mention}: "
            f"**{record['ratio']}%** ({record['unique_words']:,} unique / {record['total_words']:,} total)"
            for record in data
        ]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=embed,
            per_page=10
        )
        return await paginator.start()

    @wordstats.command(name="common")
    async def wordstats_common(self, ctx: Context) -> Message:
        """
        Shows the most commonly used words in the server.
        Excludes ignored words and requires minimum word length from config.
        """
        config = await self.bot.db.fetchrow(
            """
            SELECT min_word_length
            FROM stats.config
            WHERE guild_id = $1
            """,
            ctx.guild.id
        ) or {'min_word_length': 3}
        
        ignored = await self.bot.db.fetch(
            """
            SELECT word
            FROM stats.ignored_words
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        ignored_words = {r['word'] for r in ignored}
        
        data = await self.bot.db.fetch(
            """
            SELECT word, SUM(count) as total
            FROM stats.word_usage
            WHERE guild_id = $1
            AND LENGTH(word) >= $2
            GROUP BY word
            ORDER BY total DESC
            LIMIT 50
            """,
            ctx.guild.id,
            config['min_word_length']
        )
        
        filtered_data = [
            r for r in data 
            if r['word'].lower() not in ignored_words
        ]
        
        if not filtered_data:
            return await ctx.warn("No word statistics available yet!")
            
        total_words = sum(r['total'] for r in data)
        
        embed = Embed(title="Most Common Words")
        entries = [
            f"**{record['word']}**: {record['total']:,} times "
            f"({record['total']/total_words*100:.1f}%)"
            for record in filtered_data
        ]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=embed,
            per_page=10
        )
        embed.set_footer(text=f"Total words analyzed: {total_words:,}")
        
        return await paginator.start()

    @wordstats.group(name="ignore", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def wordstats_ignore(self, ctx: Context) -> Message:
        """
        Manage words to ignore in statistics.
        """
        return await ctx.send_help(ctx.command)

    @wordstats_ignore.command(name="add")
    @has_permissions(manage_guild=True)
    async def wordstats_ignore_add(self, ctx: Context, word: str) -> Message:
        """Add a word to the ignore list"""
        word = word.lower()
        try:
            await self.bot.db.execute(
                """
                INSERT INTO stats.ignored_words (guild_id, word, added_by)
                VALUES ($1, $2, $3)
                """,
                ctx.guild.id,
                word,
                ctx.author.id
            )
            return await ctx.approve(f"Added **{word}** to ignored words!")
        except Exception:
            return await ctx.warn(f"**{word}** is already being ignored!")

    @wordstats_ignore.command(name="remove")
    @has_permissions(manage_guild=True)
    async def wordstats_ignore_remove(self, ctx: Context, word: str) -> Message:
        """Remove a word from the ignore list"""
        word = word.lower()
        result = await self.bot.db.execute(
            """
            DELETE FROM stats.ignored_words
            WHERE guild_id = $1 AND word = $2
            """,
            ctx.guild.id,
            word
        )
        
        if result == "DELETE 0":
            return await ctx.warn(f"**{word}** was not being ignored!")
            
        return await ctx.approve(f"Removed **{word}** from ignored words!")

    @wordstats_ignore.command(name="list")
    @has_permissions(manage_guild=True)
    async def wordstats_ignore_list(self, ctx: Context) -> Message:
        """View all ignored words"""
        data = await self.bot.db.fetch(
            """
            SELECT word, added_by, added_at
            FROM stats.ignored_words
            WHERE guild_id = $1
            ORDER BY word
            """,
            ctx.guild.id
        )
        
        if not data:
            return await ctx.warn("No ignored words configured!")
            
        embed = Embed(title="Ignored Words")
        chunks = [data[i:i+10] for i in range(0, len(data), 10)]
        
        paginator = Paginator(
            ctx,
            entries=[
                "\n".join(
                    f"`{word['word']}` - Added by {ctx.guild.get_member(word['added_by']).mention} "
                    f"({format_dt(word['added_at'], 'R')})"
                    for word in chunk
                )
                for chunk in chunks
            ],
            embed=embed
        )
        return await paginator.start()

    @wordstats.command(name="config")
    @has_permissions(manage_guild=True)
    async def wordstats_config(
        self,
        ctx: Context,
        setting: str,
        value: str
    ) -> Message:
        """
        Configure wordstats settings.
        
        Settings:
        - minlength: Minimum word length to track (2-10)
        - countbots: Whether to count bot messages (true/false)
        - whitelist: Channel IDs to exclusively track (comma-separated)
        - blacklist: Channel IDs to ignore (comma-separated)
        """
        setting = setting.lower()
        if setting not in ("minlength", "countbots", "whitelist", "blacklist"):
            return await ctx.warn("Invalid setting! Use minlength, countbots, whitelist, or blacklist")

        if setting == "minlength":
            try:
                length = int(value)
                if not 2 <= length <= 10:
                    raise ValueError
            except ValueError:
                return await ctx.warn("Minimum length must be between 2 and 10!")
                
            await self.bot.db.execute(
                """
                INSERT INTO stats.config (guild_id, min_word_length)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET min_word_length = EXCLUDED.min_word_length
                """,
                ctx.guild.id,
                length
            )
            return await ctx.approve(f"Set minimum word length to **{length}**!")
            
        elif setting == "countbots":
            value = value.lower()
            if value not in ("true", "false"):
                return await ctx.warn("Value must be 'true' or 'false'!")
                
            count_bots = value == "true"
            await self.bot.db.execute(
                """
                INSERT INTO stats.config (guild_id, count_bots)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET count_bots = EXCLUDED.count_bots
                """,
                ctx.guild.id,
                count_bots
            )
            return await ctx.approve(f"{'Now' if count_bots else 'No longer'} counting bot messages!")
            
        elif setting in ("whitelist", "blacklist"):
            try:
                channels = [int(c.strip()) for c in value.split(",")]
                valid_channels = [
                    c for c in channels 
                    if ctx.guild.get_channel(c)
                ]
            except ValueError:
                return await ctx.warn("Please provide valid channel IDs separated by commas!")
                
            if not valid_channels:
                return await ctx.warn("No valid channels provided!")
                
            column = f"channel_{setting}"
            await self.bot.db.execute(
                f"""
                INSERT INTO stats.config (guild_id, {column})
                VALUES ($1, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET {column} = EXCLUDED.{column}
                """,
                ctx.guild.id,
                valid_channels
            )
            
            channels_text = ", ".join(f"<#{c}>" for c in valid_channels)
            return await ctx.approve(f"Updated {setting} to: {channels_text}")

    @Cog.listener("on_message")
    async def word_tracker(self, message: Message):
        if not message.guild or message.author.bot:
            return
            
        cache_key = f'wordstats_config_{message.guild.id}'
        config = self._get_cache(cache_key)
        if config is None:
            config = await self.bot.db.fetchrow(
                """
                SELECT count_bots, channel_whitelist, channel_blacklist
                FROM stats.config
                WHERE guild_id = $1
                """,
                message.guild.id
            ) or {'count_bots': False, 'channel_whitelist': None, 'channel_blacklist': None}
            self._set_cache(cache_key, config, expire=300)
            
        if message.author.bot and not config['count_bots']:
            return
            
        if config['channel_whitelist'] and message.channel.id not in config['channel_whitelist']:
            return
            
        if config['channel_blacklist'] and message.channel.id in config['channel_blacklist']:
            return
            
        words = re.findall(r'\b\w+\b', message.content.lower())
        if not words:
            return

        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        unique_words = list(word_counts.keys())
        counts = list(word_counts.values())

        await self.bot.db.execute(
            """
            INSERT INTO stats.word_usage (guild_id, user_id, word, count, last_used)
            SELECT $1, $2, word, count, CURRENT_TIMESTAMP
            FROM unnest($3::text[], $4::int[]) AS t(word, count)
            ON CONFLICT (guild_id, user_id, word)
            DO UPDATE SET 
                count = stats.word_usage.count + EXCLUDED.count,
                last_used = CURRENT_TIMESTAMP
            """,
            message.guild.id,
            message.author.id,
            unique_words,
            counts
        )

    @hybrid_command(aliases=["texttospeech", "speak"])
    async def tts(
        self,
        ctx: Context,
        voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "nova",
        *,
        text: str,
    ) -> Message:
        """
        Convert text to speech using OpenAI's TTS API.
        Premium users get 15 uses per hour and HD quality.
        
        Voices:
        - alloy: Versatile, balanced voice
        - echo: Warm, clear voice
        - fable: British accent, suitable for storytelling
        - onyx: Deep, authoritative voice
        - nova: Energetic female voice
        - shimmer: Gentle, welcoming voice
        """
        if len(text) > 1000:
            return await ctx.warn("Text cannot exceed 1000 characters!")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        key = f"tts:{ctx.author.id}"
        uses = await self.bot.redis.get(key)
        ttl = await self.bot.redis.ttl(key)
        
        max_uses = 15 if is_donor else 2
        
        if uses and int(uses) >= max_uses:
            embed = discord.Embed(
                color=config.COLORS.WARN,
                description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in {int(ttl)} seconds.\n\nDonors get 15 uses per hour instead of 2! Consider becoming a donor for increased access."
            )
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="Become a Donor",
                    url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                    style=discord.ButtonStyle.url
                )
            )
            msg = await ctx.send(embed=embed)
            await msg.edit(view=view)
            return

        embed = discord.Embed(
            title="Text to Speech",
            description=f"Voice: **{voice}**\nText: {text[:100]}{'...' if len(text) > 100 else ''}"
        )
        
        if is_donor:
            embed.set_footer(text="Premium User • HD Quality")
        else:
            embed.set_footer(text="Free User • Standard Quality")

        loading_msg = await ctx.send(
            f"Converting text to speech...", 
            embed=embed
        )

        async with ctx.typing():
            try:
                response = await self.bot.session.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "tts-1-hd" if is_donor else "tts-1",
                        "input": text,
                        "voice": voice,
                        "response_format": "opus"
                    }
                )
                
                if response.status != 200:
                    return await ctx.warn("Failed to generate speech!")

                audio_data = await response.read()
                file_size = len(audio_data)

                waveform = [random.randint(50, 200) for _ in range(256)]
                waveform_base64 = base64.b64encode(bytes(waveform)).decode('utf-8')

                upload_request = await self.bot.session.post(
                    f"https://discord.com/api/v10/channels/{ctx.channel.id}/attachments",
                    headers={
                        "Authorization": f"Bot {config.DISCORD.TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "files": [{
                            "filename": "voice-message.ogg",
                            "file_size": file_size,
                            "id": "2"
                        }]
                    }
                )
                
                upload_data = await upload_request.json()
                upload_url = upload_data["attachments"][0]["upload_url"]
                uploaded_filename = upload_data["attachments"][0]["upload_filename"]

                await self.bot.session.put(
                    upload_url,
                    headers={
                        "Content-Type": "audio/ogg",
                        "Authorization": f"Bot {config.DISCORD.TOKEN}"
                    },
                    data=audio_data
                )

                await self.bot.session.post(
                    f"https://discord.com/api/v10/channels/{ctx.channel.id}/messages",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bot {config.DISCORD.TOKEN}"
                    },
                    json={
                        "flags": 8192,
                        "message_reference": {
                            "message_id": loading_msg.id,
                            "channel_id": ctx.channel.id,
                            "guild_id": ctx.guild.id
                        },
                        "attachments": [{
                            "id": "0",
                            "filename": "voice-message.ogg",
                            "uploaded_filename": uploaded_filename,
                            "duration_secs": 30,
                            "waveform": waveform_base64
                        }]
                    }
                )

                await loading_msg.edit(content=None)

                pipe = self.bot.redis.pipeline()
                pipe.incr(key)
                if not uses:
                    pipe.expire(key, 3600)
                await pipe.execute()

            except Exception as e:
                await loading_msg.delete()
                return await ctx.warn(f"Failed to generate speech: {e}")

    @hybrid_command(name="imagine")
    async def imagine(
        self,
        ctx: Context,
        quality: Literal["standard", "hd"] = "standard",
        size: Literal["1024x1024", "1024x1792", "1792x1024"] = "1024x1024",
        *,
        prompt: str,
    ) -> Message:
        """
        Generate images using DALL-E 3.
        Premium users get $15 worth of credits per 2 weeks.
        Free users get 2 generations per day.

        Quality:
        - standard: Basic quality ($0.040 per image)
        - hd: Higher quality ($0.080 per image)

        Size:
        - 1024x1024: Square image
        - 1024x1792: Portrait
        - 1792x1024: Landscape
        """
        if len(prompt) > 4000:
            return await ctx.warn("Prompt cannot exceed 4000 characters!")
        
        minute_key = f"imagine_minute:{ctx.author.id}"
        minute_uses = await self.bot.redis.get(minute_key)
        if minute_uses and int(minute_uses) >= 5:
            return await ctx.warn("You can only generate 5 images per minute. Please wait a moment.")

        daily_key = f"imagine_daily:{ctx.author.id}"
        daily_uses = await self.bot.redis.get(daily_key)
        if daily_uses and int(daily_uses) >= 1000:
            ttl = await self.bot.redis.ttl(daily_key)
            hours = int(ttl / 3600)
            minutes = int((ttl % 3600) / 60)
            return await ctx.warn(f"Daily limit reached (1000/1000). Resets in {hours}h {minutes}m")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        base_cost = decimal.Decimal('0.080') if quality == "hd" else decimal.Decimal('0.040')
        if size != "1024x1024":
            base_cost *= decimal.Decimal('2')

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None:
                await self.bot.db.execute(
                    """
                    INSERT INTO dalle_credits (user_id, credits, last_reset)
                    VALUES ($1, $2, NOW())
                    """,
                    ctx.author.id,
                    15.00 
                )
                credits = decimal.Decimal('15.00')

            last_reset = await self.bot.db.fetchval(
                """
                SELECT last_reset
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if (datetime.now() - last_reset).days >= 14:
                await self.bot.db.execute(
                    """
                    UPDATE dalle_credits
                    SET credits = $1, last_reset = NOW()
                    WHERE user_id = $2
                    """,
                    15.00,
                    ctx.author.id
                )
                credits = decimal.Decimal('15.00')

            if credits < base_cost:
                return await ctx.warn(
                    f"Insufficient credits! You have ${credits:.3f} remaining.\n"
                    f"This generation would cost ${base_cost:.3f}.\n"
                    "Credits reset every 2 weeks."
                )

        else:
            key = f"imagine:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            ttl = await self.bot.redis.ttl(key)
            
            if uses and int(uses) >= 2:
                embed = discord.Embed(
                    color=config.COLORS.WARN,
                    description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in {int(ttl)} seconds.\n\nDonors get $15 worth of DALL-E credits every 2 weeks! Consider upgrading for increased access."
                )
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )
                msg = await ctx.send(embed=embed)
                await msg.edit(view=view)
                return

        global_key = "dalle_global_ratelimit"
        if await self.bot.redis.get(global_key):
            return await ctx.warn("The image generation system is cooling down. Please try again in a few seconds.")

        async with ctx.typing():
            try:
                await self.bot.redis.set(global_key, "1", ex=60) 

                response = await self.bot.session.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "dall-e-2",
                        "prompt": prompt,
                        "n": 1,
                        "quality": quality,
                        "size": size
                    }
                )

                if response.status != 200:
                    error_data = await response.json()
                    if not error_data.get('error', {}).get('message', '').startswith('Rate limit'):
                        await self.bot.redis.delete(global_key)
                
                    log.error(
                        f"DALL-E generation failed: Status {response.status}\n"
                        f"Error: {error_data}\n"
                        f"User: {ctx.author} ({ctx.author.id})\n"
                        f"Prompt: {prompt}\n"
                        f"Quality: {quality}, Size: {size}"
                    )
                    return await ctx.warn(f"Failed to generate image: {error_data.get('error', {}).get('message', 'Unknown error')}")

                data = await response.json()
                image_url = data["data"][0]["url"]

                log.info(
                    f"DALL-E image generated:\n"
                    f"User: {ctx.author} ({ctx.author.id})\n"
                    f"Prompt: {prompt}\n"
                    f"Quality: {quality}, Size: {size}\n"
                    f"Cost: ${base_cost:.3f}"
                )

                embed = discord.Embed(
                    title="DALL-E Image Generation",
                    description=f"**Prompt:** {prompt}\n**Quality:** {quality}\n**Size:** {size}"
                )
                embed.set_image(url=image_url)

                if is_donor:
                    new_credits = credits - base_cost
                    await self.bot.db.execute(
                        """
                        UPDATE dalle_credits
                        SET credits = $1
                        WHERE user_id = $2
                        """,
                        new_credits,
                        ctx.author.id
                    )
                    embed.set_footer(text=f"Premium User • ${new_credits:.3f} credits remaining")
                else:
                    pipe = self.bot.redis.pipeline()
                    pipe.incr(key)
                    if not uses:
                        pipe.expire(key, 86400) 
                    await pipe.execute()
                    embed.set_footer(text="Free User • 2 uses per day")

                pipe = self.bot.redis.pipeline()
                pipe.incr(minute_key)
                pipe.expire(minute_key, 60) 
                pipe.incr(daily_key)
                if not daily_uses:
                    pipe.expire(daily_key, 86400)  
                await pipe.execute()

                return await ctx.send(embed=embed)

            except Exception as e:
                await self.bot.redis.delete(global_key)
                
                log.error(
                    f"DALL-E generation error:\n"
                    f"Error: {str(e)}\n"
                    f"User: {ctx.author} ({ctx.author.id})\n"
                    f"Prompt: {prompt}\n"
                    f"Quality: {quality}, Size: {size}",
                    exc_info=True
                )
                return await ctx.warn(f"Failed to generate image: {str(e)}")

    @hybrid_command(name="dalle_credits")
    async def dalle_credits(self, ctx: Context) -> Message:
        """
        Check your DALL-E credits.
        """
        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None:
                await self.bot.db.execute(
                    """
                    INSERT INTO dalle_credits (user_id, credits, last_reset)
                    VALUES ($1, $2, NOW())
                    """,
                    ctx.author.id,
                    15.00 
                )
                credits = 15.00

            last_reset = await self.bot.db.fetchval(
                """
                SELECT last_reset
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if (datetime.now() - last_reset).days >= 14:
                await self.bot.db.execute(
                    """
                    UPDATE dalle_credits
                    SET credits = $1, last_reset = NOW()
                    WHERE user_id = $2
                    """,
                    15.00,
                    ctx.author.id
                )
                credits = 15.00

            days_until_reset = 14 - (datetime.now() - last_reset).days
            embed = discord.Embed(
                title="DALL-E Credits",
                description=f"You have ${credits:.3f} credits remaining.\n"
                f"Credits reset in {days_until_reset} days.\n\n"
                "**Pricing:**\n"
                "- Standard quality: $0.040 per image\n"
                "- HD quality: $0.080 per image\n"
                "- Portrait/Landscape: Double the cost\n"
                "- Premium users get $15 worth of credits every 2 weeks"
            )
            embed.set_footer(text="Contact support to request increased limits")

        else:
            key = f"imagine:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            ttl = await self.bot.redis.ttl(key)
            
            remaining_uses = 2 - int(uses) if uses else 2
            embed = discord.Embed(
                title="DALL-E Credits",
                description=f"You have {remaining_uses} generations remaining.\n"
                f"Resets in {int(ttl)} seconds.\n\n"
                "**Pricing:**\n"
                "- Standard quality: $0.040 per image\n"
                "- HD quality: $0.080 per image\n"
                "- Portrait/Landscape: Double the cost\n"
                "- Premium users get $15 worth of credits every 2 weeks"
            )
            embed.set_footer(text="Become a donor for increased access")

            if remaining_uses <= 0:
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )
                msg = await ctx.send(embed=embed)
                await msg.edit(view=view)
                return

        return await ctx.send(embed=embed)

    @hybrid_command(name="credits")
    async def dalle_credits(self, ctx: Context) -> Message:
        """Check your available DALL-E credits."""
        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None:
                await self.bot.db.execute(
                    """
                    INSERT INTO dalle_credits (user_id, credits, last_reset)
                    VALUES ($1, $2, NOW())
                    """,
                    ctx.author.id,
                    15.00
                )
                credits = 15.00

            last_reset = await self.bot.db.fetchval(
                """
                SELECT last_reset
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            days_until_reset = 14 - (datetime.now() - last_reset).days

            embed = discord.Embed(
                title="DALL-E Credits",
                description=(
                    f"**Current Balance:** ${credits:.3f}\n"
                    f"**Days until reset:** {days_until_reset}\n\n"
                    "**Pricing:**\n"
                    "- Standard Quality: $0.040 per image\n"
                    "- HD Quality: $0.080 per image\n"
                    "- Non-square sizes cost 2x more"
                )
            )
            embed.set_footer(text="Premium User • Credits reset every 2 weeks")
            return await ctx.send(embed=embed)
        else:
            key = f"imagine:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            ttl = await self.bot.redis.ttl(key)
            remaining = 2 - (int(uses) if uses else 0)

            view = None
            if remaining <= 0:
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )

            embed = discord.Embed(
                title="DALL-E Credits",
                description=(
                    f"**Remaining Uses:** {remaining}/2\n"
                    f"**Time until reset:** {int(ttl) if ttl > 0 else 0} seconds\n\n"
                    "**Premium Benefits:**\n"
                    "- $15 worth of credits every 2 weeks\n"
                    "- Higher quality options\n"
                    "- More size options"
                )
            )
            embed.set_footer(text="Free User • 2 uses per day")
            return await ctx.send(embed=embed, view=view)

    async def get_image_base64(self, url: str) -> str:
        async with self.bot.session.get(url) as response:
            if response.status != 200:
                raise ValueError("Failed to fetch image")
            image_data = await response.read()
            return f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8')}"

    @hybrid_command(name="describe")
    async def describe_image(
        self, 
        ctx: Context, 
        image: Optional[Attachment] = None
    ) -> Message:
        """Get an AI description of an image using GPT-4 Vision"""
        if not image:
            if not ctx.message.reference:
                return await ctx.warn("Please provide an image or reply to a message with an image!")
                
            try:
                reference = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                if reference.attachments:
                    image = reference.attachments[0]
                elif reference.embeds and reference.embeds[0].image:
                    image = SimpleNamespace(
                        url=reference.embeds[0].image.url,
                        content_type='image/unknown'
                    )
                else:
                    return await ctx.warn("The replied message doesn't contain any images!")
            except:
                return await ctx.warn("Couldn't fetch the replied message!")

        if not image.content_type.startswith('image/'):
            return await ctx.warn("Please provide a valid image!")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        cost = decimal.Decimal('0.05')

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None or credits < cost:
                return await ctx.warn(
                    f"Insufficient credits! You need ${cost:.3f} for this command.\n"
                    f"Current balance: ${credits:.3f if credits else 0:.3f}"
                )

        else:
            key = f"describe:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            if uses and int(uses) >= 2:
                embed = discord.Embed(
                    color=config.COLORS.WARN,
                    description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in 24h.\n\nDonors get $15 worth of credits every 2 weeks!"
                )
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )
                return await ctx.send(embed=embed, view=view)
        
        async with ctx.typing():
            try:
                image_base64 = await self.get_image_base64(image.url)
                response = await self.bot.session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-0125-preview",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Describe this image in detail"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_base64
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 300
                    }
                )
                
                if response.status != 200:
                    error_data = await response.json()
                    log.error(
                        f"GPT-4 Vision failed: Status {response.status}\n"
                        f"Error: {error_data}\n"
                        f"User: {ctx.author} ({ctx.author.id})\n"
                        f"Image URL: {image.url}"
                    )
                    return await ctx.warn(f"Failed to analyze image: {error_data.get('error', {}).get('message', 'Unknown error')}")
                    
                data = await response.json()
                description = data['choices'][0]['message']['content']
                
                if is_donor:
                    await self.bot.db.execute(
                        """
                        UPDATE dalle_credits
                        SET credits = credits - $1
                        WHERE user_id = $2
                        """,
                        cost,
                        ctx.author.id
                    )
                else:
                    pipe = self.bot.redis.pipeline()
                    pipe.incr(key)
                    if not uses:
                        pipe.expire(key, 86400)
                    await pipe.execute()
                
                embed = Embed(description=description)
                embed.set_image(url=image.url)
                if is_donor:
                    new_balance = credits - cost
                    embed.set_footer(text=f"Premium User • ${new_balance:.3f} credits remaining")
                else:
                    embed.set_footer(text="Free User • 2 uses per day")
                return await ctx.send(embed=embed)
                
            except Exception as e:
                return await ctx.warn(f"Failed to analyze image: {e}")

    @hybrid_command(name="complete")
    async def complete_text(self, ctx: Context, *, prompt: str) -> Message:
        """Complete your text using GPT-3.5"""
        if len(prompt) > 1000:
            return await ctx.warn("Prompt cannot exceed 1000 characters!")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        cost = decimal.Decimal('0.02') 

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None or credits < cost:
                return await ctx.warn(
                    f"Insufficient credits! You need ${cost:.3f} for this command.\n"
                    f"Current balance: ${credits:.3f if credits else 0:.3f}"
                )

        else:
            key = f"complete:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            if uses and int(uses) >= 3:
                embed = discord.Embed(
                    color=config.COLORS.WARN,
                    description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in 24h.\n\nDonors get $15 worth of credits every 2 weeks!"
                )
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )
                return await ctx.send(embed=embed, view=view)

        async with ctx.typing():
            try:
                response = await self.bot.session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 500,
                        "temperature": 0.7
                    }
                )
                
                if response.status != 200:
                    return await ctx.warn("Failed to generate completion!")
                    
                data = await response.json()
                completion = data['choices'][0]['message']['content']
                
                if is_donor:
                    await self.bot.db.execute(
                        """
                        UPDATE dalle_credits
                        SET credits = credits - $1
                        WHERE user_id = $2
                        """,
                        cost,
                        ctx.author.id
                    )
                else:
                    pipe = self.bot.redis.pipeline()
                    pipe.incr(key)
                    if not uses:
                        pipe.expire(key, 86400)
                    await pipe.execute()
                
                embed = Embed(title="Text Completion", description=completion)
                if is_donor:
                    new_balance = credits - cost
                    embed.set_footer(text=f"Premium User • ${new_balance:.3f} credits remaining")
                else:
                    embed.set_footer(text="Free User • 3 uses per day")
                return await ctx.send(embed=embed)
                
            except Exception as e:
                return await ctx.warn(f"Failed to generate completion: {e}")


    @command(name="donator", aliases=["donate", "donators"])
    async def donator(self, ctx: Context) -> Message:
        """View information about donator perks and benefits."""
        
        embed = discord.Embed(
            title="<:donor1:1320054420616249396> Donator Benefits",
            description=(
                "Support Evict's development and get access to exclusive features!\n\n"
                "**Monthly Perks:**\n"
                "- $15 worth of DALL-E & OpenAI credits every 2 weeks & More image size options\n" 
                "- Higher quality image generation options\n"
                "- Access to reskin features, less ratelimits & increased income \n"
                "- Priority support in our Discord server\n"
                "- Exclusive donator role and channels\n"
                "- Early access to new features\n\n"
                "**Pricing:**\n"
                "- DALL-E Standard: $0.040 per image\n"
                "- DALL-E HD: $0.080 per image\n"
                "- Non-square sizes cost 2x more\n"
                "- GPT-4 Vision: $0.050 per analysis\n"
                "- Text completion: $0.020 per request\n\n"
                "Join our [Discord server](https://discord.gg/evict) to get your donator role and access exclusive channels! This is entierely automated, as soon as payment is completed you will receive your perks. "
            ),
            color=discord.Color.gold()
        )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1186140840865333248.gif")
        embed.set_footer(text="Thank you for supporting Evict! ❤️")
        
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Become a Donor",
                url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                style=discord.ButtonStyle.url,
                emoji=config.EMOJIS.SOCIAL.WEBSITE
            )
        )
        
        return await ctx.send(embed=embed, view=view)

    @command(name="activity")
    async def activity(self, ctx: Context) -> Message:
        """View and modify bot activity settings"""
        if ctx.author.id != int(os.getenv("INSTANCE_OWNER_ID")):
            return
            
        data = await self.bot.db.fetchrow("SELECT * FROM bot_activity")
        if not data:
            data = {
                'activity_type': 'streaming',
                'activity_text': '🔗 discord.gg/evict',
                'activity_url': 'https://twitch.tv/evictbot'
            }
            await self.bot.db.execute(
                """
                INSERT INTO bot_activity (activity_type, activity_text, activity_url)
                VALUES ($1, $2, $3)
                """,
                data['activity_type'],
                data['activity_text'],
                data['activity_url']
            )
        
        embed = discord.Embed(
            title="Activity Settings",
            description=(
                "Configure the bot's activity status\n\n"
                f"**Current Settings**\n"
                f"Type: `{data['activity_type']}`\n"
                f"Text: `{data['activity_text']}`\n"
                f"URL: `{data['activity_url'] or 'None'}`"
            ),
            color=0x171614
        )
        
        class ActivityView(discord.ui.View):
            def __init__(self, bot):
                super().__init__(timeout=60)
                self.bot = bot
                
            @discord.ui.button(label="Change Type", style=discord.ButtonStyle.blurple)
            async def change_type(self, interaction: discord.Interaction, button: discord.ui.Button):
                options = [
                    discord.SelectOption(label="Playing", value="playing"),
                    discord.SelectOption(label="Streaming", value="streaming"),
                    discord.SelectOption(label="Listening", value="listening"),
                    discord.SelectOption(label="Watching", value="watching"),
                    discord.SelectOption(label="Competing", value="competing")
                ]
                
                select = discord.ui.Select(placeholder="Select activity type", options=options)
                
                async def select_callback(interaction: discord.Interaction):
                    type = select.values[0]
                    await self.bot.db.execute(
                        "UPDATE bot_activity SET activity_type = $1", type
                    )
                    await self.bot.change_presence(
                        activity=discord.Activity(
                            type=getattr(discord.ActivityType, type),
                            name=data['activity_text'],
                            url=data['activity_url']
                        )
                    )
                    await interaction.response.edit_message(
                        embed=discord.Embed(
                            description=f"Activity type set to **{type}**",
                            color=discord.Color.green()
                        ),
                        view=None
                    )
                
                select.callback = select_callback
                view = discord.ui.View()
                view.add_item(select)
                await interaction.response.edit_message(view=view)
                
            @discord.ui.button(label="Change Text", style=discord.ButtonStyle.blurple)
            async def change_text(self, interaction: discord.Interaction, button: discord.ui.Button):
                modal = discord.ui.Modal(title="Change Activity Text")
                text_input = discord.ui.TextInput(
                    label="New Text",
                    placeholder="Enter new activity text...",
                    default=data['activity_text'],
                    required=True,
                    max_length=128
                )
                modal.add_item(text_input)
                
                async def modal_callback(interaction: discord.Interaction):
                    text = text_input.value
                    await self.bot.db.execute(
                        "UPDATE bot_activity SET activity_text = $1", text
                    )
                    await self.bot.change_presence(
                        activity=discord.Activity(
                            type=getattr(discord.ActivityType, data['activity_type']),
                            name=text,
                            url=data['activity_url']
                        )
                    )
                    await interaction.response.edit_message(
                        embed=discord.Embed(
                            description=f"Activity text set to **{text}**",
                            color=discord.Color.green()
                        ),
                        view=None
                    )
                
                modal.on_submit = modal_callback
                await interaction.response.send_modal(modal)
                
            @discord.ui.button(label="Change URL", style=discord.ButtonStyle.blurple)
            async def change_url(self, interaction: discord.Interaction, button: discord.ui.Button):
                modal = discord.ui.Modal(title="Change Stream URL")
                url_input = discord.ui.TextInput(
                    label="New URL",
                    placeholder="Enter stream URL or leave empty to remove...",
                    default=data['activity_url'] or "",
                    required=False,
                    max_length=256
                )
                modal.add_item(url_input)
                
                async def modal_callback(interaction: discord.Interaction):
                    url = url_input.value or None
                    await self.bot.db.execute(
                        "UPDATE bot_activity SET activity_url = $1", url
                    )
                    await self.bot.change_presence(
                        activity=discord.Activity(
                            type=getattr(discord.ActivityType, data['activity_type']),
                            name=data['activity_text'],
                            url=url
                        )
                    )
                    await interaction.response.edit_message(
                        embed=discord.Embed(
                            description=f"Activity URL set to **{url or 'None'}**",
                            color=discord.Color.green()
                        ),
                        view=None
                    )
                
                modal.on_submit = modal_callback
                await interaction.response.send_modal(modal)
        
        view = ActivityView(self.bot)
        return await ctx.send(embed=embed, view=view)

    @command(name="customize")
    async def customize_bot(self, ctx: Context) -> Message:
        """Customize bot appearance and settings"""
        if ctx.author.id != int(os.getenv("INSTANCE_OWNER_ID")):
            return

        async with ctx.bot.session.get(
            f"https://discord.com/api/v10/applications/{ctx.bot.user.id}",
            headers={"Authorization": f"Bot {config.DISCORD.TOKEN}"}
        ) as resp:
            data = await resp.json()
            bot_data = data.get('bot', {})
            description = data.get('description')
            banner = bot_data.get('banner')

        banner_url = f"https://cdn.discordapp.com/banners/{ctx.bot.user.id}/{banner}.png" if banner else None

        embed = discord.Embed(
            title="Bot Customization",
            description=(
                "Configure the bot's appearance\n\n"
                "**Current Settings**\n"
                f"Name: `{ctx.bot.user.name}`\n"
                f"Description: {description or 'None set'}\n"
                f"Avatar: [View]({ctx.bot.user.display_avatar.url})\n"
                f"Banner: {('[View](' + banner_url + ')') if banner_url else 'None set'}"
            ),
            color=0x171614
        )
        embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
        if banner_url:
            embed.set_image(url=banner_url)

        class CustomizeView(discord.ui.View):
            def __init__(self, bot):
                super().__init__(timeout=60)
                self.bot = bot

            @discord.ui.button(label="Name", style=discord.ButtonStyle.blurple, row=0)
            async def name(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(TextModal("Bot Name", self.bot.user.name))

            @discord.ui.button(label="Description", style=discord.ButtonStyle.blurple, row=0)
            async def description(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(TextModal("Bot Description", self.bot.description or ""))

            @discord.ui.button(label="Avatar", style=discord.ButtonStyle.blurple, row=1)
            async def avatar(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(TextModal("Avatar URL"))

            @discord.ui.button(label="Banner", style=discord.ButtonStyle.blurple, row=1)
            async def banner(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(TextModal("Banner URL"))

        class TextModal(discord.ui.Modal):
            def __init__(self, title: str, default: str = ""):
                super().__init__(title=title)
                self.text_input = discord.ui.TextInput(
                    label=title,
                    default=default,
                    required=True,
                    max_length=1024 if title == "Bot Description" else 32 if title == "Bot Name" else 256
                )
                self.add_item(self.text_input)

            async def on_submit(self, interaction: discord.Interaction):
                text = self.text_input.value
                bot = interaction.client

                try:
                    if self.title == "Bot Name":
                        try:
                            log.info(f"Attempting to change bot name to: {text}")
                            async with bot.session.patch(
                                "https://discord.com/api/v10/users/@me",
                                headers={"Authorization": f"Bot {config.DISCORD.TOKEN}"},
                                json={"username": text}
                            ) as resp:
                                response_data = await resp.json()
                                log.info(f"Name change response status: {resp.status}")
                                log.info(f"Name change response data: {response_data}")
                                
                                if resp.status != 200:
                                    log.error(f"Failed to update name. Status: {resp.status}, Response: {response_data}")
                                    return await interaction.response.send_message(
                                        f"Failed to update name: {response_data.get('message', 'Unknown error')}", 
                                        ephemeral=True
                                    )
                            
                            log.info(f"Successfully changed bot name to: {text}")
                            message = "Bot name updated"
                            
                        except Exception as e:
                            log.error(f"Error changing bot name: {str(e)}", exc_info=True)
                            raise

                    elif self.title == "Bot Description":
                        async with bot.session.patch(
                            f"https://discord.com/api/v10/applications/{bot.user.id}",
                            headers={"Authorization": f"Bot {config.DISCORD.TOKEN}"},
                            json={"description": text}
                        ) as resp:
                            if resp.status != 200:
                                return await interaction.response.send_message("Failed to update description", ephemeral=True)
                        bot.description = text
                        message = "Bot description updated"

                    elif self.title == "Avatar URL":
                        async with bot.session.get(text) as resp:
                            await bot.user.edit(avatar=await resp.read())
                        message = "Avatar updated"

                    elif self.title == "Banner URL":
                        async with bot.session.get(text) as resp:
                            await bot.user.edit(banner=await resp.read())
                        message = "Banner updated"

                    await interaction.response.edit_message(
                        embed=discord.Embed(description=f"{config.EMOJIS.CONTEXT.APPROVE} {message}", color=discord.Color.green()),
                        view=None
                    )

                except Exception as e:
                    await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

        view = CustomizeView(self.bot)
        return await ctx.send(embed=embed, view=view)
