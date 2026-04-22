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
import aiohttp
import urllib.parse
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


client = AsyncOpenAI(
    api_key=os.getenv("VOID"),
    base_url="https://api.voidai.app/v1/"
)

olm_is = ["is thinking", "is cooking up a response", "wants you to order a Shamrock Shake® from McDonalds for only $5.19", "is crunching data", "thinks you're dumb", "thinks 1+1 equals ~~4~~ 2", "is making Minecraft 2", "is not real", "is <UNK><UNK><UNK><UNK><UNK>", "is probably not claude", "is typing on virtual keyboards", "is 100% artificial", "is baking 3,000 cookies", "thinks you should buy 30,000,000 Robux", "is consuming more RAM", "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", "will respond very good", "meows cutely", "i okemollm okemollm, and glittery okemollm, glittery glittery storm glittery storm okemollm glittery storm okemollm glittery storm okemollm", "can almost write a haiku", "is counting sheep", "aaaaaaaaaaaaaa", "is miwi certified", "is hallucinating excel spreadsheets", "dreams of kiwis", "- powered by 13 oceans", "2: electric boogaloo", "is migrating to mars"]

class ThoughtView(discord.ui.View):
    def __init__(self, thought: str):
        super().__init__(timeout=300)
        self.thought = thought

    @discord.ui.button(label="Show Thinking", style=discord.ButtonStyle.secondary)
    async def show_thought(self, interaction: discord.Interaction, button: discord.ui.Button):
        thought_text = self.thought[:1990] if len(self.thought) > 1990 else self.thought
        await interaction.response.send_message(f"{thought_text}", ephemeral=False)


class olm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data.get("custom_id") == "show_thought":
                thought = self.thought_store.get(interaction.message.id, "No thinking found.")
                thought_text = thought[:1990] if len(thought) > 1990 else thought
                await interaction.response.send_message(f"-# 💭 thinking\n{thought_text}", ephemeral=True)


    @app_commands.command(name='olm')
    async def olm(self, interaction, thingy: str):
        await interaction.response.send_message(f"*⏳ OLM {secrets.choice(olm_is)}...*")
        try:
            result = await v_client.chat.completions.create(model="octan", message=thingy)

            content = result[-1]['content'][0]['text']

            thought_match = re.search(r'<thought>(.*?)</thought>|<think>(.*?)</think>', content, flags=re.DOTALL)
            thought_content = next((m for m in thought_match.groups() if m),
                                   None).strip() if thought_match else None

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
                await interaction.edit_original_response(content="⏳ *checking latex with gpt 4o*")
                response = await v_client.chat.completions.create(model="gpt-4o-mini", messages=local_messages)
                corrected = response.choices[0].message.content  # <-- capture this
                print(corrected)
            else:
                corrected = None

            # after getting `corrected`
            if corrected:
                snippets = [s.strip() for s in corrected.strip().splitlines() if s.strip()][:10]
                files = []
                gallery_items_map = {}  # index -> File object

                await interaction.edit_original_response(content="⏳ *rendering latex*")
                async with aiohttp.ClientSession() as session:
                    for i, snippet in enumerate(snippets):
                        encoded = urllib.parse.quote(snippet)
                        url = f"https://latex.codecogs.com/png.latex?\\dpi{{150}}\\bg_black\\color{{white}}{encoded}"
                        print(f"Fetching: {url}")
                        async with session.get(url) as resp:
                            print(f"Status: {resp.status}, Content-Type: {resp.headers.get('content-type')}")
                            if resp.status == 200:
                                data = await resp.read()
                                filename = f"latex_{i}.png"
                                f = discord.File(io.BytesIO(data), filename=filename)
                                files.append(f)
                                gallery_items_map[i] = discord.UnfurledMediaItem(f"attachment://{filename}")

                tex_pattern = r'(\$\$.*?\$\$|\$.*?\$|\\\[.*?\\\]|\\\(.*?\\\))'
                parts = re.split(tex_pattern, content, flags=re.DOTALL)

                view = discord.ui.LayoutView()
                view.add_item(discord.ui.TextDisplay(f"-# *{thingy}*"))
                view.add_item(discord.ui.Separator())
                if thought_content:
                    action_row = discord.ui.ActionRow()
                    action_row.add_item(
                        discord.ui.Button(label="💭 Show Thinking", style=discord.ButtonStyle.secondary,
                                          custom_id="show_thought"))
                    view.add_item(action_row)

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
                msg = await interaction.original_response()
                self.thought_store[msg.id] = thought_content
            else:
                view = discord.ui.LayoutView()
                view.add_item(discord.ui.TextDisplay(f"-# *{thingy}*"))
                view.add_item(discord.ui.Separator())
                view.add_item(discord.ui.TextDisplay(content))
                await interaction.edit_original_response(content="", view=view)
                msg = await interaction.original_response()
                self.thought_store[msg.id] = thought_content

        except Exception as e:
            await interaction.edit_original_response(content=str(e))


async def setup(bot):
    await bot.add_cog(olm(bot))
