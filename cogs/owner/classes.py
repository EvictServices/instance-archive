from main import Evict

from discord import Member, Embed

import datetime


class OwnerLogs:

    async def blacklistguild(bot: Evict, guild: int, author: Member, information: str):

        channel = bot.get_channel(1268645258288435346)

        embed = Embed(timestamp=datetime.datetime.now())

        embed.set_author(
            name="Guild Blacklist", icon_url=author.display_avatar
        )  # type: ignore

        embed.add_field(name="Server ID", value=f"``{guild}``", inline=False)

        embed.add_field(name="Staff Mention", value=f"{author.mention}", inline=False)

        embed.add_field(name="Staff ID", value=f"``{author.id}``", inline=False)

        embed.add_field(name="Reason", value=f"{information}", inline=False)

        embed.set_thumbnail(url=author.display_avatar)  # type: ignore

        try:
            await channel.send(embed=embed, silent=True)

        except:
            pass

    async def unblacklistguild(
        bot: Evict, guild: int, author: Member, information: str
    ):

        channel = bot.get_channel(1268645258288435346)

        embed = Embed(timestamp=datetime.datetime.now())

        embed.set_author(
            name="Guild Unblacklist", icon_url=author.display_avatar
        )  # type: ignore

        embed.add_field(name="Server ID", value=f"``{guild}``", inline=False)

        embed.add_field(name="Staff Mention", value=f"{author.mention}", inline=False)

        embed.add_field(name="Staff ID", value=f"``{author.id}``", inline=False)

        embed.add_field(name="Reason", value=f"{information}", inline=False)

        embed.set_thumbnail(url=author.display_avatar)  # type: ignore

        try:
            await channel.send(embed=embed, silent=True)

        except:
            pass

    async def blacklistuser(bot: Evict, user: Member, author: Member, information: str):

        channel = bot.get_channel(1289496046715666432)

        embed = Embed(timestamp=datetime.datetime.now())

        embed.set_author(
            name="Blacklist", icon_url=author.display_avatar
        )  # type: ignore

        embed.add_field(name="User Mention", value=f"{user.mention}", inline=False)

        embed.add_field(name="User ID", value=f"``{user.id}``", inline=False)

        embed.add_field(name="Staff ID", value=f"``{author.id}``", inline=False)

        embed.add_field(name="Staff Mention", value=f"{author.mention}", inline=False)

        embed.add_field(name="Reason", value=f"{information}", inline=False)

        embed.set_thumbnail(url=author.display_avatar)  # type: ignore

        try:
            await channel.send(embed=embed, silent=True)

        except:
            pass

    async def unblacklistuser(
        bot: Evict, user: Member, author: Member, information: str
    ):

        channel = bot.get_channel(1289496046715666432)

        embed = Embed(timestamp=datetime.datetime.now())

        embed.set_author(
            name="Unblacklist", icon_url=author.display_avatar
        )  # type: ignore

        embed.add_field(name="User Mention", value=f"{user.mention}", inline=False)

        embed.add_field(name="User ID", value=f"``{user.id}``", inline=False)

        embed.add_field(name="Staff ID", value=f"``{author.id}``", inline=False)

        embed.add_field(name="Staff Mention", value=f"{author.mention}", inline=False)

        embed.add_field(name="Reason", value=f"{information}", inline=False)

        embed.set_thumbnail(url=author.display_avatar)  # type: ignore

        try:
            await channel.send(embed=embed, silent=True)

        except:
            pass
