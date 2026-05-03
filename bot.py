import cv2
import numpy as np
from deepface import DeepFace
import mediapipe as mp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import tempfile
import os

TELEGRAM_TOKEN = "8774144586:AAG_h4h3uW8QnR-YtODLorKwgT7d7PiCBmc"

mp_face_mesh = mp.solutions.face_mesh

def analyze_face(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return "❌ Не удалось загрузить фото"

    scores = {}

    # 1. DeepFace — возраст, пол, эмоции
    try:
        analysis = DeepFace.analyze(
            img_path=image_path,
            actions=["age", "gender", "emotion"],
            enforce_detection=False
        )
        if isinstance(analysis, list):
            analysis = analysis[0]

        age = analysis["age"]
        gender = analysis["dominant_gender"]
        emotion = analysis["dominant_emotion"]
        scores["age"] = age
        scores["gender"] = gender
        scores["emotion"] = emotion
    except Exception as e:
        scores["deepface_error"] = str(e)

    # 2. MediaPipe — симметрия и пропорции лица
    symmetry_score = 0
    proportion_score = 0

    try:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        with mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True
        ) as face_mesh:
            results = face_mesh.process(rgb)

            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                h, w = img.shape[:2]

                # Получаем координаты ключевых точек
                def get_point(idx):
                    lm = landmarks[idx]
                    return np.array([lm.x * w, lm.y * h])

                # --- Симметрия ---
                # Сравниваем левую и правую стороны лица
                pairs = [
                    (33, 263),   # уголки глаз
                    (61, 291),   # уголки рта
                    (70, 300),   # брови
                    (234, 454),  # скулы
                    (132, 361),  # щёки
                ]

                sym_diffs = []
                nose_tip = get_point(1)
                for left_idx, right_idx in pairs:
                    left = get_point(left_idx)
                    right = get_point(right_idx)
                    center_x = nose_tip[0]
                    dist_left = abs(left[0] - center_x)
                    dist_right = abs(right[0] - center_x)
                    if dist_left + dist_right > 0:
                        diff = abs(dist_left - dist_right) / ((dist_left + dist_right) / 2)
                        sym_diffs.append(diff)

                avg_asymmetry = np.mean(sym_diffs) if sym_diffs else 1
                # Чем меньше асимметрия — тем лучше
                symmetry_score = max(0, 100 - avg_asymmetry * 300)

                # --- Пропорции (золотое сечение) ---
                # Идеальное соотношение высоты к ширине лица ≈ 1.618
                left_cheek = get_point(234)
                right_cheek = get_point(454)
                chin = get_point(152)
                forehead = get_point(10)

                face_width = np.linalg.norm(right_cheek - left_cheek)
                face_height = np.linalg.norm(chin - forehead)

                if face_width > 0:
                    ratio = face_height / face_width
                    golden = 1.618
                    deviation = abs(ratio - golden) / golden
                    proportion_score = max(0, 100 - deviation * 200)

                scores["symmetry"] = round(symmetry_score, 1)
                scores["proportions"] = round(proportion_score, 1)

    except Exception as e:
        scores["mediapipe_error"] = str(e)

    # --- Jawline (резкость нижней части лица) ---
    jawline_score = 0
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Нижняя треть лица
        lower_face = gray[int(h * 0.65):, :]
        edges = cv2.Canny(lower_face, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        jawline_score = min(100, edge_density * 2000)
        scores["jawline"] = round(jawline_score, 1)
    except:
        pass

    # --- Итоговый рейтинг ---
    total = 0
    count = 0

    if "symmetry" in scores:
        total += scores["symmetry"] * 0.4  # 40% веса
        count += 1
    if "proportions" in scores:
        total += scores["proportions"] * 0.35  # 35% веса
        count += 1
    if "jawline" in scores:
        total += scores["jawline"] * 0.25  # 25% веса
        count += 1

    final_score = total if count > 0 else 50

    # --- Определяем tier ---
    if final_score >= 82:
        tier = "👑 CHAD"
        desc = "Топ уровень. Выдающиеся черты лица."
    elif final_score >= 68:
        tier = "⬆️ HTN (High Tier Normal)"
        desc = "Выше среднего. Привлекательная внешность."
    elif final_score >= 50:
        tier = "➡️ MTN (Mid Tier Normal)"
        desc = "Средний уровень. Обычная внешность."
    elif final_score >= 35:
        tier = "⬇️ LTN (Lower Than Normal)"
        desc = "Чуть ниже среднего."
    else:
        tier = "💀 Sub 5"
        desc = "Ниже среднего."

    # --- Формируем ответ ---
    result = f"📊 *Результат анализа*\n\n"
    result += f"*Оценка:* {tier}\n"
    result += f"*Итоговый балл:* {round(final_score, 1)}/100\n\n"
    result += f"📐 *Симметрия лица:* {scores.get('symmetry', 'н/д')}/100\n"
    result += f"📏 *Пропорции:* {scores.get('proportions', 'н/д')}/100\n"
    result += f"🦷 *Jawline:* {scores.get('jawline', 'н/д')}/100\n\n"

    if "age" in scores:
        result += f"🎂 *Возраст:* ~{scores['age']} лет\n"
    if "gender" in scores:
        result += f"👤 *Пол:* {scores['gender']}\n"
    if "emotion" in scores:
        result += f"😐 *Эмоция:* {scores['emotion']}\n\n"

    result += f"_{desc}_"
    return result


async def analyze_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    msg = await update.message.reply_text("Анализирую фото... 🔍")

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await file.download_to_drive(tmp_path)
        result = analyze_face(tmp_path)
        await msg.edit_text(result, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {str(e)}")
    finally:
        os.unlink(tmp_path)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Скинь чёткое фото лица — проведу анализ:\n"
        "• Симметрия лица\n"
        "• Пропорции (золотое сечение)\n"
        "• Jawline\n\n"
        "📊 Шкала: Sub 5 → LTN → MTN → HTN → Chad"
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, analyze_photo))
    print("Бот запущен...")
    app.run_polling()
