import logging
import random
import sys
from typing import TYPE_CHECKING, Dict
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands

from PIL import Image

import asyncio
import io
import re
import os
import copy

from ballsdex.core.models import Ball
from ballsdex.core.models import BallInstance
from ballsdex.core.models import balls as countryballs
from ballsdex.settings import settings

from ballsdex.core.utils.transformers import BallInstanceTransform
from ballsdex.packages.battle.xe_battle_lib import (
    BattleBall,
    BattleInstance,
    gen_battle,
)

from ballsdex.core.image_generator.image_gen import draw_card

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot
log = logging.getLogger("ballsdex.packages.merge")

def gen_name(name1, name2):
    if len(name1) > len(name2):
        oldn = name2
        name2 = name1
        name1 = oldn
    if " " in name1:
        prefix = name1.split()[0]
        suffix = name2
        return prefix + " " + suffix
    else:
        return name1 + name2[len(name1):]

def gen_text(source, state_size, min_length):
    # build markov chain
    source = source.split()
    model = {}
    for i in range(state_size, len(source)):
        current_word = source[i]
        previous_words = ' '.join(source[i-state_size:i])
        if previous_words in model:
            model[previous_words].append(current_word)
        else:
            model[previous_words] = [current_word]

    # generate text
    text = random.choice([s.split(' ') for s in model.keys() if s[0].isupper()])

    i = state_size
    while True:
        key = ' '.join(text[i-state_size:i])
        if key not in model:
            text += random.choice([s.split(' ') for s in model.keys() if s[0].isupper()])
            i += 1
            continue

        next_word = random.choice(model[key])
        text.append(next_word)
        i += 1
        if i > min_length and text[-1][-1] in ['.', '!']:
            break

    return ' '.join(text)

# this is a really bad solution for something I cant figure out
@dataclass
class FakeBall:
    short_name: str
    capacity_name: str
    capacity_description: str
    collection_card: str
    credits: str

    cached_regime: ...
    cached_economy: ...
    
@dataclass
class FakeBallInstance:
    shiny: bool
    special_card: ...

    health: int
    attack: int
    
    countryball: FakeBall

class Merge(commands.Cog):
    """
    Merge multiple countryballs!
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command()
    async def merge(self, interaction: discord.Interaction, ball1: BallInstanceTransform, ball2: BallInstanceTransform):
        """
        Merge two countryballs together.
        """

        await interaction.response.defer()

        name = gen_name(ball1.countryball.short_name, ball2.countryball.short_name)
        health = (ball1.countryball.health + ball2.countryball.health) // 2
        attack = (ball1.countryball.attack + ball2.countryball.attack) // 2
        economy = ball1.countryball.economy
        ability = gen_text(ball1.countryball.capacity_name + '. ' + ball2.countryball.capacity_name, 1, 3)
        desc = gen_text(ball1.countryball.capacity_description + '. ' + ball2.countryball.capacity_description, 1, 7)

        collection1 = Image.open(os.getcwd() + ball1.countryball.collection_card).resize((1366, 768))
        collection2 = Image.open(os.getcwd() + ball2.countryball.collection_card).resize((1366, 768))

        left = collection1.crop((0, 0, 683, 768))
        right = collection2.crop((683, 0, 1366, 768))

        collection = Image.new('RGB', (1366, 768))
        collection.paste(left, (0,0))
        collection.paste(right, (683, 0))
        
        collection.save(os.getcwd() + ball1.countryball.collection_card + '-merge.png')
        ball_instance = FakeBallInstance(
            shiny=ball1.shiny or ball2.shiny,
            special_card=ball1.special_card if ball1.special_card else ball2.special_card,

            health=health,
            attack=attack,

            countryball=FakeBall(
                short_name=name,
                capacity_name=ability,
                capacity_description=desc,
                credits=ball1.countryball.credits + ', ' + ball2.countryball.credits,
                
                collection_card=ball1.countryball.collection_card + '-merge.png',
                
                cached_regime=ball1.countryball.cached_regime,
                cached_economy=ball2.countryball.cached_economy,
            )
        )
        
        image = draw_card(ball_instance)
        buffer = io.BytesIO()
        image.save(buffer, format="png")
        buffer.seek(0)
        image.close()

        os.remove(os.getcwd() + ball1.countryball.collection_card + '-merge.png')

        await interaction.followup.send(
            file=discord.File(
                buffer,
                filename='card.png'
            )
        )
        
