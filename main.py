import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN =import os
TOKEN = os.environ.get("TOKEN")


(LANG, DEPO_TIPI, KORIDOR_TIPI, UZUNLUK, GENISLIK, PALET, KAT, YUKSEKLIK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_BOSLUK, KENAR_BOSLUK) = range(13)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def kb(rows):
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)

def teknik_resim_ciz(d, lang):
    uzunluk = d['uzunluk']
    genislik = d['genislik']
    raf_genislik = PALET_GENISLIK[d['palet']]
    koridor = KORIDOR_GENISLIK[d['koridor_tipi']]
    kat = d['kat']
    yukseklik = d['yukseklik']
    depo_tipi = d['depo_tipi']
    kenar_bosluk = d.get('kenar_bosluk', 0.0)
    giris_duvar = d.get('giris_duvar', 'alt')
    giris_konum = d.get('giris_konum', 'orta')
    giris_mesafe = d.get('giris_mesafe', 0.0)
    giris_bosluk = d.get('giris_bosluk', 2.0)

    W, H = 1050, 780
    img = Image.new('RGB', (W, H), '#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
        fn = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
    except:
        fb = fn = ft = ImageFont.load_default()

    MAVI    = '#4a9eff'
    TURUNCU = '#ff8c42'
    YESIL   = '#4ade80'
    BEYAZ   = '#e0e0e0'
    GRI     = '#2a2a40'
    AGRI    = '#505070'
    SARI    = '#ffd700'
    SINIR   = '#00b4d8'
    KIRMIZI = '#ff5555'
    MOR     = '#c084fc'

    INFO_H = 115
    pad_l, pad_t, pad_r, pad_b = 65, 52, 90, INFO_H + 30
    plan_w = W - pad_l - pad_r
    plan_h = H - pad_t - pad_b
    ox, oy = pad_l, pad_t

    sx = plan_w / uzunluk
    sy = plan_h / genislik

    # Baslik
    draw.rectangle([0, 0, W, 38], fill='#161b22')
    baslik = f"TEKNİK ÇİZİM | {depo_tipi} Tipi" if lang=='tr' else f"ТЕХНИЧЕСКИЙ ЧЕРТЁЖ | Тип {depo_tipi}"
    draw.text((W//2, 19), baslik, fill=SARI, font=ft, anchor='mm')

    # ---- DEPO SINIRI ----
    # I tipi: normal dikdortgen
    # L tipi: sol alt + sag alt + sol ust = L sekli (sag ust kose eksik)
    # U tipi: sol + alt + sag duvarlar, ust ortasi acik

    if depo_tipi == 'I':
        draw.rectangle([ox, oy, ox+plan_w, oy+plan_h], outline=SINIR, width=3)

    elif depo_tipi == 'L':
        # L: sag ust bolum kapali
        cut_w = int(plan_w * 0.4)
        cut_h = int(plan_h * 0.4)
        # duvarlar
        pts = [
            (ox, oy),
            (ox+plan_w-cut_w, oy),
            (ox+plan_w-cut_w, oy+cut_h),
            (ox+plan_w, oy+cut_h),
            (ox+plan_w, oy+plan_h),
            (ox, oy+plan_h),
            (ox, oy)
        ]
        draw.polygon(pts, outline=SINIR, fill='#0d1117')
        draw.line(pts, fill=SINIR, width=3)

    elif depo_tipi == 'U':
        # U: ust ortasi acik
        cut_w = int(plan_w * 0.4)
        cut_x = ox + (plan_w - cut_w) // 2
        cut_h = int(plan_h * 0.35)
        pts = [
            (ox, oy),
            (cut_x, oy),
            (cut_x, oy+cut_h),
            (cut_x+cut_w, oy+cut_h),
            (cut_x+cut_w, oy),
            (ox+plan_w, oy),
            (ox+plan_w, oy+plan_h),
            (ox, oy+plan_h),
            (ox, oy)
        ]
        draw.polygon(pts, outline=SINIR, fill='#0d1117')
        draw.line(pts, fill=SINIR, width=3)

    # ---- GİRİŞ KAPISI ----
    G = 55  # kapi genisligi px
    if giris_duvar == 'alt':
        if giris_konum == 'orta':
            gx = ox + plan_w // 2
        elif giris_konum == 'sol':
            gx = ox + int(giris_mesafe * sx) + G//2
        else:
            gx = ox + plan_w - int(giris_mesafe * sx) - G//2
        draw.line([gx-G//2, oy+plan_h, gx+G//2, oy+plan_h], fill=SARI, width=7)
        draw.text((gx, oy+plan_h+8), "▲ GİRİŞ" if lang=='tr' else "▲ ВХОД", fill=SARI, font=fn, anchor='mt')
        # giris boslugu - kirmizi alan
        bosluk_px = int(giris_bosluk * sy)
        draw.rectangle([ox+2, oy+plan_h-bosluk_px, ox+plan_w-2, oy+plan_h-2],
                       fill='rgba(255,85,85,25)', outline=KIRMIZI, width=1)
        draw.text((ox+plan_w//2, oy+plan_h-bosluk_px//2),
                  f"{'Boşluk' if lang=='tr' else 'Зона'} {giris_bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')

    elif giris_duvar == 'ust':
        if giris_konum == 'orta': gx = ox + plan_w // 2
        elif giris_konum == 'sol': gx = ox + int(giris_mesafe * sx) + G//2
        else: gx = ox + plan_w - int(giris_mesafe * sx) - G//2
        draw.line([gx-G//2, oy, gx+G//2, oy], fill=SARI, width=7)
        draw.text((gx, oy-8), "▼ GİRİŞ" if lang=='tr' else "▼ ВХОД", fill=SARI, font=fn, anchor='mb')
        bosluk_px = int(giris_bosluk * sy)
        draw.rectangle([ox+2, oy+2, ox+plan_w-2, oy+bosluk_px],
                       fill='rgba(255,85,85,25)', outline=KIRMIZI, width=1)
        draw.text((ox+plan_w//2, oy+bosluk_px//2),
                  f"{'Boşluk' if lang=='tr' else 'Зона'} {giris_bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')

    elif giris_duvar == 'sol':
        if giris_konum == 'orta': gy = oy + plan_h // 2
        elif giris_konum == 'ust': gy = oy + int(giris_mesafe * sy) + G//2
        else: gy = oy + plan_h - int(giris_mesafe * sy) - G//2
        draw.line([ox, gy-G//2, ox, gy+G//2], fill=SARI, width=7)
        draw.text((ox-8, gy), "◄" + ("GİRİŞ" if lang=='tr' else "ВХОД"), fill=SARI, font=fn, anchor='rm')
        bosluk_px = int(giris_bosluk * sx)
        draw.rectangle([ox+2, oy+2, ox+bosluk_px, oy+plan_h-2],
                       fill='rgba(255,85,85,25)', outline=KIRMIZI, width=1)
        draw.text((ox+bosluk_px//2, oy+plan_h//2),
                  f"{giris_bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')

    else:  # sag
        if giris_konum == 'orta': gy = oy + plan_h // 2
        elif giris_konum == 'ust': gy = oy + int(giris_mesafe * sy) + G//2
        else: gy = oy + plan_h - int(giris_mesafe * sy) - G//2
        draw.line([ox+plan_w, gy-G//2, ox+plan_w, gy+G//2], fill=SARI, width=7)
        draw.text((ox+plan_w+8, gy), "►" + ("GİRİŞ" if lang=='tr' else "ВХОД"), fill=SARI, font=fn, anchor='lm')
        bosluk_px = int(giris_bosluk * sx)
        draw.rectangle([ox+plan_w-bosluk_px, oy+2, ox+plan_w-2, oy+plan_h-2],
                       fill='rgba(255,85,85,25)', outline=KIRMIZI, width=1)
        draw.text((ox+plan_w-bosluk_px//2, oy+plan_h//2),
                  f"{giris_bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')

    # ---- RAF YERLEŞİMİ (I / L / U) ----
    kb2 = kenar_bosluk
    raf_alan_x1 = ox + int(kb2 * sx)
    raf_alan_y1 = oy + int(kb2 * sy)
    raf_alan_x2 = ox + plan_w - int(kb2 * sx)
    raf_alan_y2 = oy + plan_h - int(kb2 * sy)

    # Giris boslugu - giriş tarafındaki raf kısalması
    if giris_duvar == 'alt':
        raf_alan_y2 -= int(giris_bosluk * sy)
    elif giris_duvar == 'ust':
        raf_alan_y1 += int(giris_bosluk * sy)
    elif giris_duvar == 'sol':
        raf_alan_x1 += int(giris_bosluk * sx)
    else:
        raf_alan_x2 -= int(giris_bosluk * sx)

    raf_alan_w = raf_alan_x2 - raf_alan_x1
    raf_alan_h = raf_alan_y2 - raf_alan_y1

    efektif_genislik = (raf_alan_h / sy)
    efektif_uzunluk  = (raf_alan_w / sx)

    if depo_tipi == 'I':
        # Düz sıralar - ortada
        raf_satir = max(1, int(efektif_genislik / (raf_genislik + koridor)))
        raf_perz  = max(1, int(efektif_uzunluk / 1.1))
        raflar = []
        for row in range(raf_satir):
            ry1 = raf_alan_y1 + int((raf_genislik/2 + row*(raf_genislik+koridor)) * sy)
            ry2 = ry1 + max(int(raf_genislik * sy), 14)
            for col in range(raf_perz):
                rx1 = raf_alan_x1 + int(col * 1.1 * sx) + 1
                rx2 = raf_alan_x1 + int((col+1) * 1.1 * sx) - 1
                raflar.append((rx1, ry1, max(rx2,rx1+8), ry2, row, col))

    elif depo_tipi == 'L':
        # Sol duvar boyunca + alt duvar boyunca
        cut_w = int(plan_w * 0.4)
        cut_h = int(plan_h * 0.4)
        raf_satir = max(1, int(efektif_genislik / (raf_genislik + koridor)))
        raf_perz  = max(1, int(efektif_uzunluk / 1.1))
        raflar = []
        for row in range(raf_satir):
            ry1 = raf_alan_y1 + int((raf_genislik/2 + row*(raf_genislik+koridor)) * sy)
            ry2 = ry1 + max(int(raf_genislik * sy), 14)
            for col in range(raf_perz):
                rx1 = raf_alan_x1 + int(col * 1.1 * sx) + 1
                rx2 = raf_alan_x1 + int((col+1) * 1.1 * sx) - 1
                # L bölgesindeki rafları atla (sag ust)
                if rx2 > ox+plan_w-cut_w-10 and ry1 < oy+cut_h+10:
                    continue
                raflar.append((rx1, ry1, max(rx2,rx1+8), ry2, row, col))

    elif depo_tipi == 'U':
        # Ust ortasi acik, U sekli
        cut_w = int(plan_w * 0.4)
        cut_x = ox + (plan_w - cut_w) // 2
        cut_h = int(plan_h * 0.35)
        raf_satir = max(1, int(efektif_genislik / (raf_genislik + koridor)))
        raf_perz  = max(1, int(efektif_uzunluk / 1.1))
        raflar = []
        for row in range(raf_satir):
            ry1 = raf_alan_y1 + int((raf_genislik/2 + row*(raf_genislik+koridor)) * sy)
            ry2 = ry1 + max(int(raf_genislik * sy), 14)
            for col in range(raf_perz):
                rx1 = raf_alan_x1 + int(col * 1.1 * sx) + 1
                rx2 = raf_alan_x1 + int((col+1) * 1.1 * sx) - 1
                # U bölgesindeki rafları atla (ust orta)
                if rx1 > cut_x-10 and rx2 < cut_x+cut_w+10 and ry1 < oy+cut_h+10:
                    continue
                raflar.append((rx1, ry1, max(rx2,rx1+8), ry2, row, col))
        raf_satir_gercek = raf_satir
        raf_perz_gercek = raf_perz

    else:
        raflar = []
        raf_satir = 1
        raf_perz = 1

    # Rafları çiz
    satir_set = set()
    for (rx1, ry1, rx2, ry2, row, col) in raflar:
        satir_set.add(row)
        draw.rectangle([rx1, ry1, rx2, ry2], fill='#0a1628')
        draw.line([rx1, ry1, rx2, ry2], fill=GRI, width=1)
        draw.line([rx2, ry1, rx1, ry2], fill=GRI, width=1)
        draw.rectangle([rx1, ry1, rx2, ry2], outline=AGRI, width=1)
        draw.line([rx1+4, ry1, rx2-4, ry1], fill=TURUNCU, width=3)
        draw.line([rx1+4, ry2, rx2-4, ry2], fill=TURUNCU, width=3)
        draw.line([rx1, ry1+4, rx1, ry2-4], fill=YESIL, width=2)
        draw.line([rx2, ry1+4, rx2, ry2-4], fill=YESIL, width=2)
        r = 4
        for px, py in [(rx1,ry1),(rx2,ry1),(rx1,ry2),(rx2,ry2)]:
            draw.ellipse([px-r,py-r,px+r,py+r], fill=MAVI, outline='white', width=1)

    # Raf etiketleri ve koridor göstergesi
    prev_ry2 = {}
    for (rx1, ry1, rx2, ry2, row, col) in raflar:
        if col == 0:
            lbl = f"{'Raf' if lang=='tr' else 'Ряд'}{row+1}"
            draw.text((ox+plan_w+4, (ry1+ry2)//2), lbl, fill=BEYAZ, font=fn, anchor='lm')
        if row > 0 and col == 0:
            prev = [(r2, ro) for (r1,ry1_,r2,ry2_,ro,c) in raflar if ro == row-1 and c == 0]
            if prev:
                prev_ry2_val = prev[0][0]
                ky = (prev_ry2_val + ry1) // 2
                draw.text((ox+plan_w+4, ky), f"{koridor}m", fill=MOR, font=fn, anchor='lm')

    raf_satir_gercek = len(satir_set)
    raf_perz_gercek = len([x for x in raflar if x[4]==0])
    toplam_raf = len(raflar)

    # Ölçü: uzunluk (ust) - yakin
    draw.line([ox, oy-14, ox+plan_w, oy-14], fill=AGRI, width=1)
    draw.line([ox, oy-18, ox, oy-10], fill=AGRI, width=2)
    draw.line([ox+plan_w, oy-18, ox+plan_w, oy-10], fill=AGRI, width=2)
    draw.text((ox+plan_w//2, oy-14), f"{uzunluk}m", fill=BEYAZ, font=fn, anchor='mm')

    # Ölçü: genislik (sol) - yakin
    draw.line([ox-14, oy, ox-14, oy+plan_h], fill=AGRI, width=1)
    draw.line([ox-18, oy, ox-10, oy], fill=AGRI, width=2)
    draw.line([ox-18, oy+plan_h, ox-10, oy+plan_h], fill=AGRI, width=2)
    draw.text((ox-26, oy+plan_h//2), f"{genislik}m", fill=BEYAZ, font=fn, anchor='mm')

    # ---- ALT BİLGİ ----
    iy = H - INFO_H
    draw.rectangle([0, iy, W, H], fill='#161b22')
    draw.line([0, iy, W, iy], fill='#30363d', width=1)

    # Sol: renk + olcular (yakin yaz)
    lx, ly = 18, iy + 10
    items = [
        (MAVI,    ("● Dikme" if lang=='tr' else "● Стойка"),          f"{yukseklik}m"),
        (TURUNCU, ("━ Yatay Bağ." if lang=='tr' else "━ Балка"),       f"{raf_genislik}m"),
        (YESIL,   ("│ Derinlik" if lang=='tr' else "│ Глубина"),        "1.10m"),
        (MOR,     ("⟷ Koridor" if lang=='tr' else "⟷ Проход"),         f"{koridor}m"),
        (KIRMIZI, ("▦ Giriş Böl." if lang=='tr' else "▦ Зона входа"),   f"{giris_bosluk}m"),
    ]
    for renk, isim, olcu in items:
        draw.text((lx, ly), isim, fill=renk, font=fb)
        draw.text((lx+155, ly), olcu, fill=BEYAZ, font=fb)
        ly += 21

    # Sag: sayisal bilgiler
    rx = W//2 + 10
    ry = iy + 10
    if lang == 'tr':
        bilgiler = [
            ("Kat", str(kat)),
            ("Raf Satırı", str(raf_satir_gercek)),
            ("Sütun", str(raf_perz_gercek)),
            ("Toplam Raf", str(toplam_raf)),
            ("Kenar Boşluk", f"{kenar_bosluk}m"),
        ]
    else:
        bilgiler = [
            ("Ярусов", str(kat)),
            ("Рядов", str(raf_satir_gercek)),
            ("Колонн", str(raf_perz_gercek)),
            ("Итого", str(toplam_raf)),
            ("Отступ", f"{kenar_bosluk}м"),
        ]
    for k, v in bilgiler:
        draw.text((rx, ry), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx+150, ry), v, fill=BEYAZ, font=fb)
        ry += 21

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150, 150))
    buf.seek(0)
    return buf, raf_satir_gercek, raf_perz_gercek, toplam_raf

# ---- HANDLERS ----

async def start(update, context):
    await update.message.reply_text("🌐 Dil seçin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Türkçe", "🇷🇺 Русский"]]))
    return LANG

async def hesapla(update, context):
    await update.message.reply_text("🌐 Dil seçin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Türkçe", "🇷🇺 Русский"]]))
    return LANG

async def lang_sec(update, context):
    t = update.message.text
    context.user_data['lang'] = 'ru' if "Русский" in t else 'tr'
    lang = get_lang(context)
    msg = ("🏭 Depo şekli:\n🔹 I — Düz sıralar\n🔹 L — İki duvara bitişik\n🔹 U — Üç duvara bitişik"
           if lang=='tr' else
           "🏭 Форма склада:\n🔹 I — Прямые ряды\n🔹 L — Вдоль двух стен\n🔹 U — Вдоль трёх стен")
    await update.message.reply_text(msg, reply_markup=kb([["I", "L", "U"]]))
    return DEPO_TIPI

async def depo_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.strip().upper()[0]
    if t not in ['I','L','U']:
        await update.message.reply_text("⚠️ I, L veya U seçin." if lang=='tr' else "⚠️ I, L или U.")
        return DEPO_TIPI
    context.user_data['depo_tipi'] = t
    msg = ("🚦 Koridor tipi:\n🚜 Forklift (3.0m)\n🔧 Transpalet (2.0m)\n👐 El ile (1.2m)"
           if lang=='tr' else
           "🚦 Тип прохода:\n🚜 Погрузчик (3.0м)\n🔧 Транспалет (2.0м)\n👐 Ручной (1.2м)")
    await update.message.reply_text(msg, reply_markup=kb([["🚜 Forklift","🔧 Transpalet","👐 El ile"]]))
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
        await update.message.reply_text("⚠️ Rakam girin. Örnek: 20" if lang=='tr' else "⚠️ Только цифры. Пример: 20")
        return UZUNLUK

async def genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',','.'))
        msg = ("📦 Raf başına palet:\n1️⃣ 0.95m  2️⃣ 1.85m\n3️⃣ 2.70m  4️⃣ 3.60m"
               if lang=='tr' else
               "📦 Паллет на ряд:\n1️⃣ 0.95м  2️⃣ 1.85м\n3️⃣ 2.70м  4️⃣ 3.60м")
        await update.message.reply_text(msg, reply_markup=kb([["1","2"],["3","4"]]))
        return PALET
    except:
        await update.message.reply_text("⚠️ Rakam girin." if lang=='tr' else "⚠️ Только цифры.")
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
        await update.message.reply_text("⚠️ 1, 2, 3 veya 4 girin." if lang=='tr' else "⚠️ 1, 2, 3 или 4.")
        return PALET

async def kat_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kat'] = int(update.message.text)
        msg = "📏 Raf yüksekliği (m):\nÖrnek: 5" if lang=='tr' else "📏 Высота стеллажа (м):\nПример: 5"
        await update.message.reply_text(msg)
        return YUKSEKLIK
    except:
        await update.message.reply_text("⚠️ Rakam girin." if lang=='tr' else "⚠️ Только цифры.")
        return KAT

async def yukseklik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['yukseklik'] = float(update.message.text.replace(',','.'))
        if lang=='tr':
            msg = "🚪 Giriş kapısı hangi duvarda?\n🔽 Alt duvar\n🔼 Üst duvar\n◀️ Sol duvar\n▶️ Sağ duvar"
            rows = [["🔽 Alt","🔼 Üst"],["◀️ Sol","▶️ Sağ"]]
        else:
            msg = "🚪 На какой стене вход?\n🔽 Нижняя\n🔼 Верхняя\n◀️ Левая\n▶️ Правая"
            rows = [["🔽 Низ","🔼 Верх"],["◀️ Лево","▶️ Право"]]
        await update.message.reply_text(msg, reply_markup=kb(rows))
        return GIRIS_DUVAR
    except:
        await update.message.reply_text("⚠️ Örnek: 5" if lang=='tr' else "⚠️ Пример: 5")
        return YUKSEKLIK

async def giris_duvar_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "alt" in t or "низ" in t: context.user_data['giris_duvar'] = 'alt'
    elif "üst" in t or "верх" in t: context.user_data['giris_duvar'] = 'ust'
    elif "sol" in t or "лево" in t: context.user_data['giris_duvar'] = 'sol'
    else: context.user_data['giris_duvar'] = 'sag'

    if lang=='tr':
        msg = "🚪 Kapının konumu?\n⬅️ Sol tarafa yakın\n➡️ Sağ tarafa yakın\n🎯 Ortada"
        rows = [["⬅️ Sol yakın","🎯 Orta","➡️ Sağ yakın"]]
    else:
        msg = "🚪 Где именно вход?\n⬅️ Ближе к левой\n🎯 По центру\n➡️ Ближе к правой"
        rows = [["⬅️ Левее","🎯 Центр","➡️ Правее"]]
    await update.message.reply_text(msg, reply_markup=kb(rows))
    return GIRIS_KONUM

async def giris_konum_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "orta" in t or "центр" in t:
        context.user_data['giris_konum'] = 'orta'
        context.user_data['giris_mesafe'] = 0.0
        await _sor_giris_bosluk(update, context, lang)
        return GIRIS_BOSLUK
    elif "sol" in t or "лев" in t:
        context.user_data['giris_konum'] = 'sol'
    else:
        context.user_data['giris_konum'] = 'sag'
    msg = ("🚪 Köşeden kaç metre uzakta?\nÖrnek: 2" if lang=='tr' else
           "🚪 Расстояние от угла (м)?\nПример: 2")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return GIRIS_MESAFE

async def giris_mesafe_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',','.'))
        await _sor_giris_bosluk(update, context, lang)
        return GIRIS_BOSLUK
    except:
        await update.message.reply_text("⚠️ Örnek: 2" if lang=='tr' else "⚠️ Пример: 2")
        return GIRIS_MESAFE

async def _sor_giris_bosluk(update, context, lang):
    msg = ("🏗 Giriş önünde boş alan kaç metre?\n(Yük boşaltma / yükleme alanı)\nÖrnek: 2"
           if lang=='tr' else
           "🏗 Свободная зона перед входом (м)?\n(Зона погрузки/разгрузки)\nПример: 2")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(
        [["1","2","3"]], one_time_keyboard=True, resize_keyboard=True))

async def giris_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_bosluk'] = float(update.message.text.replace(',','.'))
        msg = ("📐 Raf ile duvar arası boşluk (m)?\n0 = duvara bitişik\nÖrnek: 0.5"
               if lang=='tr' else
               "📐 Отступ от стен (м)?\n0 = вплотную\nПример: 0.5")
        await update.message.reply_text(msg, reply_markup=kb([["0","0.5","1"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("⚠️ Örnek: 2" if lang=='tr' else "⚠️ Пример: 2")
        return GIRIS_BOSLUK

async def kenar_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kenar_bosluk'] = float(update.message.text.replace(',','.'))
        d = context.user_data
        await update.message.reply_text(
            "⏳ Teknik çizim hazırlanıyor..." if lang=='tr' else "⏳ Подготовка чертежа...",
            reply_markup=ReplyKeyboardRemove()
        )
        resim, raf_satir, raf_perz, toplam = teknik_resim_ciz(d, lang)
        if lang=='tr':
            cap = (f"📐 TEKNİK ÇİZİM\n━━━━━━━━━━━━━━\n"
                   f"Depo: {d['uzunluk']}×{d['genislik']}m | Tip: {d['depo_tipi']}\n"
                   f"Raf: {raf_satir} satır × {raf_perz} sütun = {toplam} adet\n"
                   f"Kat: {d['kat']} | Yükseklik: {d['yukseklik']}m\n"
                   f"Giriş: {d['giris_duvar']} duvar | Boşluk: {d['giris_bosluk']}m\n"
                   f"━━━━━━━━━━━━━━\nFiyat için /hesapla")
        else:
            cap = (f"📐 ТЕХНИЧЕСКИЙ ЧЕРТЁЖ\n━━━━━━━━━━━━━━\n"
                   f"Склад: {d['uzunluk']}×{d['genislik']}м | Тип: {d['depo_tipi']}\n"
                   f"Стеллажи: {raf_satir}×{raf_perz} = {toplam} шт\n"
                   f"Ярусов: {d['kat']} | Высота: {d['yukseklik']}м\n"
                   f"Вход: {d['giris_duvar']} | Зона: {d['giris_bosluk']}м\n"
                   f"━━━━━━━━━━━━━━\nРасчёт: /raschet")
        await update.message.reply_photo(photo=resim, caption=cap)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"⚠️ Hata: {e}")
        return KENAR_BOSLUK

async def iptal(update, context):
    lang = get_lang(context)
    await update.message.reply_text(
        "❌ İptal. /hesapla ile başlayın." if lang=='tr' else "❌ Отменено. /raschet",
        reply_markup=ReplyKeyboardRemove()
    )
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
            GIRIS_DUVAR:   [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_duvar_h)],
            GIRIS_KONUM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_konum_h)],
            GIRIS_MESAFE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_mesafe_h)],
            GIRIS_BOSLUK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_bosluk_h)],
            KENAR_BOSLUK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_h)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
