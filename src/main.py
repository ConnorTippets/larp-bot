import discord
import json
import random
import inspect
from discord.ext.commands import Bot, Context


class MyBot(Bot):
    def __init__(self):
        super().__init__(
            command_prefix=";",
            intents=discord.Intents.default()
            | discord.Intents._from_value(discord.Intents.message_content.flag),
        )

    async def setup_hook(self):
        print(await bot.tree.sync())


bot = MyBot()


@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="smack", description="Smack someone across the face!")
async def smack(interaction: discord.Interaction, user: discord.User | discord.Member):
    if user.name == "kiiatto":
        await interaction.response.send_message(
            f"{interaction.user.mention} just smacked {user.mention} for overusing Goober Bot!"
        )
    elif user.name == interaction.user.name:
        await interaction.response.send_message(
            f"{interaction.user.mention} just smacked... themself?"
        )
    else:
        await interaction.response.send_message(
            f"{interaction.user.mention} just smacked {user.mention}!"
        )


@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="test", description="test")
async def test(interaction: discord.Interaction):
    frame = inspect.currentframe()

    stack = ""
    while frame:
        stack += (
            frame.f_code.co_filename
            + ": "
            + frame.f_code.co_name
            + str(frame.f_lineno)
            + "\n"
        )
        frame = frame.f_back

    await interaction.response.send_message(stack[:-1])


@bot.command(name="sync", description="Sync commands.")
async def sync(interaction: Context):
    await bot.tree.sync(guild=interaction.guild)
    await bot.tree.sync()


commands: dict[str, dict[str, str | list[str]]] = {}
with open("src/actions.json", "r") as handle:
    commands = json.load(handle)

for name, action in commands.items():
    print(name, action)
    description = action["description"]
    if not isinstance(description, str):
        raise KeyError("Fix ts")

    responses = action["responses"]
    if not isinstance(responses, list):
        raise KeyError("Fix ts2")

    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @bot.tree.command(name=name, description=description)
    async def com(
        interaction: discord.Interaction, user: discord.User | discord.Member
    ):
        await interaction.response.send_message(
            random.choice(responses)
            .replace(r"${0}", interaction.user.mention)
            .replace(r"${1}", user.mention)
        )


token = ""
with open("token.txt", "r") as handle:
    token = handle.read().strip()

bot.run(token)
