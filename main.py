import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8960271967:AAGEuwGjVEmc0kj76OnVB4Z6EiBlV_THjiQ"

UZUNLUK, GENISLIK, PALET, KAT, YUKSEKLIK, YATAY_FIYAT, DIKEY_FIYAT, TRANSPORT, MONTAJ = range(9)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Depo Raf Hesaplama Botuna hoş geldiniz!\n\n"
        "Deponuzun ölçülerini girerek raf sistemi fiyatını hesaplayabilirsiniz.\n\n"
        "Başlamak için /hesapla yazın."
    )

async def hesapla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Depo uzunluğunu girin (metre olarak):\nПример: 20")
    return UZUNLUK

async def uzunluk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['uzunluk'] = float(update.message.text)
    await update.message.reply_text("Depo genişliğini girin (metre):\nПример: 12")
    return GENISLIK

async def genislik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['genislik'] = float(update.message.text)
    await update.message.reply_text(
        "Raf başına palet sayısını seçin:\n"
        "1 - 0.95m\n2 - 1.85m\n3 - 2.70m\n4 - 3.60m"
    )
    return PALET

async def palet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['palet'] = int(update.message.text)
    await update.message.reply_text("Kat sayısını girin:\nПример: 3")
    return KAT

async def kat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['kat'] = int(update.message.text)
    await update.message.reply_text("Raf yüksekliğini girin (metre):\nПример: 5")
    return YUKSEKLIK

async def yukseklik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['yukseklik'] = float(update.message.text)
    await update.message.reply_text("Yatay bağlantı birim fiyatı (₽/adet):\nПример: 850")
    return YATAY_FIYAT

async def yatay_fiyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['yatay_fiyat'] = float(update.message.text)
    await update.message.reply_text("Dikey bağlantı birim fiyatı (₽/metre):\nПример: 420")
    return DIKEY_FIYAT

async def dikey_fiyat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['dikey_fiyat'] = float(update.message.text)
    await update.message.reply_text("Transport fiyatı (₽):\nПример: 15000")
    return TRANSPORT

async def transport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['transport'] = float(update.message.text)
    await update.message.reply_text("Montaj fiyatı (₽):\nПример: 12000")
    return MONTAJ

async def montaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    d['montaj'] = float(update.message.text)

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

    mesaj = (
        f"📊 HESAPLAMA SONUÇLARI\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏭 Toplam Raf: {toplam_raf} adet\n"
        f"📐 Raf Satır Sayısı: {raf_satir}\n"
        f"📏 Raf Genişliği: {raf_genislik}m\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔩 Yatay Bağlantı: {yatay_sayi} adet = {yatay_toplam:,.0f} ₽\n"
        f"🔧 Dikey Bağlantı: {dikey_metre:.0f}m = {dikey_toplam:,.0f} ₽\n"
        f"🚛 Transport: {d['transport']:,.0f} ₽\n"
        f"🔨 Montaj: {d['montaj']:,.0f} ₽\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 GENEL TOPLAM: {genel:,.0f} ₽\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Yeni hesaplama için /hesapla yazın."
    )
    await update.message.reply_text(mesaj)
    return ConversationHandler.END

async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("İptal edildi. /hesapla ile yeniden başlayabilirsiniz.")
    return ConversationHandler.END

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    
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
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv)
    app.run_polling()
