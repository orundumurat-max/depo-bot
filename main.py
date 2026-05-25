cat > /mnt/user-data/outputs/main.py << 'ENDOFFILE'
import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8960271967:AAGEuwGjVEmc0kj76OnVB4Z6EiBlV_THjiQ"

(LANG, DEPO_MODU, DEPO_TIPI, KORIDOR_TIPI, UZUNLUK, GENISLIK, PALET, KAT,
 YUKSEKLIK, YATAY_FIYAT, DIKEY_FIYAT, ANKRAJ_FIYAT, FIKSATOR_FIYAT,
 ZEMIN_ADET, ZEMIN_FIYAT, TRANSPORT, MONTAJ,
 EK_DIKME, EK_YATAY, EK_YATAY_FIYAT2, EK_DIKEY_FIYAT2, EK_TRANSPORT, EK_MONTAJ) = range(23)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

TEXTS = {
    "tr": {
        "depo_modu": "🏭 Hesaplama türünü seçin:\n🆕 Yeni depo\n➕ Mevcut depoya ek raf",
        "depo_tipi": "🏭 Depo şeklini seçin:\n🔹 I — Düz sıralar\n🔹 L — İki duvara\n🔹 U — Üç duvara",
        "koridor_tipi": "🚦 Koridor tipini seçin:\n🚜 Forklift (3.0m)\n🔧 Transpalet (2.0m)\n👐 El ile (1.2m)",
        "uzunluk": "📏 Depo uzunluğu (m):\nÖrnek: 20",
        "genislik": "📐 Depo genişliği (m):\nÖrnek: 12",
        "palet": "📦 Raf başına palet sayısı:\n1️⃣ 0.95m  2️⃣ 1.85m\n3️⃣ 2.70m  4️⃣ 3.60m",
        "kat": "🏗 Kat sayısı:\nÖrnek: 3",
        "yukseklik": "📏 Raf yüksekliği (m):\nÖrnek: 5",
        "yatay": "🔩 Yatay bağlantı birim fiyatı (₽/adet):\nÖrnek: 850",
        "dikey": "🔧 Dikey bağlantı birim fiyatı (₽/metre):\nÖrnek: 420",
        "ankraj": "⚓ Ankraj birim fiyatı (₽/adet):\nÖrnek: 150",
        "fiksator": "🔒 Fiksatör birim fiyatı (₽/adet):\nÖrnek: 80",
        "zemin_adet": "🪛 Zemin düzeltici plaka:\nKaç adet olsun?\n(Tüm dikmeler için: 0 yaz, otomatik hesaplar)",
        "zemin_fiyat": "🪛 Zemin plakası birim fiyatı (₽/adet):\nÖrnek: 200\n(0 yazarsanız hesaba katılmaz)",
        "transport": "🚛 Transport fiyatı (₽):\nÖrnek: 15000",
        "montaj": "🔨 Montaj fiyatı (₽):\nÖrnek: 12000",
        "ek_dikme": "🔧 EK RAF — Kaç dikme eklenecek?\nÖrnek: 20",
        "ek_yatay": "🔩 EK RAF — Kaç yatay bağlantı?\nÖrnek: 60",
        "ek_yatay_fiyat": "🔩 Yatay bağlantı birim fiyatı (₽/adet):\nÖrnek: 850",
        "ek_dikey_fiyat": "🔧 Dikey bağlantı birim fiyatı (₽/metre):\nÖrnek: 420",
        "ek_transport": "🚛 Transport fiyatı (₽):\nÖrnek: 10000",
        "ek_montaj": "🔨 Montaj fiyatı (₽):\nÖrnek: 8000",
        "iptal": "❌ İptal. /hesapla ile yeniden başlayın.",
        "hata": "⚠️ Sadece rakam girin.\nÖrnek: 20",
        "sonuc": (
            "📊 HESAPLAMA SONUÇLARI\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🏭 Depo: {depo_tipi} | Koridor: {koridor_tipi} ({koridor_genislik}m)\n"
            "📐 Raf Satırı: {raf_satir} | Toplam Raf: {toplam_raf} adet\n"
            "📏 Raf Genişliği: {raf_genislik}m\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "MALZEMELİSTESİ\n"
            "🔩 Yatay Bağlantı: {yatay_sayi} adet = {yatay_toplam:,.0f} ₽\n"
            "🔧 Dikey (Dikme): {dikme_sayi} adet × {yukseklik}m = {dikey_toplam:,.0f} ₽\n"
            "⚓ Ankraj: {ankraj_sayi} adet = {ankraj_toplam:,.0f} ₽\n"
            "🔒 Fiksatör: {fiksator_sayi} adet = {fiksator_toplam:,.0f} ₽\n"
            "{zemin_satir}"
            "🚛 Transport: {transport:,.0f} ₽\n"
            "🔨 Montaj: {montaj:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 GENEL TOPLAM: {genel:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Yeni hesaplama: /hesapla"
        ),
        "ek_sonuc": (
            "📊 EK RAF HESABI\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔧 Dikme: {dikme} adet\n"
            "🔩 Yatay Bağlantı: {yatay} adet = {yatay_t:,.0f} ₽\n"
            "⚓ Ankraj: {ankraj} adet = {ankraj_t:,.0f} ₽\n"
            "🔒 Fiksatör: {fiksator} adet = {fiksator_t:,.0f} ₽\n"
            "🚛 Transport: {transport:,.0f} ₽\n"
            "🔨 Montaj: {montaj:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 TOPLAM: {genel:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Yeni hesaplama: /hesapla"
        ),
    },
    "ru": {
        "depo_modu": "🏭 Выберите тип расчёта:\n🆕 Новый склад\n➕ Дополнительные стеллажи",
        "depo_tipi": "🏭 Форма склада:\n🔹 I — Прямые ряды\n🔹 L — Вдоль двух стен\n🔹 U — Вдоль трёх стен",
        "koridor_tipi": "🚦 Тип прохода:\n🚜 Погрузчик (3.0м)\n🔧 Транспалет (2.0м)\n👐 Ручной (1.2м)",
        "uzunluk": "📏 Длина склада (м):\nПример: 20",
        "genislik": "📐 Ширина склада (м):\nПример: 12",
        "palet": "📦 Паллет на ряд:\n1️⃣ 0.95м  2️⃣ 1.85м\n3️⃣ 2.70м  4️⃣ 3.60м",
        "kat": "🏗 Количество ярусов:\nПример: 3",
        "yukseklik": "📏 Высота стеллажа (м):\nПример: 5",
        "yatay": "🔩 Цена горизонт. балки (₽/шт):\nПример: 850",
        "dikey": "🔧 Цена вертик. стойки (₽/м):\nПример: 420",
        "ankraj": "⚓ Цена анкера (₽/шт):\nПример: 150",
        "fiksator": "🔒 Цена фиксатора (₽/шт):\nПример: 80",
        "zemin_adet": "🪛 Регулировочные пластины:\nСколько штук?\n(0 = под все стойки автоматически)",
        "zemin_fiyat": "🪛 Цена пластины (₽/шт):\nПример: 200\n(0 = не включать)",
        "transport": "🚛 Доставка (₽):\nПример: 15000",
        "montaj": "🔨 Монтаж (₽):\nПример: 12000",
        "ek_dikme": "🔧 ДОП. СТЕЛЛАЖИ — Кол-во стоек:\nПример: 20",
        "ek_yatay": "🔩 ДОП. СТЕЛЛАЖИ — Кол-во балок:\nПример: 60",
        "ek_yatay_fiyat": "🔩 Цена горизонт. балки (₽/шт):\nПример: 850",
        "ek_dikey_fiyat": "🔧 Цена вертик. стойки (₽/м):\nПример: 420",
        "ek_transport": "🚛 Доставка (₽):\nПример: 10000",
        "ek_montaj": "🔨 Монтаж (₽):\nПример: 8000",
        "iptal": "❌ Отменено. Напишите /raschet чтобы начать.",
        "hata": "⚠️ Введите только цифры.\nПример: 20",
        "sonuc": (
            "📊 РЕЗУЛЬТАТЫ РАСЧЁТА\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🏭 Склад: {depo_tipi} | Проход: {koridor_tipi} ({koridor_genislik}м)\n"
            "📐 Рядов: {raf_satir} | Стеллажей: {toplam_raf} шт\n"
            "📏 Ширина стеллажа: {raf_genislik}м\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "СПИСОК МАТЕРИАЛОВ\n"
            "🔩 Горизонт. балки: {yatay_sayi} шт = {yatay_toplam:,.0f} ₽\n"
            "🔧 Стойки: {dikme_sayi} шт × {yukseklik}м = {dikey_toplam:,.0f} ₽\n"
            "⚓ Анкера: {ankraj_sayi} шт = {ankraj_toplam:,.0f} ₽\n"
            "🔒 Фиксаторы: {fiksator_sayi} шт = {fiksator_toplam:,.0f} ₽\n"
            "{zemin_satir}"
            "🚛 Доставка: {transport:,.0f} ₽\n"
            "🔨 Монтаж: {montaj:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 ИТОГО: {genel:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Новый расчёт: /raschet"
        ),
        "ek_sonuc": (
            "📊 ДОП. СТЕЛЛАЖИ\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔧 Стоек: {dikme} шт\n"
            "🔩 Балок: {yatay} шт = {yatay_t:,.0f} ₽\n"
            "⚓ Анкера: {ankraj} шт = {ankraj_t:,.0f} ₽\n"
            "🔒 Фиксаторы: {fiksator} шт = {fiksator_t:,.0f} ₽\n"
            "🚛 Доставка: {transport:,.0f} ₽\n"
            "🔨 Монтаж: {montaj:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 ИТОГО: {genel:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Новый расчёт: /raschet"
        ),
    }
}

DEPO_LABELS = {
    "tr": {"I": "I-Düz", "L": "L-Köşe", "U": "U-Üç Duvar"},
    "ru": {"I": "I-Прямой", "L": "L-Угловой", "U": "U-П-образный"}
}
KORIDOR_LABELS = {
    "tr": {"forklift": "Forklift", "transpalet": "Transpalet", "el": "El ile"},
    "ru": {"forklift": "Погрузчик", "transpalet": "Транспалет", "el": "Ручной"}
}

def get_lang(context):
    return context.user_data.get('lang', 'tr')

def teknik_resim_ciz(uzunluk, genislik, raf_genislik, koridor, raf_satir, raf_perz, kat, yukseklik, depo_tipi, lang):
    W, H = 900, 650
    img = Image.new('RGB', (W, H), color='#1a1a2e')
    draw = ImageDraw.Draw(img)

    try:
        font_buyuk = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_kucuk = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        font_baslik = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except:
        font_buyuk = ImageFont.load_default()
        font_kucuk = ImageFont.load_default()
        font_baslik = ImageFont.load_default()

    # Renkler
    MAVI = '#4a9eff'        # dikmeler
    TURUNCU = '#ff8c42'     # yatay baglantilar
    YESIL = '#4ade80'       # derinlik
    BEYAZ = '#e0e0e0'
    GRI = '#404060'
    ACIK_GRI = '#606080'
    SARI = '#ffd700'

    pad = 80
    plan_w = W - pad * 2
    plan_h = H - pad * 2 - 60

    scale_x = plan_w / uzunluk
    scale_y = plan_h / genislik

    ox = pad
    oy = pad + 50

    # Baslik
    baslik = f"DEPO STЕЛАЖ PLANI / ПЛАН СТЕЛЛАЖЕЙ — Tip/Тип: {depo_tipi}" if lang == "tr" else f"ПЛАН СТЕЛЛАЖЕЙ — Тип: {depo_tipi}"
    draw.rectangle([0, 0, W, 45], fill='#16213e')
    draw.text((W//2, 22), baslik, fill=SARI, font=font_baslik, anchor='mm')

    # Depo siniri
    draw.rectangle([ox, oy, ox + plan_w, oy + plan_h], outline='#00b4d8', width=3)
    draw.rectangle([ox+3, oy+3, ox+plan_w-3, oy+plan_h-3], outline='#1a3a5c', width=1)

    # Giris
    giris_x = ox + plan_w // 2
    draw.line([giris_x - 30, oy + plan_h, giris_x + 30, oy + plan_h], fill=SARI, width=5)
    giris_txt = "GİRİŞ" if lang == "tr" else "ВХОД"
    draw.text((giris_x, oy + plan_h + 15), giris_txt, fill=SARI, font=font_kucuk, anchor='mt')

    # Her raf satirini ciz
    for row in range(raf_satir):
        raf_y_start = oy + int((raf_genislik / 2 + row * (raf_genislik + koridor)) * scale_y)
        raf_y_end = raf_y_start + int(raf_genislik * scale_y)

        # Her raf birimi (dikdortgen + capraz)
        for col in range(raf_perz):
            rx1 = ox + int(col * 1.1 * scale_x) + 2
            rx2 = ox + int((col + 1) * 1.1 * scale_x) - 2
            ry1 = raf_y_start
            ry2 = raf_y_end

            # Raf dolgu
            draw.rectangle([rx1, ry1, rx2, ry2], fill='#0a1628', outline=ACIK_GRI, width=1)

            # Capraz cizgiler (x seklinde)
            draw.line([rx1, ry1, rx2, ry2], fill=GRI, width=1)
            draw.line([rx1, ry2, rx2, ry1], fill=GRI, width=1)

            # Dikmeler (mavi - 4 kose)
            dikme_r = 4
            for dx, dy in [(rx1, ry1), (rx2, ry1), (rx1, ry2), (rx2, ry2)]:
                draw.ellipse([dx-dikme_r, dy-dikme_r, dx+dikme_r, dy+dikme_r], fill=MAVI, outline='white', width=1)

            # Yatay baglantilar (turuncu - ust ve alt kenar)
            draw.line([rx1+dikme_r, ry1, rx2-dikme_r, ry1], fill=TURUNCU, width=3)
            draw.line([rx1+dikme_r, ry2, rx2-dikme_r, ry2], fill=TURUNCU, width=3)

            # Derinlik baglantisi (yesil - sol ve sag kenar)
            draw.line([rx1, ry1+dikme_r, rx1, ry2-dikme_r], fill=YESIL, width=2)
            draw.line([rx2, ry1+dikme_r, rx2, ry2-dikme_r], fill=YESIL, width=2)

        # Raf etiketi
        raf_lbl = f"Raf {row+1} ({raf_genislik}m)" if lang == "tr" else f"Ряд {row+1} ({raf_genislik}м)"
        draw.text((ox + plan_w + 8, (raf_y_start + raf_y_end) // 2), raf_lbl, fill=BEYAZ, font=font_kucuk, anchor='lm')

        # Koridor etiketi
        if row < raf_satir - 1:
            kor_y = raf_y_end + int(koridor * scale_y / 2)
            kor_lbl = f"Koridor {koridor}m" if lang == "tr" else f"Проход {koridor}м"
            draw.text((ox + plan_w // 2, kor_y), kor_lbl, fill=ACIK_GRI, font=font_kucuk, anchor='mm')

    # Olcu cizgileri - uzunluk (ust)
    draw.line([ox, oy - 20, ox + plan_w, oy - 20], fill=ACIK_GRI, width=1)
    draw.line([ox, oy - 25, ox, oy - 15], fill=ACIK_GRI, width=1)
    draw.line([ox + plan_w, oy - 25, ox + plan_w, oy - 15], fill=ACIK_GRI, width=1)
    draw.text((ox + plan_w // 2, oy - 20), f"{uzunluk}m", fill=BEYAZ, font=font_kucuk, anchor='mm')

    # Olcu cizgileri - genislik (sol)
    draw.line([ox - 20, oy, ox - 20, oy + plan_h], fill=ACIK_GRI, width=1)
    draw.line([ox - 25, oy, ox - 15, oy], fill=ACIK_GRI, width=1)
    draw.line([ox - 25, oy + plan_h, ox - 15, oy + plan_h], fill=ACIK_GRI, width=1)
    draw.text((ox - 35, oy + plan_h // 2), f"{genislik}m", fill=BEYAZ, font=font_kucuk, anchor='mm')

    # Lejant (alt)
    lejant_y = H - 35
    lejant_items = [
        (MAVI, "● Dikme/Стойка"),
        (TURUNCU, "— Yatay Bağlantı/Балка"),
        (YESIL, "| Derinlik/Глубина"),
        ('#00b4d8', "□ Depo/Склад"),
    ]
    lx = ox
    for renk, metin in lejant_items:
        draw.text((lx, lejant_y), metin, fill=renk, font=font_kucuk)
        lx += 200

    # Bilgi kutusu (sag alt)
    bilgi_x = W - 220
    bilgi_y = oy + 10
    draw.rectangle([bilgi_x, bilgi_y, bilgi_x+200, bilgi_y+120], fill='#16213e', outline='#30366d', width=1)
    bilgiler = [
        f"Kat/Ярус: {kat}",
        f"Yükseklik/Высота: {yukseklik}m",
        f"Raf/Стеллажей: {raf_satir * raf_perz}",
        f"Satır/Рядов: {raf_satir}",
        f"Sütun/Колонн: {raf_perz}",
    ]
    for i, b in enumerate(bilgiler):
        draw.text((bilgi_x + 10, bilgi_y + 10 + i * 22), b, fill=BEYAZ, font=font_kucuk)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

async def start(update, context):
    keyboard = [["🇹🇷 Türkçe", "🇷🇺 Русский"]]
    await update.message.reply_text("🌐 Dil seçin / Выберите язык:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return LANG

async def hesapla(update, context):
    keyboard = [["🇹🇷 Türkçe", "🇷🇺 Русский"]]
    await update.message.reply_text("🌐 Dil seçin / Выберите язык:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return LANG

async def lang_sec(update, context):
    secim = update.message.text
    context.user_data['lang'] = 'ru' if "Русский" in secim else 'tr'
    lang = get_lang(context)
    T = TEXTS[lang]
    keyboard = [["🆕 Yeni depo" if lang=="tr" else "🆕 Новый склад",
                 "➕ Mevcut depoya ek" if lang=="tr" else "➕ Дополнительные"]]
    await update.message.reply_text(T["depo_modu"],
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return DEPO_MODU

async def depo_modu_sec(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    secim = update.message.text
    if "ek" in secim.lower() or "доп" in secim.lower():
        context.user_data['mod'] = 'ek'
        await update.message.reply_text(T["ek_dikme"], reply_markup=ReplyKeyboardRemove())
        return EK_DIKME
    else:
        context.user_data['mod'] = 'yeni'
        keyboard = [["I", "L", "U"]]
        await update.message.reply_text(T["depo_tipi"],
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
        return DEPO_TIPI

async def depo_tipi_sec(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    secim = update.message.text.strip().upper()[0]
    if secim not in ["I", "L", "U"]:
        await update.message.reply_text(T["hata"])
        return DEPO_TIPI
    context.user_data['depo_tipi'] = secim
    keyboard = [["🚜 Forklift", "🔧 Transpalet", "👐 El ile"]]
    await update.message.reply_text(T["koridor_tipi"],
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
    return KORIDOR_TIPI

async def koridor_tipi_sec(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    secim = update.message.text.lower()
    if "forklift" in secim or "погрузчик" in secim:
        context.user_data['koridor_tipi'] = 'forklift'
    elif "transpalet" in secim or "транспалет" in secim:
        context.user_data['koridor_tipi'] = 'transpalet'
    else:
        context.user_data['koridor_tipi'] = 'el'
    await update.message.reply_text(T["uzunluk"], reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['uzunluk'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["genislik"])
        return GENISLIK
    except:
        await update.message.reply_text(T["hata"])
        return UZUNLUK

async def genislik(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',', '.'))
        keyboard = [["1", "2"], ["3", "4"]]
        await update.message.reply_text(T["palet"],
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))
        return PALET
    except:
        await update.message.reply_text(T["hata"])
        return GENISLIK

async def palet(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        val = int(update.message.text.strip()[0])
        if val not in [1, 2, 3, 4]: raise ValueError
        context.user_data['palet'] = val
        await update.message.reply_text(T["kat"], reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text(T["hata"])
        return PALET

async def kat(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['kat'] = int(update.message.text)
        await update.message.reply_text(T["yukseklik"])
        return YUKSEKLIK
    except:
        await update.message.reply_text(T["hata"])
        return KAT

async def yukseklik(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['yukseklik'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["yatay"])
        return YATAY_FIYAT
    except:
        await update.message.reply_text(T["hata"])
        return YUKSEKLIK

async def yatay_fiyat(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['yatay_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["dikey"])
        return DIKEY_FIYAT
    except:
        await update.message.reply_text(T["hata"])
        return YATAY_FIYAT

async def dikey_fiyat(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['dikey_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["ankraj"])
        return ANKRAJ_FIYAT
    except:
        await update.message.reply_text(T["hata"])
        return DIKEY_FIYAT

async def ankraj_fiyat(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['ankraj_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["fiksator"])
        return FIKSATOR_FIYAT
    except:
        await update.message.reply_text(T["hata"])
        return ANKRAJ_FIYAT

async def fiksator_fiyat(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['fiksator_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["zemin_adet"])
        return ZEMIN_ADET
    except:
        await update.message.reply_text(T["hata"])
        return FIKSATOR_FIYAT

async def zemin_adet(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['zemin_adet'] = int(update.message.text)
        await update.message.reply_text(T["zemin_fiyat"])
        return ZEMIN_FIYAT
    except:
        await update.message.reply_text(T["hata"])
        return ZEMIN_ADET

async def zemin_fiyat(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['zemin_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["transport"])
        return TRANSPORT
    except:
        await update.message.reply_text(T["hata"])
        return ZEMIN_FIYAT

async def transport(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['transport'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["montaj"])
        return MONTAJ
    except:
        await update.message.reply_text(T["hata"])
        return TRANSPORT

async def montaj(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        d = context.user_data
        d['montaj'] = float(update.message.text.replace(',', '.'))

        raf_genislik = PALET_GENISLIK[d['palet']]
        koridor = KORIDOR_GENISLIK[d['koridor_tipi']]
        raf_satir = int(d['genislik'] / (raf_genislik + koridor))
        raf_perz = int(d['uzunluk'] / 1.1)
        toplam_raf = raf_satir * raf_perz

        # Dogru formüller
        dikme_sayi = toplam_raf * 4
        yatay_sayi = d['kat'] * toplam_raf
        yatay_toplam = yatay_sayi * d['yatay_fiyat']
        dikey_metre = dikme_sayi * d['yukseklik']
        dikey_toplam = dikey_metre * d['dikey_fiyat']

        # Ankraj: her dikmenin altinda 4 adet
        ankraj_sayi = dikme_sayi * 4
        ankraj_toplam = ankraj_sayi * d['ankraj_fiyat']

        # Fiksator: her yatay baglantiда 4 adet
        fiksator_sayi = yatay_sayi * 4
        fiksator_toplam = fiksator_sayi * d['fiksator_fiyat']

        # Zemin plakasi
        if d['zemin_adet'] == 0:
            zemin_sayi = dikme_sayi
        else:
            zemin_sayi = d['zemin_adet']
        zemin_toplam = zemin_sayi * d['zemin_fiyat']

        if lang == "tr":
            zemin_satir = f"🪛 Zemin plakası: {zemin_sayi} adet = {zemin_toplam:,.0f} ₽\n" if d['zemin_fiyat'] > 0 else ""
        else:
            zemin_satir = f"🪛 Рег. пластины: {zemin_sayi} шт = {zemin_toplam:,.0f} ₽\n" if d['zemin_fiyat'] > 0 else ""

        genel = yatay_toplam + dikey_toplam + ankraj_toplam + fiksator_toplam + zemin_toplam + d['transport'] + d['montaj']

        mesaj = T["sonuc"].format(
            depo_tipi=DEPO_LABELS[lang][d['depo_tipi']],
            koridor_tipi=KORIDOR_LABELS[lang][d['koridor_tipi']],
            koridor_genislik=koridor,
            raf_satir=raf_satir,
            toplam_raf=toplam_raf,
            raf_genislik=raf_genislik,
            yatay_sayi=yatay_sayi,
            yatay_toplam=yatay_toplam,
            dikme_sayi=dikme_sayi,
            yukseklik=d['yukseklik'],
            dikey_toplam=dikey_toplam,
            ankraj_sayi=ankraj_sayi,
            ankraj_toplam=ankraj_toplam,
            fiksator_sayi=fiksator_sayi,
            fiksator_toplam=fiksator_toplam,
            zemin_satir=zemin_satir,
            transport=d['transport'],
            montaj=d['montaj'],
            genel=genel
        )
        await update.message.reply_text(mesaj)

        # Teknik resim gonder
        try:
            resim = teknik_resim_ciz(
                d['uzunluk'], d['genislik'], raf_genislik, koridor,
                raf_satir, raf_perz, d['kat'], d['yukseklik'], d['depo_tipi'], lang
            )
            caption = "📐 Teknik Plan" if lang == "tr" else "📐 Технический план"
            await update.message.reply_photo(photo=resim, caption=caption)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Resim oluşturulamadı: {e}")

        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(T["hata"])
        return MONTAJ

# Ek raf hesabi
async def ek_dikme(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['ek_dikme'] = int(update.message.text)
        await update.message.reply_text(T["ek_yatay"])
        return EK_YATAY
    except:
        await update.message.reply_text(T["hata"])
        return EK_DIKME

async def ek_yatay(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['ek_yatay'] = int(update.message.text)
        await update.message.reply_text(T["ek_yatay_fiyat"])
        return EK_YATAY_FIYAT2
    except:
        await update.message.reply_text(T["hata"])
        return EK_YATAY

async def ek_yatay_fiyat(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['ek_yatay_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["ek_dikey_fiyat"])
        return EK_DIKEY_FIYAT2
    except:
        await update.message.reply_text(T["hata"])
        return EK_YATAY_FIYAT2

async def ek_dikey_fiyat(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['ek_dikey_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["ek_transport"])
        return EK_TRANSPORT
    except:
        await update.message.reply_text(T["hata"])
        return EK_DIKEY_FIYAT2

async def ek_transport(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['ek_transport'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["ek_montaj"])
        return EK_MONTAJ
    except:
        await update.message.reply_text(T["hata"])
        return EK_TRANSPORT

async def ek_montaj(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        d = context.user_data
        d['ek_montaj'] = float(update.message.text.replace(',', '.'))

        dikme = d['ek_dikme']
        yatay = d['ek_yatay']
        yatay_t = yatay * d['ek_yatay_fiyat']
        ankraj = dikme * 4
        ankraj_t = ankraj * d.get('ankraj_fiyat', 0)
        fiksator = yatay * 4
        fiksator_t = fiksator * d.get('fiksator_fiyat', 0)
        genel = yatay_t + ankraj_t + fiksator_t + d['ek_transport'] + d['ek_montaj']

        mesaj = T["ek_sonuc"].format(
            dikme=dikme, yatay=yatay, yatay_t=yatay_t,
            ankraj=ankraj, ankraj_t=ankraj_t,
            fiksator=fiksator, fiksator_t=fiksator_t,
            transport=d['ek_transport'], montaj=d['ek_montaj'], genel=genel
        )
        await update.message.reply_text(mesaj)
        return ConversationHandler.END
    except:
        await update.message.reply_text(T["hata"])
        return EK_MONTAJ

async def iptal(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    await update.message.reply_text(T["iptal"], reply_markup=ReplyKeyboardRemove())
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
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
            DEPO_MODU: [MessageHandler(filters.TEXT & ~filters.COMMAND, depo_modu_sec)],
            DEPO_TIPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, depo_tipi_sec)],
            KORIDOR_TIPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_tipi_sec)],
            UZUNLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk)],
            GENISLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik)],
            PALET: [MessageHandler(filters.TEXT & ~filters.COMMAND, palet)],
            KAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, kat)],
            YUKSEKLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, yukseklik)],
            YATAY_FIYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, yatay_fiyat)],
            DIKEY_FIYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, dikey_fiyat)],
            ANKRAJ_FIYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ankraj_fiyat)],
            FIKSATOR_FIYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fiksator_fiyat)],
            ZEMIN_ADET: [MessageHandler(filters.TEXT & ~filters.COMMAND, zemin_adet)],
            ZEMIN_FIYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, zemin_fiyat)],
            TRANSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transport)],
            MONTAJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, montaj)],
            EK_DIKME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ek_dikme)],
            EK_YATAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ek_yatay)],
            EK_YATAY_FIYAT2: [MessageHandler(filters.TEXT & ~filters.COMMAND, ek_yatay_fiyat)],
            EK_DIKEY_FIYAT2: [MessageHandler(filters.TEXT & ~filters.COMMAND, ek_dikey_fiyat)],
            EK_TRANSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ek_transport)],
            EK_MONTAJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, ek_montaj)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )

    app.add_handler(conv)
    app.run_polling()
ENDOFFILE
