import traceback

import discord
from discord.ext import commands


class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(hidden=True)
    async def xp(self, ctx):
        await ctx.reply('you hqv3 on3 2illqim xp@!!!')



async def setup(bot):
    await bot.add_cog(XP(bot), guilds=[discord.Object(id=1226051359066030111), discord.Object(1187525934400671814)])
