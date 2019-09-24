from .rushwars import RushWars


async def setup(bot):
    cog = RushWars()
    bot.add_cog(cog)
