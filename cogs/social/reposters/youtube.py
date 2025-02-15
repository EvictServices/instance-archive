from datetime import datetime
from io import BytesIO
from secrets import token_urlsafe
from typing import Optional
from pydantic import BaseModel
import logging
from discord import File, Message, Embed

from cogs.social.reposters.base import Reposter, Information
from main import Evict
from core.client.context import Context

log = logging.getLogger("evict.reposters.youtube")

class YouTubeStats(BaseModel):
    likes: int = 0
    views: int = 0
    comments: int = 0

class YouTubeMetadata(BaseModel):
    title: str
    uploader: str
    stats: YouTubeStats
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    description: Optional[str] = None
    uploadDate: Optional[str] = None
    quality: Optional[str] = None

class YouTubeInfo(Information):
    class Config:
        arbitrary_types_allowed = True

    success: bool
    type: str
    url: Optional[str] = None
    metadata: Optional[YouTubeMetadata] = None

class Youtube(Reposter):
    def __init__(self, bot: Evict):
        super().__init__(
            bot,
            name="YouTube",
            regex=[
                r"(?:https?://)?(?:www\.|m\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]+)(?:\S+)?",
                r"(?:https?://)?(?:www\.|m\.)?youtube(?:\.com/shorts/)([^&\n?]+)",
            ],
        )

    async def fetch(self, url: str) -> Optional[YouTubeInfo]:
        try:
            log.info(f"[YouTube] Attempting to fetch: {url}")
            
            response = await self.bot.session.post(
                "http://localhost:7700/download",
                headers={"Authorization": "r2aq4t9ma69OiC51t"},
                json={"url": url}
            )
            
            log.info(f"[YouTube] API Response Status: {response.status}")
            data = await response.json()
            log.info(f"[YouTube] API Response Data: {data}")
            
            return YouTubeInfo(**data)

        except Exception as e:
            log.error(f"[YouTube] Download failed: {str(e)}")
            raise

    async def dispatch(self, ctx: Context, data: YouTubeInfo) -> Optional[Message]:
        log.info(f"[YouTube] Dispatching content type: {data.type}")
        
        if not data.success:
            return await ctx.warn("Failed to process YouTube content")

        embed = Embed(
            title=data.metadata.title,
            url=ctx.message.content,
            timestamp=datetime.now(),
        )
        
        if data.metadata.uploader:
            embed.set_author(name=data.metadata.uploader)

        if data.metadata.stats:
            stats = data.metadata.stats
            embed.set_footer(
                text=f"❤️ {stats.likes:,} 👀 {stats.views:,} 💬 {stats.comments:,}"
            )

        if data.url:
            async with self.bot.session.get(data.url) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to download video")
                
                video_data = await resp.read()
                return await ctx.send(
                    embed=embed if ctx.settings.reposter_embed else None,
                    file=File(
                        BytesIO(video_data),
                        filename=f"Evict{self.name}{token_urlsafe(4)}.mp4",
                    ),
                    no_reference=ctx.settings.reposter_delete,
                )
