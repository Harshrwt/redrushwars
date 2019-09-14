from .rushwars import RushWars


async def setup(bot):
    cog = RushWars()
    await cog.initialize()
    bot.add_cog(cog)
