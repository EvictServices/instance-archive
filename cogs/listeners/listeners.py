from logging import getLogger
from main import Evict

from discord.ext.commands import Cog
from discord.ext import commands, tasks
from discord import (
    abc,
    Embed,
    Guild,
    HTTPException,
    Message,
    Member
)

from discord.ui import View, Button

from typing import cast
from contextlib import suppress

import datetime
import discord
import config
import processors.listeners as processors

log = getLogger(__name__)

class Listeners(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self._guild_cache = {}
        self._jail_cache = {}

    @Cog.listener("on_guild_join")
    async def guild_join_logger(self, guild: Guild):
        await self.log_guild_event(guild, "joined")

    @Cog.listener("on_guild_remove")
    async def guild_leave_logger(self, guild: Guild):
        await self.log_guild_event(guild, "left")

    async def log_guild_event(self, guild: Guild, event_type: str) -> Message:
        """
        Log guild join or leave events to a channel.
        """
        channel = self.bot.get_channel(config.LOGGER.GUILD_JOIN_LOGGER)
        if not channel:
            return

        cache_key = f"guild_stats:{guild.id}"
        stats = await self.bot.redis.get(cache_key)
        
        if not stats:
            guild_data = {
                'members': [{'bot': m.bot} for m in guild.members],
                'member_count': guild.member_count
            }
            
            stats = await self.bot.loop.run_in_executor(
                None,
                self.bot.process_pool.apply,
                processors.process_guild_data,
                (guild_data,)
            )
            await self.bot.redis.set(cache_key, stats, ex=300)

        icon = f"[icon]({guild.icon.url})" if guild.icon else "N/A"
        splash = f"[splash]({guild.splash.url})" if guild.splash else "N/A"
        banner = f"[banner]({guild.banner.url})" if guild.banner else "N/A"

        embed = Embed(
            timestamp=datetime.datetime.now(),
            description=f"Evict has {'joined' if event_type == 'joined' else 'left'} a guild."
        )
        embed.set_thumbnail(url=guild.icon)
        embed.set_author(name=guild.name, url=guild.icon)
        
        fields = {
            "Owner": f"{guild.owner.mention}\n{guild.owner}",
            "Members": (
                f"**Users:** {stats['user_count']} ({stats['user_percentage']:.2f}%)\n"
                f"**Bots:** {stats['bot_count']} ({stats['bot_percentage']:.2f}%)\n"
                f"**Total:** {guild.member_count}"
            ),
            "Information": (
                f"**Verification:** {guild.verification_level}\n"
                f"**Boosts:** {guild.premium_subscription_count} (level {guild.premium_tier})\n"
                f"**Large:** {'yes' if guild.large else 'no'}"
            ),
            "Design": f"{icon}\n{splash}\n{banner}",
            f"Channels ({len(guild.channels)})": (
                f"**Text:** {len(guild.text_channels)}\n"
                f"**Voice:** {len(guild.voice_channels)}\n"
                f"**Categories:** {len(guild.categories)}"
            ),
            "Counts": (
                f"**Roles:** {len(guild.roles)}/250\n"
                f"**Emojis:** {len(guild.emojis)}/{guild.emoji_limit * 2}\n"
                f"**Stickers:** {len(guild.stickers)}/{guild.sticker_limit}"
            )
        }
        
        for name, value in fields.items():
            embed.add_field(name=name, value=value)

        embed.set_footer(text=f"Guild ID: {guild.id}")
        if guild.banner:
            embed.set_image(url=guild.banner)

        view = None
        if guild.vanity_url_code:
            view = View()
            view.add_item(Button(label="Invite", url=f"https://discord.gg/{guild.vanity_url_code}"))

        return await channel.send(embed=embed, view=view, silent=True)

    @Cog.listener("on_guild_join")
    async def join_message(self, guild: Guild) -> Message:
        """
        Set a custom join message upon bot join.
        """
        embed = Embed(
            title="Getting Started With Evict",
            description=(
                "Hey! Thanks for your interest in **evict bot**. "
                "The following will provide you with some tips on how to get started with your server!"
            ),
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar)

        embed.add_field(
            name="**Prefix 🤖**",
            value=(
                "The most important thing is my prefix. "
                f"It is set to `;` by default for this server and it is also customizable, "
                "so if you don't like this prefix, you can always change it with `prefix` command!"
            ),
            inline=False,
        )

        embed.add_field(
            name="**Documentation and Help 📚**",
            value=(
                "You can always visit our [documentation](https://docs.evict.bot)"
                " and view the list of commands that are available [here](https://evict.bot/commands)"
                " - and if that isn't enough, feel free to join our [Support Server](https://discord.gg/evict) for extra assistance!"
            ),
        )

        await self.bot.notify(guild, embed=embed)
        try:
            await guild.owner.send(embed=embed)
        except discord.Forbidden:
            pass

    @Cog.listener("on_guild_join")
    async def blacklist_check(self, guild: Guild) -> None:
        """
        Check if a server or server owner is blacklisted upon join.
        """
        guild_blacklisted = cast(
            bool,
            await self.bot.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM guildblacklist
                    WHERE guild_id = $1
                )
                """,
                guild.id,
            ),
        )
        
        owner_blacklisted = cast(
            bool,
            await self.bot.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM blacklist
                    WHERE user_id = $1
                )
                """,
                guild.owner_id,
            ),
        )
        if guild_blacklisted or owner_blacklisted:
            with suppress(HTTPException):
                await guild.leave()
            return

    @Cog.listener("on_guild_channel_create")
    async def jail(self, channel: abc.GuildChannel):
        """Set jail permissions when a new channel is created."""
        cache_key = f"jail_role:{channel.guild.id}"
        role_id = await self.bot.redis.get(cache_key)
        
        if role_id is None:
            check = await self.bot.db.fetchrow(
                "SELECT role_id FROM mod WHERE guild_id = $1",
                channel.guild.id
            )
            if not check:
                return
                
            role_id = check['role_id']
            await self.bot.redis.set(cache_key, role_id, ex=300)

        role = channel.guild.get_role(int(role_id))
        if not role:
            return

        try:
            perms = await self.bot.loop.run_in_executor(
                None,
                self.bot.process_pool.apply,
                processors.process_jail_permissions,
                (channel.id, role.id)
            )
            
            await channel.set_permissions(
                role,
                reason="overwriting permissions for jail role",
                **perms
            )
        except Exception as e:
            log.error(f"Failed to set jail permissions: {e}")

    @Cog.listener("on_member_join")
    async def join_jail(self, member: Member):
        """Rejail a member upon member join."""
        cache_key = f"jail_member:{member.guild.id}:{member.id}"
        is_jailed = await self.bot.redis.get(cache_key)
        
        if is_jailed is None:
            check = await self.bot.db.fetchrow(
                "SELECT 1 FROM jail WHERE guild_id = $1 AND user_id = $2",
                member.guild.id, member.id
            )
            is_jailed = bool(check)
            await self.bot.redis.set(cache_key, int(is_jailed), ex=300)
            
        if not is_jailed:
            return
            
        role_id = await self.bot.redis.get(f"jail_role:{member.guild.id}")
        if role_id is None:
            chec = await self.bot.db.fetchrow(
                "SELECT role_id FROM mod WHERE guild_id = $1",
                member.guild.id
            )
            if not chec:
                return
                
            role_id = chec['role_id']
            await self.bot.redis.set(f"jail_role:{member.guild.id}", role_id, ex=300)
            
        try:
            role = member.guild.get_role(int(role_id))
            if role:
                await self.bot.loop.run_in_executor(
                    None,
                    member.add_roles,
                    role,
                    reason="jailed before leaving"
                )
        except discord.Forbidden:
            pass

    # @Cog.listener("on_guild_join")
    # async def member_count(self, guild: Guild):
    #     """
    #     Update member count upon guild join.
    #     """
    #     if guild.member_count <= 50:
    #         await guild.leave()

    @Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} cog has been loaded")