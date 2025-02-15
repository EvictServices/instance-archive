import discord

from discord import TextChannel, VoiceChannel
from discord.ext.commands import command, has_permissions, group

from typing import Union, Optional

from core.client.context import Context
from tools import CompositeMetaClass, MixinMeta

# Going to come back to this,
# we have better shit to worry about
# - sin


class ChannelEdit(MixinMeta, metaclass=CompositeMetaClass):
    """
    Edit various Discord objects.
    """

    @group(invoke_without_command=True, aliases=["cedit"])
    async def channeledit(self, ctx: Context):
        """
        Edit various channel related features.
        """
        
        await ctx.send_help(ctx.command)

    @has_permissions(manage_channels=True)
    @channeledit.command(name="name")
    async def channeledit_name(self, ctx: Context, channel: Optional[Union[TextChannel, VoiceChannel]] = None, *, name: str):
        """
        Rename a text or voice channel.
        """
        
        await channel.edit(name=name, reason=f"Renamed by {ctx.author}")
        await ctx.approve(f"Channel renamed to {name}")