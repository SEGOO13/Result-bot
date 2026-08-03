import os
import io
import asyncio
import random
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

def make_circle_logo(img: Image.Image, size: tuple) -> Image.Image:
    """Обрезка логотипа в ровный круг"""
    img = img.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    
    output = Image.new('RGBA', size, (0, 0, 0, 0))
    output.paste(img, (0, 0), mask=mask)
    return output

def create_433_style_card(team1: str, score1: str, team2: str, score2: str, 
                          events1: str, events2: str, bg_img: Image.Image,
                          logo1_img: Image.Image = None, logo2_img: Image.Image = None) -> io.BytesIO:
    
    width, height = 1000, 1000
    bg = bg_img.resize((width, height)).convert("RGBA")

    # Тёмный оверлей
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, 250), (width, height)], fill=(10, 15, 25, 230))
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    font_title = get_font(32)
    font_score = get_font(120)
    font_team = get_font(40)
    font_status = get_font(28)
    font_events = get_font(20)

    # Рамка карточки
    card_box = [(50, 320), (950, 950)]
    draw.rounded_rectangle(card_box, radius=30, outline=(255, 255, 255, 180), width=4)

    # Заголовок
    draw.text((width // 2, 365), "RFL MATCHDAY", fill=(200, 200, 200), font=font_title, anchor="mm")

    # --- РАЗМЕЩЕНИЕ ЛОГОТИПОВ И НАЗВАНИЙ КОМАНД ---
    if logo1_img:
        l1 = make_circle_logo(logo1_img, (110, 110))
        bg.paste(l1, (205, 410), l1)
    draw.text((260, 545), team1.upper(), fill=(255, 255, 255), font=font_team, anchor="mm")

    if logo2_img:
        l2 = make_circle_logo(logo2_img, (110, 110))
        bg.paste(l2, (685, 410), l2)
    draw.text((740, 545), team2.upper(), fill=(255, 255, 255), font=font_team, anchor="mm")

    # --- СЧЁТ И СТАТУС ---
    score_text = f"{score1}  -  {score2}"
    draw.text((width // 2, 490), score_text, fill=(255, 255, 255), font=font_score, anchor="mm")
    draw.text((width // 2, 580), "FULL-TIME", fill=(234, 179, 8), font=font_status, anchor="mm")

    # Разделительная линия
    draw.line([(100, 625), (900, 625)], fill=(255, 255, 255, 80), width=2)

    # --- СОБЫТИЯ МАТЧА ---
    def draw_multiline_events(text, center_x, start_y):
        lines = text.split(',')
        current_y = start_y
        for line in lines:
            clean_line = line.strip()
            if clean_line:
                draw.text((center_x, current_y), clean_line, fill=(220, 220, 220), font=font_events, anchor="mm")
                current_y += 30

    draw_multiline_events(events1, 260, 660)
    draw_multiline_events(events2, 740, 660)

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf

# === MODALS ===

class Logo1Modal(discord.ui.Modal, title="🛡️ Аватарка Команды 1"):
    url = discord.ui.TextInput(
        label="Ссылка на фото (URL)", 
        placeholder="Отправьте лого в Discord -> Копировать ссылку -> Вставьте сюда", 
        required=True
    )

    def __init__(self, start_view):
        super().__init__()
        self.start_view = start_view

    async def on_submit(self, interaction: discord.Interaction):
        self.start_view.logo1_url = self.url.value.strip()
        await interaction.response.send_message("✅ Логотип Команды 1 сохранён!", ephemeral=True)

class Logo2Modal(discord.ui.Modal, title="🛡️ Аватарка Команды 2"):
    url = discord.ui.TextInput(
        label="Ссылка на фото (URL)", 
        placeholder="Отправьте лого в Discord -> Копировать ссылку -> Вставьте сюда", 
        required=True
    )

    def __init__(self, start_view):
        super().__init__()
        self.start_view = start_view

    async def on_submit(self, interaction: discord.Interaction):
        self.start_view.logo2_url = self.url.value.strip()
        await interaction.response.send_message("✅ Логотип Команды 2 сохранён!", ephemeral=True)

class MatchDataModal(discord.ui.Modal, title="📊 Статистика матча"):
    team1 = discord.ui.TextInput(label="Название Команды 1", placeholder="например: BAYER 04", required=True)
    team2 = discord.ui.TextInput(label="Название Команды 2", placeholder="например: VALENCIA", required=True)
    full_score = discord.ui.TextInput(label="Счёт матча (формат 2:0 или 2-0)", placeholder="2:0", required=True)
    events1 = discord.ui.TextInput(label="Голы Команды 1", placeholder="34' Schick, 60' Wirtz", required=False, default="-")
    events2 = discord.ui.TextInput(label="Голы Команды 2", placeholder="78' Duro", required=False, default="-")

    def __init__(self, start_view):
        super().__init__()
        self.start_view = start_view

    async def on_submit(self, interaction: discord.Interaction):
        raw_score = self.full_score.value.strip().replace('-', ':').replace(' ', '')
        if ':' in raw_score:
            s1, s2 = raw_score.split(':', 1)
        else:
            s1, s2 = raw_score, "0"

        self.start_view.team1 = self.team1.value.strip()
        self.start_view.team2 = self.team2.value.strip()
        self.start_view.score1 = s1
        self.start_view.score2 = s2
        self.start_view.events1 = self.events1.value
        self.start_view.events2 = self.events2.value
        await interaction.response.send_message("✅ Статистика матча зафиксирована!", ephemeral=True)

class MVPModal(discord.ui.Modal, title="⭐ Назначение MVP Матча"):
    player_name = discord.ui.TextInput(label="Имя игрока (MVP)", placeholder="например: Pedri", required=True)
    stats = discord.ui.TextInput(label="Статистика игрока", placeholder="например: 1 Гол, 2 Передачи", required=False, default="Лучший игрок встречи")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="⭐ ИГРОК МАТЧА (MVP)",
            description=f"🏆 **{self.player_name.value}** признан лучшим игроком этого матча!",
            color=discord.Color.gold()
        )
        embed.add_field(name="📊 Статистика:", value=self.stats.value, inline=False)
        embed.set_footer(text="Официальное решение RFL League")
        await interaction.followup.send(embed=embed)

# === VIEWS ===

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

class ResultStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600) 
        self.logo1_url = None
        self.logo2_url = None
        self.team1 = None
        self.score1 = None
        self.events1 = "-"
        self.team2 = None
        self.score2 = None
        self.events2 = "-"

    @discord.ui.button(label="🛡️ Логотип 1", style=discord.ButtonStyle.secondary, row=0)
    async def btn_logo1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Logo1Modal(self))

    @discord.ui.button(label="🛡️ Логотип 2", style=discord.ButtonStyle.secondary, row=0)
    async def btn_logo2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Logo2Modal(self))

    @discord.ui.button(label="📝 Статистика матча", style=discord.ButtonStyle.primary, row=0)
    async def btn_match_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchDataModal(self))

    @discord.ui.button(label="🚀 Сгенерировать карточку", style=discord.ButtonStyle.success, row=1)
    async def btn_generate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.team1 or not self.team2 or not self.score1 or not self.score2:
            await interaction.response.send_message("❌ Сначала заполните данные матча через кнопку **«📝 Статистика матча»**!", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            bg_styles = [
                "abstract dark moody soccer stadium lights background, blue neon atmosphere, professional sports photography, 4k",
                "abstract dark soccer stadium, fiery red neon lights background, intense atmosphere, 4k",
                "abstract dark stadium, golden yellow lighting background, epic champions atmosphere, 4k",
                "abstract dark stadium, deep purple violet neon background, modern matchday style, 4k",
                "abstract dark stadium, emerald green neon lights background, clean sports design, 4k",
                "abstract futuristic soccer stadium, cyan blue and orange neon light background, 4k"
            ]
            chosen_prompt = random.choice(bg_styles)
            encoded_prompt = urllib.parse.quote(chosen_prompt)
            bg_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1000&nologo=true&seed={random.randint(1, 999999)}"

            bg_img = await fetch_image(bg_url)
            if not bg_img:
                bg_img = Image.new("RGBA", (1000, 1000), (15, 23, 42))

            logo1_img = await fetch_image(self.logo1_url) if self.logo1_url else None
            logo2_img = await fetch_image(self.logo2_url) if self.logo2_url else None

            loop = asyncio.get_running_loop()
            card_buf = await loop.run_in_executor(
                None, create_433_style_card, 
                self.team1, self.score1, 
                self.team2, self.score2, 
                self.events1, self.events2, 
                bg_img, logo1_img, logo2_img
            )

            file = discord.File(fp=card_buf, filename="rfl_match_result.png")
            
            view = MatchResultView(
                self.team1, self.score1, 
                self.team2, self.score2, 
                self.events1, self.events2
            )

            await interaction.followup.send(
                content=f"🚨 **RFL MATCH RESULT** | {self.team1} vs {self.team2}",
                file=file,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при сборке карточки: `{e}`")

# === BOT EVENTS & COMMANDS ===

# 🔥 ТОЛЬКО ДЛЯ АДМИНИСТРАТОРОВ СЕРВЕРА 🔥
@bot.tree.command(name="result", description="Центр управления матчем RFL (Только для Администраторов)")
@app_commands.checks.has_permissions(administrator=True)
async def result(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚽ Центр управления RFL",
        description=(
            "Заполните информацию о прошедшем матче перед публикацией:\n\n"
            "1️⃣ **`🛡️ Логотип`** — отправьте эмблемы в Discord, скопируйте ссылки на них и вставьте.\n"
            "2️⃣ **`📝 Статистика матча`** — введите название команд, счёт и авторов голов.\n"
            "3️⃣ **`🚀 Сгенерировать карточку`** — создаст и отправит готовую карточку в чат!"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="RFL Result System v2.0")
    await interaction.response.send_message(embed=embed, view=ResultStartView(), ephemeral=True)

# ОБРАБОТЧИК ОШИБОК (ОТПРАВЛЯЕТ УВЕДОМЛЕНИЕ ЕСЛИ ВВЁЛ НЕ АДМИН)
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ У вас нет прав **Администратора** для использования этой команды!", ephemeral=True)
    else:
        print(f"Ошибка команды: {error}")

@bot.tree.command(name="help", description="Полная инструкция и возможности RFL Bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Помощник RFL League Bot",
        description="Добро пожаловать! Этот бот предназначен для стильного оформления результатов футбольных матчей лиги RFL.",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🎮 Основные команды:",
        value=(
            "• `/result` — Открывает интерактивное меню оформления матча (Только Админы).\n"
            "• `/help` — Показывает это меню со справкой."
        ),
        inline=False
    )

    embed.set_footer(text="Создано специально для лиги RFL ⚽")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"=== БОТ ЗАПУЩЕН: {bot.user} ===")
    try:
        synced = await bot.tree.sync()
        print(f"=== СИНХРОНИЗИРОВАНО КОМАНД: {len(synced)} ===")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")

TOKEN = os.getenv("BOT_TOKEN")

if __name__ == "__main__":
    if TOKEN:
        keep_alive()
        bot.run(TOKEN)
    else:
        print("ОШИБКА: Переменная BOT_TOKEN не найдена!")