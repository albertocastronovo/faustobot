from discord.ext import commands as dc
from discord import Intents
from discord import ButtonStyle, ui, Interaction
from jukebox import JukeboxView


class PersistentMusicBot(dc.Bot):
    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=dc.when_mentioned_or("f!"), intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        self.add_view(JukeboxView())
        await self.load_extension("jukebox")
