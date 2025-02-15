--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2 (Debian 17.2-1.pgdg120+1)
-- Dumped by pg_dump version 17.2 (Debian 17.2-1.pgdg120+1)
-- Date: 02/15/2025

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: alerts; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA alerts;


ALTER SCHEMA alerts OWNER TO admin;

--
-- Name: audio; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA audio;


ALTER SCHEMA audio OWNER TO admin;

--
-- Name: auto; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA auto;


ALTER SCHEMA auto OWNER TO admin;

--
-- Name: commands; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA commands;


ALTER SCHEMA commands OWNER TO admin;

--
-- Name: counting; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA counting;


ALTER SCHEMA counting OWNER TO admin;

--
-- Name: disboard; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA disboard;


ALTER SCHEMA disboard OWNER TO admin;

--
-- Name: family; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA family;


ALTER SCHEMA family OWNER TO admin;

--
-- Name: feeds; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA feeds;


ALTER SCHEMA feeds OWNER TO admin;

--
-- Name: fortnite; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA fortnite;


ALTER SCHEMA fortnite OWNER TO admin;

--
-- Name: fun; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA fun;


ALTER SCHEMA fun OWNER TO admin;

--
-- Name: history; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA history;


ALTER SCHEMA history OWNER TO admin;

--
-- Name: invoke_history; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA invoke_history;


ALTER SCHEMA invoke_history OWNER TO admin;

--
-- Name: joindm; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA joindm;


ALTER SCHEMA joindm OWNER TO admin;

--
-- Name: lastfm; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA lastfm;


ALTER SCHEMA lastfm OWNER TO admin;

--
-- Name: level; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA level;


ALTER SCHEMA level OWNER TO admin;

--
-- Name: music; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA music;


ALTER SCHEMA music OWNER TO admin;

--
-- Name: reposters; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA reposters;


ALTER SCHEMA reposters OWNER TO admin;

--
-- Name: reskin; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA reskin;


ALTER SCHEMA reskin OWNER TO admin;

--
-- Name: snipe; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA snipe;


ALTER SCHEMA snipe OWNER TO admin;

--
-- Name: spam; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA spam;


ALTER SCHEMA spam OWNER TO admin;

--
-- Name: statistics; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA statistics;


ALTER SCHEMA statistics OWNER TO admin;

--
-- Name: stats; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA stats;


ALTER SCHEMA stats OWNER TO admin;

--
-- Name: streaks; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA streaks;


ALTER SCHEMA streaks OWNER TO admin;

--
-- Name: ticket; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA ticket;


ALTER SCHEMA ticket OWNER TO admin;

--
-- Name: timer; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA timer;


ALTER SCHEMA timer OWNER TO admin;

--
-- Name: track; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA track;


ALTER SCHEMA track OWNER TO admin;

--
-- Name: transcribe; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA transcribe;


ALTER SCHEMA transcribe OWNER TO admin;

--
-- Name: verification; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA verification;


ALTER SCHEMA verification OWNER TO admin;

--
-- Name: voice; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA voice;


ALTER SCHEMA voice OWNER TO admin;

--
-- Name: voicemaster; Type: SCHEMA; Schema: -; Owner: admin
--

CREATE SCHEMA voicemaster;


ALTER SCHEMA voicemaster OWNER TO admin;

--
-- Name: citext; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;


--
-- Name: EXTENSION citext; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION citext IS 'data type for case-insensitive character strings';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: admin
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: twitch; Type: TABLE; Schema: alerts; Owner: admin
--

CREATE TABLE alerts.twitch (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    twitch_id bigint NOT NULL,
    twitch_login text NOT NULL,
    last_stream_id bigint,
    role_id bigint,
    template text
);


ALTER TABLE alerts.twitch OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: audio; Owner: admin
--

CREATE TABLE audio.config (
    guild_id bigint NOT NULL,
    volume integer NOT NULL
);


ALTER TABLE audio.config OWNER TO admin;

--
-- Name: statistics; Type: TABLE; Schema: audio; Owner: admin
--

CREATE TABLE audio.statistics (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    tracks_played integer DEFAULT 0 NOT NULL
);


ALTER TABLE audio.statistics OWNER TO admin;

--
-- Name: media; Type: TABLE; Schema: auto; Owner: admin
--

CREATE TABLE auto.media (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    type text NOT NULL,
    category text NOT NULL,
    CONSTRAINT media_type_check CHECK ((type = ANY (ARRAY['banner'::text, 'pfp'::text])))
);


ALTER TABLE auto.media OWNER TO admin;

--
-- Name: media_id_seq; Type: SEQUENCE; Schema: auto; Owner: admin
--

CREATE SEQUENCE auto.media_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE auto.media_id_seq OWNER TO admin;

--
-- Name: media_id_seq; Type: SEQUENCE OWNED BY; Schema: auto; Owner: admin
--

ALTER SEQUENCE auto.media_id_seq OWNED BY auto.media.id;


--
-- Name: disabled; Type: TABLE; Schema: commands; Owner: admin
--

CREATE TABLE commands.disabled (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    command text NOT NULL
);


ALTER TABLE commands.disabled OWNER TO admin;

--
-- Name: ignore; Type: TABLE; Schema: commands; Owner: admin
--

CREATE TABLE commands.ignore (
    guild_id bigint NOT NULL,
    target_id bigint NOT NULL
);


ALTER TABLE commands.ignore OWNER TO admin;

--
-- Name: restricted; Type: TABLE; Schema: commands; Owner: admin
--

CREATE TABLE commands.restricted (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    command text NOT NULL
);


ALTER TABLE commands.restricted OWNER TO admin;

--
-- Name: usage; Type: TABLE; Schema: commands; Owner: admin
--

CREATE TABLE commands.usage (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    user_id bigint NOT NULL,
    command text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE commands.usage OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: counting; Owner: admin
--

CREATE TABLE counting.config (
    guild_id bigint NOT NULL,
    channel_id bigint,
    current_count integer DEFAULT 0,
    high_score integer DEFAULT 0,
    safe_mode boolean DEFAULT false,
    allow_fails boolean DEFAULT false,
    last_user_id bigint,
    success_emoji text DEFAULT '✅'::text,
    fail_emoji text DEFAULT '❌'::text
);


ALTER TABLE counting.config OWNER TO admin;

--
-- Name: bump; Type: TABLE; Schema: disboard; Owner: admin
--

CREATE TABLE disboard.bump (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    bumped_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE disboard.bump OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: disboard; Owner: admin
--

CREATE TABLE disboard.config (
    guild_id bigint NOT NULL,
    status boolean DEFAULT true NOT NULL,
    channel_id bigint,
    last_channel_id bigint,
    last_user_id bigint,
    message text,
    thank_message text,
    next_bump timestamp with time zone
);


ALTER TABLE disboard.config OWNER TO admin;

--
-- Name: marriages; Type: TABLE; Schema: family; Owner: admin
--

CREATE TABLE family.marriages (
    user_id bigint NOT NULL,
    partner_id bigint NOT NULL,
    marriage_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    active boolean DEFAULT true
);


ALTER TABLE family.marriages OWNER TO admin;

--
-- Name: members; Type: TABLE; Schema: family; Owner: admin
--

CREATE TABLE family.members (
    user_id bigint NOT NULL,
    related_id bigint NOT NULL,
    relationship text
);


ALTER TABLE family.members OWNER TO admin;

--
-- Name: profiles; Type: TABLE; Schema: family; Owner: admin
--

CREATE TABLE family.profiles (
    user_id bigint NOT NULL,
    bio text
);


ALTER TABLE family.profiles OWNER TO admin;

--
-- Name: instagram; Type: TABLE; Schema: feeds; Owner: admin
--

CREATE TABLE feeds.instagram (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    instagram_id bigint NOT NULL,
    instagram_name text NOT NULL,
    template text
);


ALTER TABLE feeds.instagram OWNER TO admin;

--
-- Name: pinterest; Type: TABLE; Schema: feeds; Owner: admin
--

CREATE TABLE feeds.pinterest (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    pinterest_id text NOT NULL,
    pinterest_name text NOT NULL,
    board text,
    board_id text,
    embeds boolean DEFAULT true NOT NULL,
    only_new boolean DEFAULT false NOT NULL
);


ALTER TABLE feeds.pinterest OWNER TO admin;

--
-- Name: reddit; Type: TABLE; Schema: feeds; Owner: admin
--

CREATE TABLE feeds.reddit (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    subreddit_name text NOT NULL
);


ALTER TABLE feeds.reddit OWNER TO admin;

--
-- Name: soundcloud; Type: TABLE; Schema: feeds; Owner: admin
--

CREATE TABLE feeds.soundcloud (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    soundcloud_id bigint NOT NULL,
    soundcloud_name text NOT NULL,
    template text
);


ALTER TABLE feeds.soundcloud OWNER TO admin;

--
-- Name: tiktok; Type: TABLE; Schema: feeds; Owner: admin
--

CREATE TABLE feeds.tiktok (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    tiktok_id bigint NOT NULL,
    tiktok_name text NOT NULL,
    template text
);


ALTER TABLE feeds.tiktok OWNER TO admin;

--
-- Name: twitter; Type: TABLE; Schema: feeds; Owner: admin
--

CREATE TABLE feeds.twitter (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    twitter_id bigint NOT NULL,
    twitter_name text NOT NULL,
    template text,
    color text
);


ALTER TABLE feeds.twitter OWNER TO admin;

--
-- Name: youtube; Type: TABLE; Schema: feeds; Owner: admin
--

CREATE TABLE feeds.youtube (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    youtube_id text NOT NULL,
    youtube_name text NOT NULL,
    template text,
    shorts boolean DEFAULT false NOT NULL
);


ALTER TABLE feeds.youtube OWNER TO admin;

--
-- Name: authorization; Type: TABLE; Schema: fortnite; Owner: admin
--

CREATE TABLE fortnite."authorization" (
    user_id bigint NOT NULL,
    display_name text NOT NULL,
    account_id text NOT NULL,
    access_token text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    refresh_token text NOT NULL
);


ALTER TABLE fortnite."authorization" OWNER TO admin;

--
-- Name: reminder; Type: TABLE; Schema: fortnite; Owner: admin
--

CREATE TABLE fortnite.reminder (
    user_id bigint NOT NULL,
    item_id text NOT NULL,
    item_name text NOT NULL,
    item_type text NOT NULL
);


ALTER TABLE fortnite.reminder OWNER TO admin;

--
-- Name: rotation; Type: TABLE; Schema: fortnite; Owner: admin
--

CREATE TABLE fortnite.rotation (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message text
);


ALTER TABLE fortnite.rotation OWNER TO admin;

--
-- Name: wyr_channels; Type: TABLE; Schema: fun; Owner: admin
--

CREATE TABLE fun.wyr_channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    rating character varying(4) DEFAULT 'pg13'::character varying NOT NULL
);


ALTER TABLE fun.wyr_channels OWNER TO admin;

--
-- Name: moderation; Type: TABLE; Schema: history; Owner: admin
--

CREATE TABLE history.moderation (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    reason text NOT NULL,
    action text DEFAULT 'Unknown'::text NOT NULL,
    duration interval,
    guild_id bigint DEFAULT 0 NOT NULL,
    case_id integer DEFAULT 0 NOT NULL
);


ALTER TABLE history.moderation OWNER TO admin;

--
-- Name: moderation_id_seq; Type: SEQUENCE; Schema: history; Owner: admin
--

CREATE SEQUENCE history.moderation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE history.moderation_id_seq OWNER TO admin;

--
-- Name: moderation_id_seq; Type: SEQUENCE OWNED BY; Schema: history; Owner: admin
--

ALTER SEQUENCE history.moderation_id_seq OWNED BY history.moderation.id;


--
-- Name: commands; Type: TABLE; Schema: invoke_history; Owner: admin
--

CREATE TABLE invoke_history.commands (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    command_name text NOT NULL,
    category text NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    guild_id bigint NOT NULL
);


ALTER TABLE invoke_history.commands OWNER TO admin;

--
-- Name: commands_id_seq; Type: SEQUENCE; Schema: invoke_history; Owner: admin
--

CREATE SEQUENCE invoke_history.commands_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE invoke_history.commands_id_seq OWNER TO admin;

--
-- Name: commands_id_seq; Type: SEQUENCE OWNED BY; Schema: invoke_history; Owner: admin
--

ALTER SEQUENCE invoke_history.commands_id_seq OWNED BY invoke_history.commands.id;


--
-- Name: config; Type: TABLE; Schema: joindm; Owner: admin
--

CREATE TABLE joindm.config (
    guild_id bigint NOT NULL,
    message text,
    enabled boolean DEFAULT false
);


ALTER TABLE joindm.config OWNER TO admin;

--
-- Name: albums; Type: TABLE; Schema: lastfm; Owner: admin
--

CREATE TABLE lastfm.albums (
    user_id bigint NOT NULL,
    username text NOT NULL,
    artist public.citext NOT NULL,
    album public.citext NOT NULL,
    plays bigint NOT NULL
);


ALTER TABLE lastfm.albums OWNER TO admin;

--
-- Name: artists; Type: TABLE; Schema: lastfm; Owner: admin
--

CREATE TABLE lastfm.artists (
    user_id bigint NOT NULL,
    username text NOT NULL,
    artist public.citext NOT NULL,
    plays bigint NOT NULL
);


ALTER TABLE lastfm.artists OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: lastfm; Owner: admin
--

CREATE TABLE lastfm.config (
    user_id bigint NOT NULL,
    username public.citext NOT NULL,
    color bigint,
    command text,
    reactions text[] DEFAULT '{}'::text[] NOT NULL,
    embed_mode text DEFAULT 'default'::text NOT NULL,
    last_indexed timestamp with time zone DEFAULT now() NOT NULL,
    access_token text,
    web_authentication boolean DEFAULT false
);


ALTER TABLE lastfm.config OWNER TO admin;

--
-- Name: crowns; Type: TABLE; Schema: lastfm; Owner: admin
--

CREATE TABLE lastfm.crowns (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    artist public.citext NOT NULL,
    claimed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE lastfm.crowns OWNER TO admin;

--
-- Name: hidden; Type: TABLE; Schema: lastfm; Owner: admin
--

CREATE TABLE lastfm.hidden (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE lastfm.hidden OWNER TO admin;

--
-- Name: tracks; Type: TABLE; Schema: lastfm; Owner: admin
--

CREATE TABLE lastfm.tracks (
    user_id bigint NOT NULL,
    username text NOT NULL,
    artist public.citext NOT NULL,
    track public.citext NOT NULL,
    plays bigint NOT NULL
);


ALTER TABLE lastfm.tracks OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: level; Owner: admin
--

CREATE TABLE level.config (
    guild_id bigint NOT NULL,
    status boolean DEFAULT true NOT NULL,
    cooldown integer DEFAULT 60 NOT NULL,
    max_level integer DEFAULT 0 NOT NULL,
    stack_roles boolean DEFAULT true NOT NULL,
    formula_multiplier double precision DEFAULT 1 NOT NULL,
    xp_multiplier double precision DEFAULT 1 NOT NULL,
    xp_min integer DEFAULT 15 NOT NULL,
    xp_max integer DEFAULT 40 NOT NULL,
    effort_status boolean DEFAULT false NOT NULL,
    effort_text bigint DEFAULT 25 NOT NULL,
    effort_image bigint DEFAULT 3 NOT NULL,
    effort_booster bigint DEFAULT 10 NOT NULL
);


ALTER TABLE level.config OWNER TO admin;

--
-- Name: member; Type: TABLE; Schema: level; Owner: admin
--

CREATE TABLE level.member (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    xp integer DEFAULT 0 NOT NULL,
    level integer DEFAULT 0 NOT NULL,
    total_xp integer DEFAULT 0 NOT NULL,
    last_message timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE level.member OWNER TO admin;

--
-- Name: notification; Type: TABLE; Schema: level; Owner: admin
--

CREATE TABLE level.notification (
    guild_id bigint NOT NULL,
    channel_id bigint,
    dm boolean DEFAULT false NOT NULL,
    template text
);


ALTER TABLE level.notification OWNER TO admin;

--
-- Name: role; Type: TABLE; Schema: level; Owner: admin
--

CREATE TABLE level.role (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    level integer NOT NULL
);


ALTER TABLE level.role OWNER TO admin;

--
-- Name: history; Type: TABLE; Schema: music; Owner: admin
--

CREATE TABLE music.history (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    title text NOT NULL,
    artist text NOT NULL,
    duration integer NOT NULL,
    thumbnail text NOT NULL,
    uri text NOT NULL,
    played_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE music.history OWNER TO admin;

--
-- Name: history_id_seq; Type: SEQUENCE; Schema: music; Owner: admin
--

CREATE SEQUENCE music.history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE music.history_id_seq OWNER TO admin;

--
-- Name: history_id_seq; Type: SEQUENCE OWNED BY; Schema: music; Owner: admin
--

ALTER SEQUENCE music.history_id_seq OWNED BY music.history.id;


--
-- Name: playlist_tracks; Type: TABLE; Schema: music; Owner: admin
--

CREATE TABLE music.playlist_tracks (
    id integer NOT NULL,
    playlist_id integer,
    title text NOT NULL,
    artist text NOT NULL,
    duration integer NOT NULL,
    thumbnail text NOT NULL,
    uri text NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    added_by bigint NOT NULL
);


ALTER TABLE music.playlist_tracks OWNER TO admin;

--
-- Name: playlist_tracks_id_seq; Type: SEQUENCE; Schema: music; Owner: admin
--

CREATE SEQUENCE music.playlist_tracks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE music.playlist_tracks_id_seq OWNER TO admin;

--
-- Name: playlist_tracks_id_seq; Type: SEQUENCE OWNED BY; Schema: music; Owner: admin
--

ALTER SEQUENCE music.playlist_tracks_id_seq OWNED BY music.playlist_tracks.id;


--
-- Name: playlists; Type: TABLE; Schema: music; Owner: admin
--

CREATE TABLE music.playlists (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    name text NOT NULL,
    thumbnail text DEFAULT 'https://img.freepik.com/premium-photo/treble-clef-circle-musical-notes-black-background-design-3d-illustration_116124-10456.jpg?semt=ais'::text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE music.playlists OWNER TO admin;

--
-- Name: playlists_id_seq; Type: SEQUENCE; Schema: music; Owner: admin
--

CREATE SEQUENCE music.playlists_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE music.playlists_id_seq OWNER TO admin;

--
-- Name: playlists_id_seq; Type: SEQUENCE OWNED BY; Schema: music; Owner: admin
--

ALTER SEQUENCE music.playlists_id_seq OWNED BY music.playlists.id;


--
-- Name: afk; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.afk (
    user_id bigint NOT NULL,
    status text DEFAULT 'AFK'::text NOT NULL,
    left_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.afk OWNER TO admin;

--
-- Name: aliases; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.aliases (
    guild_id bigint NOT NULL,
    name text NOT NULL,
    invoke text NOT NULL,
    command text NOT NULL
);


ALTER TABLE public.aliases OWNER TO admin;

--
-- Name: antinuke; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.antinuke (
    guild_id bigint NOT NULL,
    whitelist bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    trusted_admins bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    bot boolean DEFAULT false NOT NULL,
    ban jsonb,
    kick jsonb,
    role jsonb,
    channel jsonb,
    webhook jsonb,
    emoji jsonb
);


ALTER TABLE public.antinuke OWNER TO admin;

--
-- Name: antiraid; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.antiraid (
    guild_id bigint NOT NULL,
    locked boolean DEFAULT false NOT NULL,
    joins jsonb,
    mentions jsonb,
    avatar jsonb,
    browser jsonb
);


ALTER TABLE public.antiraid OWNER TO admin;

--
-- Name: auto_role; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.auto_role (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    action text NOT NULL,
    delay integer
);


ALTER TABLE public.auto_role OWNER TO admin;

--
-- Name: autokick; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.autokick (
    user_id bigint,
    guild_id bigint,
    reason text,
    author_id bigint
);


ALTER TABLE public.autokick OWNER TO admin;

--
-- Name: backup; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.backup (
    key text NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    data text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.backup OWNER TO admin;

--
-- Name: birthdays; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.birthdays (
    user_id bigint NOT NULL,
    birthday timestamp without time zone NOT NULL
);


ALTER TABLE public.birthdays OWNER TO admin;

--
-- Name: blacklist; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.blacklist (
    user_id bigint NOT NULL,
    information text
);


ALTER TABLE public.blacklist OWNER TO admin;

--
-- Name: blunt; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.blunt (
    guild_id bigint NOT NULL,
    user_id bigint,
    hits bigint DEFAULT 0,
    passes bigint DEFAULT 0,
    members jsonb[] DEFAULT '{}'::jsonb[]
);


ALTER TABLE public.blunt OWNER TO admin;

--
-- Name: boost_message; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.boost_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    delete_after integer
);


ALTER TABLE public.boost_message OWNER TO admin;

--
-- Name: booster_role; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.booster_role (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    role_id bigint NOT NULL,
    shared boolean
);


ALTER TABLE public.booster_role OWNER TO admin;

--
-- Name: boosters_lost; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.boosters_lost (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    lasted_for interval NOT NULL,
    ended_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.boosters_lost OWNER TO admin;

--
-- Name: bot_activity; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.bot_activity (
    activity_type text DEFAULT 'streaming'::text NOT NULL,
    activity_text text DEFAULT '🔗 discord.gg/evict'::text NOT NULL,
    activity_url text DEFAULT 'https://twitch.tv/evictbot'::text NOT NULL
);


ALTER TABLE public.bot_activity OWNER TO admin;

--
-- Name: cases; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.cases (
    guild_id bigint,
    count integer
);


ALTER TABLE public.cases OWNER TO admin;

--
-- Name: clownboard; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.clownboard (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    self_clown boolean DEFAULT true NOT NULL,
    threshold integer DEFAULT 3 NOT NULL,
    emoji text DEFAULT '🤡'::text NOT NULL
);


ALTER TABLE public.clownboard OWNER TO admin;

--
-- Name: clownboard_entry; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.clownboard_entry (
    guild_id bigint NOT NULL,
    clown_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    emoji text NOT NULL
);


ALTER TABLE public.clownboard_entry OWNER TO admin;

--
-- Name: confess; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.confess (
    guild_id bigint,
    channel_id bigint,
    confession integer
);


ALTER TABLE public.confess OWNER TO admin;

--
-- Name: confess_members; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.confess_members (
    guild_id bigint,
    user_id bigint,
    confession integer
);


ALTER TABLE public.confess_members OWNER TO admin;

--
-- Name: confess_mute; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.confess_mute (
    guild_id bigint,
    user_id bigint
);


ALTER TABLE public.confess_mute OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.config (
    guild_id bigint NOT NULL,
    prefix text DEFAULT ','::text,
    baserole bigint,
    voicemaster jsonb DEFAULT '{}'::jsonb,
    mod_log bigint,
    invoke jsonb DEFAULT '{}'::jsonb,
    lock_ignore jsonb[] DEFAULT '{}'::jsonb[],
    reskin jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.config OWNER TO admin;

--
-- Name: counter; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.counter (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    option text NOT NULL,
    last_update timestamp with time zone DEFAULT now() NOT NULL,
    rate_limited_until timestamp with time zone
);


ALTER TABLE public.counter OWNER TO admin;

--
-- Name: crypto; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.crypto (
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    transaction_id text NOT NULL,
    transaction_type text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.crypto OWNER TO admin;

--
-- Name: dalle_credits; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.dalle_credits (
    user_id bigint NOT NULL,
    credits numeric(10,2) NOT NULL,
    last_reset timestamp without time zone NOT NULL
);


ALTER TABLE public.dalle_credits OWNER TO admin;

--
-- Name: donators; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.donators (
    user_id bigint
);


ALTER TABLE public.donators OWNER TO admin;

--
-- Name: earnings; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.earnings (
    user_id bigint NOT NULL,
    h0 double precision DEFAULT 0,
    h1 double precision DEFAULT 0,
    h2 double precision DEFAULT 0,
    h3 double precision DEFAULT 0,
    h4 double precision DEFAULT 0,
    h5 double precision DEFAULT 0,
    h6 double precision DEFAULT 0,
    h7 double precision DEFAULT 0,
    h8 double precision DEFAULT 0,
    h9 double precision DEFAULT 0,
    h10 double precision DEFAULT 0,
    h11 double precision DEFAULT 0,
    h12 double precision DEFAULT 0,
    h13 double precision DEFAULT 0,
    h14 double precision DEFAULT 0,
    h15 double precision DEFAULT 0,
    h16 double precision DEFAULT 0,
    h17 double precision DEFAULT 0,
    h18 double precision DEFAULT 0,
    h19 double precision DEFAULT 0,
    h20 double precision DEFAULT 0,
    h21 double precision DEFAULT 0,
    h22 double precision DEFAULT 0,
    h23 double precision DEFAULT 0
);


ALTER TABLE public.earnings OWNER TO admin;

--
-- Name: economy; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.economy (
    user_id bigint NOT NULL,
    balance double precision NOT NULL,
    bank double precision NOT NULL,
    earnings double precision DEFAULT 0,
    wins integer DEFAULT 0,
    total integer DEFAULT 0
);


ALTER TABLE public.economy OWNER TO admin;

--
-- Name: economy_roleshop; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.economy_roleshop (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    price bigint,
    description text
);


ALTER TABLE public.economy_roleshop OWNER TO admin;

--
-- Name: employee_stats; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.employee_stats (
    business_id bigint NOT NULL,
    employee_id bigint NOT NULL,
    work_count integer DEFAULT 0,
    total_earned bigint DEFAULT 0
);


ALTER TABLE public.employee_stats OWNER TO admin;

--
-- Name: fake_permissions; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.fake_permissions (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    permission text NOT NULL
);


ALTER TABLE public.fake_permissions OWNER TO admin;

--
-- Name: feedback; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.feedback (
    user_id bigint NOT NULL,
    message text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.feedback OWNER TO admin;

--
-- Name: gallery; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.gallery (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.gallery OWNER TO admin;

--
-- Name: giveaway; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.giveaway (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    prize text NOT NULL,
    emoji text NOT NULL,
    winners integer NOT NULL,
    ended boolean DEFAULT false NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.giveaway OWNER TO admin;

--
-- Name: gnames; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.gnames (
    guild_id bigint NOT NULL,
    name text NOT NULL,
    changed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.gnames OWNER TO admin;

--
-- Name: goodbye_message; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.goodbye_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    delete_after integer
);


ALTER TABLE public.goodbye_message OWNER TO admin;

--
-- Name: guildblacklist; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.guildblacklist (
    guild_id bigint NOT NULL,
    information text
);


ALTER TABLE public.guildblacklist OWNER TO admin;

--
-- Name: highlights; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.highlights (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    word text NOT NULL
);


ALTER TABLE public.highlights OWNER TO admin;

--
-- Name: instance_info; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.instance_info (
    instance_id integer NOT NULL,
    owner_id bigint NOT NULL,
    owner_username text NOT NULL,
    owner_email text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.instance_info OWNER TO admin;

--
-- Name: instance_info_instance_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.instance_info_instance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.instance_info_instance_id_seq OWNER TO admin;

--
-- Name: instance_info_instance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.instance_info_instance_id_seq OWNED BY public.instance_info.instance_id;


--
-- Name: inventory; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.inventory (
    user_id bigint NOT NULL,
    item text NOT NULL,
    amount integer NOT NULL
);


ALTER TABLE public.inventory OWNER TO admin;

--
-- Name: jail; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.jail (
    guild_id bigint,
    user_id bigint,
    roles text
);


ALTER TABLE public.jail OWNER TO admin;

--
-- Name: logging; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.logging (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    events integer NOT NULL
);


ALTER TABLE public.logging OWNER TO admin;

--
-- Name: mod; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.mod (
    guild_id bigint NOT NULL,
    channel_id bigint,
    jail_id bigint,
    role_id bigint,
    dm_enabled boolean DEFAULT true,
    dm_ban text,
    dm_kick text,
    dm_mute text,
    dm_unban text,
    dm_jail text,
    dm_unjail text,
    dm_unmute text,
    dm_warn text,
    dm_timeout text,
    dm_untimeout text
);


ALTER TABLE public.mod OWNER TO admin;

--
-- Name: name_history; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.name_history (
    user_id bigint NOT NULL,
    username text NOT NULL,
    is_nickname boolean DEFAULT false NOT NULL,
    is_hidden boolean DEFAULT false NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.name_history OWNER TO admin;

--
-- Name: payment; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.payment (
    guild_id bigint NOT NULL,
    customer_id bigint NOT NULL,
    method text NOT NULL,
    amount bigint NOT NULL,
    transfers integer DEFAULT 0 NOT NULL,
    paid_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.payment OWNER TO admin;

--
-- Name: pingonjoin; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.pingonjoin (
    channel_id bigint,
    guild_id bigint
);


ALTER TABLE public.pingonjoin OWNER TO admin;

--
-- Name: prefix; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.prefix (
    guild_id bigint,
    prefix text
);


ALTER TABLE public.prefix OWNER TO admin;

--
-- Name: prefixex; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.prefixex (
    guild_id bigint,
    prefix text
);


ALTER TABLE public.prefixex OWNER TO admin;

--
-- Name: publisher; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.publisher (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.publisher OWNER TO admin;

--
-- Name: pubsub; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.pubsub (
    id text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.pubsub OWNER TO admin;

--
-- Name: quoter; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.quoter (
    guild_id bigint NOT NULL,
    channel_id bigint,
    emoji text,
    embeds boolean DEFAULT true NOT NULL
);


ALTER TABLE public.quoter OWNER TO admin;

--
-- Name: reaction_role; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.reaction_role (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    role_id bigint NOT NULL,
    emoji text NOT NULL
);


ALTER TABLE public.reaction_role OWNER TO admin;

--
-- Name: reaction_trigger; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.reaction_trigger (
    guild_id bigint NOT NULL,
    trigger public.citext NOT NULL,
    emoji text NOT NULL
);


ALTER TABLE public.reaction_trigger OWNER TO admin;

--
-- Name: reminders; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.reminders (
    user_id bigint NOT NULL,
    reminder text NOT NULL,
    remind_at timestamp with time zone NOT NULL,
    invoked_at timestamp with time zone NOT NULL
);


ALTER TABLE public.reminders OWNER TO admin;

--
-- Name: reskin_user; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.reskin_user (
    user_id bigint,
    toggled boolean,
    username text,
    avatar text
);


ALTER TABLE public.reskin_user OWNER TO admin;

--
-- Name: response_trigger; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.response_trigger (
    guild_id bigint NOT NULL,
    trigger public.citext NOT NULL,
    template text NOT NULL,
    strict boolean DEFAULT false NOT NULL,
    reply boolean DEFAULT false NOT NULL,
    delete boolean DEFAULT false NOT NULL,
    delete_after integer DEFAULT 0 NOT NULL,
    role_id bigint
);


ALTER TABLE public.response_trigger OWNER TO admin;

--
-- Name: role_shops; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.role_shops (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    price integer,
    description text,
    active boolean DEFAULT true
);


ALTER TABLE public.role_shops OWNER TO admin;

--
-- Name: roleplay; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.roleplay (
    user_id bigint NOT NULL,
    target_id bigint NOT NULL,
    category text NOT NULL,
    amount integer DEFAULT 1 NOT NULL
);


ALTER TABLE public.roleplay OWNER TO admin;

--
-- Name: selfprefix; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.selfprefix (
    user_id bigint,
    prefix text
);


ALTER TABLE public.selfprefix OWNER TO admin;

--
-- Name: settings; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.settings (
    guild_id bigint NOT NULL,
    prefixes text[] DEFAULT '{}'::text[] NOT NULL,
    reskin boolean DEFAULT false NOT NULL,
    reposter_prefix boolean DEFAULT true NOT NULL,
    reposter_delete boolean DEFAULT false NOT NULL,
    reposter_embed boolean DEFAULT true NOT NULL,
    transcription boolean DEFAULT false NOT NULL,
    welcome_removal boolean DEFAULT false NOT NULL,
    booster_role_base_id bigint,
    booster_role_include_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    lock_role_id bigint,
    lock_ignore_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    log_ignore_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    reassign_ignore_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    reassign_roles boolean DEFAULT false NOT NULL,
    invoke_kick text,
    invoke_ban text,
    invoke_unban text,
    invoke_timeout text,
    invoke_untimeout text,
    invoke_play text,
    play_panel boolean DEFAULT true NOT NULL,
    play_deletion boolean DEFAULT false NOT NULL,
    safesearch_level text DEFAULT 'strict'::text NOT NULL,
    author text
);


ALTER TABLE public.settings OWNER TO admin;

--
-- Name: shop_items; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.shop_items (
    item_id integer NOT NULL,
    name text,
    price integer,
    description text,
    effect_type text,
    effect_value double precision,
    duration integer,
    effect_description text,
    effect_example jsonb,
    stock integer DEFAULT '-1'::integer,
    max_quantity integer DEFAULT '-1'::integer,
    tradeable boolean DEFAULT true
);


ALTER TABLE public.shop_items OWNER TO admin;

--
-- Name: shop_items_item_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.shop_items_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.shop_items_item_id_seq OWNER TO admin;

--
-- Name: shop_items_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.shop_items_item_id_seq OWNED BY public.shop_items.item_id;


--
-- Name: shutup; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.shutup (
    guild_id bigint,
    user_id bigint
);


ALTER TABLE public.shutup OWNER TO admin;

--
-- Name: starboard; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.starboard (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    self_star boolean DEFAULT true NOT NULL,
    threshold integer DEFAULT 3 NOT NULL,
    emoji text DEFAULT '⭐'::text NOT NULL,
    color integer
);


ALTER TABLE public.starboard OWNER TO admin;

--
-- Name: starboard_entry; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.starboard_entry (
    guild_id bigint NOT NULL,
    star_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    emoji text NOT NULL
);


ALTER TABLE public.starboard_entry OWNER TO admin;

--
-- Name: steal_disabled; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.steal_disabled (
    guild_id bigint NOT NULL
);


ALTER TABLE public.steal_disabled OWNER TO admin;

--
-- Name: sticky_message; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.sticky_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    template text NOT NULL
);


ALTER TABLE public.sticky_message OWNER TO admin;

--
-- Name: suggestion; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.suggestion (
    channel_id bigint,
    guild_id bigint,
    author_id bigint,
    blacklisted_id bigint,
    suggestion_id integer,
    thread_enabled boolean DEFAULT false,
    anonymous_allowed boolean DEFAULT true,
    required_role_id bigint
);


ALTER TABLE public.suggestion OWNER TO admin;

--
-- Name: suggestion_entries; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.suggestion_entries (
    guild_id bigint NOT NULL,
    message_id bigint NOT NULL,
    author_id bigint,
    suggestion_id integer,
    is_anonymous boolean DEFAULT false
);


ALTER TABLE public.suggestion_entries OWNER TO admin;

--
-- Name: suggestion_votes; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.suggestion_votes (
    guild_id bigint,
    message_id bigint NOT NULL,
    user_id bigint NOT NULL,
    vote_type integer
);


ALTER TABLE public.suggestion_votes OWNER TO admin;

--
-- Name: thread; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.thread (
    guild_id bigint NOT NULL,
    thread_id bigint NOT NULL
);


ALTER TABLE public.thread OWNER TO admin;

--
-- Name: timezones; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.timezones (
    user_id bigint NOT NULL,
    timezone text NOT NULL
);


ALTER TABLE public.timezones OWNER TO admin;

--
-- Name: tracker; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.tracker (
    guild_id bigint NOT NULL,
    vanity_channel_id bigint,
    username_channel_id bigint
);


ALTER TABLE public.tracker OWNER TO admin;

--
-- Name: transactions; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    user_id bigint,
    amount bigint,
    action character varying(4),
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.transactions OWNER TO admin;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: admin
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_id_seq OWNER TO admin;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: admin
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: used_items; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.used_items (
    user_id bigint NOT NULL,
    item text NOT NULL,
    ts timestamp without time zone NOT NULL,
    expiration timestamp without time zone NOT NULL
);


ALTER TABLE public.used_items OWNER TO admin;

--
-- Name: user_spotify; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.user_spotify (
    user_id bigint NOT NULL,
    access_token text,
    refresh_token text,
    token_expires_at timestamp without time zone,
    spotify_id text
);


ALTER TABLE public.user_spotify OWNER TO admin;

--
-- Name: uwulock; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.uwulock (
    guild_id bigint,
    user_id bigint
);


ALTER TABLE public.uwulock OWNER TO admin;

--
-- Name: vanity; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.vanity (
    guild_id bigint NOT NULL,
    channel_id bigint,
    role_id bigint,
    template text
);


ALTER TABLE public.vanity OWNER TO admin;

--
-- Name: vanity_sniper; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.vanity_sniper (
    guild_id bigint NOT NULL,
    status boolean DEFAULT true NOT NULL,
    channel_id bigint,
    vanities text[] DEFAULT '{}'::text[] NOT NULL
);


ALTER TABLE public.vanity_sniper OWNER TO admin;

--
-- Name: vape; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.vape (
    user_id bigint NOT NULL,
    flavor text,
    hits bigint DEFAULT 0 NOT NULL
);


ALTER TABLE public.vape OWNER TO admin;

--
-- Name: warn_actions; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.warn_actions (
    guild_id bigint NOT NULL,
    threshold integer NOT NULL,
    action text NOT NULL,
    duration integer
);


ALTER TABLE public.warn_actions OWNER TO admin;

--
-- Name: webhook; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.webhook (
    identifier text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    author_id bigint NOT NULL,
    webhook_id bigint NOT NULL
);


ALTER TABLE public.webhook OWNER TO admin;

--
-- Name: welcome_message; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.welcome_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    delete_after integer
);


ALTER TABLE public.welcome_message OWNER TO admin;

--
-- Name: whitelist; Type: TABLE; Schema: public; Owner: admin
--

CREATE TABLE public.whitelist (
    guild_id bigint NOT NULL,
    status boolean DEFAULT false NOT NULL,
    action text DEFAULT 'kick'::text NOT NULL
);


ALTER TABLE public.whitelist OWNER TO admin;

--
-- Name: disabled; Type: TABLE; Schema: reposters; Owner: admin
--

CREATE TABLE reposters.disabled (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    reposter text NOT NULL
);


ALTER TABLE reposters.disabled OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: reskin; Owner: admin
--

CREATE TABLE reskin.config (
    user_id bigint NOT NULL,
    username text,
    avatar_url text
);


ALTER TABLE reskin.config OWNER TO admin;

--
-- Name: webhook; Type: TABLE; Schema: reskin; Owner: admin
--

CREATE TABLE reskin.webhook (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    webhook_id bigint NOT NULL
);


ALTER TABLE reskin.webhook OWNER TO admin;

--
-- Name: filter; Type: TABLE; Schema: snipe; Owner: admin
--

CREATE TABLE snipe.filter (
    guild_id bigint NOT NULL,
    invites boolean DEFAULT false NOT NULL,
    links boolean DEFAULT false NOT NULL,
    words text[] DEFAULT '{}'::text[] NOT NULL
);


ALTER TABLE snipe.filter OWNER TO admin;

--
-- Name: ignore; Type: TABLE; Schema: snipe; Owner: admin
--

CREATE TABLE snipe.ignore (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE snipe.ignore OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: spam; Owner: admin
--

CREATE TABLE spam.config (
    guild_id bigint NOT NULL,
    enabled boolean DEFAULT false,
    threshold integer DEFAULT 3,
    timeout_duration integer DEFAULT 300
);


ALTER TABLE spam.config OWNER TO admin;

--
-- Name: exempt; Type: TABLE; Schema: spam; Owner: admin
--

CREATE TABLE spam.exempt (
    guild_id bigint NOT NULL,
    entity_id bigint NOT NULL,
    type text
);


ALTER TABLE spam.exempt OWNER TO admin;

--
-- Name: messages; Type: TABLE; Schema: spam; Owner: admin
--

CREATE TABLE spam.messages (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    message_hash text NOT NULL,
    count integer DEFAULT 1
);


ALTER TABLE spam.messages OWNER TO admin;

--
-- Name: daily; Type: TABLE; Schema: statistics; Owner: admin
--

CREATE TABLE statistics.daily (
    guild_id bigint NOT NULL,
    date date DEFAULT CURRENT_DATE NOT NULL,
    member_id bigint NOT NULL,
    messages_sent integer DEFAULT 0,
    voice_minutes integer DEFAULT 0
);


ALTER TABLE statistics.daily OWNER TO admin;

--
-- Name: daily_channels; Type: TABLE; Schema: statistics; Owner: admin
--

CREATE TABLE statistics.daily_channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    date date DEFAULT CURRENT_DATE NOT NULL,
    messages_sent integer DEFAULT 0
);


ALTER TABLE statistics.daily_channels OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: stats; Owner: admin
--

CREATE TABLE stats.config (
    guild_id bigint NOT NULL,
    min_word_length integer DEFAULT 3,
    count_bots boolean DEFAULT false,
    channel_whitelist bigint[],
    channel_blacklist bigint[]
);


ALTER TABLE stats.config OWNER TO admin;

--
-- Name: ignored_words; Type: TABLE; Schema: stats; Owner: admin
--

CREATE TABLE stats.ignored_words (
    guild_id bigint NOT NULL,
    word text NOT NULL,
    added_by bigint NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE stats.ignored_words OWNER TO admin;

--
-- Name: word_usage; Type: TABLE; Schema: stats; Owner: admin
--

CREATE TABLE stats.word_usage (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    word text NOT NULL,
    count integer DEFAULT 1,
    last_used timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE stats.word_usage OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: streaks; Owner: admin
--

CREATE TABLE streaks.config (
    guild_id bigint NOT NULL,
    channel_id bigint,
    notification_channel_id bigint,
    streak_emoji text DEFAULT '🔥'::text,
    image_only boolean DEFAULT false
);


ALTER TABLE streaks.config OWNER TO admin;

--
-- Name: restore_log; Type: TABLE; Schema: streaks; Owner: admin
--

CREATE TABLE streaks.restore_log (
    id integer NOT NULL,
    guild_id bigint,
    user_id bigint,
    restored_by text,
    restored_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    previous_streak integer
);


ALTER TABLE streaks.restore_log OWNER TO admin;

--
-- Name: restore_log_id_seq; Type: SEQUENCE; Schema: streaks; Owner: admin
--

CREATE SEQUENCE streaks.restore_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE streaks.restore_log_id_seq OWNER TO admin;

--
-- Name: restore_log_id_seq; Type: SEQUENCE OWNED BY; Schema: streaks; Owner: admin
--

ALTER SEQUENCE streaks.restore_log_id_seq OWNED BY streaks.restore_log.id;


--
-- Name: users; Type: TABLE; Schema: streaks; Owner: admin
--

CREATE TABLE streaks.users (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    current_streak integer DEFAULT 0,
    highest_streak integer DEFAULT 0,
    last_streak_time timestamp with time zone,
    restores_available integer DEFAULT 0,
    total_images_sent integer DEFAULT 0
);


ALTER TABLE streaks.users OWNER TO admin;

--
-- Name: button; Type: TABLE; Schema: ticket; Owner: admin
--

CREATE TABLE ticket.button (
    identifier text NOT NULL,
    guild_id bigint NOT NULL,
    template text,
    category_id bigint,
    topic text
);


ALTER TABLE ticket.button OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: ticket; Owner: admin
--

CREATE TABLE ticket.config (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    staff_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    blacklisted_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    channel_name text,
    logging_channel bigint DEFAULT 0
);


ALTER TABLE ticket.config OWNER TO admin;

--
-- Name: logs; Type: TABLE; Schema: ticket; Owner: admin
--

CREATE TABLE ticket.logs (
    guild_id bigint,
    channel_id bigint
);


ALTER TABLE ticket.logs OWNER TO admin;

--
-- Name: open; Type: TABLE; Schema: ticket; Owner: admin
--

CREATE TABLE ticket.open (
    identifier text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE ticket.open OWNER TO admin;

--
-- Name: message; Type: TABLE; Schema: timer; Owner: admin
--

CREATE TABLE timer.message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    "interval" integer NOT NULL,
    next_trigger timestamp with time zone NOT NULL
);


ALTER TABLE timer.message OWNER TO admin;

--
-- Name: purge; Type: TABLE; Schema: timer; Owner: admin
--

CREATE TABLE timer.purge (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    "interval" integer NOT NULL,
    next_trigger timestamp with time zone NOT NULL,
    method text DEFAULT 'bulk'::text NOT NULL
);


ALTER TABLE timer.purge OWNER TO admin;

--
-- Name: username; Type: TABLE; Schema: track; Owner: admin
--

CREATE TABLE track.username (
    username text NOT NULL,
    user_ids bigint[]
);


ALTER TABLE track.username OWNER TO admin;

--
-- Name: vanity; Type: TABLE; Schema: track; Owner: admin
--

CREATE TABLE track.vanity (
    vanity text NOT NULL,
    user_ids bigint[]
);


ALTER TABLE track.vanity OWNER TO admin;

--
-- Name: channels; Type: TABLE; Schema: transcribe; Owner: admin
--

CREATE TABLE transcribe.channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE transcribe.channels OWNER TO admin;

--
-- Name: rate_limit; Type: TABLE; Schema: transcribe; Owner: admin
--

CREATE TABLE transcribe.rate_limit (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    last_used timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    uses integer DEFAULT 1
);


ALTER TABLE transcribe.rate_limit OWNER TO admin;

--
-- Name: logs; Type: TABLE; Schema: verification; Owner: admin
--

CREATE TABLE verification.logs (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    session_id text NOT NULL,
    event_type text NOT NULL,
    details jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE verification.logs OWNER TO admin;

--
-- Name: logs_id_seq; Type: SEQUENCE; Schema: verification; Owner: admin
--

CREATE SEQUENCE verification.logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE verification.logs_id_seq OWNER TO admin;

--
-- Name: logs_id_seq; Type: SEQUENCE OWNED BY; Schema: verification; Owner: admin
--

ALTER SEQUENCE verification.logs_id_seq OWNED BY verification.logs.id;


--
-- Name: sessions; Type: TABLE; Schema: verification; Owner: admin
--

CREATE TABLE verification.sessions (
    session_id text NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    completed boolean DEFAULT false,
    failed_attempts integer DEFAULT 0
);


ALTER TABLE verification.sessions OWNER TO admin;

--
-- Name: settings; Type: TABLE; Schema: verification; Owner: admin
--

CREATE TABLE verification.settings (
    guild_id bigint NOT NULL,
    enabled boolean DEFAULT false,
    level text DEFAULT 'base'::text,
    methods text[] DEFAULT '{}'::text[],
    timeout integer DEFAULT 1800,
    ip_limit boolean DEFAULT false,
    vpn_check boolean DEFAULT false,
    private_tab_check boolean DEFAULT false,
    log_channel_id bigint,
    verify_channel_id bigint,
    verify_role_id bigint,
    CONSTRAINT settings_level_check CHECK ((level = ANY (ARRAY['base'::text, 'medium'::text])))
);


ALTER TABLE verification.settings OWNER TO admin;

--
-- Name: channels; Type: TABLE; Schema: voice; Owner: admin
--

CREATE TABLE voice.channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    owner_id bigint NOT NULL
);


ALTER TABLE voice.channels OWNER TO admin;

--
-- Name: config; Type: TABLE; Schema: voice; Owner: admin
--

CREATE TABLE voice.config (
    guild_id bigint NOT NULL,
    category_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    bitrate integer,
    name text,
    status text
);


ALTER TABLE voice.config OWNER TO admin;

--
-- Name: channels; Type: TABLE; Schema: voicemaster; Owner: admin
--

CREATE TABLE voicemaster.channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    owner_id bigint
);


ALTER TABLE voicemaster.channels OWNER TO admin;

--
-- Name: configuration; Type: TABLE; Schema: voicemaster; Owner: admin
--

CREATE TABLE voicemaster.configuration (
    guild_id bigint NOT NULL,
    category_id bigint,
    interface_id bigint,
    channel_id bigint,
    role_id bigint,
    region text,
    bitrate bigint,
    interface_emojis jsonb,
    interface_layout character varying(10) DEFAULT 'default'::character varying,
    interface_embed text
);


ALTER TABLE voicemaster.configuration OWNER TO admin;

--
-- Name: media id; Type: DEFAULT; Schema: auto; Owner: admin
--

ALTER TABLE ONLY auto.media ALTER COLUMN id SET DEFAULT nextval('auto.media_id_seq'::regclass);


--
-- Name: moderation id; Type: DEFAULT; Schema: history; Owner: admin
--

ALTER TABLE ONLY history.moderation ALTER COLUMN id SET DEFAULT nextval('history.moderation_id_seq'::regclass);


--
-- Name: commands id; Type: DEFAULT; Schema: invoke_history; Owner: admin
--

ALTER TABLE ONLY invoke_history.commands ALTER COLUMN id SET DEFAULT nextval('invoke_history.commands_id_seq'::regclass);


--
-- Name: history id; Type: DEFAULT; Schema: music; Owner: admin
--

ALTER TABLE ONLY music.history ALTER COLUMN id SET DEFAULT nextval('music.history_id_seq'::regclass);


--
-- Name: playlist_tracks id; Type: DEFAULT; Schema: music; Owner: admin
--

ALTER TABLE ONLY music.playlist_tracks ALTER COLUMN id SET DEFAULT nextval('music.playlist_tracks_id_seq'::regclass);


--
-- Name: playlists id; Type: DEFAULT; Schema: music; Owner: admin
--

ALTER TABLE ONLY music.playlists ALTER COLUMN id SET DEFAULT nextval('music.playlists_id_seq'::regclass);


--
-- Name: instance_info instance_id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.instance_info ALTER COLUMN instance_id SET DEFAULT nextval('public.instance_info_instance_id_seq'::regclass);


--
-- Name: shop_items item_id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.shop_items ALTER COLUMN item_id SET DEFAULT nextval('public.shop_items_item_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: restore_log id; Type: DEFAULT; Schema: streaks; Owner: admin
--

ALTER TABLE ONLY streaks.restore_log ALTER COLUMN id SET DEFAULT nextval('streaks.restore_log_id_seq'::regclass);


--
-- Name: logs id; Type: DEFAULT; Schema: verification; Owner: admin
--

ALTER TABLE ONLY verification.logs ALTER COLUMN id SET DEFAULT nextval('verification.logs_id_seq'::regclass);


--
-- Name: twitch twitch_pkey; Type: CONSTRAINT; Schema: alerts; Owner: admin
--

ALTER TABLE ONLY alerts.twitch
    ADD CONSTRAINT twitch_pkey PRIMARY KEY (guild_id, twitch_id);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: audio; Owner: admin
--

ALTER TABLE ONLY audio.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: statistics statistics_pkey; Type: CONSTRAINT; Schema: audio; Owner: admin
--

ALTER TABLE ONLY audio.statistics
    ADD CONSTRAINT statistics_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: media media_pkey; Type: CONSTRAINT; Schema: auto; Owner: admin
--

ALTER TABLE ONLY auto.media
    ADD CONSTRAINT media_pkey PRIMARY KEY (id);


--
-- Name: media unique_media_config; Type: CONSTRAINT; Schema: auto; Owner: admin
--

ALTER TABLE ONLY auto.media
    ADD CONSTRAINT unique_media_config UNIQUE (guild_id, channel_id, type);


--
-- Name: disabled disabled_pkey; Type: CONSTRAINT; Schema: commands; Owner: admin
--

ALTER TABLE ONLY commands.disabled
    ADD CONSTRAINT disabled_pkey PRIMARY KEY (guild_id, channel_id, command);


--
-- Name: ignore ignore_pkey; Type: CONSTRAINT; Schema: commands; Owner: admin
--

ALTER TABLE ONLY commands.ignore
    ADD CONSTRAINT ignore_pkey PRIMARY KEY (guild_id, target_id);


--
-- Name: restricted restricted_pkey; Type: CONSTRAINT; Schema: commands; Owner: admin
--

ALTER TABLE ONLY commands.restricted
    ADD CONSTRAINT restricted_pkey PRIMARY KEY (guild_id, role_id, command);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: counting; Owner: admin
--

ALTER TABLE ONLY counting.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: disboard; Owner: admin
--

ALTER TABLE ONLY disboard.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: marriages marriages_pkey; Type: CONSTRAINT; Schema: family; Owner: admin
--

ALTER TABLE ONLY family.marriages
    ADD CONSTRAINT marriages_pkey PRIMARY KEY (user_id, partner_id);


--
-- Name: members members_pkey; Type: CONSTRAINT; Schema: family; Owner: admin
--

ALTER TABLE ONLY family.members
    ADD CONSTRAINT members_pkey PRIMARY KEY (user_id, related_id);


--
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: family; Owner: admin
--

ALTER TABLE ONLY family.profiles
    ADD CONSTRAINT profiles_pkey PRIMARY KEY (user_id);


--
-- Name: instagram instagram_pkey; Type: CONSTRAINT; Schema: feeds; Owner: admin
--

ALTER TABLE ONLY feeds.instagram
    ADD CONSTRAINT instagram_pkey PRIMARY KEY (guild_id, instagram_id);


--
-- Name: pinterest pinterest_pkey; Type: CONSTRAINT; Schema: feeds; Owner: admin
--

ALTER TABLE ONLY feeds.pinterest
    ADD CONSTRAINT pinterest_pkey PRIMARY KEY (guild_id, pinterest_id);


--
-- Name: reddit reddit_pkey; Type: CONSTRAINT; Schema: feeds; Owner: admin
--

ALTER TABLE ONLY feeds.reddit
    ADD CONSTRAINT reddit_pkey PRIMARY KEY (guild_id, subreddit_name);


--
-- Name: soundcloud soundcloud_pkey; Type: CONSTRAINT; Schema: feeds; Owner: admin
--

ALTER TABLE ONLY feeds.soundcloud
    ADD CONSTRAINT soundcloud_pkey PRIMARY KEY (guild_id, soundcloud_id);


--
-- Name: tiktok tiktok_pkey; Type: CONSTRAINT; Schema: feeds; Owner: admin
--

ALTER TABLE ONLY feeds.tiktok
    ADD CONSTRAINT tiktok_pkey PRIMARY KEY (guild_id, tiktok_id);


--
-- Name: twitter twitter_pkey; Type: CONSTRAINT; Schema: feeds; Owner: admin
--

ALTER TABLE ONLY feeds.twitter
    ADD CONSTRAINT twitter_pkey PRIMARY KEY (guild_id, twitter_id);


--
-- Name: youtube youtube_pkey; Type: CONSTRAINT; Schema: feeds; Owner: admin
--

ALTER TABLE ONLY feeds.youtube
    ADD CONSTRAINT youtube_pkey PRIMARY KEY (guild_id, youtube_id);


--
-- Name: authorization authorization_user_id_key; Type: CONSTRAINT; Schema: fortnite; Owner: admin
--

ALTER TABLE ONLY fortnite."authorization"
    ADD CONSTRAINT authorization_user_id_key UNIQUE (user_id);


--
-- Name: reminder reminder_pkey; Type: CONSTRAINT; Schema: fortnite; Owner: admin
--

ALTER TABLE ONLY fortnite.reminder
    ADD CONSTRAINT reminder_pkey PRIMARY KEY (user_id, item_id);


--
-- Name: rotation rotation_guild_id_key; Type: CONSTRAINT; Schema: fortnite; Owner: admin
--

ALTER TABLE ONLY fortnite.rotation
    ADD CONSTRAINT rotation_guild_id_key UNIQUE (guild_id);


--
-- Name: wyr_channels wyr_channels_pkey; Type: CONSTRAINT; Schema: fun; Owner: admin
--

ALTER TABLE ONLY fun.wyr_channels
    ADD CONSTRAINT wyr_channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: moderation moderation_pkey; Type: CONSTRAINT; Schema: history; Owner: admin
--

ALTER TABLE ONLY history.moderation
    ADD CONSTRAINT moderation_pkey PRIMARY KEY (id);


--
-- Name: commands commands_pkey; Type: CONSTRAINT; Schema: invoke_history; Owner: admin
--

ALTER TABLE ONLY invoke_history.commands
    ADD CONSTRAINT commands_pkey PRIMARY KEY (id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: joindm; Owner: admin
--

ALTER TABLE ONLY joindm.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: albums albums_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.albums
    ADD CONSTRAINT albums_pkey PRIMARY KEY (user_id, artist, album);


--
-- Name: artists artists_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.artists
    ADD CONSTRAINT artists_pkey PRIMARY KEY (user_id, artist);


--
-- Name: config config_user_id_key; Type: CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.config
    ADD CONSTRAINT config_user_id_key UNIQUE (user_id);


--
-- Name: crowns crowns_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.crowns
    ADD CONSTRAINT crowns_pkey PRIMARY KEY (guild_id, artist);


--
-- Name: hidden hidden_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.hidden
    ADD CONSTRAINT hidden_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: tracks tracks_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.tracks
    ADD CONSTRAINT tracks_pkey PRIMARY KEY (user_id, artist, track);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: member member_pkey; Type: CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.member
    ADD CONSTRAINT member_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (guild_id);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (guild_id, level);


--
-- Name: role role_role_id_key; Type: CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.role
    ADD CONSTRAINT role_role_id_key UNIQUE (role_id);


--
-- Name: history history_pkey; Type: CONSTRAINT; Schema: music; Owner: admin
--

ALTER TABLE ONLY music.history
    ADD CONSTRAINT history_pkey PRIMARY KEY (id);


--
-- Name: playlist_tracks playlist_tracks_pkey; Type: CONSTRAINT; Schema: music; Owner: admin
--

ALTER TABLE ONLY music.playlist_tracks
    ADD CONSTRAINT playlist_tracks_pkey PRIMARY KEY (id);


--
-- Name: playlists playlists_pkey; Type: CONSTRAINT; Schema: music; Owner: admin
--

ALTER TABLE ONLY music.playlists
    ADD CONSTRAINT playlists_pkey PRIMARY KEY (id);


--
-- Name: afk afk_user_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.afk
    ADD CONSTRAINT afk_user_id_key UNIQUE (user_id);


--
-- Name: aliases aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.aliases
    ADD CONSTRAINT aliases_pkey PRIMARY KEY (guild_id, name);


--
-- Name: antinuke antinuke_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.antinuke
    ADD CONSTRAINT antinuke_guild_id_key UNIQUE (guild_id);


--
-- Name: antiraid antiraid_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.antiraid
    ADD CONSTRAINT antiraid_pkey PRIMARY KEY (guild_id);


--
-- Name: auto_role auto_role_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.auto_role
    ADD CONSTRAINT auto_role_pkey PRIMARY KEY (guild_id, role_id, action);


--
-- Name: backup backup_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.backup
    ADD CONSTRAINT backup_pkey PRIMARY KEY (key, guild_id);


--
-- Name: birthdays birthdays_user_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.birthdays
    ADD CONSTRAINT birthdays_user_id_key UNIQUE (user_id);


--
-- Name: blacklist blacklist_user_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.blacklist
    ADD CONSTRAINT blacklist_user_id_key UNIQUE (user_id);


--
-- Name: blunt blunt_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.blunt
    ADD CONSTRAINT blunt_pkey PRIMARY KEY (guild_id);


--
-- Name: boost_message boost_message_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.boost_message
    ADD CONSTRAINT boost_message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: booster_role booster_role_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.booster_role
    ADD CONSTRAINT booster_role_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: boosters_lost boosters_lost_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.boosters_lost
    ADD CONSTRAINT boosters_lost_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: clownboard_entry clownboard_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.clownboard_entry
    ADD CONSTRAINT clownboard_entry_pkey PRIMARY KEY (guild_id, channel_id, message_id, emoji);


--
-- Name: clownboard clownboard_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.clownboard
    ADD CONSTRAINT clownboard_pkey PRIMARY KEY (guild_id, emoji);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: counter counter_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.counter
    ADD CONSTRAINT counter_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: crypto crypto_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.crypto
    ADD CONSTRAINT crypto_pkey PRIMARY KEY (user_id, transaction_id);


--
-- Name: dalle_credits dalle_credits_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.dalle_credits
    ADD CONSTRAINT dalle_credits_pkey PRIMARY KEY (user_id);


--
-- Name: earnings earnings_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.earnings
    ADD CONSTRAINT earnings_pkey PRIMARY KEY (user_id);


--
-- Name: economy economy_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.economy
    ADD CONSTRAINT economy_pkey PRIMARY KEY (user_id);


--
-- Name: economy_roleshop economy_roleshop_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.economy_roleshop
    ADD CONSTRAINT economy_roleshop_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: employee_stats employee_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.employee_stats
    ADD CONSTRAINT employee_stats_pkey PRIMARY KEY (business_id, employee_id);


--
-- Name: fake_permissions fake_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.fake_permissions
    ADD CONSTRAINT fake_permissions_pkey PRIMARY KEY (guild_id, role_id, permission);


--
-- Name: feedback feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (user_id);


--
-- Name: gallery gallery_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.gallery
    ADD CONSTRAINT gallery_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: gnames gnames_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.gnames
    ADD CONSTRAINT gnames_pkey PRIMARY KEY (guild_id, name, changed_at);


--
-- Name: goodbye_message goodbye_message_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.goodbye_message
    ADD CONSTRAINT goodbye_message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: guildblacklist guildblacklist_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.guildblacklist
    ADD CONSTRAINT guildblacklist_guild_id_key UNIQUE (guild_id);


--
-- Name: highlights highlights_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.highlights
    ADD CONSTRAINT highlights_pkey PRIMARY KEY (guild_id, user_id, word);


--
-- Name: instance_info instance_info_owner_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.instance_info
    ADD CONSTRAINT instance_info_owner_id_key UNIQUE (owner_id);


--
-- Name: instance_info instance_info_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.instance_info
    ADD CONSTRAINT instance_info_pkey PRIMARY KEY (instance_id);


--
-- Name: inventory inventory_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.inventory
    ADD CONSTRAINT inventory_pkey PRIMARY KEY (user_id, item);


--
-- Name: logging logging_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.logging
    ADD CONSTRAINT logging_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: mod mod_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.mod
    ADD CONSTRAINT mod_pkey PRIMARY KEY (guild_id);


--
-- Name: payment payment_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.payment
    ADD CONSTRAINT payment_guild_id_key UNIQUE (guild_id);


--
-- Name: publisher publisher_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.publisher
    ADD CONSTRAINT publisher_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: pubsub pubsub_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.pubsub
    ADD CONSTRAINT pubsub_id_key UNIQUE (id);


--
-- Name: quoter quoter_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.quoter
    ADD CONSTRAINT quoter_guild_id_key UNIQUE (guild_id);


--
-- Name: reaction_role reaction_role_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.reaction_role
    ADD CONSTRAINT reaction_role_pkey PRIMARY KEY (guild_id, message_id, emoji);


--
-- Name: reaction_trigger reaction_trigger_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.reaction_trigger
    ADD CONSTRAINT reaction_trigger_pkey PRIMARY KEY (guild_id, trigger, emoji);


--
-- Name: response_trigger response_trigger_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.response_trigger
    ADD CONSTRAINT response_trigger_pkey PRIMARY KEY (guild_id, trigger);


--
-- Name: role_shops role_shops_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.role_shops
    ADD CONSTRAINT role_shops_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: roleplay roleplay_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.roleplay
    ADD CONSTRAINT roleplay_pkey PRIMARY KEY (user_id, target_id, category);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (guild_id);


--
-- Name: shop_items shop_items_name_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.shop_items
    ADD CONSTRAINT shop_items_name_key UNIQUE (name);


--
-- Name: shop_items shop_items_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.shop_items
    ADD CONSTRAINT shop_items_pkey PRIMARY KEY (item_id);


--
-- Name: starboard_entry starboard_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.starboard_entry
    ADD CONSTRAINT starboard_entry_pkey PRIMARY KEY (guild_id, channel_id, message_id, emoji);


--
-- Name: starboard starboard_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.starboard
    ADD CONSTRAINT starboard_pkey PRIMARY KEY (guild_id, emoji);


--
-- Name: steal_disabled steal_disabled_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.steal_disabled
    ADD CONSTRAINT steal_disabled_pkey PRIMARY KEY (guild_id);


--
-- Name: sticky_message sticky_message_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.sticky_message
    ADD CONSTRAINT sticky_message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: suggestion_entries suggestion_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.suggestion_entries
    ADD CONSTRAINT suggestion_entries_pkey PRIMARY KEY (guild_id, message_id);


--
-- Name: suggestion_votes suggestion_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.suggestion_votes
    ADD CONSTRAINT suggestion_votes_pkey PRIMARY KEY (message_id, user_id);


--
-- Name: thread thread_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.thread
    ADD CONSTRAINT thread_pkey PRIMARY KEY (guild_id, thread_id);


--
-- Name: timezones timezones_user_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.timezones
    ADD CONSTRAINT timezones_user_id_key UNIQUE (user_id);


--
-- Name: tracker tracker_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.tracker
    ADD CONSTRAINT tracker_pkey PRIMARY KEY (guild_id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: used_items used_items_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.used_items
    ADD CONSTRAINT used_items_pkey PRIMARY KEY (user_id, item);


--
-- Name: user_spotify user_spotify_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.user_spotify
    ADD CONSTRAINT user_spotify_pkey PRIMARY KEY (user_id);


--
-- Name: vanity vanity_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.vanity
    ADD CONSTRAINT vanity_guild_id_key UNIQUE (guild_id);


--
-- Name: vanity_sniper vanity_sniper_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.vanity_sniper
    ADD CONSTRAINT vanity_sniper_guild_id_key UNIQUE (guild_id);


--
-- Name: vape vape_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.vape
    ADD CONSTRAINT vape_pkey PRIMARY KEY (user_id);


--
-- Name: warn_actions warn_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.warn_actions
    ADD CONSTRAINT warn_actions_pkey PRIMARY KEY (guild_id, threshold);


--
-- Name: webhook webhook_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_pkey PRIMARY KEY (channel_id, webhook_id);


--
-- Name: welcome_message welcome_message_pkey; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.welcome_message
    ADD CONSTRAINT welcome_message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: whitelist whitelist_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.whitelist
    ADD CONSTRAINT whitelist_guild_id_key UNIQUE (guild_id);


--
-- Name: disabled disabled_pkey; Type: CONSTRAINT; Schema: reposters; Owner: admin
--

ALTER TABLE ONLY reposters.disabled
    ADD CONSTRAINT disabled_pkey PRIMARY KEY (guild_id, channel_id, reposter);


--
-- Name: config config_user_id_key; Type: CONSTRAINT; Schema: reskin; Owner: admin
--

ALTER TABLE ONLY reskin.config
    ADD CONSTRAINT config_user_id_key UNIQUE (user_id);


--
-- Name: webhook webhook_pkey; Type: CONSTRAINT; Schema: reskin; Owner: admin
--

ALTER TABLE ONLY reskin.webhook
    ADD CONSTRAINT webhook_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: filter filter_guild_id_key; Type: CONSTRAINT; Schema: snipe; Owner: admin
--

ALTER TABLE ONLY snipe.filter
    ADD CONSTRAINT filter_guild_id_key UNIQUE (guild_id);


--
-- Name: ignore ignore_pkey; Type: CONSTRAINT; Schema: snipe; Owner: admin
--

ALTER TABLE ONLY snipe.ignore
    ADD CONSTRAINT ignore_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: spam; Owner: admin
--

ALTER TABLE ONLY spam.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: exempt exempt_pkey; Type: CONSTRAINT; Schema: spam; Owner: admin
--

ALTER TABLE ONLY spam.exempt
    ADD CONSTRAINT exempt_pkey PRIMARY KEY (guild_id, entity_id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: spam; Owner: admin
--

ALTER TABLE ONLY spam.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (guild_id, user_id, message_hash);


--
-- Name: daily_channels daily_channels_pkey; Type: CONSTRAINT; Schema: statistics; Owner: admin
--

ALTER TABLE ONLY statistics.daily_channels
    ADD CONSTRAINT daily_channels_pkey PRIMARY KEY (guild_id, channel_id, date);


--
-- Name: daily daily_pkey; Type: CONSTRAINT; Schema: statistics; Owner: admin
--

ALTER TABLE ONLY statistics.daily
    ADD CONSTRAINT daily_pkey PRIMARY KEY (guild_id, date, member_id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: stats; Owner: admin
--

ALTER TABLE ONLY stats.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: ignored_words ignored_words_pkey; Type: CONSTRAINT; Schema: stats; Owner: admin
--

ALTER TABLE ONLY stats.ignored_words
    ADD CONSTRAINT ignored_words_pkey PRIMARY KEY (guild_id, word);


--
-- Name: word_usage word_usage_pkey; Type: CONSTRAINT; Schema: stats; Owner: admin
--

ALTER TABLE ONLY stats.word_usage
    ADD CONSTRAINT word_usage_pkey PRIMARY KEY (guild_id, user_id, word);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: streaks; Owner: admin
--

ALTER TABLE ONLY streaks.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: restore_log restore_log_pkey; Type: CONSTRAINT; Schema: streaks; Owner: admin
--

ALTER TABLE ONLY streaks.restore_log
    ADD CONSTRAINT restore_log_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: streaks; Owner: admin
--

ALTER TABLE ONLY streaks.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: button button_pkey; Type: CONSTRAINT; Schema: ticket; Owner: admin
--

ALTER TABLE ONLY ticket.button
    ADD CONSTRAINT button_pkey PRIMARY KEY (identifier, guild_id);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: ticket; Owner: admin
--

ALTER TABLE ONLY ticket.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: open open_pkey; Type: CONSTRAINT; Schema: ticket; Owner: admin
--

ALTER TABLE ONLY ticket.open
    ADD CONSTRAINT open_pkey PRIMARY KEY (identifier, guild_id, user_id);


--
-- Name: logs unique_guild_id; Type: CONSTRAINT; Schema: ticket; Owner: admin
--

ALTER TABLE ONLY ticket.logs
    ADD CONSTRAINT unique_guild_id UNIQUE (guild_id);


--
-- Name: message message_pkey; Type: CONSTRAINT; Schema: timer; Owner: admin
--

ALTER TABLE ONLY timer.message
    ADD CONSTRAINT message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: purge purge_pkey; Type: CONSTRAINT; Schema: timer; Owner: admin
--

ALTER TABLE ONLY timer.purge
    ADD CONSTRAINT purge_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: username username_pkey; Type: CONSTRAINT; Schema: track; Owner: admin
--

ALTER TABLE ONLY track.username
    ADD CONSTRAINT username_pkey PRIMARY KEY (username);


--
-- Name: vanity vanity_pkey; Type: CONSTRAINT; Schema: track; Owner: admin
--

ALTER TABLE ONLY track.vanity
    ADD CONSTRAINT vanity_pkey PRIMARY KEY (vanity);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: transcribe; Owner: admin
--

ALTER TABLE ONLY transcribe.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: rate_limit rate_limit_pkey; Type: CONSTRAINT; Schema: transcribe; Owner: admin
--

ALTER TABLE ONLY transcribe.rate_limit
    ADD CONSTRAINT rate_limit_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: logs logs_pkey; Type: CONSTRAINT; Schema: verification; Owner: admin
--

ALTER TABLE ONLY verification.logs
    ADD CONSTRAINT logs_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: verification; Owner: admin
--

ALTER TABLE ONLY verification.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_id);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: verification; Owner: admin
--

ALTER TABLE ONLY verification.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (guild_id);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: voice; Owner: admin
--

ALTER TABLE ONLY voice.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: voice; Owner: admin
--

ALTER TABLE ONLY voice.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: voicemaster; Owner: admin
--

ALTER TABLE ONLY voicemaster.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: configuration configuration_pkey; Type: CONSTRAINT; Schema: voicemaster; Owner: admin
--

ALTER TABLE ONLY voicemaster.configuration
    ADD CONSTRAINT configuration_pkey PRIMARY KEY (guild_id);


--
-- Name: instance_info update_instance_info_updated_at; Type: TRIGGER; Schema: public; Owner: admin
--

CREATE TRIGGER update_instance_info_updated_at BEFORE UPDATE ON public.instance_info FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: albums albums_user_id_fkey; Type: FK CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.albums
    ADD CONSTRAINT albums_user_id_fkey FOREIGN KEY (user_id) REFERENCES lastfm.config(user_id) ON DELETE CASCADE;


--
-- Name: artists artists_user_id_fkey; Type: FK CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.artists
    ADD CONSTRAINT artists_user_id_fkey FOREIGN KEY (user_id) REFERENCES lastfm.config(user_id) ON DELETE CASCADE;


--
-- Name: crowns crowns_user_id_artist_fkey; Type: FK CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.crowns
    ADD CONSTRAINT crowns_user_id_artist_fkey FOREIGN KEY (user_id, artist) REFERENCES lastfm.artists(user_id, artist) ON DELETE CASCADE;


--
-- Name: tracks tracks_user_id_fkey; Type: FK CONSTRAINT; Schema: lastfm; Owner: admin
--

ALTER TABLE ONLY lastfm.tracks
    ADD CONSTRAINT tracks_user_id_fkey FOREIGN KEY (user_id) REFERENCES lastfm.config(user_id) ON DELETE CASCADE;


--
-- Name: config config_guild_id_fkey; Type: FK CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.config
    ADD CONSTRAINT config_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES public.settings(guild_id) ON DELETE CASCADE;


--
-- Name: member member_guild_id_fkey; Type: FK CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.member
    ADD CONSTRAINT member_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES level.config(guild_id) ON DELETE CASCADE;


--
-- Name: notification notification_guild_id_fkey; Type: FK CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.notification
    ADD CONSTRAINT notification_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES level.config(guild_id) ON DELETE CASCADE;


--
-- Name: role role_guild_id_fkey; Type: FK CONSTRAINT; Schema: level; Owner: admin
--

ALTER TABLE ONLY level.role
    ADD CONSTRAINT role_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES level.config(guild_id) ON DELETE CASCADE;


--
-- Name: playlist_tracks playlist_tracks_playlist_id_fkey; Type: FK CONSTRAINT; Schema: music; Owner: admin
--

ALTER TABLE ONLY music.playlist_tracks
    ADD CONSTRAINT playlist_tracks_playlist_id_fkey FOREIGN KEY (playlist_id) REFERENCES music.playlists(id) ON DELETE CASCADE;


--
-- Name: clownboard_entry clownboard_entry_guild_id_emoji_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.clownboard_entry
    ADD CONSTRAINT clownboard_entry_guild_id_emoji_fkey FOREIGN KEY (guild_id, emoji) REFERENCES public.clownboard(guild_id, emoji) ON DELETE CASCADE;


--
-- Name: starboard_entry starboard_entry_guild_id_emoji_fkey; Type: FK CONSTRAINT; Schema: public; Owner: admin
--

ALTER TABLE ONLY public.starboard_entry
    ADD CONSTRAINT starboard_entry_guild_id_emoji_fkey FOREIGN KEY (guild_id, emoji) REFERENCES public.starboard(guild_id, emoji) ON DELETE CASCADE;


--
-- Name: button button_guild_id_fkey; Type: FK CONSTRAINT; Schema: ticket; Owner: admin
--

ALTER TABLE ONLY ticket.button
    ADD CONSTRAINT button_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES ticket.config(guild_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

