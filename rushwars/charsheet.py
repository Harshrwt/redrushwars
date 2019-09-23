import discord
import asyncio
import logging
import re

from typing import List, Set, Dict, Optional
from datetime import timedelta

from redbot.core import commands
from redbot.core import Config, bank
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.predicates import ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

from discord.ext.commands.converter import Converter
from discord.ext.commands.errors import BadArgument


log = logging.getLogger("red.rushwars")

_ = Translator("Rush Wars", __file__)

ORDER = [
    "name",
    ""
]

TIME_RE_STRING = r"\s?".join(
    [
        r"((?P<days>\d+?)\s?(d(ays?)?))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m))?",
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
    ]
)

TIME_RE = re.compile(TIME_RE_STRING, re.I)


def parse_timedelta(argument: str) -> Optional[timedelta]:
    matches = TIME_RE.match(argument)
    if matches:
        params = {k: int(v)
                  for k, v in matches.groupdict().items() if v is not None}
        if params:
            return timedelta(**params)
    return None


class Card:
    """An object to represent a card in the game world."""

    def __init__(self, **kwargs):
        self.name: str = kwargs.pop("name")
        self.rarity: str = kwargs.pop("rarity")
        self.att: int = kwargs.pop("att")
        self.hp: int = kwargs.pop("hp")
        self.count: int = kwargs.pop("count")
        self.targets: int = kwargs.pop("targets")
        self.space: int = kwargs.pop("space")
        self.canFly: bool = kwargs.pop("canFly")

    # @staticmethod
    # def _remove_markdowns(item):
    #     if item.startswith(".") or "_" in item:
    #         item = item.replace("_", " ").replace(".", "")
    #     if item.startswith("["):
    #         item = item.replace("[", "").replace("]", "")
    #     if item.startswith("{.:'"):
    #         item = item.replace("{.:'", "").replace("':.}", "")
    #     return item

        @classmethod
        def _from_json(cls, data: dict):
            name = "".json(data.keys())
            data = data[name]

            rarity = data["rarity"] if "rarity" in data else "Common"
            att = data["att"] if "att" in data else 0
            hp = data["hp"] if "hp" in data else 0
            count = data["count"] if "count" in data else 0
            targets = data["targets"] if "targets" in data else 0
            space = data["space"] if "space" in data else 0
            canFly = data["canFly"] if "canFly" in data else False

            card_data = {
                "name": name,
                "rarity": rarity,
                "att": att,
                "hp": hp,
                "count": count,
                "targets": targets,
                "space": space,
                "canFly": canFly
            }
            return cls(**card_data)

        def _to_json(self) -> dict:
            return {
                self.name: {
                    "name": self.name,
                    "rarity": self.rarity,
                    "att": self.att,
                    "hp": self.hp,
                    "count": self.count,
                    "targets": self.targets,
                    "space": self.space,
                    "canFly": self.canFly
                }
            }


class CardConverter(Converter):
    async def convert(self, ctx, argument):
        try:
            c = await Player._from_json(ctx.bot.get_cog("RushWars").config, ctx.author)
        except Exception:
            log.exception("Error with the new character sheet.")
            return
        no_markdown = Card._remove_markdowns(argument)
        lookup = list(i for x, i in c.profile.items()
                      if no_markdown.lower() in x.lower())
        lookup_m = list(i for x, i in c.profile.items()
                        if argument.lower() == str(i).lower())
        if len(lookup) == 1:
            return lookup[0]
        elif len(lookup_m) == 1:
            return lookup_m[0]
        elif len(lookup) == 0 and len(lookup_m) == 0:
            raise BadArgument(
                _("`{}` doesn't seem to match any cards you own.").format(argument)
            )
        else:
            if len(lookup) > 10:
                raise BadArgument(
                    _("You have too many cards matching the name `{}`, please be more specific.").format(
                        argument
                    )
                )
            cards = ""
            for number, card in enumerate(lookup):
                cards += f"{number}. {str(card)} (owned {card.owned})\n"

            msg = await ctx.send(
                _("Multiple cards share that name, which one would you like?\n{items}".format(
                    cards=box(cards, lang="css"))
                  )
            )

            emojis = ReactionPredicate.NUMBER_EMOJIS[:len(lookup)]
            start_adding_reactions(msg, emojis)
            pred = ReactionPredicate.with_emojis(emojis, msg, user=ctx.author)
            try:
                await ctx.bot.wait_for("reaction_add", check=pred, timeout=30)
            except asyncio.TimeoutError:
                raise BadArgument(_("Alright then."))
            return lookup[pred.result]


class GameSession:
    """A class to represent and hold current game sessions per server."""

    challenge: str
    attribute: str
    timer: int
    guild: discord.Guild
    boss: bool


class Player(Card):
    """A class to represent player stats."""

    def __init__(self, **kwargs):
        self.exp: int = kwargs.pop("exp")
        self.lvl: int = kwargs.pop("lvl")
        self.hq: int = kwargs.pop("hp")
        self.chopper: int = kwargs.pop("chopper")
        self.stars: int = kwargs.pop("stars")
        self.gold: int = kwargs.pop("gold")
        self.gems: bool = kwargs.pop("gems")
        self.troops: List[str] = kwargs.pop("troops")
        self.airdrops: List[str] = kwargs.pop("airdrops")
        self.defenses: List[str] = kwargs.pop("defenses")
        self.commanders: List[str] = kwargs.pop("commanders")
        self.user: discord.Member = kwargs.pop("user")
    
    def __str__(self):
        """Define str to be our default look for the character sheet."""
        next_lvl = int((self.lvl + 1) ** 4)
        return _(
            "[{user}'s Profile]\n\n"
            "Level: {lvl}\tStars: {stars}"
            "Gold: {gold}\tGems: {gems}\n\n"
            "[Troops]\n{troops}\n\n"
            "[Airdrops]\n{airdrops}"
            "[Defenses]\n{defenses}"
            "[Commander]\n{commander}\n\n"
        ).format(
            user=self.user.display_name,
            lvl=self.lvl,
            stars=self.stars,
            gold=self.gold,
            gems=self.gems,
            troops='\n- '.join(self.troops),
            airdrops='\n- '.join(self.airdrops),
            defenses='\n- '.join(self.troops),
            commander='\n- '.join(self.commanders),
        )

    # def __cards__(self, kind):
    #     """
    #         Define a secondary like __str__ to show selected cards.
    #     """
    #     # form_string = ""
    #     # last_card = ""
    #     # rjust = max([len(str(getattr(self, i) for i in ORDER))])
        
    #     # for item in ORDER:
    #     #     card = getattr(self, item)
    #     #     if card is None:
    #     #         card_name = card
    #     #         form_string += _("\n {}").format(card_name.title())
    #     #         last_card = card_name

    #     #         att = card.att
    #     #         hp = card.hp
    #     #         rarity = card.rarity
    #     #         count = card.count
    #     #         if card.targets == 0:
    #     #             targets = "Ground"
    #     #         elif card.targets == 1:
    #     #             targets = "Air"
    #     #         else:
    #     #             targets = "Air & Ground"
    #     #         canFly = "Yes" if card.canFly else "No"

        
    def _sort_new_squad(self, squad: dict):
        # tmp = {}
        # for item in squad:
        #     troops = squad[troops].slot
        return squad
            
    def __squad__(self, consumed: list=[]):
        categories = [self.troops, self.airdrops, self.commanders]
        i = 1
        for category in categories:
            sqd = self._sort_new_squad(category)
            if i == 1:
                kind = "Troops"
            if i == 2:
                kind = "Airdrops"
            if i == 3:
                kind = "Commanders"
            else:
                kind = "Cards"
            form_string = _(f"{kind} in squad: \n")
            consumed_list = [i for i in consumed]
            for card_name in sqd:
                form_string += f"\n{card_name}"

        return form_string + "\n"

    def _from_json(self, ctx, bt):
        pass
