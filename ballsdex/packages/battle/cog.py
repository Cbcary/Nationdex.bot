import logging
import random
import sys
from typing import TYPE_CHECKING, Dict
from dataclasses import dataclass, field

import discord
from discord import app_commands
from discord.ext import commands

import asyncio
import io

from ballsdex.core.models import Ball
from ballsdex.core.models import balls as countryballs
from ballsdex.settings import settings

from ballsdex.core.utils.transformers import BallInstanceTransform
from ballsdex.packages.battle.xe_battle_lib import (
    BattleBall,
    BattleInstance,
    gen_battle,
)

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot
log = logging.getLogger("ballsdex.packages.battle")


@dataclass
class GuildBattle:
    author: discord.Member
    opponent: discord.Member
    author_ready: bool = False
    opponent_ready: bool = False
    battle: BattleInstance = field(default_factory=BattleInstance)


def gen_deck(balls) -> str:
    """Generates a text representation of the player's deck."""
    if not balls:
        return "Empty"
    return "\n".join(
        [
            f"- {ball.emoji} {ball.name} (HP: {ball.health} | DMG: {ball.attack})"
            for ball in balls
        ]
    )


def update_embed(
    author_balls, opponent_balls, author, opponent, author_ready, opponent_ready
) -> discord.Embed:
    """Creates an embed for the battle setup phase."""
    embed = discord.Embed(
        title="Countryballs Battle Plan",
        description="Add or remove countryballs you want to propose to the other player using the '/battle add' and '/battle remove' commands. Once you've finished, click the tick button to start the battle.",
        color=discord.Colour.blurple(),
    )

    author_emoji = ":white_check_mark:" if author_ready else ""
    opponent_emoji = ":white_check_mark:" if opponent_ready else ""

    embed.add_field(
        name=f"{author_emoji} {author}'s deck:",
        value=gen_deck(author_balls),
        inline=True,
    )
    embed.add_field(
        name=f"{opponent_emoji} {opponent}'s deck:",
        value=gen_deck(opponent_balls),
        inline=True,
    )
    return embed


def create_disabled_buttons() -> discord.ui.View:
    """Creates a view with disabled start and cancel buttons."""
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.success, emoji="✔", label="Ready", disabled=True
        )
    )
    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.danger, emoji="✖", label="Cancel", disabled=True
        )
    )


class Battle(commands.GroupCog):
    """
    Battle your countryballs! - Made by xen64
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.battles: Dict[int, GuildBattle] = {}
        self.interactions: Dict[int, discord.Interaction] = {}

    async def start_battle(self, interaction: discord.Interaction):
        guild_battle = self.battles.get(interaction.guild_id)
        if not guild_battle or interaction.user not in (
            guild_battle.author,
            guild_battle.opponent,
        ):
            await interaction.response.send_message(
                "You aren't a part of this battle.", ephemeral=True
            )
            return
        # Set the player's readiness status

        if interaction.user == guild_battle.author:
            guild_battle.author_ready = True
        elif interaction.user == guild_battle.opponent:
            guild_battle.opponent_ready = True
        # If both players are ready, start the battle

        if guild_battle.author_ready and guild_battle.opponent_ready:
            if not (guild_battle.battle.p1_balls and guild_battle.battle.p2_balls):
                await interaction.response.send_message(
                    "Both players must add countryballs!"
                )
                return
            new_view = create_disabled_buttons()
            battle_log = "\n".join(gen_battle(guild_battle.battle))

            embed = discord.Embed(
                title="Countryballs Battle Plan",
                description=f"Battle between {guild_battle.author.mention} and {guild_battle.opponent.mention}",
                color=discord.Color.green(),
            )
            embed.add_field(
                name=f"{guild_battle.author}'s deck:",
                value=gen_deck(guild_battle.battle.p1_balls),
                inline=True,
            )
            embed.add_field(
                name=f"{guild_battle.opponent}'s deck:",
                value=gen_deck(guild_battle.battle.p2_balls),
                inline=True,
            )
            embed.add_field(
                name="Winner:",
                value=f"{guild_battle.battle.winner} - Turn: {guild_battle.battle.turns}",
                inline=False,
            )
            embed.set_footer(text="Battle log is attached.")

            await interaction.response.defer()
            await interaction.message.edit(
                content=f"{guild_battle.author.mention} vs {guild_battle.opponent.mention}",
                embed=embed,
                view=new_view,
                attachments=[
                    discord.File(io.StringIO(battle_log), filename="battle-log.txt")
                ],
            )
            self.battles[interaction.guild_id] = None
        else:
            # One player is ready, waiting for the other player

            await interaction.response.send_message(
                f"Done! Waiting for the other player to press 'Ready'.", ephemeral=True
            )

            author_emoji = (
                ":white_check_mark:" if interaction.user == guild_battle.author else ""
            )
            opponent_emoji = (
                ":white_check_mark:"
                if interaction.user == guild_battle.opponent
                else ""
            )

            embed = discord.Embed(
                title="Countryballs Battle Plan",
                description="Add or remove countryballs you want to propose to the other player using the '/battle add' and '/battle remove' commands. Once you've finished, click the tick button to start the battle.",
                color=discord.Colour.blurple(),
            )

            embed.add_field(
                name=f"{author_emoji} {guild_battle.author.name}'s deck:",
                value=gen_deck(guild_battle.battle.p1_balls),
                inline=True,
            )
            embed.add_field(
                name=f"{opponent_emoji} {guild_battle.opponent.name}'s deck:",
                value=gen_deck(guild_battle.battle.p2_balls),
                inline=True,
            )

            await self.interactions[interaction.guild_id].edit_original_response(
                embed=embed
            )

    async def cancel_battle(self, interaction: discord.Interaction):
        guild_battle = self.battles.get(interaction.guild_id)

        if not guild_battle:
            return

        if interaction.user not in (guild_battle.author, guild_battle.opponent):
            await interaction.response.send_message(
                "You aren't a part of this battle!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Countryballs Battle Plan",
            description="The battle has been cancelled.",
            color=discord.Color.red(),
        )
        embed.add_field(
            name=f"{guild_battle.author}'s deck:",
            value=gen_deck(guild_battle.battle.p1_balls),
            inline=True,
        )
        embed.add_field(
            name=f"{guild_battle.opponent}'s deck:",
            value=gen_deck(guild_battle.battle.p2_balls),
            inline=True,
        )

        try:
            await interaction.response.defer()
        except discord.errors.InteractionResponded:
            pass
        await interaction.message.edit(embed=embed, view=create_disabled_buttons())
        self.battles[interaction.guild_id] = None

    @app_commands.command()
    async def start(self, interaction: discord.Interaction, opponent: discord.Member):
        """
        Start a battle with a chosen user. - Made by xen64
        """
        if self.battles.get(interaction.guild_id):
            await interaction.response.send_message(
                "You cannot create a new battle right now, as one is already ongoing in this server.",
                ephemeral=True,
            )
            return
        self.battles[interaction.guild_id] = GuildBattle(
            author=interaction.user, opponent=opponent
        )
        embed = update_embed([], [], interaction.user.name, opponent.name, False, False)

        start_button = discord.ui.Button(
            style=discord.ButtonStyle.success, emoji="✔", label="Ready"
        )
        cancel_button = discord.ui.Button(
            style=discord.ButtonStyle.danger, emoji="✖", label="Cancel"
        )

        # Set callbacks

        start_button.callback = self.start_battle
        cancel_button.callback = self.cancel_battle

        view = discord.ui.View(timeout=None)
        view.add_item(start_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(
            f"Hey, {opponent.mention}, {interaction.user.name} is proposing a battle with you!",
            embed=embed,
            view=view,
        )

        self.interactions[interaction.guild_id] = interaction

    @app_commands.command()
    async def add(
        self, interaction: discord.Interaction, countryball: BallInstanceTransform
    ):
        """
        Add a countryball to a battle. - Made by xen64
        """
        guild_battle = self.battles.get(interaction.guild_id)
        if not guild_battle:
            await interaction.response.send_message(
                "There is no ongoing battle in this server!", ephemeral=True
            )
            return
        # Check if the user is already ready

        if (interaction.user == guild_battle.author and guild_battle.author_ready) or (
            interaction.user == guild_battle.opponent and guild_battle.opponent_ready
        ):
            await interaction.response.send_message(
                "You cannot change your balls as you are already ready.", ephemeral=True
            )
            return
        # Check if user is one of the participants

        if interaction.user not in (guild_battle.author, guild_battle.opponent):
            await interaction.response.send_message(
                "You aren't a part of this battle!", ephemeral=True
            )
            return
        # Determine if the user is the author or opponent and get the appropriate ball list

        user_balls = (
            guild_battle.battle.p1_balls
            if interaction.user == guild_battle.author
            else guild_battle.battle.p2_balls
        )
        # Create the BattleBall instance

        ball = BattleBall(
            countryball.countryball.country,
            interaction.user.name,
            countryball.health,
            countryball.attack,
            self.bot.get_emoji(countryball.countryball.emoji_id),
        )

        # Check if ball has already been added

        if ball in user_balls:
            await interaction.response.send_message(
                "You cannot add the same ball twice!", ephemeral=True
            )
            return
        user_balls.append(ball)

        # Construct the message

        attack_sign = "+" if countryball.attack_bonus >= 0 else ""
        health_sign = "+" if countryball.health_bonus >= 0 else ""

        await interaction.response.send_message(
            f"Added `#{countryball.id} {countryball.countryball.country} ({attack_sign}{countryball.attack_bonus}%/{health_sign}{countryball.health_bonus}%)`!",
            ephemeral=True,
        )

        # Update the battle embed for both players

        await self.interactions[interaction.guild_id].edit_original_response(
            embed=update_embed(
                guild_battle.battle.p1_balls,
                guild_battle.battle.p2_balls,
                guild_battle.author.name,
                guild_battle.opponent.name,
                guild_battle.author_ready,
                guild_battle.opponent_ready,
            )
        )

    @app_commands.command()
    async def remove(
        self, interaction: discord.Interaction, countryball: BallInstanceTransform
    ):
        """
        Remove a countryball from battle. - Made by xen64
        """
        guild_battle = self.battles.get(interaction.guild_id)
        if not guild_battle:
            await interaction.response.send_message(
                "There is no ongoing battle in this server!", ephemeral=True
            )
            return
        # Check if the user is already ready

        if (interaction.user == guild_battle.author and guild_battle.author_ready) or (
            interaction.user == guild_battle.opponent and guild_battle.opponent_ready
        ):
            await interaction.response.send_message(
                "You cannot change your balls as you are already ready.", ephemeral=True
            )
            return
        # Check if user is one of the participants

        if interaction.user not in (guild_battle.author, guild_battle.opponent):
            await interaction.response.send_message(
                "You aren't a part of this battle!", ephemeral=True
            )
            return
        # Determine if the user is the author or opponent and get the appropriate ball list

        user_balls = (
            guild_battle.battle.p1_balls
            if interaction.user == guild_battle.author
            else guild_battle.battle.p2_balls
        )

        # Create the BattleBall instance for comparison

        ball_to_remove = BattleBall(
            countryball.countryball.country,
            interaction.user.name,
            countryball.health,
            countryball.attack,
            self.bot.get_emoji(countryball.countryball.emoji_id),
        )

        if ball_to_remove in user_balls:
            user_balls.remove(ball_to_remove)

            # Construct the message

            attack_sign = "+" if countryball.attack_bonus >= 0 else ""
            health_sign = "+" if countryball.health_bonus >= 0 else ""

            await interaction.response.send_message(
                f"Removed `#{countryball.id} {countryball.countryball.country} ({attack_sign}{countryball.attack_bonus}%/{health_sign}{countryball.health_bonus}%)`!",
                ephemeral=True,
            )

            # Update the battle embed for both players

            await self.interactions[interaction.guild_id].edit_original_response(
                embed=update_embed(
                    guild_battle.battle.p1_balls,
                    guild_battle.battle.p2_balls,
                    guild_battle.author.name,
                    guild_battle.opponent.name,
                    guild_battle.author_ready,
                    guild_battle.opponent_ready,
                )
            )
        else:
            await interaction.response.send_message(
                f"That countryball is not in your battle deck!", ephemeral=True
            )
