import os
import io
import asyncio
import urllib.parse
import threading
from flask import Flask
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "RFL Bot Status: Active"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

# --- DISCORD БОТ ---
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

async def fetch_image(url: str) -> Image.Image:
    if not url or not url.startswith("http"):
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        print(f"Ошибка загрузки картинки: {e}")
    return None

def get_font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        except:
            return ImageFont.load_default()

def create_433_style_card(team1: str, score1: str, team2: str, score2: str, 
                          events1: str, events2: str, bg_img: Image.Image,
                          logo1_img: Image.Image = None, logo2_img: Image.Image = None) -> io.BytesIO:
    
    width, height = 1000, 1000
    bg = bg_img.resize((width, height)).convert("RGBA")

    # Тёмный оверлей
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, 300), (width, height)], fill=(10, 15, 25, 225))
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    font_title = get_font(36)
    font_score = get_font(110)
    font_team = get_font(46)
    font_status = get_font(32)
    font_events = get_font(26)

    # Рамка карточки
    card_box = [(50, 400), (950, 930)]
    draw.rounded_rectangle(card_box, radius=30, outline=(255, 255, 255, 180), width=4)

    # Заголовок
    draw.text((width // 2, 445), "RFL MATCHDAY", fill=(200, 200, 200), font=font_title, anchor="mm")

    # Названия команд
    draw.text((260, 520), team1.upper(), fill=(255, 255, 255), font=font_team, anchor="mm")
    draw.text((740, 520), team2.upper(), fill=(255, 255, 255), font=font_team, anchor="mm")

    # Счёт
    score_text = f"{score1}  -  {score2}"
    draw.text((width // 2, 620), score_text, fill=(255, 255, 255), font=font_score, anchor="mm")

    # FULL-TIME
    draw.text((width // 2, 715), "FULL-TIME", fill=(234, 179, 8), font=font_status, anchor="mm")

    # Отрисовка логотипов (если они валидны)
    if logo1_img:
        l1 = logo1_img.resize((120, 120))
        bg.paste(l1, (200, 570), l1)
    if logo2_img:
        l2 = logo2_img.resize((120, 120))
        bg.paste(l2, (680, 570), l2)

    # Разделительная линия
    draw.line([(100, 755), (900, 755)], fill=(255, 255, 255, 80), width=2)

    # События по бокам
    draw.text((260, 830), events1, fill=(220, 220, 220), font=font_events, anchor="mm")
    draw.text((740, 830), events2, fill=(220, 220, 220), font=font_events, anchor="mm")

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ФОРМА ВВОДА С ВОЗМОЖНОСТЬЮ ВСТАВИТЬ ССЫЛКИ НА ЛОГОТИПЫ
class ResultModal(discord.ui.Modal, title="Протокол матча RFL"):
    team1 = discord.ui.TextInput(label="Команда 1 и Счёт (Формат: Название - Счёт)", placeholder="BAYER 04 - 2", required=True)
    events1 = discord.ui.TextInput(label="Голы Команды 1", placeholder="34' Schick, 60' Wirtz", required=False, default="-")
    
    team2 = discord.ui.TextInput(label="Команда 2 и Счёт (Формат: Название - Счёт)", placeholder="VALENCIA - 0", required=True)
    events2 = discord.ui.TextInput(label="Голы Команды 2", placeholder="78' Duro", required=False, default="-")

    logos = discord.ui.TextInput(label="Ссылки на логотипы (необязательно)", placeholder="Ссылка1 | Ссылка2 (через знак |)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # 🔥 МГНОВЕННО отвечаем Discord, чтобы не было ошибки "не ответил вовремя"
        await interaction.response.defer()

        try:
            # Разбор Команды 1
            if "-" in self.team1.value:
                t1, s1 = self.team1.value.rsplit("-", 1)
            else:
                t1, s1 = self.team1.value, "0"

            # Разбор Команды 2
            if "-" in self.team2.value:
                t2, s2 = self.team2.value.rsplit("-", 1)
            else:
                t2, s2 = self.team2.value, "0"

            # Разбор ссылок на лого
            logo1_url, logo2_url = None, None
            if self.logos.value and "|" in self.logos.value:
                parts = self.logos.value.split("|")
                logo1_url = parts[0].strip()
                logo2_url = parts[1].strip()

            ai_prompt = "abstract dark moody soccer stadium lights background, blue neon atmosphere, 4k"
            encoded_prompt = urllib.parse.quote(ai_prompt)
            bg_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1000&nologo=true"

            bg_img = await fetch_image(bg_url)
            if not bg_img:
                bg_img = Image.new("RGBA", (1000, 1000), (15, 23, 42))

            logo1_img = await fetch_image(logo1_url) if logo1_url else None
            logo2_img = await fetch_image(logo2_url) if logo2_url else None

            loop = asyncio.get_running_loop()
            card_buf = await loop.run_in_executor(
                None, create_433_style_card, 
                t1.strip(), s1.strip(), 
                t2.strip(), s2.strip(), 
                self.events1.value, self.events2.value, 
                bg_img, logo1_img, logo2_img
            )

            file = discord.File(fp=card_buf, filename="rfl_match_result.png")
            
            view = MatchResultView(
                t1.strip(), s1.strip(), 
                t2.strip(), s2.strip(), 
                self.events1.value, self.events2.value
            )

            await interaction.followup.send(
                content=f"🚨 **RFL MATCH RESULT** | {t1.strip()} vs {t2.strip()}",
                file=file,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при сборке карточки: `{e}`")

# ФОРМА ДЛЯ ВВОДА MVP
class MVPModal(discord.ui.Modal, title="Назначение MVP Матча"):
    player_name = discord.ui.TextInput(label="Имя игрока (MVP)", placeholder="например: Pedri", required=True)
    stats = discord.ui.TextInput(label="Статистика", placeholder="например: 1 Гол, 2 Передачи", required=False, default="Лучший игрок встречи")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="⭐ ИГРОК МАТЧА (MVP)",
            description=f"🏆 **{self.player_name.value}** признан лучшим игроком этого матча!",
            color=discord.Color.gold()
        )
        embed.add_field(name="📊 Статистика:", value=self.stats.value, inline=False)
        embed.set_footer(text="Официальное решение RFL")
        await interaction.followup.send(embed=embed)

# ИНТЕРАКТИВНЫЕ КНОПКИ
class MatchResultView(discord.ui.View):
    def __init__(self, team1: str, score1: str, team2: str, score2: str, events1: str, events2: str):
        super().__init__(timeout=None)
        self.team1 = team1
        self.score1 = score1
        self.team2 = team2
        self.score2 = score2
        self.events1 = events1
        self.events2 = events2

    @discord.ui.button(label="📋 Протокол", style=discord.ButtonStyle.primary, custom_id="btn_details")
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title=f"📋 ПОДРОБНЫЙ ПРОТОКОЛ: {self.team1} vs {self.team2}",
            color=discord.Color.blue()
        )
        embed.add_field(name=f"⚽ {self.team1}", value=f"**Счёт:** {self.score1}\n\n**События:**\n{self.events1}", inline=True)
        embed.add_field(name=f"⚽ {self.team2}", value=f"**Счёт:** {self.score2}\n\n**События:**\n{self.events2}", inline=True)
        embed.set_footer(text="Официальный протокол RFL League")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="⭐ MVP Матча", style=discord.ButtonStyle.success, custom_id="btn_mvp")
    async def mvp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MVPModal())

    @discord.ui.button(label="📊 Таблица", style=discord.ButtonStyle.secondary, custom_id="btn_table")
    async def table_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="📊 ТУРНИРНАЯ ТАБЛИЦА RFL",
            description="Результат матча зафиксирован! Таблица обновляется после завершения тура.\n\nПосмотреть положение команд можно в канале `#таблица`.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

# СТАРТОВАЯ ПАНЕЛЬ
class ResultStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Заполнить протокол матча", style=discord.ButtonStyle.success, custom_id="btn_open_modal")
    async def open_modal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ResultModal())

@bot.tree.command(name="result", description="Открыть панель оформления матча RFL")
async def result(interaction: discord.Interaction):
    # Защита от таймаута для вызова меню
    embed = discord.Embed(
        title="⚽ Центр управления RFL",
        description="Нажмите кнопку ниже, чтобы открыть форму протокола.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=ResultStartView(), ephemeral=True)

@bot.tree.command(name="help", description="Помощь по боту")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("Используйте `/result` для запуска формы карточки.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"=== БОТ ЗАПУЩЕН: {bot.user} ===")
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

TOKEN = os.getenv("BOT_TOKEN")

if __name__ == "__main__":
    if TOKEN:
        keep_alive()
        bot.run(TOKEN)