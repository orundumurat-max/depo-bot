import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8960271967:AAGEuwGjVEmc0kj76OnVB4Z6EiBlV_THjiQ"

(LANG, DEPO_TIPI, KORIDOR_TIPI, UZUNLUK, GENISLIK, PALET, KAT, YUKSEKLIK,
 CONFIRM_UZUNLUK, CONFIRM_GENISLIK, CONFIRM_PALET, CONFIRM_KAT, CONFIRM_YUKSEKLIK,
 YATAY_FIYAT, DIKEY_FIYAT, ANKRAJ_FIYAT, FIKSATOR_FIYAT,
 ZEMIN_ADET, ZEMIN_FIYAT, TRANSPORT, MONTAJ) = range(21)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def devam_kb(lang):
    if lang == 'tr':
        return ReplyKeyboardMarkup([["✅ Devam", "🔄 Düzelt", "❌ Baştan"]], one_time_keyboard=True, resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["✅ Далее", "🔄 Исправить", "❌ Сначала"]], one_time_keyboard=True, resize_keyboard=True)

def is_devam(txt, lang):
    return "devam" in txt.lower() or "далее" in txt.lower() or "✅" in txt

def is_duzelt(txt, lang):
    return "düzelt" in txt.lower() or "исправ" in txt.lower() or "🔄" in txt

def is_bastan(txt, lang):
    return "baştan" in txt.lower() or "сначала" in txt.lower() or "❌" in txt

def teknik_resim_ciz(uzunluk, genislik, raf_genislik, koridor, raf_satir, raf_perz, kat, yukseklik, depo_tipi, lang):
    W, H = 1000, 720
    img = Image.new('RGB', (W, H), color='#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        fn = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except:
        fb = ImageFont.load_default()
        fn = ImageFont.load_default()
        ft = ImageFont.load_default()

    MAVI = '#4a9eff'
    TURUNCU = '#ff8c42'
    YESIL = '#4ade80'
    BEYAZ = '#e0e0e0'
    GRI = '#303050'
    AGRI = '#505070'
    SARI = '#ffd700'
    SINIR = '#00b4d8'

    # Plan alani
    pad_left = 70
    pad_top = 55
    pad_right = 30
    info_h = 130
    pad_bot = info_h + 20

    plan_w = W - pad_left - pad_right
    plan_h = H - pad_top - pad_bot

    scale_x = plan_w / uzunluk
    scale_y = plan_h / genislik
    ox = pad_left
    oy = pad_top

    # Baslik
    draw.rectangle([0, 0, W, 42], fill='#161b22')
    if lang == 'tr':
        baslik = f"DEPO STELAJLARI — TEKNİK ÇİZİM  |  Tip: {depo_tipi}"
    else:
        baslik = f"СКЛАДСКИЕ СТЕЛЛАЖИ — ТЕХНИЧЕСКИЙ ЧЕРТЁЖ  |  Тип: {depo_tipi}"
    draw.text((W//2, 21), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo siniri
    draw.rectangle([ox, oy, ox+plan_w, oy+plan_h], outline=SINIR, width=3)

    # Giris (alt orta)
    gx = ox + plan_w // 2
    draw.line([gx-35, oy+plan_h, gx+35, oy+plan_h], fill=SARI, width=6)
    draw.text((gx, oy+plan_h+12), "GİRİŞ" if lang=='tr' else "ВХОД", fill=SARI, font=fn, anchor='mt')

    # Raflar
    for row in range(raf_satir):
        ry1 = oy + int((raf_genislik/2 + row*(raf_genislik+koridor)) * scale_y)
        ry2 = ry1 + int(raf_genislik * scale_y)
        ry2 = max(ry2, ry1+18)

        for col in range(raf_perz):
            rx1 = ox + int(col * 1.1 * scale_x) + 1
            rx2 = ox + int((col+1) * 1.1 * scale_x) - 1
            rx2 = max(rx2, rx1+10)

            # Raf icini doldur (koyu)
            draw.rectangle([rx1, ry1, rx2, ry2], fill='#0a1628')

            # Capraz cizgiler
            draw.line([rx1, ry1, rx2, ry2], fill=GRI, width=1)
            draw.line([rx2, ry1, rx1, ry2], fill=GRI, width=1)

            # Raf cercevesi (gri)
            draw.rectangle([rx1, ry1, rx2, ry2], outline=AGRI, width=1)

            # Yatay baglantilar (turuncu - ust/alt kenар)
            draw.line([rx1+5, ry1, rx2-5, ry1], fill=TURUNCU, width=3)
            draw.line([rx1+5, ry2, rx2-5, ry2], fill=TURUNCU, width=3)

            # Derinlik baglantisi (yesil - sol/sag kenar)
            draw.line([rx1, ry1+5, rx1, ry2-5], fill=YESIL, width=2)
            draw.line([rx2, ry1+5, rx2, ry2-5], fill=YESIL, width=2)

            # Dikmeler (mavi daire - 4 kose)
            r = 5
            for px, py in [(rx1, ry1), (rx2, ry1), (rx1, ry2), (rx2, ry2)]:
                draw.ellipse([px-r, py-r, px+r, py+r], fill=MAVI, outline='#ffffff', width=1)

        # Raf etiketi (sag)
        lbl = f"{'Raf' if lang=='tr' else 'Ряд'} {row+1}  {raf_genislik}m"
        draw.text((ox+plan_w+6, (ry1+ry2)//2), lbl, fill=BEYAZ, font=fn, anchor='lm')

        # Koridor genislik etiketi
        if row < raf_satir - 1:
            ky = ry2 + int(koridor*scale_y/2)
            klbl = f"{koridor}m" 
            draw.text((ox+plan_w+6, ky), klbl, fill=AGRI, font=fn, anchor='lm')

    # Olcu: uzunluk (ust)
    draw.line([ox, oy-18, ox+plan_w, oy-18], fill=AGRI, width=1)
    draw.line([ox, oy-24, ox, oy-12], fill=AGRI, width=1)
    draw.line([ox+plan_w, oy-24, ox+plan_w, oy-12], fill=AGRI, width=1)
    draw.text((ox+plan_w//2, oy-18), f"{uzunluk} m", fill=BEYAZ, font=fn, anchor='mm')

    # Olcu: genislik (sol)
    draw.line([ox-18, oy, ox-18, oy+plan_h], fill=AGRI, width=1)
    draw.line([ox-24, oy, ox-12, oy], fill=AGRI, width=1)
    draw.line([ox-24, oy+plan_h, ox-12, oy+plan_h], fill=AGRI, width=1)
    draw.text((ox-32, oy+plan_h//2), f"{genislik} m", fill=BEYAZ, font=fn, anchor='mm')

    # Alt bilgi bolumu
    info_y = H - info_h - 5
    draw.rectangle([0, info_y, W, H], fill='#161b22')
    draw.line([0, info_y, W, info_y], fill='#30363d', width=1)

    # Sol: renk aciklamalari + olcular
    sol_x = 30
    sy = info_y + 14

    # Renkler
    renk_items = [
        (MAVI,    "● " + ("Dikme" if lang=='tr' else "Стойка"),          f"{yukseklik} m"),
        (TURUNCU, "━ " + ("Yatay Bağlantı" if lang=='tr' else "Балка"),   f"{raf_genislik} m"),
        (YESIL,   "│ " + ("Derinlik" if lang=='tr' else "Глубина"),        "1.10 m"),
    ]
    for renk, isim, olcu in renk_items:
        draw.text((sol_x, sy), isim, fill=renk, font=fb)
        draw.text((sol_x+220, sy), olcu, fill=BEYAZ, font=fb)
        sy += 28

    # Orta: ayirici
    draw.line([W//2-20, info_y+10, W//2-20, H-10], fill='#30363d', width=1)

    # Sag: raf bilgileri
    sag_x = W//2
    sy2 = info_y + 14
    if lang == 'tr':
        bilgiler = [
            ("Kat Sayısı", str(kat)),
            ("Raf Satırı", str(raf_satir)),
            ("Sütun Sayısı", str(raf_perz)),
            ("Toplam Raf", str(raf_satir * raf_perz)),
        ]
    else:
        bilgiler = [
            ("Ярусов", str(kat)),
            ("Рядов", str(raf_satir)),
            ("Колонн", str(raf_perz)),
            ("Всего стеллажей", str(raf_satir * raf_perz)),
        ]
    for k, v in bilgiler:
        draw.text((sag_x, sy2), k + ":", fill=AGRI, font=fn)
        draw.text((sag_x+200, sy2), v, fill=BEYAZ, font=fb)
        sy2 += 26

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150, 150))
    buf.seek(0)
    return buf

# --- HANDLERS ---

async def start(update, context):
    kb = [["🇹🇷 Türkçe", "🇷🇺 Русский"]]
    await update.message.reply_text(
        "🌐 Dil seçin / Выберите язык:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return LANG

async def hesapla(update, context):
    kb = [["🇹🇷 Türkçe", "🇷🇺 Русский"]]
    await update.message.reply_text(
        "🌐 Dil seçin / Выберите язык:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return LANG

async def lang_sec(update, context):
    t = update.message.text
    context.user_data['lang'] = 'ru' if "Русский" in t else 'tr'
    lang = get_lang(context)
    kb = [["I", "L", "U"]]
    msg = ("🏭 Depo şeklini seçin:\n🔹 I — Düz sıralar\n🔹 L — İki duvara\n🔹 U — Üç duvara"
           if lang == 'tr' else
           "🏭 Форма склада:\n🔹 I — Прямые ряды\n🔹 L — Вдоль двух стен\n🔹 U — Вдоль трёх стен")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return DEPO_TIPI

async def depo_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.strip().upper()[0]
    if t not in ['I','L','U']:
        await update.message.reply_text("⚠️ I, L veya U girin." if lang=='tr' else "⚠️ Введите I, L или U.")
        return DEPO_TIPI
    context.user_data['depo_tipi'] = t
    kb = [["🚜 Forklift", "🔧 Transpalet", "👐 El ile"]]
    msg = ("🚦 Koridor tipini seçin:\n🚜 Forklift (3.0m)\n🔧 Transpalet (2.0m)\n👐 El ile (1.2m)"
           if lang=='tr' else
           "🚦 Тип прохода:\n🚜 Погрузчик (3.0м)\n🔧 Транспалет (2.0м)\n👐 Ручной (1.2м)")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return KORIDOR_TIPI

async def koridor_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "forklift" in t or "погрузчик" in t:
        context.user_data['koridor_tipi'] = 'forklift'
    elif "transpalet" in t or "транспалет" in t:
        context.user_data['koridor_tipi'] = 'transpalet'
    else:
        context.user_data['koridor_tipi'] = 'el'
    msg = "📏 Depo uzunluğu (m):\nÖrnek: 20" if lang=='tr' else "📏 Длина склада (м):\nПример: 20"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk(update, context):
    lang = get_lang(context)
    try:
        v = float(update.message.text.replace(',','.'))
        context.user_data['uzunluk'] = v
        msg = f"📏 Uzunluk: {v}m\n✅ Devam et?" if lang=='tr' else f"📏 Длина: {v}м\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_UZUNLUK
    except:
        await update.message.reply_text("⚠️ Sadece rakam girin. Örnek: 20" if lang=='tr' else "⚠️ Только цифры. Пример: 20")
        return UZUNLUK

async def confirm_uzunluk(update, context):
    lang = get_lang(context)
    t = update.message.text
    if is_bastan(t, lang):
        return await hesapla(update, context)
    if is_duzelt(t, lang):
        msg = "📏 Depo uzunluğu (m):" if lang=='tr' else "📏 Длина склада (м):"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return UZUNLUK
    msg = "📐 Depo genişliği (m):\nÖrnek: 12" if lang=='tr' else "📐 Ширина склада (м):\nПример: 12"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return GENISLIK

async def genislik(update, context):
    lang = get_lang(context)
    try:
        v = float(update.message.text.replace(',','.'))
        context.user_data['genislik'] = v
        msg = f"📐 Genişlik: {v}m\n✅ Devam et?" if lang=='tr' else f"📐 Ширина: {v}м\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_GENISLIK
    except:
        await update.message.reply_text("⚠️ Sadece rakam girin." if lang=='tr' else "⚠️ Только цифры.")
        return GENISLIK

async def confirm_genislik(update, context):
    lang = get_lang(context)
    t = update.message.text
    if is_bastan(t, lang): return await hesapla(update, context)
    if is_duzelt(t, lang):
        msg = "📐 Depo genişliği (m):" if lang=='tr' else "📐 Ширина склада (м):"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return GENISLIK
    kb = [["1","2"],["3","4"]]
    msg = ("📦 Raf başına palet:\n1️⃣ 0.95m  2️⃣ 1.85m\n3️⃣ 2.70m  4️⃣ 3.60m"
           if lang=='tr' else
           "📦 Паллет на ряд:\n1️⃣ 0.95м  2️⃣ 1.85м\n3️⃣ 2.70м  4️⃣ 3.60м")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return PALET

async def palet(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet'] = v
        rg = PALET_GENISLIK[v]
        msg = f"📦 Palet: {v} ({rg}m)\n✅ Devam et?" if lang=='tr' else f"📦 Паллет: {v} ({rg}м)\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_PALET
    except:
        await update.message.reply_text("⚠️ 1, 2, 3 veya 4 girin." if lang=='tr' else "⚠️ Введите 1, 2, 3 или 4.")
        return PALET

async def confirm_palet(update, context):
    lang = get_lang(context)
    t = update.message.text
    if is_bastan(t, lang): return await hesapla(update, context)
    if is_duzelt(t, lang):
        kb = [["1","2"],["3","4"]]
        msg = "📦 Raf başına palet:" if lang=='tr' else "📦 Паллет на ряд:"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        return PALET
    msg = "🏗 Kat sayısı:\nÖrnek: 3" if lang=='tr' else "🏗 Количество ярусов:\nПример: 3"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return KAT

async def kat(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text)
        context.user_data['kat'] = v
        msg = f"🏗 Kat sayısı: {v}\n✅ Devam et?" if lang=='tr' else f"🏗 Ярусов: {v}\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_KAT
    except:
        await update.message.reply_text("⚠️ Sadece rakam girin." if lang=='tr' else "⚠️ Только цифры.")
        return KAT

async def confirm_kat(update, context):
    lang = get_lang(context)
    t = update.message.text
    if is_bastan(t, lang): return await hesapla(update, context)
    if is_duzelt(t, lang):
        msg = "🏗 Kat sayısı:" if lang=='tr' else "🏗 Количество ярусов:"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return KAT
    msg = "📏 Raf yüksekliği (m):\nÖrnek: 5" if lang=='tr' else "📏 Высота стеллажа (м):\nПример: 5"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return YUKSEKLIK

async def yukseklik(update, context):
    lang = get_lang(context)
    try:
        v = float(update.message.text.replace(',','.'))
        context.user_data['yukseklik'] = v
        msg = f"📏 Yükseklik: {v}m\n✅ Devam et?" if lang=='tr' else f"📏 Высота: {v}м\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_YUKSEKLIK
    except:
        await update.message.reply_text("⚠️ Sadece rakam girin." if lang=='tr' else "⚠️ Только цифры.")
        return YUKSEKLIK

async def confirm_yukseklik(update, context):
    lang = get_lang(context)
    t = update.message.text
    if is_bastan(t, lang): return await hesapla(update, context)
    if is_duzelt(t, lang):
        msg = "📏 Raf yüksekliği (m):" if lang=='tr' else "📏 Высота стеллажа (м):"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return YUKSEKLIK

    # Tüm bilgiler tamam, resmi ciz
    d = context.user_data
    raf_genislik = PALET_GENISLIK[d['palet']]
    koridor = KORIDOR_GENISLIK[d['koridor_tipi']]
    raf_satir = max(1, int(d['genislik'] / (raf_genislik + koridor)))
    raf_perz = max(1, int(d['uzunluk'] / 1.1))

    await update.message.reply_text(
        "⏳ Teknik çizim hazırlanıyor..." if lang=='tr' else "⏳ Подготовка технического чертежа...",
        reply_markup=ReplyKeyboardRemove()
    )

    try:
        resim = teknik_resim_ciz(
            d['uzunluk'], d['genislik'], raf_genislik, koridor,
            raf_satir, raf_perz, d['kat'], d['yukseklik'], d['depo_tipi'], lang
        )
        if lang == 'tr':
            cap = (f"📐 TEKNİK ÇİZİM\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"Depo: {d['uzunluk']}m × {d['genislik']}m\n"
                   f"Tip: {d['depo_tipi']} | Koridor: {d['koridor_tipi']}\n"
                   f"Raf: {raf_satir} satır × {raf_perz} sütun = {raf_satir*raf_perz} adet\n"
                   f"Kat: {d['kat']} | Yükseklik: {d['yukseklik']}m\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"Fiyat hesabı için /hesapla")
        else:
            cap = (f"📐 ТЕХНИЧЕСКИЙ ЧЕРТЁЖ\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"Склад: {d['uzunluk']}м × {d['genislik']}м\n"
                   f"Тип: {d['depo_tipi']} | Проход: {d['koridor_tipi']}\n"
                   f"Стеллажи: {raf_satir} рядов × {raf_perz} колонн = {raf_satir*raf_perz} шт\n"
                   f"Ярусов: {d['kat']} | Высота: {d['yukseklik']}м\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"Расчёт цены: /raschet")
        await update.message.reply_photo(photo=resim, caption=cap)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Resim hatası: {e}")

    return ConversationHandler.END

async def iptal(update, context):
    lang = get_lang(context)
    msg = "❌ İptal. /hesapla ile başlayın." if lang=='tr' else "❌ Отменено. Напишите /raschet."
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('hesapla', hesapla),
            CommandHandler('raschet', hesapla),
        ],
        states={
            LANG:             [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
            DEPO_TIPI:        [MessageHandler(filters.TEXT & ~filters.COMMAND, depo_tipi_sec)],
            KORIDOR_TIPI:     [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_tipi_sec)],
            UZUNLUK:          [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk)],
            CONFIRM_UZUNLUK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_uzunluk)],
            GENISLIK:         [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik)],
            CONFIRM_GENISLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_genislik)],
            PALET:            [MessageHandler(filters.TEXT & ~filters.COMMAND, palet)],
            CONFIRM_PALET:    [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_palet)],
            KAT:              [MessageHandler(filters.TEXT & ~filters.COMMAND, kat)],
            CONFIRM_KAT:      [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_kat)],
            YUKSEKLIK:        [MessageHandler(filters.TEXT & ~filters.COMMAND, yukseklik)],
            CONFIRM_YUKSEKLIK:[MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_yukseklik)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
