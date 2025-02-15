from pathlib import Path
import json
from typing import Dict, Any
import logging
from discord import Embed

log = logging.getLogger(__name__)

class Translator:
    def __init__(self, bot):
        self.bot = bot
        self.default_lang = "en"
        self.translations = {}
        self.error_channel_id = 1310147136800817183
        
    async def setup(self):
        translations_dir = Path('languages')
        log.info(f"Loading translations from: {translations_dir}")
        if not translations_dir.exists():
            log.warning("Translations directory does not exist!")
            translations_dir.mkdir(parents=True)
            
        for translation_file in translations_dir.rglob('*.json'):
            lang_code = translation_file.stem
            cog_path = str(translation_file.relative_to(translations_dir).parent)
            
            log.info(f"Found translation file: {translation_file}")
            log.info(f"Loading {lang_code} translations for {cog_path}")
            
            if cog_path not in self.translations:
                self.translations[cog_path] = {}
                
            try:
                with open(translation_file, 'r', encoding='utf-8') as f:
                    if lang_code not in self.translations[cog_path]:
                        self.translations[cog_path][lang_code] = {}
                    self.translations[cog_path][lang_code].update(json.load(f))
                log.info(f"Loaded translations for {cog_path}/{lang_code}")
            except Exception as e:
                log.error(f"Failed to load translations for {cog_path}/{lang_code}: {e}")

    async def send_error(self, bot, key: str, error_msg: str):
        channel = bot.get_channel(self.error_channel_id)
        if channel:
            embed = Embed(
                title="Translation Error",
                description=f"**Key:** `{key}`\n**Error:** {error_msg}",
                color=0xFF0000
            )
            await channel.send(embed=embed)

    async def get_text(self, key: str, lang: str = None, **kwargs) -> str:
        lang = lang or self.default_lang
        
        try:
            cog_path, key_path = key.split('.', 1)
            log.info(f"Translation request - Cog: {cog_path}, Key: {key_path}, Lang: {lang}")
            
            cog_translations = self.translations.get(cog_path, {})
            if not cog_translations:
                log.warning(f"No translations found for cog: {cog_path}")
                await self.send_error(self.bot, key, f"No translations found for cog: {cog_path}")
                return key
            
            lang_translations = cog_translations.get(lang, {}).get(cog_path, {})
            if not lang_translations and lang != self.default_lang:
                log.warning(f"No translations for lang {lang}, falling back to {self.default_lang}")
                lang_translations = cog_translations.get(self.default_lang, {}).get(cog_path, {})
            
            current = lang_translations
            for part in key_path.split('.'):
                if not isinstance(current, dict) or part not in current:
                    log.warning(f"Key part '{part}' not found in: {current}")
                    await self.send_error(self.bot, key, f"Key part '{part}' not found in translation")
                    return key
                current = current[part]
            
            if isinstance(current, str):
                try:
                    return current.format(**kwargs)
                except KeyError as e:
                    await self.send_error(self.bot, key, f"Missing format argument: {str(e)}")
                    return current
            return key
        except ValueError:
            await self.send_error(self.bot, key, "Invalid translation key format")
            return key
