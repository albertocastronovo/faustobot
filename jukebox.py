from discord.ext import commands as dc
from discord import ui
from discord import Interaction, ButtonStyle
import yt_dlp as youtube_dl
from discord import FFmpegPCMAudio, FFmpegAudio, FFmpegOpusAudio
from re import match


class Jukebox(dc.Cog):
    def __init__(self, bot: dc.Bot):
        self.__bot: dc.Bot = bot
        self.__is_playing: bool = False
        self.__paused: bool = True
        self.__voice_client = None
        self.__past_queue = []
        self.__queue = []
        self.__view = JukeboxView(self)

    def __toggle_playing(self):
        self.__is_playing = not self.__is_playing

    def paused(self):
        return self.__paused

    def playing(self):
        return self.__is_playing

    @dc.command(pass_context=True, name="join")
    async def join_voice_channel(self, context):
        try:
            channel = context.author.voice.channel
        except AttributeError:
            await context.send("You are not in a voice channel!")
            return
        if context.voice_client is not None:
            await context.voice_client.move_to(channel)
        else:
            await channel.connect()
            self.__voice_client = context.voice_client

    @dc.command(pass_context=True, name="leave")
    async def leave_voice_channel(self, context):
        if context.voice_client is not None:
            await context.voice_client.disconnect()
            self.__voice_client = None

    @dc.command(pass_context=False, name="play")
    async def play_first_from_queue(self):
        if len(self.__queue) == 0:  # no songs to be played
            return
        self.__voice_client.play(
            FFmpegOpusAudio(
                executable="C:/ffmpeg/bin/ffmpeg.exe",
                source=self.__queue[0]["ffmpeg_url"],
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            ),
            after=lambda l: self.__toggle_playing()
        )
        self.__is_playing = True
        self.__paused = False
        self.__past_queue.append(self.__queue[0])
        if len(self.__past_queue) > 10:
            del self.__past_queue[0]
        del self.__queue[0]

    @dc.command(pass_context=False, name="previous")
    async def replay_previous_song(self):
        if len(self.__past_queue) == 0:
            return
        self.__queue.insert(0, self.__past_queue[-1])
        del self.__past_queue[-1]
        await self.stop()
        await self.play_first_from_queue()

    @dc.command(pass_context=False, name="next")
    async def play_next_in_queue(self):
        if len(self.__queue) == 0:
            return
        await self.stop()
        await self.play_first_from_queue()

    @staticmethod
    def __get_ffmpeg_url(file_info: list[dict], quality: str = "medium", filetype: str = "webm"):
        all_audio = {f.get("format_note"): f.get("url")
                     for f in file_info
                     if f.get("format_note") in ["low", "medium", "high"] and f.get("ext") == filetype
                     }
        if quality in all_audio:
            return all_audio[quality]
        else:
            while True:
                if quality == "high":
                    quality = "medium"
                elif quality == "medium":
                    quality = "low"
                else:
                    return None
                if quality in all_audio:
                    return all_audio[quality]

    @staticmethod
    def is_valid_link(link: str):
        return match(r"http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?", link) is not None

    @dc.command(pass_context=False, name="pause")
    async def pause(self):
        if self.__voice_client is not None and self.__is_playing and not self.__paused:
            self.__voice_client.pause()
            self.__paused = True

    @dc.command(pass_context=False, name="resume")
    async def resume(self):
        if self.__voice_client is not None and self.__is_playing and self.__paused:
            self.__voice_client.resume()
            self.__paused = False

    @dc.command(pass_context=False, name="stop")
    async def stop(self):
        if self.__voice_client is not None and self.__is_playing:
            self.__voice_client.stop()
            self.__is_playing = False
            self.__paused = True

    @dc.command(pass_context=True, name="jukebox")
    async def jukebox(self, context):
        await context.send(view=self.__view)

    @dc.command(pass_context=True, name="add")
    async def add_to_queue(self, context, *args):
        await self.join_voice_channel(context)

        if len(args) == 1:
            link = str(args[0])
            if not self.is_valid_link(link):
                await context.send("Invalid YouTube link!")
                return

            with youtube_dl.YoutubeDL() as ydl:
                audio_info = ydl.extract_info(link, download=False)
            self.__queue.append(
                {
                    "channel": context.author.voice.channel,
                    "url": link,
                    "ffmpeg_url": self.__get_ffmpeg_url(audio_info["formats"], quality="high"),
                    "title": audio_info["title"]
                }
            )

        else:
            with youtube_dl.YoutubeDL() as ydl:
                audio_info_list = ydl.extract_info(f"ytsearch:{' '.join(args)}", download=False)
                audio_info = audio_info_list["entries"][0]
            self.__queue.append(
                {
                    "channel": context.author.voice.channel,
                    "url": audio_info["webpage_url"],
                    "ffmpeg_url": self.__get_ffmpeg_url(audio_info["formats"], quality="high"),
                    "title": audio_info["title"]
                }
            )
        if not self.__is_playing:
            await self.play_first_from_queue()


async def setup(bot: dc.Bot):
    await bot.add_cog(Jukebox(bot))


class JukeboxView(ui.View):
    def __init__(self, jukebox: Jukebox | None = None):
        super().__init__(timeout=None)
        self.__jukebox = jukebox

    @ui.button(label="⏹️", style=ButtonStyle.blurple, custom_id="stop", row=0)
    async def stop_button(self, interaction: Interaction, button: ui.Button):
        await self.__jukebox.stop()

    @ui.button(label="▶️", style=ButtonStyle.blurple, custom_id="play", row=0)
    async def play_button(self, interaction: Interaction, button: ui.Button):
        if self.__jukebox.playing():    # if a song is already playing, resume it
            await self.__jukebox.resume()
        else:                           # if not, then start playing the first one
            await self.__jukebox.play_first_from_queue()

    @ui.button(label="⏸️", style=ButtonStyle.blurple, custom_id="pause", row=0)
    async def pause_button(self, interaction: Interaction, button: ui.Button):
        if self.__jukebox.paused():     # if a song is paused, then resume it
            await self.__jukebox.resume()
        else:                           # if not, then pause it
            await self.__jukebox.pause()


