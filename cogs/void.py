import traceback
import discord
from discord.ext import commands
import json
import io
from collections import defaultdict
import re
from openai import AsyncOpenAI
import base64
from dotenv import load_dotenv
import os

load_dotenv()

import datetime

CURRENT_DATE = datetime.datetime.now().strftime("%Y-%m-%d")


prompt = f"""
You are an AI, a discord user on the internet, responding to a image or text message. Today's date is {CURRENT_DATE}.


Here are the guidelines you should follow AT ALL TIMES:
Keep your responses around 1-2 sentences long (unless asked otherwise), and talk like you arent best friends, but you dont hate them. Make the occasional typo and don't put too much effort into spelling things.
You do NOT need to use proper grammar or punctuation, you're on the internet.
You are allowed and encouraged to use swear words.
You are allowed and encouraged to be edgy to match the user's energy and tone.
Do not police people for edgy/offensive/etc. language, you are allowed to use it in return if someone else starts it, within reason.



"""
prompt2=prompt

messages = [
    {'role': 'system', 'content': prompt}
]

client = AsyncOpenAI(
    api_key=os.getenv("VOID"),
    base_url="https://api.voidai.app/v1/"
)

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class CitationsView(discord.ui.View):
        def __init__(self, citations_data):
            super().__init__(timeout=180)  # View expires after 3 minutes
            self.citations_data = citations_data  # Store the citation data

        @discord.ui.button(label="Sources")
        async def view_citations_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer()
            citation_text = " "
            if not self.citations_data:
                citation_text = "there ar enone"
            else:
                is_list_of_urls = all(isinstance(item, str) for item in self.citations_data)

                if is_list_of_urls:
                    for i, url in enumerate(self.citations_data):
                        citation_text += f"{url}\n"
                else:
                    for i, citation in enumerate(self.citations_data):
                        title = citation.get('title', 'h')
                        url = citation.get('url', '#')

                        citation_text += f"[{title}]({url})\n"

            await interaction.message.reply(
                content=citation_text,
                suppress_embeds=True
            )

    @commands.command()
    async def chat(self, ctx):
        try:
            await ctx.reply("please ping me instead, this command is no longer active", delete_after=5)
        except Exception as e:  # Catch a more general exception to ensure all errors are reported
            await ctx.reply(f"An error occurred: {traceback.format_exc()}")

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.author.bot or not self.bot.user.mentioned_in(message):
                return

            await message.add_reaction('⏳')

            # 1. Create a FRESH message list for this specific interaction
            # (Or move the system prompt into the function)
            local_messages = [{"role": "system", "content": prompt2}]

            # Clean the mention from the message
            modified_msg = re.sub(rf'<@{self.bot.user.id}>', "", message.content).strip()

            grok = False
            if "sonar" in modified_msg.lower():
                modified_msg = modified_msg.lower().replace("sonar", "").strip()
                grok = True

            # 2. Handle replying to context
            if message.reference and message.reference.message_id:
                try:
                    replied_message = await message.channel.fetch_message(message.reference.message_id)
                    context_text = f"Replying to @{replied_message.author.name}: \"{replied_message.content[:200]}...\""
                    local_messages.append({"role": "user", "content": context_text})
                except:
                    pass

            # 3. Construct the user message properly (don't f-string the whole list)
            user_text_content = f"{message.author.name}: {modified_msg}"

            if message.attachments:
                user_content = [{"type": "text", "text": user_text_content}]
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image'):
                        user_content.append({"type": "image_url", "image_url": {"url": attachment.url}})
            else:
                user_content = user_text_content

            local_messages.append({"role": "user", "content": user_content})

            # 4. Make the API Call
            if grok:
                response = await client.chat.completions.create(model="sonar", messages=local_messages)
                # Use getattr or model_extra to safely get citations
                citations = getattr(response, "citations", [])
            else:
                response = await client.chat.completions.create(model="gpt-4o-mini", messages=local_messages)
                citations = None

            # 5. Handle UI and Reply
            view = self.CitationsView(citations) if citations else None
            await message.reply(f"{response.choices[0].message.content}", view=view)

        except Exception:
            await message.reply(f"```py\n{traceback.format_exc()}\n```")


async def setup(bot):
    await bot.add_cog(AI(bot))