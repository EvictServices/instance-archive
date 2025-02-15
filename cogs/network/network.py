import os
import json
import logging
import config
import asyncio
import time
import discord
import aiohttp
import stripe
from discord import Embed

from main import Evict

from aiohttp import web, WSMsgType
from aiohttp.abc import AbstractAccessLogger
from aiohttp_cors import setup as cors_setup, ResourceOptions
from aiohttp.web import BaseRequest, Request, Response, StreamResponse

from discord.ext.commands import Cog, command, group

from functools import wraps
from typing import Callable, Optional
from cashews import cache
from pomice import LoopMode
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from collections import defaultdict


class Module(BaseModel):
    threshold: int
    duration: int


class Settings(BaseModel):
    bot: bool = False
    ban: Optional[Module] = None
    kick: Optional[Module] = None
    role: Optional[Module] = None
    channel: Optional[Module] = None
    webhook: Optional[Module] = None
    emoji: Optional[Module] = None

    @classmethod
    async def fetch(cls, bot, guild):
        data = await bot.db.fetchrow(
            "SELECT * FROM antinuke WHERE guild_id = $1", guild.id
        )
        return cls(**data) if data else cls()

    @classmethod
    async def revalidate(cls, bot, guild):
        await bot.cache.delete(f"antinuke:{guild.id}")


cache.setup("mem://")
log = logging.getLogger(__name__)


class AccessLogger(AbstractAccessLogger):
    def log(
        self: "AccessLogger",
        request: BaseRequest,
        response: StreamResponse,
        time: float,
    ) -> None:
        self.logger.info(
            f"Request for {request.path!r} with status of {response.status!r}."
        )


def requires_auth(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(self: "Network", request: Request) -> Response:
        auth_header = request.headers.get("Authorization")
        if auth_header != "2O91CtFwD3L2MXLI50V":
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await func(self, request)

    return wrapper

def requires_not_auth(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(self: "Network", request: Request) -> Response:
        auth_header = request.headers.get("Authorization")
        if auth_header != "3SaoBuHv45K6dgc5Khp":
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await func(self, request)

    return wrapper


def route(pattern: str, method: str | list[str] = "GET") -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self: "Network", request: Request) -> None:
            log.info(f"Route decorator received {request.method} request for {pattern}")
            log.info(f"Expected method(s): {method}")
            log.info(f"Raw headers: {request.raw_headers}")
            
            actual_method = request.headers.get('X-HTTP-Method', request.method)
            log.info(f"Using method: {actual_method} (original: {request.method})")
            
            allowed_methods = method if isinstance(method, list) else [method]
            if actual_method not in allowed_methods:
                log.warning(f"Method mismatch - got {actual_method}, expected one of {allowed_methods}")
                return web.json_response(
                    {"error": f"Method {actual_method} not allowed, expected {allowed_methods}"}, 
                    status=405,
                    headers={"Allow": ", ".join(allowed_methods)}
                )
            
            request._method = actual_method
            
            try:
                return await func(self, request)
            except Exception as e:
                log.error(f"Error handling request for {pattern}: {e}")
                return web.json_response({"error": "Internal server error"}, status=500)

        wrapper.methods = [method] if isinstance(method, str) else method
        wrapper.pattern = pattern
        return wrapper
    return decorator


class Network(Cog):
    def __init__(self, bot: Evict):
        self.bot: Evict = bot
        self.app = web.Application(logger=log)
        self.runner = None 
        self.site = None  
        
        self.cors = cors_setup(
            self.app,
            defaults={
                "*": ResourceOptions(
                    allow_credentials=False,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods=["GET", "POST", "OPTIONS"],
                    max_age=3600
                )
            },
        )

        @web.middleware
        async def request_middleware(request, handler):
            log.info(f"Incoming request: {request.method} {request.path}")
            log.info(f"Headers: {dict(request.headers)}")
            try:
                response = await handler(request)
                log.info(f"Response status: {response.status}")
                return response
            except Exception as e:
                log.error(f"Error handling request: {e}")
                raise

        self.app.middlewares.append(request_middleware)

        for module in dir(self):
            route = getattr(self, module)
            if not hasattr(route, "pattern"):
                continue
            
            log.info(f"Registering route {route.pattern} with methods {route.methods}")
            
            resource = self.app.router.add_resource(route.pattern)
            
            methods = route.methods if isinstance(route.methods, list) else [route.methods]
            methods = [m for m in methods if m != "OPTIONS"]
            
            for method in methods:
                handler = resource.add_route(method, route)
                self.cors.add(handler)
                log.info(f"Added route for {route.pattern!r} ({method}).")

        root_resource = self.app.router.add_get("/", self.root_handler)
        self.cors.add(root_resource)

        self.ws_connections = {}

        self.app.router.add_get("/ws/music/{guild_id}", self.music_websocket)
        self.app.router.add_get("/ws/antinuke/{guild_id}", self.antinuke_websocket)

        self.failed_payment_notifications = defaultdict(list)  # Track failed payment DMs

    def required_xp(self, level: int, multiplier: int = 1) -> int:
        """
        Calculate the required XP for a given level.
        """
        xp = sum((i * 100) + 75 for i in range(level))
        return int(xp * multiplier)

    async def root_handler(self, request):
        return web.json_response(
            {
            "commands": {len([cmd for cmd in self.bot.walk_commands() if cmd.cog_name != 'Jishaku' and cmd.cog_name != 'Owner'])},
            "latency": self.bot.latency * 1000,
            "cache": {
                "guilds": len(self.bot.guilds),
                "users": len([user for user in self.bot.users if not user.bot]),
            },
            }
        )

    async def cog_load(self) -> None:
        host = config.STATUS.HOST
        port = config.STATUS.PORT
        
        self.runner = web.AppRunner(self.app, access_log=log, access_log_class=AccessLogger)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        
        log.info(f"Started the internal API on {host}:{port}.")

    async def cog_unload(self) -> None:
        if self.site:
            await self.site.stop()
            log.info("Stopped the TCP site")
        
        if self.runner:
            await self.runner.cleanup()
            log.info("Cleaned up the runner")
        
        await self.app.shutdown()
        await self.app.cleanup()
        log.info("Gracefully shutdown the API")

    @route("/commands")
    async def commands(self: "Network", request: Request) -> Response:
        """
        Export command information as JSON, including commands within groups.
        """
        commands_info = []
        for command in self.bot.commands:
            if isinstance(command, group):
                for subcommand in command.commands:
                    command_info = {
                    "category": subcommand.cog_name or "Uncategorized",
                    "description": subcommand.help or "",
                    "name": f"{command.name} {subcommand.name}",
                    "parameters": [
                        {"name": param.name, "optional": param.default != param.empty}
                        for param in subcommand.clean_params.values()
                    ],
                    "permissions": (
                        [perm for perm in subcommand.permissions]
                        if subcommand.permissions
                        else ["N/A"]
                    ),
                    }
                    commands_info.append(command_info)
                else:
                    command_info = {
                        "category": command.cog_name or "Uncategorized",
                        "description": command.help or "",
                        "name": command.name,
                        "parameters": [
                        {"name": param.name, "optional": param.default != param.empty}
                        for param in command.clean_params.values()
                        ],
                        "permissions": (
                        [perm for perm in command.permissions]
                        if command.permissions
                        else ["N/A"]
                        ),
                    }
                    commands_info.append(command_info)
                return web.json_response(commands_info)

    @route("/status")
    async def status(self, request: Request) -> Response:
        return web.json_response(
            {
                "shards": [
                    {
                        "guilds": f"{len([guild for guild in self.bot.guilds if guild.shard_id == shard.id])}",
                        "id": f"{shard.id}",
                        "ping": f"{(shard.latency * 1000):.2f}ms",
                        "uptime": f"{int(self.bot.uptime2)}",
                        "users": f"{len([user for guild in self.bot.guilds for user in guild.members if not user.bot if guild.shard_id == shard.id])}",
                    }
                    for shard in self.bot.shards.values()
                ]
            }
        )

    @route("/tickets")
    @requires_auth
    async def tickets(self: "Network", request: Request) -> Response:
        ticket_id = request.query.get("id")
        user_id = request.headers.get("User-ID")
        authorization = request.headers.get("Authorization")

        log.info(
            f"Request received for ticket {ticket_id} with Authorization: {authorization} and User-ID: {user_id}"
        )

        if not ticket_id:
            return web.json_response({"error": "Missing ticket ID"}, status=400)
        if not user_id:
            return web.json_response({"error": "Missing User-ID header"}, status=400)

        ticket_path = f"/root/tickets/{ticket_id}.json"
        user_ids_path = f"/root/tickets/{ticket_id}_ids.json"

        if not os.path.isfile(ticket_path):
            log.warning(f"Ticket {ticket_id} not found.")
            return web.json_response({"error": "Ticket not found"}, status=404)

        if not os.path.isfile(user_ids_path):
            log.warning(f"Access list for ticket {ticket_id} not found.")
            return web.json_response(
                {"error": "Access list not found for ticket"}, status=404
            )

        try:
            with open(user_ids_path, "r") as ids_file:
                user_data = json.load(ids_file)
                if user_id not in map(str, user_data.get("ids", [])):
                    log.warning(
                        f"User {user_id} is not authorized to access ticket {ticket_id}."
                    )
                    return web.json_response(
                        {"error": "User not authorized to access this ticket"},
                        status=403,
                    )

            with open(ticket_path, "r") as file:
                ticket_data = json.load(file)

            log.info(f"Ticket {ticket_id} successfully fetched for User-ID: {user_id}.")
            return web.json_response(ticket_data)

        except Exception as e:
            log.error(f"Error reading ticket {ticket_id}: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

    @route("/levels")
    @requires_auth
    async def levels(self: "Network", request: Request) -> Response:
        """
        Fetch level information for all members in a guild including user avatar, username, display name, roles, and level roles.
        """
        guild_id = request.headers.get("X-GUILD-ID")
        if not guild_id:
            return web.json_response({"error": "Missing X-GUILD-ID header"}, status=400)

        try:
            guild_id = int(guild_id)
        except ValueError:
            return web.json_response({"error": "Invalid X-GUILD-ID header"}, status=400)

        guild_exists_query = """
        SELECT EXISTS(SELECT 1 FROM level.member WHERE guild_id = $1);
        """
        guild_exists = await self.bot.db.fetchval(guild_exists_query, guild_id)
        if not guild_exists:
            return web.json_response({"error": "Guild ID does not exist"}, status=404)

        level_query = """
        SELECT user_id, xp, level, total_xp, formula_multiplier
        FROM level.member
        INNER JOIN level.config
        ON level.member.guild_id = level.config.guild_id
        WHERE level.member.guild_id = $1;
        """
        level_records = await self.bot.db.fetch(level_query, guild_id)

        users_data = []
        for record in level_records:
            user = self.bot.get_user(record["user_id"])
            if user:
                avatar_url = (
                    str(user.avatar)
                    if user.avatar
                    else (
                        str(user.default_avatar_url)
                        if user.default_avatar_url
                        else None
                    )
                )

                users_data.append(
                    {
                        "user_id": record["user_id"],
                        "xp": record["xp"],
                        "level": record["level"],
                        "total_xp": record["total_xp"],
                        "max_xp": self.required_xp(
                            record["level"] + 1, record["formula_multiplier"]
                        ),
                        "avatar_url": avatar_url,
                        "username": user.name if user.name else "Unknown",
                        "display_name": (
                            user.display_name if user.display_name else "Unknown"
                        ),
                    }
                )

        level_roles_query = """
        SELECT role_id, level
        FROM level.role
        WHERE guild_id = $1
        """
        level_roles_records = await self.bot.db.fetch(level_roles_query, guild_id)

        level_roles = []
        guild = self.bot.get_guild(guild_id)
        for role in level_roles_records:
            discord_role = discord.utils.get(guild.roles, id=role["role_id"])
            if discord_role:
                level_roles.append(
                    {
                        "role_id": role["role_id"],
                        "level": role["level"],
                        "role_name": discord_role.name,
                        "hex_color": (
                            str(discord_role.color) if discord_role.color else None
                        ),
                    }
                )

        response_data = {
            "guild_id": guild_id,
            "guild_name": guild.name if guild else "Unknown Guild",
            "level_roles": level_roles,
            "users": users_data,
        }

        return web.json_response(response_data)

    @route("/statistics")
    @requires_auth
    async def statistics(self: "Network", request: Request) -> Response:
        try:
            guild_id = request.headers.get("X-GUILD-ID")
            days = int(request.headers.get("X-DAYS", "7"))

            if not guild_id:
                return web.json_response(
                    {"error": "Missing X-GUILD-ID header"}, status=400
                )

            dates = [
                (datetime.now(timezone.utc) - timedelta(days=i)).date()
                for i in range(days)
            ]

            stats_query = """
            SELECT 
                d.date::text,
                COALESCE(commands_used, 0) as commands_used,
                COALESCE(messages_sent, 0) as messages_sent,
                COALESCE(voice_minutes, 0) as voice_minutes
            FROM (
                SELECT unnest($1::date[]) AS date
            ) d
            LEFT JOIN statistics.daily sd 
                ON sd.date = d.date 
                AND sd.guild_id = $2
            ORDER BY d.date DESC;
            """

            mod_query = """
            SELECT 
                DATE(timestamp)::text as date,
                action,
                COUNT(*) as count
            FROM history.moderation
            WHERE guild_id = $1
                AND timestamp >= $2
                AND timestamp < $2 + INTERVAL '1 day' * $3
            GROUP BY DATE(timestamp), action
            ORDER BY date DESC;
            """

            stats_records = await self.bot.db.fetch(stats_query, dates, int(guild_id))
            mod_records = await self.bot.db.fetch(
                mod_query, int(guild_id), dates[-1], days
            )

            mod_by_date = {}
            for record in mod_records:
                if record["date"] not in mod_by_date:
                    mod_by_date[record["date"]] = {}
                mod_by_date[record["date"]][record["action"]] = record["count"]

            response_data = {
                "guild_id": guild_id,
                "days": days,
                "statistics": [
                    {
                        "date": record["date"],
                        "commands_used": record["commands_used"],
                        "messages_sent": record["messages_sent"],
                        "voice_minutes": record["voice_minutes"],
                        "moderation": mod_by_date.get(record["date"], {}),
                    }
                    for record in stats_records
                ],
            }

            return web.json_response(response_data)

        except ValueError as e:
            return web.json_response({"error": "Invalid X-DAYS value"}, status=400)
        except Exception as e:
            log.error(f"Error fetching statistics: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

    @route("/invokes")
    @requires_auth
    async def invokes(self: "Network", request: Request) -> Response:
        try:
            guild_id = request.headers.get("X-GUILD-ID")

            if not guild_id:
                return web.json_response(
                    {"error": "Missing X-GUILD-ID header"}, status=400
                )

            query = """
            SELECT 
                user_id,
                command_name,
                category,
                timestamp::text
            FROM invoke_history.commands
            WHERE 
                guild_id = $1
                AND timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
            ORDER BY timestamp DESC;
            """

            records = await self.bot.db.fetch(query, int(guild_id))

            unique_users = {record["user_id"] for record in records}
            users_data = []

            for user_id in unique_users:
                user = self.bot.get_user(user_id)
                if user:
                    avatar_url = (
                        str(user.avatar.url)
                        if user.avatar
                        else "https://cdn.discordapp.com/embed/avatars/1.png"
                    )
                    users_data.append(
                        {
                            "user_id": str(user_id),
                            "user_name": user.name,
                            "user_displayname": user.display_name,
                            "user_avatar": avatar_url,
                        }
                    )
                else:
                    users_data.append(
                        {
                            "user_id": str(user_id),
                            "user_name": "Unknown User",
                            "user_displayname": "Unknown User",
                            "user_avatar": "https://cdn.discordapp.com/embed/avatars/1.png",
                        }
                    )

            response_data = {
                "guild_id": guild_id,
                "total_invokes": len(records),
                "users": users_data,
                "invokes": [
                    {
                        "user_id": str(record["user_id"]),
                        "command": record["command_name"],
                        "category": record["category"],
                        "timestamp": record["timestamp"],
                    }
                    for record in records
                ],
            }

            return web.json_response(response_data)

        except Exception as e:
            log.error(f"Error fetching invoke history: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

    async def music_websocket(self, request: web.Request) -> web.WebSocketResponse:
        log.info(
            f"WebSocket connection attempt from {request.remote} for guild {request.match_info['guild_id']}"
        )

        ws = web.WebSocketResponse(protocols=["auth.2O91CtFwD3L2MXLI50V"])
        await ws.prepare(request)

        auth_protocol = next(
            (
                p
                for p in request.headers.getall("Sec-WebSocket-Protocol", [])
                if p.startswith("auth.")
            ),
            None,
        )
        if not auth_protocol or auth_protocol.split(".")[1] != "2O91CtFwD3L2MXLI50V":
            log.warning(
                f"Unauthorized WebSocket connection attempt from {request.remote}"
            )
            await ws.close(code=4001, message=b"Unauthorized")
            return ws

        guild_id = request.match_info["guild_id"]
        log.info(
            f"Authorized WebSocket connection established for guild {guild_id} from {request.remote}!!!"
        )

        if guild_id not in self.ws_connections:
            self.ws_connections[guild_id] = set()
        self.ws_connections[guild_id].add(ws)

        try:
            guild = self.bot.get_guild(int(guild_id))
            state_data = {
                "type": "STATE_UPDATE",
                "data": {
                    "current": None,
                    "queue": [],
                    "recentlyPlayed": [],
                    "controls": {
                        "volume": 100,
                        "isPlaying": False,
                        "repeat": "off",
                        "shuffle": False,
                    },
                },
            }

            if guild and guild.voice_client:
                voice_client = guild.voice_client
                if voice_client.current:
                    recent_tracks = await self.bot.db.fetch(
                        """
                        SELECT DISTINCT ON (title)
                            title, artist, duration, thumbnail, uri
                        FROM music.history
                        WHERE guild_id = $1
                        ORDER BY title, played_at DESC
                        LIMIT 10
                        """,
                        guild.id,
                    )

                    loop_mode = "off"
                    if voice_client.queue and voice_client.queue.loop_mode:
                        try:
                            loop_mode = voice_client.queue.loop_mode.value
                        except AttributeError:
                            loop_mode = "off"

                    state_data["data"].update(
                        {
                            "current": {
                                "title": voice_client.current.title,
                                "artist": voice_client.current.author,
                                "duration": voice_client.current.length,
                                "thumbnail": voice_client.current.thumbnail
                                or "https://cdn.discordapp.com/attachments/1173913793446527016/1175145799481962506/music.png",
                                "uri": voice_client.current.uri,
                                "position": voice_client.position,
                                "is_playing": not voice_client.is_paused,
                            },
                            "queue": [
                                {
                                    "title": t.title,
                                    "artist": t.author,
                                    "duration": t.length,
                                    "thumbnail": t.thumbnail
                                    or "https://cdn.discordapp.com/attachments/1173913793446527016/1175145799481962506/music.png",
                                    "uri": t.uri,
                                }
                                for t in (voice_client.queue or [])
                            ],
                            "recentlyPlayed": [
                                {
                                    "id": str(i),
                                    "title": record["title"],
                                    "artist": record["artist"],
                                    "duration": record["duration"],
                                    "thumbnail": record["thumbnail"],
                                }
                                for i, record in enumerate(recent_tracks)
                            ],
                            "controls": {
                                "volume": voice_client.volume,
                                "isPlaying": not voice_client.is_paused,
                                "repeat": loop_mode,
                                "shuffle": False,
                            },
                        }
                    )

            log.info(f"Sending initial state to new connection for guild {guild_id}")
            await ws.send_json(state_data)

            update_task = asyncio.create_task(self.periodic_music_updates(ws, guild_id))

            try:
                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)

                            if data.get("type") == "PING":
                                await ws.send_json({"type": "PONG"})
                                continue

                            command = data.get("command")
                            if not command:
                                continue

                            log.info(
                                f"Received WebSocket command '{command}' for guild {guild_id}"
                            )

                            audio_cog = self.bot.get_cog("Audio")
                            if not audio_cog:
                                log.error(
                                    f"Audio cog not available for guild {guild_id}"
                                )
                                await ws.send_json(
                                    {"error": "Audio system not available"}
                                )
                                continue

                            guild = self.bot.get_guild(int(guild_id))
                            if not guild:
                                log.error(f"Guild {guild_id} not found")
                                await ws.send_json({"error": "Guild not found"})
                                continue

                            voice_client = guild.voice_client
                            if not voice_client:
                                log.error(f"No voice client for guild {guild_id}")
                                await ws.send_json({"error": "Not connected to voice"})
                                continue

                            if command == "play":
                                if not voice_client.is_playing():
                                    await voice_client.resume()
                                    await ws.send_json({"network": "resumed"})
                                    log.info(f"Resumed playback for guild {guild_id}")

                            elif command == "pause":
                                if voice_client.is_playing():
                                    await voice_client.pause()
                                    await ws.send_json({"network": "paused"})
                                    log.info(f"Paused playback for guild {guild_id}")

                            elif command == "skip":
                                await voice_client.stop()
                                await ws.send_json({"network": "skipped"})
                                log.info(f"Skipped track for guild {guild_id}")

                            elif command == "seek":
                                position = data.get("position")
                                if position is not None:
                                    await voice_client.seek(position)
                                    await ws.send_json(
                                        {"network": "seeked", "position": position}
                                    )
                                    log.info(
                                        f"Seeked to position {position} for guild {guild_id}"
                                    )

                            elif command == "volume":
                                volume = data.get("volume")
                                if volume is not None:
                                    await voice_client.set_volume(volume)
                                    await ws.send_json(
                                        {"network": "volume_changed", "volume": volume}
                                    )
                                    log.info(
                                        f"Changed volume to {volume} for guild {guild_id}"
                                    )

                            elif command == "shuffle":
                                if voice_client.queue:
                                    voice_client.queue.shuffle()
                                    await ws.send_json({"network": "shuffled"})
                                    log.info(f"Shuffled queue for guild {guild_id}")

                            elif command == "repeat":
                                mode = data.get("mode")
                                if mode in ["track", "queue", "off"]:
                                    if mode == "track":
                                        voice_client.queue.set_loop_mode(LoopMode.TRACK)
                                    elif mode == "queue":
                                        voice_client.queue.set_loop_mode(LoopMode.QUEUE)
                                    else:
                                        voice_client.queue.disable_loop()
                                    await ws.send_json(
                                        {"network": "repeat_changed", "mode": mode}
                                    )
                                    log.info(
                                        f"Changed repeat mode to {mode} for guild {guild_id}"
                                    )

                            elif command == "play_index":
                                index = data.get("index")
                                if index is not None and voice_client.queue:
                                    if 0 <= index < len(voice_client.queue):
                                        track = voice_client.queue[index]
                                        voice_client.queue.remove(track)
                                        voice_client.queue._queue.insert(0, track)
                                        await voice_client.stop()
                                        await ws.send_json(
                                            {"network": "playing_index", "index": index}
                                        )
                                        log.info(
                                            f"Playing track at index {index} for guild {guild_id}"
                                        )

                            elif command == "next":
                                if voice_client.queue:
                                    next_track = voice_client.queue[0]
                                    await voice_client.stop()
                                    await ws.send_json(
                                        {
                                            "network": "next",
                                            "track": {
                                                "title": next_track.title,
                                                "artist": next_track.author,
                                                "duration": next_track.length,
                                                "thumbnail": next_track.thumbnail
                                                or self.default_thumbnail,
                                                "uri": next_track.uri,
                                            },
                                        }
                                    )
                                    log.info(f"Playing next track for guild {guild_id}")

                            elif command == "previous":
                                await ws.send_json({"network": "previous_not_supported"})
                                log.info(
                                    f"Previous track requested but not supported for guild {guild_id}"
                                )

                            elif command == "repeat":
                                mode = data.get("mode")
                                if mode in ["track", "queue", "off"]:
                                    if mode == "track":
                                        voice_client.queue.set_loop_mode(LoopMode.TRACK)
                                    elif mode == "queue":
                                        voice_client.queue.set_loop_mode(LoopMode.QUEUE)
                                    else:
                                        voice_client.queue.disable_loop()
                                    await ws.send_json(
                                        {"network": "repeat_changed", "mode": mode}
                                    )
                                    log.info(
                                        f"Changed repeat mode to {mode} for guild {guild_id}"
                                    )

                            elif command == "shuffle":
                                if voice_client.queue:
                                    voice_client.queue.shuffle()
                                    await ws.send_json({"network": "shuffled"})
                                    log.info(f"Shuffled queue for guild {guild_id}")

                            elif command == "playlist_create":
                                name = data.get("name")
                                thumbnail = data.get(
                                    "thumbnail", "default_thumbnail_url"
                                )
                                user_id = data.get("user_id")

                                if not user_id:
                                    await ws.send_json({"error": "Missing user_id"})
                                    continue

                                playlist_id = await self.bot.db.fetchval(
                                    """
                                    INSERT INTO music.playlists (guild_id, user_id, name, thumbnail)
                                    VALUES ($1, $2, $3, $4)
                                    RETURNING id
                                """,
                                    int(guild_id),
                                    int(user_id),
                                    name,
                                    thumbnail,
                                )

                                await ws.send_json(
                                    {
                                        "type": "PLAYLIST_CREATED",
                                        "data": {
                                            "id": playlist_id,
                                            "name": name,
                                            "thumbnail": thumbnail,
                                        },
                                    }
                                )

                            elif command == "playlist_delete":
                                playlist_id = data.get("playlist_id")
                                user_id = data.get("user_id")

                                if not playlist_id or not user_id:
                                    await ws.send_json(
                                        {"error": "Missing playlist_id or user_id"}
                                    )
                                    continue

                                await self.bot.db.execute(
                                    """
                                    DELETE FROM music.playlists 
                                    WHERE id = $1 AND user_id = $2 AND guild_id = $3
                                """,
                                    int(playlist_id),
                                    int(user_id),
                                    int(guild_id),
                                )

                                await ws.send_json(
                                    {
                                        "type": "PLAYLIST_DELETED",
                                        "data": {"id": playlist_id},
                                    }
                                )

                            elif command == "playlist_update":
                                playlist_id = data.get("playlist_id")
                                name = data.get("name")
                                thumbnail = data.get("thumbnail")
                                user_id = data.get("user_id")

                                if not playlist_id or not user_id:
                                    await ws.send_json(
                                        {"error": "Missing playlist_id or user_id"}
                                    )
                                    continue

                                await self.bot.db.execute(
                                    """
                                    UPDATE music.playlists 
                                    SET name = $1, thumbnail = $2, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = $3 AND user_id = $4 AND guild_id = $5
                                """,
                                    name,
                                    thumbnail,
                                    int(playlist_id),
                                    int(user_id),
                                    int(guild_id),
                                )

                                await ws.send_json(
                                    {
                                        "type": "PLAYLIST_UPDATED",
                                        "data": {
                                            "id": playlist_id,
                                            "name": name,
                                            "thumbnail": thumbnail,
                                        },
                                    }
                                )

                            elif command == "playlist_add_track":
                                playlist_id = data.get("playlist_id")
                                track = data.get("track")
                                user_id = data.get("user_id")

                                if not playlist_id or not user_id or not track:
                                    await ws.send_json(
                                        {
                                            "error": "Missing playlist_id, user_id, or track data"
                                        }
                                    )
                                    continue

                                await self.bot.db.execute(
                                    """
                                    INSERT INTO music.playlist_tracks 
                                    (playlist_id, title, artist, duration, thumbnail, uri, added_by)
                                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                                """,
                                    int(playlist_id),
                                    track["title"],
                                    track["artist"],
                                    track["duration"],
                                    track["thumbnail"],
                                    track["uri"],
                                    int(user_id),
                                )

                                await ws.send_json(
                                    {
                                        "type": "TRACK_ADDED",
                                        "data": {
                                            "playlist_id": playlist_id,
                                            "track": track,
                                        },
                                    }
                                )

                            elif command == "playlist_remove_track":
                                playlist_id = data.get("playlist_id")
                                track_id = data.get("track_id")
                                user_id = data.get("user_id")

                                if not playlist_id or not track_id or not user_id:
                                    await ws.send_json(
                                        {
                                            "error": "Missing playlist_id, track_id, or user_id"
                                        }
                                    )
                                    continue

                                await self.bot.db.execute(
                                    """
                                    DELETE FROM music.playlist_tracks 
                                    WHERE id = $1 AND playlist_id IN (
                                        SELECT id FROM music.playlists 
                                        WHERE id = $2 AND user_id = $3 AND guild_id = $4
                                    )
                                """,
                                    int(track_id),
                                    int(playlist_id),
                                    int(user_id),
                                    int(guild_id),
                                )

                                await ws.send_json(
                                    {
                                        "type": "TRACK_REMOVED",
                                        "data": {
                                            "playlist_id": playlist_id,
                                            "track_id": track_id,
                                        },
                                    }
                                )

                            elif command == "get_playlists":
                                user_id = data.get("user_id")

                                if not user_id:
                                    await ws.send_json({"error": "Missing user_id"})
                                    continue

                                playlists = await self.bot.db.fetch(
                                    """
                                    SELECT 
                                        p.id,
                                        p.name,
                                        p.thumbnail,
                                        p.created_at,
                                        p.updated_at,
                                        COALESCE(
                                            json_agg(
                                                json_build_object(
                                                    'id', pt.id,
                                                    'title', pt.title,
                                                    'artist', pt.artist,
                                                    'duration', pt.duration,
                                                    'thumbnail', pt.thumbnail,
                                                    'uri', pt.uri
                                                )
                                            ) FILTER (WHERE pt.id IS NOT NULL),
                                            '[]'
                                        ) as tracks
                                    FROM music.playlists p
                                    LEFT JOIN music.playlist_tracks pt ON p.id = pt.playlist_id
                                    WHERE p.user_id = $1 AND p.guild_id = $2
                                    GROUP BY p.id
                                    ORDER BY p.created_at DESC
                                """,
                                    int(user_id),
                                    int(guild_id),
                                )

                                await ws.send_json(
                                    {
                                        "type": "PLAYLISTS_FETCHED",
                                        "data": [
                                            {
                                                "id": row["id"],
                                                "name": row["name"],
                                                "thumbnail": row["thumbnail"],
                                                "created_at": (
                                                    row["created_at"].isoformat()
                                                    if row["created_at"]
                                                    else None
                                                ),
                                                "updated_at": (
                                                    row["updated_at"].isoformat()
                                                    if row["updated_at"]
                                                    else None
                                                ),
                                                "tracks": row["tracks"],
                                            }
                                            for row in playlists
                                        ],
                                    }
                                )

                        except json.JSONDecodeError:
                            log.error(f"Invalid JSON received from {request.remote}")
                            await ws.send_json({"error": "Invalid JSON"})
                        except Exception as e:
                            log.error(
                                f"Error handling command for guild {guild_id}: {e}"
                            )
                            await ws.send_json({"error": str(e)})

            except Exception as e:
                log.error(f"WebSocket error: {e}")
            finally:
                update_task.cancel()

            return ws

        finally:
            if guild_id in self.ws_connections:
                self.ws_connections[guild_id].remove(ws)
                if not self.ws_connections[guild_id]:
                    del self.ws_connections[guild_id]
                log.info(
                    f"WebSocket connection closed for guild {guild_id} from {request.remote}"
                )

    async def periodic_music_updates(self, ws: web.WebSocketResponse, guild_id: str):
        """Send periodic updates about the music state"""
        last_update = time.time()
        try:
            while True:
                current_time = time.time()
                guild = self.bot.get_guild(int(guild_id))

                state_data = {
                    "type": "STATE_UPDATE",
                    "data": {
                        "current": None,
                        "queue": [],
                        "recentlyPlayed": [],
                        "controls": {
                            "volume": 100,
                            "isPlaying": False,
                            "repeat": "off",
                            "shuffle": False,
                        },
                    },
                }

                if guild and guild.voice_client:
                    voice_client = guild.voice_client
                    if voice_client.current:
                        recent_tracks = await self.bot.db.fetch(
                            """
                            SELECT DISTINCT ON (title)
                                title, artist, duration, thumbnail, uri
                            FROM music.history
                            WHERE guild_id = $1
                            ORDER BY title, played_at DESC
                            LIMIT 10
                            """,
                            guild.id,
                        )

                        loop_mode = "off"
                        if voice_client.queue and voice_client.queue.loop_mode:
                            try:
                                loop_mode = voice_client.queue.loop_mode.value
                            except AttributeError:
                                loop_mode = "off"

                        state_data["data"].update(
                            {
                                "current": {
                                    "title": voice_client.current.title,
                                    "artist": voice_client.current.author,
                                    "duration": voice_client.current.length,
                                    "thumbnail": voice_client.current.thumbnail
                                    or "https://img.freepik.com/premium-photo/treble-clef-circle-musical-notes-black-background-design-3d-illustration_116124-10456.jpg?semt=ais",
                                    "uri": voice_client.current.uri,
                                    "position": voice_client.position,
                                    "is_playing": not voice_client.is_paused,
                                },
                                "queue": [
                                    {
                                        "title": t.title,
                                        "artist": t.author,
                                        "duration": t.length,
                                        "thumbnail": t.thumbnail
                                        or "https://img.freepik.com/premium-photo/treble-clef-circle-musical-notes-black-background-design-3d-illustration_116124-10456.jpg?semt=ais",
                                        "uri": t.uri,
                                    }
                                    for t in (voice_client.queue or [])
                                ],
                                "recentlyPlayed": [
                                    {
                                        "id": str(i),
                                        "title": record["title"],
                                        "artist": record["artist"],
                                        "duration": record["duration"],
                                        "thumbnail": record["thumbnail"],
                                    }
                                    for i, record in enumerate(recent_tracks)
                                ],
                                "controls": {
                                    "volume": voice_client.volume,
                                    "isPlaying": not voice_client.is_paused,
                                    "repeat": loop_mode,
                                    "shuffle": False,
                                },
                            }
                        )

                await ws.send_json(state_data)
                last_update = current_time

                await asyncio.sleep(1)

        except Exception as e:
            log.error(f"Error in periodic updates: {e}")

    async def broadcast_music_state(self, guild_id: str, data: dict):
        """Send music state updates to all connected clients for a guild"""
        if guild_id in self.ws_connections:
            for ws in self.ws_connections[guild_id]:
                try:
                    await ws.send_json(data)
                except Exception as e:
                    log.error(f"Error broadcasting music state: {e}")
                    self.ws_connections[guild_id].remove(ws)

    async def antinuke_websocket(self, request: web.Request) -> web.WebSocketResponse:
        log.info(
            f"WebSocket connection attempt from {request.remote} for guild {request.match_info['guild_id']}"
        )

        ws = web.WebSocketResponse(protocols=["auth.2O91CtFwD3L2MXLI50V"])
        await ws.prepare(request)

        auth_protocol = next(
            (
                p
                for p in request.headers.getall("Sec-WebSocket-Protocol", [])
                if p.startswith("auth.")
            ),
            None,
        )
        if not auth_protocol or auth_protocol.split(".")[1] != "2O91CtFwD3L2MXLI50V":
            log.warning(
                f"Unauthorized WebSocket connection attempt from {request.remote}"
            )
            await ws.close(code=4001, message=b"Unauthorized")
            return ws

        guild_id = request.match_info["guild_id"]
        guild = self.bot.get_guild(int(guild_id))

        if not guild:
            await ws.close(code=4004, message=b"Guild not found")
            return ws

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)

                        if data.get("type") == "PING":
                            await ws.send_json({"type": "PONG"})
                            continue

                        command = data.get("command")
                        if command == "get_antinuke":
                            settings = await Settings.fetch(self.bot, guild)

                            protection_data = {
                                "bot": {
                                    "enabled": settings.bot,
                                    "threshold": 1,
                                    "duration": 60,
                                },
                                "ban": {
                                    "enabled": bool(settings.ban),
                                    "threshold": (
                                        settings.ban.threshold if settings.ban else None
                                    ),
                                    "duration": (
                                        settings.ban.duration if settings.ban else None
                                    ),
                                },
                                "kick": {
                                    "enabled": bool(settings.kick),
                                    "threshold": (
                                        settings.kick.threshold
                                        if settings.kick
                                        else None
                                    ),
                                    "duration": (
                                        settings.kick.duration
                                        if settings.kick
                                        else None
                                    ),
                                },
                                "role": {
                                    "enabled": bool(settings.role),
                                    "threshold": (
                                        settings.role.threshold
                                        if settings.role
                                        else None
                                    ),
                                    "duration": (
                                        settings.role.duration
                                        if settings.role
                                        else None
                                    ),
                                },
                                "channel": {
                                    "enabled": bool(settings.channel),
                                    "threshold": (
                                        settings.channel.threshold
                                        if settings.channel
                                        else None
                                    ),
                                    "duration": (
                                        settings.channel.duration
                                        if settings.channel
                                        else None
                                    ),
                                },
                                "webhook": {
                                    "enabled": bool(settings.webhook),
                                    "threshold": (
                                        settings.webhook.threshold
                                        if settings.webhook
                                        else None
                                    ),
                                    "duration": (
                                        settings.webhook.duration
                                        if settings.webhook
                                        else None
                                    ),
                                },
                                "emoji": {
                                    "enabled": bool(settings.emoji),
                                    "threshold": (
                                        settings.emoji.threshold
                                        if settings.emoji
                                        else None
                                    ),
                                    "duration": (
                                        settings.emoji.duration
                                        if settings.emoji
                                        else None
                                    ),
                                },
                            }

                            await ws.send_json(
                                {"type": "ANTINUKE_SETTINGS", "data": protection_data}
                            )

                        elif command == "update_antinuke":
                            module = data.get("module")
                            enabled = data.get("enabled")
                            threshold = data.get("threshold")
                            duration = data.get("duration")

                            if not module:
                                await ws.send_json({"error": "Missing module name"})
                                continue

                            if module not in [
                                "bot",
                                "ban",
                                "kick",
                                "role",
                                "channel",
                                "webhook",
                                "emoji",
                            ]:
                                await ws.send_json({"error": "Invalid module name"})
                                continue

                            settings = await Settings.fetch(self.bot, guild)

                            if module == "bot":
                                await self.bot.db.execute(
                                    """
                                    UPDATE antinuke
                                    SET bot = $2
                                    WHERE guild_id = $1
                                    """,
                                    guild.id,
                                    enabled,
                                )
                            else:
                                if enabled:
                                    module_settings = Module(
                                        threshold=threshold, duration=int(duration)
                                    )
                                    await self.bot.db.execute(
                                        f"""
                                        UPDATE antinuke
                                        SET {module} = $2
                                        WHERE guild_id = $1
                                        """,
                                        guild.id,
                                        module_settings.dict(),
                                    )
                                else:
                                    await self.bot.db.execute(
                                        f"""
                                        UPDATE antinuke
                                        SET {module} = NULL
                                        WHERE guild_id = $1
                                        """,
                                        guild.id,
                                    )

                            await Settings.revalidate(self.bot, guild)
                            settings = await Settings.fetch(self.bot, guild)

                            module_data = {"enabled": enabled}
                            if enabled and module != "bot":
                                module_data.update(
                                    {
                                        "threshold": (
                                            getattr(settings, module).threshold
                                            if getattr(settings, module)
                                            else None
                                        ),
                                        "duration": (
                                            getattr(settings, module).duration
                                            if getattr(settings, module)
                                            else None
                                        ),
                                    }
                                )

                            await ws.send_json(
                                {
                                    "type": "ANTINUKE_UPDATED",
                                    "data": {"module": module, "settings": module_data},
                                }
                            )

                    except json.JSONDecodeError:
                        log.error(f"Invalid JSON received from {request.remote}")
                        await ws.send_json({"error": "Invalid JSON"})
                    except Exception as e:
                        log.error(f"Error handling command for guild {guild_id}: {e}")
                        await ws.send_json({"error": str(e)})

        except Exception as e:
            log.error(f"Error in antinuke websocket: {e}")
        finally:
            return ws

    @route("/spotify/auth", ["POST"])
    @requires_not_auth
    async def spotify_auth(self: "Network", request: Request) -> Response:
        try:
            data = await request.json()
            
            required_fields = {
                "user_id": data.get("user_id"),
                "spotify_access_token": data.get("spotify_access_token"), 
                "spotify_refresh_token": data.get("spotify_refresh_token"),
                "expires_in": data.get("expires_in"),
                "spotify_id": data.get("spotify_id")
            }

            if missing := [k for k, v in required_fields.items() if not v]:
                return web.json_response(
                    {"error": f"Missing required fields: {', '.join(missing)}"},
                    status=400
                )

            current_time = datetime.now(timezone.utc)
            expires_at = (current_time + timedelta(seconds=int(required_fields["expires_in"])))
            
            expires_at_ts = expires_at.replace(tzinfo=None)

            await self.bot.db.execute(
                """
                INSERT INTO user_spotify (
                    user_id, access_token, refresh_token, token_expires_at, spotify_id
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token, 
                    token_expires_at = EXCLUDED.token_expires_at,
                    spotify_id = EXCLUDED.spotify_id
                """,
                int(required_fields["user_id"]),
                required_fields["spotify_access_token"],
                required_fields["spotify_refresh_token"], 
                expires_at_ts, 
                required_fields["spotify_id"]
            )

            return web.json_response({"success": True})
            
        except Exception as e:
            log.error(f"Error processing Spotify auth: {str(e)}", exc_info=True)
            return web.json_response({"error": "Internal server error"}, status=500)

    async def handle_options(self, request):
        return web.Response(status=200)

    @route("/lastfm/auth", ["POST"])
    @requires_not_auth
    async def lastfm_auth(self: "Network", request: Request) -> Response:
        try:
            data = await request.json()
            
            required_fields = {
                "user_id": data.get("user_id"),
                "access_token": data.get("access_token"),
                "username": data.get("username")
            }

            if missing := [k for k, v in required_fields.items() if not v]:
                return web.json_response(
                    {"error": f"Missing required fields: {', '.join(missing)}"},
                    status=400
                )

            await self.bot.db.execute(
                """
                INSERT INTO lastfm.config (
                    user_id, access_token, username, web_authentication
                ) VALUES ($1, $2, $3, true)
                ON CONFLICT (user_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    username = EXCLUDED.username,
                    web_authentication = true
                """,
                int(required_fields["user_id"]),
                required_fields["access_token"],
                required_fields["username"]
            )

            return web.json_response({"success": True})
            
        except Exception as e:
            log.error(f"Error processing Last.fm auth: {str(e)}", exc_info=True)
            return web.json_response({"error": "Internal server error"}, status=500)

    async def can_send_failure_notification(self, user_id: int) -> bool:
        """Check if we can send a failure notification to the user (max 2 per hour)"""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        
        self.failed_payment_notifications[user_id] = [
            timestamp for timestamp in self.failed_payment_notifications[user_id]
            if timestamp > hour_ago
        ]
        
        return len(self.failed_payment_notifications[user_id]) < 2

    @route("/stripe-webhook", ["POST"])
    async def stripe_webhook(self: "Network", request: Request) -> Response:
        try:
            payload = await request.text()
            sig_header = request.headers.get('Stripe-Signature')

            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, "whsec_ugClyU2MEMyWCgnQfrl2vsiXQNZtDsDG"
                )
            except ValueError:
                log.error("Invalid Stripe payload received")
                return web.json_response({"error": "Invalid payload"}, status=400)
            except stripe.error.SignatureVerificationError:
                log.error("Invalid Stripe signature")
                return web.json_response({"error": "Invalid signature"}, status=400)

            log_channel = self.bot.get_channel(1319933684576550922)
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                discord_id = None
                if 'custom_fields' in session:
                    for field in session['custom_fields']:
                        if field['key'] == 'useriddiscord':
                            discord_id = field['text']['value']
                            break
                
                if discord_id:
                    try:
                        user = await self.bot.fetch_user(int(discord_id))
                        guild = self.bot.get_guild(892675627373699072)
                        member = await guild.fetch_member(int(discord_id))

                        embed = Embed(
                            title="Thank You for Supporting evict!",
                            description=(
                                "Your donation has been received and processed successfully! 🎉\n\n"
                                "You now have access to premium features including:\n"
                                "- Custom bot reskins\n"
                                "- Extended limits for OpenAI features\n"
                                "- Enhanced transcription capabilities\n"
                                "- Priority support\n\n"
                                "Thank you for helping keep evict running! ❤️"
                            ),
                            color=0x2ecc71
                        )
                        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                        await user.send(embed=embed)

                        role = guild.get_role(1318054098666389534)
                        if role and role not in member.roles:
                            await member.add_roles(role, reason="Donation received")

                        if log_channel:
                            log_embed = Embed(
                                title="New Donation Received",
                                description=(
                                    f"User: {user.mention} (`{user.id}`)\n"
                                    f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
                                    f"Payment ID: `{session['payment_intent']}`"
                                ),
                                color=0x2ecc71,
                                timestamp=datetime.now(timezone.utc)
                            )
                            await log_channel.send(embed=log_embed)

                        return web.json_response({"success": True})

                    except Exception as e:
                        log.error(f"Failed to process donation for user {discord_id}: {e}")
                        if log_channel:
                            error_embed = Embed(
                                title="Donation Processing Failed",
                                description=(
                                    f"Failed to process donation for Discord ID: `{discord_id}`\n"
                                    f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
                                    f"Payment ID: `{session['payment_intent']}`\n"
                                    f"Error: ```{str(e)}```"
                                ),
                                color=0xff0000,
                                timestamp=datetime.now(timezone.utc)
                            )
                            await log_channel.send(embed=error_embed)
                        return web.json_response(
                            {"error": f"Failed to process donation: {str(e)}"}, 
                            status=500
                        )
                else:
                    if log_channel:
                        error_embed = Embed(
                            title="Donation Processing Failed",
                            description=(
                                "Payment received but no Discord ID provided\n"
                                f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
                                f"Payment ID: `{session['payment_intent']}`\n"
                                f"Raw session data: ```{json.dumps(session, indent=2)}```"
                            ),
                            color=0xff0000,
                            timestamp=datetime.now(timezone.utc)
                        )
                        await log_channel.send(embed=error_embed)
                    return web.json_response(
                        {"error": "Missing discord_user_id in metadata"}, 
                        status=400
                    )

            elif event['type'] == 'checkout.session.expired':
                session = event['data']['object']
                discord_id = session['metadata'].get('discord_user_id')
                if log_channel:
                    embed = Embed(
                        title="Checkout Session Expired",
                        description=(
                            f"Discord ID: `{discord_id if discord_id else 'Not provided'}`\n"
                            f"Session ID: `{session['id']}`"
                        ),
                        color=0xffa500,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=embed)

            elif event['type'] == 'payment_intent.payment_failed':
                intent = event['data']['object']
                discord_id = None
                
                if 'custom_fields' in intent:
                    for field in intent['custom_fields']:
                        if field['key'] == 'useriddiscord':
                            discord_id = field['text']['value']
                            break
                
                if log_channel:
                    embed = Embed(
                        title="Payment Failed",
                        description=(
                            f"Discord ID: `{discord_id if discord_id else 'Not provided'}`\n"
                            f"Payment ID: `{intent['id']}`\n"
                            f"Error: `{intent['last_payment_error']['message'] if intent.get('last_payment_error') else 'Unknown error'}`"
                        ),
                        color=0xff0000,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=embed)

                if discord_id:
                    try:
                        user_id = int(discord_id)
                        if await self.can_send_failure_notification(user_id):
                            user = await self.bot.fetch_user(user_id)
                            error_message = (
                                intent['last_payment_error']['message'] 
                                if intent.get('last_payment_error') 
                                else 'Unknown error'
                            )
                            
                            embed = Embed(
                                title="Payment Failed",
                                description=(
                                    "Your payment to evict could not be processed.\n\n"
                                    f"Reason: {error_message}\n\n"
                                    "You can try again with a different payment method or contact your bank "
                                    "if you believe this is an error."
                                ),
                                color=0xff0000,
                                timestamp=datetime.now(timezone.utc)
                            )
                            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                            await user.send(embed=embed)
                            
                            self.failed_payment_notifications[user_id].append(datetime.now(timezone.utc))
                    except Exception as e:
                        log.error(f"Failed to send payment failure notification to user {discord_id}: {e}")

            return web.json_response({"success": True})

        except Exception as e:
            log.error(f"Error processing webhook: {e}")
            if log_channel:
                error_embed = Embed(
                    title="Webhook Processing Error",
                    description=f"Error: ```{str(e)}```",
                    color=0xff0000,
                    timestamp=datetime.now(timezone.utc)
                )
                await log_channel.send(embed=error_embed)
            return web.json_response({"error": "Internal server error"}, status=500)