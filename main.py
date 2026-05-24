import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8960271967:AAGEuwGjVEmc0kj76OnVB4Z6EiBlV_THjiQ"

LANG, DEPO_TIPI, KORIDOR_TIPI, UZUNLUK, GENISLIK, PALET, KAT, YUKSEKLIK, YATAY_FIYAT, DIKEY_FIYAT, ANKRAJ_FIYAT, FIKSATOR_FIYAT, ZEMIN_FIYAT, TRANSPORT, MONTAJ = range(15)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

TEXTS = {
    "tr": {
        "depo_tipi": "🏭 Depo şeklini seçin:\n🔹 I — Düz sıralar\n🔹 L — İki duvara yaslanmış\n🔹 U — Üç duvara yaslanmış",
        "koridor_tipi": "🚦 Koridor tipini seçin:\n🚜 Forklift (3.0m)\n🔧 Transpalet (2.0m)\n👐 El ile (1.2m)",
        "uzunluk": "📏 Depo uzunluğunu girin (metre):\nÖrnek: 20",
        "genislik": "📐 Depo genişliğini girin (metre):\nÖrnek: 12",
        "palet": "📦 Raf başına palet sayısını seçin:\n1️⃣ - 0.95m\n2️⃣ - 1.85m\n3️⃣ - 2.70m\n4️⃣ - 3.60m",
        "kat": "🏗 Kat sayısını girin:\nÖrnek: 3",
        "yukseklik": "📏 Raf yüksekliğini girin (metre):\nÖrnek: 5",
        "yatay": "🔩 Yatay bağlantı birim fiyatı (₽/adet):\nÖrnek: 850",
        "dikey": "🔧 Dikey bağlantı birim fiyatı (₽/metre):\nÖrnek: 420",
        "ankraj": "⚓ Ankraj birim fiyatı (₽/adet):\nÖrnek: 150\n(0 yazarsanız hesaba katılmaz)",
        "fiksator": "🔒 Fiksatör birim fiyatı (₽/adet):\nÖrnek: 80\n(0 yazarsanız hesaba katılmaz)",
        "zemin": "🪛 Zemin düzeltici plaka fiyatı (₽/adet):\nÖrnek: 200\n(0 yazarsanız hesaba katılmaz)",
        "transport": "🚛 Transport fiyatı (₽):\nÖrnek: 15000",
        "montaj": "🔨 Montaj fiyatı (₽):\nÖrnek: 12000",
        "iptal": "❌ İptal edildi. /hesapla veya /raschet ile yeniden başlayabilirsiniz.",
        "hata": "⚠️ Lütfen sadece rakam girin.\nÖrnek: 20",
        "sonuc": "📊 HESAPLAMA SONUÇLARI\n━━━━━━━━━━━━━━━━━━\n🏭 Depo Tipi: {depo_tipi}\n🚦 Koridor: {koridor_tipi} ({koridor_genislik}m)\n📐 Raf Satır Sayısı: {raf_satir}\n🏗 Toplam Raf: {toplam_raf} adet\n📏 Raf Genişliği: {raf_genislik}m\n━━━━━━━━━━━━━━━━━━\nMALİYET LİSTESİ\n🔩 Yatay Bağlantı: {yatay_sayi} adet = {yatay_toplam:,.0f} ₽\n🔧 Dikey Bağlantı: {dikey_metre:.0f}m = {dikey_toplam:,.0f} ₽\n{ankraj_satir}{fiksator_satir}{zemin_satir}🚛 Transport: {transport:,.0f} ₽\n🔨 Montaj: {montaj:,.0f} ₽\n━━━━━━━━━━━━━━━━━━\n💰 GENEL TOPLAM: {genel:,.0f} ₽\n━━━━━━━━━━━━━━━━━━\nYeni hesaplama: /hesapla",
    },
    "ru": {
        "depo_tipi": "🏭 Выберите форму склада:\n🔹 I — Прямые ряды\n🔹 L — Вдоль двух стен\n🔹 U — Вдоль трёх стен",
        "koridor_tipi": "🚦 Выберите тип прохода:\n🚜 Погрузчик (3.0м)\n🔧 Транспалет (2.0м)\n👐 Ручной (1.2м)",
        "uzunluk": "📏 Введите длину склада (в метрах):\nПример: 20",
        "genislik": "📐 Введите ширину склада (в метрах):\nПример: 12",
        "palet": "📦 Выберите кол-во паллет на ряд:\n1️⃣ - 0.95м\n2️⃣ - 1.85м\n3️⃣ - 2.70м\n4️⃣ - 3.60м",
        "kat": "🏗 Введите количество ярусов:\nПример: 3",
        "yukseklik": "📏 Введите высоту стеллажа (в метрах):\nПример: 5",
        "yatay": "🔩 Цена горизонтальной балки (₽/шт):\nПример: 850",
        "dikey": "🔧 Цена вертикальной стойки (₽/м):\nПример: 420",
        "ankraj": "⚓ Цена анкера (₽/шт):\nПример: 150\n(Введите 0 если не нужно)",
        "fiksator": "🔒 Цена фиксатора (₽/шт):\nПример: 80\n(Введите 0 если не нужно)",
        "zemin": "🪛 Цена регулировочной пластины (₽/шт):\nПример: 200\n(Введите 0 если не нужно)",
        "transport": "🚛 Стоимость доставки (₽):\nПример: 15000",
        "montaj": "🔨 Стоимость монтажа (₽):\nПример: 12000",
        "iptal": "❌ Отменено. Напишите /hesapla или /raschet чтобы начать заново.",
        "hata": "⚠️ Пожалуйста, введите только цифры.\nПример: 20",
        "sonuc": "📊 РЕЗУЛЬТАТЫ РАСЧЁТА\n━━━━━━━━━━━━━━━━━━\n🏭 Тип склада: {depo_tipi}\n🚦 Проход: {koridor_tipi} ({koridor_genislik}м)\n📐 Рядов стеллажей: {raf_satir}\n🏗 Всего стеллажей: {toplam_raf} шт\n📏 Ширина стеллажа: {raf_genislik}м\n━━━━━━━━━━━━━━━━━━\nСПИСОК МАТЕРИАЛОВ\n🔩 Горизонт. балки: {yatay_sayi} шт = {yatay_toplam:,.0f} ₽\n🔧 Вертик. стойки: {dikey_metre:.0f}м = {dikey_toplam:,.0f} ₽\n{ankraj_satir}{fiksator_satir}{zemin_satir}🚛 Доставка: {transport:,.0f} ₽\n🔨 Монтаж: {montaj:,.0f} ₽\n━━━━━━━━━━━━━━━━━━\n💰 ИТОГО: {genel:,.0f} ₽\n━━━━━━━━━━━━━━━━━━\nНовый расчёт: /raschet",
    }
}

DEPO_TIPI_LABELS = {
    "tr": {"I": "I — Düz", "L": "L — Köşe", "U": "U — Üç Duvar"},
    "ru": {"I": "I — Прямой", "L": "L — Угловой", "U": "U — П-образный"}
}

KORIDOR_TIPI_LABELS = {
    "tr": {"forklift": "Forklift", "transpalet": "Transpalet", "el": "El ile"},
    "ru": {"forklift": "Погрузчик", "transpalet": "Транспалет", "el": "Ручной"}
}

def get_lang(context):
    return context.user_data.get('lang', 'tr')

async def start(update, context):
    keyboard = [["🇹🇷 Türkçe", "🇷🇺 Русский"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🌐 Dil seçin / Выберите язык:", reply_markup=reply_markup)
    return LANG

async def hesapla(update, context):
    keyboard = [["🇹🇷 Türkçe", "🇷🇺 Русский"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🌐 Dil seçin / Выберите язык:", reply_markup=reply_markup)
    return LANG

async def lang_sec(update, context):
    secim = update.message.text
    context.user_data['lang'] = 'ru' if "Русский" in secim else 'tr'
    lang = get_lang(context)
    T = TEXTS[lang]
    keyboard = [["I", "L", "U"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(T["depo_tipi"], reply_markup=reply_markup)
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
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(T["koridor_tipi"], reply_markup=reply_markup)
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
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(T["palet"], reply_markup=reply_markup)
        return PALET
    except:
        await update.message.reply_text(T["hata"])
        return GENISLIK

async def palet(update, context):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        val = int(update.message.text.strip()[0])
        if val not in [1, 2, 3, 4]:
            raise ValueError
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
        await update.message.reply_text(T["zemin"])
        return ZEMIN_FIYAT
    except:
        await update.message.reply_text(T["hata"])
        return FIKSATOR_FIYAT

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

        yatay_sayi = d['kat'] * toplam_raf
        yatay_toplam = yatay_sayi * d['yatay_fiyat']
        dikey_metre = toplam_raf * 4 * d['yukseklik']
        dikey_toplam = dikey_metre * d['dikey_fiyat']

        ankraj_sayi = toplam_raf * 4
        ankraj_toplam = ankraj_sayi * d['ankraj_fiyat']
        fiksator_sayi = toplam_raf * 2
        fiksator_toplam = fiksator_sayi * d['fiksator_fiyat']
        zemin_sayi = toplam_raf * 4
        zemin_toplam = zemin_sayi * d['zemin_fiyat']

        if lang == "tr":
            ankraj_satir = f"⚓ Ankraj: {ankraj_sayi} adet = {ankraj_toplam:,.0f} ₽\n" if d['ankraj_fiyat'] > 0 else ""
            fiksator_satir = f"🔒 Fiksatör: {fiksator_sayi} adet = {fiksator_toplam:,.0f} ₽\n" if d['fiksator_fiyat'] > 0 else ""
            zemin_satir = f"🪛 Zemin plakası: {zemin_sayi} adet = {zemin_toplam:,.0f} ₽\n" if d['zemin_fiyat'] > 0 else ""
        else:
            ankraj_satir = f"⚓ Анкера: {ankraj_sayi} шт = {ankraj_toplam:,.0f} ₽\n" if d['ankraj_fiyat'] > 0 else ""
            fiksator_satir = f"🔒 Фиксаторы: {fiksator_sayi} шт = {fiksator_toplam:,.0f} ₽\n" if d['fiksator_fiyat'] > 0 else ""
            zemin_satir = f"🪛 Рег. пластины: {zemin_sayi} шт = {zemin_toplam:,.0f} ₽\n" if d['zemin_fiyat'] > 0 else ""

        genel = yatay_toplam + dikey_toplam + ankraj_toplam + fiksator_toplam + zemin_toplam + d['transport'] + d['montaj']

        depo_label = DEPO_TIPI_LABELS[lang][d['depo_tipi']]
        koridor_label = KORIDOR_TIPI_LABELS[lang][d['koridor_tipi']]

        mesaj = T["sonuc"].format(
            depo_tipi=depo_label,
            koridor_tipi=koridor_label,
            koridor_genislik=koridor,
            raf_satir=raf_satir,
            toplam_raf=toplam_raf,
            raf_genislik=raf_genislik,
            yatay_sayi=yatay_sayi,
            yatay_toplam=yatay_toplam,
            dikey_metre=dikey_metre,
            dikey_toplam=dikey_toplam,
            ankraj_satir=ankraj_satir,
            fiksator_satir=fiksator_satir,
            zemin_satir=zemin_satir,
            transport=d['transport'],
            montaj=d['montaj'],
            genel=genel
        )
        await update.message.reply_text(mesaj)

        cizim = cizim_yap(d['uzunluk'], d['genislik'], raf_genislik, koridor, raf_satir, d['depo_tipi'], lang)
        await update.message.reply_text(f"```\n{cizim}\n```", parse_mode='Markdown')

        return ConversationHandler.END
    except:
        await update.message.reply_text(T["hata"])
        return MONTAJ

def cizim_yap(uzunluk, genislik, raf_genislik, koridor, raf_satir, depo_tipi, lang):
    en = 32
    satirlar = []
    if lang == "tr":
        satirlar.append(f"DEPO PLANI ({depo_tipi} tipi)")
    else:
        satirlar.append(f"ПЛАН СКЛАДА (тип {depo_tipi})")
    satirlar.append(f"{'─' * en}")
    satirlar.append(f"  uzunluk: {uzunluk}m")
    satirlar.append("┌" + "─" * (en - 2) + "┐")
    for i in range(raf_satir):
        raf_ic = "▬" * 12
        if lang == "tr":
            satirlar.append(f"│ {raf_ic}  {raf_ic[:4]} │ Raf {i+1} ({raf_genislik}m)")
        else:
            satirlar.append(f"│ {raf_ic}  {raf_ic[:4]} │ Ряд {i+1} ({raf_genislik}м)")
        if i < raf_satir - 1:
            bos = " " * (en - 4)
            if lang == "tr":
                satirlar.append(f"│{bos}│ Koridor {koridor}m")
            else:
                satirlar.append(f"│{bos}│ Проход {koridor}м")
    satirlar.append("└" + "─" * (en - 2) + "┘")
    if lang == "tr":
        satirlar.append(f"  GIRIS  |  genislik: {genislik}m")
    else:
        satirlar.append(f"  ВХОД   |  ширина: {genislik}м")
    return "\n".join(satirlar)

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
            ZEMIN_FIYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, zemin_fiyat)],
            TRANSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transport)],
            MONTAJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, montaj)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )

    app.add_handler(conv)
    app.run_polling()
