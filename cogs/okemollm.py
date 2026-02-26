import discord
from discord import app_commands
from discord.ext import commands
import os
import platform
import subprocess
import sys
import asyncio
import re
import secrets

from gradio_client import Client
client = Client("https://polarisapi.okemovail.com/gradio/gradio_api/run/predict/")

olm_is = ["is thinking", "is cooking up a response", "wants you to order a Shamrock Shake® from McDonalds for only $5.19", "is crunching data", "thinks you're dumb", "thinks 1+1 equals 4", "is making JavaScript 2", "is not real", "is <UNK><UNK><UNK><UNK><UNK>", "is probably not claude", "is typing on virtual keyboards", "is 100% artificial", "is baking 3,000 cookies", "thinks you should buy 30,000,000 Robux", "is consuming more RAM", "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", "will respond very good", "meows cutely", "hates xrt"]

class olm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.olm_queue = asyncio.Queue()
        self.processing = False

    async def cog_load(self):
        self.worker_task = asyncio.create_task(self.olm_worker())

    async def cog_unload(self):
        self.worker_task.cancel()

    async def olm_worker(self):
        while True:
            interaction, thingy = await self.olm_queue.get()
            self.processing = True
            try:
                result = await asyncio.to_thread(
                    client.predict,
                    message=thingy,
                    history=[],
                    use_thought=True,
                    api_name="/chat"
                )
                content = result[-1]['content'][0]['text']
                content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL)
                content = content.replace('__DONE__', '').strip()

                view = discord.ui.LayoutView()
                view.add_item(discord.ui.TextDisplay(f"-# *{thingy}*"))
                view.add_item(discord.ui.Separator())
                view.add_item(discord.ui.TextDisplay(content))
                await interaction.edit_original_response(content="", view=view)

            except Exception as e:
                await interaction.edit_original_response(content=str(e))
            finally:
                self.processing = False
                self.olm_queue.task_done()

    @app_commands.command(name='olm')
    async def olm(self, interaction, thingy: str):
        busy = self.processing or not self.olm_queue.empty()
        queue_text = f"\n-# another request is being handled, this one has been placed in a queue" if busy else ""
        await interaction.response.send_message(f"*⏳ OLM {secrets.choice(olm_is)}...{queue_text}*")
        await self.olm_queue.put((interaction, thingy))


async def setup(bot):
    await bot.add_cog(olm(bot))
