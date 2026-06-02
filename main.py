import os
import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, UZUNLUK, GENISLIK, DEPO_YUK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_GENISLIK, GIRIS_BOSLUK,
 KENAR_BOSLUK, KORIDOR_TIPI, PALET, KAT, RAF_YUK) = range(14)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def kb(rows):
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)

def hesapla_secenek(tip, uzunluk, genislik, raf_g, koridor, kb2, g_duvar, g_bosluk):
    if g_duvar in ['alt', 'ust']:
        ef_g = genislik - kb2*2 - g_bosluk
        ef_u = uzunluk - kb2*2
    else:
        ef_g = genislik - kb2*2
        ef_u = uzunluk - kb2*2 - g_bosluk
    ef_g = max(ef_g, 0.1)
    ef_u = max(ef_u, 0.1)

    if tip == 'I_paralel':
        satir = max(1, int(ef_g / (raf_g + koridor)))
        perz  = max(1, int(ef_u / 1.1))
        toplam = satir * perz
        kalan = ef_g - satir*(raf_g+koridor)
        return {'toplam': toplam, 'satir': satir, 'perz': perz, 'kalan': round(kalan,2), 'tip': tip}

    elif tip == 'I_sirt':
        satir = max(1, int(ef_g / (raf_g + koridor)))
        perz  = max(1, int(ef_u / 1.1))
        toplam = satir * perz
        kalan = ef_g - satir*(raf_g+koridor)
        return {'toplam': toplam, 'satir': satir, 'perz': perz, 'kalan': round(kalan,2), 'tip': tip}

    elif tip == 'L':
        sol = max(1, int(ef_g / 1.1))
        alt = max(1, int((ef_u - raf_g - koridor) / 1.1))
        return {'toplam': sol+alt, 'sol': sol, 'alt': alt, 'tip': tip}

    elif tip == 'U':
        sol = max(1, int(ef_g / 1.1))
        sag = sol
        ara = ef_u - raf_g*2 - koridor*2
        alt = max(0, int(ara / 1.1)) if ara > 0 else 0
        return {'toplam': sol+sag+alt, 'sol': sol, 'sag': sag, 'alt': alt, 'tip': tip}

    elif tip == 'U_orta':
        sol = max(1, int(ef_g / 1.1))
        sag = sol
        ara = ef_u - raf_g*2 - koridor*2
        alt = max(0, int(ara / 1.1)) if ara > 0 else 0
        ic_g = ef_g - raf_g*2 - koridor*2
        ic_u = ara
        ek_s = max(0, int(ic_g / (raf_g + koridor))) if ic_g > 0 else 0
        ek_p = max(0, int(ic_u / 1.1)) if ic_u > 0 else 0
        return {'toplam': sol+sag+alt+ek_s*ek_p, 'sol': sol, 'sag': sag, 'alt': alt,
                'ek_satir': ek_s, 'ek_perz': ek_p, 'tip': tip}
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

def olcu_yatay(draw, x1, x2, y, metin, font, renk):
    draw.line([x1, y, x2, y], fill=renk, width=1)
    draw.line([x1, y-5, x1, y+5], fill=renk, width=2)
    draw.line([x2, y-5, x2, y+5], fill=renk, width=2)
    draw.text(((x1+x2)//2, y-6), metin, fill=renk, font=font, anchor='mb')

def olcu_dikey(draw, x, y1, y2, metin, font, renk):
    draw.line([x, y1, x, y2], fill=renk, width=1)
    draw.line([x-5, y1, x+5, y1], fill=renk, width=2)
    draw.line([x-5, y2, x+5, y2], fill=renk, width=2)
    draw.text((x+6, (y1+y2)//2), metin, fill=renk, font=font, anchor='lm')

def teknik_ciz(d, lang, sec, sira_no, toplam_sira):
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
    g_gen     = d.get('giris_genislik', 3.0)
    tip       = sec['tip']

    # Yukleme alani m2
    if g_duvar in ['alt','ust']:
        yukleme_m2 = round(uzunluk * g_bosluk, 1)
        yukleme_en = uzunluk
        yukleme_boy = g_bosluk
    else:
        yukleme_m2 = round(genislik * g_bosluk, 1)
        yukleme_en = g_bosluk
        yukleme_boy = genislik

    W, H = 1150, 880
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
    AGRI   = '#505070'
    SARI   = '#ffd700'
    SINIR  = '#00b4d8'
    MOR    = '#c084fc'
    YESIL2 = '#22c55e'

    tip_adi = {'I_paralel':'I — Paralel Siralar','I_sirt':'I — Sirt Sirta',
               'L':'L — Iki Duvara','U':'U — Uc Duvara','U_orta':'U — Uc Duvar + Orta'}
    tip_adi_ru = {'I_paralel':'I — Параллельные ряды','I_sirt':'I — Спина к спине',
                  'L':'L — Вдоль двух стен','U':'U — Вдоль трёх стен','U_orta':'U — Три стены + центр'}

    INFO_H = 150
    pl, pt, pr, pb = 80, 55, 125, INFO_H + 40
    pw = W - pl - pr
    ph = H - pt - pb
    ox, oy = pl, pt
    sx = pw / uzunluk
    sy = ph / genislik

    # Baslik
    draw.rectangle([0, 0, W, 42], fill='#161b22')
    t_adi = tip_adi_ru.get(tip,tip) if lang=='ru' else tip_adi.get(tip,tip)
    if lang == 'tr':
        baslik = f"SECENEK {sira_no}/{toplam_sira}  |  {t_adi}  |  {sec['toplam']} raf"
    else:
        baslik = f"ВАРИАНТ {sira_no}/{toplam_sira}  |  {t_adi}  |  {sec['toplam']} стелл."
    draw.text((W//2, 21), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo
    draw.rectangle([ox, oy, ox+pw, oy+ph], outline=SINIR, width=3)
    draw.rectangle([ox+2, oy+2, ox+pw-2, oy+ph-2], outline='#1a3a5c', width=1)

    # Kapi ve yukleme alani
    G = max(int(g_gen*sx), 30)
    kapi_lbl = "GIRIS/CIKIS" if lang=='tr' else "ВХОД/ВЫХОД"
    if g_duvar in ['alt','ust']:
        if g_konum == 'orta': gx = ox+pw//2
        elif g_konum == 'sol': gx = ox+int(g_mesafe*sx)+G//2
        else: gx = ox+pw-int(g_mesafe*sx)-G//2
    else:
        if g_konum == 'orta': gy = oy+ph//2
        elif g_konum == 'ust': gy = oy+int(g_mesafe*sy)+G//2
        else: gy = oy+ph-int(g_mesafe*sy)-G//2

    bp_y = int(g_bosluk*sy)
    bp_x = int(g_bosluk*sx)

    # Yukleme alani (yesil) + olculeri
    if g_duvar == 'alt':
        draw.rectangle([ox+3, oy+ph-bp_y, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        zm = f"{yukleme_en}×{yukleme_boy}m = {yukleme_m2}m²"
        draw.text((ox+pw//2, oy+ph-bp_y//2-7), "YUKLEME/BOSALTMA" if lang=='tr' else "ЗОНА ПОГРУЗКИ", fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw//2, oy+ph-bp_y//2+9), zm, fill=YESIL2, font=fb, anchor='mm')
        olcu_yatay(draw, ox, ox+pw, oy+ph-bp_y-18, f"{uzunluk}m", fsm, YESIL2)
        olcu_dikey(draw, ox+pw+8, oy+ph-bp_y, oy+ph, f"{g_bosluk}m", fsm, YESIL2)
        draw.line([gx-G//2, oy+ph, gx+G//2, oy+ph], fill=SARI, width=8)
        draw.text((gx, oy+ph+9), kapi_lbl, fill=SARI, font=fsm, anchor='mt')
        olcu_yatay(draw, gx-G//2, gx+G//2, oy+ph+24, f"{g_gen}m", fsm, SARI)
        if g_mesafe > 0 and g_konum != 'orta':
            if g_konum == 'sol': olcu_yatay(draw, ox, gx-G//2, oy+ph+38, f"{g_mesafe}m", fsm, BEYAZ)
            else: olcu_yatay(draw, gx+G//2, ox+pw, oy+ph+38, f"{g_mesafe}m", fsm, BEYAZ)

    elif g_duvar == 'ust':
        draw.rectangle([ox+3, oy+3, ox+pw-3, oy+bp_y], fill='#052e16', outline=YESIL2, width=2)
        zm = f"{yukleme_en}×{yukleme_boy}m = {yukleme_m2}m²"
        draw.text((ox+pw//2, oy+bp_y//2-7), "YUKLEME/BOSALTMA" if lang=='tr' else "ЗОНА ПОГРУЗКИ", fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw//2, oy+bp_y//2+9), zm, fill=YESIL2, font=fb, anchor='mm')
        olcu_dikey(draw, ox+pw+8, oy, oy+bp_y, f"{g_bosluk}m", fsm, YESIL2)
        draw.line([gx-G//2, oy, gx+G//2, oy], fill=SARI, width=8)
        draw.text((gx, oy-9), kapi_lbl, fill=SARI, font=fsm, anchor='mb')
        olcu_yatay(draw, gx-G//2, gx+G//2, oy-22, f"{g_gen}m", fsm, SARI)

    elif g_duvar == 'sol':
        draw.rectangle([ox+3, oy+3, ox+bp_x, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        zm = f"{yukleme_en}×{yukleme_boy}m={yukleme_m2}m²"
        draw.text((ox+bp_x//2, oy+ph//2-7), "YUKLEME" if lang=='tr' else "ЗОНА", fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+bp_x//2, oy+ph//2+9), zm, fill=YESIL2, font=fb, anchor='mm')
        olcu_yatay(draw, ox, ox+bp_x, oy+ph+8, f"{g_bosluk}m", fsm, YESIL2)
        draw.line([ox, gy-G//2, ox, gy+G//2], fill=SARI, width=8)
        draw.text((ox-8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='rm')
        olcu_dikey(draw, ox-35, gy-G//2, gy+G//2, f"{g_gen}m", fsm, SARI)

    else:
        draw.rectangle([ox+pw-bp_x, oy+3, ox+pw-3, oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        zm = f"{yukleme_en}×{yukleme_boy}m={yukleme_m2}m²"
        draw.text((ox+pw-bp_x//2, oy+ph//2-7), "YUKLEME" if lang=='tr' else "ЗОНА", fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw-bp_x//2, oy+ph//2+9), zm, fill=YESIL2, font=fb, anchor='mm')
        olcu_yatay(draw, ox+pw-bp_x, ox+pw, oy+ph+8, f"{g_bosluk}m", fsm, YESIL2)
        draw.line([ox+pw, gy-G//2, ox+pw, gy+G//2], fill=SARI, width=8)
        draw.text((ox+pw+8, gy), kapi_lbl, fill=SARI, font=fsm, anchor='lm')
        olcu_dikey(draw, ox+pw+25, gy-G//2, gy+G//2, f"{g_gen}m", fsm, SARI)

    # RAF ALANI
    rax1 = ox+int(kb2*sx); ray1 = oy+int(kb2*sy)
    rax2 = ox+pw-int(kb2*sx); ray2 = oy+ph-int(kb2*sy)
    if g_duvar == 'alt':   ray2 -= bp_y
    elif g_duvar == 'ust': ray1 += bp_y
    elif g_duvar == 'sol': rax1 += bp_x
    else:                  rax2 -= bp_x

    raflar = []
    dikme_say = 0
    yatay_say = 0

    if tip in ['I_paralel','I_sirt']:
        n_s = sec['satir']; n_p = sec['perz']
        satir_ry = {}
        for row in range(n_s):
            rry1 = ray1+int((raf_g/2+row*(raf_g+koridor))*sy)
            rry2 = max(rry1+int(raf_g*sy), rry1+14)
            for col in range(n_p):
                rrx1 = rax1+int(col*1.1*sx)+1
                rrx2 = max(rax1+int((col+1)*1.1*sx)-1, rrx1+8)
                raflar.append((rrx1,rry1,rrx2,rry2,row))
            if row not in satir_ry: satir_ry[row] = (rry1,rry2)
        dikme_say = n_s * n_p * 4
        yatay_say = n_s * n_p * kat * 2

        # Raf etiketi + koridor olcusu
        for i,row in enumerate(sorted(satir_ry.keys())):
            b,d2 = satir_ry[row]
            draw.text((ox+pw+6,(b+d2)//2), f"R{row+1}", fill=BEYAZ, font=fsm, anchor='lm')
            if i > 0:
                prev = sorted(satir_ry.keys())[i-1]
                prev_d2 = satir_ry[prev][1]
                olcu_dikey(draw, ox+pw+6, prev_d2, b, f"{koridor}m", fsm, MOR)
        # Yatay baglanti olcusu
        if n_p > 0:
            rrx1 = rax1+1; rrx2 = max(rax1+int(1.1*sx)-1, rrx1+8)
            rry1 = ray1+int(raf_g/2*sy)
            olcu_yatay(draw, rrx1, rrx2, rry1-14, f"{raf_g}m", fsm, MOR)

    elif tip == 'L':
        dp_x = int(raf_g*sx); dp_y = int(raf_g*sy)
        for i in range(sec['sol']):
            rry1 = ray1+int(i*1.1*sy); rry2 = max(rry1+int(0.9*sy),rry1+8)
            if rry2 > ray2: break
            raflar.append((rax1,rry1,rax1+dp_x,rry2,i))
        bas_x = rax1+dp_x+int(koridor*sx)
        if g_duvar == 'alt':
            for i in range(sec['alt']):
                rrx1=bas_x+int(i*1.1*sx); rrx2=max(rrx1+int(0.9*sx),rrx1+8)
                if rrx2>rax2: break
                raflar.append((rrx1,ray1,rrx2,ray1+dp_y,i+100))
        else:
            for i in range(sec['alt']):
                rrx1=bas_x+int(i*1.1*sx); rrx2=max(rrx1+int(0.9*sx),rrx1+8)
                if rrx2>rax2: break
                raflar.append((rrx1,ray2-dp_y,rrx2,ray2,i+100))
        dikme_say = len(raflar) * 4
        yatay_say = len(raflar) * kat * 2
        olcu_yatay(draw, rax1, rax1+dp_x, ray1-14, f"{raf_g}m", fsm, MOR)

    elif tip in ['U','U_orta']:
        dp_x = int(raf_g*sx); dp_y = int(raf_g*sy)
        sol_x2 = rax1+dp_x; sag_x1 = rax2-dp_x
        for i in range(sec['sol']):
            rry1=ray1+int(i*1.1*sy); rry2=max(rry1+int(0.9*sy),rry1+8)
            if rry2>ray2: break
            raflar.append((rax1,rry1,sol_x2,rry2,i))
            raflar.append((sag_x1,rry1,rax2,rry2,i+100))
        bas_x=sol_x2+int(koridor*sx); bit_x=sag_x1-int(koridor*sx)
        if g_duvar == 'alt':
            for i in range(sec['alt']):
                rrx1=bas_x+int(i*1.1*sx); rrx2=max(rrx1+int(0.9*sx),rrx1+8)
                if rrx2>bit_x: break
                raflar.append((rrx1,ray1,rrx2,ray1+dp_y,i+200))
        else:
            for i in range(sec['alt']):
                rrx1=bas_x+int(i*1.1*sx); rrx2=max(rrx1+int(0.9*sx),rrx1+8)
                if rrx2>bit_x: break
                raflar.append((rrx1,ray2-dp_y,rrx2,ray2,i+200))
        if tip=='U_orta' and sec.get('ek_satir',0)>0:
            for row in range(sec['ek_satir']):
                rry1=ray1+dp_y+int(koridor*sy)+int(row*1.1*sy)
                rry2=max(rry1+int(0.9*sy),rry1+8)
                for col in range(sec['ek_perz']):
                    rrx1=bas_x+int(col*1.1*sx); rrx2=max(rrx1+int(0.9*sx),rrx1+8)
                    if rrx2>bit_x: break
                    raflar.append((rrx1,rry1,rrx2,rry2,row+300))
        dikme_say = len(raflar)*4
        yatay_say = len(raflar)*kat*2
        olcu_yatay(draw, rax1, sol_x2, ray1-14, f"{raf_g}m", fsm, MOR)
        olcu_dikey(draw, ox+pw+6, ray1, ray1+dp_y+int(koridor*sy), f"{koridor}m", fsm, MOR)

    for r in raflar:
        ciz_raf(draw, r[0], r[1], r[2], r[3])

    # Depo ana olculeri
    olcu_yatay(draw, ox, ox+pw, oy-20, f"{uzunluk}m", fn, BEYAZ)
    olcu_dikey(draw, ox-20, oy, oy+ph, f"{genislik}m", fn, BEYAZ)

    # ---- ALT BİLGİ ----
    iy = H-INFO_H
    draw.rectangle([0, iy, W, H], fill='#161b22')
    draw.line([0, iy, W, iy], fill='#404060', width=2)

    # Sol sutun - malzeme listesi
    lx, ly = 20, iy+14
    if lang == 'tr':
        draw.text((lx, ly), "MALZEME LİSTESİ", fill=SARI, font=fb)
        ly += 22
        # Dikme
        dikme_toplam = round(dikme_say * raf_yuk, 1)
        draw.text((lx, ly), f"● Dikme:", fill='#4a9eff', font=fb)
        draw.text((lx+110, ly), f"1 adet = {raf_yuk}m  |  {dikme_say} adet  |  Toplam: {dikme_toplam}m", fill=BEYAZ, font=fn)
        ly += 22
        # Yatay baglanti
        draw.text((lx, ly), f"━ Yatay Bag.:", fill='#ff8c42', font=fb)
        draw.text((lx+110, ly), f"1 adet = {raf_g}m  |  {yatay_say} adet  |  Toplam: {round(yatay_say*raf_g,1)}m", fill=BEYAZ, font=fn)
        ly += 22
        # Derinlik
        derinlik_say = dikme_say // 2
        draw.text((lx, ly), f"| Derinlik:", fill='#4ade80', font=fb)
        draw.text((lx+110, ly), f"1 adet = 1.10m  |  {derinlik_say} adet  |  Toplam: {round(derinlik_say*1.1,1)}m", fill=BEYAZ, font=fn)
        ly += 22
        # Yukleme alani
        draw.text((lx, ly), f"▦ Yukleme Alani:", fill='#22c55e', font=fb)
        draw.text((lx+148, ly), f"{yukleme_en}m × {yukleme_boy}m = {yukleme_m2} m²", fill='#22c55e', font=fn)
        ly += 22
        # Koridor
        draw.text((lx, ly), f"↔ Koridor:", fill='#c084fc', font=fb)
        draw.text((lx+110, ly), f"{koridor}m  |  Kapi: {g_gen}m", fill=BEYAZ, font=fn)
    else:
        draw.text((lx, ly), "СПИСОК МАТЕРИАЛОВ", fill=SARI, font=fb)
        ly += 22
        dikme_toplam = round(dikme_say * raf_yuk, 1)
        draw.text((lx, ly), f"● Стойка:", fill='#4a9eff', font=fb)
        draw.text((lx+100, ly), f"1 шт = {raf_yuk}м  |  {dikme_say} шт  |  Итого: {dikme_toplam}м", fill=BEYAZ, font=fn)
        ly += 22
        draw.text((lx, ly), f"━ Балка:", fill='#ff8c42', font=fb)
        draw.text((lx+100, ly), f"1 шт = {raf_g}м  |  {yatay_say} шт  |  Итого: {round(yatay_say*raf_g,1)}м", fill=BEYAZ, font=fn)
        ly += 22
        derinlik_say = dikme_say // 2
        draw.text((lx, ly), f"| Глубина:", fill='#4ade80', font=fb)
        draw.text((lx+100, ly), f"1 шт = 1.10м  |  {derinlik_say} шт  |  Итого: {round(derinlik_say*1.1,1)}м", fill=BEYAZ, font=fn)
        ly += 22
        draw.text((lx, ly), f"▦ Зона погрузки:", fill='#22c55e', font=fb)
        draw.text((lx+148, ly), f"{yukleme_en}м × {yukleme_boy}м = {yukleme_m2} м²", fill='#22c55e', font=fn)
        ly += 22
        draw.text((lx, ly), f"↔ Проход:", fill='#c084fc', font=fb)
        draw.text((lx+100, ly), f"{koridor}м  |  Ворота: {g_gen}м", fill=BEYAZ, font=fn)

    # Sag sutun - ozet
    rx2b, ry2b = W//2+20, iy+14
    if lang == 'tr':
        draw.text((rx2b, ry2b), "ÖZET", fill=SARI, font=fb)
        ry2b += 22
        bilgiler = [
            ("Toplam Raf", str(sec['toplam'])),
            ("Kat Sayisi",  str(kat)),
            ("Raf Yuksekligi", f"{raf_yuk}m"),
            ("Depo", f"{uzunluk}×{genislik}×{d['depo_yukseklik']}m"),
            ("Koridor Tipi", d['koridor_tipi'].title()),
        ]
    else:
        draw.text((rx2b, ry2b), "СВОДКА", fill=SARI, font=fb)
        ry2b += 22
        bilgiler = [
            ("Всего стеллажей", str(sec['toplam'])),
            ("Ярусов",           str(kat)),
            ("Высота стеллажа",  f"{raf_yuk}м"),
            ("Склад", f"{uzunluk}×{genislik}×{d['depo_yukseklik']}м"),
            ("Тип прохода",      d['koridor_tipi'].title()),
        ]
    for k, v in bilgiler:
        draw.text((rx2b, ry2b), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx2b+185, ry2b), v, fill=BEYAZ, font=fb)
        ry2b += 22

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
        msg = "🚪 Kapi genisligi (m):\nOrnek: 3" if lang=='tr' else "🚪 Ширина ворот (м):\nПример: 3"
        await update.message.reply_text(msg, reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_GENISLIK
    else:
        msg = "🚪 Koseden kac metre?\nOrnek: 2" if lang=='tr' else "🚪 Расстояние от угла (м)?\nПример: 2"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return GIRIS_MESAFE

async def giris_mesafe_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',','.'))
        msg = "🚪 Kapi genisligi (m):\nOrnek: 3" if lang=='tr' else "🚪 Ширина ворот (м):\nПример: 3"
        await update.message.reply_text(msg, reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_MESAFE

async def giris_genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_genislik'] = float(update.message.text.replace(',','.'))
        msg = "🏗 Yukleme/bosaltma alani (m):\nOrnek: 3" if lang=='tr' else "🏗 Зона погрузки/разгрузки (м):\nПример: 3"
        await update.message.reply_text(msg, reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_GENISLIK

async def giris_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_bosluk'] = float(update.message.text.replace(',','.'))
        msg = "📐 Raf-duvar arasi bosluk?\n0=bitisik" if lang=='tr' else "📐 Отступ от стен?\n0=вплотную"
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

        # 5 secenek hesapla, en iyi 3 tane gonder
        tipler = ['I_paralel','I_sirt','L','U','U_orta']
        secenekler = []
        for t in tipler:
            s = hesapla_secenek(t, d['uzunluk'], d['genislik'], raf_g, koridor, kb2, d['giris_duvar'], d['giris_bosluk'])
            if s['toplam'] > 0:
                secenekler.append(s)
        secenekler.sort(key=lambda x: x['toplam'], reverse=True)
        secenekler = secenekler[:3]
        context.user_data['secenekler'] = secenekler

        tip_adi    = {'I_paralel':'I-Paralel','I_sirt':'I-Sirt Sirta','L':'L-Tip','U':'U-Tip','U_orta':'U+Orta'}
        tip_adi_ru = {'I_paralel':'I-Паралл.','I_sirt':'I-Спина к спине','L':'L-Тип','U':'U-Тип','U_orta':'U+Центр'}

        if lang == 'tr':
            msg = "⏳ 3 secenek hazirlaniyor, lutfen bekleyin..."
        else:
            msg = "⏳ Готовлю 3 варианта, подождите..."
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())

        # 3 resim gonder ust uste
        for i, sec in enumerate(secenekler):
            resim = teknik_ciz(d, lang, sec, i+1, len(secenekler))
            t_ad = tip_adi_ru.get(sec['tip'],sec['tip']) if lang=='ru' else tip_adi.get(sec['tip'],sec['tip'])
            if lang == 'tr':
                cap = f"{'⭐ EN İYİ — ' if i==0 else ''}{i+1}. SECENEK: {t_ad}\nToplam raf: {sec['toplam']} adet"
            else:
                cap = f"{'⭐ ЛУЧШИЙ — ' if i==0 else ''}{i+1}. ВАРИАНТ: {t_ad}\nСтеллажей: {sec['toplam']} шт"
            await update.message.reply_photo(photo=resim, caption=cap)

        if lang == 'tr':
            await update.message.reply_text("✅ Tum secenekler hazir!\nFiyat hesabi icin: /hesapla\nYeni cizim icin: /hesapla")
        else:
            await update.message.reply_text("✅ Все варианты готовы!\nРасчёт цены: /raschet\nНовый чертёж: /raschet")

        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

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
            LANG:          [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
            UZUNLUK:       [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk_h)],
            GENISLIK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik_h)],
            DEPO_YUK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, depo_yuk_h)],
            GIRIS_DUVAR:   [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_duvar_h)],
            GIRIS_KONUM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_konum_h)],
            GIRIS_MESAFE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_mesafe_h)],
            GIRIS_GENISLIK:[MessageHandler(filters.TEXT & ~filters.COMMAND, giris_genislik_h)],
            GIRIS_BOSLUK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_bosluk_h)],
            KENAR_BOSLUK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_h)],
            KORIDOR_TIPI:  [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_h)],
            PALET:         [MessageHandler(filters.TEXT & ~filters.COMMAND, palet_h)],
            KAT:           [MessageHandler(filters.TEXT & ~filters.COMMAND, kat_h)],
            RAF_YUK:       [MessageHandler(filters.TEXT & ~filters.COMMAND, raf_yuk_h)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
