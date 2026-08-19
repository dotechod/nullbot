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
import httpx

from openai import AsyncOpenAI
prompt = f"""
You are an AI designed to take incorrect LaTeX/mathjax snippets and fixing it 
They will be separated by newlines, and you must output the corrected snippet the same way in the same order
When you respond, you must respond with ONLY the corrected latex snippet, and DO NOT add any mathjax dollar signs/indicators

"""

async def strip_stainless_headers(request: httpx.Request):
    for key in list(request.headers.keys()):
        if key.lower().startswith("x-stainless"):
            del request.headers[key]

messages = [
    {'role': 'system', 'content': prompt}
]
v_client = AsyncOpenAI(
    api_key=os.getenv("VOID"),
    base_url="https://api.voidai.app/v1/"
)


client = AsyncOpenAI(
    api_key="sk-none",
    base_url="https://api.okemovail.com/v1",
    http_client=httpx.AsyncClient(event_hooks={"request": [strip_stainless_headers]})
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
        self.thought_store = {}

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
            result = await client.chat.completions.create(model="octan", messages=[{"role": "user", "content": thingy}])
            content = result.choices[0].message.content

            thought_match = re.search(r'<thought>(.*?)</thought>|<think>(.*?)</think>', content, flags=re.DOTALL)
            thought_content = next((m for m in thought_match.groups() if m),
                                   None).strip() if thought_match else None

            content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL)
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            content = content.replace('__DONE__', '').strip()


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
