import traceback
import datetime
import discord
from discord.ext import commands, tasks
import feedparser

prev_xml = None
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class YT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.fetch_xml.start()

    @tasks.loop(seconds=60)
    async def fetch_xml(self):
        try:
            d = feedparser.parse("https://www.youtube.com/feeds/videos.xml?channel_id=UCxgkDK11DnpzXhCXe7n7mjw")

            if not d.entries:
                return

            latest = d.entries[0]

            global prev_xml
            if prev_xml is None:
                prev_xml = d.entries[0]
                return
            if latest.link != prev_xml.link:
                latest = d.entries[0]
                title = latest.title
                link = latest.link
                author = latest.author
                thumbnail = latest.media_thumbnail[0]['url']
                embed = discord.Embed(title=title, url=link, color=discord.Color.red())
                embed.set_image(url=thumbnail)
                embed.set_author(name=f"New Upload | {author}")
                embed.timestamp = datetime.datetime.now()
                channel = self.bot.get_channel(1187616334339645440)
                await channel.send(embed=embed)
                prev_xml = latest


        except Exception as e:
            traceback.print_exc()


async def setup(bot):
    await bot.add_cog(YT(bot), guilds=[discord.Object(id=1226051359066030111), discord.Object(1187525934400671814)])
