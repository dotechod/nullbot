# this cog sucks. i know.
# i dont care about this project.
# i dont enjoy working on this bot.

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

prompt = """
You are OLM, a helpful AI assistant chatting in a Discord thread.
Keep responses conversational and reasonably concise.
"""

OKEMOVAIL_URL = "https://api.okemovail.com/v1/chat/completions"

# how many prior turns to keep when replying, so payloads/context don't grow forever
MAX_HISTORY_MESSAGES = 20
# how many active conversation threads to keep in memory at once
MAX_TRACKED_CONVERSATIONS = 500

olm_is = ["is thinking", "is cooking up a response", "wants you to order a Shamrock Shake® from McDonalds for only $5.19", "is crunching data", "thinks you're dumb", "thinks 1+1 equals ~~4~~ 2", "is making Minecraft 2", "is not real", "is <UNK><UNK><UNK><UNK><UNK>", "is probably not claude", "is typing on virtual keyboards", "is 100% artificial", "is baking 3,000 cookies", "thinks you should buy 30,000,000 Robux", "is consuming more RAM", "Lorem ipsum dolor sit amet, consectetur adipiscing elit.", "will respond very good", "meows cutely", "i okemollm okemollm, and glittery okemollm, glittery glittery storm glittery storm okemollm glittery storm okemollm glittery storm okemollm", "can almost write a haiku", "is counting sheep", "aaaaaaaaaaaaaa", "is miwi certified", "is hallucinating excel spreadsheets", "dreams of kiwis", "- powered by 13 oceans", "2: electric boogaloo", "is migrating to mars"]


async def call_okemovail(chat_messages: list[dict]) -> str:
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
                "messages": chat_messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def strip_thought(content: str):
    """Pulls <thought>/<think> blocks out of a response, returns (clean_content, thought_or_None)."""
    thought_match = re.search(r'<thought>(.*?)</thought>|<think>(.*?)</think>', content, flags=re.DOTALL)
    thought_content = next((m for m in thought_match.groups() if m), None).strip() if thought_match else None

    content = re.sub(r'<thought>.*?</thought>', '', content, flags=re.DOTALL)
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    content = content.replace('__DONE__', '').strip()
    return content, thought_content


def build_view(prompt_label: str, content: str) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView()
    view.add_item(discord.ui.TextDisplay(f"-# *{prompt_label}*"))
    view.add_item(discord.ui.Separator())
    view.add_item(discord.ui.TextDisplay(content[:3900] if len(content) > 3900 else content))
    return view


class olm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.thought_store = {}
        # message_id (of a bot response) -> list[{"role": ..., "content": ...}]
        self.conversations: dict[int, list[dict]] = {}

    def _remember(self, message_id: int, history: list[dict]):
        # simple cap so this doesn't grow forever across a long-running process
        if len(self.conversations) >= MAX_TRACKED_CONVERSATIONS:
            oldest_key = next(iter(self.conversations))
            self.conversations.pop(oldest_key, None)
        self.conversations[message_id] = history[-MAX_HISTORY_MESSAGES:]

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data.get("custom_id") == "show_thought":
                thought = self.thought_store.get(interaction.message.id, "No thinking found.")
                thought_text = thought[:1990] if len(thought) > 1990 else thought
                await interaction.response.send_message(f"-# 💭 thinking\n{thought_text}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.reference or not message.reference.message_id:
            return

        parent_id = message.reference.message_id
        history = self.conversations.get(parent_id)
        if history is None:
            return  # not a thread we're tracking, ignore

        user_text = message.content.strip()
        if not user_text:
            return

        async with message.channel.typing():
            new_history = history + [{"role": "user", "content": user_text}]
            try:
                raw_content = await call_okemovail(new_history)
            except Exception as e:
                await message.reply(f"⚠️ {e}", mention_author=False)
                return

            content, thought_content = strip_thought(raw_content)
            new_history.append({"role": "assistant", "content": raw_content})

            view = build_view(user_text, content)
            if thought_content:
                action_row = discord.ui.ActionRow()
                action_row.add_item(
                    discord.ui.Button(label="💭 Show Thinking", style=discord.ButtonStyle.secondary,
                                      custom_id="show_thought"))
                view.add_item(action_row)

            reply_msg = await message.reply(view=view, mention_author=False)
            self.thought_store[reply_msg.id] = thought_content
            self._remember(reply_msg.id, new_history)

    @app_commands.command(name='olm')
    async def olm(self, interaction, thingy: str):
        await interaction.response.send_message(f"*⏳ OLM {secrets.choice(olm_is)}...*")
        try:
            history = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": thingy},
            ]
            raw_content = await call_okemovail(history)
            content, thought_content = strip_thought(raw_content)
            history.append({"role": "assistant", "content": raw_content})

            view = build_view(thingy, content)
            if thought_content:
                action_row = discord.ui.ActionRow()
                action_row.add_item(
                    discord.ui.Button(label="💭 Show Thinking", style=discord.ButtonStyle.secondary,
                                      custom_id="show_thought"))
                view.add_item(action_row)

            await interaction.edit_original_response(content="", view=view)
            msg = await interaction.original_response()
            self.thought_store[msg.id] = thought_content
            self._remember(msg.id, history)

        except Exception as e:
            await interaction.edit_original_response(content=str(e))


async def setup(bot):
    await bot.add_cog(olm(bot))