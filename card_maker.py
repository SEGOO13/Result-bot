import io
from PIL import Image, ImageDraw, ImageFont


def generate_scorecard(
    home_logo_bytes,
    away_logo_bytes,
    home_score: int,
    away_score: int,
    tour_text: str,
    home_scorers_text: str,
    away_scorers_text: str,
):
    # 1. Загружаем фон и логотипы
    background = Image.open("background.png").convert("RGBA")
    home_logo = Image.open(io.BytesIO(home_logo_bytes)).convert("RGBA")
    away_logo = Image.open(io.BytesIO(away_logo_bytes)).convert("RGBA")

    # 2. Подгоняем размеры эмблем (квадратные 250x250 под наш стильный референс)
    logo_size = (250, 250)
    home_logo = home_logo.resize(logo_size, Image.Resampling.LANCZOS)
    away_logo = away_logo.resize(logo_size, Image.Resampling.LANCZOS)

    # Вставляем лого по бокам
    background.paste(home_logo, (220, 580), home_logo)
    background.paste(away_logo, (1450, 580), away_logo)

    draw = ImageDraw.Draw(background)

    # 3. Подгружаем шрифты
    try:
        font_score = ImageFont.truetype("impact.ttf", 240)
        font_tour = ImageFont.truetype("arial.ttf", 35)
        font_names = ImageFont.truetype("arial.ttf", 32)
    except IOError:
        font_score = ImageFont.truetype("arial.ttf", 200)
        font_tour = ImageFont.load_default()
        font_names = ImageFont.load_default()

    # 4. Счёт
    draw.text((700, 700), str(home_score), fill="white", font=font_score, anchor="mm")
    draw.text((1220, 700), str(away_score), fill="white", font=font_score, anchor="mm")

    # 5. Плашка тура
    draw.rectangle([(900, 680), (1020, 730)], outline="white", width=2)
    draw.text((960, 705), tour_text, fill="white", font=font_tour, anchor="mm")

    # 6. Авторы голов (разбираем строки через запятую)
    home_list = (
        [s.strip() for s in home_scorers_text.split(",")]
        if home_scorers_text
        else []
    )
    away_list = (
        [s.strip() for s in away_scorers_text.split(",")]
        if away_scorers_text
        else []
    )

    # Слева (выравнивание вправо к центру)
    y_offset = 860
    for scorer in home_list:
        draw.text(
            (820, y_offset), scorer, fill="white", font=font_names, anchor="rm"
        )
        y_offset += 45

    # Справа (выравнивание влево от центра)
    y_offset = 860
    for scorer in away_list:
        draw.text(
            (1100, y_offset), scorer, fill="white", font=font_names, anchor="lm"
        )
        y_offset += 45

    # Сохраняем готовую картинку в виртуальную память для передачи боту
    buffer = io.BytesIO()
    background.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer