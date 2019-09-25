# Standard Library
import csv
import json
import random
import logging
from collections import namedtuple
from typing import Optional

# Discord
import discord

# Redbot
from redbot.core import commands, Config
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

__version__ = "0.0.1"
__author__ = "Snowsee"

# (level, number of cards)
default_card_stats = (1, 1)

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
                    "Sneaky Ninja": default_card_stats,  # only for testing, remove later
                },
                "airdrops": {
                    "Arcade": default_card_stats,
                },
                "defenses": {
                    "Cannon": default_card_stats,
                    "Mines": default_card_stats,
                },
                "commanders": {},
            },
            "active": {
                "troops": {"Troopers": 0, "Pitcher": 0, "Shields": 0},
                "airdrops": {"Arcade": 0},
                "defenses": {"Troopers": 0},
                "commanders": {},
            },
            "stars": 0,
            "keys": 5,
            # "gold": 200,
            "gems": 150,
        }

default_defenses = [
    {"Troopers": 4, "Pitcher": 0, "Shields": 0},
    {"Troopers": 0, "Pitcher": 4, "Shields": 0},
    {"Troopers": 0, "Pitcher": 0, "Shields": 4},
    {"Troopers": 2, "Pitcher": 2, "Shields": 0},
    {"Troopers": 1, "Pitcher": 0, "Shields": 3},
    {"Troopers": 0, "Pitcher": 3, "Shields": 1}
]

base_card_levels = {
    "common": 1,
    "rare": 5,
    "epic": 9,
    "commander": 13
}

max_card_level = 20

# chopperLvl: (troops, airdrops, defenses)
chopper_capacity = {
    1: (3, 1, 4),
    2: (5, 1, 5),
    3: (6, 1, 7),
    4: (6, 1, 9),
    5: (7, 2, 10),
    6: (8, 2, 11),
    7: (9, 2, 12),
    8: (10, 2, 13)
}


class RushWars(BaseCog):
    """Simulate Rush Wars"""

    def __init__(self):
        self.path = bundled_data_path(self)

        self.config = Config.get_conf(
            self, 1_070_701_001, force_registration=True)

        self.config.register_user(**default_user)

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
    async def rush(self, ctx, *, member: discord.Member = None):
        """Attack a base!"""

        if member is not None:
            if member.id == ctx.author.id:
                return await ctx.send("You can't battle against yourself!")

        try:
            async with self.config.user(ctx.author).active() as active:
                troops = active["troops"]
                airdrops = active["airdrops"]
                # commanders = active["commanders"]
                player = ctx.author.name
        except Exception as ex:
            return await ctx.send(f"Error with character sheet!")
            log.exception(f"Error with character sheet: {ex}!")

        hp = 0
        att = 0
        def_hp = 0
        def_att = 0

        sel_trp = sum(troops.values())
        sel_ardp = sum(airdrops.values())

        if sel_trp == 0 or sel_trp == 0:
            return await ctx.send("Please add items to squad! Help: `[p]help squad`")

        for troop in troops.keys():
            troop_stats = self.card_search(troop)[1]
            count = troops[troop]
            hp += int(troop_stats.Hp) * count
            att += int(troop_stats.Att) * count

        for airdrop in airdrops.keys():
            airdrop_stats = self.card_search(airdrop)[1]
            count = airdrops[airdrop]
            ability = airdrop_stats.Ability
            if ability == "Damage":
                att += int(airdrop_stats.Value) * \
                           float(airdrop_stats.Duration) * count
            elif ability == "Boost":
                att += int(airdrop_stats.Value) * \
                           float(airdrop_stats.Duration) * count
                hp += int(airdrop_stats.Value) * \
                          float(airdrop_stats.Duration) * count
            elif ability == "Heal":
                hp += int(airdrop_stats.Value) * \
                          float(airdrop_stats.Duration) * count
            elif ability in ["Invisibility", "Freeze"]:
                def_att -= int(airdrop_stats.Value) * \
                               float(airdrop_stats.Duration) * count

        if member is not None:
            try:
                async with self.config.user(member).active() as active:
                    defenses = active["defenses"]
                    opponent = member.name
            except:
                await ctx.send("User has not set a defense!")
                return
        else:
            defenses = random.choice(default_defenses)
            opponent = "Computer"

        for defense in defenses.keys():
            defense_stats = self.card_search(defense)[1]
            count = defenses[defense]
            def_hp += int(defense_stats.Hp) * count
            def_att += int(defense_stats.Att) * count

        troop = [(troop, troops[troop]) for troop in troops.keys()]
        airdrop = [(airdrop, airdrops[airdrop]) for airdrop in airdrops.keys()]
        defense = [(defense, defenses[defense]) for defense in defenses.keys()]

        attack_str = "`TROOPS`\n"
        defense_str = ""
        for item in troop:
            card_name = item[0]
            card_emote = self.card_emotes(card_name)
            count = item[1]
            if count <= 0:
                continue
            attack_str += f"{card_emote} {card_name} x{count}\n"
        attack_str += "`AIRDROPS`\n"
        for item in airdrop:
            card_name = item[0]
            card_emote = self.card_emotes(card_name)
            count = item[1]
            if count <= 0:
                continue
            attack_str += f"{card_emote} {card_name} x{count}\n"
        for item in defense:
            card_name = item[0]
            card_emote = self.card_emotes(card_name)
            count = item[1]
            if count <= 0:
                continue
            defense_str += f"{card_emote} {card_name} x{count}\n"

        embed = discord.Embed(colour=0x999966, title="Battle Info",
                              description="Will you get mega rich after this battle?")
        embed.set_author(name=f"{player} vs {opponent}",
                         icon_url="https://cdn.discordapp.com/attachments/622323508755693581/626058519929684027/Leaderboard.png")
        embed.add_field(
            name="Attack <:RW_Attck:625783202836905984>", value=attack_str)
        embed.add_field(
            name="Defense <:RW_Defenses:626339085501333504>", value=defense_str)
        await ctx.send(embed=embed)

        if def_hp/att < hp/def_att:
            await ctx.send("You win!")
        else:
            await ctx.send("You lose!")

    @commands.command()
    async def card(self, ctx, card_name: str, level: int = None):
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

        embed = discord.Embed(colour=color, title=card.Name,
                              description=description, url=url)
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(
            name="Level <:RW_Level:625788888480350216>", value=level)

        if card_type == 'troop' or card_type == 'defense':
            lvl_stats = [int(card.Hp), int(card.Att)]
            upd_stats = self.card_level(
                level, lvl_stats, card.Rarity, card_type)

            if isinstance(upd_stats, int):
                await ctx.send((f"{card.Rarity} starts at level {upd_stats}! Showing level {upd_stats} stats..."))
                level = upd_stats
                upd_stats = lvl_stats

            target = self.card_targets(int(card.Targets))

            dps = int(upd_stats[1]/float(card.AttSpeed))

            embed.add_field(
                name="Health <:RW_Health:625786278058917898>", value=upd_stats[0])
            embed.add_field(
                name="Damage <:RW_Damage:625786276938907659>", value=upd_stats[1])
            embed.add_field(
                name="Damage per second <:RW_DPS:625786277903466498>", value=dps)
            if card_type == 'troop':
                embed.add_field(
                    name="Squad Size <:RW_Count:625786275802382347>", value=card.Count)
                embed.add_field(
                    name="Space <:RW_Space:625783199670206486>", value=card.Space)
            else:
                embed.add_field(
                    name="Space <:RW_Defense:626338600467824660>", value=card.Space)
            embed.add_field(
                name="Targets <:RW_Targets:625786278096535574>", value=target)
            embed.add_field(
                name="Attack Speed <:RW_AttSpeed:625787097709543427>", value=f"{card.AttSpeed}s")

        elif card_type == 'airdrop':
            lvl_stats = [float(card.Duration)]
            upd_stats = self.card_level(
                level, lvl_stats, card.Rarity, card_type)

            if isinstance(upd_stats, int):
                await ctx.send((f"{card.Rarity} starts at level {upd_stats}! Showing level {upd_stats} stats..."))
                level = upd_stats
                upd_stats = lvl_stats

            value_emote = self.airdrop_value_emotes(card.Ability)

            embed.add_field(
                name=f"{card.Ability} {value_emote}", value=card.Value)
            embed.add_field(
                name="Duration <:Duration:626042235753857034>", value=str(upd_stats[0])+"s")
            embed.add_field(
                name="Space <:RW_Airdrop:626000292810588164>", value=card.Space)

        embed.add_field(
            name="Rarity <:RW_Rarity:625783200983154701>", value=card.Rarity)
        embed.add_field(
            name="HQ Level <:RW_HQ:625787531664818224>", value=card.UnlockLvl)
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
                if card_type == 'airdrop':
                    upgrader = 0.5
                else:
                    upgrader = stat/10
                i = 1
                while i < level:
                    stat += upgrader
                    i += 1
                if card_type == 'airdrop':
                    new_stats.append(stat)
                else:
                    new_stats.append(int(stat))
            else:
                new_stats.append(stat)
        return new_stats

    @commands.group(name="squad", autohelp=False)
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
            except Exception as ex:
                return await ctx.send(f"Error with character sheet!")
                log.exception(f"Error with character sheet: {ex}!")

            embed = discord.Embed(colour=0x999966, title="Squad",
                                  description="Is your squad strong enough to kick butt and get mega rich?")
            embed.set_author(
                name=ctx.author.name, icon_url="https://cdn.discordapp.com/attachments/626063027543736320/626063120263020574/squad-icon.png")
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
                        sqd_str += f"{card_emote} `{card_name}` x{count}\n"

                if sqd_str == "":
                    sqd_str = f"No {kind.lower()} in squad."
                type_emote = self.type_emotes(kind)
                embed.add_field(name=f"{kind} {type_emote}", value=sqd_str)

            await ctx.send(embed=embed)

    @_squad.command(name="add")
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
        card_space = int(card_info[1].Space)

        chopperLvl = await self.config.user(ctx.author).chopper()

        if card_type == "troops":
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active[card_type]
            except:
                log.exception("Error with character sheet.")
                return
            capacity = chopper_capacity[chopperLvl][0]

        elif card_type == "airdrops":
            try:
                async with self.config.user(ctx.author).active() as active:
                    data = active[card_type]
            except:
                log.exception("Error with character sheet.")
                return
            capacity = chopper_capacity[chopperLvl][1]

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
    async def _defense(self, ctx):
        """Lookup your defense. Subcommands give more defense functions."""

        if not ctx.invoked_subcommand:
            try:
                async with self.config.user(ctx.author).active() as active:
                   defense = active["defenses"]
            except Exception as ex:
                return await ctx.send(f"Error with character sheet!")
                log.exception(f"Error with character sheet: {ex}!")

            embed = discord.Embed(colour=0x999966, title="Defense",
                                  description="Is your defense strong enough to protect your treasures?")
            embed.set_author(
                name=ctx.author.name, icon_url="https://cdn.discordapp.com/attachments/626063027543736320/626338507958386697/Defense.png")
            def_str = ""
            # card_info = [(item, items[item]) for item in items.keys()]
            for item in defense.keys():
                if item:
                    card_name = item
                    card_emote = self.card_emotes(card_name)
                    count = defense[item]
                    if count <= 0:
                        continue
                    def_str += f"{card_emote} `{card_name}` x{count}\n"

            if def_str == "":
                def_str = "No defenses in squad."
            emote = self.type_emotes("Defenses")
            embed.add_field(name=f"Defenses {emote}", value=def_str)

            await ctx.send(embed=embed)

    @_defense.command(name="add")
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
        capacity = chopper_capacity[chopperLvl][2]

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
    
    @commands.command(name="sethq")
    async def set_hq(self, ctx, lvl:int=None):
        await self.level_up_hq(ctx, lvl)
        await ctx.send("Done")

    @commands.command(name="cards")
    async def cards(self, ctx):
        """Shows all the cards you can unlock."""
        embed = discord.Embed(colour=0x999966, title="Cards")
        try:
            async with self.config.user(ctx.author).cards() as cards:
                for card_type in ['troops', 'airdrops', 'defenses', 'commanders']:
                    card_str = ""
                    data = cards[card_type]
                    for item in data.keys():
                        emote = self.card_emotes(item)
                        level = data[item][0]
                        found = data[item][1]
                        card_str += f"{emote} {item}\nLevel: {level}\tFound: {found}\n\n"
                    
                    if card_str == "":
                        card_str = f"No {card_type} unlocked."
                    
                    type_emote = self.type_emotes(card_type.title())
                    embed.add_field(name=f"`{card_type.upper()}` {type_emote}", value=card_str)
        except Exception as ex:
            log.exception(ex)
            return
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
            "Sneaky Ninja": "<:SneakyNinja:625807033354158100>",
            "Arcade": "<:Arcade:626008229763219477>",
            "Heal": "<:Heal:626008230233112576>",
            "Boost": "<:Boost:626008230186975233>",
            "Fridge": "<:Fridge:626008230279118848>",
            "Paratroopers": "<:Paratroopers:626008231478558732>",
            "Invisibility": "<:Invisibility:626008231713439794>",
            "Satellite": "<:Satellite:626010083406643200>",
            "Cannon": "<:Cannon:123432123>"
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

    async def level_up_hq(self, ctx, lvl:int=None):
        """Function to handle HQ level ups."""
        # get current hq level 
        if lvl is None:
            hq = await self.config.user(ctx.author).hq() + 1
        else:
            hq = int(lvl)

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
        # return cards_unlocked
        # update cards to include newly unlocked cards
        try:
            async with self.config.user(ctx.author).cards() as cards:
                for card_type in ['troops', 'airdrops', 'defenses', 'commanders']:
                    for card in cards_unlocked[card_type]:
                        if card not in list(cards[card_type]):
                            cards[card_type][card] = (1,0)
        except Exception as ex:
            log.exception(ex)
            return
