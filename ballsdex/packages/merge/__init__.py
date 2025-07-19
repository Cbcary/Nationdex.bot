from typing import TYPE_CHECKING

from ballsdex.packages.merge.cog import Merge

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(Merge(bot))
