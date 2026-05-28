import os
import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, DEPO_TIPI, UZUNLUK, GENISLIK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_BOSLUK, KENAR_BOSLUK,
 KORIDOR_TIPI, PALET, KAT, YUKSEKLIK) = range(13)

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

    W, H = 1100, 820
    img = Image.new('RGB', (W, H), '#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
        fn  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        ft  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        fsm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except:
        fb = fn = ft = fsm = ImageFont.load_default()

    MAVI    = '#4a9eff'
    TURUNCU = '#ff8c42'
    YESIL   = '#4ade80'
    BEYAZ   = '#e8e8e8'
    GRI     = '#2a2a40'
    AGRI    = '#606080'
    SARI    = '#ffd700'
    SINIR   = '#00b4d8'
    KIRMIZI = '#ff5555'
    MOR     = '#c084fc'
    YESIL2  = '#22c55e'

    INFO_H = 130
    pad_l, pad_t, pad_r, pad_b = 70, 55, 100, INFO_H + 35
    plan_w = W - pad_l - pad_r
    plan_h = H - pad_t - pad_b
    ox, oy = pad_l, pad_t
    sx = plan_w / uzunluk
    sy = plan_h / genislik

    # Baslik
    draw.rectangle([0, 0, W, 42], fill='#161b22')
    if lang == 'tr':
        baslik = f"TEKNIK CIZIM  |  Tip: {depo_tipi}  |  {uzunluk}x{genislik}m"
    else:
        baslik = f"TEHNICHESKIY CHERTEZH  |  Tip: {depo_tipi}  |  {uzunluk}x{genislik}m"
    draw.text((W//2, 21), baslik, fill=SARI, font=ft, anchor='mm')

    # --- DEPO SINIRI ---
    if depo_tipi == 'I':
        draw.rectangle([ox, oy, ox+plan_w, oy+plan_h], outline=SINIR, width=3)
        draw.rectangle([ox+2, oy+2, ox+plan_w-2, oy+plan_h-2], outline='#1a3a5c', width=1)

    elif depo_tipi == 'L':
        cw = int(plan_w * 0.38)
        ch = int(plan_h * 0.38)
        pts = [
            (ox, oy),
            (ox+plan_w-cw, oy),
            (ox+plan_w-cw, oy+ch),
            (ox+plan_w, oy+ch),
            (ox+plan_w, oy+plan_h),
            (ox, oy+plan_h),
            (ox, oy)
        ]
        draw.polygon(pts, fill='#0d1117')
        for i in range(len(pts)-1):
            draw.line([pts[i], pts[i+1]], fill=SINIR, width=3)

    elif depo_tipi == 'U':
        cw = int(plan_w * 0.38)
        cx = ox + (plan_w - cw) // 2
        ch = int(plan_h * 0.32)
        pts = [
            (ox, oy),
            (cx, oy),
            (cx, oy+ch),
            (cx+cw, oy+ch),
            (cx+cw, oy),
            (ox+plan_w, oy),
            (ox+plan_w, oy+plan_h),
            (ox, oy+plan_h),
            (ox, oy)
        ]
        draw.polygon(pts, fill='#0d1117')
        for i in range(len(pts)-1):
            draw.line([pts[i], pts[i+1]], fill=SINIR, width=3)

    # --- GIRIS KAPISI ---
    G = 60
    kapi_lbl = "GIRIS/CIKIS KAPISI" if lang=='tr' else "VKHOD/VYKHOD"

    if giris_duvar == 'alt':
        if giris_konum == 'orta':
            gx = ox + plan_w // 2
        elif giris_konum == 'sol':
            gx = ox + int(giris_mesafe * sx) + G//2
        else:
            gx = ox + plan_w - int(giris_mesafe * sx) - G//2
        # Kapi
        draw.line([gx-G//2, oy+plan_h, gx+G//2, oy+plan_h], fill=SARI, width=8)
        draw.text((gx, oy+plan_h+10), kapi_lbl, fill=SARI, font=fsm, anchor='mt')
        # Mesafe
        if giris_konum != 'orta' and giris_mesafe > 0:
            if giris_konum == 'sol':
                draw.line([ox, oy+plan_h+25, gx-G//2, oy+plan_h+25], fill=AGRI, width=1)
                draw.text(((ox + gx-G//2)//2, oy+plan_h+22), f"{giris_mesafe}m", fill=BEYAZ, font=fsm, anchor='mb')
            else:
                draw.line([gx+G//2, oy+plan_h+25, ox+plan_w, oy+plan_h+25], fill=AGRI, width=1)
                draw.text(((gx+G//2+ox+plan_w)//2, oy+plan_h+22), f"{giris_mesafe}m", fill=BEYAZ, font=fsm, anchor='mb')
        # Giris boslugu - YESIL
        bp = int(giris_bosluk * sy)
        draw.rectangle([ox+3, oy+plan_h-bp, ox+plan_w-3, oy+plan_h-3], fill='#052e16', outline=YESIL2, width=2)
        if lang == 'tr':
            draw.text((ox+plan_w//2, oy+plan_h-bp//2), f"YUKLEME/BOSALTMA ALANI\n{giris_bosluk}m", fill=YESIL2, font=fsm, anchor='mm')
        else:
            draw.text((ox+plan_w//2, oy+plan_h-bp//2), f"ZONA POGRUZKI/RAZGRUZKI\n{giris_bosluk}m", fill=YESIL2, font=fsm, anchor='mm')

    elif giris_duvar == 'ust':
        if giris_konum == 'orta': gx = ox + plan_w // 2
        elif giris_konum == 'sol': gx = ox + int(giris_mesafe * sx) + G//2
        else: gx = ox + plan_w - int(giris_mesafe * sx) - G//2
        draw.line([gx-G//2, oy, gx+G//2, oy], fill=SARI, width=8)
        draw.text((gx, oy-10), kapi_lbl, fill=SARI, font=fsm, anchor='mb')
        if giris_konum != 'orta' and giris_mesafe > 0:
            draw.text((ox+10, oy-10), f"{giris_mesafe}m", fill=BEYAZ, font=fsm)
        bp = int(giris_bosluk * sy)
        draw.rectangle([ox+3, oy+3, ox+plan_w-3, oy+bp], fill='#052e16', outline=YESIL2, width=2)
        lbl2 = f"YUKLEME ALANI {giris_bosluk}m" if lang=='tr' else f"ZONA POGRUZKI {giris_bosluk}m"
        draw.text((ox+plan_w//2, oy+bp//2), lbl2, fill=YESIL2, font=fsm, anchor='mm')

    elif giris_duvar == 'sol':
        if giris_konum == 'orta': gy = oy + plan_h // 2
        elif giris_konum == 'ust': gy = oy + int(giris_mesafe * sy) + G//2
        else: gy = oy + plan_h - int(giris_mesafe * sy) - G//2
        draw.line([ox, gy-G//2, ox, gy+G//2], fill=SARI, width=8)
        draw.text((ox-8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='rm')
        if giris_konum != 'orta' and giris_mesafe > 0:
            draw.text((ox-8, gy+G), f"{giris_mesafe}m", fill=BEYAZ, font=fsm, anchor='rm')
        bp = int(giris_bosluk * sx)
        draw.rectangle([ox+3, oy+3, ox+bp, oy+plan_h-3], fill='#052e16', outline=YESIL2, width=2)
        lbl2 = f"YUKLEME\n{giris_bosluk}m" if lang=='tr' else f"ZONA\n{giris_bosluk}m"
        draw.text((ox+bp//2, oy+plan_h//2), lbl2, fill=YESIL2, font=fsm, anchor='mm')

    else:  # sag
        if giris_konum == 'orta': gy = oy + plan_h // 2
        elif giris_konum == 'ust': gy = oy + int(giris_mesafe * sy) + G//2
        else: gy = oy + plan_h - int(giris_mesafe * sy) - G//2
        draw.line([ox+plan_w, gy-G//2, ox+plan_w, gy+G//2], fill=SARI, width=8)
        draw.text((ox+plan_w+8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='lm')
        if giris_konum != 'orta' and giris_mesafe > 0:
            draw.text((ox+plan_w+8, gy+G), f"{giris_mesafe}m", fill=BEYAZ, font=fsm, anchor='lm')
        bp = int(giris_bosluk * sx)
        draw.rectangle([ox+plan_w-bp, oy+3, ox+plan_w-3, oy+plan_h-3], fill='#052e16', outline=YESIL2, width=2)
        lbl2 = f"YUKLEME\n{giris_bosluk}m" if lang=='tr' else f"ZONA\n{giris_bosluk}m"
        draw.text((ox+plan_w-bp//2, oy+plan_h//2), lbl2, fill=YESIL2, font=fsm, anchor='mm')

    # --- RAF ALANI ---
    raf_x1 = ox + int(kenar_bosluk * sx)
    raf_y1 = oy + int(kenar_bosluk * sy)
    raf_x2 = ox + plan_w - int(kenar_bosluk * sx)
    raf_y2 = oy + plan_h - int(kenar_bosluk * sy)

    if giris_duvar == 'alt':   raf_y2 -= int(giris_bosluk * sy)
    elif giris_duvar == 'ust': raf_y1 += int(giris_bosluk * sy)
    elif giris_duvar == 'sol': raf_x1 += int(giris_bosluk * sx)
    else:                      raf_x2 -= int(giris_bosluk * sx)

    raf_alan_w = raf_x2 - raf_x1
    raf_alan_h = raf_y2 - raf_y1
    ef_genislik = raf_alan_h / sy
    ef_uzunluk  = raf_alan_w / sx

    raf_satir = max(1, int(ef_genislik / (raf_genislik + koridor)))
    raf_perz  = max(1, int(ef_uzunluk / 1.1))

    # L ve U icin kesim bolgesi
    if depo_tipi == 'L':
        cw = int(plan_w * 0.38)
        ch = int(plan_h * 0.38)
        L_cut = (ox+plan_w-cw, oy, ox+plan_w, oy+ch)
    else:
        L_cut = None

    if depo_tipi == 'U':
        cw2 = int(plan_w * 0.38)
        cx2 = ox + (plan_w - cw2) // 2
        ch2 = int(plan_h * 0.32)
        U_cut = (cx2, oy, cx2+cw2, oy+ch2)
    else:
        U_cut = None

    raflar = []
    for row in range(raf_satir):
        ry1 = raf_y1 + int((raf_genislik/2 + row*(raf_genislik+koridor)) * sy)
        ry2 = max(ry1 + int(raf_genislik * sy), ry1 + 14)
        for col in range(raf_perz):
            rx1 = raf_x1 + int(col * 1.1 * sx) + 1
            rx2 = max(raf_x1 + int((col+1) * 1.1 * sx) - 1, rx1 + 8)
            if L_cut:
                lx1, ly1, lx2, ly2 = L_cut
                if rx1 > lx1-5 and ry1 < ly2+5:
                    continue
            if U_cut:
                ux1, uy1, ux2, uy2 = U_cut
                if rx1 >= ux1-5 and rx2 <= ux2+5 and ry1 < uy2+5:
                    continue
            raflar.append((rx1, ry1, rx2, ry2, row, col))

    # Raflari ciz
    for (rx1, ry1, rx2, ry2, row, col) in raflar:
        draw.rectangle([rx1, ry1, rx2, ry2], fill='#0a1628')
        draw.line([rx1, ry1, rx2, ry2], fill=GRI, width=1)
        draw.line([rx2, ry1, rx1, ry2], fill=GRI, width=1)
        draw.rectangle([rx1, ry1, rx2, ry2], outline='#404060', width=1)
        draw.line([rx1+4, ry1, rx2-4, ry1], fill=TURUNCU, width=3)
        draw.line([rx1+4, ry2, rx2-4, ry2], fill=TURUNCU, width=3)
        draw.line([rx1, ry1+4, rx1, ry2-4], fill=YESIL, width=2)
        draw.line([rx2, ry1+4, rx2, ry2-4], fill=YESIL, width=2)
        r = 4
        for px, py in [(rx1,ry1),(rx2,ry1),(rx1,ry2),(rx2,ry2)]:
            draw.ellipse([px-r,py-r,px+r,py+r], fill=MAVI, outline='white', width=1)

    # Raf etiketleri
    satir_ry = {}
    for (rx1, ry1, rx2, ry2, row, col) in raflar:
        if row not in satir_ry:
            satir_ry[row] = (ry1, ry2)

    for i, row in enumerate(sorted(satir_ry.keys())):
        ry1, ry2 = satir_ry[row]
        draw.text((ox+plan_w+6, (ry1+ry2)//2), f"R{row+1}", fill=BEYAZ, font=fn, anchor='lm')
        if i > 0:
            prev_row = sorted(satir_ry.keys())[i-1]
            prev_ry2 = satir_ry[prev_row][1]
            ky = (prev_ry2 + ry1) // 2
            draw.text((ox+plan_w+6, ky), f"{koridor}m", fill=MOR, font=fsm, anchor='lm')

    toplam_raf = len(raflar)

    # Olcular
    draw.line([ox, oy-16, ox+plan_w, oy-16], fill=AGRI, width=1)
    draw.line([ox, oy-21, ox, oy-11], fill=AGRI, width=2)
    draw.line([ox+plan_w, oy-21, ox+plan_w, oy-11], fill=AGRI, width=2)
    draw.text((ox+plan_w//2, oy-16), f"{uzunluk}m", fill=BEYAZ, font=fn, anchor='mm')

    draw.line([ox-16, oy, ox-16, oy+plan_h], fill=AGRI, width=1)
    draw.line([ox-21, oy, ox-11, oy], fill=AGRI, width=2)
    draw.line([ox-21, oy+plan_h, ox-11, oy+plan_h], fill=AGRI, width=2)
    draw.text((ox-30, oy+plan_h//2), f"{genislik}m", fill=BEYAZ, font=fn, anchor='mm')

    # --- ALT BILGI ---
    iy = H - INFO_H
    draw.rectangle([0, iy, W, H], fill='#161b22')
    draw.line([0, iy, W, iy], fill='#404060', width=2)

    # Sol: renk aciklamalari
    lx, ly = 20, iy + 12
    if lang == 'tr':
        items = [
            (MAVI,    "● Dikme",           f"{yukseklik} m"),
            (TURUNCU, "━ Yatay Baglanti",  f"{raf_genislik} m"),
            (YESIL,   "│ Derinlik",         "1.10 m"),
            (MOR,     "↔ Koridor",          f"{koridor} m"),
            (YESIL2,  "▦ Yukleme Alani",    f"{giris_bosluk} m"),
        ]
    else:
        items = [
            (MAVI,    "● Stoyka",           f"{yukseklik} m"),
            (TURUNCU, "━ Gorizont. Balka",  f"{raf_genislik} m"),
            (YESIL,   "│ Glubina",           "1.10 m"),
            (MOR,     "↔ Prokhod",           f"{koridor} m"),
            (YESIL2,  "▦ Zona Pogruzki",     f"{giris_bosluk} m"),
        ]
    for renk, isim, olcu in items:
        draw.text((lx, ly), isim, fill=renk, font=fb)
        draw.text((lx+210, ly), olcu, fill=BEYAZ, font=fb)
        ly += 24

    # Sag: sayisal bilgiler
    rx2b = W//2 + 20
    ry2b = iy + 12
    if lang == 'tr':
        bilgiler = [
            ("Kat Sayisi",  str(kat)),
            ("Raf Satiri",  str(len(satir_ry))),
            ("Sutun",       str(raf_perz)),
            ("Toplam Raf",  str(toplam_raf)),
            ("Kenar Bosluk", f"{kenar_bosluk} m"),
        ]
    else:
        bilgiler = [
            ("Yarusov",    str(kat)),
            ("Ryadov",     str(len(satir_ry))),
            ("Kolonn",     str(raf_perz)),
            ("Itogo",      str(toplam_raf)),
            ("Otstup",     f"{kenar_bosluk} m"),
        ]
    for k, v in bilgiler:
        draw.text((rx2b, ry2b), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx2b+180, ry2b), v, fill=BEYAZ, font=fb)
        ry2b += 24

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150, 150))
    buf.seek(0)
    return buf, len(satir_ry), raf_perz, toplam_raf

# --- HANDLERS ---

async def start(update, context):
    await update.message.reply_text(
        "Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce", "🇷🇺 Russkiy"]])
    )
    return LANG

async def hesapla(update, context):
    await update.message.reply_text(
        "Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce", "🇷🇺 Russkiy"]])
    )
    return LANG

async def lang_sec(update, context):
    t = update.message.text
    context.user_data['lang'] = 'ru' if "Russkiy" in t else 'tr'
    lang = get_lang(context)
    if lang == 'tr':
        msg = "🏭 Depo sekli secin:\nI — Duz siralar\nL — Iki duvara bitisik (L sekli)\nU — Uc duvara bitisik (U sekli)"
    else:
        msg = "🏭 Выберите форму склада:\nI — Прямые ряды\nL — Вдоль двух стен (Г-образный)\nU — Вдоль трёх стен (П-образный)"
    await update.message.reply_text(msg, reply_markup=kb([["I", "L", "U"]]))
    return DEPO_TIPI

async def depo_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.strip().upper()[0]
    if t not in ['I', 'L', 'U']:
        await update.message.reply_text("I, L veya U secin." if lang=='tr' else "Введите I, L или U.")
        return DEPO_TIPI
    context.user_data['depo_tipi'] = t
    if lang == 'tr':
        msg = "📏 Depo uzunlugu (metre):\nOrnek: 20"
    else:
        msg = "📏 Длина склада (метры):\nПример: 20"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['uzunluk'] = float(update.message.text.replace(',', '.'))
        msg = "📐 Depo genisligi (metre):\nOrnek: 12" if lang=='tr' else "📐 Ширина склада (метры):\nПример: 12"
        await update.message.reply_text(msg)
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 20" if lang=='tr' else "Только цифры. Пример: 20")
        return UZUNLUK

async def genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',', '.'))
        if lang == 'tr':
            msg = "🚪 Giris kapisi hangi duvarda?\nAlt — Ust — Sol — Sag"
        else:
            msg = "🚪 На какой стене находится вход?\nНиз — Верх — Лево — Право"
        await update.message.reply_text(msg, reply_markup=kb([
            ["Alt" if lang=='tr' else "Низ", "Ust" if lang=='tr' else "Верх"],
            ["Sol" if lang=='tr' else "Лево", "Sag" if lang=='tr' else "Право"]
        ]))
        return GIRIS_DUVAR
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 12" if lang=='tr' else "Только цифры. Пример: 12")
        return GENISLIK

async def giris_duvar_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "alt" in t or "низ" in t: context.user_data['giris_duvar'] = 'alt'
    elif "ust" in t or "верх" in t: context.user_data['giris_duvar'] = 'ust'
    elif "sol" in t or "лево" in t: context.user_data['giris_duvar'] = 'sol'
    else: context.user_data['giris_duvar'] = 'sag'

    if lang == 'tr':
        msg = "🚪 Kapinin konumu:\nSol yakin — Orta — Sag yakin"
        rows = [["Sol yakin", "Orta", "Sag yakin"]]
    else:
        msg = "🚪 Расположение входа:\nЛевее — По центру — Правее"
        rows = [["Левее", "По центру", "Правее"]]
    await update.message.reply_text(msg, reply_markup=kb(rows))
    return GIRIS_KONUM

async def giris_konum_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "orta" in t or "центру" in t:
        context.user_data['giris_konum'] = 'orta'
        context.user_data['giris_mesafe'] = 0.0
        msg = ("🏗 Giris onunde yukleme/bosaltma alani kac metre?\nOrnek: 2"
               if lang=='tr' else
               "🏗 Зона погрузки/разгрузки перед входом (метры)?\nПример: 2")
        await update.message.reply_text(msg, reply_markup=kb([["1", "2", "3"]]))
        return GIRIS_BOSLUK
    elif "sol" in t or "левее" in t:
        context.user_data['giris_konum'] = 'sol'
    else:
        context.user_data['giris_konum'] = 'sag'
    msg = ("🚪 Koseden kac metre uzakta?\nOrnek: 2"
           if lang=='tr' else
           "🚪 Расстояние от угла (метры)?\nПример: 2")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return GIRIS_MESAFE

async def giris_mesafe_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',', '.'))
        msg = ("🏗 Giris onunde yukleme/bosaltma alani kac metre?\nOrnek: 2"
               if lang=='tr' else
               "🏗 Зона погрузки/разгрузки перед входом (метры)?\nПример: 2")
        await update.message.reply_text(msg, reply_markup=kb([["1", "2", "3"]]))
        return GIRIS_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 2" if lang=='tr' else "Только цифры. Пример: 2")
        return GIRIS_MESAFE

async def giris_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_bosluk'] = float(update.message.text.replace(',', '.'))
        msg = ("📐 Raf ile duvar arasi bosluk (m)?\n0 = duvara bitisik\nOrnek: 0.5"
               if lang=='tr' else
               "📐 Отступ стеллажей от стен (м)?\n0 = вплотную к стене\nПример: 0.5")
        await update.message.reply_text(msg, reply_markup=kb([["0", "0.5", "1"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 2" if lang=='tr' else "Только цифры. Пример: 2")
        return GIRIS_BOSLUK

async def kenar_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kenar_bosluk'] = float(update.message.text.replace(',', '.'))
        if lang == 'tr':
            msg = "🚦 Koridor tipi:\nForklift — 3.0m\nTranspalet — 2.0m\nEl ile — 1.2m"
        else:
            msg = "🚦 Тип прохода:\nПогрузчик — 3.0м\nТранспалет — 2.0м\nРучной — 1.2м"
        await update.message.reply_text(msg, reply_markup=kb([
            ["Forklift", "Transpalet", "El ile" if lang=='tr' else "Ruchnoy"]
        ]))
        return KORIDOR_TIPI
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 0.5" if lang=='tr' else "Только цифры. Пример: 0.5")
        return KENAR_BOSLUK

async def koridor_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "forklift" in t or "погрузчик" in t: context.user_data['koridor_tipi'] = 'forklift'
    elif "transpalet" in t or "транспалет" in t: context.user_data['koridor_tipi'] = 'transpalet'
    else: context.user_data['koridor_tipi'] = 'el'
    if lang == 'tr':
        msg = "📦 Raf basina palet sayisi:\n1 — 0.95m\n2 — 1.85m\n3 — 2.70m\n4 — 3.60m"
    else:
        msg = "📦 Количество паллет на ряд:\n1 — 0.95м\n2 — 1.85м\n3 — 2.70м\n4 — 3.60м"
    await update.message.reply_text(msg, reply_markup=kb([["1", "2"], ["3", "4"]]))
    return PALET

async def palet_h(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text.strip()[0])
        if v not in [1, 2, 3, 4]: raise ValueError
        context.user_data['palet'] = v
        msg = "🏗 Kat sayisi:\nOrnek: 3" if lang=='tr' else "🏗 Количество ярусов:\nПример: 3"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1, 2, 3 veya 4 girin." if lang=='tr' else "Введите 1, 2, 3 или 4.")
        return PALET

async def kat_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kat'] = int(update.message.text)
        msg = "📏 Raf yuksekligi (metre):\nOrnek: 5" if lang=='tr' else "📏 Высота стеллажа (метры):\nПример: 5"
        await update.message.reply_text(msg)
        return YUKSEKLIK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 3" if lang=='tr' else "Только цифры. Пример: 3")
        return KAT

async def yukseklik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['yukseklik'] = float(update.message.text.replace(',', '.'))
        d = context.user_data
        await update.message.reply_text(
            "⏳ Teknik cizim hazirlaniyor..." if lang=='tr' else "⏳ Подготовка технического чертежа...",
            reply_markup=ReplyKeyboardRemove()
        )
        resim, raf_satir, raf_perz, toplam = teknik_resim_ciz(d, lang)
        if lang == 'tr':
            cap = (f"TEKNIK CIZIM\n"
                   f"Depo: {d['uzunluk']}x{d['genislik']}m | Tip: {d['depo_tipi']}\n"
                   f"Raf: {raf_satir} satir x {raf_perz} sutun = {toplam} adet\n"
                   f"Kat: {d['kat']} | Yukseklik: {d['yukseklik']}m\n"
                   f"Giris: {d['giris_duvar']} duvar | Yukleme alani: {d['giris_bosluk']}m\n"
                   f"Fiyat icin: /hesapla")
        else:
            cap = (f"TEHNICHESKIY CHERTEZH\n"
                   f"Sklad: {d['uzunluk']}x{d['genislik']}m | Tip: {d['depo_tipi']}\n"
                   f"Stellazhi: {raf_satir}x{raf_perz} = {toplam} sht\n"
                   f"Yarusov: {d['kat']} | Vysota: {d['yukseklik']}m\n"
                   f"Vkhod: {d['giris_duvar']} | Zona: {d['giris_bosluk']}m\n"
                   f"Raschet tseny: /raschet")
        await update.message.reply_photo(photo=resim, caption=cap)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return YUKSEKLIK

async def iptal(update, context):
    lang = get_lang(context)
    await update.message.reply_text(
        "Iptal edildi. /hesapla ile baslayin." if lang=='tr' else "Отменено. Напишите /raschet.",
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
            LANG:         [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
            DEPO_TIPI:    [MessageHandler(filters.TEXT & ~filters.COMMAND, depo_tipi_sec)],
            UZUNLUK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk_h)],
            GENISLIK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik_h)],
            GIRIS_DUVAR:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_duvar_h)],
            GIRIS_KONUM:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_konum_h)],
            GIRIS_MESAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_mesafe_h)],
            GIRIS_BOSLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_bosluk_h)],
            KENAR_BOSLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_h)],
            KORIDOR_TIPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_tipi_sec)],
            PALET:        [MessageHandler(filters.TEXT & ~filters.COMMAND, palet_h)],
            KAT:          [MessageHandler(filters.TEXT & ~filters.COMMAND, kat_h)],
            YUKSEKLIK:    [MessageHandler(filters.TEXT & ~filters.COMMAND, yukseklik_h)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
