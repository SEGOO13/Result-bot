import os
import io
import discord
from discord import app_commands
from discord.ext import commands
import asyncio

# Импортируем твою функцию генерации из card_maker.py
try:
    from card_maker import create_match_card
except ImportError:
    # Заглушка, если функции в card_maker еще нет
    def create_match_card(team1, score1, team2, score2, events, logo1_url=None, logo2_url=None):
        return None

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class MatchResultModal(discord.ui.Modal, title="Ввод результата матча RFL"):
    team1_input = discord.ui.TextInput(
        label="Команда 1 и счёт",
        placeholder="Например: Реал Мадрид 2",
        required=True
    )
    team2_input = discord.ui.TextInput(
        label="Команда 2 и счёт",
        placeholder="Например: Барселона 1",
        required=True
    )
    logo_urls = discord.ui.TextInput(
        label="Ссылки на логотипы (необязательно)",
        placeholder="URL_Команды_1 | URL_Команды_2 (через знак |)",
        required=False,
        style=discord.TextStyle.paragraph
    )
    events_input = discord.ui.TextInput(
        label="Авторы голов / События матча",
        placeholder="Например: 15' Бензема, 70' Винисиус — 40' Месси",
        style=discord.TextStyle.paragraph,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Оповещаем Discord, что мы приняли запрос и обрабатываем его (чтобы не было таймаута)
        await interaction.response.defer(thinking=True)

        try:
            # Разбираем ввод команд
            t1_val = self.team1_input.value.strip().rsplit(' ', 1)
            t2_val = self.team2_input.value.strip().rsplit(' ', 1)

            team1 = t1_val[0] if len(t1_val) > 0 else "Команда 1"
            score1 = t1_val[1] if len(t1_val) > 1 else "0"

            team2 = t2_val[0] if len(t2_val) > 0 else "Команда 2"
            score2 = t2_val[1] if len(t2_val) > 1 else "0"

            # Ссылки на логотипы
            logo1, logo2 = None, None
            if self.logo_urls.value:
                parts = self.logo_urls.value.split('|')
                logo1 = parts[0].strip() if len(parts) > 0 else None
                logo2 = parts[1].strip() if len(parts) > 1 else None

            events = self.events_input.value or "Без событий"

            # Запускаем генерацию карточки в отдельном потоке, чтобы не блокировать бота
            loop = asyncio.get_running_loop()
            img_bytes = await loop.run_in_executor(
                None, 
                create_match_card, 
                team1, score1, team2, score2, events, logo1, logo2
            )

            if img_bytes:
                file = discord.File(fp=img_bytes, filename="result.png")
                await interaction.followup.send(
                    content=f"⚽ **Результат матча RFL:** {team1} **{score1} : {score2}** {team2}",
                    file=file
                )
            else:
                await interaction.followup.send(
                    content=f"⚽ **Результат матча RFL:**\n**{team1}** {score1} : {score2} **{team2}**\n\n📝 **События:**\n{events}"
                )

        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при генерации карточки: `{e}`")

class ResultView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Оформить результат матча", style=discord.ButtonStyle.green, emoji="⚽")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultModal())

    @discord.ui.button(label="Закрыть", style=discord.ButtonStyle.red)
    async def close_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Меню закрыто.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано команд: {len(synced)}")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

# Заменили /rfl на /result
@bot.tree.command(name="result", description="Управление результатами матчей RFL")
async def result_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏆 Управление результатами RFL",
        description="Нажми кнопку ниже, чтобы ввести счет матча и сгенерировать карточку:",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=ResultView(), ephemeral=True)

TOKEN = os.getenv("BOT_TOKEN")

async def main():
    if not TOKEN:
        print("ОШИБКА: Переменная BOT_TOKEN не найдена!")
        return
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())