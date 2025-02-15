import datetime
import discord
import config

from main import Evict

from discord import (
    abc,
    Embed,
    Guild,
    HTTPException,
    Member
)
from discord.ext.commands import Cog
from discord.ui import View, Button

from typing import cast
from contextlib import suppress

class Listeners(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot

    @Cog.listener("on_guild_join")
    async def guild_join_logger(self, guild: Guild):
        await self.log_guild_event(guild, "joined")

    @Cog.listener("on_guild_remove")
    async def guild_leave_logger(self, guild: Guild):
        await self.log_guild_event(guild, "left")

    async def log_guild_event(self, guild: Guild, event_type: str):
        """
        Log guild join or leave events to a channel.
        """
        channel_id = config.LOGGER.GUILD_JOIN_LOGGER
        channel = self.bot.get_channel(channel_id)

        icon = f"[icon]({guild.icon.url})" if guild.icon is not None else "N/A"
        splash = f"[splash]({guild.splash.url})" if guild.splash is not None else "N/A"
        banner = f"[banner]({guild.banner.url})" if guild.banner is not None else "N/A"

        action = "Evict has joined a guild." if event_type == "joined" else "Evict has left a guild."
        embed = Embed(
            timestamp=datetime.datetime.now(),
            description=action,
        )
        embed.set_thumbnail(url=guild.icon)
        embed.set_author(name=guild.name, url=guild.icon)
        embed.add_field(name="Owner", value=f"{guild.owner.mention}\n{guild.owner}")
        embed.add_field(
            name="Members",
            value=(
                f"**Users:** {len(set(i for i in guild.members if not i.bot))} "
                f"({((len(set(i for i in guild.members if not i.bot)))/guild.member_count) * 100:.2f}%)\n"
                f"**Bots:** {len(set(i for i in guild.members if i.bot))} "
                f"({(len(set(i for i in guild.members if i.bot))/guild.member_count) * 100:.2f}%)\n"
                f"**Total:** {guild.member_count}"
            ),
        )
        embed.add_field(
            name="Information",
            value=(
                f"**Verification:** {guild.verification_level}\n"
                f"**Boosts:** {guild.premium_subscription_count} (level {guild.premium_tier})\n"
                f"**Large:** {'yes' if guild.large else 'no'}"
            ),
        )
        embed.add_field(name="Design", value=f"{icon}\n{splash}\n{banner}")
        embed.add_field(
            name=f"Channels ({len(guild.channels)})",
            value=(
                f"**Text:** {len(guild.text_channels)}\n"
                f"**Voice:** {len(guild.voice_channels)}\n"
                f"**Categories:** {len(guild.categories)}"
            ),
        )
        embed.add_field(
            name="Counts",
            value=(
                f"**Roles:** {len(guild.roles)}/250\n"
                f"**Emojis:** {len(guild.emojis)}/{guild.emoji_limit * 2}\n"
                f"**Stickers:** {len(guild.stickers)}/{guild.sticker_limit}"
            ),
        )
        embed.set_footer(text=f"Guild ID: {guild.id}")

        if guild.banner:
            embed.set_image(url=guild.banner)

        view = None
        if guild.vanity_url_code:
            view = View()
            button = Button(label="Invite", url=f"https://discord.gg/{guild.vanity_url_code}")
            view.add_item(button)

        await channel.send(embed=embed, view=view, silent=True)

    @Cog.listener("on_guild_join")
    async def join_message(self, guild: Guild):
        """
        Set a custom join message upon bot join.
        """
        channel = discord.utils.find(
            lambda c: (
                isinstance(c, discord.TextChannel) and 
                c.permissions_for(guild.me).send_messages and 
                c.permissions_for(guild.me).embed_links
            ), 
            guild.text_channels
        )

        if not channel:
            print(f"No suitable channel found in guild {guild.id}")
            return

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

        await channel.send(embed=embed)
        try:
            await guild.owner.send(embed=embed)
        except discord.Forbidden:
            pass

    @Cog.listener("on_guild_join")
    async def blacklist_check(self, guild: Guild) -> None:
        """
        Check if a server is blacklisted upon join.
        """
        blacklisted = cast(
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
        if blacklisted:
            with suppress(HTTPException):
                await guild.leave()

            return

    @Cog.listener("on_guild_channel_create")
    async def jail(self, channel: abc.GuildChannel):
        """
        Set jail permissions when a new channel is created.
        """
        check = await self.bot.db.fetchrow(
            """
            SELECT * FROM mod 
            WHERE guild_id = $1
            """,
            channel.guild.id
        )

        if check:
            await channel.set_permissions(
                channel.guild.get_role(int(check["role_id"])),
                view_channel=False,
                reason="overwriting permissions for jail role",
            )

    @Cog.listener("on_member_join")
    async def join_jail(self, member: Member):
        """
        Rejail a member upon member join.
        """
        check = await self.bot.db.fetchrow(
            """
            SELECT * FROM jail 
            WHERE guild_id = $1 
            AND user_id = $2
            """,
            member.guild.id, 
            member.id
        )
        
        if check:
            chec = await self.bot.db.fetchrow(
                """
                SELECT * FROM mod 
                WHERE guild_id = $1
                """,
                member.guild.id
            )
            
            if chec:
                try:
                    await member.add_roles(
                        member.guild.get_role(int(chec["role_id"])),
                        reason="jailed before leaving",
                    )
                except discord.Forbidden:
                    return