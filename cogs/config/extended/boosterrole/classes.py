from discord.ui import button, View, Button
from discord import Interaction, ButtonStyle
from core.client.context import Context


class ConfirmView(View):
    def __init__(self, ctx: Context, member):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.member = member
        self.value = None

    @button(label="Approve", style=ButtonStyle.green)
    async def approve(self, interaction: Interaction, button: Button):
            
            if interaction.user != self.member:
                return await interaction.warn("You are **not** the author of this embed!")
            
            self.value = True
            self.stop()

    @button(label="Decline", style=ButtonStyle.red)
    async def decline(self, interaction: Interaction, button: Button):
            
            if interaction.user != self.member:
                return await interaction.warn("You are **not** the author of this embed!")
            
            self.value = False
            self.stop()