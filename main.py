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

def ciz_raf(draw, rx1, ry1, rx2, ry2, TURUNCU, YESIL, MAVI, GRI):
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

def teknik_resim_ciz(d, lang):
    uzunluk    = d['uzunluk']
    genislik   = d['genislik']
    raf_g      = PALET_GENISLIK[d['palet']]
    koridor    = KORIDOR_GENISLIK[d['koridor_tipi']]
    kat        = d['kat']
    yukseklik  = d['yukseklik']
    tip        = d['depo_tipi']
    kb2        = d.get('kenar_bosluk', 0.0)
    g_duvar    = d.get('giris_duvar', 'alt')
    g_konum    = d.get('giris_konum', 'orta')
    g_mesafe   = d.get('giris_mesafe', 0.0)
    g_bosluk   = d.get('giris_bosluk', 2.0)

    W, H = 1100, 820
    img  = Image.new('RGB', (W, H), '#0d1117')
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
    MOR     = '#c084fc'
    YESIL2  = '#22c55e'

    INFO_H = 130
    pl, pt, pr, pb = 70, 55, 110, INFO_H + 35
    pw = W - pl - pr
    ph = H - pt - pb
    ox, oy = pl, pt
    sx = pw / uzunluk
    sy = ph / genislik

    # Baslik
    draw.rectangle([0, 0, W, 42], fill='#161b22')
    if lang == 'tr':
        baslik = f"TEKNIK CIZIM  |  Raf Tipi: {tip}  |  {uzunluk}x{genislik}m"
    else:
        baslik = f"TEHNICHESKIY CHERTEZH  |  Tip: {tip}  |  {uzunluk}x{genislik}m"
    draw.text((W//2, 21), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo - her zaman dikdortgen
    draw.rectangle([ox, oy, ox+pw, oy+ph], outline=SINIR, width=3)
    draw.rectangle([ox+2, oy+2, ox+pw-2, oy+ph-2], outline='#1a3a5c', width=1)

    # Giris kapisi
    G = 60
    kapi_lbl = "GIRIS/CIKIS" if lang=='tr' else "VHOD/VYHOD"

    def kapi_ve_bosluk(gx=None, gy=None):
        if g_duvar == 'alt':
            draw.line([gx-G//2, oy+ph, gx+G//2, oy+ph], fill=SARI, width=8)
            draw.text((gx, oy+ph+10), kapi_lbl, fill=SARI, font=fsm, anchor='mt')
            if g_mesafe > 0 and g_konum != 'orta':
                if g_konum == 'sol':
                    draw.line([ox, oy+ph+28, gx-G//2, oy+ph+28], fill=AGRI, width=1)
                    draw.text(((ox+gx-G//2)//2, oy+ph+25), f"{g_mesafe}m", fill=BEYAZ, font=fsm, anchor='mb')
                else:
                    draw.line([gx+G//2, oy+ph+28, ox+pw, oy+ph+28], fill=AGRI, width=1)
                    draw.text(((gx+G//2+ox+pw)//2, oy+ph+25), f"{g_mesafe}m", fill=BEYAZ, font=fsm, anchor='mb')
            bp = int(g_bosluk * sy)
            draw.rectangle([ox+3, oy+ph-bp, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
            lbl = ("YUKLEME/BOSALTMA ALANI" if lang=='tr' else "ZONA POGRUZKI/RAZGRUZKI")
            draw.text((ox+pw//2, oy+ph-bp//2-8), lbl, fill=YESIL2, font=fsm, anchor='mm')
            draw.text((ox+pw//2, oy+ph-bp//2+8), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')

        elif g_duvar == 'ust':
            draw.line([gx-G//2, oy, gx+G//2, oy], fill=SARI, width=8)
            draw.text((gx, oy-10), kapi_lbl, fill=SARI, font=fsm, anchor='mb')
            if g_mesafe > 0 and g_konum != 'orta':
                draw.text((ox+10, oy-10), f"{g_mesafe}m", fill=BEYAZ, font=fsm)
            bp = int(g_bosluk * sy)
            draw.rectangle([ox+3, oy+3, ox+pw-3, oy+bp], fill='#052e16', outline=YESIL2, width=2)
            lbl = ("YUKLEME/BOSALTMA ALANI" if lang=='tr' else "ZONA POGRUZKI/RAZGRUZKI")
            draw.text((ox+pw//2, oy+bp//2-8), lbl, fill=YESIL2, font=fsm, anchor='mm')
            draw.text((ox+pw//2, oy+bp//2+8), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')

        elif g_duvar == 'sol':
            draw.line([ox, gy-G//2, ox, gy+G//2], fill=SARI, width=8)
            draw.text((ox-8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='rm')
            if g_mesafe > 0 and g_konum != 'orta':
                draw.text((ox-8, gy+G+5), f"{g_mesafe}m", fill=BEYAZ, font=fsm, anchor='rm')
            bp = int(g_bosluk * sx)
            draw.rectangle([ox+3, oy+3, ox+bp, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
            lbl = ("YUKLEME\nALANI" if lang=='tr' else "ZONA\nPOGRUZKI")
            draw.text((ox+bp//2, oy+ph//2-8), lbl, fill=YESIL2, font=fsm, anchor='mm')
            draw.text((ox+bp//2, oy+ph//2+8), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')

        else:  # sag
            draw.line([ox+pw, gy-G//2, ox+pw, gy+G//2], fill=SARI, width=8)
            draw.text((ox+pw+8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='lm')
            if g_mesafe > 0 and g_konum != 'orta':
                draw.text((ox+pw+8, gy+G+5), f"{g_mesafe}m", fill=BEYAZ, font=fsm, anchor='lm')
            bp = int(g_bosluk * sx)
            draw.rectangle([ox+pw-bp, oy+3, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
            lbl = ("YUKLEME\nALANI" if lang=='tr' else "ZONA\nPOGRUZKI")
            draw.text((ox+pw-bp//2, oy+ph//2-8), lbl, fill=YESIL2, font=fsm, anchor='mm')
            draw.text((ox+pw-bp//2, oy+ph//2+8), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')

    # Kapi konumu hesapla
    if g_duvar in ['alt', 'ust']:
        if g_konum == 'orta': gx = ox + pw // 2
        elif g_konum == 'sol': gx = ox + int(g_mesafe * sx) + G//2
        else: gx = ox + pw - int(g_mesafe * sx) - G//2
        kapi_ve_bosluk(gx=gx)
    else:
        if g_konum == 'orta': gy = oy + ph // 2
        elif g_konum == 'ust': gy = oy + int(g_mesafe * sy) + G//2
        else: gy = oy + ph - int(g_mesafe * sy) - G//2
        kapi_ve_bosluk(gy=gy)

    # Raf alani sinirlarini hesapla
    raf_x1 = ox + int(kb2 * sx)
    raf_y1 = oy + int(kb2 * sy)
    raf_x2 = ox + pw - int(kb2 * sx)
    raf_y2 = oy + ph - int(kb2 * sy)

    bp_px_y = int(g_bosluk * sy)
    bp_px_x = int(g_bosluk * sx)
    if g_duvar == 'alt':   raf_y2 -= bp_px_y
    elif g_duvar == 'ust': raf_y1 += bp_px_y
    elif g_duvar == 'sol': raf_x1 += bp_px_x
    else:                  raf_x2 -= bp_px_x

    raf_aw = raf_x2 - raf_x1
    raf_ah = raf_y2 - raf_y1
    ef_u   = raf_aw / sx
    ef_g   = raf_ah / sy

    raflar = []

    if tip == 'I':
        # Paralel sıralar - depo ortasında
        raf_satir = max(1, int(ef_g / (raf_g + koridor)))
        raf_perz  = max(1, int(ef_u / 1.1))
        for row in range(raf_satir):
            ry1 = raf_y1 + int((raf_g/2 + row*(raf_g+koridor)) * sy)
            ry2 = max(ry1 + int(raf_g * sy), ry1 + 14)
            for col in range(raf_perz):
                rx1 = raf_x1 + int(col * 1.1 * sx) + 1
                rx2 = max(raf_x1 + int((col+1) * 1.1 * sx) - 1, rx1 + 8)
                raflar.append((rx1, ry1, rx2, ry2, 'I', row))

    elif tip == 'L':
        # Sol duvara bitisik raf sirasi (dikey)
        # Alt duvara bitisik raf sirasi (yatay)
        raf_derinlik_px = int(raf_g * sx)
        raf_derinlik_py = int(raf_g * sy)
        raf_boy_px = int(1.1 * sx)
        raf_boy_py = int(1.1 * sy)

        # Sol duvara bitisik - yukaridan asagiya
        sol_x1 = raf_x1
        sol_x2 = raf_x1 + raf_derinlik_px
        n_sol = max(1, int(ef_g / 1.1))
        for i in range(n_sol):
            ry1 = raf_y1 + int(i * 1.1 * sy)
            ry2 = max(ry1 + int(0.9 * sy), ry1 + 8)
            if ry2 > raf_y2: break
            raflar.append((sol_x1, ry1, sol_x2, ry2, 'L_sol', i))

        # Alt duvara bitisik - soldan saga (sol duvar rafinin sagından başla)
        alt_y2 = raf_y2
        alt_y1 = raf_y2 - raf_derinlik_py
        baslangic_x = sol_x2 + int(koridor * sx)
        n_alt = max(1, int((raf_x2 - baslangic_x) / 1.1 / sx))
        for i in range(n_alt):
            rx1 = baslangic_x + int(i * 1.1 * sx)
            rx2 = max(rx1 + int(0.9 * sx), rx1 + 8)
            if rx2 > raf_x2: break
            raflar.append((rx1, alt_y1, rx2, alt_y2, 'L_alt', i))

    elif tip == 'U':
        # Sol duvara bitisik raf
        # Sag duvara bitisik raf
        # Alt duvara bitisik raf
        raf_derinlik_px = int(raf_g * sx)
        raf_derinlik_py = int(raf_g * sy)

        # Sol duvara bitisik
        sol_x1 = raf_x1
        sol_x2 = raf_x1 + raf_derinlik_px
        n_sol = max(1, int(ef_g / 1.1))
        for i in range(n_sol):
            ry1 = raf_y1 + int(i * 1.1 * sy)
            ry2 = max(ry1 + int(0.9 * sy), ry1 + 8)
            if ry2 > raf_y2 - int(raf_g * sy): break
            raflar.append((sol_x1, ry1, sol_x2, ry2, 'U_sol', i))

        # Sag duvara bitisik
        sag_x2 = raf_x2
        sag_x1 = raf_x2 - raf_derinlik_px
        for i in range(n_sol):
            ry1 = raf_y1 + int(i * 1.1 * sy)
            ry2 = max(ry1 + int(0.9 * sy), ry1 + 8)
            if ry2 > raf_y2 - int(raf_g * sy): break
            raflar.append((sag_x1, ry1, sag_x2, ry2, 'U_sag', i))

        # Alt duvara bitisik (sol ve sag raflar arasinda)
        alt_y2 = raf_y2
        alt_y1 = raf_y2 - raf_derinlik_py
        baslangic_x = sol_x2 + int(koridor * sx)
        bitis_x = sag_x1 - int(koridor * sx)
        n_alt = max(1, int((bitis_x - baslangic_x) / (1.1 * sx)))
        for i in range(n_alt):
            rx1 = baslangic_x + int(i * 1.1 * sx)
            rx2 = max(rx1 + int(0.9 * sx), rx1 + 8)
            if rx2 > bitis_x: break
            raflar.append((rx1, alt_y1, rx2, alt_y2, 'U_alt', i))

    # Raflari ciz
    for (rx1, ry1, rx2, ry2, tip_r, idx) in raflar:
        ciz_raf(draw, rx1, ry1, rx2, ry2, TURUNCU, YESIL, MAVI, GRI)

    toplam_raf = len(raflar)

    # Raf etiketleri - I icin satir numaralari
    if tip == 'I':
        satir_ry = {}
        for (rx1, ry1, rx2, ry2, t, row) in raflar:
            if row not in satir_ry: satir_ry[row] = (ry1, ry2)
        for i, row in enumerate(sorted(satir_ry.keys())):
            ry1, ry2 = satir_ry[row]
            draw.text((ox+pw+6, (ry1+ry2)//2), f"R{row+1}", fill=BEYAZ, font=fn, anchor='lm')
            if i > 0:
                prev = sorted(satir_ry.keys())[i-1]
                prev_ry2 = satir_ry[prev][1]
                ky = (prev_ry2 + ry1) // 2
                draw.text((ox+pw+6, ky), f"{koridor}m", fill=MOR, font=fsm, anchor='lm')
    else:
        # L ve U icin duvar etiketleri
        if lang == 'tr':
            if tip == 'L':
                draw.text((ox+pw+6, oy+ph//4), "Sol\nDuvar", fill=BEYAZ, font=fsm, anchor='lm')
                draw.text((ox+pw//2, oy+ph+6), "Alt Duvar", fill=BEYAZ, font=fsm, anchor='mt')
            else:
                draw.text((ox+pw+6, oy+ph//4), "Sol/Sag\nDuvar", fill=BEYAZ, font=fsm, anchor='lm')
                draw.text((ox+pw//2, oy+ph+6), "Alt Duvar", fill=BEYAZ, font=fsm, anchor='mt')
        else:
            if tip == 'L':
                draw.text((ox+pw+6, oy+ph//4), "Lev.\nStena", fill=BEYAZ, font=fsm, anchor='lm')
                draw.text((ox+pw//2, oy+ph+6), "Nizh. Stena", fill=BEYAZ, font=fsm, anchor='mt')
            else:
                draw.text((ox+pw+6, oy+ph//4), "Lev./Prav.\nStena", fill=BEYAZ, font=fsm, anchor='lm')
                draw.text((ox+pw//2, oy+ph+6), "Nizh. Stena", fill=BEYAZ, font=fsm, anchor='mt')

    # Olcular
    draw.line([ox, oy-16, ox+pw, oy-16], fill=AGRI, width=1)
    draw.line([ox, oy-21, ox, oy-11], fill=AGRI, width=2)
    draw.line([ox+pw, oy-21, ox+pw, oy-11], fill=AGRI, width=2)
    draw.text((ox+pw//2, oy-16), f"{uzunluk}m", fill=BEYAZ, font=fn, anchor='mm')
    draw.line([ox-16, oy, ox-16, oy+ph], fill=AGRI, width=1)
    draw.line([ox-21, oy, ox-11, oy], fill=AGRI, width=2)
    draw.line([ox-21, oy+ph, ox-11, oy+ph], fill=AGRI, width=2)
    draw.text((ox-30, oy+ph//2), f"{genislik}m", fill=BEYAZ, font=fn, anchor='mm')

    # Alt bilgi
    iy = H - INFO_H
    draw.rectangle([0, iy, W, H], fill='#161b22')
    draw.line([0, iy, W, iy], fill='#404060', width=2)

    lx, ly = 20, iy + 14
    if lang == 'tr':
        items = [
            (MAVI,    "● Dikme",             f"{yukseklik} m"),
            (TURUNCU, "━ Yatay Baglanti",    f"{raf_g} m"),
            (YESIL,   "| Derinlik",           "1.10 m"),
            (MOR,     "↔ Koridor",            f"{koridor} m"),
            (YESIL2,  "▦ Yukleme Alani",      f"{g_bosluk} m"),
        ]
    else:
        items = [
            (MAVI,    "● Stoyka",             f"{yukseklik} m"),
            (TURUNCU, "━ Gorizont. Balka",    f"{raf_g} m"),
            (YESIL,   "| Glubina",             "1.10 m"),
            (MOR,     "↔ Prokhod",             f"{koridor} m"),
            (YESIL2,  "▦ Zona Pogruzki",       f"{g_bosluk} m"),
        ]
    for renk, isim, olcu in items:
        draw.text((lx, ly), isim, fill=renk, font=fb)
        draw.text((lx+220, ly), olcu, fill=BEYAZ, font=fb)
        ly += 24

    rx2b, ry2b = W//2 + 20, iy + 14
    if lang == 'tr':
        bilgiler = [
            ("Kat Sayisi",   str(kat)),
            ("Toplam Raf",   str(toplam_raf)),
            ("Raf Tipi",     tip),
            ("Kenar Bosluk", f"{kb2} m"),
            ("Giris Alani",  f"{g_bosluk} m"),
        ]
    else:
        bilgiler = [
            ("Yarusov",      str(kat)),
            ("Itogo Stell.", str(toplam_raf)),
            ("Tip",          tip),
            ("Otstup",       f"{kb2} m"),
            ("Zona vkhoda",  f"{g_bosluk} m"),
        ]
    for k, v in bilgiler:
        draw.text((rx2b, ry2b), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx2b+185, ry2b), v, fill=BEYAZ, font=fb)
        ry2b += 24

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150, 150))
    buf.seek(0)
    return buf, toplam_raf

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
        msg = ("🏭 Raf dizilisini secin:\n\n"
               "I — Raflar birbirine paralel, ortada\n"
               "L — Raflar iki duvara bitisik (L sekli)\n"
               "U — Raflar uc duvara bitisik (U sekli)\n\n"
               "Not: Depo her zaman dikdortgendir, sadece raflar degisir.")
    else:
        msg = ("🏭 Выберите расположение стеллажей:\n\n"
               "I — Стеллажи параллельно друг другу, в центре\n"
               "L — Стеллажи вдоль двух стен (Г-образно)\n"
               "U — Стеллажи вдоль трёх стен (П-образно)\n\n"
               "Примечание: Склад всегда прямоугольный, меняется только расположение стеллажей.")
    await update.message.reply_text(msg, reply_markup=kb([["I", "L", "U"]]))
    return DEPO_TIPI

async def depo_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.strip().upper()[0]
    if t not in ['I', 'L', 'U']:
        await update.message.reply_text("I, L veya U secin." if lang=='tr' else "Введите I, L или U.")
        return DEPO_TIPI
    context.user_data['depo_tipi'] = t
    msg = "📏 Depo uzunlugu (metre):\nOrnek: 20" if lang=='tr' else "📏 Длина склада (метры):\nПример: 20"
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
            msg = "🚪 Giris kapisi hangi duvarda?"
            rows = [["Alt duvar", "Ust duvar"], ["Sol duvar", "Sag duvar"]]
        else:
            msg = "🚪 На какой стене находится вход?"
            rows = [["Нижняя стена", "Верхняя стена"], ["Левая стена", "Правая стена"]]
        await update.message.reply_text(msg, reply_markup=kb(rows))
        return GIRIS_DUVAR
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 12" if lang=='tr' else "Только цифры. Пример: 12")
        return GENISLIK

async def giris_duvar_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "alt" in t or "нижн" in t: context.user_data['giris_duvar'] = 'alt'
    elif "ust" in t or "верхн" in t: context.user_data['giris_duvar'] = 'ust'
    elif "sol" in t or "лев" in t: context.user_data['giris_duvar'] = 'sol'
    else: context.user_data['giris_duvar'] = 'sag'
    if lang == 'tr':
        msg = "🚪 Kapinin konumu?"
        rows = [["Sol yakin", "Orta", "Sag yakin"]]
    else:
        msg = "🚪 Где именно вход?"
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
               "🏗 Зона погрузки/разгрузки перед входом (м)?\nПример: 2")
        await update.message.reply_text(msg, reply_markup=kb([["1", "2", "3"]]))
        return GIRIS_BOSLUK
    elif "sol" in t or "левее" in t:
        context.user_data['giris_konum'] = 'sol'
    else:
        context.user_data['giris_konum'] = 'sag'
    msg = ("🚪 Koseden kac metre uzakta?\nOrnek: 2"
           if lang=='tr' else
           "🚪 Расстояние от угла (м)?\nПример: 2")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return GIRIS_MESAFE

async def giris_mesafe_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',', '.'))
        msg = ("🏗 Giris onunde yukleme/bosaltma alani kac metre?\nOrnek: 2"
               if lang=='tr' else
               "🏗 Зона погрузки/разгрузки перед входом (м)?\nПример: 2")
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
               "📐 Отступ стеллажей от стен (м)?\n0 = вплотную\nПример: 0.5")
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
        await update.message.reply_text(msg, reply_markup=kb([["Forklift", "Transpalet", "El ile" if lang=='tr' else "Ruchnoy"]]))
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
        resim, toplam = teknik_resim_ciz(d, lang)
        if lang == 'tr':
            cap = (f"TEKNIK CIZIM\n"
                   f"Depo: {d['uzunluk']}x{d['genislik']}m\n"
                   f"Raf tipi: {d['depo_tipi']} | Toplam raf: {toplam} adet\n"
                   f"Kat: {d['kat']} | Yukseklik: {d['yukseklik']}m\n"
                   f"Giris: {d['giris_duvar']} duvar | Yukleme alani: {d['giris_bosluk']}m\n"
                   f"Fiyat icin: /hesapla")
        else:
            cap = (f"TEHNICHESKIY CHERTEZH\n"
                   f"Sklad: {d['uzunluk']}x{d['genislik']}m\n"
                   f"Tip: {d['depo_tipi']} | Vsego: {toplam} sht\n"
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
