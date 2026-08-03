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

def create_433_style_card(team1: str, score1: str, team2: str, score2: str, details: str, 
                          bg_img: Image.Image, logo1_img: Image.Image = None, logo2_img: Image.Image = None) -> io.BytesIO:
    
    width, height = 800, 1000
    
    # Фон
    bg = bg_img.resize((width, height)).convert("RGBA")

    # Градиентное затемнение снизу (чтобы крупный текст четко читался)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, 450), (width, height)], fill=(0, 0, 0, 210))
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)

    # Рамка для инфо-блока
    card_box = [(30, 580), (770, 960)]
    draw.rounded_rectangle(card_box, radius=25, outline=(255, 255, 255, 140), width=3)

    # Текст над счётом (КРУПНЫЙ)
    draw.text((width // 2, 615), "RFL MATCHDAY", fill=(220, 220, 220), anchor="mm")

    # Счёт (ОЧЕНЬ КРУПНЫЙ)
    score_text = f"{score1} - {score2}"
    draw.text((width // 2, 710), score_text, fill=(255, 255, 255), anchor="mm")

    # Статус матча
    draw.text((width // 2, 775), "FULL-TIME", fill=(234, 179, 8), anchor="mm")

    # Названия команд (КРУПНЫЕ)
    draw.text((200, 815), team1.upper(), fill=(255, 255, 255), anchor="mm")
    draw.text((600, 815), team2.upper(), fill=(255, 255, 255), anchor="mm")

    # Авторы голов / Детали
    draw.text((width // 2, 895), details, fill=(230, 230, 230), anchor="mm")

    # УВЕЛИЧЕННЫЕ ЛОГОТИПЫ КОМАНД (Размер 140x140 вместо 80x80)
    if logo1_img:
        logo1 = logo1_img.resize((140, 140))
        bg.paste(logo1, (130, 650), logo1)
    
    if logo2_img:
        logo2 = logo2_img.resize((140, 140))
        bg.paste(logo2, (530, 650), logo2)

    buf = io.BytesIO()
    bg.save(buf, format="PNG")
    buf.seek(0)
    return buf

# ВСПЛЫВАЮЩАЯ ФОРМА ВВОДА
class ResultModal(discord.ui.Modal, title="Оформление матча RFL"):
    team1 = discord.ui.TextInput(label="Команда 1", placeholder="например: BARCELONA", required=True)
    score1 = discord.ui.TextInput(label="Счёт 1", placeholder="например: 3", required=True)
    team2 = discord.ui.TextInput(label="Команда 2", placeholder="например: REAL MADRID", required=True)
    score2 = discord.ui.TextInput(label="Счёт 2", placeholder="например: 1", required=True)
    details = discord.ui.TextInput(label="События / Голы", placeholder="34' Messi, 78' Pedri", required=False, default="Без событий")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            # Четкий промпт только для классического европейского футбола (soccer)
            ai_prompt = "photorealistic dynamic action photo of a professional soccer player celebrating goal on European football stadium, Premier League style, 4k, no helmets"
            encoded_prompt = urllib.parse.quote(ai_prompt)
            bg_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=1000&nologo=true"

            bg_img = await fetch_image(bg_url)

            loop = asyncio.get_running_loop()
            card_buf = await loop.run_in_executor(
                None, create_433_style_card, 
                self.team1.value, self.score1.value, 
                self.team2.value, self.score2.value, 
                self.details.value, bg_img
            )

            file = discord.File(fp=card_buf, filename="rfl_match_result.png")
            
            view = MatchResultView(f"{self.team1.value} {self.score1.value}:{self.score2.value} {self.team2.value}\nДетали: {self.details.value}")

            await interaction.followup.send(
                content=f"🚨 **RFL MATCH RESULT** | {self.team1.value} vs {self.team2.value}",
                file=file,
                view=view
            )
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при создании карточки: `{e}`")

# ИНТЕРАКТИВНОЕ МЕНЮ С КНОПКАМИ
class ResultStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Заполнить протокол матча", style=discord.ButtonStyle.success, custom_id="btn_open_modal")
    async def open_modal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ResultModal())

class MatchResultView(discord.ui.View):
    def __init__(self, match_info: str):
        super().__init__(timeout=None)
        self.match_info = match_info

    @discord.ui.button(label="⚽ Протокол", style=discord.ButtonStyle.primary, custom_id="btn_details")
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"📋 **Подробности матча:**\n{self.match_info}", ephemeral=True)

    @discord.ui.button(label="🔥 Игрок матча", style=discord.ButtonStyle.secondary, custom_id="btn_mvp")
    async def mvp_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⭐ Игрок матча выбран администрацией RFL!", ephemeral=True)

# КОМАНДА /RESULT (Открывает меню)
@bot.tree.command(name="result", description="Открыть меню оформления матча RFL")
async def result(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚽ Центр управления результатами RFL",
        description="Нажмите на кнопку ниже, чтобы открыть удобную форму и сгенерировать карточку матча.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=ResultStartView(), ephemeral=True)

# КОМАНДА /HELP
@bot.tree.command(name="help", description="Инструкция по боту")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Помощь по Result-Bot",
        description="Используйте `/result`, чтобы вызвать меню с формой заполнения матча.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"=== БОТ УСПЕШНО ЗАПУЩЕН КАК: {bot.user} ===")
    try:
        synced = await bot.tree.sync()
        print(f"=== СИНХРОНИЗИРОВАНО КОМАНД: {len(synced)} ===")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

TOKEN = os.getenv("BOT_TOKEN")

if __name__ == "__main__":
    if TOKEN:
        keep_alive()
        bot.run(TOKEN)