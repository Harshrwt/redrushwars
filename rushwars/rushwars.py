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

base_card_levels = {
    "common": 1,
    "rare": 5,
    "epic": 9,
    "commander": 13
}

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
        pass
        # troops_fp = bundled_data_path(self) / "troops.json"
        # airdrops_fp = bundled_data_path(self) / "airdrops.json"
        # defenses_fp = bundled_data_path(self) / "defenses.json"
        # commanders_fp = bundled_data_path(self) / "commanders.json"
        # files = {
        #     "troops": troops_fp,
        #     "airdrops": airdrops_fp,
        #     "defenses": defenses_fp,
        #     "commanders": commanders_fp,
        # }

        # with files["troops"].open("r") as f:
        #     self.TROOPS = json.load(f)
        # with files["airdrops"].open("r") as f:
        #     self.AIRDROPS = json.load(f)
        # with files["defenses"].open("r") as f:
        #     self.DEFENSES = json.load(f)
        # with files["commanders"].open("r") as f:
        #     self.COMMANDERS = json.load(f)

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
            troop_stats = self.card_search(troop)[1]
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
            defense_stats = self.card_search(defense)[1]
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
            attack_str += f"{card_name} {card_emote} x{count}\n"
        for item in defense:
            card_name = item[0]
            card_emote = self.card_emotes(card_name)
            count = item[1]
            if count <= 0:
                continue
            defense_str += f"{card_name} {card_emote} x{count}\n"

        embed = discord.Embed(colour=0x999966, title="Battle Info", description="Will you get mega rich after this battle?")
        embed.add_field(name="Attack <:RW_Attck:625783202836905984>", value=attack_str)
        embed.add_field(name="Defense <:RW_Defense:625804692760559636>", value=defense_str)
        await ctx.send(embed=embed)

        if def_hp/att < hp/def_att:
            await ctx.send("You win!")
        else:
            await ctx.send("You lose!")

    @commands.command()
    async def card(self, ctx, card_name: str, level:int=None):
        """Search for a card in the Rush Wars universe.
            Examples:
                `[p]card shields`
                `[p]card "rocket truck"`
                `[p]card "sneaky ninja" 9`
        """
        if level is not None and level > max_card_level:
            return await ctx.send("Maximum possible level is 20!")

        data = self.card_search(card_name.title())
        if data is None:
            return await ctx.send("Card with that name could not be found.")
        
        card_type = data[0]
        card = data[1]

        color = self.color_lookup(card.Rarity)
        title_name = card.Name.replace(" ", "_")
        thumb_name = card.Name.replace(" ", "-")
        url = f"https://rushwars.fandom.com/wiki/{title_name}"
        thumbnail_url = f"https://www.rushstats.com/assets/{card_type}/{thumb_name}.png"
        description = f"{card.Description}"

        if "â" in description:
            description = description.replace("â", "-")

        if level is None:
            level = base_card_levels[(card.Rarity).lower()]

        embed = discord.Embed(colour=color, title=card.Name, description=description, url=url)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name="Level <:RW_Level:625788888480350216>", value=level)

        if card_type == 'troop':
            target = self.troop_targets(card.Targets)

            lvl_stats = [int(card.Hp), int(card.Att)]
            upd_stats = self.card_level(level, lvl_stats, card.Rarity, card_type)
        
            if isinstance(upd_stats, int):
                await ctx.send((f"{card.Rarity} starts at level {upd_stats}! Showing level {upd_stats} stats..."))
                level = upd_stats
                upd_stats = lvl_stats

            target = self.troop_targets(card.Targets)

            dps = int(upd_stats[1]/float(card.AttSpeed))

            embed.add_field(name="Health <:RW_Health:625786278058917898>", value=upd_stats[0])
            embed.add_field(name="Damage <:RW_Damage:625786276938907659>", value=upd_stats[1])
            embed.add_field(name="Damage per second <:RW_DPS:625786277903466498>", value=dps)
            embed.add_field(name="Squad Size <:RW_Count:625786275802382347>", value=card.Count)
            embed.add_field(name="Space <:RW_Space:625783199670206486>", value=card.Space)
            embed.add_field(name="Targets <:RW_Targets:625786278096535574>", value=target)
            embed.add_field(name="Attack Speed <:RW_AttSpeed:625787097709543427>", value=f"{card.AttSpeed}s")
        
        elif card_type == 'airdrop':
            lvl_stats = [int(card.Value), float(card.Duration)]
            upd_stats = self.card_level(level, lvl_stats, card.Rarity, card_type)

            if isinstance(upd_stats, int):
                await ctx.send((f"{card.Rarity} starts at level {upd_stats}! Showing level {upd_stats} stats..."))
                level = upd_stats
                upd_stats = lvl_stats

            value_emote = self.airdrop_value_emotes(card.Ability)

            embed.add_field(name=f"Value {value_emote}", value=upd_stats[0])
            embed.add_field(name="Duration <:Duration:626042235753857034>", value=upd_stats[1])
            embed.add_field(name="Space <:RW_Airdrop:626000292810588164>", value=card.Space)
            
        embed.add_field(name="Rarity <:RW_Rarity:625783200983154701>", value=card.Rarity)
        embed.add_field(name="HQ Level <:RW_HQ:625787531664818224>", value=card.UnlockLvl)
        await ctx.send(embed=embed)

    def card_search(self, name):
        files = ['troops.csv', 'airdrops.csv', 'defenses.csv', 'commanders.csv']
        for file in files: 
            fp = self.path / file
            try:
                with fp.open('rt', encoding='iso-8859-15') as f:
                    reader = csv.DictReader(f, delimiter=',')
                    for row in reader:
                        if row['Name'] == name:
                            Card = namedtuple('Name', reader.fieldnames)
                            card_type = file.split('.')[0]
                            # remove trailing "s"
                            card_type = card_type[:-1]
                            return (card_type, Card(**row))
                        else:
                            continue
            except FileNotFoundError:
                log.exception(f"{file} file could not be found in Rush Wars data folder.")
                continue

    def troop_targets(self, targets):
        if targets == 0:
            return "Ground"
        elif targets == 1:
            return "Air"
        else:
            return "Air & Ground"

    def card_level(self, level, stats: list, rarity, card_type):
        """Get stats by selected level"""

        start = base_card_levels[rarity.lower()]

        if level < start:
            return start

        level -= start - 1

        new_stats = []

        for stat in stats:
            if stat != 0:
                if isinstance(stat, int):
                    upgrader = stat/10
                elif isinstance(stat, float):
                    upgrader = 0.5
                i = 1
                new_stat = stat
                while i < level:
                    new_stat += upgrader
                    i += 1
                if isinstance(stat, int):
                    new_stats.append(int(new_stat))
                elif isinstance(stat, float):
                    new_stats.append(new_stat)
            else:
                new_stats.append(stat)
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

            embed = discord.Embed(colour=0x999966, title="Squad", description="Is your squad strong enough to kick butt and get mega rich?")
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
                    if item:
                        card_name = item
                        card_emote = self.card_emotes(card_name)
                        count = items[item]
                        if count <= 0:
                            continue
                        sqd_str += f"{card_name} {card_emote} x{count}\n"
                
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
            "Shields": "<:Shields:625807036663332865>",
            "Arcade": "<:Arcade:626008229763219477>",
            "Heal": "<:Heal:626008230233112576>",
            "Rage": "<:Boost:626008230186975233>",
            "Fridge": "<:Fridge:626008230279118848>",
            "Paratroopers": "<:Paratroopers:626008231478558732>",
            "Invisibility": "<:Invisibility:626008231713439794>",
            "Satellite": "<:Satellite:626010083406643200>"
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

    @staticmethod
    def airdrop_value_emotes(airdrop_ability):
        emotes = {
            "Boost": "<:BoostIcon:626042235812708362>",
            "Damage": "<:AreaDMG:626042235351334943>",
            "Heal": "<:HealIcon:626042237339303946>",
            "Invisibility": "<:AreaDMG:626042235351334943>",
            "Freeze": "<:Freeze:626042235661713408>"
        }
        return emotes[airdrop_ability]
