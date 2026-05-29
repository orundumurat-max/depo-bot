import os
import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, UZUNLUK, GENISLIK, DEPO_YUK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_BOSLUK,
 KENAR_BOSLUK, KORIDOR_TIPI, PALET, KAT, RAF_YUK,
 ONERI_ONAYLA, MANUEL_TIP) = range(15)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def kb(rows):
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)

def hesapla_tipler(uzunluk, genislik, raf_g, koridor, kb2, g_duvar, g_bosluk):
    if g_duvar in ['alt', 'ust']:
        ef_g = genislik - kb2*2 - g_bosluk
        ef_u = uzunluk - kb2*2
    else:
        ef_g = genislik - kb2*2
        ef_u = uzunluk - kb2*2 - g_bosluk

    ef_g = max(ef_g, 1)
    ef_u = max(ef_u, 1)

    i_satir = max(1, int(ef_g / (raf_g + koridor)))
    i_perz  = max(1, int(ef_u / 1.1))
    i_toplam = i_satir * i_perz
    i_kalan = ef_g - i_satir * (raf_g + koridor)

    sol_adet = max(1, int(ef_g / 1.1))
    alt_adet = max(1, int((ef_u - raf_g - koridor) / 1.1))
    l_toplam = sol_adet + alt_adet

    sol_u = max(1, int(ef_g / 1.1))
    sag_u = sol_u
    ara_u = ef_u - raf_g*2 - koridor*2
    alt_u = max(0, int(ara_u / 1.1)) if ara_u > 0 else 0
    u_toplam = sol_u + sag_u + alt_u

    sonuclar = {
        'I': {'toplam': i_toplam, 'satir': i_satir, 'perz': i_perz, 'kalan': i_kalan},
        'L': {'toplam': l_toplam, 'sol': sol_adet, 'alt': alt_adet},
        'U': {'toplam': u_toplam, 'sol': sol_u, 'sag': sag_u, 'alt': alt_u},
    }
    en_iyi = max(sonuclar, key=lambda x: sonuclar[x]['toplam'])
    return en_iyi, sonuclar

def ciz_raf(draw, rx1, ry1, rx2, ry2):
    TURUNCU = '#ff8c42'
    YESIL   = '#4ade80'
    MAVI    = '#4a9eff'
    GRI     = '#2a2a40'
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

def teknik_ciz(d, lang, tip, sonuclar):
    uzunluk  = d['uzunluk']
    genislik = d['genislik']
    raf_g    = PALET_GENISLIK[d['palet']]
    koridor  = KORIDOR_GENISLIK[d['koridor_tipi']]
    kat      = d['kat']
    raf_yuk  = d['raf_yuk']
    kb2      = d.get('kenar_bosluk', 0.0)
    g_duvar  = d.get('giris_duvar', 'alt')
    g_konum  = d.get('giris_konum', 'orta')
    g_mesafe = d.get('giris_mesafe', 0.0)
    g_bosluk = d.get('giris_bosluk', 2.0)

    W, H = 1100, 840
    img  = Image.new('RGB', (W, H), '#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
        fn  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        ft  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        fsm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except:
        fb = fn = ft = fsm = ImageFont.load_default()

    BEYAZ  = '#e8e8e8'
    AGRI   = '#606080'
    SARI   = '#ffd700'
    SINIR  = '#00b4d8'
    MOR    = '#c084fc'
    YESIL2 = '#22c55e'
    TURUNCU= '#ff8c42'
    YESIL  = '#4ade80'
    MAVI   = '#4a9eff'

    INFO_H = 140
    pl, pt, pr, pb = 70, 55, 110, INFO_H + 40
    pw = W - pl - pr
    ph = H - pt - pb
    ox, oy = pl, pt
    sx = pw / uzunluk
    sy = ph / genislik

    # Baslik
    draw.rectangle([0, 0, W, 42], fill='#161b22')
    toplam = sonuclar[tip]['toplam']
    if lang == 'tr':
        baslik = f"TEKNIK CIZIM | Tip:{tip} | {uzunluk}x{genislik}m | {toplam} raf"
    else:
        baslik = f"CHERTEZH | Tip:{tip} | {uzunluk}x{genislik}m | {toplam} stell."
    draw.text((W//2, 21), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo dikdortgen
    draw.rectangle([ox, oy, ox+pw, oy+ph], outline=SINIR, width=3)
    draw.rectangle([ox+2, oy+2, ox+pw-2, oy+ph-2], outline='#1a3a5c', width=1)

    # Kapi konumu
    G = 60
    kapi_lbl = "GIRIS/CIKIS" if lang=='tr' else "VHOD/VYHOD"
    gx = gy = 0
    if g_duvar in ['alt', 'ust']:
        if g_konum == 'orta': gx = ox + pw // 2
        elif g_konum == 'sol': gx = ox + int(g_mesafe * sx) + G//2
        else: gx = ox + pw - int(g_mesafe * sx) - G//2
    else:
        if g_konum == 'orta': gy = oy + ph // 2
        elif g_konum == 'ust': gy = oy + int(g_mesafe * sy) + G//2
        else: gy = oy + ph - int(g_mesafe * sy) - G//2

    # Yukleme alani + kapi - kapinin oldugu tarafta
    bp_y = int(g_bosluk * sy)
    bp_x = int(g_bosluk * sx)
    zona_lbl = "YUKLEME/BOSALTMA" if lang=='tr' else "ZONA POGRUZKI"

    if g_duvar == 'alt':
        draw.rectangle([ox+3, oy+ph-bp_y, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw//2, oy+ph-bp_y//2-7), zona_lbl, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw//2, oy+ph-bp_y//2+9), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')
        draw.line([gx-G//2, oy+ph, gx+G//2, oy+ph], fill=SARI, width=8)
        draw.text((gx, oy+ph+10), kapi_lbl, fill=SARI, font=fsm, anchor='mt')
    elif g_duvar == 'ust':
        draw.rectangle([ox+3, oy+3, ox+pw-3, oy+bp_y], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw//2, oy+bp_y//2-7), zona_lbl, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw//2, oy+bp_y//2+9), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')
        draw.line([gx-G//2, oy, gx+G//2, oy], fill=SARI, width=8)
        draw.text((gx, oy-10), kapi_lbl, fill=SARI, font=fsm, anchor='mb')
    elif g_duvar == 'sol':
        draw.rectangle([ox+3, oy+3, ox+bp_x, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+bp_x//2, oy+ph//2-7), zona_lbl, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+bp_x//2, oy+ph//2+9), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')
        draw.line([ox, gy-G//2, ox, gy+G//2], fill=SARI, width=8)
        draw.text((ox-8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='rm')
    else:
        draw.rectangle([ox+pw-bp_x, oy+3, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw-bp_x//2, oy+ph//2-7), zona_lbl, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw-bp_x//2, oy+ph//2+9), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')
        draw.line([ox+pw, gy-G//2, ox+pw, gy+G//2], fill=SARI, width=8)
        draw.text((ox+pw+8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='lm')

    # RAF ALANI - kapinin KARSISINDA
    rx1 = ox + int(kb2 * sx)
    ry1 = oy + int(kb2 * sy)
    rx2 = ox + pw - int(kb2 * sx)
    ry2 = oy + ph - int(kb2 * sy)

    if g_duvar == 'alt':   ry2 -= bp_y
    elif g_duvar == 'ust': ry1 += bp_y
    elif g_duvar == 'sol': rx1 += bp_x
    else:                  rx2 -= bp_x

    aw = rx2 - rx1
    ah = ry2 - ry1
    eu = aw / sx
    eg = ah / sy

    raflar = []
    kalan_txt = ""

    if tip == 'I':
        n_satir = max(1, int(eg / (raf_g + koridor)))
        n_perz  = max(1, int(eu / 1.1))
        for row in range(n_satir):
            rry1 = ry1 + int((raf_g/2 + row*(raf_g+koridor)) * sy)
            rry2 = max(rry1 + int(raf_g * sy), rry1 + 14)
            for col in range(n_perz):
                rrx1 = rx1 + int(col * 1.1 * sx) + 1
                rrx2 = max(rx1 + int((col+1)*1.1*sx)-1, rrx1+8)
                raflar.append((rrx1, rry1, rrx2, rry2, row))
        kalan = eg - n_satir*(raf_g+koridor)
        ek = int(kalan / (raf_g + koridor))
        if lang == 'tr':
            kalan_txt = f"Kalan: {kalan:.1f}m"
            if ek > 0: kalan_txt += f" → {ek} sira daha!"
        else:
            kalan_txt = f"Остаток: {kalan:.1f}м"
            if ek > 0: kalan_txt += f" → ещё {ek} ряд(а)!"

        # Etiketler
        satir_ry = {}
        for (a,b,c,d2,row) in raflar:
            if row not in satir_ry: satir_ry[row] = (b,d2)
        for i, row in enumerate(sorted(satir_ry.keys())):
            b,d2 = satir_ry[row]
            draw.text((ox+pw+6, (b+d2)//2), f"R{row+1}", fill=BEYAZ, font=fn, anchor='lm')
            if i > 0:
                prev = sorted(satir_ry.keys())[i-1]
                prev_d2 = satir_ry[prev][1]
                ky = (prev_d2 + b) // 2
                draw.text((ox+pw+6, ky), f"{koridor}m", fill=MOR, font=fsm, anchor='lm')

    elif tip == 'L':
        dp_x = int(raf_g * sx)
        dp_y = int(raf_g * sy)
        # Sol duvara bitisik
        n_sol = max(1, int(eg / 1.1))
        for i in range(n_sol):
            rry1 = ry1 + int(i * 1.1 * sy)
            rry2 = max(rry1 + int(0.9*sy), rry1+8)
            if rry2 > ry2: break
            raflar.append((rx1, rry1, rx1+dp_x, rry2, i))
        # Kapinin karsisindaki duvara bitisik
        if g_duvar == 'alt':
            # Ust duvara bitisik
            bas_x = rx1 + dp_x + int(koridor*sx)
            for i in range(max(1, int((eu - raf_g - koridor) / 1.1))):
                rrx1 = bas_x + int(i*1.1*sx)
                rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                if rrx2 > rx2: break
                raflar.append((rrx1, ry1, rrx2, ry1+dp_y, i+100))
        else:
            # Alt duvara bitisik
            bas_x = rx1 + dp_x + int(koridor*sx)
            for i in range(max(1, int((eu - raf_g - koridor) / 1.1))):
                rrx1 = bas_x + int(i*1.1*sx)
                rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                if rrx2 > rx2: break
                raflar.append((rrx1, ry2-dp_y, rrx2, ry2, i+100))
        kalan_txt = f"{len(raflar)} raf" if lang=='tr' else f"{len(raflar)} stell."

    elif tip == 'U':
        dp_x = int(raf_g * sx)
        dp_y = int(raf_g * sy)
        sol_x1, sol_x2 = rx1, rx1+dp_x
        sag_x1, sag_x2 = rx2-dp_x, rx2
        bas_x = sol_x2 + int(koridor*sx)
        bit_x = sag_x1 - int(koridor*sx)
        # Sol ve sag duvara bitisik
        n_yan = max(1, int(eg / 1.1))
        for i in range(n_yan):
            rry1 = ry1 + int(i*1.1*sy)
            rry2 = max(rry1+int(0.9*sy), rry1+8)
            if rry2 > ry2: break
            raflar.append((sol_x1, rry1, sol_x2, rry2, i))
            raflar.append((sag_x1, rry1, sag_x2, rry2, i+100))
        # Kapinin karsisindaki duvara bitisik
        if g_duvar == 'alt':
            n_ust = max(1, int((bit_x-bas_x)/(1.1*sx)))
            for i in range(n_ust):
                rrx1 = bas_x + int(i*1.1*sx)
                rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                if rrx2 > bit_x: break
                raflar.append((rrx1, ry1, rrx2, ry1+dp_y, i+200))
        else:
            n_alt = max(1, int((bit_x-bas_x)/(1.1*sx)))
            for i in range(n_alt):
                rrx1 = bas_x + int(i*1.1*sx)
                rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                if rrx2 > bit_x: break
                raflar.append((rrx1, ry2-dp_y, rrx2, ry2, i+200))
        kalan_txt = f"{len(raflar)} raf" if lang=='tr' else f"{len(raflar)} stell."

    # Raflari ciz
    for r in raflar:
        ciz_raf(draw, r[0], r[1], r[2], r[3])

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

    lx, ly = 20, iy+14
    if lang == 'tr':
        items = [
            (MAVI,    "● Dikme",          f"{raf_yuk} m"),
            (TURUNCU, "━ Yatay Baglanti", f"{raf_g} m"),
            (YESIL,   "| Derinlik",        "1.10 m"),
            (MOR,     "↔ Koridor",         f"{koridor} m"),
            (YESIL2,  "▦ Yukleme Alani",   f"{g_bosluk} m"),
        ]
    else:
        items = [
            (MAVI,    "● Stoyka",          f"{raf_yuk} m"),
            (TURUNCU, "━ Balka",           f"{raf_g} m"),
            (YESIL,   "| Glubina",          "1.10 m"),
            (MOR,     "↔ Prokhod",          f"{koridor} m"),
            (YESIL2,  "▦ Zona Pogruzki",    f"{g_bosluk} m"),
        ]
    for renk, isim, olcu in items:
        draw.text((lx, ly), isim, fill=renk, font=fb)
        draw.text((lx+220, ly), olcu, fill=BEYAZ, font=fb)
        ly += 25

    rx2b, ry2b = W//2+20, iy+14
    if lang == 'tr':
        bilgiler = [
            ("Kat",        str(kat)),
            ("Toplam Raf", str(len(raflar))),
            ("Tip",        tip),
            ("Kenar",      f"{kb2} m"),
            ("Durum",      kalan_txt),
        ]
    else:
        bilgiler = [
            ("Yarusov",    str(kat)),
            ("Vsego",      str(len(raflar))),
            ("Tip",        tip),
            ("Otstup",     f"{kb2} m"),
            ("Status",     kalan_txt),
        ]
    for k, v in bilgiler:
        draw.text((rx2b, ry2b), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx2b+185, ry2b), v, fill=BEYAZ, font=fb)
        ry2b += 25

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150,150))
    buf.seek(0)
    return buf, len(raflar), kalan_txt

# ---- HANDLERS ----

async def baslat(update, context):
    context.user_data.clear()
    await update.message.reply_text(
        "Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce", "🇷🇺 Russkiy"]])
    )
    return LANG

async def lang_sec(update, context):
    t = update.message.text
    context.user_data['lang'] = 'ru' if "Russkiy" in t else 'tr'
    lang = get_lang(context)
    msg = "📏 Depo uzunlugu (m):\nOrnek: 20" if lang=='tr' else "📏 Длина склада (м):\nПример: 20"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['uzunluk'] = float(update.message.text.replace(',','.'))
        msg = "📐 Depo genisligi (m):\nOrnek: 12" if lang=='tr' else "📐 Ширина склада (м):\nПример: 12"
        await update.message.reply_text(msg)
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 20" if lang=='tr' else "Только цифры. Пример: 20")
        return UZUNLUK

async def genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',','.'))
        msg = "📏 Depo yuksekligi (m):\nOrnek: 6" if lang=='tr' else "📏 Высота склада (м):\nПример: 6"
        await update.message.reply_text(msg)
        return DEPO_YUK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 12" if lang=='tr' else "Только цифры. Пример: 12")
        return GENISLIK

async def depo_yuk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['depo_yukseklik'] = float(update.message.text.replace(',','.'))
        if lang == 'tr':
            msg = "🚪 Giris kapisi hangi duvarda?"
            rows = [["Alt duvar","Ust duvar"],["Sol duvar","Sag duvar"]]
        else:
            msg = "🚪 На какой стене вход?"
            rows = [["Нижняя стена","Верхняя стена"],["Левая стена","Правая стена"]]
        await update.message.reply_text(msg, reply_markup=kb(rows))
        return GIRIS_DUVAR
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 6" if lang=='tr' else "Только цифры. Пример: 6")
        return DEPO_YUK

async def giris_duvar_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "alt" in t or "нижн" in t: context.user_data['giris_duvar'] = 'alt'
    elif "ust" in t or "верхн" in t: context.user_data['giris_duvar'] = 'ust'
    elif "sol" in t or "лев" in t: context.user_data['giris_duvar'] = 'sol'
    else: context.user_data['giris_duvar'] = 'sag'
    if lang == 'tr':
        rows = [["Sol yakin","Orta","Sag yakin"]]
        msg = "🚪 Kapinin konumu?"
    else:
        rows = [["Левее","По центру","Правее"]]
        msg = "🚪 Где именно вход?"
    await update.message.reply_text(msg, reply_markup=kb(rows))
    return GIRIS_KONUM

async def giris_konum_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "orta" in t or "центру" in t:
        context.user_data['giris_konum'] = 'orta'
        context.user_data['giris_mesafe'] = 0.0
        msg = ("🏗 Yukleme/bosaltma alani kac metre?\nOrnek: 3"
               if lang=='tr' else
               "🏗 Зона погрузки/разгрузки (м)?\nПример: 3")
        await update.message.reply_text(msg, reply_markup=kb([["2","3","4","5"]]))
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
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',','.'))
        msg = ("🏗 Yukleme/bosaltma alani kac metre?\nOrnek: 3"
               if lang=='tr' else
               "🏗 Зона погрузки/разгрузки (м)?\nПример: 3")
        await update.message.reply_text(msg, reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 2" if lang=='tr' else "Только цифры. Пример: 2")
        return GIRIS_MESAFE

async def giris_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_bosluk'] = float(update.message.text.replace(',','.'))
        msg = ("📐 Raf-duvar arasi bosluk (m)?\n0 = bitisik\nOrnek: 0.5"
               if lang=='tr' else
               "📐 Отступ от стен (м)?\n0 = вплотную\nПример: 0.5")
        await update.message.reply_text(msg, reply_markup=kb([["0","0.5","1"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_BOSLUK

async def kenar_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kenar_bosluk'] = float(update.message.text.replace(',','.'))
        if lang == 'tr':
            msg = "🚦 Koridor tipi?\nForklift — 3.0m\nTranspalet — 2.0m\nEl ile — 1.2m"
        else:
            msg = "🚦 Тип прохода?\nПогрузчик — 3.0м\nТранспалет — 2.0м\nРучной — 1.2м"
        await update.message.reply_text(msg, reply_markup=kb([
            ["Forklift","Transpalet","El ile" if lang=='tr' else "Ruchnoy"]
        ]))
        return KORIDOR_TIPI
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return KENAR_BOSLUK

async def koridor_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "forklift" in t or "погрузчик" in t: context.user_data['koridor_tipi'] = 'forklift'
    elif "transpalet" in t or "транспалет" in t: context.user_data['koridor_tipi'] = 'transpalet'
    else: context.user_data['koridor_tipi'] = 'el'
    if lang == 'tr':
        msg = "📦 Raf basina palet?\n1 — 0.95m\n2 — 1.85m\n3 — 2.70m\n4 — 3.60m"
    else:
        msg = "📦 Паллет на ряд?\n1 — 0.95м\n2 — 1.85м\n3 — 2.70м\n4 — 3.60м"
    await update.message.reply_text(msg, reply_markup=kb([["1","2"],["3","4"]]))
    return PALET

async def palet_h(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet'] = v
        msg = "🏗 Kat sayisi?\nOrnek: 3" if lang=='tr' else "🏗 Количество ярусов?\nПример: 3"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1-4 arasi girin." if lang=='tr' else "Введите 1-4.")
        return PALET

async def kat_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kat'] = int(update.message.text)
        msg = "📏 Raf yuksekligi (m)?\nOrnek: 5" if lang=='tr' else "📏 Высота стеллажа (м)?\nПример: 5"
        await update.message.reply_text(msg)
        return RAF_YUK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 3" if lang=='tr' else "Только цифры. Пример: 3")
        return KAT

async def raf_yuk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['raf_yuk'] = float(update.message.text.replace(',','.'))
        d = context.user_data
        en_iyi, sonuclar = hesapla_tipler(
            d['uzunluk'], d['genislik'],
            PALET_GENISLIK[d['palet']],
            KORIDOR_GENISLIK[d['koridor_tipi']],
            d.get('kenar_bosluk', 0),
            d['giris_duvar'],
            d['giris_bosluk']
        )
        context.user_data['sonuclar'] = sonuclar
        context.user_data['en_iyi'] = en_iyi

        si = sonuclar['I']
        sl = sonuclar['L']
        su = sonuclar['U']

        if lang == 'tr':
            msg = (f"🤖 SİSTEM ÖNERİSİ\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"📊 Karsilastirma:\n"
                   f"I tipi: {si['toplam']} raf ({si['satir']} sira × {si['perz']} sutun)\n"
                   f"L tipi: {sl['toplam']} raf\n"
                   f"U tipi: {su['toplam']} raf\n\n"
                   f"✅ Öneri: {en_iyi} tipi ({sonuclar[en_iyi]['toplam']} raf)\n"
                   f"Deponuza en fazla raf bu tipte sigiyor.\n\n"
                   f"Onayliyor musunuz?")
            rows = [[f"✅ {en_iyi} tipini onayla", "🔄 Baska tip sec"]]
        else:
            msg = (f"🤖 РЕКОМЕНДАЦИЯ\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"📊 Сравнение:\n"
                   f"Тип I: {si['toplam']} стелл. ({si['satir']} рядов × {si['perz']} колонн)\n"
                   f"Тип L: {sl['toplam']} стелл.\n"
                   f"Тип U: {su['toplam']} стелл.\n\n"
                   f"✅ Рекомендую: Тип {en_iyi} ({sonuclar[en_iyi]['toplam']} стелл.)\n"
                   f"Максимум стеллажей для вашего склада.\n\n"
                   f"Подтверждаете?")
            rows = [[f"✅ Тип {en_iyi} — подтвердить", "🔄 Выбрать другой"]]

        await update.message.reply_text(msg, reply_markup=kb(rows))
        return ONERI_ONAYLA
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

async def oneri_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    d = context.user_data
    if "baska" in t or "другой" in t or "🔄" in t:
        if lang == 'tr':
            msg = "Hangi tipi istersiniz?\nI — Paralel siralar\nL — Iki duvara bitisik\nU — Uc duvara bitisik"
        else:
            msg = "Какой тип выбрать?\nI — Параллельные ряды\nL — Вдоль двух стен\nU — Вдоль трёх стен"
        await update.message.reply_text(msg, reply_markup=kb([["I","L","U"]]))
        return MANUEL_TIP
    tip = d['en_iyi']
    await _ciz(update, context, lang, tip)
    return ConversationHandler.END

async def manuel_h(update, context):
    lang = get_lang(context)
    t = update.message.text.strip().upper()[0]
    if t not in ['I','L','U']:
        await update.message.reply_text("I, L veya U girin." if lang=='tr' else "I, L или U.")
        return MANUEL_TIP
    await _ciz(update, context, lang, t)
    return ConversationHandler.END

async def _ciz(update, context, lang, tip):
    d = context.user_data
    sonuclar = d.get('sonuclar')
    if not sonuclar:
        _, sonuclar = hesapla_tipler(
            d['uzunluk'], d['genislik'],
            PALET_GENISLIK[d['palet']],
            KORIDOR_GENISLIK[d['koridor_tipi']],
            d.get('kenar_bosluk',0),
            d['giris_duvar'],
            d['giris_bosluk']
        )
    await update.message.reply_text(
        "⏳ Cizim hazirlaniyor..." if lang=='tr' else "⏳ Подготовка чертежа...",
        reply_markup=ReplyKeyboardRemove()
    )
    try:
        resim, toplam, kalan = teknik_ciz(d, lang, tip, sonuclar)
        if lang == 'tr':
            cap = (f"TEKNİK CİZİM — Tip: {tip}\n"
                   f"Depo: {d['uzunluk']}×{d['genislik']}m\n"
                   f"Toplam raf: {toplam} | Kat: {d['kat']} | Yuk: {d['raf_yuk']}m\n"
                   f"{kalan}\nFiyat: /hesapla")
        else:
            cap = (f"ЧЕРТЁЖ — Тип: {tip}\n"
                   f"Склад: {d['uzunluk']}×{d['genislik']}м\n"
                   f"Стеллажей: {toplam} | Ярусов: {d['kat']} | Выс.: {d['raf_yuk']}м\n"
                   f"{kalan}\nРасчёт: /raschet")
        await update.message.reply_photo(photo=resim, caption=cap)
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")

async def iptal(update, context):
    lang = get_lang(context)
    await update.message.reply_text(
        "Iptal. /hesapla yazin." if lang=='tr' else "Отменено. /raschet",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', baslat),
            CommandHandler('hesapla', baslat),
            CommandHandler('raschet', baslat),
        ],
        states={
            LANG:         [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
            UZUNLUK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk_h)],
            GENISLIK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik_h)],
            DEPO_YUK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, depo_yuk_h)],
            GIRIS_DUVAR:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_duvar_h)],
            GIRIS_KONUM:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_konum_h)],
            GIRIS_MESAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_mesafe_h)],
            GIRIS_BOSLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_bosluk_h)],
            KENAR_BOSLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_h)],
            KORIDOR_TIPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_h)],
            PALET:        [MessageHandler(filters.TEXT & ~filters.COMMAND, palet_h)],
            KAT:          [MessageHandler(filters.TEXT & ~filters.COMMAND, kat_h)],
            RAF_YUK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, raf_yuk_h)],
            ONERI_ONAYLA: [MessageHandler(filters.TEXT & ~filters.COMMAND, oneri_h)],
            MANUEL_TIP:   [MessageHandler(filters.TEXT & ~filters.COMMAND, manuel_h)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
