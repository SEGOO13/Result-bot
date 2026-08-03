import os
import urllib.parse
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "RFL Bot is alive!"

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

@bot.tree.command(name="result", description="Оформить результат матча RFL с ИИ-артом")
@app_commands.describe(
    team1="Название первой команды",
    score1="Счёт первой команды",
    team2="Название второй команды",
    score2="Счёт второй команды",
    details="Авторы голов / События матча",
    logo1="Эмблема первой команды",
    logo2="Эмблема второй команды"
)
async def result(
    interaction: discord.Interaction, 
    team1: str, 
    score1: int, 
    team2: str, 
    score2: int,
    details: str = "Без событий",
    logo1: discord.Attachment = None,
    logo2: discord.Attachment = None
):
    await interaction.response.defer()

    try:
        # Цвет рамки
        if score1 > score2:
            embed_color = discord.Color.green()
        elif score2 > score1:
            embed_color = discord.Color.red()
        else:
            embed_color = discord.Color.gold()

        embed = discord.Embed(
            title="🏆 ПРОТОКОЛ МАТЧА RFL",
            color=embed_color
        )

        embed.add_field(name=f"⚽ {team1}", value=f"**Счёт: {score1}**", inline=True)
        embed.add_field(name="VS", value="⚔️", inline=True)
        embed.add_field(name=f"⚽ {team2}", value=f"**Счёт: {score2}**", inline=True)

        embed.add_field(name="📝 События и авторы голов:", value=details, inline=False)

        # 🤖 ИИ-Генерация картинки футбольного матча
        ai_prompt = f"cyberpunk futuristic soccer stadium match between {team1} and {team2}, final score {score1} to {score2}, neon lights, epic stadium background, high quality, 4k"
        encoded_prompt = urllib.parse.quote(ai_prompt)
        ai_image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=675&nologo=true"

        # Вставляем ИИ-арт как основную обложку карточки
        embed.set_image(url=ai_image_url)

        # Если прикрепили логотип — ставим его в иконку
        if logo1:
            embed.set_thumbnail(url=logo1.url)

        embed.set_footer(text="Официальный результат лиги RFL | AI Generated Card")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(content=f"❌ Ошибка: `{e}`")

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
    else:
        print("ОШИБКА: Переменная BOT_TOKEN не найдена!")