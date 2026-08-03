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

def get_font(size: int):
    # Пытаемся загрузить стандартный шрифт, если нет — дефолтный
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        try:
            return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        except:
            return ImageFont.load_default()

def create_433_style_card(team1: str, score1: str, team2: str, score2: str, 
                          events1: str, events2: str, bg_img: Image.Image) -> io.BytesIO:
    
    width, height = 1000, 1000
    
    # Фон
    bg = bg_img.resize((width, height)).convert("RGBA")

    # Тёмный слой-оверлей для контраста
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    # Затемняем всю нижнюю половину
    overlay_draw.rectangle([(0, 300), (width, height)], fill=(10, 15, 25, 220))
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    # Шрифт разного размера
    font_title = get_font(36)
    font_score = get_font(110)
    font_team = get_font(50)
    font_status = get_font(32)
    font_events = get_font(28)

    # Рамка блока карточки
    card_box = [(50, 400), (950, 930)]
    draw.rounded_rectangle(card_box, radius=30, outline=(255, 255, 255, 180), width=4)

    # Заголовок RFL MATCHDAY
    draw.text((width // 2, 450), "RFL MATCHDAY", fill=(200, 200, 200), font=font_title, anchor="mm")

    # Названия команд (БОЛЬШИЕ)
    draw.text((260, 530), team1.upper(), fill=(255, 255, 255), font=font_team, anchor="mm")
    draw.text((740, 530), team2.upper(), fill=(255, 255, 255), font=font_team, anchor="mm")

    # Счёт (ОГРОМНЫЙ)
    score_text = f"{score1}  -  {score2}"
    draw.text((width // 2, 630), score_text, fill=(255, 255, 255), font=font_score, anchor="mm")

    # Статус FULL-TIME
    draw.text((width // 2, 720), "FULL-TIME", fill=(234, 179, 8), font=font_status, anchor="mm")

    # Разделительная линия для событий
    draw.line([(100, 760), (900, 760)], fill=(255, 255, 255, 80), width=2)

    # События Команды 1 (Слева)
    draw.text((260, 830), events1, fill=(220, 220, 220), font=font_events, anchor="mm")

    # События Команды 2 (Справа)
    draw.text((740, 830), events2, fill=(220, 220, 220), font=font_events, anchor="mm")

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ВСПЛЫВАЮЩАЯ ФОРМА С РАЗДЕЛЬНЫМИ СОБЫТИЯМИ
class ResultModal(discord.ui.Modal, title="Оформление матча RFL"):
    team1 = discord.ui.TextInput(label="Команда 1", placeholder="например: BAYER 04", required=True)
    score1 = discord.ui.TextInput(label="Счёт 1", placeholder="например: 2", required=True)
    events1 = discord.ui.TextInput(label="Голы / События Команды 1", placeholder="34' Schick\n67' Wirtz", required=False, default="-")
    
    team2 = discord.ui.TextInput(label="Команда 2", placeholder="например: VALENCIA", required=True)
    score2 = discord.ui.TextInput(label="Счёт 2", placeholder="например: 0", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            # Генерация чистого красивого фона футбольной арены без "уродливых ИИ-людей"
            ai_prompt = "abstract dark moody soccer stadium lights background, blue and gold neon atmosphere, professional sports photography, 4k"
            encoded_prompt = urllib.parse.quote(ai_prompt)
            bg_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1000&height=1000&nologo=true"

            bg_img = await fetch_image(bg_url)

            # Если фон не загрузился — создаем тёмный запасной
            if not bg_img:
                bg_img = Image.new("RGBA", (1000, 1000), (15, 23, 42))

            loop = asyncio.get_running_loop()
            card_buf = await loop.run_in_executor(
                None, create_433_style_card, 
                self.team1.value, self.score1.value, 
                self.team2.value, self.score2.value, 
                self.events1.value, "-", bg_img
            )

            file = discord.File(fp=card_buf, filename="rfl_match_result.png")
            
            view = MatchResultView(f"**{self.team1.value}** ({self.score1.value}) vs ({self.score2.value}) **{self.team2.value}**\n\n⚽ **События:**\n{self.events1.value}")

            await interaction.followup.send(
                content=f"🚨 **RFL MATCH RESULT** | {self.team1.value} vs {self.team2.value}",
                file=file,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка: `{e}`")

# КНОПКИ ПОД КАРТОЧКОЙ МАТЧА
class MatchResultView(discord.ui.View):
    def __init__(self, match_info: str):
        super().__init__(timeout=None)
        self.match_info = match_info

    @discord.ui.button(label="📋 Протокол", style=discord.ButtonStyle.primary, custom_id="btn_details")
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"📋 **Подробности матча:**\n{self.match_info}", ephemeral=True)

    @discord.ui.button(label="⭐ MVP Матча", style=discord.ButtonStyle.success, custom_id="btn_mvp")
    async def mvp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⭐ **Игрок матча** будет определён отдельным голосованием!", ephemeral=True)

    @discord.ui.button(label="📊 Таблица", style=discord.ButtonStyle.secondary, custom_id="btn_table")
    async def table_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📊 Турнирная таблица обновляется после каждого тура.", ephemeral=True)

# СТАРТОВОЕ МЕНЮ
class ResultStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Заполнить протокол", style=discord.ButtonStyle.success, custom_id="btn_open_modal")
    async def open_modal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ResultModal())

@bot.tree.command(name="result", description="Открыть панель оформления матча RFL")
async def result(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚽ Центр управления RFL",
        description="Нажмите кнопку ниже для заполнения данных матча.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=ResultStartView(), ephemeral=True)

@bot.tree.command(name="help", description="Помощь по боту")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("Используйте `/result` для вызова формы результата.", ephemeral=True)

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