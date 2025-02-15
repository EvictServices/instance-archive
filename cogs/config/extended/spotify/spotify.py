from discord.ext.commands import Cog, group
from discord import Embed, Message, Member
from core.client.context import Context
from tools import CompositeMetaClass, MixinMeta
from datetime import datetime, timezone
import discord
import logging
from typing import Optional, Literal

from managers.paginator import Paginator

log = logging.getLogger(__name__)

class Spotify(MixinMeta, metaclass=CompositeMetaClass):
    """
    Link and manage Spotify accounts.
    """
    
    @group(invoke_without_command=True)
    async def spotify(self, ctx: Context) -> Message:
        """View Spotify connection status and current playback."""
        
        token = await self._get_token(ctx)
        if not token:
            return
        
        log.info(f"Making Spotify API request for user {ctx.author.id}")
        log.info(f"Access token: {token[:20]}...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        log.info(f"Request headers: {headers}")
        
        async with self.bot.session.get(
            "https://api.spotify.com/v1/me/player",
            headers=headers
        ) as resp:
            log.info(f"Spotify API response status: {resp.status}")
            log.info(f"Response headers: {dict(resp.headers)}")
            
            if resp.status == 204:
                embed = Embed(
                    title="<:spotify:1318853142003318814> Spotify",
                    description="No active playback",
                    color=0x1DB954
                )
                return await ctx.send(embed=embed)
            
            if resp.status == 401:
                embed = Embed(
                    title="<:spotify:1318853142003318814> Authentication Error",
                    description="Session expired. Please relink your account using `;spotify link`",
                    color=0x1DB954
                )
                return await ctx.send(embed=embed)
            
            data = await resp.json()
            log.info(f"Spotify API response data: {data}")
            
            if not data.get('item'):
                embed = Embed(
                    title="<:spotify:1318853142003318814> Spotify",
                    description="No track information available",
                    color=0x1DB954
                )
                return await ctx.send(embed=embed)

            track = data['item']
            artists = ", ".join(artist['name'] for artist in track['artists'])
            duration = track['duration_ms'] / 1000
            progress = data['progress_ms'] / 1000 if data.get('progress_ms') else 0
            
            bar_length = 8
            filled = int((progress / duration) * bar_length)
            
            if filled == 0:
                progress_bar = "<:left:1318855421183655979>" + "<:black:1318856866150875218>" * (bar_length - 2) + "<:blackright:1236094153159610439>"
            elif filled == bar_length:
                progress_bar = "<:blackright:1236094153159610439>" * filled
            else:
                progress_bar = "<:left:1318855421183655979>" + "<:white:1318855409854976065>" * (filled - 1) + "<:right:1318855457682624535>" + "<:black:1318856866150875218>" * (bar_length - filled - 2) + "<:blackright:1236094153159610439>"

            embed = Embed(color=0x1DB954)
            
            if track['album']['images']:
                embed.set_thumbnail(url=track['album']['images'][0]['url'])
            
            embed.add_field(
                name="<:spotify:1318853142003318814> Now Playing",
                value=f"**[{track['name']}]({track['external_urls'].get('spotify', '')})**{' <:explicit:1318858668791435264>' if track.get('explicit') else ''}\nby **{artists}**",
                inline=False
            )
            
            embed.add_field(
                name="Progress",
                value=f"`{int(progress//60):02d}:{int(progress%60):02d}` {progress_bar} `{int(duration//60):02d}:{int(duration%60):02d}`",
                inline=False
            )
            
            states = []
            if data.get('is_playing'):
                states.append("<:listening:1318854824111902770> Playing")
            else:
                states.append("⏸️ Paused")
            if data.get('shuffle_state'):
                states.append("<:shuffle:1318854828008407081> Shuffle")
            if data.get('repeat_state') != "off":
                states.append("<:repeat:1318854825953329173> Repeat")
            if data.get('device'):
                states.append(f"<:device:1318859440929374219> {data['device'].get('type', 'Unknown').title()}")
            
            log.info(f"Device data: {data.get('device')}")
            log.info(f"States: {states}")
            
            embed.add_field(
                name="Status",
                value=" • ".join(states),
                inline=True
            )

            device_emojis = {
                "computer": "💻",
                "smartphone": "📱",
                "speaker": "🔊",
                "tv": "📺",
                "tablet": "📱",
                "gamepad": "🎮",
                "avr": "🎧",
                "stb": "📱",
                "audiodongle": "🎧",
                "automobile": "🚗",
                "unknown": "📱"
            }

            view = None
            async with self.bot.session.get(
                "https://api.spotify.com/v1/me/player/devices",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    devices = await resp.json()
                    if devices.get('devices'):
                        options = []
                        current_device_id = data.get('device', {}).get('id')
                        
                        for device in devices['devices']:
                            device_type = device['type'].lower()
                            device_emoji = device_emojis.get(device_type, "📱")
                            options.append(
                                discord.SelectOption(
                                    label=f"{device['name']} ({device['type']})",
                                    value=device['id'],
                                    description="Active" if device.get('is_active') else "Available",
                                    emoji=device_emoji,
                                    default=device['id'] == current_device_id
                                )
                            )
                        
                        if options:
                            view = DeviceSelectView(ctx, token, options)

            playback_view = PlaybackControlsView(ctx, token)
            if view:
                for item in playback_view.children:
                    view.add_item(item)
            else:
                view = playback_view

            return await ctx.send(embed=embed, view=view)

    @spotify.command(name="link")
    async def spotify_link(self, ctx: Context) -> Message:
        """Link your Spotify account."""
        
        view = discord.ui.View()
        button = discord.ui.Button(
            style=discord.ButtonStyle.url,
            label="Connect Spotify",
            url="https://evict.bot/login?forSpotify=true"
        )
        view.add_item(button)
        
        embed = Embed(
            title="🎵 Link Spotify Account",
            description="Click the button below to connect your Spotify account",
            color=ctx.color
        )
        
        return await ctx.send(embed=embed, view=view)

    @spotify.command(name="unlink")
    async def spotify_unlink(self, ctx: Context) -> Message:
        """Unlink your Spotify account."""
        
        await self.bot.db.execute(
            """
            DELETE FROM user_spotify
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        embed = Embed(
            title="🎵 Spotify Disconnected",
            description="Your Spotify account has been unlinked",
            color=ctx.color
        )
        
        return await ctx.send(embed=embed)

    @spotify.command(name="next")
    async def spotify_next(self, ctx: Context) -> Message:
        """Skip to the next track."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.post(
            "https://api.spotify.com/v1/me/player/next",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                embed = Embed(description="<:next:1318858363240583239> Skipped to next track", color=0x1DB954)
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to skip track")

    @spotify.command(name="previous")
    async def spotify_previous(self, ctx: Context) -> Message:
        """Go back to the previous track."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.post(
            "https://api.spotify.com/v1/me/player/previous",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                embed = Embed(description="<:previous:1318858364784218152> Returned to previous track", color=0x1DB954)
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to go to previous track")

    @spotify.command(name="pause")
    async def spotify_pause(self, ctx: Context) -> Message:
        """Pause playback."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.put(
            "https://api.spotify.com/v1/me/player/pause",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                embed = Embed(description="<:pause:1318858446220824658> Paused playback", color=0x1DB954)
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to pause playback")

    @spotify.command(name="play")
    async def spotify_play(self, ctx: Context, *, query: str = None) -> Message:
        """Resume playback or play a specific song/playlist."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        if not query:
            async with self.bot.session.put(
                "https://api.spotify.com/v1/me/player/play",
                headers=headers
            ) as resp:
                if resp.status in (204, 200):
                    embed = Embed(description="<:listening:1318854824111902770> Resumed playback", color=0x1DB954)
                    return await ctx.send(embed=embed, ephemeral=True)
                return await ctx.warn("Failed to resume playback")
            
        if "spotify.com/" in query:
            if "track/" in query:
                track_id = query.split("track/")[1].split("?")[0]
                play_data = {"uris": [f"spotify:track:{track_id}"]}
                
                async with self.bot.session.put(
                    "https://api.spotify.com/v1/me/player/play",
                    headers=headers,
                    json=play_data
                ) as resp:
                    if resp.status in (204, 200):
                        async with self.bot.session.get(
                            f"https://api.spotify.com/v1/tracks/{track_id}",
                            headers=headers
                        ) as track_resp:
                            if track_resp.status == 200:
                                track_data = await track_resp.json()
                                embed = Embed(description=f"<:listening:1318854824111902770> Playing **{track_data['name']}** by **{track_data['artists'][0]['name']}**", color=0x1DB954)
                                return await ctx.send(embed=embed, ephemeral=True)
                    return await ctx.warn("Failed to play track")
                    
            elif "playlist/" in query:
                playlist_id = query.split("playlist/")[1].split("?")[0]
                play_data = {"context_uri": f"spotify:playlist:{playlist_id}"}
                
                async with self.bot.session.put(
                    "https://api.spotify.com/v1/me/player/play",
                    headers=headers,
                    json=play_data
                ) as resp:
                    if resp.status in (204, 200):
                        async with self.bot.session.get(
                            f"https://api.spotify.com/v1/playlists/{playlist_id}",
                            headers=headers
                        ) as playlist_resp:
                            if playlist_resp.status == 200:
                                playlist_data = await playlist_resp.json()
                                embed = Embed(description=f"<:listening:1318854824111902770> Playing playlist **{playlist_data['name']}**", color=0x1DB954)
                                return await ctx.send(embed=embed, ephemeral=True)
                    return await ctx.warn("Failed to play playlist")
        
        async with self.bot.session.get(
            f"https://api.spotify.com/v1/search?q={query}&type=track&limit=1",
            headers=headers
        ) as resp:
            if resp.status != 200:
                return await ctx.warn("Failed to search for track")
            
            data = await resp.json()
            if not data['tracks']['items']:
                return await ctx.warn("No tracks found")
            
            track = data['tracks']['items'][0]
            
            async with self.bot.session.put(
                "https://api.spotify.com/v1/me/player/play",
                headers=headers,
                json={"uris": [track['uri']]}
            ) as resp:
                if resp.status in (204, 200):
                    embed = Embed(description=f"<:listening:1318854824111902770> Playing **{track['name']}** by **{track['artists'][0]['name']}**", color=0x1DB954)
                    return await ctx.send(embed=embed, ephemeral=True)
                return await ctx.warn("Failed to play track")

    @spotify.command(name="stop")
    async def spotify_stop(self, ctx: Context) -> Message:
        """Stop playback."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.put(
            "https://api.spotify.com/v1/me/player/pause",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                embed = Embed(description="⏹️ Stopped playback", color=0x1DB954)
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to stop playback")

    @spotify.command(name="seek")
    async def spotify_seek(self, ctx: Context, position: str) -> Message:
        """Seek to a specific position (in seconds or MM:SS format)."""
        token = await self._get_token(ctx)
        if not token:
            return
            
        try:
            if ':' in position:
                minutes, seconds = position.split(':')
                position_ms = (int(minutes) * 60 + int(seconds)) * 1000
            else:
                position_ms = int(position) * 1000
        except ValueError:
            return await ctx.warn("Invalid time format. Use seconds or MM:SS")

        headers = {"Authorization": f"Bearer {token}"}
        
        async with self.bot.session.put(
            f"https://api.spotify.com/v1/me/player/seek?position_ms={position_ms}",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                embed = Embed(description=f"⏩ Seeked to `{position}`", color=0x1DB954)
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to seek")

    @spotify.command(name="volume")
    async def spotify_volume(self, ctx: Context, volume: int) -> Message:
        """Set the volume (0-100)."""
        if not 0 <= volume <= 100:
            return await ctx.warn("Volume must be between 0 and 100")

        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.put(
            f"https://api.spotify.com/v1/me/player/volume?volume_percent={volume}",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                embed = Embed(description=f"<:volume:1318858592689852416> Volume set to {volume}%", color=0x1DB954)
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to set volume")

    @spotify.command(name="playlists", aliases=["pl"])
    async def spotify_playlists(self, ctx: Context) -> Message:
        """View your Spotify playlists."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.get(
            "https://api.spotify.com/v1/me/playlists",
            headers=headers
        ) as resp:
            if resp.status != 200:
                return await ctx.warn("Failed to fetch playlists")
            
            data = await resp.json()
            if not data['items']:
                return await ctx.warn("You don't have any playlists!")

            entries = []
            for playlist in data['items']:
                owner = "👑 " if playlist['owner']['id'] == ctx.author.id else ""
                privacy = "🔒 " if not playlist['public'] else ""
                collab = "👥 " if playlist['collaborative'] else ""
                
                entries.append(
                    f"{owner}{privacy}{collab}[**{playlist['name']}**]({playlist['external_urls']['spotify']})\n"
                    f"> {playlist['tracks']['total']:,} tracks"
                )

            embed = Embed(
                color=0x1DB954,
                title="<:spotify:1318853142003318814> Your Spotify Playlists"
            )
            
            paginator = Paginator(
                ctx,
                entries=entries,
                embed=embed,
                per_page=5
            )
            return await paginator.start()

    @spotify.command(name="queue", aliases=["q"])
    async def spotify_queue(self, ctx: Context) -> Message:
        """View your current Spotify queue."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.get(
            "https://api.spotify.com/v1/me/player/queue",
            headers=headers
        ) as resp:
            if resp.status != 200:
                return await ctx.warn("Failed to fetch queue")
            
            data = await resp.json()
            if not data.get('queue'):
                return await ctx.warn("Your queue is empty!")

            entries = []
            for i, track in enumerate(data['queue'][:10], 1):
                artists = ", ".join(artist['name'] for artist in track['artists'])
                entries.append(
                    f"`{i}.` [**{track['name']}**]({track['external_urls']['spotify']}) by **{artists}**"
                )

            embed = Embed(
                color=0x1DB954,
                title="<:spotify:1318853142003318814> Queue"
            )
            
            if data.get('currently_playing'):
                track = data['currently_playing']
                artists = ", ".join(artist['name'] for artist in track['artists'])
                embed.add_field(
                    name="Now Playing",
                    value=f"[**{track['name']}**]({track['external_urls']['spotify']}) by **{artists}**",
                    inline=False
                )
                
            embed.description = "\n".join(entries)
            return await ctx.send(embed=embed)

    @spotify.command(name="shuffle")
    async def spotify_shuffle(self, ctx: Context) -> Message:
        """Toggle shuffle mode."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.get(
            "https://api.spotify.com/v1/me/player",
            headers=headers
        ) as resp:
            if resp.status != 200:
                return await ctx.warn("Failed to get playback state")
            
            data = await resp.json()
            current_state = data.get('shuffle_state', False)
        
        async with self.bot.session.put(
            f"https://api.spotify.com/v1/me/player/shuffle?state={not current_state}",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                state = "enabled" if not current_state else "disabled"
                embed = Embed(
                    description=f"<:shuffle:1318854828008407081> Shuffle {state}",
                    color=0x1DB954
                )
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to toggle shuffle")

    @spotify.command(name="repeat", aliases=["loop"])
    async def spotify_repeat(self, ctx: Context, mode: Optional[Literal["off", "track", "context"]] = None) -> Message:
        """
        Change repeat mode.
        Modes: off, track (current song), context (playlist/album)
        """
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        if not mode:
            async with self.bot.session.get(
                "https://api.spotify.com/v1/me/player",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to get playback state")
                
                data = await resp.json()
                current_state = data.get('repeat_state', 'off')
                modes = ['off', 'track', 'context']
                mode = modes[(modes.index(current_state) + 1) % len(modes)]
        
        async with self.bot.session.put(
            f"https://api.spotify.com/v1/me/player/repeat?state={mode}",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                states = {
                    "off": "Repeat disabled",
                    "track": "Repeating current track",
                    "context": "Repeating playlist/album"
                }
                embed = Embed(
                    description=f"<:repeat:1318854825953329173> {states[mode]}",
                    color=0x1DB954
                )
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to change repeat mode")

    @spotify.command(name="save", aliases=["like"])
    async def spotify_save(self, ctx: Context) -> Message:
        """Save the current track to your Liked Songs."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers=headers
        ) as resp:
            if resp.status != 200:
                return await ctx.warn("No track is currently playing")
            
            data = await resp.json()
            if not data.get('item'):
                return await ctx.warn("No track information available")
            
            track_id = data['item']['id']
        
        async with self.bot.session.put(
            f"https://api.spotify.com/v1/me/tracks?ids={track_id}",
            headers=headers
        ) as resp:
            if resp.status in (200, 204):
                track = data['item']
                artists = ", ".join(artist['name'] for artist in track['artists'])
                embed = Embed(
                    description=f"<:fav:1318904945679794279> Saved [**{track['name']}**]({track['external_urls']['spotify']}) by **{artists}** to your Liked Songs",
                    color=0x1DB954
                )
                return await ctx.send(embed=embed, ephemeral=True)
            return await ctx.warn("Failed to save track")

    @spotify.command(name="unsave", aliases=["unlike", "remove"])
    async def spotify_unsave(self, ctx: Context) -> Message:
        """Remove the current track from your Liked Songs."""
        headers = {"Authorization": f"Bearer {await self._get_token(ctx)}"}
        
        async with self.bot.session.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers=headers
        ) as resp:
            if resp.status != 200:
                return await ctx.warn("No track is currently playing")
            
            data = await resp.json()
            if not data.get('item'):
                return await ctx.warn("No track information available")
            
            track_id = data['item']['id']
        
        async with self.bot.session.delete(
            f"https://api.spotify.com/v1/me/tracks?ids={track_id}",
            headers=headers
        ) as resp:
            if resp.status == 403:
                return await ctx.warn("Missing permissions to modify your library. Please relink your account with the proper scopes.")
            elif resp.status not in (200, 204):
                return await ctx.warn("Failed to remove track")
            
            track = data['item']
            artists = ", ".join(artist['name'] for artist in track['artists'])
            embed = Embed(
                description=f"<:remove:1318905525567492096> Removed [**{track['name']}**]({track['external_urls']['spotify']}) by **{artists}** from your Liked Songs",
                color=0x1DB954
            )
            return await ctx.send(embed=embed, ephemeral=True)

    async def _get_token(self, ctx: Context) -> str:
        """Helper method to get a valid token."""
        linked = await self.bot.db.fetchrow(
            """
            SELECT 
                access_token,
                refresh_token,
                token_expires_at AT TIME ZONE 'UTC' as token_expires_at
            FROM user_spotify 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        if not linked:
            await ctx.warn("Your Spotify account is not linked. Use `;spotify link` to connect.")
            return None

        expires_at = linked['token_expires_at'].replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        
        log.info(f"[Spotify] Token expires at: {expires_at}")
        log.info(f"[Spotify] Current time: {now}")
        log.info(f"[Spotify] Token expired: {expires_at <= now}")
        
        if expires_at <= now:
            log.info(f"[Spotify] Attempting to refresh token for user {ctx.author.id}")
            try:
                async with self.bot.session.post(
                    "https://accounts.spotify.com/api/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": linked['refresh_token'],
                        "client_id": "35160aca03654d799ac2bd1dd023dd9b",
                        "client_secret": "a37fede97e154c4d89b2420cbe18dda6"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as resp:
                    if resp.status != 200:
                        log.error(f"Failed to refresh token: {await resp.text()}")
                        await ctx.warn("Failed to refresh Spotify token. Please relink using `;spotify link`")
                        return None
                    
                    data = await resp.json()
                    new_access_token = data['access_token']
                    expires_in = data['expires_in']
                    
                    log.info(f"[Spotify] Successfully refreshed token, expires in {expires_in} seconds")
                    
                    await self.bot.db.execute(
                        """
                        UPDATE user_spotify 
                        SET 
                            access_token = $1,
                            token_expires_at = NOW() + interval '1 second' * $2
                        WHERE user_id = $3
                        """,
                        new_access_token,
                        expires_in,
                        ctx.author.id
                    )
                    
                    return new_access_token
            except Exception as e:
                log.error(f"Error refreshing token: {e}")
                await ctx.warn("An error occurred while refreshing your Spotify token. Please try again or relink.")
                return None
        
        log.info("[Spotify] Using existing token")
        return linked['access_token']

class DeviceSelectView(discord.ui.View):
    def __init__(self, ctx, token, options):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.token = token
        
        select = discord.ui.Select(
            placeholder="Switch Playback Device",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.device_selected
        self.add_item(select)
        
    async def device_selected(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return
            
        device_id = interaction.data['values'][0]
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        async with self.ctx.bot.session.put(
            f"https://api.spotify.com/v1/me/player",
            headers=headers,
            json={"device_ids": [device_id]}
        ) as resp:
            if resp.status in (204, 200):
                await interaction.response.send_message("✅ Playback device updated!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to update playback device", ephemeral=True)

class PlaybackControlsView(discord.ui.View):
    def __init__(self, ctx, token):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.token = token
        
        self.previous = discord.ui.Button(emoji="<:previous:1318858364784218152>", style=discord.ButtonStyle.gray)
        self.play_pause = discord.ui.Button(emoji="<:pause:1318858446220824658>", style=discord.ButtonStyle.gray)
        self.next = discord.ui.Button(emoji="<:next:1318858363240583239>", style=discord.ButtonStyle.gray)
        self.volume = discord.ui.Button(emoji="<:volume:1318858592689852416>", style=discord.ButtonStyle.gray)
        
        self.previous.callback = self.previous_track
        self.play_pause.callback = self.toggle_playback
        self.next.callback = self.next_track
        self.volume.callback = self.toggle_mute
        
        self.add_item(self.previous)
        self.add_item(self.play_pause)
        self.add_item(self.next)
        self.add_item(self.volume)
        
    async def previous_track(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return
            
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.ctx.bot.session.post(
            "https://api.spotify.com/v1/me/player/previous",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                await interaction.response.send_message("⏮️ Previous track", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to go to previous track", ephemeral=True)
                
    async def toggle_playback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return
            
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.ctx.bot.session.get(
            "https://api.spotify.com/v1/me/player",
            headers=headers
        ) as resp:
            if resp.status != 200:
                await interaction.response.send_message("❌ Failed to get playback state", ephemeral=True)
                return
                
            data = await resp.json()
            is_playing = data.get('is_playing', False)
            
            endpoint = "pause" if is_playing else "play"
            async with self.ctx.bot.session.put(
                f"https://api.spotify.com/v1/me/player/{endpoint}",
                headers=headers
            ) as resp:
                if resp.status in (204, 200):
                    await interaction.response.send_message(
                        "⏸️ Paused" if is_playing else "▶️ Playing",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message("❌ Failed to toggle playback", ephemeral=True)
                    
    async def next_track(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return
            
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.ctx.bot.session.post(
            "https://api.spotify.com/v1/me/player/next",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                await interaction.response.send_message("⏭️ Next track", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to skip track", ephemeral=True)

    async def toggle_mute(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return
            
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.ctx.bot.session.put(
            "https://api.spotify.com/v1/me/player/volume?volume_percent=0",
            headers=headers
        ) as resp:
            if resp.status in (204, 200):
                await interaction.response.send_message("🔇 Muted", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to mute playback", ephemeral=True)