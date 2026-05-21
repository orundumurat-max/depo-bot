import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8960271967:AAGEuwGjVEmc0kj76OnVB4Z6EiBlV_THjiQ"

LANG, UZUNLUK, GENISLIK, PALET, KAT, YUKSEKLIK, YATAY_FIYAT, DIKEY_FIYAT, TRANSPORT, MONTAJ = range(10)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}

TEXTS = {
    "tr": {
        "welcome": "Merhaba! 👋 Depo Raf Hesaplama Botuna hoş geldiniz!\n\nDeponuzun ölçülerini girerek raf sistemi fiyatını hesaplayabilirsiniz.\n\nBaşlamak için /hesapla yazın.",
        "uzunluk": "📏 Depo uzunluğunu girin (metre):\nÖrnek: 20",
        "genislik": "📐 Depo genişliğini girin (metre):\nÖrnek: 12",
        "palet": "📦 Raf başına palet sayısını seçin:\n1️⃣ - 0.95m\n2️⃣ - 1.85m\n3️⃣ - 2.70m\n4️⃣ - 3.60m",
        "kat": "🏗 Kat sayısını girin:\nÖrnek: 3",
        "yukseklik": "📏 Raf yüksekliğini girin (metre):\nÖrnek: 5",
        "yatay": "🔩 Yatay bağlantı birim fiyatı (₽/adet):\nÖrnek: 850",
        "dikey": "🔧 Dikey bağlantı birim fiyatı (₽/metre):\nÖrnek: 420",
        "transport": "🚛 Transport fiyatı (₽):\nÖrnek: 15000",
        "montaj": "🔨 Montaj fiyatı (₽):\nÖrnek: 12000",
        "iptal": "❌ İptal edildi. /hesapla ile yeniden başlayabilirsiniz.",
        "hata": "⚠️ Lütfen sadece rakam girin.\nÖrnek: 20",
        "sonuc": (
            "📊 HESAPLAMA SONUÇLARI\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🏭 Toplam Raf: {toplam_raf} adet\n"
            "📐 Raf Satır Sayısı: {raf_satir}\n"
            "📏 Raf Genişliği: {raf_genislik}m\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔩 Yatay Bağlantı: {yatay_sayi} adet = {yatay_toplam:,.0f} ₽\n"
            "🔧 Dikey Bağlantı: {dikey_metre:.0f}m = {dikey_toplam:,.0f} ₽\n"
            "🚛 Transport: {transport:,.0f} ₽\n"
            "🔨 Montaj: {montaj:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 GENEL TOPLAM: {genel:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Yeni hesaplama için /hesapla yazın."
        ),
    },
    "ru": {
        "welcome": "Привет! 👋 Добро пожаловать в бот расчёта складских стеллажей!\n\nВведите размеры вашего склада и получите расчёт стоимости стеллажной системы.\n\nДля начала напишите /hesapla",
        "uzunluk": "📏 Введите длину склада (в метрах):\nПример: 20",
        "genislik": "📐 Введите ширину склада (в метрах):\nПример: 12",
        "palet": "📦 Выберите количество паллет на ряд:\n1️⃣ - 0.95м\n2️⃣ - 1.85м\n3️⃣ - 2.70м\n4️⃣ - 3.60м",
        "kat": "🏗 Введите количество ярусов:\nПример: 3",
        "yukseklik": "📏 Введите высоту стеллажа (в метрах):\nПример: 5",
        "yatay": "🔩 Цена горизонтальной балки (₽/шт):\nПример: 850",
        "dikey": "🔧 Цена вертикальной стойки (₽/м):\nПример: 420",
        "transport": "🚛 Стоимость доставки (₽):\nПример: 15000",
        "montaj": "🔨 Стоимость монтажа (₽):\nПример: 12000",
        "iptal": "❌ Отменено. Напишите /hesapla чтобы начать заново.",
        "hata": "⚠️ Пожалуйста, введите только цифры.\nПример: 20",
        "sonuc": (
            "📊 РЕЗУЛЬТАТЫ РАСЧЁТА\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🏭 Всего стеллажей: {toplam_raf} шт\n"
            "📐 Рядов стеллажей: {raf_satir}\n"
            "📏 Ширина стеллажа: {raf_genislik}м\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔩 Горизонт. балки: {yatay_sayi} шт = {yatay_toplam:,.0f} ₽\n"
            "🔧 Вертик. стойки: {dikey_metre:.0f}м = {dikey_toplam:,.0f} ₽\n"
            "🚛 Доставка: {transport:,.0f} ₽\n"
            "🔨 Монтаж: {montaj:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 ИТОГО: {genel:,.0f} ₽\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Новый расчёт: /hesapla"
        ),
    }
}

def cizim_yap(uzunluk, genislik, raf_genislik, koridor, raf_satir):
    satirlar = []
    en = 30
    satirlar.append("🗺 DEPO PLANI / ПЛАН СКЛАДА")
    satirlar.append(f"{'─' * en}")
    satirlar.append(f"  {uzunluk}m →")
    satirlar.append("┌" + "─" * (en-2) + "┐")

    for i in range(raf_satir):
        raf_ic = "█" * (en - 4)
        satirlar.append(f"│ {raf_ic} │ ← RAF/РЯД {i+1} ({raf_genislik}m)")
        if i < raf_satir - 1:
            bos = " " * (en - 4)
            satirlar.append(f"│ {bos} │ ← Koridor {koridor}m")

    satirlar.append("└" + "─" * (en-2) + "┘")
    satirlar.append(f"  ↑ GİRİŞ/ВХОД")
    satirlar.append(f"{'─' * en}")
    satirlar.append(f"↕ {genislik}m")
    return "\n".join(satirlar)

def get_lang(context):
    return context.user_data.get('lang', 'tr')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇹🇷 Türkçe", "🇷🇺 Русский"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "🌐 Dil seçin / Выберите язык:",
        reply_markup=reply_markup
    )
    return LANG

async def lang_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secim = update.message.text
    if "Русский" in secim:
        context.user_data['lang'] = 'ru'
    else:
        context.user_data['lang'] = 'tr'
    lang = get_lang(context)
    T = TEXTS[lang]
    await update.message.reply_text(T["welcome"], reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def hesapla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    await update.message.reply_text(T["uzunluk"])
    return UZUNLUK

async def uzunluk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['uzunluk'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["genislik"])
        return GENISLIK
    except:
        await update.message.reply_text(T["hata"])
        return UZUNLUK

async def genislik(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def palet(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def kat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['kat'] = int(update.message.text)
        await update.message.reply_text(T["yukseklik"])
        return YUKSEKLIK
    except:
        await update.message.reply_text(T["hata"])
        return KAT

async def yukseklik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['yukseklik'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["yatay"])
        return YATAY_FIYAT
    except:
        await update.message.reply_text(T["hata"])
        return YUKSEKLIK

async def yatay_fiyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['yatay_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["dikey"])
        return DIKEY_FIYAT
    except:
        await update.message.reply_text(T["hata"])
        return YATAY_FIYAT

async def dikey_fiyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['dikey_fiyat'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["transport"])
        return TRANSPORT
    except:
        await update.message.reply_text(T["hata"])
        return DIKEY_FIYAT

async def transport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        context.user_data['transport'] = float(update.message.text.replace(',', '.'))
        await update.message.reply_text(T["montaj"])
        return MONTAJ
    except:
        await update.message.reply_text(T["hata"])
        return TRANSPORT

async def montaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    try:
        d = context.user_data
        d['montaj'] = float(update.message.text.replace(',', '.'))

        raf_genislik = PALET_GENISLIK[d['palet']]
        koridor = 2.5
        raf_satir = int(d['genislik'] / (raf_genislik + koridor))
        raf_perz = int(d['uzunluk'] / 1.1)
        toplam_raf = raf_satir * raf_perz
        yatay_sayi = d['kat'] * toplam_raf
        yatay_toplam = yatay_sayi * d['yatay_fiyat']
        dikey_metre = toplam_raf * 4 * d['yukseklik']
        dikey_toplam = dikey_metre * d['dikey_fiyat']
        genel = yatay_toplam + dikey_toplam + d['transport'] + d['montaj']

        mesaj = T["sonuc"].format(
            toplam_raf=toplam_raf,
            raf_satir=raf_satir,
            raf_genislik=raf_genislik,
            yatay_sayi=yatay_sayi,
            yatay_toplam=yatay_toplam,
            dikey_metre=dikey_metre,
            dikey_toplam=dikey_toplam,
            transport=d['transport'],
            montaj=d['montaj'],
            genel=genel
        )
        await update.message.reply_text(mesaj)

        cizim = cizim_yap(d['uzunluk'], d['genislik'], raf_genislik, koridor, raf_satir)
        await update.message.reply_text(f"```\n{cizim}\n```", parse_mode='Markdown')

        return ConversationHandler.END
    except:
        await update.message.reply_text(T["hata"])
        return MONTAJ

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    T = TEXTS[lang]
    await update.message.reply_text(T["iptal"], reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    lang_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler('hesapla', hesapla)],
        states={
            UZUNLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk)],
            GENISLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik)],
            PALET: [MessageHandler(filters.TEXT & ~filters.COMMAND, palet)],
            KAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, kat)],
            YUKSEKLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, yukseklik)],
            YATAY_FIYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, yatay_fiyat)],
            DIKEY_FIYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, dikey_fiyat)],
            TRANSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transport)],
            MONTAJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, montaj)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )

    app.add_handler(lang_handler)
    app.add_handler(conv)
    app.run_polling()
