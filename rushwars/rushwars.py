# Standard Library
import csv
import json
import logging
from collections import namedtuple

# Discord
import discord

# Redbot
from redbot.core import commands, Config
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import box

# Third-Party Requirements
# from tabulate import tabulate


BaseCog = getattr(commands, "Cog", object)

log = logging.getLogger("red.rushwars")
listener = getattr(commands.Cog, "listener", None)

__version__ = "0.0.1"
__author__ = "Snowsee"

# (level, number of cards)
default_card_stats = (1, 0)

default_user = {
            "xp": 0,
            "lvl": 1,
            "hq": 1,
            "chopper": 1,
            "cards": {
                "troops": {
                    "Troopers": default_card_stats,
                    "Pitcher": default_card_stats,
                    "Shields": default_card_stats,
                },
                "airdrops": {
                    "Rage": default_card_stats,
                },
                "defenses": {
                    "Bomb": default_card_stats,
                    "Mines": default_card_stats,
                    "Cannon": default_card_stats,
                },
                "commanders": {}
            },
            "squad": {
                "troops": ["Troopers", "Pitcher", "Shields"],
                "airdrops": ["Rage"],
                "commaders": [],
            },
            "stars": 0,
            "keys": 5,
            # "gold": 200,
            "gems": 150,
        }

TROOPS: dict = None
AIRDROPS: dict = None
DEFENSES: dict = None
COMMANDERS: dict = None


class RushWars(BaseCog):
    """Simulate Rush Wars"""

    def __init__(self):
        self.path = bundled_data_path(self)

        self.config = Config.get_conf(
            self, 1_070_701_001, force_registration=True)

        self.config.register_user(**default_user)

    async def initialize(self):
        """This will load all the bundled data into respective variables"""
        troops_fp = bundled_data_path(self) / "troops.json"
        airdrops_fp = bundled_data_path(self) / "airdrops.json"
        defenses_fp = bundled_data_path(self) / "defenses.json"
        commanders_fp = bundled_data_path(self) / "commanders.json"
        files = {
            "troops": troops_fp,
            "airdrops": airdrops_fp,
            "defenses": defenses_fp,
            "commanders": commanders_fp,
        }

        with files["troops"].open("r") as f:
            self.TROOPS = json.load(f)
        with files["airdrops"].open("r") as f:
            self.AIRDROPS = json.load(f)
        with files["defenses"].open("r") as f:
            self.DEFENSES = json.load(f)
        with files["commanders"].open("r") as f:
            self.COMMANDERS = json.load(f)

    @commands.group(autohelp=True)
    async def rushwars(self, ctx):
        """This is the list of Rush Wars commands you can use."""
        pass

    @rushwars.command()
    async def version(self, ctx):
        """Display running version of Rush Wars cog
        
            Returns:
                Text output of your installed version of Rush Wars.
        """
        await ctx.send(f"You are running Rush Wars version {__version__}")

    @commands.command()
    async def rush(self, ctx):
        """Attack a base!"""

        try:
            squad = await self.config.user(ctx.author).squad()
            cards = await self.config.user(ctx.author).cards()
        except Exception:
            await ctx.send("Error!")
            return

        await ctx.send(f"{squad}")
        await ctx.send(f"{cards}")
