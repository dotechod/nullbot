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
import matplotlib.pyplot as plt
import aiohttp
import urllib.parse
import io
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import io


from openai import AsyncOpenAI
prompt = f"""
You are an AI designed to take incorrect LaTeX/mathjax snippets and fixing it 
They will be separated by newlines, and you must output the corrected snippet the same way in the same order
When you respond, you must respond with ONLY the corrected latex snippet, and DO NOT add any mathjax dollar signs/indicators

"""
messages = [
    {'role': 'system', 'content': prompt}
]
v_client = AsyncOpenAI(
    api_key=os.getenv("VOID"),
    base_url="https://api.voidai.app/v1/"
)


from gradio_client import Client
client = Client("https://polarisapi.okemovail.com/gradio/")

olm_is = ["is thinking", "is cooking up a response", "wants you to order a Shamrock Shake® from McDonalds for only $5.19", "is crunching data", "thinks you're dumb", "thinks 1+1 equals ~~4~~ 2", "is making Minecraft 2", "is not real", "is <UNK><UNK><UNK><UNK><UNK>", "is probably not claude", "is typing on virtual keyboards", "is 100% artificial", "is baking 3,000 cookies", "thinks you should buy 30,000,000 Robux", "is consuming more RAM", "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", "will respond very good", "meows cutely", "i okemollm okemollm, and glittery okemollm, glittery glittery storm glittery storm okemollm glittery storm okemollm glittery storm okemollm", "can almost write a haiku", "is counting sheep", "aaaaaaaaaaaaaa", "is miwi certified", "is hallucinating excel spreadsheets", "dreams of kiwis", "- powered by 13 oceans", "2: electric boogaloo", "is migrating to mars"]


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
                    search=False,
                    job_id=thingy,
                    use_thought=True,
                    system_prompt="",
                    api_name="/chat"
                )
                content = result[-1]['content'][0]['text']
                content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL)
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                content = content.replace('__DONE__', '').strip()

                tex_pattern = r'\$\$(.*?)\$\$|\$(.*?)\$|\\\[(.*?)\\\]|\\\((.*?)\\\)'
                matches = re.findall(tex_pattern, content, re.DOTALL)
                extracted = ""
                for match in matches:
                    content2 = next((m for m in match if m), "").strip()
                    if content2:
                        extracted += f"{content2}\n"  # was: content
                        print(extracted)

                if extracted.strip():
                    local_messages = [{"role": "system", "content": prompt}, {"role": "user", "content": extracted}]
                    await interaction.edit_original_response(content="⏳ *consulting with gpt 4o*\n-# checking for invalid latex")
                    response = await v_client.chat.completions.create(model="gpt-4o-mini", messages=local_messages)
                    corrected = response.choices[0].message.content  # <-- capture this
                    print(corrected)
                else:
                    corrected = None

                # after getting `corrected`
                if corrected:
                    snippets = [s.strip() for s in corrected.strip().splitlines() if s.strip()]
                    files = []
                    gallery_items_map = {}  # index -> File object

                    await interaction.edit_original_response(content="⏳ *rendering latex*")
                    async with aiohttp.ClientSession() as session:
                        for i, snippet in enumerate(snippets):
                            encoded = urllib.parse.quote(snippet)
                            url = f"https://math.vercel.app/?from={encoded}&color=white&bgcolor=black"
                            print(f"Fetching: {url}")
                            async with session.get(url) as resp:
                                print(f"Status: {resp.status}, Content-Type: {resp.headers.get('content-type')}")
                                if resp.status == 200:
                                    svg_data = await resp.read()
                                    drawing = svg2rlg(io.BytesIO(svg_data))
                                    png_buf = io.BytesIO()
                                    renderPM.drawToFile(drawing, png_buf, fmt="PNG")
                                    png_buf.seek(0)
                                    filename = f"latex_{i}.png"
                                    files.append(discord.File(png_buf, filename=filename))
                                    gallery_items_map[i] = discord.UnfurledMediaItem(f"attachment://{filename}")

                    tex_pattern = r'(\$\$.*?\$\$|\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\))'
                    parts = re.split(tex_pattern, content, flags=re.DOTALL)

                    view = discord.ui.LayoutView()
                    view.add_item(discord.ui.TextDisplay(f"-# *{thingy}*"))
                    view.add_item(discord.ui.Separator())

                    img_index = 0
                    for part in parts:
                        part = part.strip()
                        if not part:
                            continue
                        if re.fullmatch(tex_pattern, part, flags=re.DOTALL):
                            if img_index in gallery_items_map:
                                view.add_item(discord.ui.MediaGallery(
                                    discord.MediaGalleryItem(media=gallery_items_map[img_index])
                                ))
                            img_index += 1
                        else:
                            view.add_item(discord.ui.TextDisplay(part))

                    await interaction.edit_original_response(content="", attachments=files, view=view)
                else:
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
