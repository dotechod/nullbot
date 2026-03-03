import traceback
import discord
from discord.ext import commands
import asyncio
import os
from colorama import Fore
from dotenv import load_dotenv
import subprocess


load_dotenv()


intents = discord.Intents.all()
mentions = discord.AllowedMentions(everyone=False, users=True, roles=False)
bot = commands.Bot(
    command_prefix=',',
    intents=intents,
    application_id=1345951741144989766,
    activity=discord.Game(name="Playing Half-Life 41"),
)


@bot.event
async def on_ready():
    print(Fore.LIGHTWHITE_EX + f'logged in as {bot.user.name} - {bot.user.id} ({discord.__version__})')
    print(Fore.RESET)
    bot.startup_time = discord.utils.utcnow()


async def load():
    for file in os.listdir('./cogs'):
        if file.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{file[:-3]}')
                print(Fore.GREEN + f'{file}')
            except:
                print(Fore.RED + f'{file}')
                traceback.print_exc()


async def main():
    await load()
    await bot.start(os.getenv("TOKEN"), reconnect=True)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
