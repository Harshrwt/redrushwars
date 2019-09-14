import asyncio
import discord
import json
import random
import time
import logging
import os
from typing import Optional

from redbot.core import commands, bank, checks, Config
from redbot.core.commands.context import Context
from redbot.core.errors import BalanceTooHigh
from redbot.core.data_manager import bundled_data_path, cog_data_path
from redbot.core.utils.chat_formatting import box, pagify, bold, humanize_list, escape
from redbot.core.utils.common_filters import filter_various_mentions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, start_adding_reactions
from redbot.core.i18n import Translator, cog_i18n


BaseCog = getattr(commands, "Cog", object)

_ = Translator("RushWars", __file__)

log = logging.getLogger("red.rushwars")
listener = getattr(commands.Cog, "listener", None)

if listener is None:
    def listener(name=None):
        return lambda x:x

@cog_i18n(_)
class RushWars(BaseCog):
    """A simplified version of the game Rush Wars, developed by Supercell."""

    __version__ = "0.0.1"

    def init(self):
        # self.bot = bot
        self.path = bundled_data_path(self)

        self.locks = {}

        self.config = Config.get_conf(self, 1_070_701_001, force_registration=True)

        # (level, number of cards)
        default_card_stats = (1, 0)

        default_user = {
            "exp": 0,
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
                "troops": [],
                "airdrops": [],
                "commaders": [],
            },
            "stars": 0,
            # "gold": 200,
            "gems": 150,
        }

        self.TROOPS: dict = None
        self.AIRDROPS: dict = None
        self.DEFENSES: dict = None
        self.COMMANDERS: dict = None

        self.config.register_user(**default_user)
        self.cleanup_loop = self.bot.loop.create_task(self.cleanup_tasks())

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
        
    async def cleanup_tasks(self):
        await self.bot.wait_until_ready()
        while self is self.bot.get_cog("RushWars"):
            for task in self.tasks:
                if task.done():
                    self.tasks.remove(task)
            await asyncio.sleep(300)

    async def allow_in_dm(self, ctx):
        """Checks if the bank is global and allows the command in dm."""
        if ctx.guild is not None:
            return True
        if ctx.guild is None and await bank.is_global():
            return True
        else:
            return False

    def get_lock(self, member: discord.Member):
        if member.id not in self.locks:
            self.locks[member.id] = asyncio.Lock()
        return self.locks[member.id]

    @staticmethod
    def E(t: str) -> str:
        return escape(filter_various_mentions(t), mass_mentions=True, formatting=True)

    @commands.group(name="squad", autohelp=False)
    async def _squad(self, ctx: Context):
        """This shows your squad.
        
        Add: Add card to squad - `[p]squad add item_name [quantity]`
        Remove: Remove card from squad - `[p]squad remove item_name [quantity]`
        Save:  Save current squad - `[p]squad save (squad_name)`
        """
        if not await self.allow_in_dm(ctx):
            return await ctx.send(_("This command is not available in DM's on this bot."))
        if not ctx.invoked_subcommand:
            await ctx.send("hello, world!")

    @commands.command(name="attack", autohelp=False)
    async def _attack(self, ctx: Context):
        """Attack another base for stars, gold and glory!"""
        await ctx.send("hello, world!")
    
    # @commands.command(name="")


    def cog_unload(self):
        for task in self.tasks:
            log.debug(f"removing task {task}")
            task.cancel()

    __unload = cog_unload
