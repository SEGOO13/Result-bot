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

    # Отрисовка логотипов
    if logo1_img:
        l1 = logo1_img.resize((120, 120))
        bg.paste(l1, (200, 570), l1)
    if logo2_img:
        l2 = logo2_img.resize((120, 120))
        bg.paste(l2, (680, 570), l2)

    # Разделительная линия
    draw.line([(100, 755), (900, 755)], fill=(255, 255, 255, 80), width=2)

    # События
    draw.text((260, 830), events1, fill=(220, 220, 220), font=font_events, anchor="mm")
    draw.text((740, 830), events2, fill=(220, 220, 220), font=font_events, anchor="mm")

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ОКНО ВВОДА ССЫЛКИ НА ЛОГОТИП КОМАНДЫ 1
class Logo1Modal(discord.ui.Modal, title="🛡️ Аватарка Команды 1"):
    url = discord.ui.TextInput(
        label="Ссылка на фото (или скопируйте из Discord)", 
        placeholder="Отправьте лого в чат Discord -> Скопируйте ссылку -> Вставьте сюда", 
        required=True
    )

    def __init__(self, start_view):
        super().__init__()
        self.start_view = start_view

    async def on_submit(self, interaction: discord.Interaction):
        self.start_view.logo1_url = self.url.value.strip()
        await interaction.response.send_message("✅ Логотип Команды 1 сохранён!", ephemeral=True)

# ОКНО ВВОДА ССЫЛКИ НА ЛОГОТИП КОМАНДЫ 2
class Logo2Modal(discord.ui.Modal, title="🛡️ Аватарка Команды 2"):
    url = discord.ui.TextInput(
        label="Ссылка на фото (или скопируйте из Discord)", 
        placeholder="Отправьте лого в чат Discord -> Скопируйте ссылку -> Вставьте сюда", 
        required=True
    )

    def __init__(self, start_view):
        super().__init__()
        self.start_view = start_view

    async def on_submit(self, interaction: discord.Interaction):
        self.start_view.logo2_url = self.url.value.strip()
        await interaction.response.send_message("✅ Логотип Команды 2 сохранён!", ephemeral=True)

# ОКНО ВВОДА ДАННЫХ МАТЧА
class MatchDataModal(discord.ui.Modal, title="📊 Статистика матча"):
    team1 = discord.ui.TextInput(label="Название Команды 1", placeholder="например: BAYER 04", required=True)
    score1 = discord.ui.TextInput(label="Счёт Команды 1", placeholder="2", required=True)
    events1 = discord.ui.TextInput(label="Авторы голов Команды 1", placeholder="34' Schick, 60' Wirtz", required=False, default="-")

    team2 = discord.ui.TextInput(label="Название Команды 2", placeholder="например: VALENCIA", required=True)
    score2 = discord.ui.TextInput(label="Счёт Команды 2", placeholder="0", required=True)
    events2 = discord.ui.TextInput(label="Авторы голов Команды 2", placeholder="78' Duro", required=False, default="-")

    def __init__(self, start_view):
        super().__init__()
        self.start_view = start_view

    async def on_submit(self, interaction: discord.Interaction):
        self.start_view.team1 = self.team1.value.strip()
        self.start_view.score1 = self.score1.value.strip()
        self.start_view.events1 = self.events1.value
        self.start_view.team2 = self.team2.value.strip()
        self.start_view.score2 = self.score2.value.strip()
        self.start_view.events2 = self.events2.value
        await interaction.response.send_message("✅ Статистика матча успешно зафиксирована!", ephemeral=True)

# ФОРМА ДЛЯ ВВОДА MVP
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

# КНОПКИ ПОД ГОТОВОЙ КАРТОЧКОЙ
class MatchResultView(discord.ui.View):
    def __init__(self, team1: str, score1: str, team2: str, score2: str, events1: str, events2: str):
        super().__init__(timeout=None) # Вечное меню
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
            description="Результат матча зафиксирован! Таблица обновляется после завершения тура.\n\nПосмотреть актуальное положение команд можно в канале `#таблица`.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

# СТАРТОВАЯ ПАНЕЛЬ С КНОПКАМИ ПОСЛЕ /result (ВЕЧНАЯ И БЕЗ ТАЙМАУТА)
class ResultStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # timeout=None гарантирует, что кнопки не выключаются
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

        # Мгновенно сообщаем Discord о начале генерации (фикс ошибки "не ответил вовремя")
        await interaction.response.defer()

        try:
            ai_prompt = "abstract dark moody soccer stadium lights background, blue neon atmosphere, 4k"
            encoded_prompt = urllib.parse.quote(ai_prompt)
            bg_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1000&nologo=true"

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

# КОМАНДА /result
@bot.tree.command(name="result", description="Центр управления матчем RFL")
async def result(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚽ Центр управления RFL",
        description=(
            "Заполните информацию о прошедшем матче перед публикацией:\n\n"
            "1️⃣ **`🛡️ Логотип 1`** и **`🛡️ Логотип 2`** — отправьте эмблему в любой чат Discord, скопируйте ссылку на неё и вставьте.\n"
            "2️⃣ **`📝 Статистика матча`** — введите название команд, счёт и авторов голов.\n"
            "3️⃣ **`🚀 Сгенерировать карточку`** — создаст и отправит готовую карточку в чат!"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="RFL Result System v2.0")
    await interaction.response.send_message(embed=embed, view=ResultStartView(), ephemeral=True)

# КОМАНДА /help
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
            "• `/result` — Открывает интерактивное меню оформления матча.\n"
            "• `/help` — Показывает это меню с справкой."
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛠️ Как опубликовать матч?",
        value=(
            "1. Введите команду `/result`.\n"
            "2. (Опционально) Нажмите кнопки **`🛡️ Логотип`** и вставьте ссылку на эмблему.\n"
            "3. Нажмите **`📝 Статистика матча`**, чтобы указать клубы, счёт и авторов голов.\n"
            "4. Жмите **`🚀 Сгенерировать карточку`** — бот сделает крутую картинку!"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Кнопки под готовой карточкой:",
        value=(
            "• **📋 Протокол** — показывает детализацию по забитым голам.\n"
            "• **⭐ MVP Матча** — открывает форму для голосования/выбора лучшего игрока.\n"
            "• **📊 Таблица** — отправляет статус турнирного положения."
        ),
        inline=False
    )

    embed.set_footer(text="Создано специально для лиги RFL ⚽")
    await interaction.response.send_message(embed=embed, ephemeral=True)

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