import os
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="result", description="Оформить результат матча RFL")
@app_commands.describe(
    team1="Название первой команды",
    score1="Счёт первой команды",
    team2="Название второй команды",
    score2="Счёт второй команды",
    details="Авторы голов / События матча",
    logo1="Эмблема/аватарка первой команды",
    logo2="Эмблема/аватарка второй команды"
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
    # Мгновенно говорим Discord, что приняли запрос
    await interaction.response.defer()

    try:
        # Определяем кто победил для цвета карточки
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

        # Выводим команды и счет
        embed.add_field(
            name=f"⚽ {team1}", 
            value=f"**Счёт: {score1}**", 
            inline=True
        )
        embed.add_field(
            name="VS", 
            value="⚔️", 
            inline=True
        )
        embed.add_field(
            name=f"⚽ {team2}", 
            value=f"**Счёт: {score2}**", 
            inline=True
        )

        # Подробности / Голы
        embed.add_field(
            name="📝 События и авторы голов:", 
            value=details, 
            inline=False
        )

        # Если прикрепили логотип первой команды — ставим его на иконку
        if logo1:
            embed.set_thumbnail(url=logo1.url)
        # Если прикрепили логотип второй команды — выводим его вниз
        if logo2:
            embed.set_image(url=logo2.url)

        embed.set_footer(text="Официальный результат лиги RFL")

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
    if not TOKEN:
        print("ОШИБКА: Переменная BOT_TOKEN не найдена!")
    else:
        bot.run(TOKEN)