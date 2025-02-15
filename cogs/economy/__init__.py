from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .economy import Economy

    await bot.add_cog(Economy(bot))
