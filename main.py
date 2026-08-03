import os
import io
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Функция для скачивания изображения по URL
async def download_image(url: str) -> Image.Image:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.read()
                return Image.open(io.BytesIO(data)).convert("RGBA")
    return None

# Генерация красивой карточки с помощью Pillow
def generate_card(team1_name: str, score1: str, team2_name: str, score2: str, 
                  details: str, logo1_img: Image.Image = None, logo2_img: Image.Image = None) -> io.BytesIO:
    
    # Создаём холст 1200x675 (стандартное соотношение 16:9)
    width, height = 1200, 675
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255)) # Темно-синий/углистый фон
    draw = ImageDraw.Draw(img)

    # Рисуем стильную рамку и градиентные акценты
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(56, 189, 248), width=3)
    draw.rectangle([(25, 25), (width - 25, 100)], fill=(30, 41, 59))
    
    # Заголовок RFL
    draw.text((width // 2, 60), "RFL MATCH RESULT", fill=(255, 255, 255), anchor="mm")

    # Карточки Команды 1 и Команды 2
    # Зелёный блок слева, Красный/Оранжевый справа
    draw.rounded_rectangle([(50, 130), (560, 480)], radius=15, fill=(22, 101, 52, 220), outline=(34, 197, 94), width=2)
    draw.rounded_rectangle([(640, 130), (1150, 480)], radius=15, fill=(153, 27, 27, 220), outline=(239, 68, 68), width=2)

    # Отрисовка Логотипа 1
    if logo1_img:
        logo1_img.thumbnail((120, 120))
        img.paste(logo1_img, (90, 150), logo1_img)
    
    # Отрисовка Логотипа 2
    if logo2_img:
        logo2_img.thumbnail((120, 120))
        img.paste(logo2_img, (680, 150), logo2_img)

    # Названия команд и счёт
    draw.text((320, 180), team1_name.upper(), fill=(255, 255, 255), anchor="mm")
    draw.text((320, 260), str(score1), fill=(255, 255, 255), anchor="mm")

    draw.text((910, 180), team2_name.upper(), fill=(255, 255, 255), anchor="mm")
    draw.text((910, 260), str(score2), fill=(255, 255, 255), anchor="mm")

    # Линия разделения и авторы голов
    draw.line([(70, 320), (540, 320)], fill=(34, 197, 94), width=2)
    draw.line([(660, 320), (1130, 320)], fill=(239, 68, 68), width=2)

    # Текст деталей / событий
    draw.text((70, 340), details or "Без забитых мячей", fill=(226, 232, 240))

    # Подпись снизу
    draw.rectangle([(50, 510), (1150, 620)], fill=(30, 41, 59))
    draw.text((width // 2, 565), f"Официальный протокол матча RFL | {team1_name} {score1} : {score2} {team2_name}", fill=(148, 163, 184), anchor="mm")

    # Сохраняем в буфер
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

@bot.tree.command(name="result", description="Оформить результат матча с логотипами")
@app_commands.describe(
    team1="Название первой команды",
    score1="Счёт первой команды",
    team2="Название второй команды",
    score2="Счёт второй команды",
    details="Авторы голов / События",
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
    # Показываем статус загрузки (чтобы не было "Приложение не отвечает")
    await interaction.response.defer(thinking=True)

    try:
        # Скачиваем эмблемы, если прикреплены
        img_logo1 = await download_image(logo1.url) if logo1 else None
        img_logo2 = await download_image(logo2.url) if logo2 else None

        # Генерируем карточку
        loop = asyncio.get_running_loop()
        card_buf = await loop.run_in_executor(
            None, generate_card, team1, str(score1), team2, str(score2), details, img_logo1, img_logo2
        )

        file = discord.File(fp=card_buf, filename="rfl_match_result.png")
        
        await interaction.followup.send(
            content=f"⚽ **МАТЧ ОКОНЧЕН!**\n🏆 **{team1}** {score1} : {score2} **{team2}**",
            file=file
        )

    except Exception as e:
        await interaction.followup.send(content=f"❌ Ошибка при формировании карточки: `{e}`")

@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано команд: {len(synced)}")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

TOKEN = os.getenv("BOT_TOKEN")

async def main():
    if not TOKEN:
        print("ОШИБКА: Переменная BOT_TOKEN не найдена!")
        return
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())