import random
import traceback

import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import time
import textwrap
from PIL import Image, ImageDraw, ImageFont
import requests
import embeds
import aiohttp
import httpx

ryderize_running = False


class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Resets ryderize if broken", hidden=True)
    async def re(self, ctx):
        global ryderize_running
        ryderize_running = False



    @app_commands.command(name='ryderize', description='adds a photo of ryder/ pointing to an image')
    async def ryderize(self, interaction, image: discord.Attachment, scale: float = 1.0):
        async with httpx.AsyncClient() as c:
            r = await c.post(
                "https://api.okemovail.com/v1/chat/completions",
                headers={"Authorization": "Bearer sk-none", "Content-Type": "application/json"},
                json={"model": "octan", "messages": [{"role": "user", "content": "test"}]},
            )
            await interaction.response.send_message(r.status_code)
            print(r.status_code, r.text[:300])

    @commands.command(name='inspire', description='be inspired')
    async def inspire(self, ctx):
        msg = await ctx.reply('waiting...', mention_author=False)
        try:
            out = requests.get(url="https://inspirobot.me/api?generate=true")
            link = out.text
            await msg.edit(content=link)
        except:
            await msg.edit(content=f"```{traceback.format_exc()}```")

    @app_commands.command(name='inspire', description='gets a quote using inspirobot')
    async def inspirecmd(self, ctx):
        try:
            out = requests.get(url="https://inspirobot.me/api?generate=true")
            link = out.text
            await ctx.response.send_message(link)
        except:
            await ctx.response.send_message(content=f"```{traceback.format_exc()}```")



async def setup(bot):
    await bot.add_cog(Images(bot))
