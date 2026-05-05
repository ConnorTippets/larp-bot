import discord
import json
import random
import inspect
from discord.ext.commands import Bot, Context, is_owner
from discord import ui
import aiosqlite


class Consent(ui.Modal, title="Consent"):
    sex = ui.Label(
        text="Sex",
        component=ui.RadioGroup(
            options=[
                discord.RadioGroupOption(label="Male"),
                discord.RadioGroupOption(label="Female"),
            ]
        ),
    )
    consenting_with = ui.Label(
        text="You consent to",
        component=ui.CheckboxGroup(
            options=[
                discord.CheckboxGroupOption(label="Male"),
                discord.CheckboxGroupOption(label="Female"),
            ]
        ),
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not bot.db:
            await interaction.response.send_message(
                "Database connection failed!", ephemeral=True
            )
            return

        consenting = (
            self.consenting_with.component.values  # pyright: ignore[reportAttributeAccessIssue]
        )
        await bot.db.execute(
            "INSERT OR REPLACE INTO consent VALUES (?, ?, ?, ?)",
            (
                interaction.user.id,
                self.sex.component.value  # pyright: ignore[reportAttributeAccessIssue]
                == "Female",
                "Male" in consenting,
                "Female" in consenting,
            ),
        )
        await bot.db.commit()
        await interaction.response.send_message(
            f"Consent settings updated!",
            ephemeral=True,
        )


class MyBot(Bot):
    def __init__(self):
        super().__init__(
            command_prefix=";",
            intents=discord.Intents.default()
            | discord.Intents._from_value(discord.Intents.message_content.flag),
            owner_ids=(376129806313455616,),
        )
        self.db = None

    async def setup_hook(self):
        print(await bot.tree.sync())

        self.db = await aiosqlite.connect("database.db")
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS consent (
                user INTEGER UNIQUE,
                sex BOOLEAN,
                consent_male BOOLEAN,
                consent_female BOOLEAN
            );
        """)


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
@bot.tree.command(name="consent", description="Change your consent configuration.")
async def consent(interaction: discord.Interaction):
    await interaction.response.send_modal(Consent())


@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name="test", description="test")
async def test(interaction: discord.Interaction):
    if not bot.db:
        return await interaction.response.send_message(
            "Database connection failed!", ephemeral=True
        )

    cursor = await bot.db.execute("SELECT * FROM consent")
    await interaction.response.send_message(await cursor.fetchall())


@bot.command(name="sync", description="Sync commands.")
@is_owner()
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

    yourself = action["yourself"]
    if not isinstance(yourself, str):
        raise KeyError("you suck ass")

    exec(
        f"""@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name=name, description=description)
async def {name}"""
        + r"""(
    interaction: discord.Interaction, user: discord.User | discord.Member
):
    if interaction.user.id == user.id:
        await interaction.response.send_message(
            yourself.replace(
                r"${0}", interaction.user.mention
            )
        )
    await interaction.response.send_message(
        random.choice(responses)
        .replace(r"${0}", interaction.user.mention)
        .replace(r"${1}", user.mention)
    )""",
        {**locals(), **globals()},
    )


token = ""
with open("token.txt", "r") as handle:
    token = handle.read().strip()

bot.run(token)
