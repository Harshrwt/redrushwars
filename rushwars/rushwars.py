# Standard Library
import csv
import json
import random
import logging
from collections import namedtuple
from typing import Optional
from math import ceil

from .boxes import Boxes

# Discord
import discord

# Redbot
from redbot.core import commands, Config
from redbot.core.config import Group
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.predicates import ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

# Third-Party Requirements
# from tabulate import tabulate


BaseCog = getattr(commands, "Cog", object)

log = logging.getLogger("red.rushwars")
listener = getattr(commands.Cog, "listener", None)

__version__ = "1.0.0"
__author__ = "Snowsee"

# [level, number of cards]
default_card_stats = [1, 1]

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
            "Arcade": default_card_stats,
        },
        "defenses": {},
        "commanders": {},
    },
    "active": {
        "troops": {},
        "airdrops": {},
        "defenses": {},
        "commanders": {},
    },
    "stars": {
        "attack": 0,
        "defense": 0
    },
    "keys": 5,
    "gold": 200,
    "gems": 150,
    "boxes": 0,
    "temp_stars": 0,
    "temp_def_stars": 0
}

default_defenses = [
    {"Troopers": 4},
    {"Pitcher": 4},
    {"Shields": 4},
    {"Troopers": 2, "Pitcher": 2},
    {"Troopers": 1, "Shields": 3},
    {"Pitcher": 3, "Shields": 1}
]

base_card_levels = {
    "common": 1,
    "rare": 5,
    "epic": 9,
    "commander": 13
}

max_card_level = 20

TOTAL_CARDS = 43

LEAGUE_ICONS_BASE_URL = "https://www.rushstats.com/assets/league/"
# (lower limit, upper limit, box multiplier)
LEAGUES = {
    "Rookie": (0, 200, 120),
    "Bronze": (200, 600, 140),
    "Silver": (600, 1200, 160),
    "Gold": (1200, 1800, 180),
    "Specialist": (1800, 2400, 200),
    "Ninja": (2400, 3000, 220),
    "Destroyer": (3000, 4000, 240),
    "Champion": (4000, 5200, 260),
    "Legend": (5200, 6500, 280),
    "Supreme": (6500, 8000, 300),
    "Superstar": (8000, 10000, 320),
    "Elite": (10000, 12000, 340)
}

STAT_EMOTES = {
    "Experience": "<:RW_XP:625783207518011412>",
    "Stars": "<:RW_Stars:626716336797777921>",
    "HQ": "<:RW_HQ:625787531664818224>",
    "Gold_Icon": "<:RW_Gold:625783196394717267>",
    "Gems": "<:RW_Gem:625783196558295065>",
    "Attack Stars": "<:RW_Attck:625783202836905984>",
    "Defense Stars": "<:RW_Defense:626338600467824660>",
    "Keys": "<:RW_Key:625783197963255838>",
    "Chopper": "<:RW_Chopper:626718677986967553>",
    "Rookie": "<:Rookie:626724912509485057>",
    "Bronze": "<:Bronze:626724908008734730>",
    "Silver": "<:Silver:626724911901310976>",
    "Gold": "<:Gold:626724912408821771>",
    "Specialist": "<:Specialist:626724911750053889>",
    "Ninja": "<:Ninja:626724910420721684>",
    "Destroyer": "<:Destroyer:626724909887914004>",
    "Champion": "<:Champion:626724909996834826>",
    "Legend": "<:Legend:626724911850848267>",
    "Supreme": "<:Supreme:626724913562255360>",
    "Superstar": "<:Superstar:626724912681451531>",
    "Elite": "<:Elite:626724913058807809>"
}

LEVEL_BASE_URL = "https://www.rushstats.com/assets/level/"

LowGoldError = "You do not have enough gold"


class RushWars(BaseCog):
    """Simulate Rush Wars"""

    def __init__(self):
        self.path = bundled_data_path(self)

        self.config = Config.get_conf(
            self, 1_070_701_001, force_registration=True)

        self.XP_LEVELS: dict = None
        self.HQ_LEVELS: dict = None
        self.CHOPPER_LEVELS: dict = None
        self.BOXES_INFO: dict = None
        self.RARITY_INFO: dict = None

        self.config.register_user(**default_user)

    async def initialize(self):
        """This will load all the bundled data into respective variables."""
        try:
            xp_levels_fp = bundled_data_path(self) / "xp_levels.json"
            hq_levels_fp = bundled_data_path(self) / "hq_levels.json"
            chopper_levels_fp = bundled_data_path(self) / "chopper_levels.json"
            boxes_fp = bundled_data_path(self) / "boxes.json"
            rarities_fp = bundled_data_path(self) / "rarities.json"
        except:
            log.exception("Error with file path.")

        with xp_levels_fp.open("r") as f:
            self.XP_LEVELS = json.load(f)
        with hq_levels_fp.open("r") as f:
            self.HQ_LEVELS = json.load(f)
        with chopper_levels_fp.open("r") as f:
            self.CHOPPER_LEVELS = json.load(f)
        with boxes_fp.open("r") as f:
            self.BOXES_INFO = json.load(f)
        with rarities_fp.open("r") as f:
            self.RARITY_INFO = json.load(f)

    @commands.command(name="rushversion", autohelp=True)
    @commands.cooldown(rate=5, per=120, type=commands.BucketType.guild)
    async def rushversion(self, ctx):
        """Display running version of Rush Wars cog

            Returns:
                Text output of your installed version of Rush Wars.
        """
        await ctx.send(f"You are running Rush Wars version {__version__}")

    @commands.command()
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    async def rush(self, ctx, *, member: discord.Member = None):
        """Attack a base!"""

        if member is not None:
            if member.id == ctx.author.id:
                return await ctx.send("You can't battle against yourself!")

        try:
            async with self.config.user(ctx.author).active() as active:
                troops = active["troops"]
                airdrops = active["airdrops"]
                commanders = active["commanders"]
                player = ctx.author.name
        except Exception as ex:
            return await ctx.send(f"Error with character sheet!")
            log.exception(f"Error with character sheet: {ex}!")

        try:
            async with self.config.user(ctx.author).stars() as tot_stars:
                att_stars = tot_stars["attack"]
                def_stars = tot_stars["defense"]
        except:
            log.exception("Error with character sheet.")
            return

        total_stars = att_stars + def_stars

        if member:
            try:
                async with self.config.user(member).active() as active:
                    defenses = active["defenses"]
                    opponent = member.name
            except:
                log.exception("Error with character sheet.")
                return
            if not defenses:
                return await ctx.send("User has not set up a defense.")

            opponent_stars = await self.get_stars(member)
            if total_stars - opponent_stars >= 100:
                return await ctx.send(f"Can't attack {opponent} because of large difference in stars.")

            if total_stars < 10:
                await ctx.send("First 4 battles must be against computer. Changing to computer...")
                defenses = random.choice(default_defenses)
                opponent = "Computer"
        else:
            defenses = random.choice(default_defenses)
            opponent = "Computer"
            if total_stars > 10:
                member = await self.matchmaking(ctx)
                if member:
                    try:
                        async with self.config.user(member).active() as active:
                            defenses = active["defenses"]
                            opponent = member.name
                    except:
                        log.exception("Error with character sheet.")
                        return

        hp = 0
        attps = 0
        def_hp = 0
        def_attps = 0
        user_avg_levels = [0, 0]  # [iterations, value]

        sel_trp = sum(troops.values())
        sel_ardp = sum(airdrops.values())

        if sel_trp == 0 or sel_trp == 0:
            return await ctx.send("Please add items to squad! Help: `[p]help squad`")

        foo = await self.cost_gold(ctx)
        if not foo:
            return await ctx.send("You do not have enough gold to cover attack costs.")

        for troop in troops.keys():
            stats = self.card_search(troop)[1]
            level = await self.rush_card_level(ctx, troop.title(), "troops")
            lvl_stats = [int(stats.Hp), int(stats.Att)]
            upd_stats = self.card_level(
                level, lvl_stats, stats.Rarity, "troops")

            count = troops[troop]

            hp += upd_stats[0] * count
            # return await ctx.send(hp)
            att = upd_stats[1] * count
            attps += (att/float(stats.AttSpeed))

            user_avg_levels[0] += 1
            user_avg_levels[1] += level

        for airdrop in airdrops.keys():
            stats = self.card_search(airdrop)[1]
            level = await self.rush_card_level(ctx, airdrop.title(), "airdrops")

            lvl_stats = [int(stats.Duration)]
            upd_stats = self.card_level(
                level, lvl_stats, stats.Rarity, "airdrops")

            count = airdrops[airdrop]

            duration = upd_stats[0] * count

            ability = stats.Ability
            if ability == "Damage":
                attps += int(stats.Value) * duration
            elif ability == "Boost":
                attps += int(stats.Value) * duration
                hp += int(stats.Value) * duration
            elif ability == "Heal":
                hp += int(stats.Value) * duration
            elif ability in ["Invisibility", "Freeze"]:
                def_attps -= int(stats.Value) * duration

            user_avg_levels[0] += 1
            user_avg_levels[1] += level

        for commander in commanders.keys():
            stats = self.card_search(commander)[1]
            level = await self.rush_card_level(ctx, commander.title(), "commanders")
            lvl_stats = [int(stats.Hp), int(stats.Att)]
            upd_stats = self.card_level(
                level, lvl_stats, stats.Rarity, "commanders")

            count = commanders[commander]

            hp += upd_stats[0] * count
            # return await ctx.send(hp)
            att = upd_stats[1] * count
            attps += (att/float(stats.AttSpeed))

            user_avg_levels[0] += 1
            user_avg_levels[1] += level

        user_avg_level = round(user_avg_levels[1]/user_avg_levels[0])

        for defense in defenses.keys():
            stats = self.card_search(defense)[1]
            if member:
                level = await self.rush_card_level(ctx, defense.title(), "defenses")
            else:
                level = random.choice(
                    range(user_avg_level-1, user_avg_level+2))
                if level < 1:
                    level = 1

            lvl_stats = [int(stats.Hp), int(stats.Att)]
            upd_stats = self.card_level(
                level, lvl_stats, stats.Rarity, "defenses")

            count = defenses[defense]

            def_hp += upd_stats[0] * count
            def_att = upd_stats[1] * count
            def_attps += (def_att/float(stats.AttSpeed))

        troop = [(troop, troops[troop]) for troop in troops.keys()]
        airdrop = [(airdrop, airdrops[airdrop]) for airdrop in airdrops.keys()]
        defense = [(defense, defenses[defense]) for defense in defenses.keys()]
        commander = [(commander, commanders[commander])
                     for commander in commanders.keys()]

        attack_str = "`TROOPS`\n"
        attack_str += self.rush_strings(troop)
        if self.rush_strings(airdrop) != "":
            attack_str += "`AIRDROPS`\n"
            attack_str += self.rush_strings(airdrop)
        if self.rush_strings(commander) != "":
            attack_str += "`COMMANDERS`\n"
            attack_str += self.rush_strings(commander)
        defense_str = self.rush_strings(defense)

        embed = discord.Embed(colour=0x98D9EB, title="Battle Info",
                              description="Will you get mega rich after this battle?")
        embed.set_author(name=f"{player} vs {opponent}",
                         icon_url="https://cdn.discordapp.com/attachments/622323508755693581/626058519929684027/Leaderboard.png")
        embed.add_field(
            name="Attack <:RW_Attck:625783202836905984>", value=attack_str)
        embed.add_field(
            name="Defense <:RW_Defenses:626339085501333504>", value=defense_str)
        await ctx.send(embed=embed)

        # battle logic
        res = hp/def_attps - def_hp/attps
        if res > 8:
            stars = 3
        elif res > 4:
            stars = 2
        elif res > 0:
            stars = 1
        else:
            stars = 0

        if total_stars < 9:
            stars = 3
        elif total_stars < 10:
            stars = 1

        if stars > 0:
            victory = True
            await ctx.send(f"You win!")
        else:
            victory = False
            await ctx.send("You lose!")

        rewards = await self.get_rewards(ctx, stars)
        await ctx.send(embed=rewards)

        open_box = await self.handle_keys(ctx, stars)
        if open_box:
            box = await self._box(ctx)
            await ctx.send(embed=box)

        # update defense stars of opponent
        if stars != 3:
            if member:
                async with self.config.user(member).stars() as member_stars:
                    def_stars = member_stars["defense"] + (3 - stars)
                await self.config.user(member).set_raw("stars", "defense", value=def_stars)

        level_up = True
        while level_up:
            level_up = await self.xp_level_handler(ctx)
            if level_up:
                await ctx.send(level_up[0])
                await ctx.send(level_up[1])

    @commands.command(name="rushinfo")
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.user)
    async def rush_info(self, ctx):
        """Get information related to rush (battle)."""
        hq = await self.config.user(ctx.author).hq()

        attack_cost = self.HQ_LEVELS[str(hq)]["AttackCost"]
        temp_stars = await self.config.user(ctx.author).temp_stars()
        temp_def_stars = await self.config.user(ctx.author).temp_def_stars()
        keys = await self.config.user(ctx.author).keys()

        embed = discord.Embed(colour=0x98D9EB, title="Rush Info")
        embed.add_field(name="Attack Cost",
                        value=f"{STAT_EMOTES['Gold_Icon']} {attack_cost}")
        embed.add_field(name="Stars Till Next Box",
                        value=f"{STAT_EMOTES['Stars']} {5 - temp_stars}")
        embed.add_field(name="Defense Box",
                        value=f"{STAT_EMOTES['Stars']} {temp_def_stars}/100")
        embed.add_field(name="Keys", value=f"{STAT_EMOTES['Keys']} {keys}")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def card(self, ctx, card_name: str, level: int = None):
        """Search for a card in the Rush Wars universe.
            Examples:
                `[p]card shields`
                `[p]card "rocket truck"`
                `[p]card "b.i.g." 13`
        """
        if level is not None and level > max_card_level:
            return await ctx.send("Maximum possible level is 20!")

        data = self.card_search(card_name.title())
        if data is None:
            return await ctx.send("Card with that name could not be found.")

        card_type = data[0]
        card = data[1]

        color = self.color_lookup(card.Rarity)
        url_name = card.Name.replace(" ", "-")
        url = f"https://www.rushstats.com/cards/{card_type}/{url_name}"
        thumbnail_url = f"https://www.rushstats.com/assets/{card_type}/{url_name}.png"
        description = f"{card.Description}"

        if "â" in description:
            description = description.replace("â", "-")

        description = description.replace("\\n\\n", '\n\n')

        if level is None:
            level = base_card_levels[(card.Rarity).lower()]

        embed = discord.Embed(colour=color, description=description)
        embed.set_author(name=card.Name, url=url)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(
            name="Level", value=f"<:RW_Level:625788888480350216> {level}")

        if card_type == 'troop' or card_type == 'defense' or card_type == 'commander':
            lvl_stats = [int(card.Hp), int(card.Att)]
            upd_stats = self.card_level(
                level, lvl_stats, card.Rarity, card_type+"s")

            if isinstance(upd_stats, int):
                await ctx.send((f"{card.Rarity} starts at level {upd_stats}! Showing level {upd_stats} stats..."))
                level = upd_stats
                upd_stats = lvl_stats

            target = self.card_targets(int(card.Targets))

            dps = int(upd_stats[1]/float(card.AttSpeed))

            embed.add_field(
                name="Health", value=f"<:RW_Health:625786278058917898> {upd_stats[0]}")
            embed.add_field(
                name="Damage", value=f"<:RW_Damage:625786276938907659> {upd_stats[1]}")
            embed.add_field(
                name="Damage per second", value=f"<:RW_DPS:625786277903466498> {dps}")
            if card_type == 'troop':
                embed.add_field(
                    name="Squad Size", value=f"<:RW_Count:625786275802382347> {card.Count}")
                embed.add_field(
                    name="Space", value=f"<:RW_Space:625783199670206486> {card.Space}")
            elif card_type == 'defense':
                embed.add_field(
                    name="Space", value=f"<:RW_Defense:626338600467824660> {card.Space}")
            embed.add_field(
                name="Targets", value=f"<:RW_Targets:625786278096535574> {target}")
            embed.add_field(
                name="Attack Speed", value=f"<:RW_AttSpeed:625787097709543427> {card.AttSpeed}s")

        elif card_type == 'airdrop':
            lvl_stats = [float(card.Duration)]
            upd_stats = self.card_level(
                level, lvl_stats, card.Rarity, card_type+"s")

            if isinstance(upd_stats, int):
                await ctx.send((f"{card.Rarity} starts at level {upd_stats}! Showing level {upd_stats} stats..."))
                level = upd_stats
                upd_stats = lvl_stats

            value_emote = self.airdrop_value_emotes(card.Ability)

            embed.add_field(
                name=f"{card.Ability} {value_emote}", value=card.Value)
            embed.add_field(
                name="Duration", value=f"<:Duration:626042235753857034> {str(upd_stats[0])+'s'}")
            embed.add_field(
                name="Space", value=f"<:RW_Airdrop:626000292810588164> {card.Space}")

        embed.add_field(
            name="Rarity", value=f"<:RW_Rarity:625783200983154701> {card.Rarity}")
        embed.add_field(
            name="Required HQ Level", value=f"<:RW_HQ:625787531664818224> {card.UnlockLvl}")
        await ctx.send(embed=embed)

    @commands.group(name="squad", autohelp=False)
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def _squad(self, ctx, member: Optional[discord.Member] = None):
        """Lookup your or any other server member's squad. Subcommands give more squad functions.

        save:  Save current squad - `[p]squad save (squad_name)`
        """
        if not ctx.invoked_subcommand:
            if member is None:
                user = ctx.author
            else:
                user = member
            try:
                async with self.config.user(user).active() as active:
                    att_data = [
                        active["troops"],
                        active["airdrops"],
                        active["commanders"]
                    ]
                chopperLvl = await self.config.user(ctx.author).chopper()
            except Exception as ex:
                return await ctx.send(f"Error with character sheet!")
                log.exception(f"Error with character sheet: {ex}!")

            embed = discord.Embed(colour=0x98D9EB,
                                  description="Is your squad strong enough to kick butt and get mega rich?")
            embed.set_author(
                name=f"{ctx.author.name}'s Squad", icon_url="https://cdn.discordapp.com/attachments/626063027543736320/626719420219392010/SilverStar.png")
            i = 1
            for items in att_data:
                if i == 1:
                    kind = "Troops"
                    capacity = self.CHOPPER_LEVELS[str(
                        chopperLvl)]["TroopHousing"]
                elif i == 2:
                    kind = "Airdrops"
                    capacity = self.CHOPPER_LEVELS[str(
                        chopperLvl)]["AirdropHousing"]
                elif i == 3:
                    kind = "Commanders"
                    capacity = 1
                else:
                    break
                i += 1
                sqd_str = ""
                total_type = 0
                # card_info = [(item, items[item]) for item in items.keys()]
                for item in items.keys():
                    if item:
                        card_name = item
                        card_emote = self.card_emotes(card_name)
                        count = items[item]
                        if count <= 0:
                            continue
                        sqd_str += f"{card_emote} `{card_name}` x{count}\n"

                        card_space = int(
                            (self.card_search(card_name)[1]).Space)
                        total_type += count * card_space

                if sqd_str == "":
                    sqd_str = f"No {kind.lower()} in squad."
                type_emote = self.type_emotes(kind)

                embed.add_field(
                    name=f"{kind} ({total_type}/{capacity}) {type_emote}", value=sqd_str)

            await ctx.send(embed=embed)

    @_squad.command(name="add")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def squad_add(self, ctx, card, number=1):
        """Add cards to your squad: `[p]squad add card [number]`
            Examples:
                `[p]squad add troopers`
                `[p]squad add pitcher 5`
                `[p]squad add "sneaky ninja"`
                `[p]squad add "rocket trucks" 2`
        """
        card = card.title()

        card_info = self.card_search(card)

        if not card_info:
            return await ctx.send(f"{card.title()} does not exist.")

        card_type = str(card_info[0]) + "s"
        if card_type == "commanders":
            card_space = 1
        else:
            card_space = int(card_info[1].Space)

        chopperLvl = await self.config.user(ctx.author).chopper()

        if card_type == "troops":
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active[card_type]
            except:
                log.exception("Error with character sheet.")
                return
            capacity = self.CHOPPER_LEVELS[str(chopperLvl)]["TroopHousing"]

        elif card_type == "airdrops":
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active[card_type]
            except:
                log.exception("Error with character sheet.")
                return
            capacity = self.CHOPPER_LEVELS[str(chopperLvl)]["AirdropHousing"]

        elif card_type == "commanders":
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active[card_type]
            except:
                log.exception("Error with character sheet.")
                return
            capacity = 1

        else:
            return await ctx.send(f"{card.title()} is not a valid attack card.")

        total_selected = self.total_selected(card, data)
        if total_selected >= capacity:
            return await ctx.send("Chopper is already full. Remove some cards first.")

        # check if user owns the card
        try:
            async with self.config.user(ctx.author).cards() as cards:
                owned = cards[card_type]
        except:
            log.exception("Error with character sheet.")
            return

        owns = False
        for item in owned.keys():
            if card == item:
                if owned[item][1] >= 1:
                    owns = True
                    break

        if owns:
            if total_selected + (number * card_space) > capacity:
                return await ctx.send("Adding the card(s) will exceed chopper capacity.")
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active[card_type]
                    for sqd_card in data.keys():
                        if card == sqd_card:
                            data[sqd_card] += number
                            break
                    else:
                        data[card] = number
            except:
                log.exception("Error with character sheet.")
                return
        else:
            return await ctx.send("You have not unlocked the card.")

        await ctx.send(f"{number} {card.title()} card(s) added to squad.")

    @_squad.command(name="remove")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def squad_remove(self, ctx, card, number=1):
        """Remove cards from squad: `[p]squad remove card [number]`
        Examples:
                `[p]squad remove troopers`
                `[p]squad remove pitcher 5`
                `[p]squad remove "sneaky ninja"`
                `[p]squad remove "rocket trucks" 2`
        """
        if number < 1:
            return await ctx.send("Must remove at least one card.")

        try:
            async with self.config.user(ctx.author).active() as active:
                cards_selected = [active["troops"],
                                  active["airdrops"], active["commanders"]]
        except:
            log.exception("Error with character sheet.")
            return

        card = card.title()

        selected = False
        i = 0
        for items in cards_selected:
            i += 1
            for item in items.keys():
                if item == card:
                    selected = True
                    if i == 1:
                        card_type = "troops"
                    elif i == 2:
                        card_type = "airdrops"
                    elif i == 3:
                        card_type = "commanders"
                    break

        if selected:
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active[card_type]
                    for sqd_card in data.keys():
                        if card == sqd_card:
                            if data[sqd_card] >= number:
                                data[sqd_card] -= number
                                if data[sqd_card] == 0:
                                    del data[sqd_card]
                                break
                            else:
                                return await ctx.send(f"Number of {card.title()} cards in squad are less than {number}.")
            except:
                log.exception("Error with character sheet.")
                return
        else:
            return await ctx.send(f"{card.title()} is not in squad.")

        await ctx.send(f"{number} {card.title()} card(s) removed from squad.")

    @_squad.command(name="reset")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def squad_reset(self, ctx, card_type=None):
        """Remove all cards of the optionally specified type. If no type is specified, all cards will be removed.
        Examples:
                `[p]squad reset`
                `[p]squad reset airdrops`
        """
        if card_type is None:
            categories = ["troops", "airdrops", "commanders"]
            msg = await ctx.send(f"Are you sure you want to reset the whole squad?")
            start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

            pred = ReactionPredicate.yes_or_no(msg, ctx.author)
            await ctx.bot.wait_for("reaction_add", check=pred)
            if pred.result is True:
                for category in categories:
                    try:
                        async with self.config.user(ctx.author).active() as active:
                            active[category] = {}
                    except:
                        log.exception("Error with character sheet.")
                        return
                await ctx.send("Squad reset.")
            else:
                return await ctx.send("Reset cancelled by the user.")
        else:
            card_type = card_type.lower()
            if card_type not in ["troops", "airdrops", "commanders"]:
                return await ctx.send("Entered card type is not valid.")
            else:
                msg = await ctx.send(f"Are you sure you want to reset {card_type} squad?")
                start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

                pred = ReactionPredicate.yes_or_no(msg, ctx.author)
                await ctx.bot.wait_for("reaction_add", check=pred)
                if pred.result is True:
                    try:
                        async with self.config.user(ctx.author).active() as active:
                            active[card_type].clear()
                            await ctx.send(f"{card_type.title()} squad reset.")
                    except:
                        log.exception("Error with character sheet.")
                        return
                else:
                    return await ctx.send("Reset cancelled by the user.")

    @commands.group(name="defense", autohelp=False)
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.user)
    async def _defense(self, ctx):
        """Lookup your defense. Subcommands give more defense functions."""

        if not ctx.invoked_subcommand:
            try:
                async with self.config.user(ctx.author).active() as active:
                    defense = active["defenses"]
                chopperLvl = await self.config.user(ctx.author).chopper()
            except Exception as ex:
                return await ctx.send(f"Error with character sheet!")
                log.exception(f"Error with character sheet: {ex}!")

            embed = discord.Embed(colour=0x98D9EB,
                                  description="Is your defense strong enough to protect your treasures?")
            embed.set_author(
                name=f"{ctx.author.name}'s Defense", icon_url="https://cdn.discordapp.com/attachments/626063027543736320/626338507958386697/Defense.png")

            capacity = self.CHOPPER_LEVELS[str(chopperLvl)]["DefenceHousing"]
            def_str = ""
            total_defense = 0
            # card_info = [(item, items[item]) for item in items.keys()]
            for item in defense.keys():
                if item:
                    card_name = item
                    card_emote = self.card_emotes(card_name)
                    count = defense[item]
                    if count <= 0:
                        continue

                    def_str += f"{card_emote} `{card_name}` x{count}\n"
                    card_space = int((self.card_search(card_name)[1]).Space)
                    total_defense += count * card_space

            if def_str == "":
                def_str = "No defenses in squad."

            emote = self.type_emotes("Defenses")
            embed.add_field(
                name=f"Defenses ({total_defense}/{capacity}) {emote}", value=def_str)

            await ctx.send(embed=embed)

    @_defense.command(name="add")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def defense_add(self, ctx, card, number=1):
        """Add cards to your defense: `[p]defense add card [number]`
            Examples:
                `[p]defense add troopers`
                `[p]defense add mortar 2`
                `[p]defense add "rocket trap"`
                `[p]defense add "cluster cake" 2`
        """
        card = card.title()

        card_info = self.card_search(card)

        if not card_info:
            return await ctx.send(f"{card.title()} does not exist.")

        card_type = str(card_info[0]) + "s"
        if card_type not in ["troops", "defenses"]:
            return await ctx.send(f"{card.title()} is not a valid defense card.")

        card_space = int(card_info[1].Space)
        chopperLvl = await self.config.user(ctx.author).chopper()

        try:
            async with self.config.user(ctx.author).active() as active:
                data = active["defenses"]
        except:
            log.exception("Error with character sheet.")
            return
        capacity = self.CHOPPER_LEVELS[str(chopperLvl)]["DefenceHousing"]

        total_selected = self.total_selected(card, data)
        if total_selected >= capacity:
            return await ctx.send(f"Defense is already full. Remove some cards first.")

        # check if user owns the card
        try:
            async with self.config.user(ctx.author).cards() as cards:
                owned = cards[card_type]
        except:
            log.exception("Error with character sheet.")
            return

        owns = False
        for item in owned.keys():
            if card == item:
                if owned[item][1] >= 1:
                    owns = True
                    break

        if owns:
            if total_selected + (number * card_space) > capacity:
                return await ctx.send("Adding the card(s) will exceed defense capacity.")
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active["defenses"]
                    for def_card in data.keys():
                        if card == def_card:
                            data[def_card] += number
                            break
                    else:
                        data[card] = number
            except:
                log.exception("Error with character sheet.")
                return
        else:
            return await ctx.send("You have not unlocked the card.")

        await ctx.send(f"{number} {card.title()} card(s) added to defense.")

    @_defense.command(name="remove")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def defense_remove(self, ctx, card, number=1):
        """Remove cards from defense: `[p]defense remove card [number]`
        Examples:
                `[p]defense remove troopers`
                `[p]defense remove pitcher 5`
                `[p]defense remove "sneaky ninja"`
                `[p]defense remove "rocket trucks" 2`
        """
        if number < 1:
            return await ctx.send("Must remove at least one card.")

        try:
            async with self.config.user(ctx.author).active() as active:
                data = active["defenses"]
        except:
            log.exception("Error with character sheet.")
            return

        card = card.title()

        selected = False
        for item in data.keys():
            if item == card:
                selected = True

        if selected:
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active["defenses"]
                    for def_card in data.keys():
                        if card == def_card:
                            if data[def_card] >= number:
                                data[def_card] -= number
                                break
                            else:
                                return await ctx.send(f"Number of {card.title()} cards in defense are less than {number}.")
            except:
                log.exception("Error with character sheet.")
                return
        else:
            return await ctx.send(f"{card.title()} is not in defense.")

        await ctx.send(f"{number} {card.title()} card(s) removed from defense.")

    @_defense.command(name="reset")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def defense_reset(self, ctx):
        """Remove all cards from defense: `[p]defense reset`"""
        msg = await ctx.send(f"Are you sure you want to reset your defense?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            try:
                async with self.config.user(ctx.author).active() as active:
                    active["defenses"].clear()
                    await ctx.send(f"Defense reset.")
            except:
                log.exception("Error with character sheet.")
                return
        else:
            return await ctx.send("Reset cancelled by the user.")

    # @commands.command(name="sethq")
    # async def set_hq(self, ctx, lvl: int = None):
    #     await self.new_hq_cards(ctx, lvl)
    #     await self.config.user(ctx.author).hq.set(lvl)
    #     await ctx.send("Done")

    @commands.command(name="cards")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def cards(self, ctx):
        """Shows all the cards you can find in boxes."""
        embed = discord.Embed(colour=0x98D9EB, title="Cards")
        try:
            async with self.config.user(ctx.author).cards() as cards:
                embeds = []
                for card_type in ['troops', 'airdrops', 'defenses', 'commanders']:
                    data = cards[card_type]

                    type_emote = self.type_emotes(card_type.title())
                    embed = discord.Embed(
                        color=0x98D9EB, title=f"{card_type.title()}")

                    for item in data.keys():
                        emote = self.card_emotes(item)
                        level = data[item][0]
                        found = data[item][1]
                        # if found < 1:
                        #     found = "Not Found"
                        # else:
                        #     found = str(found) + " Cards"
                        try:
                            val_str = f"<:RW_Levels:626490780386721792>`{level}\u28FFLevel`" \
                                f" | <:RW_Cards:626422103092232192>`{found}\u28FFCards`\n"
                            embed.add_field(
                                name=f"{item.upper()} {emote}", value=val_str)
                        except:
                            embed.add_field(name="No cards!",
                                            value=f"No {card_type} unlocked.")
                    embeds.append(embed)
                await menu(ctx, embeds, DEFAULT_CONTROLS)
        except Exception as ex:
            log.exception(ex)
            return

    @commands.command(name="profile", aliases=["stats"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def profile(self, ctx, member: discord.Member = None):
        """Lookup your or another member's profile stats."""
        if member:
            user = member
        else:
            user = ctx.author

        try:
            hq = await self.config.user(user).hq()
            chopper = await self.config.user(user).chopper()
            keys = await self.config.user(user).keys()
            gold = await self.config.user(user).gold()
            gems = await self.config.user(user).gems()
            lvl = await self.config.user(user).lvl()
            xp = await self.config.user(user).xp()
        except:
            log.exception("Error with character sheet.")
            return

        try:
            async with self.config.user(user).stars() as stars:
                att_stars = stars["attack"]
                def_stars = stars["defense"]
        except:
            log.exception("Error with character sheet.")
            return

        total_stars = att_stars + def_stars
        # return await ctx.send(total_stars)
        # get user league
        for item in LEAGUES.keys():
            low, high = LEAGUES[item][0], LEAGUES[item][1]
            if total_stars in range(low, high):
                league = item
        league_url = f"{LEAGUE_ICONS_BASE_URL}{league}.png"

        # xp required for next level
        next_xp = self.XP_LEVELS[str(lvl)]["ExpToNextLevel"]

        embed = discord.Embed(colour=0x98D9EB)
        # embed.set_thumbnail(url=league_url)
        embed.set_author(name=f"{user.name}'s Profile",
                         icon_url=f"{LEVEL_BASE_URL}{lvl}.png")
        embed.add_field(name="HQ Level", value=f"{STAT_EMOTES['HQ']} {hq}")
        embed.add_field(name="Chopper Level",
                        value=f"{STAT_EMOTES['Chopper']} {chopper}")
        embed.add_field(name="Keys", value=f"{STAT_EMOTES['Keys']} {keys}/5")
        embed.add_field(
            name="Stars", value=f"{STAT_EMOTES[league]} {total_stars}")
        embed.add_field(name="Attack Stars",
                        value=f"{STAT_EMOTES['Attack Stars']} {att_stars}")
        embed.add_field(name="Defense Stars",
                        value=f"{STAT_EMOTES['Defense Stars']} {def_stars}")
        embed.add_field(
            name="Gold", value=f"{STAT_EMOTES['Gold_Icon']} {gold}")
        embed.add_field(name="Gems", value=f"{STAT_EMOTES['Gems']} {gems}")
        embed.add_field(name="Experience",
                        value=f"{STAT_EMOTES['Experience']} {xp}/{next_xp}")

        await ctx.send(embed=embed)

    @commands.group(name="upgrade", autohelp=False)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def _upgrade(self, ctx):
        """Upgrade HQ, chopper or a card."""
        if not ctx.invoked_subcommand:
            return await ctx.send("Please specify one of the following to upgrade: hq, chopper or a card.")

    @_upgrade.command(name="hq")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def upgrade_hq(self, ctx):
        """Upgrade HQ level: `[p]upgrade hq`"""
        # get new hq level
        hq = await self.config.user(ctx.author).hq() + 1

        # check if HQ level up is possible with user's xp level
        lvl = await self.config.user(ctx.author).lvl()
        highest_possible_hq = self.XP_LEVELS[str(lvl)]["MaxHQLevel"]
        if hq > highest_possible_hq:
            return await ctx.send("You need more experience to upgrade HQ!")

        upgrade_cost = self.HQ_LEVELS[str(hq-1)]["UpgradeGold"]

        msg = await ctx.send(f"Upgrading HQ will cost {upgrade_cost} {STAT_EMOTES['Gold_Icon']}. Continue?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            try:
                gold = await self.config.user(ctx.author).gold()
                if gold >= upgrade_cost:
                    await self.config.user(ctx.author).hq.set(hq)
                    await self.new_hq_cards(ctx, hq)

                    upd_gold = gold - upgrade_cost
                    await self.config.user(ctx.author).gold.set(upd_gold)
                    return await ctx.send(f"HQ upgraded to level {hq}.")
                else:
                    return await ctx.send("You do not have enough gold to upgrade.")
            except:
                log.exception("Error with updating character sheet.")
                return
        else:
            return await ctx.send("Upgrade cancelled by the user.")

    @_upgrade.command(name="chopper")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def upgrade_chopper(self, ctx):
        """Upgrade chopper level: `[p]upgrade chopper`"""
        # get new chopper level
        chopper = await self.config.user(ctx.author).chopper() + 1

        # check if chopper level up is possible
        hq = await self.config.user(ctx.author).hq()
        if chopper > hq:
            return await ctx.send("You need to upgrade HQ first!")

        upgrade_cost = self.CHOPPER_LEVELS[str(chopper-1)]["UpgradeGold"]

        msg = await ctx.send(f"Upgrading Chopper will cost {upgrade_cost} {STAT_EMOTES['Gold_Icon']}. Continue?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            try:
                gold = await self.config.user(ctx.author).gold()
                if gold >= upgrade_cost:
                    await self.config.user(ctx.author).chopper.set(chopper)

                    upd_gold = gold - upgrade_cost
                    await self.config.user(ctx.author).gold.set(upd_gold)
                    return await ctx.send(f"Chopper upgraded to level {chopper}.")
                else:
                    return await ctx.send("You do not have enough gold to upgrade.")
            except:
                log.exception("Error with updating character sheet.")
                return
        else:
            return await ctx.send("Upgrade cancelled by the user.")

    @_upgrade.command(name="card")
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def upgrade_card(self, ctx, card_name):
        """Upgrade a card: `[p]upgrade card [card_name]`
        Example:
            `[p]upgrade card troopers`
        """
        card_name = card_name.title()

        # check if card exists
        card_info = self.card_search(card_name)

        if not card_info:
            return await ctx.send(f"{card.title()} does not exist.")

        card_type = str(card_info[0]) + "s"
        card_info = card_info[1]

        # get user card level and number of cards
        async with self.config.user(ctx.author).cards() as cards:
            for item in cards[card_type]:
                if card_name == item:
                    user_level = cards[card_type][item][0]
                    user_num_of_cards = cards[card_type][item][1]

        rarity = card_info.Rarity
        cards_reqd = self.RARITY_INFO[rarity]["UpgradeCards"][user_level]

        if cards_reqd > user_num_of_cards:
            return await ctx.send(f"You do not have enough cards to upgrade. ({user_num_of_cards}/{cards_reqd})")

        leftover = user_num_of_cards - cards_reqd

        upgrade_cost = self.RARITY_INFO[rarity]["UpgradeCost"][user_level]
        reward_xp = self.RARITY_INFO[rarity]["UpgradePlayerExp"][user_level]

        msg = await ctx.send(f"Upgrading {card_name} to level {user_level+1} will cost {upgrade_cost} {STAT_EMOTES['Gold_Icon']}. Continue?")
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if not pred.result:
            return await ctx.send("Upgrade cancelled by the user.")

        try:
            gold = await self.config.user(ctx.author).gold()
            if gold >= upgrade_cost:
                # update config variables
                async with self.config.user(ctx.author).cards() as cards:
                    for item in cards[card_type]:
                        if card_name == item:
                            cards[card_type][item][0] += 1
                            cards[card_type][item][1] = leftover
                upd_gold = gold - upgrade_cost
                await self.config.user(ctx.author).gold.set(upd_gold)
                xp = await self.config.user(ctx.author).xp()
                await self.config.user(ctx.author).xp.set(reward_xp+xp)

                await ctx.send(f"{card_name} upgraded to level {user_level+1}.")
                await ctx.send(f"Rewards: {reward_xp} {STAT_EMOTES['Experience']}")
                level_up = True
                while level_up:
                    level_up = await self.xp_level_handler(ctx)
                    if level_up:
                        await ctx.send(level_up[0])
                        await ctx.send(level_up[1])
            else:
                return await ctx.send("You do not have enough gold to upgrade.")
        except:
            log.exception("Error with updating character sheet.")
            return

    @commands.group(name="collect", autohelp=False)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def _collect(self, ctx):
        """Collect gold, key, free box or defense boxes."""
        if not ctx.invoked_subcommand:
            return await ctx.send("Please specify one of the following to collect: gold, key, free box or defense box.")

    @_collect.command(name="gold")
    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    async def collect_gold(self, ctx):
        """Collect gold from gold mine once every hour: `[p]collect gold`"""
        gold = await self.config.user(ctx.author).gold()
        hq = await self.config.user(ctx.author).hq()
        resource_gold = self.HQ_LEVELS[str(hq)]["ResourceMax"]
        await self.config.user(ctx.author).gold.set(gold+resource_gold)
        await ctx.send(f"You got {resource_gold} {STAT_EMOTES['Gold_Icon']}!")

    @_collect.command(name="key")
    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    async def collect_key(self, ctx):
        """Collect a key once every hour: `[p]collect key`"""
        keys = await self.config.user(ctx.author).keys()
        if keys == 5:
            return await ctx.send("You already have 5 keys!")
        else:
            await self.config.user(ctx.author).keys.set(keys+1)
            await ctx.send(f"You got 1 {STAT_EMOTES['Keys']}!")

    @_collect.command(name="free")
    @commands.cooldown(rate=1, per=10800, type=commands.BucketType.user)
    async def collect_free_box(self, ctx):
        """Collect a free box once every 3 hours: `[p]collect free`"""
        box = await self._box(ctx, "Free")
        await ctx.send(embed=box)

    @_collect.command(name="defense")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def collect_defense_box(self, ctx):
        """Collect defense box if it is available: `[p]collect defense`"""
        temp_def_stars = await self.config.user(ctx.author).temp_def_stars()

        if temp_def_stars < 100:
            return await ctx.send(f"You do not have enough defense stars. ({temp_def_stars}/100)")

        box = await self._box(ctx, "Defense")
        await ctx.send(embed=box)
    
    @commands.command(name="rushboard")
    async def rushboard(self, ctx):
        """Check the leaderboards to see who is at the top!"""
        all_users = await self.config.all_users()
        users = []
        for user_id in all_users:
            user = ctx.guild.get_member(user_id)
            stars = self.get_stars(user)
            users.append({'name': user, 'stars': stars})
        users = sorted(users, key=lambda k: k['stars'])
        embed = discord.Embed(colour=0x98D9EB)
        embed.set_author(name="Leaderboard", 
            icon_url="https://cdn.discordapp.com/attachments/626063027543736320/627811022723350528/Leaderboard.png")
        
        # return first 10 (or fewer) members
        for i in range(10):
            try:
                embed.add_field(name=f"{i+1}. {users['name']}", value=f"{STAT_EMOTES['Stars']} {users['stars']}")
            except:
                break
        
        # add rank of user
        for idx, user in enumerate(users):
            if ctx.author == user['name']:
                    embed.add_field(name=f"Your position: {idx+1}", value=f"{STAT_EMOTES['Stars']} {user['stars']}")
        
        await ctx.send(embed=embed)
    
    def card_search(self, name):
        files = ['troops.csv', 'airdrops.csv',
                 'defenses.csv', 'commanders.csv']
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
                log.exception(
                    f"{file} file could not be found in Rush Wars data folder.")
                continue

    def card_targets(self, targets):
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
                if card_type == 'airdrops':
                    upgrader = 0.5
                else:
                    upgrader = stat/10
                i = 1
                while i < level:
                    stat += upgrader
                    i += 1
                if card_type == 'airdrops':
                    new_stats.append(stat)
                else:
                    new_stats.append(int(stat))
            else:
                new_stats.append(stat)
        return new_stats

    @staticmethod
    def color_lookup(rarity):
        colors = {"Common": 0xAE8F6F, "Rare": 0x74BD9C,
                  "Epic": 0xB77AE0, "Commander": 0xF7EE85}
        return colors[rarity]

    @staticmethod
    def card_emotes(card_name):
        emotes = {
            "Troopers": "<:Troopers:625807035362967605>",
            "Pitcher": "<:Pitcher:625807035954626590>",
            "Shields": "<:Shields:625807036663332865>",
            "Jetpacks": "<:Jetpacks:625807036117942272>",
            "Plumber Van": "<:PlumberVan:625807036462006285>",
            "Henchmen": "<:Henchmen:625807033425199115>",
            "Kungfu": "<:Kungfu:625807035505836032>",
            "Bazooka": "<:Bazooka:625807021316505600>",
            "Hotshot": "<:Hotshot:625807032301125646>",
            "Sneaky Ninja": "<:SneakyNinja:625807033354158100>",
            "Boxer": "<:Boxer:625807036759933025>",
            "Tank": "<:Tank:627548870443925523>",
            "Gorilla": "<:Gorilla:625807036290170901>",
            "Laser": "<:Laser:625807037481353217>",
            "Rocket Truck": "<:RocketTruck:625807036810133515>",
            "Helipod": "<:Helipod:627548868694900774>",
            "Blaze": "<:Blaze:625807036474458112>",
            "Arcade": "<:Arcade:626008229763219477>",
            "Heal": "<:Heal:626008230233112576>",
            "Boost": "<:Boost:626008230186975233>",
            "Fridge": "<:Fridge:626008230279118848>",
            "Paratroopers": "<:Paratroopers:626008231478558732>",
            "Invisibility": "<:Invisibility:626008231713439794>",
            "Satellite": "<:Satellite:626010083406643200>",
            "Cannon": "<:Cannon:626527978368794663>",
            "Mines": "<:Mines:626527978393829417>",
            "Plumber Hole": "<:PlumberHole:626527979811504133>",
            "Mortar": "<:Mortar:626527978800676875>",
            "Bomb": "<:Bomb:626527974937722890>",
            "Gatling": "<:Gatling:626527979677286449>",
            "Walls": "<:Wall:627556663146315776>",
            "Cluster Cake": "<:ClusterCake:626527978477715469>",
            "Tesla": "<:Tesla:627556705231831040>",
            "Box Ninja": "<:BoxNinja:626527977433464842>",
            "Freeze Mine": "<:FreezeMine:626527979723554816>",
            "Dummy": "<:Dummy:626527979085758514>",
            "Rocket Trap": "<:RocketTrap:626527978935025664>",
            "Plasmagun": "<:Plasmagun:626527977215229974>",
            "Lady Grenade": "<:LadyGrenade:627556853139767297>",
            "Bearman": "<:Bearman:627556852846297088>",
            "Mother": "<:Mother:627556854528212992>",
            "Coach": "<:Coach:627556853152481300>",
            "B.I.G.": "<:BIG:627556852913406011>"
        }
        try:
            return emotes[card_name]
        except:
            return emotes["Troopers"]

    @staticmethod
    def type_emotes(card_type):
        emotes = {
            "Troops": "<:RW_Attck:625783202836905984>",
            "Airdrops": "<:RW_Airdrop:626000292810588164>",
            "Defenses": "<:RW_Defense:626338600467824660>",
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

    def total_selected(self, card, data):
        total = 0
        for item in data.keys():
            card_info = self.card_search(item)
            card_space = int(card_info[1].Space)

            number = data[item]
            total += (number * card_space)
        return total

    async def new_hq_cards(self, ctx, hq):
        """Function to handle HQ level ups."""
        # check which cards are unlocked at the new HQ level
        cards_unlocked = {
            "troops": [],
            "airdrops": [],
            "defenses": [],
            "commanders": []
        }
        files = ['troops.csv', 'airdrops.csv',
                 'defenses.csv', 'commanders.csv']
        for file in files:
            fp = self.path / file
            try:
                with fp.open('rt', encoding='iso-8859-15') as f:
                    reader = csv.DictReader(f, delimiter=',')
                    for row in reader:
                        if int(row['UnlockLvl']) == hq:
                            card_type = file.split('.')[0]
                            cards_unlocked[card_type].append(row['Name'])
                            continue
            except FileNotFoundError:
                log.exception("File not found.")
                return
            except Exception as ex:
                return

        # update cards to include newly unlocked cards
        try:
            async with self.config.user(ctx.author).cards() as cards:
                for card_type in ['troops', 'airdrops', 'defenses', 'commanders']:
                    for card in cards_unlocked[card_type]:
                        if card not in list(cards[card_type]):
                            # get card rarity
                            card_info = self.card_search(card)[1]
                            rarity = card_info.Rarity
                            level = base_card_levels[rarity.lower()]
                            cards[card_type][card] = [level, 0]
        except Exception as ex:
            log.exception(ex)
            return

    def rush_strings(self, data):
        """To return strings containing card information."""
        info = ""
        for item in data:
            card_name = item[0]
            card_emote = self.card_emotes(card_name)
            count = item[1]
            if count <= 0:
                continue
            info += f"{card_emote} {card_name} x{count}\n"
        return info

    async def rush_card_level(self, ctx, card_name, card_type):
        """Return the level of card user owns."""
        try:
            async with self.config.user(ctx.author).cards() as cards:
                if card_type == "defenses":
                    card_types = ["troops", "defenses"]
                else:
                    card_types = [card_type]
                for ctype in card_types:
                    data = cards[ctype]
                    for item in data.keys():
                        if card_name == item:
                            return data[item][0]
        except:
            log.exception("Error with character sheet.")
            return

    async def get_rewards(self, ctx, reward_stars):
        hq = await self.config.user(ctx.author).hq()
        cost = self.HQ_LEVELS[str(hq)]["AttackCost"]

        if cost < 25:
            available_gold_in_mine = random.choice(range(5, cost+10))
        else:
            available_gold_in_mine = random.choice(range(25, cost+10))

        if reward_stars > 0:
            reward_gold = available_gold_in_mine * reward_stars
        else:
            reward_gold = random.choice(range(0, available_gold_in_mine))

        try:
            async with self.config.user(ctx.author).stars() as stars:
                att_stars = stars["attack"]
                def_stars = stars["defense"]
        except:
            log.exception("Error with character sheet.")
            return
        total_stars = att_stars + def_stars
        i = 0
        for league in LEAGUES.keys():
            i += 1
            low, high = LEAGUES[league][0], LEAGUES[league][1]
            if total_stars in range(low, high):
                single_star_xp = i
                break
        reward_xp = single_star_xp * reward_stars

        # update user variables
        gold = await self.config.user(ctx.author).gold()
        upd_gold = gold + reward_gold
        await self.config.user(ctx.author).gold.set(upd_gold)
        xp = await self.config.user(ctx.author).xp()
        upd_xp = xp + reward_xp
        await self.config.user(ctx.author).xp.set(upd_xp)
        async with self.config.user(ctx.author).stars() as stars:
            att_stars = stars["attack"] + reward_stars
        await self.config.user(ctx.author).set_raw("stars", "attack", value=att_stars)
        # except:
        #     log.exception("Error with character sheet.")
        #     return

        embed = discord.Embed(colour=0x98D9EB, title="Rewards")
        embed.add_field(
            name="Stars", value=f"{STAT_EMOTES['Stars']} {reward_stars}")
        embed.add_field(
            name="Gold", value=f"{STAT_EMOTES['Gold_Icon']} {reward_gold}")
        embed.add_field(name="Experience",
                        value=f"{STAT_EMOTES['Experience']} {reward_xp}")

        return embed

    async def xp_level_handler(self, ctx):
        """Handles xp level ups."""
        xp = await self.config.user(ctx.author).xp()
        lvl = await self.config.user(ctx.author).lvl()

        next_xp = self.XP_LEVELS[str(lvl)]["ExpToNextLevel"]

        if xp >= next_xp:
            carry = xp - next_xp
        else:
            return False

        await self.config.user(ctx.author).xp.set(carry)
        await self.config.user(ctx.author).lvl.set(lvl+1)

        level_up_msg = f"Level up! You have reached level {lvl+1}."

        gem_reward = self.XP_LEVELS[str(lvl)]["GemReward"]
        reward_msg = f"Rewards: {gem_reward} {STAT_EMOTES['Gems']}"

        gems = await self.config.user(ctx.author).gems()
        upd_gem = gems + gem_reward
        await self.config.user(ctx.author).gems.set(upd_gem)

        return (level_up_msg, reward_msg)

    async def cost_gold(self, ctx):
        """Handle rush gold cost."""
        hq = await self.config.user(ctx.author).hq()
        cost = self.HQ_LEVELS[str(hq)]["AttackCost"]

        gold = await self.config.user(ctx.author).gold()

        if cost >= gold:
            return False

        upd_gold = gold - cost
        await self.config.user(ctx.author).gold.set(upd_gold)
        return True

    async def _box(self, ctx, box_type=None):
        """To handle box openings."""

        unlocked_boxes = await self.config.user(ctx.author).boxes()

        if not box_type:
            c = Boxes(unlocked_boxes)
            box_type = c.box_type

        box_data = self.BOXES_INFO[box_type]

        hq = await self.config.user(ctx.author).hq()

        reward_gem = None

        if box_type == "Free":
            multiplier = self.HQ_LEVELS[str(hq)]["BoxMultiplier"] / 100
            desc = f"HQ {hq} Free Box"
            get_gem = random.randint(1, 10)
            if get_gem >= 7:
                reward_gem = random.randint(2, 8)
        else:
            try:
                async with self.config.user(ctx.author).stars() as stars:
                    att_stars = stars["attack"]
                    def_stars = stars["defense"]
            except:
                log.exception("Error with character sheet.")
                return
            total_stars = att_stars + def_stars
            i = 0
            for league in LEAGUES.keys():
                low, high, multi = LEAGUES[league]
                if total_stars in range(low, high):
                    multiplier = multi / 100
                    desc = f"{league.title()} {box_type.title()} Box"
                    break

        user_cards = {
            "Common": [],
            "Rare": [],
            "Epic": [],
            "Commander": []
        }
        async with self.config.user(ctx.author).cards() as cards:
            for i in [cards["troops"], cards["airdrops"], cards["defenses"]]:
                for card_name in i.keys():
                    card_info = self.card_search(card_name)[1]
                    rarity = card_info.Rarity
                    user_cards[rarity].append(card_name)
            commanders = cards["commanders"]
            if commanders:
                for commander in commanders:
                    user_cards["Commander"].append(commander)

        stacks = box_data["Stacks"]
        total_cards = round(box_data["TotalCards"] * multiplier)
        rare_chance = box_data["RareChance"]
        epic_chance = box_data["EpicChance"]
        commander_chance = box_data["CommanderChance"]

        commander = epic = rare = False
        random_draw = random.random()

        if random_draw < 1/commander_chance:
            commander = True

        if random_draw < 1/epic_chance:
            epic = True

        if random_draw < 1/rare_chance:
            rare = True

        draws = {}

        # guaranteed commander in 1st box of HQ 5
        if commanders:
            for item in commanders:
                num_of_cards = commanders[item][1]
                if num_of_cards < 1 and hq == 5:
                    commander = True

        # code below is a complete mess.
        # move this to boxes.py
        if commander:
            total_commander = 1
            total_epics = ceil((total_cards - 1) * 0.03)
            total_rares = ceil((total_cards - 1) * 0.25)
            total_commons = round((total_cards - 1) * 0.72)
            total_all = total_commander + total_epics + total_rares + total_commons
            if total_all > total_cards:
                diff = total_all - total_cards
                total_commons -= diff
            elif total_all < total_cards:
                diff = total_cards - total_all
                total_commons += diff

            if stacks == 3:
                distribution = (1, 1, 0, 1)
            elif stacks == 4:
                distribution = (1, 1, 0, 2)
            elif stacks == 5:
                distribution = (1, 0, 1, 2)
            elif stacks == 8:
                distribution = (1, 1, 2, 4)

            commander_draw = user_cards["Commander"]
            if not commander_draw:
                commander_draw = user_cards["Epic"]
                if not commander_draw:
                    commander_draw = user_cards["Rare"]
                    if not commander_draw:
                        commander_draw = user_cards["Common"]
            draws[random.choice(commander_draw)] = 1

            if distribution[1] > 0:
                count = self.split_in_integers(total_epics, distribution[1])
                for i in range(distribution[1]):
                    epic_draw = user_cards["Epic"]
                    if not epic_draw:
                        epic_draw = user_cards["Rare"]
                        if not epic_draw:
                            epic_draw = user_cards["Common"]

                    drawn = random.choice(epic_draw)
                    if drawn in draws.keys():
                        draws[drawn] += count[i]
                    else:
                        draws[drawn] = count[i]

            if distribution[2] > 0:
                count = self.split_in_integers(total_rares, distribution[2])
                for i in range(distribution[2]):
                    rare_draw = user_cards["Rare"]
                    if not epic_draw:
                        rare_draw = user_cards["Common"]

                    drawn = random.choice(rare_draw)
                    if drawn in draws.keys():
                        draws[drawn] += count[i]
                    else:
                        draws[drawn] = count[i]

                if distribution[3] > 0:
                    count = self.split_in_integers(
                        total_commons, distribution[3])
                    for i in range(distribution[3]):
                        common_draw = user_cards["Common"]

                        drawn = random.choice(common_draw)
                        if drawn in draws.keys():
                            draws[drawn] += count[i]
                        else:
                            draws[drawn] = count[i]

        elif epic:
            total_epics = ceil(total_cards * 0.03)
            total_rares = ceil(total_cards * 0.25)
            total_commons = round(total_cards * 0.72)
            total_all = total_epics + total_rares + total_commons
            if total_all > total_cards:
                diff = total_all - total_cards
                total_commons -= diff
            elif total_all < total_cards:
                diff = total_cards - total_all
                total_commons += diff

            if stacks == 3:
                distribution = (1, 0, 2)
            elif stacks == 4:
                distribution = (1, 1, 2)
            elif stacks == 5:
                distribution = (1, 2, 2)
            elif stacks == 8:
                distribution = (2, 2, 4)

            if distribution[0] > 0:
                count = self.split_in_integers(total_epics, distribution[0])
                for i in range(distribution[0]):
                    epic_draw = user_cards["Epic"]
                    if not epic_draw:
                        epic_draw = user_cards["Rare"]
                        if not epic_draw:
                            epic_draw = user_cards["Common"]

                    drawn = random.choice(epic_draw)
                    if drawn in draws.keys():
                        draws[drawn] += count[i]
                    else:
                        draws[drawn] = count[i]

            if distribution[1] > 0:
                count = self.split_in_integers(total_rares, distribution[1])
                for i in range(distribution[1]):
                    rare_draw = user_cards["Rare"]
                    if not rare_draw:
                        rare_draw = user_cards["Common"]

                drawn = random.choice(rare_draw)
                if drawn in draws.keys():
                    draws[drawn] += count[i]
                else:
                    draws[drawn] = count[i]

            if distribution[2] > 0:
                count = self.split_in_integers(total_commons, distribution[2])
                for i in range(distribution[2]):
                    common_draw = user_cards["Common"]

                    drawn = random.choice(common_draw)
                    if drawn in draws.keys():
                        draws[drawn] += count[i]
                    else:
                        draws[drawn] = count[i]

        elif rare:
            total_rares = ceil(total_cards * 0.28)
            total_commons = round(total_cards * 0.72)
            total_all = total_rares + total_commons
            if total_all > total_cards:
                diff = total_all - total_cards
                total_commons -= diff
            elif total_all < total_cards:
                diff = total_cards - total_all
                total_commons += diff

            if stacks == 3:
                distribution = (1, 2)
            elif stacks == 4:
                distribution = (1, 3)
            elif stacks == 5:
                distribution = (2, 3)
            elif stacks == 8:
                distribution = (3, 5)

            if distribution[0] > 0:
                count = self.split_in_integers(total_rares, distribution[0])
                for i in range(distribution[0]):
                    rare_draw = user_cards["Rare"]
                    if not rare_draw:
                        rare_draw = user_cards["Common"]

                    drawn = random.choice(rare_draw)
                    if drawn in draws.keys():
                        draws[drawn] += count[i]
                    else:
                        draws[drawn] = count[i]

            if distribution[1] > 0:
                count = self.split_in_integers(total_commons, distribution[1])
                for i in range(distribution[1]):
                    common_draw = user_cards["Common"]

                    drawn = random.choice(common_draw)
                    if drawn in draws.keys():
                        draws[drawn] += count[i]
                    else:
                        draws[drawn] = count[i]

        else:
            total_commons = total_cards

            count = self.split_in_integers(total_commons, stacks)
            for i in range(stacks):
                common_draw = user_cards["Common"]

                drawn = random.choice(common_draw)
                if drawn in draws.keys():
                    draws[drawn] += count[i]
                else:
                    draws[drawn] = count[i]

        try:
            async with self.config.user(ctx.author).cards() as cards:
                for card_name in draws.keys():
                    count = draws[card_name]
                    card_info = self.card_search(card_name)
                    card_type = str(card_info[0]) + "s"
                    # return await ctx.send(card_name)
                    # update number of cards
                    cards[card_type][card_name][1] += count
        except Exception as ex:
            log.exception(ex)
            return

        # handle gold
        min_gold = round(box_data["MinGold"] * multiplier)
        max_gold = round(box_data["MaxGold"] * multiplier)

        reward_gold = random.randint(min_gold, max_gold)

        gold = await self.config.user(ctx.author).gold()
        upd_gold = gold + reward_gold
        await self.config.user(ctx.author).gold.set(upd_gold)

        # increase number of boxes
        await self.config.user(ctx.author).boxes.set(unlocked_boxes+1)

        # return rewards embed
        embed = discord.Embed(colour=0x98D9EB)
        embed.set_author(
            name=desc, icon_url=f"https://www.rushstats.com/assets/box/{box_type}.png")

        if reward_gem:
            gems = await self.config.user(ctx.author).gems()
            upd_gems = gold + reward_gold
            await self.config.user(ctx.author).gold.set(upd_gems)
            embed.add_field(
                name=f"Gems {STAT_EMOTES['Gems']}", value=f"{reward_gem}")

        embed.add_field(
            name=f"Gold {STAT_EMOTES['Gold_Icon']}", value=f"{reward_gold}")

        for rarity in user_cards.keys():
            # embed.add_field()
            items = user_cards[rarity]
            for card in draws.keys():
                count = draws[card]
                if card in items:
                    # card_rarity = rarity
                    card_emote = self.card_emotes(card)
                    embed.add_field(
                        name=f"{card} {card_emote} x {count}", value=f"Rarity: {rarity}")

        return embed

    def split_in_integers(self, number, num_of_pieces):
        """Split a number into number of integers."""
        if num_of_pieces == 1:
            total_sum = 1
        else:
            total_sum = sum(range(1, num_of_pieces))

        parts = []
        for i in range(num_of_pieces):
            x = int((i+1) * number / total_sum)
            parts.append(x)

        parts.sort()
        return parts

    async def handle_keys(self, ctx, stars):
        """Handle keys and check whether to open box or not."""
        temp_stars = await self.config.user(ctx.author).temp_stars()
        keys = await self.config.user(ctx.author).keys()

        if keys > 0:
            temp_stars += stars
            if temp_stars >= 5:
                # update config variable
                await self.config.user(ctx.author).temp_stars.set(temp_stars - 5)
                # update keys
                await self.config.user(ctx.author).keys.set(keys-1)
                return True
            else:
                await self.config.user(ctx.author).temp_stars.set(temp_stars)
                return False
        if keys < 0:
            temp_stars += stars
            if temp_stars > 5:
                temp_stars = 5
            await self.config.user(ctx.author).temp_stars.set(temp_stars)
            return False

    async def matchmaking(self, ctx):
        user_stars = await self.get_stars(ctx.author)
        # return await ctx.send(f"`{ctx.author}`")
        selected = None

        opponents = await self.config.all_users()
        opponent_keys = list(opponents.keys())
        random.shuffle(opponent_keys)
        for opponent_id in opponent_keys:
            # return await ctx.send(opponent)
            if opponent_id == ctx.author.id:
                continue

            opponent = ctx.guild.get_member(opponent_id)
            opponent_stars = await self.get_stars(opponent)

            if user_stars in range(opponent_stars-100, opponent_stars+100):
                if opponents[opponent_id]["active"]["defenses"]:
                    selected = opponent
                    break
            else:
                continue

        return selected

    async def get_stars(self, user):
        """Get total stars of selected user."""
        try:
            async with self.config.user(user).stars() as stars:
                att_stars = stars["attack"]
                def_stars = stars["defense"]
        except:
            log.exception("Error with character sheet.")
            return

        return att_stars + def_stars
    