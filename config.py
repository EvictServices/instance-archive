import os
from dotenv import load_dotenv

load_dotenv()

# THE OPENAI KEY IS NOT TO BE USED BY ANYONE OTHER THAN THE BOT. I MONITOR THE API USAGE DAILY.

class DISCORD:
    """
    Main bot connection class.
    """
    TOKEN: str = os.getenv("DISCORD_TOKEN")
    PUBLIC_KEY: str = "106c561c9e3de75150aa63a7f7cf28ab136ce6bae16a2b5cd2f0afec72af52b9"
    CLIENT_ID: str = os.getenv("DISCORD_CLIENT_ID")
    CLIENT_SECRET: str = os.getenv("DISCORD_CLIENT_SECRET")
    REDIRECT_URI: str = "https://x.X.sh/login"


class CLIENT:
    """
    Main client class.
    """
    PREFIX: str = os.getenv("BOT_PREFIX", ";")
    DESCRIPTION: str | None = None
    OWNER_IDS: list[int] = [
        598125772754124823,
        930383131863842816,
        1272545050102071460,
        1332327503062106154
    ]
    SUPPORT_URL: str = "https://discord.gg/evict"
    INVITE_URL: str = (
        "https://discord.com/oauth2/authorize?client_id=1203514684326805524&permissions=8&scope=bot"
    )
    TWITCH_URL: str = (
        "https://twitch.tv/evictbot"
    )
    BACKEND_HOST: str = "api.evict.bot"
    FRONTEND_HOST: str = "evict.bot"
    WARP: str = "http://127.1:40000"


class LOGGER:
    """
    Change the bots logging channels.
    """
    MAIN_GUILD: int = 892675627373699072
    LOGGING_GUILD: int = 1318473085032071178
    TESTING_GUILD: int = ""
    COMMAND_LOGGER: int = 1319467001051090956
    STATUS_LOGGER: int = 1319470623071670295
    GUILD_JOIN_LOGGER: int = 1319466970474610708


class LAVALINK:
    """
    Lavalink authentication node.
    """
    NODE_COUNT: int = 1
    HOST: str = "127.0.0.1"
    PORT: int = 2333
    PASSWORD: str = "youshallnotpass"

class POSTHOG:
    """
    PostHog analytics class.
    """
    API_KEY: str = "phc_9CO68Be49weXo25XXmg0CY7wwFLl2HMzW5qoXWdH1J8"
    HOST: str = "https://us.i.posthog.com"

class STATUS:
    """
    Main IPC authentication class.
    """
    HOST: str = "0.0.0.0"
    PORT: int = 6000

class DATABASE:
    """
    Postgres authentication class.
    """
    DSN: str = os.getenv("DATABASE_DSN")

class REDIS:
    """
    Redis authentication class.
    """
    DB: int = 0
    HOST: str = "localhost"
    PORT: int = 6380
    PASSWORD: str = "eFbs45tE0jCLdA5UU07sh9t"

class AUTHORIZATION:
    """
    API keys for various services.
    """
    FNBR: str = "20490584-82aa-4ac3-8831-73d411d7c3d2"
    CLEVER: str = "CC9db9SL-aX3lL2t0GLBfTTkTug"
    WOLFRAM: str = "W95RJG-RRUXURP6XY"
    WEATHER: str = "0c5b47ed5774413c90b155456223004"
    OSU: str = "69c45249d9df06a933041e8da565392b458f80fc"
    LASTFM: list[str] = [
        "bc84a74e4b3cf9eb040fbeaab4071df5",
        "4210d59afeeb6c350442d7141747704c",
    ]
    SOUNDCLOUD: str = "OAuth 2-292593-994587358-Af8VbLnc6zIplJ"
    GEMINI: str = "AIzaSyCjgGH83OyUblhY4JHMQFJ5j3UVH5ztkaA"
    KRAKEN: str = "NjEyZTQyMzIwZTE4OWQ3OeLx-wiasK1ZCCKRbrPE13dJfF64AetJ4HvFef4w9c0s"
    FERNET_KEY: str = "0GKftpvX45aoHDZ1p4_OgYuaoPnI2TEPnJGeuvPjXjg="
    PIPED_API: str = "pipedapi.adminforge.de"
    PUBSUB_KEY: str = "qXhjfaXxt2e_2WrkWwx3QR"
    IPC_KEY: str = "ZguzxNhhtz4PG6zOaD0"
    JEYY_API: str = "74PJ0CPO6COJ6C9O6OPJGD1I70OJC.CLR6IORK.lkpD588_z_FMB40-Nl6L1w"
    OPENAI: str = (
     "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"
    )

    class GOOGLE:
        """
        Google API class.
        """
        CX: str = "b7498d486b2d19b97"
        KEY: str = "AIzaSyDHcNBPqv-GpTR6_oyA6EnTyiRXeGUjokI"

    class TWITCH:
        """
        Twitch API class.
        """
        CLIENT_ID: str = "30guvrlrw4lvf3knqsbin99asxdg4t"
        CLIENT_SECRET: str = "pxfuxxo2mn5qebq5xrl8g31ryh91gz"

    class SPOTIFY:
        """
        Spotify API class.
        """
        CLIENT_ID: str = "908846bb106d4190b4cdf5ceb3d1e0e5"
        CLIENT_SECRET: str = "d08df8638ee44bdcbfe6057a5e7ffd78"

    class REDDIT:
        """
        Reddit API class.
        """
        CLIENT_ID: str = "gM_QdMnswc2geCIvlbTkdQ"
        CLIENT_SECRET: str = "sMnPrsejKe5btrGPULuYrVOjMpAXkA"

class EMOJIS:
    """
    Controls the emojis throughout the bot.
    """

    class INTERFACE:
        """
        Changes the emojis on the VoiceMaster Panel.
        """
        LOCK: str = "<:lock:1320338245782999171>"
        UNLOCK: str = "<:unlock:1320338267828260866>"
        GHOST: str = "<:hide:1320338273310212238>"
        REVEAL: str = "<:revealwhite:1320338271707861022>"
        CLAIM: str = "<:claim:1320338274673233920>"
        DISCONNECT: str = "<:hammer:1320439504523231242>"
        ACTIVITY: str = "<:activity:1320439502606434406>"
        INFORMATION: str = "<:information:1320338239139348554>"
        INCREASE: str = "<:plus:1320439497443508286>"
        DECREASE: str = "<:minus:1320439500496703669>"

    class PAGINATOR:
        """
        Changes the emojis on the paginator.
        """
        NEXT: str = "<:right:1263727130370637995>"
        NAVIGATE: str = "<:filter:1263727034798968893>"
        PREVIOUS: str = "<:left:1263727060078035066>"
        CANCEL: str = "<:deny:1263727013433184347>"

    class AUDIO:
        """
        Changes the emojis on the audio panel.
        """
        SKIP: str = "<:skip:1243011308333564006>"
        RESUME: str = "<:resume:1243011309449252864>"
        REPEAT: str = "<:repeat:1243011309843382285>"
        PREVIOUS: str = "<:previous:1243011310942162990>"
        PAUSE: str = "<:pause:1243011311860842627>"
        QUEUE: str = "<:queue:1243011313006022698>"
        REPEAT_TRACK: str = "<:repeat_track:1243011313660334101>"

    class ANTINUKE:
        """
        Changes the emojis on the Antinuke-Config command.
        """
        ENABLE = "<:enable:1320338287331770400>"
        DISABLE = "<:disable:1320338285234749450>"

    class BADGES:
        """
        Changes the emojis that show on badges.
        """
        HYPESQUAD_BRILLIANCE: str = "<:hypesquad_brillance:1289500479117590548>"
        BOOST: str = "<:booster:1263727083310415885>"
        STAFF: str = "<:staff:1263729127199084645>"
        VERIFIED_BOT_DEVELOPER: str = "<:earlydev:1263727027022860330>"
        SERVER_OWNER: str = "<a:crown:1263741407969939467>"
        HYPESQUAD_BRAVERY: str = "<:hypesquad_bravery:1289500873830961279>"
        PARTNER: str = "<:partner:1263727124066340978>"
        HYPESQUAD_BALANCE: str = "<:hypesquad_balance:1289500688052785222>"
        EARLY_SUPPORTER: str = "<:early:1263727021318602783>"
        HYPESQUAD: str = "<:hypesquad:1289501069449236572>"
        BUG_HUNTER_LEVEL_2: str = "<:buggold:1263726960882876456>"
        CERTIFIED_MODERATOR: str = "<:certified_moderator:1289501261640765462>"
        NITRO: str = "<:nitro:1289499927117828106>"
        BUG_HUNTER: str = "<:bugreg:1263726968377966642>"
        ACTIVE_DEVELOPER: str = "<:activedev:1263726943048695828>"

    class CONTEXT:
        """
        Changes the emojis on context.
        """
        APPROVE = "<:approve:1320338298417184820>"
        DENY = "<:deny:1320338232239718512>"
        WARN = "<:warn:1320338261343993917>"
        FILTER = "<:filter:1263727034798968893>"
        LEFT = "<:left:1263727060078035066>"
        RIGHT = "<:right:1263727130370637995>"
        JUUL = "<:juul:1320437668861181973>"
        NO_JUUL = "<:no_juul:1320441293427707934>"

    class SOCIAL:
        """
        Changes the emojis on social commands.
        """
        DISCORD = "<:discord:1290120978306695281>"
        GITHUB = "<:github:1289507143887884383>"
        WEBSITE = "<:link:1290119682103316520>"

    class TICKETS:
        """
        Changes the emojis on tickets.
        """
        TRASH = "<:trash:1263727144832602164>"
    
    class ECONOMY:
        """
        Changes the emojis on the economy commands.
        """
        PURPLE_DEVIL = "<:purple_devil:1309072250107854911>"
        WHITE_POWEDER = "<:white_powder:1309072260551675904>"
        OXY = "<:oxy:1309072269565235200>"
        METH = "<:meth:1309072276683100183>"
        SHROOMS = "<:shroom:1309072285264646194>"
        HEROIN = "<:heroin:1309072311047159818>"
        ACID = "<:acid:1309072318684729356>"
        UP = "<:econ_up:1309071103397859398>"
        DOWN = "<:econ_down:1309071092681408553>"

class COLORS:
    """
    Changes the colors on context outputs.
    """
    NEUTRAL = 0xCCCCFF
    APPROVE = 0xCCCCFF
    WARN = 0xCCCCFF
    DENY = 0xCCCCFF

class ECONOMY:
    """
    Changes the chances on economy commands.
    """
    CHANCES = {
        "roll": {"percentage": 50.0, "total": 100.0},
        "coinflip": {"percentage": 50.0, "total": 100.0},
        "gamble": {"percentage": 20.0, "total": 100.0},
        "supergamble": {"percentage": 50.0, "total": 1000.0},
    }

class RATELIMITS:
    """
    Changes the rate limits on the bot.
    """
    PER_10S = 20
    PER_30S = 35
    PER_1M = 65