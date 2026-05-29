import os
import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, UZUNLUK, GENISLIK, YUKSEKLIK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_BOSLUK,
 KENAR_BOSLUK, KORIDOR_TIPI, PALET, KAT,
 ONERI_ONAYLA, MANUEL_TIP) = range(14)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def kb(rows):
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)

def hesapla_en_iyi_tip(uzunluk, genislik, raf_g, koridor, kb2, g_duvar, g_bosluk):
    """Her tip için sıra sayısı ve verimlilik hesapla, en iyisini öner."""
    sonuclar = {}

    # Kullanılabilir alan
    if g_duvar in ['alt', 'ust']:
        ef_g = genislik - kb2*2 - g_bosluk
        ef_u = uzunluk - kb2*2
    else:
        ef_g = genislik - kb2*2
        ef_u = uzunluk - kb2*2 - g_bosluk

    # I tipi - paralel siralar
    i_satir = max(1, int(ef_g / (raf_g + koridor)))
    i_perz  = max(1, int(ef_u / 1.1))
    i_toplam = i_satir * i_perz
    i_kullanim = (i_satir * raf_g) / ef_g * 100 if ef_g > 0 else 0
    sonuclar['I'] = {
        'toplam': i_toplam, 'satir': i_satir, 'perz': i_perz,
        'kullanim': i_kullanim, 'kalan_g': ef_g - i_satir*(raf_g+koridor)
    }

    # L tipi - iki duvara bitisik
    sol_adet = max(1, int(ef_g / 1.1))
    alt_adet = max(1, int((ef_u - raf_g - koridor) / 1.1))
    l_toplam = sol_adet + alt_adet
    sonuclar['L'] = {
        'toplam': l_toplam, 'sol_adet': sol_adet, 'alt_adet': alt_adet,
        'kullanim': 75, 'kalan_g': 0
    }

    # U tipi - uc duvara bitisik
    sol_adet_u = max(1, int(ef_g / 1.1))
    sag_adet_u = sol_adet_u
    ara_u = ef_u - raf_g*2 - koridor*2
    alt_adet_u = max(1, int(ara_u / 1.1)) if ara_u > 0 else 0
    u_toplam = sol_adet_u + sag_adet_u + alt_adet_u
    sonuclar['U'] = {
        'toplam': u_toplam, 'sol_adet': sol_adet_u, 'sag_adet': sag_adet_u,
        'alt_adet': alt_adet_u, 'kullanim': 85, 'kalan_g': 0
    }

    # En iyi tip: en fazla raf
    en_iyi = max(sonuclar, key=lambda x: sonuclar[x]['toplam'])
    return en_iyi, sonuclar

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

def teknik_resim_ciz(d, lang, tip, sonuclar):
    uzunluk   = d['uzunluk']
    genislik  = d['genislik']
    raf_g     = PALET_GENISLIK[d['palet']]
    koridor   = KORIDOR_GENISLIK[d['koridor_tipi']]
    kat       = d['kat']
    yukseklik = d['yukseklik']
    kb2       = d.get('kenar_bosluk', 0.0)
    g_duvar   = d.get('giris_duvar', 'alt')
    g_konum   = d.get('giris_konum', 'orta')
    g_mesafe  = d.get('giris_mesafe', 0.0)
    g_bosluk  = d.get('giris_bosluk', 2.0)

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

    INFO_H = 140
    pl, pt, pr, pb = 70, 55, 110, INFO_H + 40
    pw = W - pl - pr
    ph = H - pt - pb
    ox, oy = pl, pt
    sx = pw / uzunluk
    sy = ph / genislik

    # Baslik
    draw.rectangle([0, 0, W, 42], fill='#161b22')
    if lang == 'tr':
        baslik = f"TEKNIK CIZIM  |  Tip: {tip}  |  {uzunluk}x{genislik}m  |  {sonuclar[tip]['toplam']} raf"
    else:
        baslik = f"CHERTEZH  |  Tip: {tip}  |  {uzunluk}x{genislik}m  |  {sonuclar[tip]['toplam']} stell."
    draw.text((W//2, 21), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo - her zaman dikdortgen
    draw.rectangle([ox, oy, ox+pw, oy+ph], outline=SINIR, width=3)
    draw.rectangle([ox+2, oy+2, ox+pw-2, oy+ph-2], outline='#1a3a5c', width=1)

    # Kapı konumu hesapla
    G = 60
    kapi_lbl = "GIRIS/CIKIS" if lang=='tr' else "VHOD/VYHOD"
    if g_duvar in ['alt', 'ust']:
        if g_konum == 'orta': gx = ox + pw // 2
        elif g_konum == 'sol': gx = ox + int(g_mesafe * sx) + G//2
        else: gx = ox + pw - int(g_mesafe * sx) - G//2
    else:
        if g_konum == 'orta': gy = oy + ph // 2
        elif g_konum == 'ust': gy = oy + int(g_mesafe * sy) + G//2
        else: gy = oy + ph - int(g_mesafe * sy) - G//2

    # Yukleme alani (yesil) - kapinin oldugu tarafta
    bp_y = int(g_bosluk * sy)
    bp_x = int(g_bosluk * sx)

    if g_duvar == 'alt':
        draw.rectangle([ox+3, oy+ph-bp_y, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        lbl = "YUKLEME/BOSALTMA" if lang=='tr' else "ZONA POGRUZKI"
        draw.text((ox+pw//2, oy+ph-bp_y//2-7), lbl, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw//2, oy+ph-bp_y//2+9), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')
        draw.line([gx-G//2, oy+ph, gx+G//2, oy+ph], fill=SARI, width=8)
        draw.text((gx, oy+ph+10), kapi_lbl, fill=SARI, font=fsm, anchor='mt')

    elif g_duvar == 'ust':
        draw.rectangle([ox+3, oy+3, ox+pw-3, oy+bp_y], fill='#052e16', outline=YESIL2, width=2)
        lbl = "YUKLEME/BOSALTMA" if lang=='tr' else "ZONA POGRUZKI"
        draw.text((ox+pw//2, oy+bp_y//2-7), lbl, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw//2, oy+bp_y//2+9), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')
        draw.line([gx-G//2, oy, gx+G//2, oy], fill=SARI, width=8)
        draw.text((gx, oy-10), kapi_lbl, fill=SARI, font=fsm, anchor='mb')

    elif g_duvar == 'sol':
        draw.rectangle([ox+3, oy+3, ox+bp_x, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        lbl = "YUKLEME" if lang=='tr' else "ZONA"
        draw.text((ox+bp_x//2, oy+ph//2-7), lbl, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+bp_x//2, oy+ph//2+9), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')
        draw.line([ox, gy-G//2, ox, gy+G//2], fill=SARI, width=8)
        draw.text((ox-8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='rm')

    else:  # sag
        draw.rectangle([ox+pw-bp_x, oy+3, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        lbl = "YUKLEME" if lang=='tr' else "ZONA"
        draw.text((ox+pw-bp_x//2, oy+ph//2-7), lbl, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw-bp_x//2, oy+ph//2+9), f"{g_bosluk}m", fill=YESIL2, font=fb, anchor='mm')
        draw.line([ox+pw, gy-G//2, ox+pw, gy+G//2], fill=SARI, width=8)
        draw.text((ox+pw+8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='lm')

    # Kapidan mesafe goster
    if g_mesafe > 0 and g_konum != 'orta':
        if g_duvar in ['alt', 'ust']:
            ex = oy+ph+28 if g_duvar=='alt' else oy-28
            if g_konum == 'sol':
                draw.line([ox, ex, gx-G//2, ex], fill=AGRI, width=1)
                draw.text(((ox+gx-G//2)//2, ex-3), f"{g_mesafe}m", fill=BEYAZ, font=fsm, anchor='mb')
            else:
                draw.line([gx+G//2, ex, ox+pw, ex], fill=AGRI, width=1)
                draw.text(((gx+G//2+ox+pw)//2, ex-3), f"{g_mesafe}m", fill=BEYAZ, font=fsm, anchor='mb')

    # RAF ALANI - kapinin KARSISINDA
    raf_x1 = ox + int(kb2 * sx)
    raf_y1 = oy + int(kb2 * sy)
    raf_x2 = ox + pw - int(kb2 * sx)
    raf_y2 = oy + ph - int(kb2 * sy)

    # Kapinin karsi tarafina raflar - yukleme alani kapinin yaninda kalsin
    if g_duvar == 'alt':
        raf_y2 -= bp_y   # alt yuklemeden uzak - raflar uste
    elif g_duvar == 'ust':
        raf_y1 += bp_y   # ust yuklemeden uzak - raflar alta
    elif g_duvar == 'sol':
        raf_x1 += bp_x   # sol yuklemeden uzak - raflar saga
    else:
        raf_x2 -= bp_x   # sag yuklemeden uzak - raflar sola

    raf_aw = raf_x2 - raf_x1
    raf_ah = raf_y2 - raf_y1
    ef_u = raf_aw / sx
    ef_g = raf_ah / sy

    raflar = []
    kalan_bilgi = ""

    if tip == 'I':
        raf_satir = max(1, int(ef_g / (raf_g + koridor)))
        raf_perz  = max(1, int(ef_u / 1.1))

        # Raflar kapinin KARSISINDA baslasin
        if g_duvar == 'alt':
            # Raflar yukari taraftan baslar
            for row in range(raf_satir):
                ry1 = raf_y1 + int((raf_g/2 + row*(raf_g+koridor)) * sy)
                ry2 = max(ry1 + int(raf_g * sy), ry1 + 14)
                for col in range(raf_perz):
                    rx1 = raf_x1 + int(col * 1.1 * sx) + 1
                    rx2 = max(raf_x1 + int((col+1)*1.1*sx)-1, rx1+8)
                    raflar.append((rx1, ry1, rx2, ry2, row))
        else:
            for row in range(raf_satir):
                ry1 = raf_y1 + int((raf_g/2 + row*(raf_g+koridor)) * sy)
                ry2 = max(ry1 + int(raf_g * sy), ry1 + 14)
                for col in range(raf_perz):
                    rx1 = raf_x1 + int(col * 1.1 * sx) + 1
                    rx2 = max(raf_x1 + int((col+1)*1.1*sx)-1, rx1+8)
                    raflar.append((rx1, ry1, rx2, ry2, row))

        kalan_g = ef_g - raf_satir*(raf_g+koridor)
        ek_sir = int(kalan_g / (raf_g + koridor))
        if lang == 'tr':
            kalan_bilgi = f"Kalan alan: {kalan_g:.1f}m"
            if ek_sir > 0:
                kalan_bilgi += f" ({ek_sir} sira daha sigabilir!)"
        else:
            kalan_bilgi = f"Остаток: {kalan_g:.1f}м"
            if ek_sir > 0:
                kalan_bilgi += f" (ещё {ek_sir} ряд(а) поместится!)"

        # Raf etiketleri
        satir_ry = {}
        for (rx1, ry1, rx2, ry2, row) in raflar:
            if row not in satir_ry: satir_ry[row] = (ry1, ry2)
        for i, row in enumerate(sorted(satir_ry.keys())):
            ry1v, ry2v = satir_ry[row]
            draw.text((ox+pw+6, (ry1v+ry2v)//2), f"R{row+1}", fill=BEYAZ, font=fn, anchor='lm')
            if i > 0:
                prev = sorted(satir_ry.keys())[i-1]
                prev_ry2 = satir_ry[prev][1]
                ky = (prev_ry2 + ry1v) // 2
                draw.text((ox+pw+6, ky), f"{koridor}m", fill=MOR, font=fsm, anchor='lm')

    elif tip == 'L':
        raf_dp_x = int(raf_g * sx)
        raf_dp_y = int(raf_g * sy)

        # Kapinin karsisina gore L yonu belirle
        if g_duvar == 'alt':
            # Sol + ust duvara bitisik
            sol_x1, sol_x2 = raf_x1, raf_x1 + raf_dp_x
            n_sol = max(1, int(ef_g / 1.1))
            for i in range(n_sol):
                ry1 = raf_y1 + int(i * 1.1 * sy)
                ry2 = max(ry1 + int(0.9*sy), ry1+8)
                if ry2 > raf_y2: break
                raflar.append((sol_x1, ry1, sol_x2, ry2, i))
            ust_y1, ust_y2 = raf_y1, raf_y1 + raf_dp_y
            bas_x = sol_x2 + int(koridor * sx)
            n_ust = max(1, int((raf_x2 - bas_x) / (1.1*sx)))
            for i in range(n_ust):
                rx1 = bas_x + int(i * 1.1 * sx)
                rx2 = max(rx1 + int(0.9*sx), rx1+8)
                if rx2 > raf_x2: break
                raflar.append((rx1, ust_y1, rx2, ust_y2, i+100))
        else:
            # Sol + alt duvara bitisik
            sol_x1, sol_x2 = raf_x1, raf_x1 + raf_dp_x
            n_sol = max(1, int(ef_g / 1.1))
            for i in range(n_sol):
                ry1 = raf_y1 + int(i * 1.1 * sy)
                ry2 = max(ry1 + int(0.9*sy), ry1+8)
                if ry2 > raf_y2: break
                raflar.append((sol_x1, ry1, sol_x2, ry2, i))
            alt_y1, alt_y2 = raf_y2 - raf_dp_y, raf_y2
            bas_x = sol_x2 + int(koridor * sx)
            n_alt = max(1, int((raf_x2 - bas_x) / (1.1*sx)))
            for i in range(n_alt):
                rx1 = bas_x + int(i * 1.1 * sx)
                rx2 = max(rx1 + int(0.9*sx), rx1+8)
                if rx2 > raf_x2: break
                raflar.append((rx1, alt_y1, rx2, alt_y2, i+100))

        kalan_bilgi = f"{len(raflar)} raf" if lang=='tr' else f"{len(raflar)} stell."

    elif tip == 'U':
        raf_dp_x = int(raf_g * sx)
        raf_dp_y = int(raf_g * sy)

        # Sol duvara bitisik
        sol_x1, sol_x2 = raf_x1, raf_x1 + raf_dp_x
        # Sag duvara bitisik
        sag_x1, sag_x2 = raf_x2 - raf_dp_x, raf_x2

        if g_duvar == 'alt':
            # Ust duvara bitisik (kapi karsisi)
            ust_y1, ust_y2 = raf_y1, raf_y1 + raf_dp_y
            bas_x = sol_x2 + int(koridor * sx)
            bit_x = sag_x1 - int(koridor * sx)
            n_ust = max(1, int((bit_x - bas_x) / (1.1*sx)))
            for i in range(n_ust):
                rx1 = bas_x + int(i * 1.1 * sx)
                rx2 = max(rx1 + int(0.9*sx), rx1+8)
                if rx2 > bit_x: break
                raflar.append((rx1, ust_y1, rx2, ust_y2, i+200))
        else:
            # Alt duvara bitisik (kapi karsisi)
            alt_y1, alt_y2 = raf_y2 - raf_dp_y, raf_y2
            bas_x = sol_x2 + int(koridor * sx)
            bit_x = sag_x1 - int(koridor * sx)
            n_alt = max(1, int((bit_x - bas_x) / (1.1*sx)))
            for i in range(n_alt):
                rx1 = bas_x + int(i * 1.1 * sx)
                rx2 = max(rx1 + int(0.9*sx), rx1+8)
                if rx2 > bit_x: break
                raflar.append((rx1, alt_y1, rx2, alt_y2, i+200))

        # Sol ve sag duvara her zaman bitisik
        ef_g_yan = ef_g
        n_yan = max(1, int(ef_g_yan / 1.1))
        for i in range(n_yan):
            ry1 = raf_y1 + int(i * 1.1 * sy)
            ry2 = max(ry1 + int(0.9*sy), ry1+8)
            if ry2 > raf_y2: break
            raflar.append((sol_x1, ry1, sol_x2, ry2, i))
            raflar.append((sag_x1, ry1, sag_x2, ry2, i+100))

        kalan_bilgi = f"{len(raflar)} raf" if lang=='tr' else f"{len(raflar)} stell."

    # Raflari ciz
    for r in raflar:
        ciz_raf(draw, r[0], r[1], r[2], r[3], TURUNCU, YESIL, MAVI, GRI)

    toplam_raf = len(raflar)

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
            (MAVI,    "● Dikme",          f"{yukseklik} m"),
            (TURUNCU, "━ Yatay Baglanti", f"{raf_g} m"),
            (YESIL,   "| Derinlik",        "1.10 m"),
            (MOR,     "↔ Koridor",         f"{koridor} m"),
            (YESIL2,  "▦ Yukleme Alani",   f"{g_bosluk} m"),
        ]
    else:
        items = [
            (MAVI,    "● Stoyka",          f"{yukseklik} m"),
            (TURUNCU, "━ Balka",           f"{raf_g} m"),
            (YESIL,   "| Glubina",          "1.10 m"),
            (MOR,     "↔ Prokhod",          f"{koridor} m"),
            (YESIL2,  "▦ Zona Pogruzki",    f"{g_bosluk} m"),
        ]
    for renk, isim, olcu in items:
        draw.text((lx, ly), isim, fill=renk, font=fb)
        draw.text((lx+220, ly), olcu, fill=BEYAZ, font=fb)
        ly += 25

    rx2b, ry2b = W//2 + 20, iy + 14
    if lang == 'tr':
        bilgiler = [
            ("Kat",          str(kat)),
            ("Toplam Raf",   str(toplam_raf)),
            ("Raf Tipi",     tip),
            ("Kenar Bosluk", f"{kb2} m"),
            ("Durum",        kalan_bilgi),
        ]
    else:
        bilgiler = [
            ("Yarusov",      str(kat)),
            ("Vsego stell.", str(toplam_raf)),
            ("Tip",          tip),
            ("Otstup",       f"{kb2} m"),
            ("Status",       kalan_bilgi),
        ]
    for k, v in bilgiler:
        draw.text((rx2b, ry2b), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx2b+185, ry2b), v, fill=BEYAZ, font=fb)
        ry2b += 25

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150, 150))
    buf.seek(0)
    return buf, toplam_raf, kalan_bilgi

# --- HANDLERS ---

async def start(update, context):
    await update.message.reply_text(
        "Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce", "🇷🇺 Russkiy"]])
    )
    return LANG

async def hesapla(update, context):
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
    msg = ("📏 Depo uzunlugu (metre):\nOrnek: 20"
           if lang=='tr' else
           "📏 Длина склада (метры):\nПример: 20")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['uzunluk'] = float(update.message.text.replace(',', '.'))
        msg = ("📐 Depo genisligi (metre):\nOrnek: 12"
               if lang=='tr' else
               "📐 Ширина склада (метры):\nПример: 12")
        await update.message.reply_text(msg)
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 20" if lang=='tr' else "Только цифры. Пример: 20")
        return UZUNLUK

async def genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',', '.'))
        msg = ("📏 Depo yuksekligi (metre):\nOrnek: 6"
               if lang=='tr' else
               "📏 Высота склада (метры):\nПример: 6")
        await update.message.reply_text(msg)
        return YUKSEKLIK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 12" if lang=='tr' else "Только цифры. Пример: 12")
        return GENISLIK

async def yukseklik_depo_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['depo_yukseklik'] = float(update.message.text.replace(',', '.'))
        if lang == 'tr':
            msg = "🚪 Giris kapisi hangi duvarda?"
            rows = [["Alt duvar", "Ust duvar"], ["Sol duvar", "Sag duvar"]]
        else:
            msg = "🚪 На какой стене находится вход?"
            rows = [["Нижняя стена", "Верхняя стена"], ["Левая стена", "Правая стена"]]
        await update.message.reply_text(msg, reply_markup=kb(rows))
        return GIRIS_DUVAR
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 6" if lang=='tr' else "Только цифры. Пример: 6")
        return YUKSEKLIK

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
        msg = ("🏗 Giris onunde yukleme/bosaltma alani kac metre?\nOrnek: 3"
               if lang=='tr' else
               "🏗 Зона погрузки/разгрузки перед входом (м)?\nПример: 3")
        await update.message.reply_text(msg, reply_markup=kb([["2", "3", "4", "5"]]))
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
        msg = ("🏗 Giris onunde yukleme/bosaltma alani kac metre?\nOrnek: 3"
               if lang=='tr' else
               "🏗 Зона погрузки/разгрузки перед входом (м)?\nПример: 3")
        await update.message.reply_text(msg, reply_markup=kb([["2", "3", "4", "5"]]))
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
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_BOSLUK

async def kenar_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kenar_bosluk'] = float(update.message.text.replace(',', '.'))
        if lang == 'tr':
            msg = "🚦 Koridor tipi?\nForklift — 3.0m\nTranspalet — 2.0m\nEl ile — 1.2m"
        else:
            msg = "🚦 Тип прохода?\nПогрузчик — 3.0м\nТранспалет — 2.0м\nРучной — 1.2м"
        await update.message.reply_text(msg, reply_markup=kb([
            ["Forklift", "Transpalet", "El ile" if lang=='tr' else "Ruchnoy"]
        ]))
        return KORIDOR_TIPI
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return KENAR_BOSLUK

async def koridor_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "forklift" in t or "погрузчик" in t: context.user_data['koridor_tipi'] = 'forklift'
    elif "transpalet" in t or "транспалет" in t: context.user_data['koridor_tipi'] = 'transpalet'
    else: context.user_data['koridor_tipi'] = 'el'
    if lang == 'tr':
        msg = "📦 Raf basina palet sayisi?\n1 — 0.95m\n2 — 1.85m\n3 — 2.70m\n4 — 3.60m"
    else:
        msg = "📦 Количество паллет на ряд?\n1 — 0.95м\n2 — 1.85м\n3 — 2.70м\n4 — 3.60м"
    await update.message.reply_text(msg, reply_markup=kb([["1", "2"], ["3", "4"]]))
    return PALET

async def palet_h(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text.strip()[0])
        if v not in [1, 2, 3, 4]: raise ValueError
        context.user_data['palet'] = v
        msg = "🏗 Raf kat sayisi?\nOrnek: 3" if lang=='tr' else "🏗 Количество ярусов?\nПример: 3"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1, 2, 3 veya 4 girin." if lang=='tr' else "Введите 1, 2, 3 или 4.")
        return PALET

async def kat_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kat'] = int(update.message.text)
        msg = "📏 Raf yuksekligi (metre)?\nOrnek: 5" if lang=='tr' else "📏 Высота стеллажа (м)?\nПример: 5"
        await update.message.reply_text(msg)
        return YUKSEKLIK
    except:
        await update.message.reply_text("Sadece rakam. Ornek: 3" if lang=='tr' else "Только цифры. Пример: 3")
        return KAT

async def raf_yukseklik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['yukseklik'] = float(update.message.text.replace(',', '.'))
        d = context.user_data

        # En iyi tipi hesapla
        en_iyi, sonuclar = hesapla_en_iyi_tip(
            d['uzunluk'], d['genislik'],
            PALET_GENISLIK[d['palet']],
            KORIDOR_GENISLIK[d['koridor_tipi']],
            d.get('kenar_bosluk', 0),
            d['giris_duvar'],
            d['giris_bosluk']
        )
        context.user_data['sonuclar'] = sonuclar
        context.user_data['en_iyi_tip'] = en_iyi

        s = sonuclar[en_iyi]
        if lang == 'tr':
            msg = (f"🤖 SISTEM ONERİSİ\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"En uygun raf tipi: {en_iyi}\n\n"
                   f"I tipi: {sonuclar['I']['toplam']} raf ({sonuclar['I']['satir']} sira x {sonuclar['I']['perz']} sutun)\n"
                   f"L tipi: {sonuclar['L']['toplam']} raf\n"
                   f"U tipi: {sonuclar['U']['toplam']} raf\n\n"
                   f"Onerim: {en_iyi} tipi en fazla raf sigiyor.\n"
                   f"Onayliyor musunuz?")
            rows = [[f"✅ {en_iyi} tipini onayla", "🔄 Baska tip sec"]]
        else:
            msg = (f"🤖 РЕКОМЕНДАЦИЯ СИСТЕМЫ\n"
                   f"━━━━━━━━━━━━━━━━\n"
                   f"Оптимальный тип: {en_iyi}\n\n"
                   f"Тип I: {sonuclar['I']['toplam']} стелл. ({sonuclar['I']['satir']} рядов x {sonuclar['I']['perz']} колонн)\n"
                   f"Тип L: {sonuclar['L']['toplam']} стелл.\n"
                   f"Тип U: {sonuclar['U']['toplam']} стелл.\n\n"
                   f"Рекомендую тип {en_iyi} — максимум стеллажей.\n"
                   f"Подтверждаете?")
            rows = [[f"✅ Тип {en_iyi} — подтвердить", "🔄 Выбрать другой"]]

        await update.message.reply_text(msg, reply_markup=kb(rows))
        return ONERI_ONAYLA
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return YUKSEKLIK

async def oneri_onayla_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    d = context.user_data

    if "baska" in t or "другой" in t or "🔄" in t:
        if lang == 'tr':
            msg = "Hangi tipi tercih edersiniz?\nI — Paralel siralar\nL — Iki duvara bitisik\nU — Uc duvara bitisik"
        else:
            msg = "Какой тип предпочитаете?\nI — Параллельные ряды\nL — Вдоль двух стен\nU — Вдоль трёх стен"
        await update.message.reply_text(msg, reply_markup=kb([["I", "L", "U"]]))
        return MANUEL_TIP

    # Onaylandi
    tip = d['en_iyi_tip']
    await _cizim_yap(update, context, lang, tip)
    return ConversationHandler.END

async def manuel_tip_h(update, context):
    lang = get_lang(context)
    t = update.message.text.strip().upper()[0]
    if t not in ['I', 'L', 'U']:
        await update.message.reply_text("I, L veya U girin." if lang=='tr' else "I, L или U.")
        return MANUEL_TIP
    await _cizim_yap(update, context, lang, t)
    return ConversationHandler.END

async def _cizim_yap(update, context, lang, tip):
    d = context.user_data
    sonuclar = d.get('sonuclar', {})
    if not sonuclar:
        _, sonuclar = hesapla_en_iyi_tip(
            d['uzunluk'], d['genislik'],
            PALET_GENISLIK[d['palet']],
            KORIDOR_GENISLIK[d['koridor_tipi']],
            d.get('kenar_bosluk', 0),
            d['giris_duvar'],
            d['giris_bosluk']
        )

    await update.message.reply_text(
        "⏳ Teknik cizim hazirlaniyor..." if lang=='tr' else "⏳ Подготовка чертежа...",
        reply_markup=ReplyKeyboardRemove()
    )
    try:
        resim, toplam, kalan = teknik_resim_ciz(d, lang, tip, sonuclar)
        if lang == 'tr':
            cap = (f"TEKNIK CIZIM — Tip: {tip}\n"
                   f"Depo: {d['uzunluk']}x{d['genislik']}m\n"
                   f"Toplam raf: {toplam} adet | Kat: {d['kat']}\n"
                   f"Yukseklik: {d['yukseklik']}m | {kalan}\n"
                   f"Fiyat icin: /hesapla")
        else:
            cap = (f"CHERTEZH — Tip: {tip}\n"
                   f"Sklad: {d['uzunluk']}x{d['genislik']}m\n"
                   f"Stell.: {toplam} sht | Yarusov: {d['kat']}\n"
                   f"Vysota: {d['yukseklik']}m | {kalan}\n"
                   f"Raschet: /raschet")
        await update.message.reply_photo(photo=resim, caption=cap)
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")

async def iptal(update, context):
    lang = get_lang(context)
    await update.message.reply_text(
        "Iptal. /hesapla ile baslayin." if lang=='tr' else "Отменено. /raschet",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[
            CommandHandler('start', hesapla),
            CommandHandler('hesapla', hesapla),
            CommandHandler('raschet', hesapla),
        ],
        states={
            LANG:          [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
            UZUNLUK:       [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk_h)],
            GENISLIK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik_h)],
            YUKSEKLIK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, yukseklik_depo_h)],
            GIRIS_DUVAR:   [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_duvar_h)],
            GIRIS_KONUM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_konum_h)],
            GIRIS_MESAFE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_mesafe_h)],
            GIRIS_BOSLUK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_bosluk_h)],
            KENAR_BOSLUK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_h)],
            KORIDOR_TIPI:  [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_tipi_sec)],
            PALET:         [MessageHandler(filters.TEXT & ~filters.COMMAND, palet_h)],
            KAT:           [MessageHandler(filters.TEXT & ~filters.COMMAND, kat_h)],
            ONERI_ONAYLA:  [MessageHandler(filters.TEXT & ~filters.COMMAND, oneri_onayla_h)],
            MANUEL_TIP:    [MessageHandler(filters.TEXT & ~filters.COMMAND, manuel_tip_h)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
