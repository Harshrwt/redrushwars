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
    "xp",
    "hq",
    "chopper",
    "cards",
    "squad",
    "stars",
    "gold",
    "gems"
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
        params = {k: int(v) for k, v in matches.groupdict().items() if v is not None}
        if params:
            return timedelta(**params)
    return None


class Card:
    """An object to represent a card in the game world."""

    def __init__(self, **kwargs):
        self.name: str = kwargs.pop("name")
        