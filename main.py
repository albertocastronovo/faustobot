from discord.ext import commands as dc
from discord import Intents
from discord_classes import PersistentMusicBot
from jukebox import Jukebox

with open("token.txt", "r") as f:
    app_token = f.readline()

bot = PersistentMusicBot()


@bot.event
async def on_ready():
    print("Bot ready.")


bot.run(token=app_token)
