import datetime
import discord
import config
import humanize

from main import Evict
from core.client.context import Context
from tools.conversion.embed1 import EmbedScript

from typing import Union
from datetime import timedelta

from discord import (
    Member, 
    User, 
    Embed,
    Interaction,
    ButtonStyle
)
from discord.ui import Button, View
from discord.ext import commands

class Mod:
    def is_mod_configured():
        async def predicate(ctx: Context):
            check = await ctx.bot.db.fetchrow(
                """
                SELECT * FROM mod 
                WHERE guild_id = $1
                """, 
                ctx.guild.id
            )

            if not check:
                await ctx.warn(
                    f"Moderation isn't **enabled** in this server. Enable it using `{ctx.clean_prefix}setme` command"
                )
                return False
            return True

        return commands.check(predicate)


class ModConfig:
    async def sendlogs(
        bot: Evict,
        action: str,
        author: Member,
        victim: Union[Member, User],
        reason: str,
        duration: Union[timedelta, int, None] = None,
    ):
        action_data = {
            'action': action,
            'duration': duration
        }

        processed_action = {
            'should_dm': True,
            'title': action,
            'is_unaction': False,
            'is_antinuke': False,
            'is_antiraid': False
        }

        settings = await bot.db.fetchrow(
            """
            SELECT * FROM mod 
            WHERE guild_id = $1
            """,
            author.guild.id
        )

        if not settings:
            return

        res = await bot.db.fetchrow(
            """
            SELECT count 
            FROM cases 
            WHERE guild_id = $1
            """, 
            author.guild.id
        )
        case = int(res["count"]) + 1

        await bot.db.execute(
            """
            UPDATE cases SET count = $1 
            WHERE guild_id = $2
            """, 
            case, 
            author.guild.id
        )

        duration_value = (
            int(duration.total_seconds())
            if isinstance(duration, timedelta)
            else duration
        )

        await bot.db.execute(
            """
            INSERT INTO history.moderation 
            (guild_id, case_id, user_id, moderator_id, action, reason, duration)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            author.guild.id,
            case,
            victim.id,
            author.id,
            action,
            reason,
            duration_value,
        )

        if settings.get("channel_id"):
            embed = Embed(timestamp=datetime.datetime.now())
            embed.set_author(name="Modlog Entry", icon_url=author.display_avatar)
            duration_text = (
                f"\n**Duration**: {humanize.naturaldelta(duration)}" if duration else ""
            )
            embed.add_field(
                name="Information",
                value=f"**Case #{case}** | {action}\n**User **: {victim} (`{victim.id}`)\n**Moderator**: {author} (`{author.id}`)\n**Reason**: {reason}{duration_text}",
            )

            try:
                await author.guild.get_channel(int(settings["channel_id"])).send(embed=embed)
            except:
                pass

        if processed_action['should_dm'] and settings.get("dm_enabled"):
            try:
                script = settings.get(f"dm_{action.lower()}")
                
                if script:
                    script_obj = EmbedScript(script)
                    await script_obj.send(
                        victim,
                        guild=author.guild,
                        moderator=author,
                        reason=reason,
                        duration=duration
                    )
                else:
                    duration_text = f"{humanize.naturaldelta(duration)}" if duration else ""
                    embed = Embed(
                        title=processed_action['title'].title(),
                        description=duration_text if duration else "",
                        color=discord.Color.green() if processed_action['is_unaction'] else discord.Color.red(),
                        timestamp=datetime.datetime.now()
                    )
                    embed.add_field(
                        name=f"You have been {processed_action['title']} in",
                        value=author.guild.name,
                        inline=True
                    )
                    embed.add_field(
                        name="Moderator",
                        value=str(author),
                        inline=True
                    )
                    embed.add_field(
                        name="Reason",
                        value=reason,
                        inline=True
                    )

                    if action == "unban":
                        try:
                            channels = [channel for channel in author.guild.text_channels 
                                        if channel.permissions_for(author.guild.me).create_instant_invite]
                            
                            if channels:
                                try:
                                    invite = await channels[0].create_invite(
                                        max_age=0,
                                        max_uses=0, 
                                        reason="Unban notification",
                                        unique=False 
                                    )
                                    
                                    if invite:
                                        view = InviteButton(invite.url)
                                        embed.set_footer(text="To dispute this action, contact a moderator")
                                        try:
                                            await victim.send(embed=embed, view=view)
                                            return
                                        except (discord.Forbidden, discord.HTTPException):
                                            pass
                                except discord.HTTPException:
                                    pass
                        except Exception:
                            pass

                    if processed_action['is_antinuke'] or processed_action['is_antiraid']:
                        try:
                            owner = author.guild.owner
                            if owner and owner.id != victim.id:
                                owner_embed = Embed(
                                    title=f"Security Alert: {processed_action['title']}",
                                    description=duration_text if duration else "",
                                    color=discord.Color.red(),
                                    timestamp=datetime.datetime.now()
                                )
                                owner_embed.add_field(
                                    name="User ",
                                    value=f"{victim} (`{victim.id}`)",
                                    inline=True
                                )
                                owner_embed.add_field(
                                    name="Action",
                                    value=action,
                                    inline=True
                                )
                                owner_embed.add_field(
                                    name="Reason",
                                    value=reason,
                                    inline=True
                                )
                                await owner.send(embed=owner_embed)
                        except (discord.Forbidden, discord.HTTPException):
                            pass

                    if action != "unban":
                        try:
                            await victim.send(embed=embed)
                        except (discord.Forbidden, discord.HTTPException):
                            pass

            except (discord.Forbidden, discord.HTTPException):
                pass

class ClearMod(View):
    def __init__(self, ctx: Context):
        super().__init__()
        self.ctx = ctx
        self.status = False

    @discord.ui.button(emoji=config.EMOJIS.CONTEXT.APPROVE)
    async def yes(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.warn("You are not the author of this embed")

        check = await interaction.client.db.fetchrow(
            """
            SELECT * FROM mod 
            WHERE guild_id = $1
            """, 
            interaction.guild.id
        )

        channelid = check["channel_id"]
        roleid = check["role_id"]
        logsid = check["jail_id"]

        channel = interaction.guild.get_channel(channelid)
        role = interaction.guild.get_role(roleid)
        logs = interaction.guild.get_channel(logsid)

        try:
            await channel.delete()
        except:
            pass

        try:
            await role.delete()
        except:
            pass

        try:
            await logs.delete()
        except:
            pass

        await interaction.client.db.execute(
            """
            DELETE FROM mod 
            WHERE guild_id = $1
            """, 
            interaction.guild.id
        )

        self.status = True

        return await interaction.approve("Disabled the jail system!")

    @discord.ui.button(emoji=config.EMOJIS.CONTEXT.DENY)
    async def no(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.warn("You are not the author of this embed")

        await interaction.response.edit_message(
            embed=Embed(description="Aborting action"), view=None
        )
        self.status = True

    async def on_timeout(self) -> None:
        if self.status == False:
            for item in self.children:
                item.disabled = True

            await self.message.edit(view=self)


class InviteButton(View):
    def __init__(self, url: str):
        super().__init__()
        self.add_item(Button(
            emoji=config.EMOJIS.SOCIAL.WEBSITE,
            url=url,
            style=ButtonStyle.link
        ))
