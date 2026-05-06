import discord
import json
import random
import inspect
from discord.ext.commands import Bot, Context, is_owner
from discord import ui
import aiosqlite


async def check_dms(
    interaction: discord.Interaction, user: discord.User | discord.Member
) -> bool:
    if not bot.db:
        await interaction.response.send_message(
            "Database connection failed!", ephemeral=True
        )
        return False

    cursor = await bot.db.execute(
        "SELECT nsfw_in_dms FROM consent WHERE user = ?", (interaction.user.id,)
    )
    consent_author_row = await cursor.fetchone()

    if not consent_author_row:
        await interaction.response.send_message(
            "You have not consented to dms yet!", ephemeral=True
        )
        return False

    consent_author: int = consent_author_row[0]

    if not consent_author:
        await interaction.response.send_message(
            "You do not consent to dms!", ephemeral=True
        )
        return False

    cursor = await bot.db.execute(
        "SELECT nsfw_in_dms FROM consent WHERE user = ?", (user.id,)
    )
    consent_receiver_row = await cursor.fetchone()

    if not consent_receiver_row:
        await interaction.response.send_message(
            f"`{user.name}` has not consented to dms yet!", ephemeral=True
        )
        return False

    consent_receiver: int = consent_receiver_row[0]

    if not consent_receiver:
        await interaction.response.send_message(
            f"`{user.name}` does not consent to dms!", ephemeral=True
        )
        return False

    return True


async def check_consent(
    interaction: discord.Interaction, user: discord.User | discord.Member
) -> bool:
    if not bot.db:
        await interaction.response.send_message(
            "Database connection failed!", ephemeral=True
        )
        return False

    cursor = await bot.db.execute(
        "SELECT sex, consent_male, consent_female FROM consent WHERE user = ?",
        (interaction.user.id,),
    )
    consent_author_row = await cursor.fetchone()

    if not consent_author_row:
        await interaction.response.send_message(
            "You have not configured consent!", ephemeral=True
        )
        return False

    author_sex, author_allow_male, author_allow_female = consent_author_row

    cursor = await bot.db.execute(
        "SELECT sex, consent_male, consent_female FROM consent WHERE user = ?",
        (user.id,),
    )
    consent_user_row = await cursor.fetchone()

    if not consent_user_row:
        await interaction.response.send_message(
            f"`{user.name}` has not configured consent!", ephemeral=True
        )
        return False

    user_sex, user_allow_male, user_allow_female = consent_user_row

    if (not user_sex and not author_allow_male) or (
        user_sex and not author_allow_female
    ):
        await interaction.response.send_message(
            f"You do not consent to {"females" if user_sex else "males"}!",
            ephemeral=True,
        )
        return False

    if (not author_sex and not user_allow_male) or (
        author_sex and not user_allow_female
    ):
        await interaction.response.send_message(
            f"`{user.name}` does not consent to {"females" if author_sex else "males"}!",
            ephemeral=True,
        )
        return False

    return True


async def get_sex(user: discord.User | discord.Member) -> bool | None:
    if not bot.db:
        # if we're calling this function, the bot almost certainly has a database connection
        return

    cursor = await bot.db.execute(
        "SELECT sex FROM consent WHERE user = ?",
        (user.id,),
    )
    user_row = await cursor.fetchone()

    if not user_row:
        # both users should have a row by now
        return

    user_sex: int = user_row[0]

    return bool(user_sex)


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
    nsfw_in_dms = ui.Label(text="Allow NSFW in dms?", component=ui.Checkbox())

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
            "INSERT OR REPLACE INTO consent VALUES (?, ?, ?, ?, ?)",
            (
                interaction.user.id,
                self.sex.component.value  # pyright: ignore[reportAttributeAccessIssue]
                == "Female",
                "Male" in consenting,
                "Female" in consenting,
                self.nsfw_in_dms.component.value,  # pyright: ignore[reportAttributeAccessIssue]
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
                consent_female BOOLEAN,
                nsfw_in_dms BOOLEAN
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


@bot.command(description="Sync commands.")
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

    yourself = action["yourself"]
    if not isinstance(yourself, str):
        raise KeyError("you suck ass")

    type = action["type"]
    if not isinstance(type, str):
        raise KeyError("bich")

    match type:
        case "nonnsfw":
            responses = action["responses"]
            if not isinstance(responses, list):
                raise KeyError("Fix ts2")

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
        return
        
    await interaction.response.send_message(
        random.choice(responses)
        .replace(r"${0}", interaction.user.mention)
        .replace(r"${1}", user.mention)
    )""",
                {**locals(), **globals()},
            )
        case "anynsfw":
            mmresponses = action["mmresponses"]
            if not isinstance(mmresponses, list):
                raise KeyError("Fix ts23")

            mfresponses = action["mfresponses"]
            if not isinstance(mfresponses, list):
                raise KeyError("Fix ts25")

            fmresponses = action["fmresponses"]
            if not isinstance(fmresponses, list):
                raise KeyError("Fix ts22")

            ffresponses = action["ffresponses"]
            if not isinstance(ffresponses, list):
                raise KeyError("Fix ts28")
            exec(
                f"""@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@bot.tree.command(name=name, description=description, nsfw=True)
async def {name}"""
                + r"""(
    interaction: discord.Interaction, user: discord.User | discord.Member
):
    if not interaction.guild and not await check_dms(interaction, user):
        return 
    
    if not await check_consent(interaction, user):
        return

    if interaction.user.id == user.id:
        await interaction.response.send_message(
            yourself.replace(
                r"${0}", interaction.user.mention
            )
        )
        return
        
    author_sex = await get_sex(interaction.user)
    user_sex = await get_sex(user)
    
    responses: list = []
    if not (author_sex or user_sex):  # both are male
        responses = mmresponses
    elif not author_sex and user_sex:
        responses = mfresponses
    elif author_sex and not user_sex:  # symmetric but useful!
        responses = fmresponses
    else:  # only other possibility is both being female
        responses = ffresponses
    
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
