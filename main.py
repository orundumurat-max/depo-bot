import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8960271967:AAGEuwGjVEmc0kj76OnVB4Z6EiBlV_THjiQ"

(LANG, DEPO_TIPI, KORIDOR_TIPI, UZUNLUK, GENISLIK, PALET, KAT, YUKSEKLIK,
 GIRIS_KENAR, GIRIS_KONUM, GIRIS_MESAFE, KENAR_BOSLUK) = range(12)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def teknik_resim_ciz(d, lang):
    uzunluk = d['uzunluk']
    genislik = d['genislik']
    raf_genislik = PALET_GENISLIK[d['palet']]
    koridor = KORIDOR_GENISLIK[d['koridor_tipi']]
    kat = d['kat']
    yukseklik = d['yukseklik']
    depo_tipi = d['depo_tipi']
    bosluk = d.get('kenar_bosluk', 0)
    giris_kenar = d.get('giris_kenar', 'alt')
    giris_konum = d.get('giris_konum', 'orta')
    giris_mesafe = d.get('giris_mesafe', 0)

    W, H = 1000, 740
    img = Image.new('RGB', (W, H), '#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        fn = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        fb = fn = ft = ImageFont.load_default()

    MAVI = '#4a9eff'
    TURUNCU = '#ff8c42'
    YESIL = '#4ade80'
    BEYAZ = '#e0e0e0'
    GRI = '#303050'
    AGRI = '#505070'
    SARI = '#ffd700'
    SINIR = '#00b4d8'
    KIRMIZI = '#ff4444'

    INFO_H = 110
    pad_l, pad_t, pad_r, pad_b = 60, 50, 80, INFO_H + 25
    plan_w = W - pad_l - pad_r
    plan_h = H - pad_t - pad_b
    ox, oy = pad_l, pad_t

    sx = plan_w / uzunluk
    sy = plan_h / genislik

    # Baslik
    draw.rectangle([0, 0, W, 38], fill='#161b22')
    baslik = f"TEKNİK ÇİZİM | Tip: {depo_tipi}" if lang=='tr' else f"ТЕХНИЧЕСКИЙ ЧЕРТЁЖ | Тип: {depo_tipi}"
    draw.text((W//2, 19), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo siniri - tipe gore
    draw.rectangle([ox, oy, ox+plan_w, oy+plan_h], outline=SINIR, width=3)

    # L tipi - sag ust kose kapali
    if depo_tipi == 'L':
        kose_w = int(plan_w * 0.35)
        kose_h = int(plan_h * 0.35)
        draw.rectangle([ox+plan_w-kose_w, oy, ox+plan_w, oy+kose_h], fill='#161b22', outline='#161b22', width=1)
        draw.line([ox+plan_w-kose_w, oy, ox+plan_w-kose_w, oy+kose_h], fill=SINIR, width=3)
        draw.line([ox+plan_w-kose_w, oy+kose_h, ox+plan_w, oy+kose_h], fill=SINIR, width=3)

    # U tipi - ust ortasi acik
    if depo_tipi == 'U':
        ac_w = int(plan_w * 0.4)
        ac_x = ox + (plan_w - ac_w) // 2
        draw.rectangle([ac_x, oy, ac_x+ac_w, oy+int(plan_h*0.3)], fill='#161b22', outline='#161b22', width=1)
        draw.line([ac_x, oy, ac_x, oy+int(plan_h*0.3)], fill=SINIR, width=3)
        draw.line([ac_x+ac_w, oy, ac_x+ac_w, oy+int(plan_h*0.3)], fill=SINIR, width=3)

    # Giris kapisi
    giris_uzunluk = 50
    if giris_kenar == 'alt':
        if giris_konum == 'orta':
            gx = ox + plan_w // 2
        elif giris_konum == 'sol':
            gx = ox + int(giris_mesafe * sx) + giris_uzunluk // 2
        else:
            gx = ox + plan_w - int(giris_mesafe * sx) - giris_uzunluk // 2
        draw.line([gx-giris_uzunluk//2, oy+plan_h, gx+giris_uzunluk//2, oy+plan_h], fill=SARI, width=6)
        draw.text((gx, oy+plan_h+10), "▲ " + ("GİRİŞ" if lang=='tr' else "ВХОД"), fill=SARI, font=fn, anchor='mt')
    elif giris_kenar == 'ust':
        if giris_konum == 'orta':
            gx = ox + plan_w // 2
        elif giris_konum == 'sol':
            gx = ox + int(giris_mesafe * sx) + giris_uzunluk // 2
        else:
            gx = ox + plan_w - int(giris_mesafe * sx) - giris_uzunluk // 2
        draw.line([gx-giris_uzunluk//2, oy, gx+giris_uzunluk//2, oy], fill=SARI, width=6)
        draw.text((gx, oy-12), "▼ " + ("GİRİŞ" if lang=='tr' else "ВХОД"), fill=SARI, font=fn, anchor='mb')
    elif giris_kenar == 'sol':
        if giris_konum == 'orta':
            gy = oy + plan_h // 2
        elif giris_konum == 'ust':
            gy = oy + int(giris_mesafe * sy) + giris_uzunluk // 2
        else:
            gy = oy + plan_h - int(giris_mesafe * sy) - giris_uzunluk // 2
        draw.line([ox, gy-giris_uzunluk//2, ox, gy+giris_uzunluk//2], fill=SARI, width=6)
        draw.text((ox-10, gy), "◄" + ("GİRİŞ" if lang=='tr' else "ВХОД"), fill=SARI, font=fn, anchor='rm')
    else:  # sag
        if giris_konum == 'orta':
            gy = oy + plan_h // 2
        elif giris_konum == 'ust':
            gy = oy + int(giris_mesafe * sy) + giris_uzunluk // 2
        else:
            gy = oy + plan_h - int(giris_mesafe * sy) - giris_uzunluk // 2
        draw.line([ox+plan_w, gy-giris_uzunluk//2, ox+plan_w, gy+giris_uzunluk//2], fill=SARI, width=6)
        draw.text((ox+plan_w+8, gy), "►" + ("GİRİŞ" if lang=='tr' else "ВХОД"), fill=SARI, font=fn, anchor='lm')

    # Raf alani (bosluklari hesaba kat)
    raf_ox = ox + int(bosluk * sx)
    raf_ow = plan_w - int(bosluk * sx) * 2
    raf_oy = oy + int(bosluk * sy)
    raf_oh = plan_h - int(bosluk * sy) * 2

    raf_satir = max(1, int((genislik - bosluk*2) / (raf_genislik + koridor)))
    raf_perz = max(1, int((uzunluk - bosluk*2) / 1.1))

    rsx = raf_ow / max(raf_perz, 1)
    rsy_total = raf_oh

    for row in range(raf_satir):
        ry1 = raf_oy + int((raf_genislik/2 + row*(raf_genislik+koridor)) * (raf_oh/max(genislik-bosluk*2,1)))
        ry2 = ry1 + max(int(raf_genislik * (raf_oh/max(genislik-bosluk*2,1))), 16)

        for col in range(raf_perz):
            rx1 = raf_ox + int(col * rsx) + 1
            rx2 = raf_ox + int((col+1) * rsx) - 1
            rx2 = max(rx2, rx1+10)

            # Raf dolgu ve cerceve
            draw.rectangle([rx1, ry1, rx2, ry2], fill='#0a1628')
            draw.line([rx1, ry1, rx2, ry2], fill=GRI, width=1)
            draw.line([rx2, ry1, rx1, ry2], fill=GRI, width=1)
            draw.rectangle([rx1, ry1, rx2, ry2], outline=AGRI, width=1)

            # Yatay baglantilar (turuncu)
            draw.line([rx1+5, ry1, rx2-5, ry1], fill=TURUNCU, width=3)
            draw.line([rx1+5, ry2, rx2-5, ry2], fill=TURUNCU, width=3)

            # Derinlik (yesil)
            draw.line([rx1, ry1+5, rx1, ry2-5], fill=YESIL, width=2)
            draw.line([rx2, ry1+5, rx2, ry2-5], fill=YESIL, width=2)

            # Dikmeler (mavi)
            r = 4
            for px, py in [(rx1,ry1),(rx2,ry1),(rx1,ry2),(rx2,ry2)]:
                draw.ellipse([px-r,py-r,px+r,py+r], fill=MAVI, outline='white', width=1)

        # Raf etiketi
        lbl = f"{'Raf' if lang=='tr' else 'Ряд'}{row+1}"
        draw.text((ox+plan_w+5, (ry1+ry2)//2), lbl, fill=BEYAZ, font=fn, anchor='lm')

        # Koridor
        if row < raf_satir-1:
            ky = ry2 + int(koridor*(raf_oh/max(genislik-bosluk*2,1))/2)
            draw.text((ox+plan_w+5, ky), f"{koridor}m", fill=AGRI, font=fn, anchor='lm')

    # Bosluk goster
    if bosluk > 0:
        draw.rectangle([ox+1, oy+1, raf_ox-1, oy+plan_h-1], fill='rgba(255,100,100,30)', outline=KIRMIZI, width=1)
        draw.text((ox+int((bosluk*sx)/2), oy+plan_h//2), f"{bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')

    # Olcu: uzunluk (ust)
    draw.line([ox, oy-16, ox+plan_w, oy-16], fill=AGRI, width=1)
    draw.line([ox, oy-20, ox, oy-12], fill=AGRI, width=1)
    draw.line([ox+plan_w, oy-20, ox+plan_w, oy-12], fill=AGRI, width=1)
    draw.text((ox+plan_w//2, oy-16), f"{uzunluk}m", fill=BEYAZ, font=fn, anchor='mm')

    # Olcu: genislik (sol)
    draw.line([ox-16, oy, ox-16, oy+plan_h], fill=AGRI, width=1)
    draw.line([ox-20, oy, ox-12, oy], fill=AGRI, width=1)
    draw.line([ox-20, oy+plan_h, ox-12, oy+plan_h], fill=AGRI, width=1)
    draw.text((ox-28, oy+plan_h//2), f"{genislik}m", fill=BEYAZ, font=fn, anchor='mm')

    # Alt bilgi
    info_y = H - INFO_H
    draw.rectangle([0, info_y, W, H], fill='#161b22')
    draw.line([0, info_y, W, info_y], fill='#30363d', width=1)

    # Sol - renk + olcu (yakin)
    items = [
        (MAVI,    ("● Dikme" if lang=='tr' else "● Стойка"),       f"{yukseklik}m"),
        (TURUNCU, ("━ Yatay Bağ." if lang=='tr' else "━ Балка"),   f"{raf_genislik}m"),
        (YESIL,   ("│ Derinlik" if lang=='tr' else "│ Глубина"),    "1.10m"),
    ]
    lx, ly = 20, info_y+12
    for renk, isim, olcu in items:
        draw.text((lx, ly), isim, fill=renk, font=fb)
        draw.text((lx+160, ly), olcu, fill=BEYAZ, font=fb)
        ly += 26

    # Sag - bilgiler
    rx2 = W//2 + 20
    ry2 = info_y+12
    if lang=='tr':
        bilgiler = [("Kat",str(kat)),("Raf Satırı",str(raf_satir)),("Sütun",str(raf_perz)),("Toplam",str(raf_satir*raf_perz))]
    else:
        bilgiler = [("Ярусов",str(kat)),("Рядов",str(raf_satir)),("Колонн",str(raf_perz)),("Итого",str(raf_satir*raf_perz))]
    for k,v in bilgiler:
        draw.text((rx2, ry2), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx2+140, ry2), v, fill=BEYAZ, font=fb)
        ry2 += 24

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150,150))
    buf.seek(0)
    return buf, raf_satir, raf_perz

def get_kb(items):
    return ReplyKeyboardMarkup([items], one_time_keyboard=True, resize_keyboard=True)

async def start(update, context):
    await update.message.reply_text(
        "🌐 Dil seçin / Выберите язык:",
        reply_markup=get_kb(["🇹🇷 Türkçe", "🇷🇺 Русский"])
    )
    return LANG

async def hesapla(update, context):
    await update.message.reply_text(
        "🌐 Dil seçin / Выберите язык:",
        reply_markup=get_kb(["🇹🇷 Türkçe", "🇷🇺 Русский"])
    )
    return LANG

async def lang_sec(update, context):
    t = update.message.text
    context.user_data['lang'] = 'ru' if "Русский" in t else 'tr'
    lang = get_lang(context)
    msg = ("🏭 Depo şeklini seçin:\n🔹 I — Düz sıralar\n🔹 L — İki duvara\n🔹 U — Üç duvara"
           if lang=='tr' else
           "🏭 Форма склада:\n🔹 I — Прямые ряды\n🔹 L — Вдоль двух стен\n🔹 U — Вдоль трёх стен")
    await update.message.reply_text(msg, reply_markup=get_kb(["I","L","U"]))
    return DEPO_TIPI

async def depo_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.strip().upper()[0]
    if t not in ['I','L','U']:
        await update.message.reply_text("⚠️ I, L veya U seçin." if lang=='tr' else "⚠️ Выберите I, L или U.")
        return DEPO_TIPI
    context.user_data['depo_tipi'] = t
    msg = ("🚦 Koridor tipi:\n🚜 Forklift (3.0m)\n🔧 Transpalet (2.0m)\n👐 El ile (1.2m)"
           if lang=='tr' else
           "🚦 Тип прохода:\n🚜 Погрузчик (3.0м)\n🔧 Транспалет (2.0м)\n👐 Ручной (1.2м)")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(
        [["🚜 Forklift","🔧 Transpalet","👐 El ile"]], one_time_keyboard=True, resize_keyboard=True))
    return KORIDOR_TIPI

async def koridor_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "forklift" in t or "погрузчик" in t: context.user_data['koridor_tipi'] = 'forklift'
    elif "transpalet" in t or "транспалет" in t: context.user_data['koridor_tipi'] = 'transpalet'
    else: context.user_data['koridor_tipi'] = 'el'
    msg = "📏 Depo uzunluğu (m):\nÖrnek: 20" if lang=='tr' else "📏 Длина склада (м):\nПример: 20"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['uzunluk'] = float(update.message.text.replace(',','.'))
        msg = "📐 Depo genişliği (m):\nÖrnek: 12" if lang=='tr' else "📐 Ширина склада (м):\nПример: 12"
        await update.message.reply_text(msg)
        return GENISLIK
    except:
        await update.message.reply_text("⚠️ Örnek: 20" if lang=='tr' else "⚠️ Пример: 20")
        return UZUNLUK

async def genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',','.'))
        msg = ("📦 Raf başına palet:\n1️⃣ 0.95m  2️⃣ 1.85m\n3️⃣ 2.70m  4️⃣ 3.60m"
               if lang=='tr' else
               "📦 Паллет на ряд:\n1️⃣ 0.95м  2️⃣ 1.85м\n3️⃣ 2.70м  4️⃣ 3.60м")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(
            [["1","2"],["3","4"]], one_time_keyboard=True, resize_keyboard=True))
        return PALET
    except:
        await update.message.reply_text("⚠️ Örnek: 12" if lang=='tr' else "⚠️ Пример: 12")
        return GENISLIK

async def palet_h(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet'] = v
        msg = "🏗 Kat sayısı:\nÖrnek: 3" if lang=='tr' else "🏗 Количество ярусов:\nПример: 3"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("⚠️ 1-4 arası girin." if lang=='tr' else "⚠️ Введите 1-4.")
        return PALET

async def kat_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kat'] = int(update.message.text)
        msg = "📏 Raf yüksekliği (m):\nÖrnek: 5" if lang=='tr' else "📏 Высота стеллажа (м):\nПример: 5"
        await update.message.reply_text(msg)
        return YUKSEKLIK
    except:
        await update.message.reply_text("⚠️ Örnek: 3" if lang=='tr' else "⚠️ Пример: 3")
        return KAT

async def yukseklik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['yukseklik'] = float(update.message.text.replace(',','.'))
        if lang == 'tr':
            msg = "🚪 Giriş kapısı hangi kenarda?\n◀️ Sol duvar\n▶️ Sağ duvar\n🔼 Ön duvar\n🔽 Arka duvar"
            kb = [["◀️ Sol","▶️ Sağ"],["🔼 Ön","🔽 Arka"]]
        else:
            msg = "🚪 Где расположен вход?\n◀️ Левая стена\n▶️ Правая стена\n🔼 Передняя\n🔽 Задняя"
            kb = [["◀️ Лево","▶️ Право"],["🔼 Перед","🔽 Зад"]]
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        return GIRIS_KENAR
    except:
        await update.message.reply_text("⚠️ Örnek: 5" if lang=='tr' else "⚠️ Пример: 5")
        return YUKSEKLIK

async def giris_kenar_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "sol" in t or "лево" in t: context.user_data['giris_kenar'] = 'sol'
    elif "sağ" in t or "право" in t: context.user_data['giris_kenar'] = 'sag'
    elif "ön" in t or "перед" in t: context.user_data['giris_kenar'] = 'ust'
    else: context.user_data['giris_kenar'] = 'alt'

    if lang == 'tr':
        msg = "🚪 Kapının konumu:\n⬅️ Sol tarafa yakın\n➡️ Sağ tarafa yakın\n🎯 Ortada"
        kb = [["⬅️ Sol yakın","➡️ Sağ yakın","🎯 Orta"]]
    else:
        msg = "🚪 Расположение входа:\n⬅️ Ближе к левой\n➡️ Ближе к правой\n🎯 По центру"
        kb = [["⬅️ Левее","➡️ Правее","🎯 Центр"]]
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return GIRIS_KONUM

async def giris_konum_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "orta" in t or "центр" in t:
        context.user_data['giris_konum'] = 'orta'
        context.user_data['giris_mesafe'] = 0
        await _kenar_bosluk_sor(update, context, lang)
        return KENAR_BOSLUK
    elif "sol" in t or "лев" in t:
        context.user_data['giris_konum'] = 'sol'
    else:
        context.user_data['giris_konum'] = 'sag'
    msg = ("🚪 Köşeden kaç metre uzakta?\nÖrnek: 2" if lang=='tr' else
           "🚪 На каком расстоянии от угла (м)?\nПример: 2")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return GIRIS_MESAFE

async def giris_mesafe_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',','.'))
        await _kenar_bosluk_sor(update, context, lang)
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("⚠️ Örnek: 2" if lang=='tr' else "⚠️ Пример: 2")
        return GIRIS_MESAFE

async def _kenar_bosluk_sor(update, context, lang):
    if lang == 'tr':
        msg = "📐 Raf ile duvar arası boşluk?\n0️⃣ Yok (duvara bitişik)\nVeya metre girin (örnek: 0.5)"
    else:
        msg = "📐 Отступ стеллажей от стены?\n0️⃣ Нет (вплотную к стене)\nИли введите метры (пример: 0.5)"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(
        [["0"]], one_time_keyboard=True, resize_keyboard=True))

async def kenar_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kenar_bosluk'] = float(update.message.text.replace(',','.'))
        d = context.user_data
        await update.message.reply_text(
            "⏳ Teknik çizim hazırlanıyor..." if lang=='tr' else "⏳ Подготовка чертежа...",
            reply_markup=ReplyKeyboardRemove()
        )
        resim, raf_satir, raf_perz = teknik_resim_ciz(d, lang)
        toplam = raf_satir * raf_perz
        if lang == 'tr':
            cap = (f"📐 TEKNİK ÇİZİM\n━━━━━━━━━━━━━━\n"
                   f"Depo: {d['uzunluk']}×{d['genislik']}m | Tip: {d['depo_tipi']}\n"
                   f"Raf: {raf_satir} satır × {raf_perz} sütun = {toplam} adet\n"
                   f"Kat: {d['kat']} | Yükseklik: {d['yukseklik']}m\n"
                   f"━━━━━━━━━━━━━━\n"
                   f"Fiyat için /hesapla")
        else:
            cap = (f"📐 ТЕХНИЧЕСКИЙ ЧЕРТЁЖ\n━━━━━━━━━━━━━━\n"
                   f"Склад: {d['uzunluk']}×{d['genislik']}м | Тип: {d['depo_tipi']}\n"
                   f"Стеллажи: {raf_satir}×{raf_perz} = {toplam} шт\n"
                   f"Ярусов: {d['kat']} | Высота: {d['yukseklik']}м\n"
                   f"━━━━━━━━━━━━━━\n"
                   f"Расчёт цены: /raschet")
        await update.message.reply_photo(photo=resim, caption=cap)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"⚠️ Hata: {e}")
        return KENAR_BOSLUK

async def iptal(update, context):
    lang = get_lang(context)
    msg = "❌ İptal. /hesapla ile başlayın." if lang=='tr' else "❌ Отменено. /raschet"
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
            LANG:          [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
            DEPO_TIPI:     [MessageHandler(filters.TEXT & ~filters.COMMAND, depo_tipi_sec)],
            KORIDOR_TIPI:  [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_tipi_sec)],
            UZUNLUK:       [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk_h)],
            GENISLIK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik_h)],
            PALET:         [MessageHandler(filters.TEXT & ~filters.COMMAND, palet_h)],
            KAT:           [MessageHandler(filters.TEXT & ~filters.COMMAND, kat_h)],
            YUKSEKLIK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, yukseklik_h)],
            GIRIS_KENAR:   [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_kenar_h)],
            GIRIS_KONUM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_konum_h)],
            GIRIS_MESAFE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_mesafe_h)],
            KENAR_BOSLUK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_h)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
