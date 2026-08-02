import os
import asyncio
from aiohttp import web
import discord
from discord.ext import commands
from card_maker import generate_scorecard

# === 1. ВЕБ-СЕРВЕР ДЛЯ RENDER (поддержание 24/7) ===
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")


# === 2. ФОРМА ВВОДА РЕЗУЛЬТАТОВ (MODAL) ===
class MatchResultModal(discord.ui.Modal, title="Ввод результата матча RFL"):
    team1 = discord.ui.TextInput(
        label="Команда 1 и счёт", 
        placeholder="Например: Спартак 2"
    )
    team2 = discord.ui.TextInput(
        label="Команда 2 и счёт", 
        placeholder="Например: ЦСКА 1"
    )
    scorers = discord.ui.TextInput(
        label="Авторы голов / События матча", 
        style=discord.TextStyle.paragraph,
        placeholder="Например: 15' Иванов, 70' Петров — 40' Сидоров",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Генерирую карточку матча...", ephemeral=True)
        
        # Генерация изображения через Pillow
        image_path = generate_scorecard(
            team1=self.team1.value, 
            team2=self.team2.value, 
            details=self.scorers.value
        )

        # Отправка карточки в публичный чат
        file = discord.File(image_path, filename="result.png")
        await interaction.channel.send(content="⚽ **Результат матча RFL**", file=file)


# === 3. ИНТЕРАКТИВНОЕ МЕНЮ (VIEW) ===
class MatchMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Оформить результат матча", style=discord.ButtonStyle.success, emoji="⚽")
    async def make_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultModal())

    @discord.ui.button(label="Закрыть", style=discord.ButtonStyle.danger)
    async def close_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


# === 4. НАСТРОЙКА БОТА ===
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Бот запущен как {bot.user}')


# === 5. СЛЭШ-КОМАНДЫ (/rfl и /help) ===

@bot.tree.command(name="rfl", description="Панель администратора RFL для генерации карточек")
async def open_menu(interaction: discord.Interaction):
    view = MatchMenu()
    await interaction.response.send_message(
        "### 🏆 Управление результатами RFL\nНажми кнопку ниже, чтобы ввести счет матча:", 
        view=view, 
        ephemeral=True
    )


@bot.tree.command(name="help", description="Инструкция по использованию бота RFL")
async def show_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Справка и инструкция по RFL Results Bot",
        description="Данный бот предназначен для автоматической генерации графических карточек с результатами матчей лиги RFL.",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📌 Основные команды:",
        value=(
            "`/rfl` — Открывает приватное меню для создания карточки матча.\n"
            "`/help` — Показывает эту инструкцию."
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚽ Как опубликовать результат матча:",
        value=(
            "1. Введи команду `/rfl` в нужном текстовом канале.\n"
            "2. Нажми зеленую кнопку **«Оформить результат матча»** (меню видно только тебе).\n"
            "3. В открывшемся окне заполни поля:\n"
            "   • **Команда 1 и счёт** (напр. *Команда А 3*)\n"
            "   • **Команда 2 и счёт** (напр. *Команда Б 1*)\n"
            "   • **Авторы голов** (необязательное поле, можно указать минутники и авторов).\n"
            "4. Нажми кнопку **Отправить**. Бот автоматически сгенерирует изображение и опубликует его в чат."
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔒 Приватность:",
        value="Все команды управления (`/rfl`, `/help`) работают в интерактивном режиме (ephemeral). Процесс заполнения формы видишь **только ты**, а итоговая картинка публикуется в общий доступ.",
        inline=False
    )
    
    embed.set_footer(text="RFL Bot System • Render 24/7 Hosted")

    # ephemeral=True — справка показывается только вызвавшему пользователю
    await interaction.response.send_message(embed=embed, ephemeral=True)


# === 6. ЗАПУСК БОТА И ВЕБ-СЕРВЕРА ===
async def main():
    await start_web_server()
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("ОШИБКА: Переменная BOT_TOKEN не найдена!")
        return
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())ы