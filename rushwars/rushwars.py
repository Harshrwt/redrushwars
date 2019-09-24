# Standard Library
import csv
import json
import random
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
                "commanders": {},
            },
            "active": {
                "troops": {"Troopers": 2, "Pitcher": 2, "Shields": 1},
                "airdrops": {"Troopers": 1},
                "defenses": {"Troopers": 1, "Pitcher": 2, "Shields": 1},
                "commanders": {},
            },
            "stars": 0,
            "keys": 5,
            # "gold": 200,
            "gems": 150,
        }

default_defenses = [
    {"Troopers": 1, "Pitcher": 2, "Shields": 1},
    {"Troopers": 3, "Pitcher": 1, "Shields": 0},
    {"Troopers": 2, "Pitcher": 2, "Shields": 2}
]

max_card_level = 20

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
    async def rush(self, ctx, *, member:discord.Member=None):
        """Attack a base!"""

        try:
            # squad = await self.config.user(ctx.author).squad()
            async with self.config.user(ctx.author).active() as active:
                troops = active["troops"]
        except Exception as ex:
            return await ctx.send("Error with character sheet!")
            log.exception(f"Error with character sheet: {ex}!")

        hp = 0
        att = 0
        for troop in troops.keys():
            troop_stats = self.troop_search(troop)
            count = troops[troop]
            hp += int(troop_stats.Hp) * count
            att += int(troop_stats.Att) * count

        if member is not None:
            try:
                async with self.config.user(member).active() as active:
                    defenses = active["defenses"]
            except:
                await ctx.send("User has not set a defense!")
                return
        else:
            defenses = random.choice(default_defenses)

        def_hp = 0
        def_att = 0
        for defense in defenses.keys():
            defense_stats = self.troop_search(defense)
            count = defenses[defense]
            def_hp += int(defense_stats.Hp) * count
            def_att += int(defense_stats.Att) * count

        attack = [(troop, troops[troop]) for troop in troops.keys()]
        defense = [(defense, defenses[defense]) for defense in defenses.keys()]

        attack_str = ""
        defense_str = ""
        for item in attack:
            card_name = item[0]
            card_emote = self.card_emotes(card_name)
            count = item[1]
            if count <= 0:
                continue
            attack_str += f"**{card_name}** {card_emote} x{count}\n"
        for item in defense:
            card_name = item[0]
            card_emote = self.card_emotes(card_name)
            count = item[1]
            if count <= 0:
                continue
            defense_str += f"**{card_name}** {card_emote} x{count}\n"

        embed = discord.Embed(colour=0x999966, title="Battle Info", description="*Will you get mega rich after this battle?*")
        embed.add_field(name="**Attack** <:RW_Attck:625783202836905984>", value=attack_str)
        embed.add_field(name="**Defense** <:RW_Defense:625804692760559636>", value=defense_str)
        await ctx.send(embed=embed)

        if def_hp/att < hp/def_att:
            await ctx.send("You win!")
        else:
            await ctx.send("You lose!")

    @commands.command()
    async def troop(self, ctx, troop_name: str, level=1):
        """Search for an troop in the Rush Wars universe.
            Args:
                troop_name: variable length string
            Returns:
                Discord embed
            Raises:
                AttributeError: Troop not found
            Examples:
                troop shields
        """
        if level > max_card_level:
            return await ctx.send("Maximum possible level is 20!")

        troop = self.troop_search(troop_name.title())
        if troop is None:
            return await ctx.send("Troop with that name could not be found.")

        color = self.color_lookup(troop.Rarity)
        title_name = troop.Name.replace(" ", "_")
        thumb_name = troop.Name.replace(" ", "-")
        url = f"https://rushwars.fandom.com/wiki/{title_name}"
        thumbnail_url = f"https://www.rushstats.com/assets/troop/{thumb_name}.png"
        target = self.troop_targets(troop.Targets)
        description = f"**{troop.Description}**"

        if "â" in description:
            description = description.replace("â", "-")

        lvl_stats = [int(troop.Hp), int(troop.Att)]
        upd_stats = self.card_level(level, lvl_stats, troop.Rarity)
        
        if isinstance(upd_stats, int):
            await ctx.send((f"{troop.Rarity} starts at level {upd_stats}! Showing level {upd_stats} stats..."))
            level = upd_stats
            upd_stats = lvl_stats

        dps = int(upd_stats[1]/float(troop.AttSpeed))

        embed = discord.Embed(colour=color, title=troop.Name, description=description, url=url)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name="Level <:RW_Level:625788888480350216>", value=level)
        embed.add_field(name="Health <:RW_Health:625786278058917898>", value=upd_stats[0])
        embed.add_field(name="Damage <:RW_Damage:625786276938907659>", value=upd_stats[1])
        embed.add_field(name="Damage per second <:RW_DPS:625786277903466498>", value=dps)
        embed.add_field(name="Rarity <:RW_Rarity:625783200983154701>", value=troop.Rarity)
        embed.add_field(name="Squad Size <:RW_Count:625786275802382347>", value=troop.Count)
        embed.add_field(name="Space <:RW_Space:625783199670206486>", value=troop.Space)
        embed.add_field(name="Targets <:RW_Targets:625786278096535574>", value=target)
        embed.add_field(name="Attack Speed <:RW_AttSpeed:625787097709543427>", value=f"{troop.AttSpeed}s")
        embed.add_field(name="HQ Level <:RW_HQ:625787531664818224>", value=troop.UnlockLvl)
        await ctx.send(embed=embed)

    def troop_search(self, name):
        fp = self.path / 'troops.csv'
        try:
            with fp.open('rt', encoding='iso-8859-15') as f:
                reader = csv.DictReader(f, delimiter=',')
                for row in reader:
                    if row['Name'] == name:
                        Troop = namedtuple('Name', reader.fieldnames)
                        return Troop(**row)
        except FileNotFoundError:
            print("The csv file could not be found in Rush Wars data folder.")
            return None

    def troop_targets(self, targets):
        if targets == 0:
            return "Ground"
        elif targets == 1:
            return "Air"
        else:
            return "Air & Ground"

    def card_level(self, level, stats: list, rarity):
        """Get stats by selected level"""

        if rarity.lower().startswith('c'):
            start = 1
        elif rarity.lower().startswith('r'):
            start = 5
        elif rarity.lower().startswith('e'):
            start = 9
        elif rarity.lower().startswith('co'):
            start = 13

        if level < start:
            return start

        level -= start - 1

        new_stats = []

        for stat in stats:
            stat = int(stat) 
            upgrader = stat/10
            i = 1
            while i < level:
                stat += upgrader
                i += 1
            new_stats.append(int(stat))

        return new_stats

    @commands.group(name="squad", autohelp=False)
    async def _squad(self,ctx):
        """This shows your squad.

        Add: Add card to squad - `[p]squad add item_name [quantity]`
        Remove: Remove card from squad - `[p]squad remove item_name [quantity]`
        Save:  Save current squad - `[p]squad save (squad_name)`
        Reset: Remove all cards from squad - `[p]squad reset`
        """

        if not ctx.invoked_subcommand:
            try:
                async with self.config.user(ctx.author).active() as active:
                    att_data = [
                        active["troops"], 
                        active["airdrops"], 
                        active["commanders"]
                    ]
            except Exception as ex:
                return await ctx.send(f"Error with character sheet! {ex}")
                log.exception(f"Error with character sheet: {ex}!")

            embed = discord.Embed(colour=0x999966, title="Squad", description="*Is your squad strong enough to kick butt and get mega rich?*")
            i = 1
            for items in att_data:
                if i == 1:
                    kind = "Troops"
                elif i == 2:
                    kind = "Airdrops"
                elif i == 3:
                    kind = "Commanders"
                else:
                    break
                i += 1
                sqd_str = ""
                # card_info = [(item, items[item]) for item in items.keys()]
                for item in items.keys():
                    if len(item) > 0:
                        card_name = item
                        card_emote = self.card_emotes(card_name)
                        count = items[item]
                        if count <= 0:
                            continue
                        sqd_str = f"**{card_name}** {card_emote} x{count}\n"
                
                if sqd_str == "":
                    sqd_str = f"No {kind.lower()} in squad."
                type_emote = self.type_emotes(kind)
                embed.add_field(name=f"{kind} {type_emote}", value=sqd_str)  
    
            await ctx.send(embed=embed)
    
    @staticmethod
    def color_lookup(rarity):
        colors = {"Common": 0xAE8F6F, "Rare": 0x74BD9C, "Epic": 0xB77AE0, "Commander": 0xF7EE85}
        return colors[rarity]
        
    @staticmethod
    def card_emotes(card_name):
        emotes = {
            "Troopers": "<:Troopers:625807035362967605>",
            "Pitcher": "<:Pitcher:625807035954626590>",
            "Shields": "<:Shields:625807036663332865>"
        }
        return emotes[card_name]

    @staticmethod
    def type_emotes(card_type):
        emotes = {
            "Troops": "<:RW_Attck:625783202836905984>",
            "Airdrops": "<:RW_Airdrop:626000292810588164>",
            "Defenses": "<:RW_Defense:625804692760559636>",
            "Commanders": "<:RW_Commander:626000293519163422>"
        }
        return emotes[card_type]