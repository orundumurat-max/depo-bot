import os
import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, UZUNLUK, GENISLIK, DEPO_YUK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_GENISLIK, GIRIS_BOSLUK,
 KENAR_BOSLUK, KORIDOR_TIPI, PALET, KAT, RAF_YUK,
 SECENEK_SEC) = range(15)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def kb(rows):
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)

def hesapla_secenek(tip, uzunluk, genislik, raf_g, koridor, kb2, g_duvar, g_bosluk):
    """Her tip için raf sayısı hesapla."""
    if g_duvar in ['alt', 'ust']:
        ef_g = genislik - kb2*2 - g_bosluk
        ef_u = uzunluk - kb2*2
    else:
        ef_g = genislik - kb2*2
        ef_u = uzunluk - kb2*2 - g_bosluk
    ef_g = max(ef_g, 0.1)
    ef_u = max(ef_u, 0.1)

    if tip == 'I_paralel':
        # Klasik paralel siralar
        satir = max(1, int(ef_g / (raf_g + koridor)))
        perz  = max(1, int(ef_u / 1.1))
        toplam = satir * perz
        kalan = ef_g - satir*(raf_g+koridor)
        return {'toplam': toplam, 'satir': satir, 'perz': perz, 'kalan': round(kalan,2), 'tip': 'I_paralel'}

    elif tip == 'I_sirt':
        # Ortada cift sira sirt sirta + kenarlarda tek sira
        if ef_g >= raf_g*4 + koridor*3:
            orta_satir = 2
            kenar_satir = max(0, int((ef_g - 2*raf_g - koridor) / (raf_g + koridor))) - 2
            kenar_satir = max(0, kenar_satir)
        else:
            orta_satir = 2
            kenar_satir = 0
        satir = orta_satir + kenar_satir
        satir = max(1, satir)
        perz = max(1, int(ef_u / 1.1))
        toplam = satir * perz
        kalan = ef_g - satir*(raf_g+koridor)
        return {'toplam': toplam, 'satir': satir, 'perz': perz, 'kalan': round(kalan,2), 'tip': 'I_sirt'}

    elif tip == 'L':
        sol = max(1, int(ef_g / 1.1))
        alt = max(1, int((ef_u - raf_g - koridor) / 1.1))
        toplam = sol + alt
        return {'toplam': toplam, 'sol': sol, 'alt': alt, 'tip': 'L'}

    elif tip == 'U':
        sol = max(1, int(ef_g / 1.1))
        sag = sol
        ara = ef_u - raf_g*2 - koridor*2
        alt = max(0, int(ara / 1.1)) if ara > 0 else 0
        toplam = sol + sag + alt
        return {'toplam': toplam, 'sol': sol, 'sag': sag, 'alt': alt, 'tip': 'U'}

    elif tip == 'U_orta':
        # U + ortada ek siralar
        sol = max(1, int(ef_g / 1.1))
        sag = sol
        ara = ef_u - raf_g*2 - koridor*2
        alt = max(0, int(ara / 1.1)) if ara > 0 else 0
        # Ortada ek sira
        ic_alan_g = ef_g - raf_g*2 - koridor*2
        ic_alan_u = ara
        ek_satir = max(0, int(ic_alan_g / (PALET_GENISLIK[2] + KORIDOR_GENISLIK['transpalet'])))
        ek_perz  = max(0, int(ic_alan_u / 1.1))
        toplam = sol + sag + alt + (ek_satir * ek_perz)
        return {'toplam': toplam, 'sol': sol, 'sag': sag, 'alt': alt,
                'ek_satir': ek_satir, 'ek_perz': ek_perz, 'tip': 'U_orta'}
    return {'toplam': 0, 'tip': tip}

def ciz_raf(draw, rx1, ry1, rx2, ry2):
    draw.rectangle([rx1, ry1, rx2, ry2], fill='#0a1628')
    draw.line([rx1, ry1, rx2, ry2], fill='#2a2a40', width=1)
    draw.line([rx2, ry1, rx1, ry2], fill='#2a2a40', width=1)
    draw.rectangle([rx1, ry1, rx2, ry2], outline='#404060', width=1)
    draw.line([rx1+4, ry1, rx2-4, ry1], fill='#ff8c42', width=3)
    draw.line([rx1+4, ry2, rx2-4, ry2], fill='#ff8c42', width=3)
    draw.line([rx1, ry1+4, rx1, ry2-4], fill='#4ade80', width=2)
    draw.line([rx2, ry1+4, rx2, ry2-4], fill='#4ade80', width=2)
    r = 4
    for px, py in [(rx1,ry1),(rx2,ry1),(rx1,ry2),(rx2,ry2)]:
        draw.ellipse([px-r,py-r,px+r,py+r], fill='#4a9eff', outline='white', width=1)

def olcu_ciz(draw, x1, y1, x2, y2, metin, font, BEYAZ, AGRI, dikey=False):
    """Ok ile olcu goster."""
    if dikey:
        cx = (x1+x2)//2
        draw.line([cx, y1, cx, y2], fill=AGRI, width=1)
        draw.line([cx-5, y1, cx+5, y1], fill=AGRI, width=2)
        draw.line([cx-5, y2, cx+5, y2], fill=AGRI, width=2)
        draw.text((cx+6, (y1+y2)//2), metin, fill=BEYAZ, font=font, anchor='lm')
    else:
        cy = (y1+y2)//2
        draw.line([x1, cy, x2, cy], fill=AGRI, width=1)
        draw.line([x1, cy-5, x1, cy+5], fill=AGRI, width=2)
        draw.line([x2, cy-5, x2, cy+5], fill=AGRI, width=2)
        draw.text(((x1+x2)//2, cy-6), metin, fill=BEYAZ, font=font, anchor='mb')

def teknik_ciz(d, lang, sec):
    uzunluk   = d['uzunluk']
    genislik  = d['genislik']
    raf_g     = PALET_GENISLIK[d['palet']]
    koridor   = KORIDOR_GENISLIK[d['koridor_tipi']]
    kat       = d['kat']
    raf_yuk   = d['raf_yuk']
    kb2       = d.get('kenar_bosluk', 0.0)
    g_duvar   = d.get('giris_duvar', 'alt')
    g_konum   = d.get('giris_konum', 'orta')
    g_mesafe  = d.get('giris_mesafe', 0.0)
    g_bosluk  = d.get('giris_bosluk', 2.0)
    g_genislik= d.get('giris_genislik', 3.0)
    tip       = sec['tip']

    W, H = 1150, 900
    img  = Image.new('RGB', (W, H), '#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        fn  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        ft  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
        fsm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        fb = fn = ft = fsm = ImageFont.load_default()

    BEYAZ  = '#e8e8e8'
    AGRI   = '#606080'
    SARI   = '#ffd700'
    SINIR  = '#00b4d8'
    MOR    = '#c084fc'
    YESIL2 = '#22c55e'
    KIRMIZI= '#ff5555'

    INFO_H = 130
    pl, pt, pr, pb = 80, 58, 120, INFO_H + 45
    pw = W - pl - pr
    ph = H - pt - pb
    ox, oy = pl, pt
    sx = pw / uzunluk
    sy = ph / genislik

    # Baslik
    draw.rectangle([0, 0, W, 42], fill='#161b22')
    tip_adi = {'I_paralel': 'I-Paralel', 'I_sirt': 'I-Sirt Sirta', 'L': 'L-Tip', 'U': 'U-Tip', 'U_orta': 'U+Orta'}
    if lang == 'tr':
        baslik = f"TEKNIK CIZIM | {tip_adi.get(tip,tip)} | {uzunluk}×{genislik}m | {sec['toplam']} raf"
    else:
        baslik = f"CHERTEZH | {tip_adi.get(tip,tip)} | {uzunluk}×{genislik}m | {sec['toplam']} stell."
    draw.text((W//2, 21), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo siniri
    draw.rectangle([ox, oy, ox+pw, oy+ph], outline=SINIR, width=3)
    draw.rectangle([ox+2, oy+2, ox+pw-2, oy+ph-2], outline='#1a3a5c', width=1)

    # Kapi konumu
    G = int(g_genislik * sx)
    G = max(G, 30)
    kapi_lbl = "G/C" if lang=='tr' else "V/V"
    if g_duvar in ['alt','ust']:
        if g_konum == 'orta': gx = ox + pw//2
        elif g_konum == 'sol': gx = ox + int(g_mesafe*sx) + G//2
        else: gx = ox + pw - int(g_mesafe*sx) - G//2
    else:
        if g_konum == 'orta': gy = oy + ph//2
        elif g_konum == 'ust': gy = oy + int(g_mesafe*sy) + G//2
        else: gy = oy + ph - int(g_mesafe*sy) - G//2

    # Yukleme alani
    bp_y = int(g_bosluk * sy)
    bp_x = int(g_bosluk * sx)
    zona = "YUKLEME/BOSALTMA" if lang=='tr' else "ZONA POGRUZKI"

    if g_duvar == 'alt':
        draw.rectangle([ox+3, oy+ph-bp_y, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw//2, oy+ph-bp_y//2), zona, fill=YESIL2, font=fsm, anchor='mm')
        # Yukleme alani olculeri
        olcu_ciz(draw, ox+3, oy+ph-bp_y-18, ox+pw-3, oy+ph-bp_y-18, f"{uzunluk}m", fsm, YESIL2, YESIL2)
        olcu_ciz(draw, ox+pw+5, oy+ph-bp_y, ox+pw+5, oy+ph, f"{g_bosluk}m", fsm, YESIL2, YESIL2, dikey=True)
        # Kapi
        draw.line([gx-G//2, oy+ph, gx+G//2, oy+ph], fill=SARI, width=8)
        draw.text((gx, oy+ph+8), kapi_lbl, fill=SARI, font=fsm, anchor='mt')
        # Kapi olcusu
        olcu_ciz(draw, gx-G//2, oy+ph+22, gx+G//2, oy+ph+22, f"{g_genislik}m", fsm, SARI, SARI)
        # Kapinin duvara mesafesi
        if g_konum == 'sol' and g_mesafe > 0:
            olcu_ciz(draw, ox, oy+ph+38, gx-G//2, oy+ph+38, f"{g_mesafe}m", fsm, BEYAZ, AGRI)
        elif g_konum == 'sag' and g_mesafe > 0:
            olcu_ciz(draw, gx+G//2, oy+ph+38, ox+pw, oy+ph+38, f"{g_mesafe}m", fsm, BEYAZ, AGRI)

    elif g_duvar == 'ust':
        draw.rectangle([ox+3, oy+3, ox+pw-3, oy+bp_y], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw//2, oy+bp_y//2), zona, fill=YESIL2, font=fsm, anchor='mm')
        olcu_ciz(draw, ox+pw+5, oy, ox+pw+5, oy+bp_y, f"{g_bosluk}m", fsm, YESIL2, YESIL2, dikey=True)
        draw.line([gx-G//2, oy, gx+G//2, oy], fill=SARI, width=8)
        draw.text((gx, oy-8), kapi_lbl, fill=SARI, font=fsm, anchor='mb')
        olcu_ciz(draw, gx-G//2, oy-22, gx+G//2, oy-22, f"{g_genislik}m", fsm, SARI, SARI)

    elif g_duvar == 'sol':
        draw.rectangle([ox+3, oy+3, ox+bp_x, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+bp_x//2, oy+ph//2), zona, fill=YESIL2, font=fsm, anchor='mm')
        olcu_ciz(draw, ox, oy+ph+5, ox+bp_x, oy+ph+5, f"{g_bosluk}m", fsm, YESIL2, YESIL2)
        draw.line([ox, gy-G//2, ox, gy+G//2], fill=SARI, width=8)
        draw.text((ox-8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='rm')
        olcu_ciz(draw, ox-35, gy-G//2, ox-35, gy+G//2, f"{g_genislik}m", fsm, SARI, SARI, dikey=True)

    else:
        draw.rectangle([ox+pw-bp_x, oy+3, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw-bp_x//2, oy+ph//2), zona, fill=YESIL2, font=fsm, anchor='mm')
        olcu_ciz(draw, ox+pw-bp_x, oy+ph+5, ox+pw, oy+ph+5, f"{g_bosluk}m", fsm, YESIL2, YESIL2)
        draw.line([ox+pw, gy-G//2, ox+pw, gy+G//2], fill=SARI, width=8)
        draw.text((ox+pw+8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='lm')
        olcu_ciz(draw, ox+pw+20, gy-G//2, ox+pw+20, gy+G//2, f"{g_genislik}m", fsm, SARI, SARI, dikey=True)

    # RAF ALANI
    rx1 = ox + int(kb2*sx)
    ry1 = oy + int(kb2*sy)
    rx2 = ox + pw - int(kb2*sx)
    ry2 = oy + ph - int(kb2*sy)
    if g_duvar == 'alt':   ry2 -= bp_y
    elif g_duvar == 'ust': ry1 += bp_y
    elif g_duvar == 'sol': rx1 += bp_x
    else:                  rx2 -= bp_x

    aw = rx2-rx1
    ah = ry2-ry1

    raflar = []

    if tip in ['I_paralel','I_sirt']:
        n_s = sec['satir']
        n_p = sec['perz']
        for row in range(n_s):
            rry1 = ry1 + int((raf_g/2 + row*(raf_g+koridor))*sy)
            rry2 = max(rry1+int(raf_g*sy), rry1+14)
            for col in range(n_p):
                rrx1 = rx1+int(col*1.1*sx)+1
                rrx2 = max(rx1+int((col+1)*1.1*sx)-1, rrx1+8)
                raflar.append((rrx1, rry1, rrx2, rry2, row))
        # Koridor olculeri - satirlar arasi
        satir_ry = {}
        for (a,b,c,d2,row) in raflar:
            if row not in satir_ry: satir_ry[row] = (b,d2)
        for i,row in enumerate(sorted(satir_ry.keys())):
            b,d2 = satir_ry[row]
            draw.text((ox+pw+5,(b+d2)//2), f"R{row+1}", fill=BEYAZ, font=fsm, anchor='lm')
            # Yatay baglanti olcusu (ilk satirda)
            if row == 0 and n_p > 0:
                rrx1 = rx1+1
                rrx2 = max(rx1+int(1.1*sx)-1, rrx1+8)
                olcu_ciz(draw, rrx1, b-16, rrx2, b-16, f"{raf_g}m", fsm, MOR, MOR)
            if i > 0:
                prev = sorted(satir_ry.keys())[i-1]
                prev_d2 = satir_ry[prev][1]
                ky = (prev_d2+b)//2
                # Koridor olcusu
                olcu_ciz(draw, ox+pw+5, prev_d2, ox+pw+5, b, f"{koridor}m", fsm, MOR, MOR, dikey=True)

    elif tip == 'L':
        dp_x = int(raf_g*sx)
        dp_y = int(raf_g*sy)
        n_sol = sec['sol']
        n_alt = sec['alt']
        for i in range(n_sol):
            rry1 = ry1+int(i*1.1*sy)
            rry2 = max(rry1+int(0.9*sy), rry1+8)
            if rry2 > ry2: break
            raflar.append((rx1, rry1, rx1+dp_x, rry2, i))
        bas_x = rx1+dp_x+int(koridor*sx)
        if g_duvar == 'alt':
            for i in range(n_alt):
                rrx1 = bas_x+int(i*1.1*sx)
                rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                if rrx2 > rx2: break
                raflar.append((rrx1, ry1, rrx2, ry1+dp_y, i+100))
            # Yatay baglanti olcusu
            if n_alt > 0:
                olcu_ciz(draw, bas_x, ry1-16, bas_x+int(0.9*sx), ry1-16, f"{raf_g}m", fsm, MOR, MOR)
        else:
            for i in range(n_alt):
                rrx1 = bas_x+int(i*1.1*sx)
                rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                if rrx2 > rx2: break
                raflar.append((rrx1, ry2-dp_y, rrx2, ry2, i+100))
        # Sol raf yatay baglanti olcusu
        olcu_ciz(draw, rx1, ry1-16, rx1+dp_x, ry1-16, f"{raf_g}m", fsm, MOR, MOR)

    elif tip in ['U','U_orta']:
        dp_x = int(raf_g*sx)
        dp_y = int(raf_g*sy)
        sol_x2 = rx1+dp_x
        sag_x1 = rx2-dp_x
        n_yan = sec['sol']
        for i in range(n_yan):
            rry1 = ry1+int(i*1.1*sy)
            rry2 = max(rry1+int(0.9*sy), rry1+8)
            if rry2 > ry2: break
            raflar.append((rx1, rry1, sol_x2, rry2, i))
            raflar.append((sag_x1, rry1, rx2, rry2, i+100))
        bas_x = sol_x2+int(koridor*sx)
        bit_x = sag_x1-int(koridor*sx)
        n_alt = sec['alt']
        if g_duvar == 'alt':
            for i in range(n_alt):
                rrx1 = bas_x+int(i*1.1*sx)
                rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                if rrx2 > bit_x: break
                raflar.append((rrx1, ry1, rrx2, ry1+dp_y, i+200))
        else:
            for i in range(n_alt):
                rrx1 = bas_x+int(i*1.1*sx)
                rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                if rrx2 > bit_x: break
                raflar.append((rrx1, ry2-dp_y, rrx2, ry2, i+200))
        if tip == 'U_orta' and sec.get('ek_satir',0) > 0:
            ic_g = ry2-ry1-dp_y*2-int(koridor*sy)*2
            ic_u = bit_x-bas_x
            for row in range(sec['ek_satir']):
                rry1 = ry1+dp_y+int(koridor*sy)+int(row*1.1*sy)
                rry2 = max(rry1+int(0.9*sy), rry1+8)
                for col in range(sec['ek_perz']):
                    rrx1 = bas_x+int(col*1.1*sx)
                    rrx2 = max(rrx1+int(0.9*sx), rrx1+8)
                    if rrx2 > bit_x: break
                    raflar.append((rrx1, rry1, rrx2, rry2, row+300))
        # Koridor olcusu
        olcu_ciz(draw, ox+pw+5, ry1, ox+pw+5, ry1+dp_y+int(koridor*sy), f"{koridor}m", fsm, MOR, MOR, dikey=True)
        olcu_ciz(draw, rx1, ry1-16, sol_x2, ry1-16, f"{raf_g}m", fsm, MOR, MOR)

    # Raflari ciz
    for r in raflar:
        ciz_raf(draw, r[0], r[1], r[2], r[3])

    # Ana depo olculeri
    olcu_ciz(draw, ox, oy-20, ox+pw, oy-20, f"{uzunluk}m", fn, BEYAZ, AGRI)
    olcu_ciz(draw, ox-20, oy, ox-20, oy+ph, f"{genislik}m", fn, BEYAZ, AGRI, dikey=True)

    # Alt bilgi
    iy = H-INFO_H
    draw.rectangle([0, iy, W, H], fill='#161b22')
    draw.line([0, iy, W, iy], fill='#404060', width=2)

    lx, ly = 20, iy+12
    if lang == 'tr':
        items = [
            ('#4a9eff',  "● Dikme",           f"{raf_yuk}m"),
            ('#ff8c42',  "━ Yatay Bag.",       f"{raf_g}m"),
            ('#4ade80',  "| Derinlik",          "1.10m"),
            ('#c084fc',  "↔ Koridor",           f"{koridor}m"),
            ('#22c55e',  "▦ Yukleme Alani",     f"{g_bosluk}m"),
            ('#ffd700',  "▐ Kapi",              f"{g_genislik}m"),
        ]
    else:
        items = [
            ('#4a9eff',  "● Stoyka",            f"{raf_yuk}m"),
            ('#ff8c42',  "━ Balka",             f"{raf_g}m"),
            ('#4ade80',  "| Glubina",            "1.10m"),
            ('#c084fc',  "↔ Prokhod",            f"{koridor}m"),
            ('#22c55e',  "▦ Zona Pogruzki",      f"{g_bosluk}m"),
            ('#ffd700',  "▐ Vkhod",              f"{g_genislik}m"),
        ]
    for renk, isim, olcu in items:
        draw.text((lx, ly), isim, fill=renk, font=fb)
        draw.text((lx+195, ly), olcu, fill=BEYAZ, font=fb)
        ly += 20

    rx2b, ry2b = W//2+10, iy+12
    if lang == 'tr':
        bilgiler = [
            ("Kat",        str(kat)),
            ("Toplam Raf", str(sec['toplam'])),
            ("Tip",        tip_adi.get(tip,tip)),
            ("Kenar",      f"{kb2}m"),
            ("Kapi Yeri",  g_duvar),
        ]
    else:
        bilgiler = [
            ("Yarusov",    str(kat)),
            ("Vsego",      str(sec['toplam'])),
            ("Tip",        tip_adi.get(tip,tip)),
            ("Otstup",     f"{kb2}m"),
            ("Vkhod",      g_duvar),
        ]
    for k, v in bilgiler:
        draw.text((rx2b, ry2b), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx2b+165, ry2b), v, fill=BEYAZ, font=fb)
        ry2b += 20

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150,150))
    buf.seek(0)
    return buf

# ---- HANDLERS ----

async def baslat(update, context):
    context.user_data.clear()
    await update.message.reply_text(
        "Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce","🇷🇺 Russkiy"]])
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
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return UZUNLUK

async def genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',','.'))
        msg = "📏 Depo yuksekligi (m):\nOrnek: 6" if lang=='tr' else "📏 Высота склада (м):\nПример: 6"
        await update.message.reply_text(msg)
        return DEPO_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
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
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
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
    elif "sol" in t or "левее" in t:
        context.user_data['giris_konum'] = 'sol'
    else:
        context.user_data['giris_konum'] = 'sag'

    if context.user_data['giris_konum'] == 'orta':
        msg = ("🚪 Kapi genisligi (m):\nOrnek: 3"
               if lang=='tr' else
               "🚪 Ширина ворот (м):\nПример: 3")
        await update.message.reply_text(msg, reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_GENISLIK
    else:
        msg = ("🚪 Koseden kac metre uzakta?\nOrnek: 2"
               if lang=='tr' else
               "🚪 Расстояние от угла (м)?\nПример: 2")
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return GIRIS_MESAFE

async def giris_mesafe_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',','.'))
        msg = ("🚪 Kapi genisligi (m):\nOrnek: 3"
               if lang=='tr' else
               "🚪 Ширина ворот (м):\nПример: 3")
        await update.message.reply_text(msg, reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_MESAFE

async def giris_genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_genislik'] = float(update.message.text.replace(',','.'))
        msg = ("🏗 Yukleme/bosaltma alani (m):\nOrnek: 3"
               if lang=='tr' else
               "🏗 Зона погрузки/разгрузки (м):\nПример: 3")
        await update.message.reply_text(msg, reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_GENISLIK

async def giris_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_bosluk'] = float(update.message.text.replace(',','.'))
        msg = ("📐 Raf-duvar arasi bosluk (m)?\n0=bitisik"
               if lang=='tr' else
               "📐 Отступ от стен (м)?\n0=вплотную")
        await update.message.reply_text(msg, reply_markup=kb([["0","0.3","0.5","1"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_BOSLUK

async def kenar_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kenar_bosluk'] = float(update.message.text.replace(',','.'))
        if lang == 'tr':
            msg = "🚦 Koridor tipi?\nForklift 3m | Transpalet 2m | El 1.2m"
        else:
            msg = "🚦 Тип прохода?\nПогрузчик 3м | Транспалет 2м | Ручной 1.2м"
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
        msg = "📦 Raf basina palet?\n1=0.95m  2=1.85m\n3=2.70m  4=3.60m"
    else:
        msg = "📦 Паллет на ряд?\n1=0.95м  2=1.85м\n3=2.70м  4=3.60м"
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
        await update.message.reply_text("1-4 girin." if lang=='tr' else "Введите 1-4.")
        return PALET

async def kat_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kat'] = int(update.message.text)
        msg = "📏 Raf yuksekligi (m)?\nOrnek: 5" if lang=='tr' else "📏 Высота стеллажа (м)?\nПример: 5"
        await update.message.reply_text(msg)
        return RAF_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return KAT

async def raf_yuk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['raf_yuk'] = float(update.message.text.replace(',','.'))
        d = context.user_data
        raf_g   = PALET_GENISLIK[d['palet']]
        koridor = KORIDOR_GENISLIK[d['koridor_tipi']]
        kb2     = d.get('kenar_bosluk', 0)
        g_duvar = d['giris_duvar']
        g_bosluk= d['giris_bosluk']

        # 5 secenek hesapla
        tipler = ['I_paralel', 'I_sirt', 'L', 'U', 'U_orta']
        secenekler = []
        for t in tipler:
            s = hesapla_secenek(t, d['uzunluk'], d['genislik'], raf_g, koridor, kb2, g_duvar, g_bosluk)
            if s['toplam'] > 0:
                secenekler.append(s)
        secenekler.sort(key=lambda x: x['toplam'], reverse=True)
        context.user_data['secenekler'] = secenekler

        tip_adi = {'I_paralel':'I-Paralel','I_sirt':'I-Sirt Sirta','L':'L-Tip','U':'U-Tip','U_orta':'U+Orta'}
        if lang == 'tr':
            msg = "🤖 EN UYGUN RAF YERLEŞİM SEÇENEKLERİ\n━━━━━━━━━━━━━━━━━━━━━\n"
            for i, s in enumerate(secenekler[:3]):
                emoji = "⭐" if i==0 else "▪"
                msg += f"{emoji} {i+1}. {tip_adi.get(s['tip'],s['tip'])}: {s['toplam']} raf\n"
            msg += f"\n⭐ = En iyi secenek\nHangi secenegi istersiniz?"
            rows = [[f"1. {tip_adi.get(secenekler[0]['tip'],'')}",
                     f"2. {tip_adi.get(secenekler[1]['tip'],'')}"] if len(secenekler)>1 else
                    [f"1. {tip_adi.get(secenekler[0]['tip'],'')}"],
                    [f"3. {tip_adi.get(secenekler[2]['tip'],'')}"] if len(secenekler)>2 else []]
            rows = [r for r in rows if r]
        else:
            msg = "🤖 ЛУЧШИЕ ВАРИАНТЫ РАССТАНОВКИ СТЕЛЛАЖЕЙ\n━━━━━━━━━━━━━━━━━━━━━\n"
            for i, s in enumerate(secenekler[:3]):
                emoji = "⭐" if i==0 else "▪"
                msg += f"{emoji} {i+1}. {tip_adi.get(s['tip'],s['tip'])}: {s['toplam']} стелл.\n"
            msg += f"\n⭐ = Лучший вариант\nКакой выбираете?"
            rows = [[f"1. {tip_adi.get(secenekler[0]['tip'],'')}",
                     f"2. {tip_adi.get(secenekler[1]['tip'],'')}"] if len(secenekler)>1 else
                    [f"1. {tip_adi.get(secenekler[0]['tip'],'')}"],
                    [f"3. {tip_adi.get(secenekler[2]['tip'],'')}"] if len(secenekler)>2 else []]
            rows = [r for r in rows if r]

        await update.message.reply_text(msg, reply_markup=kb(rows))
        return SECENEK_SEC
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

async def secenek_sec_h(update, context):
    lang = get_lang(context)
    t = update.message.text.strip()
    d = context.user_data
    secenekler = d.get('secenekler', [])

    # Secilen secenegi bul
    sec = secenekler[0]  # varsayilan en iyi
    if t.startswith('2') and len(secenekler) > 1:
        sec = secenekler[1]
    elif t.startswith('3') and len(secenekler) > 2:
        sec = secenekler[2]

    await update.message.reply_text(
        "⏳ Cizim hazirlaniyor..." if lang=='tr' else "⏳ Подготовка чертежа...",
        reply_markup=ReplyKeyboardRemove()
    )
    try:
        resim = teknik_ciz(d, lang, sec)
        tip_adi = {'I_paralel':'I-Paralel','I_sirt':'I-Sirt Sirta','L':'L-Tip','U':'U-Tip','U_orta':'U+Orta'}
        if lang == 'tr':
            cap = (f"TEKNİK ÇİZİM\n"
                   f"Tip: {tip_adi.get(sec['tip'],sec['tip'])}\n"
                   f"Depo: {d['uzunluk']}×{d['genislik']}m | Yuk: {d['depo_yukseklik']}m\n"
                   f"Toplam raf: {sec['toplam']} | Kat: {d['kat']} | Raf yuk: {d['raf_yuk']}m\n"
                   f"Kapi: {d['giris_duvar']} duvar | Yukleme: {d['giris_bosluk']}m\n"
                   f"Fiyat icin: /hesapla")
        else:
            cap = (f"ТЕХНИЧЕСКИЙ ЧЕРТЁЖ\n"
                   f"Тип: {tip_adi.get(sec['tip'],sec['tip'])}\n"
                   f"Склад: {d['uzunluk']}×{d['genislik']}м | Выс: {d['depo_yukseklik']}м\n"
                   f"Стеллажей: {sec['toplam']} | Ярусов: {d['kat']} | Выс. стелл.: {d['raf_yuk']}м\n"
                   f"Вход: {d['giris_duvar']} | Зона: {d['giris_bosluk']}м\n"
                   f"Расчёт: /raschet")
        await update.message.reply_photo(photo=resim, caption=cap)
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
    return ConversationHandler.END

async def iptal(update, context):
    lang = get_lang(context)
    await update.message.reply_text(
        "Iptal. /hesapla" if lang=='tr' else "Отменено. /raschet",
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
            GIRIS_GENISLIK:[MessageHandler(filters.TEXT & ~filters.COMMAND, giris_genislik_h)],
            GIRIS_BOSLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_bosluk_h)],
            KENAR_BOSLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_h)],
            KORIDOR_TIPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_h)],
            PALET:        [MessageHandler(filters.TEXT & ~filters.COMMAND, palet_h)],
            KAT:          [MessageHandler(filters.TEXT & ~filters.COMMAND, kat_h)],
            RAF_YUK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, raf_yuk_h)],
            SECENEK_SEC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, secenek_sec_h)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
