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
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.read()
                return Image.open(io.BytesIO(data)).convert("RGBA")
    return None

def create_433_style_card(team1: str, score1: int, team2: str, score2: int, details: str, 
                          bg_img: Image.Image, logo1_img: Image.Image = None, logo2_img: Image.Image = None) -> io.BytesIO:
    
    # Размеры карточки как в 433 (вертикальный/квадратный формат 800x1000)
    width, height = 800, 1000
    
    # Подгоняем фон
    bg = bg_img.resize((width, height)).convert("RGBA")
    draw = ImageDraw.Draw(bg)

    # Затемнение нижней части карточки (градиентный слой)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, 500), (width, height)], fill=(0, 0, 0, 180))
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    # Отрисовка плашки счёта в стиле 433
    card_box = [(40, 650), (760, 950)]
    draw.rounded_rectangle(card_box, radius=20, outline=(255, 255, 255, 100), width=2)

    # Текст над счётом
    draw.text((width // 2, 675), "RFL MATCHDAY", fill=(200, 200, 200), anchor="mm")

    # Счёт (1 - 0)
    score_text = f"{score1} - {score2}"
    draw.text((width // 2, 740), score_text, fill=(255, 255, 255), anchor="mm")

    # Статус матча
    draw.text((width // 2, 790), "FULL-TIME", fill=(234, 179, 8), anchor="mm")

    # Названия команд
    draw.text((180, 820), team1.upper(), fill=(255, 255, 255), anchor="mm")
    draw.text((620, 820), team2.upper(), fill=(255, 255, 255), anchor="mm")

    # Авторы голов
    draw.text((width // 2, 880), details, fill=(220, 220, 220), anchor="mm")

    # Наложение логотипов
    if logo1_img:
        logo1 = logo1_img.resize((80, 80))
        bg.paste(logo1, (140, 710), logo1)
    
    if logo2_img:
        logo2 = logo2_img.resize((80, 80))
        bg.paste(logo2, (580, 710), logo2)

    # Сохранение
    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ИНТЕРАКТИВНЫЕ КНОПКИ ПОД СООБЩЕНИЕМ
class MatchResultView(discord.ui.View):
    def __init__(self, match_info: str):
        super().__init__(timeout=None)
        self.match_info = match_info

    @discord.ui.button(label="⚽ Протокол", style=discord.ButtonStyle.primary, custom_id="btn_details")
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"📋 **Подробная информация о матче:**\n{self.match_info}", ephemeral=True)

    @discord.ui.button(label="🔥 Лучший игрок", style=discord.ButtonStyle.success, custom_id="btn_mvp")
    async def mvp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⭐ Игрок матча официально определён администрацией RFL!", ephemeral=True)


# КОМАНДА /HELP
@bot.tree.command(name="help", description="Инструкция по использованию бота RFL")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Помощь по Result-Bot (RFL)",
        description="Бот предназначен для создания профессиональных карточек результатов матчей в стиле **433**.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Команда `/result`",
        value="Заполните параметры: команды, счёт, авторы голов и прикрепите логотипы файлом.",
        inline=False
    )
    embed.add_field(
        name="Кнопки под протоколом",
        value="Позволяют участникам просматривать детали матча и игрока матча в один клик.",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# КОМАНДА /RESULT
@bot.tree.command(name="result", description="Создать карточку матча 433")
@app_commands.describe(
    team1="Команда 1", score1="Счёт 1", team2="Команда 2", score2="Счёт 2",
    details="Авторы голов (например: 34' D. Szoboszlai)",
    logo1="Логотип Команды 1", logo2="Логотип Команды 2"
)
async def result(
    interaction: discord.Interaction,
    team1: str, score1: int, team2: str, score2: int,
    details: str = "Без событий",
    logo1: discord.Attachment = None, logo2: discord.Attachment = None
):
    await interaction.response.defer()

    try:
        # 1. Генерируем с помощью ИИ яркий футбольный арт с игроком для фона
        ai_prompt = "photorealistic dynamic action shot of celebration football player in stadium, epic background, sports photo 4k"
        encoded_prompt = urllib.parse.quote(ai_prompt)
        bg_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=1000&nologo=true"

        bg_img = await fetch_image(bg_url)
        logo1_img = await fetch_image(logo1.url) if logo1 else None
        logo2_img = await fetch_image(logo2.url) if logo2 else None

        # 2. Отрисовываем стиль 433 поверх ИИ-фона
        loop = asyncio.get_running_loop()
        card_buf = await loop.run_in_executor(
            None, create_433_style_card, team1, score1, team2, score2, details, bg_img, logo1_img, logo2_img
        )

        file = discord.File(fp=card_buf, filename="433_match_result.png")
        view = MatchResultView(f"{team1} {score1}:{score2} {team2}\nСобытия: {details}")

        await interaction.followup.send(
            content=f"🚨 **RFL MATCH RESULT** | {team1} vs {team2}",
            file=file,
            view=view
        )

    except Exception as e:
        await interaction.followup.send(content=f"❌ Ошибка: `{e}`")

@bot.event
async def on_ready():
    print(f"=== БОТ УСПЕШНО ЗАПУЩЕН КАК: {bot.user} ===")
    try:
        # Принудительно регистрируем команды мгновенно для всех серверов
        synced = await bot.tree.sync()
        print(f"=== СИНХРОНИЗИРОВАНО КОМАНД: {len(synced)} ===")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

TOKEN = os.getenv("BOT_TOKEN")

if __name__ == "__main__":
    if TOKEN:
        keep_alive()
        bot.run(TOKEN)