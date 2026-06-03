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
DERINLIK = 1.1  # sabit derinlik

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def kb(rows):
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)

def hesapla_secenekler(uzunluk, genislik, raf_g, koridor, kb2, g_duvar, g_bosluk):
    """
    Raf yonu: yatay baglanti KORIDORA PARALEL, derinlik DUVARA DIK
    Yani bir raf birimi: genislik=raf_g (koridor boyunca), derinlik=1.1m (duvara dogru)
    """
    # Kullanilabilir alan
    if g_duvar in ['alt','ust']:
        ef_uzun = uzunluk - kb2*2        # koridorun uzundugu taraf
        ef_gen  = genislik - kb2*2 - g_bosluk  # koridorun genisligi
    else:
        ef_uzun = uzunluk - kb2*2 - g_bosluk
        ef_gen  = genislik - kb2*2

    ef_uzun = max(ef_uzun, 0.1)
    ef_gen  = max(ef_gen, 0.1)

    # Bir raf satirinin depo uzunluguna kac adet sigdigi
    # Raf birimi: raf_g genislikte (koridora paralel yatay baglanti)
    raf_basi = max(1, int(ef_uzun / raf_g))

    # ---- SECENEK 1: I - Paralel Siralar ----
    # Koridorlar arasi: her sira 1 derinlik (1.1m) + koridor
    satir_1 = max(1, int(ef_gen / (DERINLIK + koridor)))
    toplam_1 = satir_1 * raf_basi
    kalan_1 = ef_gen - satir_1*(DERINLIK + koridor)

    # ---- SECENEK 2: I - Sirt Sirta Ortada ----
    # Cift sira: 2*1.1=2.2m + her iki yaninda koridor
    cift_derinlik = DERINLIK * 2
    cift_sayisi = max(0, int(ef_gen / (cift_derinlik + koridor)))
    tek_kalan_alan = ef_gen - cift_sayisi*(cift_derinlik + koridor)
    tek_sayisi = max(0, int(tek_kalan_alan / (DERINLIK + koridor)))
    toplam_2 = (cift_sayisi*2 + tek_sayisi) * raf_basi
    kalan_2 = tek_kalan_alan - tek_sayisi*(DERINLIK+koridor)

    # ---- SECENEK 3: U - Kenarlara + Ortaya ----
    # Sol ve sag duvara: derinlik=1.1m (duvara dik)
    # Kalan ortaya: sirt sirta ciftler
    yan_alan = DERINLIK  # her yan raf 1.1m yer kaplar
    # Raf uzunlugu boyunca kac raf: raf_basi (ayni)
    # Orta alan genisligi:
    orta_gen = ef_gen - yan_alan*2 - koridor*2
    if orta_gen >= cift_derinlik + koridor:
        orta_cift = max(0, int(orta_gen / (cift_derinlik + koridor)))
    else:
        orta_cift = 0
    orta_kalan = orta_gen - orta_cift*(cift_derinlik+koridor) if orta_gen > 0 else 0
    orta_tek = max(0, int(orta_kalan / (DERINLIK+koridor))) if orta_kalan > 0 else 0

    # Sol ve sag: raf_basi adet her biri (uzunluk boyunca)
    yan_raf = raf_basi * 2  # sol + sag
    orta_raf = (orta_cift*2 + orta_tek) * raf_basi
    toplam_3 = yan_raf + orta_raf

    return [
        {
            'tip': 'I_paralel', 'toplam': toplam_1,
            'satir': satir_1, 'raf_basi': raf_basi, 'kalan': round(kalan_1,2),
            'ef_uzun': ef_uzun, 'ef_gen': ef_gen
        },
        {
            'tip': 'I_sirt', 'toplam': toplam_2,
            'cift': cift_sayisi, 'tek': tek_sayisi, 'raf_basi': raf_basi,
            'kalan': round(kalan_2,2), 'ef_uzun': ef_uzun, 'ef_gen': ef_gen
        },
        {
            'tip': 'U_orta', 'toplam': toplam_3,
            'yan_raf': raf_basi, 'orta_cift': orta_cift, 'orta_tek': orta_tek,
            'raf_basi': raf_basi, 'orta_gen': orta_gen,
            'ef_uzun': ef_uzun, 'ef_gen': ef_gen
        },
    ]

def ciz_raf_birimi(draw, rx1, ry1, rx2, ry2):
    """Tek bir raf birimini ciz. Yatay baglanti uzun kenarda, derinlik kisa kenarda."""
    draw.rectangle([rx1, ry1, rx2, ry2], fill='#0a1628')
    draw.line([rx1, ry1, rx2, ry2], fill='#2a2a40', width=1)
    draw.line([rx2, ry1, rx1, ry2], fill='#2a2a40', width=1)
    draw.rectangle([rx1, ry1, rx2, ry2], outline='#404060', width=1)
    # Yatay baglanti - uzun kenar (sol ve sag)
    draw.line([rx1, ry1+4, rx1, ry2-4], fill='#ff8c42', width=3)
    draw.line([rx2, ry1+4, rx2, ry2-4], fill='#ff8c42', width=3)
    # Derinlik - kisa kenar (ust ve alt)
    draw.line([rx1+4, ry1, rx2-4, ry1], fill='#4ade80', width=2)
    draw.line([rx1+4, ry2, rx2-4, ry2], fill='#4ade80', width=2)
    # Dikmeler - 4 kose
    r = 4
    for px, py in [(rx1,ry1),(rx2,ry1),(rx1,ry2),(rx2,ry2)]:
        draw.ellipse([px-r,py-r,px+r,py+r], fill='#4a9eff', outline='white', width=1)

def olcu_y(draw, x1, x2, y, txt, font, renk):
    draw.line([x1,y,x2,y], fill=renk, width=1)
    draw.line([x1,y-4,x1,y+4], fill=renk, width=2)
    draw.line([x2,y-4,x2,y+4], fill=renk, width=2)
    draw.text(((x1+x2)//2, y-5), txt, fill=renk, font=font, anchor='mb')

def olcu_d(draw, x, y1, y2, txt, font, renk):
    draw.line([x,y1,x,y2], fill=renk, width=1)
    draw.line([x-4,y1,x+4,y1], fill=renk, width=2)
    draw.line([x-4,y2,x+4,y2], fill=renk, width=2)
    draw.text((x+5, (y1+y2)//2), txt, fill=renk, font=font, anchor='lm')

def teknik_ciz(d, lang, sec, sira, toplam_sira):
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
    g_gen    = d.get('giris_genislik', 3.0)
    tip      = sec['tip']

    if g_duvar in ['alt','ust']:
        yukleme_m2 = round(uzunluk * g_bosluk, 1)
        yukleme_en, yukleme_boy = uzunluk, g_bosluk
    else:
        yukleme_m2 = round(genislik * g_bosluk, 1)
        yukleme_en, yukleme_boy = g_bosluk, genislik

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
    AGRI   = '#505070'
    SARI   = '#ffd700'
    SINIR  = '#00b4d8'
    MOR    = '#c084fc'
    YESIL2 = '#22c55e'

    tip_adi = {
        'I_paralel': ('I — Paralel Siralar', 'I — Параллельные ряды'),
        'I_sirt':    ('I — Sirt Sirta + Tek', 'I — Спина к спине'),
        'U_orta':    ('U — Kenara + Ortaya', 'U — Стены + Центр'),
    }

    INFO_H = 155
    pl, pt, pr, pb = 80, 55, 125, INFO_H + 45
    pw = W - pl - pr
    ph = H - pt - pb
    ox, oy = pl, pt
    sx = pw / uzunluk
    sy = ph / genislik

    # Baslik
    draw.rectangle([0,0,W,42], fill='#161b22')
    t_ad = tip_adi.get(tip, (tip,tip))[1 if lang=='ru' else 0]
    if lang == 'tr':
        baslik = f"SECENEK {sira}/{toplam_sira}  |  {t_ad}  |  {sec['toplam']} raf"
    else:
        baslik = f"ВАРИАНТ {sira}/{toplam_sira}  |  {t_ad}  |  {sec['toplam']} стелл."
    draw.text((W//2,21), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo siniri
    draw.rectangle([ox,oy,ox+pw,oy+ph], outline=SINIR, width=3)
    draw.rectangle([ox+2,oy+2,ox+pw-2,oy+ph-2], outline='#1a3a5c', width=1)

    # Kapi konumu
    G = max(int(g_gen*sx), 30)
    kapi_lbl = "G/C" if lang=='tr' else "В/В"
    gx = gy = 0
    if g_duvar in ['alt','ust']:
        if g_konum=='orta': gx=ox+pw//2
        elif g_konum=='sol': gx=ox+int(g_mesafe*sx)+G//2
        else: gx=ox+pw-int(g_mesafe*sx)-G//2
    else:
        if g_konum=='orta': gy=oy+ph//2
        elif g_konum=='ust': gy=oy+int(g_mesafe*sy)+G//2
        else: gy=oy+ph-int(g_mesafe*sy)-G//2

    bp_y = int(g_bosluk*sy)
    bp_x = int(g_bosluk*sx)
    zona = "YUKLEME/BOSALTMA" if lang=='tr' else "ЗОНА ПОГРУЗКИ"

    if g_duvar=='alt':
        draw.rectangle([ox+3,oy+ph-bp_y,ox+pw-3,oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw//2,oy+ph-bp_y//2-8), zona, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw//2,oy+ph-bp_y//2+8), f"{yukleme_en}×{yukleme_boy}m={yukleme_m2}m²", fill=YESIL2, font=fb, anchor='mm')
        olcu_d(draw, ox+pw+8, oy+ph-bp_y, oy+ph, f"{g_bosluk}m", fsm, YESIL2)
        draw.line([gx-G//2,oy+ph,gx+G//2,oy+ph], fill=SARI, width=8)
        draw.text((gx,oy+ph+9), kapi_lbl, fill=SARI, font=fsm, anchor='mt')
        olcu_y(draw, gx-G//2, gx+G//2, oy+ph+24, f"{g_gen}m", fsm, SARI)
        if g_mesafe>0 and g_konum!='orta':
            if g_konum=='sol': olcu_y(draw, ox, gx-G//2, oy+ph+38, f"{g_mesafe}m", fsm, BEYAZ)
            else: olcu_y(draw, gx+G//2, ox+pw, oy+ph+38, f"{g_mesafe}m", fsm, BEYAZ)
    elif g_duvar=='ust':
        draw.rectangle([ox+3,oy+3,ox+pw-3,oy+bp_y], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw//2,oy+bp_y//2-8), zona, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw//2,oy+bp_y//2+8), f"{yukleme_en}×{yukleme_boy}m={yukleme_m2}m²", fill=YESIL2, font=fb, anchor='mm')
        olcu_d(draw, ox+pw+8, oy, oy+bp_y, f"{g_bosluk}m", fsm, YESIL2)
        draw.line([gx-G//2,oy,gx+G//2,oy], fill=SARI, width=8)
        draw.text((gx,oy-9), kapi_lbl, fill=SARI, font=fsm, anchor='mb')
        olcu_y(draw, gx-G//2, gx+G//2, oy-22, f"{g_gen}m", fsm, SARI)
    elif g_duvar=='sol':
        draw.rectangle([ox+3,oy+3,ox+bp_x,oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+bp_x//2,oy+ph//2-8), zona, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+bp_x//2,oy+ph//2+8), f"{yukleme_en}×{yukleme_boy}m={yukleme_m2}m²", fill=YESIL2, font=fb, anchor='mm')
        olcu_y(draw, ox, ox+bp_x, oy+ph+8, f"{g_bosluk}m", fsm, YESIL2)
        draw.line([ox,gy-G//2,ox,gy+G//2], fill=SARI, width=8)
        draw.text((ox-8,gy), kapi_lbl, fill=SARI, font=fsm, anchor='rm')
        olcu_d(draw, ox-35, gy-G//2, gy+G//2, f"{g_gen}m", fsm, SARI)
    else:
        draw.rectangle([ox+pw-bp_x,oy+3,ox+pw-3,oy+ph-3], fill='#052e16', outline=YESIL2, width=2)
        draw.text((ox+pw-bp_x//2,oy+ph//2-8), zona, fill=YESIL2, font=fsm, anchor='mm')
        draw.text((ox+pw-bp_x//2,oy+ph//2+8), f"{yukleme_en}×{yukleme_boy}m={yukleme_m2}m²", fill=YESIL2, font=fb, anchor='mm')
        olcu_y(draw, ox+pw-bp_x, ox+pw, oy+ph+8, f"{g_bosluk}m", fsm, YESIL2)
        draw.line([ox+pw,gy-G//2,ox+pw,gy+G//2], fill=SARI, width=8)
        draw.text((ox+pw+8,gy), kapi_lbl, fill=SARI, font=fsm, anchor='lm')
        olcu_d(draw, ox+pw+25, gy-G//2, gy+G//2, f"{g_gen}m", fsm, SARI)

    # RAF ALANI SINIRI
    rax1 = ox+int(kb2*sx); ray1 = oy+int(kb2*sy)
    rax2 = ox+pw-int(kb2*sx); ray2 = oy+ph-int(kb2*sy)
    if g_duvar=='alt':   ray2 -= bp_y
    elif g_duvar=='ust': ray1 += bp_y
    elif g_duvar=='sol': rax1 += bp_x
    else:                rax2 -= bp_x

    # Raf birimlerini hesapla ve ciz
    # Raf birimi: raf_g genislik (koridora paralel = uzunluk boyunca)
    #             DERINLIK derinlik (duvara dik = genislik boyunca)
    # Piksel karsiligi:
    raf_g_px    = int(raf_g * sx)       # raf genisligi piksel (uzunluk yonunde)
    derinlik_px = int(DERINLIK * sy)    # derinlik piksel (genislik yonunde)
    koridor_px  = int(koridor * sy)     # koridor piksel (genislik yonunde)

    raflar = []
    dikme_say = 0
    yatay_say = 0

    ef_uzun = sec['ef_uzun']
    ef_gen  = sec['ef_gen']
    raf_basi = sec['raf_basi']

    if tip == 'I_paralel':
        satir = sec['satir']
        for s in range(satir):
            # Her sira: derinlik_px yuksekliginde, raf_g_px genisliginde
            ry1_s = ray1 + int(s*(DERINLIK+koridor)*sy)
            ry2_s = ry1_s + derinlik_px
            for i in range(raf_basi):
                rx1_r = rax1 + int(i*raf_g*sx)
                rx2_r = rx1_r + raf_g_px - 1
                if rx2_r > rax2: break
                raflar.append((rx1_r, ry1_s, rx2_r, ry2_s))
            # Etiket
            draw.text((ox+pw+5, (ry1_s+ry2_s)//2), f"S{s+1}", fill=BEYAZ, font=fsm, anchor='lm')
            if s > 0:
                prev_ry2 = ray1 + int((s-1)*(DERINLIK+koridor)*sy) + derinlik_px
                olcu_d(draw, ox+pw+5, prev_ry2, ry1_s, f"{koridor}m", fsm, MOR)
        # Olcu: raf genisligi
        if raf_basi > 0:
            olcu_y(draw, rax1, rax1+raf_g_px, ray1-14, f"{raf_g}m", fsm, MOR)
        # Olcu: derinlik
        olcu_d(draw, rax1-18, ray1, ray1+derinlik_px, f"{DERINLIK}m", fsm, '#4ade80')

    elif tip == 'I_sirt':
        # Cift siralar (sirt sirta)
        y_pos = ray1
        grup_no = 0
        # Cift gruplar
        for _ in range(sec['cift']):
            # Ilk sira
            ry1_s = y_pos
            ry2_s = ry1_s + derinlik_px
            for i in range(raf_basi):
                rx1_r = rax1+int(i*raf_g*sx); rx2_r=rx1_r+raf_g_px-1
                if rx2_r>rax2: break
                raflar.append((rx1_r,ry1_s,rx2_r,ry2_s))
            # Ikinci sira (sirt sirta)
            ry1_s2 = ry2_s
            ry2_s2 = ry1_s2 + derinlik_px
            for i in range(raf_basi):
                rx1_r=rax1+int(i*raf_g*sx); rx2_r=rx1_r+raf_g_px-1
                if rx2_r>rax2: break
                raflar.append((rx1_r,ry1_s2,rx2_r,ry2_s2))
            draw.text((ox+pw+5,(ry1_s+ry2_s2)//2), f"G{grup_no+1}", fill=BEYAZ, font=fsm, anchor='lm')
            olcu_d(draw, ox+pw+5, ry1_s, ry2_s2, f"{DERINLIK*2}m", fsm, MOR)
            y_pos = ry2_s2 + koridor_px
            grup_no += 1
        # Tek siralar
        for t in range(sec['tek']):
            ry1_s=y_pos; ry2_s=ry1_s+derinlik_px
            for i in range(raf_basi):
                rx1_r=rax1+int(i*raf_g*sx); rx2_r=rx1_r+raf_g_px-1
                if rx2_r>rax2: break
                raflar.append((rx1_r,ry1_s,rx2_r,ry2_s))
            draw.text((ox+pw+5,(ry1_s+ry2_s)//2), f"T{t+1}", fill=BEYAZ, font=fsm, anchor='lm')
            y_pos = ry2_s + koridor_px
        if raf_basi>0:
            olcu_y(draw, rax1, rax1+raf_g_px, ray1-14, f"{raf_g}m", fsm, MOR)
        olcu_d(draw, rax1-18, ray1, ray1+derinlik_px, f"{DERINLIK}m", fsm, '#4ade80')

    elif tip == 'U_orta':
        # Sol duvara bitisik
        sol_ry1 = ray1; sol_ry2 = ray1+derinlik_px
        for i in range(raf_basi):
            rx1_r=rax1+int(i*raf_g*sx); rx2_r=rx1_r+raf_g_px-1
            if rx2_r>rax2: break
            raflar.append((rx1_r, sol_ry1, rx2_r, sol_ry2))
        draw.text((ox+pw+5,(sol_ry1+sol_ry2)//2), "Sol" if lang=='tr' else "Лев", fill=BEYAZ, font=fsm, anchor='lm')

        # Sag duvara bitisik
        sag_ry2 = ray2; sag_ry1 = ray2-derinlik_px
        for i in range(raf_basi):
            rx1_r=rax1+int(i*raf_g*sx); rx2_r=rx1_r+raf_g_px-1
            if rx2_r>rax2: break
            raflar.append((rx1_r, sag_ry1, rx2_r, sag_ry2))
        draw.text((ox+pw+5,(sag_ry1+sag_ry2)//2), "Sag" if lang=='tr' else "Пра", fill=BEYAZ, font=fsm, anchor='lm')

        # Koridor olcusu
        olcu_d(draw, ox+pw+5, sol_ry2, sol_ry2+koridor_px, f"{koridor}m", fsm, MOR)
        olcu_d(draw, ox+pw+5, sag_ry1-koridor_px, sag_ry1, f"{koridor}m", fsm, MOR)

        # Orta alan: cift ve tek siralar
        orta_y = sol_ry2 + koridor_px
        orta_bitis = sag_ry1 - koridor_px

        for _ in range(sec['orta_cift']):
            if orta_y + derinlik_px*2 > orta_bitis: break
            ry1_s=orta_y; ry2_s=ry1_s+derinlik_px
            for i in range(raf_basi):
                rx1_r=rax1+int(i*raf_g*sx); rx2_r=rx1_r+raf_g_px-1
                if rx2_r>rax2: break
                raflar.append((rx1_r,ry1_s,rx2_r,ry2_s))
            ry1_s2=ry2_s; ry2_s2=ry1_s2+derinlik_px
            for i in range(raf_basi):
                rx1_r=rax1+int(i*raf_g*sx); rx2_r=rx1_r+raf_g_px-1
                if rx2_r>rax2: break
                raflar.append((rx1_r,ry1_s2,rx2_r,ry2_s2))
            orta_y = ry2_s2 + koridor_px

        for _ in range(sec['orta_tek']):
            if orta_y + derinlik_px > orta_bitis: break
            ry1_s=orta_y; ry2_s=ry1_s+derinlik_px
            for i in range(raf_basi):
                rx1_r=rax1+int(i*raf_g*sx); rx2_r=rx1_r+raf_g_px-1
                if rx2_r>rax2: break
                raflar.append((rx1_r,ry1_s,rx2_r,ry2_s))
            orta_y = ry2_s + koridor_px

        if raf_basi>0:
            olcu_y(draw, rax1, rax1+raf_g_px, ray1-14, f"{raf_g}m", fsm, MOR)
        olcu_d(draw, rax1-18, ray1, ray1+derinlik_px, f"{DERINLIK}m", fsm, '#4ade80')

    # Raflari ciz
    for r in raflar:
        ciz_raf_birimi(draw, r[0], r[1], r[2], r[3])

    dikme_say = len(raflar) * 4
    yatay_say = len(raflar) * kat * 2
    derinlik_say = len(raflar) * 2

    # Ana olcular
    olcu_y(draw, ox, ox+pw, oy-20, f"{uzunluk}m", fn, BEYAZ)
    olcu_d(draw, ox-20, oy, oy+ph, f"{genislik}m", fn, BEYAZ)

    # ALT BILGI
    iy = H-INFO_H
    draw.rectangle([0,iy,W,H], fill='#161b22')
    draw.line([0,iy,W,iy], fill='#404060', width=2)

    lx,ly = 20, iy+14
    if lang=='tr':
        draw.text((lx,ly), "MALZEME LİSTESİ", fill=SARI, font=fb); ly+=22
        draw.text((lx,ly), "● Dikme:", fill='#4a9eff', font=fb)
        draw.text((lx+105,ly), f"1 adet={raf_yuk}m  |  {dikme_say} adet  |  Toplam: {round(dikme_say*raf_yuk,1)}m", fill=BEYAZ, font=fn); ly+=22
        draw.text((lx,ly), "━ Yatay Bag.:", fill='#ff8c42', font=fb)
        draw.text((lx+105,ly), f"1 adet={raf_g}m  |  {yatay_say} adet  |  Toplam: {round(yatay_say*raf_g,1)}m", fill=BEYAZ, font=fn); ly+=22
        draw.text((lx,ly), "| Derinlik:", fill='#4ade80', font=fb)
        draw.text((lx+105,ly), f"1 adet=1.10m  |  {derinlik_say} adet  |  Toplam: {round(derinlik_say*1.1,1)}m", fill=BEYAZ, font=fn); ly+=22
        draw.text((lx,ly), "▦ Yukleme:", fill='#22c55e', font=fb)
        draw.text((lx+105,ly), f"{yukleme_en}×{yukleme_boy}m = {yukleme_m2} m²", fill='#22c55e', font=fn); ly+=22
        draw.text((lx,ly), "↔ Koridor:", fill='#c084fc', font=fb)
        draw.text((lx+105,ly), f"{koridor}m  |  Kapi: {g_gen}m  |  Kat: {kat}", fill=BEYAZ, font=fn)
    else:
        draw.text((lx,ly), "СПИСОК МАТЕРИАЛОВ", fill=SARI, font=fb); ly+=22
        draw.text((lx,ly), "● Стойка:", fill='#4a9eff', font=fb)
        draw.text((lx+95,ly), f"1 шт={raf_yuk}м  |  {dikme_say} шт  |  Итого: {round(dikme_say*raf_yuk,1)}м", fill=BEYAZ, font=fn); ly+=22
        draw.text((lx,ly), "━ Балка:", fill='#ff8c42', font=fb)
        draw.text((lx+95,ly), f"1 шт={raf_g}м  |  {yatay_say} шт  |  Итого: {round(yatay_say*raf_g,1)}м", fill=BEYAZ, font=fn); ly+=22
        draw.text((lx,ly), "| Глубина:", fill='#4ade80', font=fb)
        draw.text((lx+95,ly), f"1 шт=1.10м  |  {derinlik_say} шт  |  Итого: {round(derinlik_say*1.1,1)}м", fill=BEYAZ, font=fn); ly+=22
        draw.text((lx,ly), "▦ Зона:", fill='#22c55e', font=fb)
        draw.text((lx+95,ly), f"{yukleme_en}×{yukleme_boy}м = {yukleme_m2} м²", fill='#22c55e', font=fn); ly+=22
        draw.text((lx,ly), "↔ Проход:", fill='#c084fc', font=fb)
        draw.text((lx+95,ly), f"{koridor}м  |  Ворота: {g_gen}м  |  Ярусов: {kat}", fill=BEYAZ, font=fn)

    rx2b,ry2b = W//2+20, iy+14
    if lang=='tr':
        draw.text((rx2b,ry2b), "ÖZET", fill=SARI, font=fb); ry2b+=22
        for k,v in [("Toplam Raf",str(sec['toplam'])),("Kat",str(kat)),
                    ("Raf Yuk.",f"{raf_yuk}m"),("Depo",f"{uzunluk}×{genislik}m"),
                    ("Koridor",d['koridor_tipi'])]:
            draw.text((rx2b,ry2b), f"{k}:", fill=AGRI, font=fn)
            draw.text((rx2b+165,ry2b), v, fill=BEYAZ, font=fb); ry2b+=22
    else:
        draw.text((rx2b,ry2b), "СВОДКА", fill=SARI, font=fb); ry2b+=22
        for k,v in [("Стеллажей",str(sec['toplam'])),("Ярусов",str(kat)),
                    ("Высота",f"{raf_yuk}м"),("Склад",f"{uzunluk}×{genislik}м"),
                    ("Проход",d['koridor_tipi'])]:
            draw.text((rx2b,ry2b), f"{k}:", fill=AGRI, font=fn)
            draw.text((rx2b+165,ry2b), v, fill=BEYAZ, font=fb); ry2b+=22

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150,150))
    buf.seek(0)
    return buf

# ---- HANDLERS ----

async def baslat(update, context):
    context.user_data.clear()
    await update.message.reply_text("Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce","🇷🇺 Russkiy"]]))
    return LANG

async def lang_sec(update, context):
    t = update.message.text
    context.user_data['lang'] = 'ru' if "Russkiy" in t else 'tr'
    lang = get_lang(context)
    await update.message.reply_text(
        "📏 Depo uzunlugu (m):\nOrnek: 20" if lang=='tr' else "📏 Длина склада (м):\nПример: 20",
        reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['uzunluk'] = float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Depo genisligi (m):\nOrnek: 12" if lang=='tr' else "📐 Ширина склада (м):\nПример: 12")
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return UZUNLUK

async def genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',','.'))
        await update.message.reply_text("📏 Depo yuksekligi (m):\nOrnek: 6" if lang=='tr' else "📏 Высота склада (м):\nПример: 6")
        return DEPO_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GENISLIK

async def depo_yuk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['depo_yukseklik'] = float(update.message.text.replace(',','.'))
        if lang=='tr':
            await update.message.reply_text("🚪 Giris kapisi hangi duvarda?",
                reply_markup=kb([["Alt duvar","Ust duvar"],["Sol duvar","Sag duvar"]]))
        else:
            await update.message.reply_text("🚪 На какой стене вход?",
                reply_markup=kb([["Нижняя стена","Верхняя стена"],["Левая стена","Правая стена"]]))
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
    if lang=='tr':
        await update.message.reply_text("🚪 Kapinin konumu?",
            reply_markup=kb([["Sol yakin","Orta","Sag yakin"]]))
    else:
        await update.message.reply_text("🚪 Где именно вход?",
            reply_markup=kb([["Левее","По центру","Правее"]]))
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
        await update.message.reply_text("🚪 Kapi genisligi (m):\nOrnek: 3" if lang=='tr' else "🚪 Ширина ворот (м):\nПример: 3",
            reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_GENISLIK
    else:
        await update.message.reply_text("🚪 Koseden kac metre?\nOrnek: 2" if lang=='tr' else "🚪 Расстояние от угла (м)?\nПример: 2",
            reply_markup=ReplyKeyboardRemove())
        return GIRIS_MESAFE

async def giris_mesafe_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',','.'))
        await update.message.reply_text("🚪 Kapi genisligi (m):\nOrnek: 3" if lang=='tr' else "🚪 Ширина ворот (м):\nПример: 3",
            reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_MESAFE

async def giris_genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_genislik'] = float(update.message.text.replace(',','.'))
        await update.message.reply_text("🏗 Yukleme/bosaltma alani (m):\nOrnek: 3" if lang=='tr' else "🏗 Зона погрузки/разгрузки (м):\nПример: 3",
            reply_markup=kb([["2","3","4","5"]]))
        return GIRIS_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_GENISLIK

async def giris_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_bosluk'] = float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Raf-duvar arasi bosluk?\n0=bitisik" if lang=='tr' else "📐 Отступ от стен?\n0=вплотную",
            reply_markup=kb([["0","0.3","0.5","1"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_BOSLUK

async def kenar_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kenar_bosluk'] = float(update.message.text.replace(',','.'))
        await update.message.reply_text("🚦 Koridor tipi?\nForklift 3m | Transpalet 2m | El 1.2m" if lang=='tr' else "🚦 Тип прохода?\nПогрузчик 3м | Транспалет 2м | Ручной 1.2м",
            reply_markup=kb([["Forklift","Transpalet","El ile" if lang=='tr' else "Ruchnoy"]]))
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
    await update.message.reply_text("📦 Raf basina palet?\n1=0.95m  2=1.85m\n3=2.70m  4=3.60m" if lang=='tr' else "📦 Паллет на ряд?\n1=0.95м  2=1.85м\n3=2.70м  4=3.60м",
        reply_markup=kb([["1","2"],["3","4"]]))
    return PALET

async def palet_h(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet'] = v
        await update.message.reply_text("🏗 Kat sayisi?\nOrnek: 3" if lang=='tr' else "🏗 Количество ярусов?\nПример: 3",
            reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1-4 girin." if lang=='tr' else "Введите 1-4.")
        return PALET

async def kat_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kat'] = int(update.message.text)
        await update.message.reply_text("📏 Raf yuksekligi (m)?\nOrnek: 5" if lang=='tr' else "📏 Высота стеллажа (м)?\nПример: 5")
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
        kb2     = d.get('kenar_bosluk',0)

        secenekler = hesapla_secenekler(d['uzunluk'], d['genislik'], raf_g, koridor, kb2, d['giris_duvar'], d['giris_bosluk'])
        secenekler.sort(key=lambda x: x['toplam'], reverse=True)

        await update.message.reply_text(
            "⏳ 3 secenek hazirlaniyor..." if lang=='tr' else "⏳ Готовлю 3 варианта...",
            reply_markup=ReplyKeyboardRemove())

        for i, sec in enumerate(secenekler):
            resim = teknik_ciz(d, lang, sec, i+1, len(secenekler))
            tip_tr = {'I_paralel':'I-Paralel','I_sirt':'I-Sirt Sirta','U_orta':'U-Kenara+Ortaya'}
            tip_ru = {'I_paralel':'I-Параллельные','I_sirt':'I-Спина к спине','U_orta':'U-Стены+Центр'}
            t_ad = tip_ru.get(sec['tip'],sec['tip']) if lang=='ru' else tip_tr.get(sec['tip'],sec['tip'])
            if lang=='tr':
                cap = f"{'⭐ EN İYİ — ' if i==0 else ''}{i+1}. SECENEK: {t_ad}\nToplam raf: {sec['toplam']} adet"
            else:
                cap = f"{'⭐ ЛУЧШИЙ — ' if i==0 else ''}{i+1}. ВАРИАНТ: {t_ad}\nСтеллажей: {sec['toplam']} шт"
            await update.message.reply_photo(photo=resim, caption=cap)

        await update.message.reply_text(
            "✅ Tum secenekler hazir! Fiyat icin: /hesapla" if lang=='tr' else
            "✅ Все варианты готовы! Расчёт: /raschet")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

async def iptal(update, context):
    lang = get_lang(context)
    await update.message.reply_text("Iptal. /hesapla" if lang=='tr' else "Отменено. /raschet",
        reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start',baslat),CommandHandler('hesapla',baslat),CommandHandler('raschet',baslat)],
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
        fallbacks=[CommandHandler('iptal',iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
