import discord
import logging
import random
import re

from discord.utils import get
from discord import app_commands
from discord.ext import commands

from ballsdex.settings import settings
from ballsdex.core.utils.paginator import FieldPageSource, Pages
from ballsdex.settings import settings
from ballsdex.core.models import Player, BallInstance, specials, balls 
from ballsdex.packages.countryballs.countryball import BallSpawnView

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.gaPacks")

class gaPacks(commands.Cog):
    """
    Simple vote commands.
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def rarity(self, interaction: discord.Interaction):
        # DO NOT CHANGE THE CREDITS TO THE AUTHOR HERE!
        """
        Show the rarity list of the dex - Made by GamingadlerHD
        """
        # Filter enabled collectibles
        enabled_collectibles = [x for x in balls.values() if x.enabled]

        if not enabled_collectibles:
            await interaction.response.send_message(
                f"There are no collectibles registered in {settings.bot_name} yet.",
                ephemeral=True,
            )
            return

        # Sort collectibles by rarity in ascending order
        sorted_collectibles = sorted(enabled_collectibles, key=lambda x: x.rarity)

        entries = []

        for collectible in sorted_collectibles:
            name = f"{collectible.country}"
            emoji = self.bot.get_emoji(collectible.emoji_id)

            if emoji:
                emote = str(emoji)
            else:
                emote = "N/A"
            #if you want the Rarity to only show full numbers like 1 or 12 use the code part here:
            # rarity = int(collectible.rarity)
            # otherwise you want to display numbers like 1.5, 5.3, 76.9 use the normal part.
            rarity = collectible.rarity

            entry = (name, f"{emote} Rarity: {rarity}")
            entries.append(entry)
        # This is the number of countryballs who are displayed at one page, 
        # you can change this, but keep in mind: discord has an embed size limit.
        per_page = 5 

        source = FieldPageSource(entries, per_page=per_page, inline=False, clear_description=False)
        source.embed.description = (
            f"__**{settings.bot_name} rarity**__"
        )
        source.embed.colour = discord.Colour.blurple()
        source.embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60, key=lambda i: i.user.id)
    async def events_rarity(self, interaction: discord.Interaction):
        # DO NOT CHANGE THE CREDITS TO THE AUTHOR HERE!
        """
        Show the rarity list of the dex - Made by GamingadlerHD
        """
        # Filter enabled collectibles
        events = [x for x in specials.values()]

        if not events:
            await interaction.response.send_message(
                f"There are no events registered in {settings.bot_name} yet.",
                ephemeral=True,
            )
            return

        # Sort collectibles by rarity in ascending order
        

        entries = []

        for special in events:
            name = f"{special.name}"
            emoji = special.emoji

            if emoji:
                emote = str(emoji)
            else:
                emote = "N/A"
            
            filters = {} 
            filters["special"] = special

            count = await BallInstance.filter(**filters)
            countNum = len(count)
            #sorted_collectibles = sorted(enabled_collectibles.values(), key=lambda x: x.rarity)
            #if you want the Rarity to only show full numbers like 1 or 12 use the code part here:
            # rarity = int(collectible.rarity)
            # otherwise you want to display numbers like 1.5, 5.3, 76.9 use the normal part.
            

            entry = (name, f"{emote} Count: {countNum}")
            entries.append(entry)
        # This is the number of countryballs who are displayed at one page, 
        # you can change this, but keep in mind: discord has an embed size limit.
        per_page = 5 

        source = FieldPageSource(entries, per_page=per_page, inline=False, clear_description=False)
        source.embed.description = (
            f"__**{settings.bot_name} events rarity**__"
        )
        source.embed.colour = discord.Colour.blurple()
        source.embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )

        pages = Pages(source=source, interaction=interaction, compact=True)
        await pages.start()
