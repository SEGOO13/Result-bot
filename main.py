import os
import io
import asyncio
import random
import threading
import sqlite3
import textwrap
from datetime import datetime
from flask import Flask
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- ИНИЦИАЛИЗА БАЗЫ ДАННЫХ (SQLite) ---
DB_NAME = "matches.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team1 TEXT NOT NULL,
            score1 INTEGER NOT NULL,
            team2 TEXT NOT NULL,
            score2 INTEGER NOT NULL,
            events1 TEXT,
            events2 TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_match_to_db(team1: str, score1: str, team2: str, score2: str, events1: str, events2: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute('''
        INSERT INTO matches (team1, score1, team2, score2, events1, events2, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (team1, int(score1), team2, int(score2), events1, events2, now_str))
    conn.commit()
    conn.close()

def get_recent_matches(limit: int = 5):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT team1, score1, team2, score2, timestamp FROM matches ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

init_db()

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "RESULTS Bot Status: Live & Persistent"

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
        clean_url = url.split("?")[0] if "cdn.discordapp.com" in url or "media.discordapp.net" in url else url
        if not (clean_url.endswith('.png') or clean_url.endswith('.jpg') or clean_url.endswith('.jpeg') or clean_url.endswith('.webp')):
            clean_url = url

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(clean_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        print(f"Ошибка загрузки картинки ({url}): {e}")
    return None

def draw_stadium_bg(width: int = 1000, height: int = 1000) -> Image.Image:
    """Генерация футбольной арены со случайными цветовыми темами"""
    PALETTES = [
        {"bg": (8, 15, 30, 255), "light1": (0, 142, 255, 180), "light2": (10, 160, 70, 160)},
        {"bg": (20, 10, 35, 255), "light1": (160, 32, 240, 180), "light2": (230, 0, 120, 150)},
        {"bg": (30, 10, 15, 255), "light1": (240, 40, 40, 180), "light2": (255, 140, 0, 150)},
        {"bg": (25, 20, 10, 255), "light1": (245, 180, 0, 180), "light2": (180, 100, 0, 150)},
        {"bg": (5, 25, 20, 255), "light1": (0, 200, 160, 180), "light2": (15, 140, 60, 160)}
    ]

    theme = random.choice(PALETTES)
    bg = Image.new("RGBA", (width, height), theme["bg"])
    
    light_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(light_layer)
    
    ldraw.ellipse((-150, -250, 1150, 550), fill=theme["light1"])
    ldraw.ellipse((-200, 550, 1200, 1200), fill=theme["light2"])
    
    light_layer = light_layer.filter(ImageFilter.GaussianBlur(65))
    bg = Image.alpha_composite(bg, light_layer)

    lines_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    lines_draw = ImageDraw.Draw(lines_layer)
    lines_draw.ellipse((200, 200, 800, 800), outline=(255, 255, 255, 80), width=4)
    lines_draw.ellipse((485, 485, 515, 515), fill=(255, 255, 255, 120))
    lines_draw.line([(0, 500), (1000, 500)], fill=(255, 255, 255, 70), width=3)
    
    bg = Image.alpha_composite(bg, lines_layer)
    return bg

def get_font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        except:
            return ImageFont.load_default()

def make_circle_logo(img: Image.Image, size: tuple) -> Image.Image:
    """Обрезка логотипа в круг"""
    img = img.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    
    output = Image.new('RGBA', size, (0, 0, 0, 0))
    output.paste(img, (0, 0), mask=mask)
    return output

# --- ФУНКЦИЯ ГЕНЕРАЦИИ КАРТОЧКИ ---
def create_433_style_card(team1: str, score1: str, team2: str, score2: str, 
                          events1: str, events2: str,
                          logo1_img: Image.Image = None, logo2_img: Image.Image = None) -> io.BytesIO:
    
    width, height = 1000, 1000
    bg = draw_stadium_bg(width, height)

    draw = ImageDraw.Draw(bg)

    font_title = get_font(30)
    font_team = get_font(30)
    font_status = get_font(26)
    font_events = get_font(20)

    score_text = f"{score1}  -  {score2}"
    score_font_size = 95 if len(score_text) <= 7 else 65
    font_score = get_font(score_font_size)

    frame_left = 50
    frame_right = 950
    card_box = [(frame_left, 320), (frame_right, 950)]
    
    draw.rounded_rectangle(card_box, radius=30, fill=(8, 14, 26, 170), outline=(255, 255, 255, 180), width=4)

    # 1. Заголовок
    draw.text((width // 2, 365), "RESULTS MATCHDAY", fill=(200, 200, 200), font=font_title, anchor="mm")

    # 2. Счёт
    draw.text((width // 2, 460), score_text, fill=(255, 255, 255), font=font_score, anchor="mm")

    # 3. Команды
    draw.text((260, 560), team1.upper(), fill=(255, 255, 255), font=font_team, anchor="mm")
    draw.text((740, 560), team2.upper(), fill=(255, 255, 255), font=font_team, anchor="mm")

    # 4. Статус
    draw.text((width // 2, 600), "FULL-TIME", fill=(234, 179, 8), font=font_status, anchor="mm")

    # 5. Разделитель
    draw.line([(100, 640), (900, 640)], fill=(255, 255, 255, 80), width=2)

    # 6. ВЫВОД ГОЛОВ И СОБЫТИЙ
    def draw_multiline_events(text, center_x, start_y):
        if not text or text.strip() == "":
            return
        
        raw_items = text.split(',')
        lines = []
        
        for item in raw_items:
            clean_item = item.strip()
            if clean_item:
                wrapped = textwrap.wrap(clean_item, width=22)
                lines.extend(wrapped)
                
        current_y = start_y
        for line in lines:
            if current_y > 920:
                break
            draw.text((center_x, current_y), line, fill=(220, 220, 220), font=font_events, anchor="mm")
            current_y += 28

    draw_multiline_events(events1, 260, 675)
    draw_multiline_events(events2, 740, 675)

    # 7. ЛОГОТИПЫ
    logo_size_val = 110
    logo_y_pos = 410 

    if logo1_img:
        l1 = make_circle_logo(logo1_img, (logo_size_val, logo_size_val))
        bg.paste(l1, (frame_left + 40, logo_y_pos), l1)

    if logo2_img:
        l2 = make_circle_logo(logo2_img, (logo_size_val, logo_size_val))
        bg.paste(l2, (frame_right - logo_size_val - 40, logo_y_pos), l2)

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf

# === MODALS ===

class Logo1Modal(discord.ui.Modal, title="🛡️ Аватарка Команды 1"):
    url = discord.ui.TextInput(
        label="Ссылка на фото (URL)", 
        placeholder="Отправьте лого в Discord -> Скопируйте ссылку на изображение", 
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
        placeholder="Отправьте лого в Discord -> Скопируйте ссылку на изображение", 
        required=True
    )

    def __init__(self, start_view):
        super().__init__()
        self.start_view = start_view

    async def on_submit(self, interaction: discord.Interaction):
        self.start_view.logo2_url = self.url.value.strip()
        await interaction.response.send_message("✅ Логотип Команды 2 сохранён!", ephemeral=True)

class MatchDataModal(discord.ui.Modal, title="📊 Статистика матча"):
    team1 = discord.ui.TextInput(label="Название Команды 1", placeholder="BAYER 04", required=True)
    team2 = discord.ui.TextInput(label="Название Команды 2", placeholder="VALENCIA", required=True)
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
        await interaction.response.send_message("✅ Статистика матча успешно зафиксирована!", ephemeral=True)

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
        embed.set_footer(text="Официальное решение RESULTS League")
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
        embed.set_footer(text="Официальный протокол RESULTS League")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="⭐ MVP Матча", style=discord.ButtonStyle.success, custom_id="btn_mvp")
    async def mvp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ограничение прав: только админ может вызывать меню MVP
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Только администраторы могут назначать MVP матча!", ephemeral=True)
            return
        await interaction.response.send_modal(MVPModal())

class ResultStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.logo1_url = None
        self.logo2_url = None
        self.team1 = None
        self.score1 = None
        self.events1 = "-"
        self.team2 = None
        self.score2 = None
        self.events2 = "-"

    @discord.ui.button(label="🛡️ Логотип 1", style=discord.ButtonStyle.secondary, custom_id="results_v2:btn_logo1", row=0)
    async def btn_logo1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Logo1Modal(self))

    @discord.ui.button(label="🛡️ Логотип 2", style=discord.ButtonStyle.secondary, custom_id="results_v2:btn_logo2", row=0)
    async def btn_logo2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Logo2Modal(self))

    @discord.ui.button(label="📝 Статистика матча", style=discord.ButtonStyle.primary, custom_id="results_v2:btn_match_data", row=0)
    async def btn_match_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchDataModal(self))

    @discord.ui.button(label="🚀 Сгенерировать карточку", style=discord.ButtonStyle.success, custom_id="results_v2:btn_generate", row=1)
    async def btn_generate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.team1 or not self.team2 or not self.score1 or not self.score2:
            await interaction.response.send_message("❌ Сначала заполните данные матча через кнопку **«📝 Статистика матча»**!", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            save_match_to_db(self.team1, self.score1, self.team2, self.score2, self.events1, self.events2)

            logo1_img = await fetch_image(self.logo1_url) if self.logo1_url else None
            logo2_img = await fetch_image(self.logo2_url) if self.logo2_url else None

            loop = asyncio.get_running_loop()
            card_buf = await loop.run_in_executor(
                None, create_433_style_card, 
                self.team1, self.score1, 
                self.team2, self.score2, 
                self.events1, self.events2, 
                logo1_img, logo2_img
            )

            file = discord.File(fp=card_buf, filename="results_match_result.png")
            
            view = MatchResultView(
                self.team1, self.score1, 
                self.team2, self.score2, 
                self.events1, self.events2
            )

            await interaction.followup.send(
                content=f"🚨 **RESULTS MATCH RESULT** | {self.team1} vs {self.team2}",
                file=file,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при сборке карточки: `{e}`")

# === BOT EVENTS & COMMANDS ===

# ИЗМЕНЕНО: Убрана проверка @app_commands.checks.has_permissions(administrator=True)
@bot.tree.command(name="result", description="Центр управления матчем RESULTS (Любой пользователь)")
async def result(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚽ Центр управления RESULTS",
        description=(
            "Заполните информацию о прошедшем матче перед публикацией:\n\n"
            "1️⃣ **`🛡️ Логотип`** — отправьте эмблемы в Discord, скопируйте ссылки на них и вставьте.\n"
            "2️⃣ **`📝 Статистика матча`** — введите название команд, счёт и авторов голов.\n"
            "3️⃣ **`🚀 Сгенерировать карточку`** — создаст и отправит готовую карточку в чат (и сохранит в базу)!"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="RESULTS System v2.0")
    await interaction.response.send_message(embed=embed, view=ResultStartView(), ephemeral=True)

@bot.tree.command(name="history", description="История последних сыгранных матчей RESULTS")
async def history(interaction: discord.Interaction):
    matches = get_recent_matches(5)
    if not matches:
        await interaction.response.send_message("📂 В базе данных пока нет сохранённых матчей.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📜 История последних матчей RESULTS",
        color=discord.Color.blue()
    )
    
    for t1, s1, t2, s2, date in matches:
        embed.add_field(
            name=f"⚽ {t1}  {s1} - {s2}  {t2}",
            value=f"🗓️ Дата: {date}",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ У вас нет прав **Администратора** для использования этой команды!", ephemeral=True)
    else:
        print(f"Ошибка команды: {error}")

@bot.tree.command(name="help", description="Полная инструкция и возможности RESULTS Bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Помощник RESULTS League Bot",
        description="Добро пожаловать! Этот бот предназначен для стильного оформления результатов футбольных матчей.",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="🎮 Основные команды:",
        value=(
            "• `/result` — Открывает интерактивное меню оформления матча (Любой пользователь).\n"
            "• `/history` — История последних сыгранных матчей.\n"
            "• `/help` — Показывает это меню со справкой."
        ),
        inline=False
    )

    embed.set_footer(text="Создано специально для RESULTS ⚽")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"=== БОТ ЗАПУЩЕН: {bot.user} ===")
    bot.add_view(ResultStartView())
    
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