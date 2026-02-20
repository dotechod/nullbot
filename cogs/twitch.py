import discord
from discord import app_commands
from discord.ext import commands
import os
import platform
import subprocess
import sys
import asyncio
import yaml
from pathlib import Path
import dotenv

import json

from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.object.eventsub import StreamOnlineEvent, StreamOfflineEvent




dotenv.load_dotenv()

CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
TARGET_SCOPES = [AuthScope.USER_READ_EMAIL]
TARGET_CHANNEL = 'xarrak99'
TOKEN_FILE = 'twitch_tokens.json'


def save_tokens(token, refresh_token):
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'token': token, 'refresh_token': refresh_token}, f)
    print("✓ Tokens saved")


def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
            return data['token'], data['refresh_token']
    return None, None


class TwitchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.twitch = None
        self.eventsub = None
        self.user_id = None
        self.is_live = False

    async def cog_load(self):
        await self.setup_twitch()

    async def cog_unload(self):
        await self.cleanup()

    async def cleanup(self):
        try:
            if self.eventsub:
                await self.eventsub.stop()
            if self.twitch:
                await self.twitch.close()
            print("✓ Twitch connections cleaned up")
        except Exception as e:
            print(f"Error during cleanup: {e}")

    async def setup_twitch(self):
        try:
            print("Setting up Twitch integration...")

            self.twitch = await Twitch(CLIENT_ID, CLIENT_SECRET)
            token, refresh_token = load_tokens()

            if token and refresh_token:
                print("Using saved Twitch tokens...")
                try:
                    await self.twitch.set_user_authentication(token, TARGET_SCOPES, refresh_token)
                    print("✓ Authenticated with saved tokens")
                except Exception as e:
                    print(f"Saved tokens invalid: {e}")
                    token, refresh_token = None, None

            if not token:
                print("Authenticating with Twitch (browser will open)...")
                auth = UserAuthenticator(self.twitch, TARGET_SCOPES)
                token, refresh_token = await auth.authenticate()
                await self.twitch.set_user_authentication(token, TARGET_SCOPES, refresh_token)
                save_tokens(token, refresh_token)
                print("✓ Twitch authentication complete")

            user = await first(self.twitch.get_users(logins=[TARGET_CHANNEL]))
            if not user:
                print(f"❌ User {TARGET_CHANNEL} not found!")
                return

            self.user_id = user.id
            print(f"Found user: {user.display_name} (ID: {self.user_id})")

            self.eventsub = EventSubWebsocket(self.twitch)
            self.eventsub.start()
            print("EventSub WebSocket connected")

            await self.eventsub.listen_stream_online(
                broadcaster_user_id=self.user_id,
                callback=self.on_stream_online
            )
            print("✓ Subscribed to stream online events")

            await self.eventsub.listen_stream_offline(
                broadcaster_user_id=self.user_id,
                callback=self.on_stream_offline
            )
            print("✓ Subscribed to stream offline events")

            print("🚀 Twitch EventSub is running!\n")

        except Exception as e:
            print(f"❌ Error setting up Twitch: {e}")
            import traceback
            traceback.print_exc()

    async def send_online_notification(self, data: StreamOnlineEvent):
        try:
            stream = await first(self.twitch.get_streams(user_id=[self.user_id]))

            if not stream:
                return

            game_name = "Game Name"
            if stream.game_id:
                game = await first(self.twitch.get_games(game_ids=[stream.game_id]))
                if game:
                    game_name = game.name

            thumbnail_url = stream.thumbnail_url.replace('{width}', '1920').replace('{height}', '1080')

            user = await first(self.twitch.get_users(user_ids=[self.user_id]))
            profile_image = user.profile_image_url if user else None

            channel = self.bot.get_channel(1187531474031890592)
            if channel:
                embed = discord.Embed(
                    title=f"**{data.event.broadcaster_user_name}** is now live on Twitch",
                    description=stream.title or "Stream Name",
                    color=discord.Color.purple(),
                    url=f"https://twitch.tv/{data.event.broadcaster_user_login}"
                )
                embed.add_field(name="Category", value=game_name, inline=True)
                embed.add_field(name="Viewers", value=str(stream.viewer_count), inline=True)
                embed.set_image(url=thumbnail_url)

                if profile_image:
                    embed.set_thumbnail(url=profile_image)

                embed.timestamp = data.event.started_at

                await channel.send("<@&1187602012926390334>", embed=embed)
        except Exception as e:
            pass
    async def send_offline_notification(self, data: StreamOfflineEvent):
        try:
            channel = self.bot.get_channel(1187531474031890592)
            if channel:
                await channel.send('Stream is now offline')
        except Exception as e:
            pass
    async def on_stream_online(self, data: StreamOnlineEvent):

        self.is_live = True

        asyncio.run_coroutine_threadsafe(
            self.send_online_notification(data),
            self.bot.loop
        )

    async def on_stream_offline(self, data: StreamOfflineEvent):
        self.is_live = False

        asyncio.run_coroutine_threadsafe(
            self.send_offline_notification(data),
            self.bot.loop
        )

    @commands.command(name='livestatus')
    async def live_status(self, ctx):
        if self.is_live:
            await ctx.send(f"🔴 {TARGET_CHANNEL} is currently live on Twitch")
        else:
            await ctx.send(f"⚫ {TARGET_CHANNEL} is currently offline")

    @commands.command(name='reloadtwitch')
    @commands.has_permissions(administrator=True)
    async def reload_twitch(self, ctx):
        await ctx.send("Reloading Twitch integration...")
        await self.cleanup()
        await self.setup_twitch()
        await ctx.send("✓ Twitch integration reloaded!")


async def setup(bot):
    await bot.add_cog(TwitchCog(bot))