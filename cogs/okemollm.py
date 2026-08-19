import discord
from discord import app_commands
from discord.ext import commands
import os
import re
import secrets
import aiohttp
import httpx
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

OKEMOVAIL_URL = "https://api.okemovail.com/v1/chat/completions"

olm_is = ["is thinking", "is cooking up a response", "wants you to order a Shamrock Shake® from McDonalds for only $5.19", "is crunching data", "thinks you're dumb", "thinks 1+1 equals ~~4~~ 2", "is making Minecraft 2", "is not real", "is <UNK><UNK><UNK><UNK><UNK>", "is probably not claude", "is typing on virtual keyboards", "is 100% artificial", "is baking 3,000 cookies", "thinks you should buy 30,000,000 Robux", "is consuming more RAM", "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", "will respond very good", "meows cutely", "i okemollm okemollm, and glittery okemollm, glittery glittery storm glittery storm okemollm glittery storm okemollm glittery storm okemollm", "can almost write a haiku", "is counting sheep", "aaaaaaaaaaaaaa", "is miwi certified", "is hallucinating excel spreadsheets", "dreams of kiwis", "- powered by 13 oceans", "2: electric boogaloo", "is migrating to mars"]


async def call_okemovail(thingy: str) -> str:
    """Hits the okemovail chat completions endpoint with a bare httpx request,
    since the openai SDK's request shape gets blocked from this network
    (Cloudflare or similar) even though plain httpx/curl succeed."""
    async with httpx.AsyncClient(timeout=60) as http_client:
        resp = await http_client.post(
            OKEMOVAIL_URL,
            headers={
                "Authorization": "Bearer sk-none",
                "Content-Type": "application/json",
            },
            json={
                "model": "octan",
                "messages": [{"role": "user", "content": thingy}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


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
            content = await call_okemovail(thingy)

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