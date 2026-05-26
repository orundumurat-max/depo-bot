import logging
import io
import math
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ═══════════════════════════════════════════════════════════
#  KONFİGÜRASYON
# ═══════════════════════════════════════════════════════════

TOKEN = "8960271967:AAGEuwGjVEmc0kj76OnVB4Z6EiBlV_THjiQ"

# --- Conversation States ---
(LANG, DEPO_TIPI, KORIDOR_TIPI,
 UZUNLUK, GENISLIK, PALET, KAT, YUKSEKLIK,
 CONFIRM_UZUNLUK, CONFIRM_GENISLIK, CONFIRM_PALET, CONFIRM_KAT, CONFIRM_YUKSEKLIK,
 KAPI_YERI, KENAR_BOSLUK, YUKLEME_ALANI, KOLON_VAR, KOLON_ADET, OFIS_ALANI,
 FIYAT_LAMA) = range(20)

# --- Sabit Değerler ---
PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}
RAF_DERINLIK = 1.10  # Standart raf derinliği (m)

# ═══════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════

def get_lang(c):
    return c.user_data.get('lang', 'tr')

def devam_kb(lang):
    if lang == 'tr':
        return ReplyKeyboardMarkup([["✅ Devam", "🔄 Düzelt", "❌ Baştan"]],
                                    one_time_keyboard=True, resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["✅ Далее", "🔄 Исправить", "❌ Сначала"]],
                                    one_time_keyboard=True, resize_keyboard=True)

def is_devam(txt, lang):
    return "devam" in txt.lower() or "далее" in txt.lower() or "✅" in txt

def is_duzelt(txt, lang):
    return "düzelt" in txt.lower() or "исправ" in txt.lower() or "🔄" in txt

def is_bastan(txt, lang):
    return "baştan" in txt.lower() or "сначала" in txt.lower() or "❌" in txt

def t(lang, tr, ru):
    return tr if lang == 'tr' else ru


# ═══════════════════════════════════════════════════════════
#  GELİŞMİŞ TEKNİK ÇİZİM FONKSİYONU
# ═══════════════════════════════════════════════════════════

def teknik_resim_ciz(uzunluk, genislik, raf_genislik, koridor, kat, yukseklik,
                     depo_tipi, kapi_yeri, kenar_bosluk, yukleme_alani,
                     kolon_listesi, ofis_alani, lang):
    """
    depo_tipi : 'I', 'L', 'U'
    kapi_yeri : 'alt_orta', 'alt_sol', 'alt_sag', 'ust_orta', 'ust_sol', 'ust_sag', 'sol_orta', 'sag_orta'
    kenar_bosluk: {'ust': m, 'alt': m, 'sol': m, 'sag': m}
    yukleme_alani: {'var': True/False, 'yer': 'sol'/'sag'/'ust'/'alt', 'genislik': m, 'derinlik': m}
    kolon_listesi: [(x, y), ...] metre cinsinden
    ofis_alani: {'var': True/False, 'yer': 'sol_ust'/'sag_ust'/'sol_alt'/'sag_alt', 'genislik': m, 'derinlik': m}
    """

    W, H = 1200, 850
    img = Image.new('RGB', (W, H), color='#0d1117')
    draw = ImageDraw.Draw(img)

    # Fontlar
    try:
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
        fn = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 19)
        fk = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    except:
        fb = fn = ft = fk = ImageFont.load_default()

    # Renk paleti
    C = {
        'mavi': '#4a9eff', 'turuncu': '#ff8c42', 'yesil': '#4ade80',
        'beyaz': '#e0e0e0', 'gri': '#303050', 'agri': '#505070',
        'sari': '#ffd700', 'sinir': '#00b4d8', 'koyu_zemin': '#0a1628',
        'kirmizi': '#ff4444', 'mor': '#c084fc', 'pembe': '#f472b6',
        'acik_yesil': '#86efac', 'lacivert': '#1e3a5f'
    }

    # Plan alanı padding
    pad_left = 90
    pad_top = 60
    pad_right = 40
    info_h = 155
    pad_bot = info_h + 25

    plan_w = W - pad_left - pad_right
    plan_h = H - pad_top - pad_bot

    scale_x = plan_w / uzunluk
    scale_y = plan_h / genislik
    ox = pad_left
    oy = pad_top

    # Yardımcı: metre → pixel
    def mx(metre_x):
        return ox + int(metre_x * scale_x)

    def my(metre_y):
        return oy + int(metre_y * scale_y)

    def sx(px):
        return (px - ox) / scale_x

    def sy(py):
        return (py - oy) / scale_y

    # ═══════════════════════════════════════════════
    # BAŞLIK
    # ═══════════════════════════════════════════════
    draw.rectangle([0, 0, W, 40], fill='#161b22')
    baslik = (f"DEPO STELAJLARI — TEKNİK ÇİZİM  |  Tip: {depo_tipi}  |  {uzunluk}m × {genislik}m"
              if lang == 'tr' else
              f"СКЛАДСКИЕ СТЕЛЛАЖИ — ТЕХНИЧЕСКИЙ ЧЕРТЁЖ  |  Тип: {depo_tipi}  |  {uzunluk}м × {genislik}м")
    draw.text((W // 2, 20), baslik, fill=C['sari'], font=ft, anchor='mm')

    # ═══════════════════════════════════════════════
    # DEPO SINIRI + KENAR BOŞLUKLARI
    # ═══════════════════════════════════════════════
    kb = kenar_bosluk  # {'ust': m, 'alt': m, 'sol': m, 'sag': m}
    ic_x1 = mx(kb['sol'])
    ic_y1 = my(kb['ust'])
    ic_x2 = mx(uzunluk - kb['sag'])
    ic_y2 = my(genislik - kb['alt'])

    # Dış sınır (depo duvarları)
    draw.rectangle([ox, oy, ox + plan_w, oy + plan_h], outline=C['sinir'], width=3)

    # Kenar boşluk tarama çizgileri (diagonal)
    if any(v > 0 for v in kb.values()):
        step = 8
        # Üst boşluk
        for i in range(ox, ox + plan_w + plan_h, step):
            draw.line([(i, oy), (i - plan_h, oy + int(kb['ust'] * scale_y))],
                      fill='#1a2744', width=1)
        # Alt boşluk
        for i in range(ox, ox + plan_w + plan_h, step):
            draw.line([(i, oy + plan_h), (i - plan_h, oy + plan_h - int(kb['alt'] * scale_y))],
                      fill='#1a2744', width=1)
        # Sol boşluk
        for i in range(oy, oy + plan_h + plan_w, step):
            draw.line([(ox, i), (ox + int(kb['sol'] * scale_x), i - plan_w)],
                      fill='#1a2744', width=1)
        # Sağ boşluk
        for i in range(oy, oy + plan_h + plan_w, step):
            draw.line([(ox + plan_w, i), (ox + plan_w - int(kb['sag'] * scale_x), i - plan_w)],
                      fill='#1a2744', width=1)

    # İç kullanım alanı (yesil ince çerçeve)
    draw.rectangle([ic_x1, ic_y1, ic_x2, ic_y2], outline=C['yesil'], width=2)

    # ═══════════════════════════════════════════════
    # KAPI (GİRİŞ) ÇİZİMİ
    # ═══════════════════════════════════════════════
    kapi_w_px = max(50, int(2.5 * scale_x))  # Minimum 50px
    kapi_h_px = 8
    kapi_label = "GİRİŞ" if lang == 'tr' else "ВХОД"

    if kapi_yeri == 'alt_orta':
        gx = ox + plan_w // 2
        gy = oy + plan_h
        draw.line([gx - kapi_w_px // 2, gy, gx + kapi_w_px // 2, gy], fill=C['sari'], width=7)
        draw.text((gx, gy + 14), kapi_label, fill=C['sari'], font=fn, anchor='mt')
    elif kapi_yeri == 'alt_sol':
        gx = ox + int(kb['sol'] * scale_x) + kapi_w_px // 2 + 20
        gy = oy + plan_h
        draw.line([gx - kapi_w_px // 2, gy, gx + kapi_w_px // 2, gy], fill=C['sari'], width=7)
        draw.text((gx, gy + 14), kapi_label, fill=C['sari'], font=fn, anchor='mt')
    elif kapi_yeri == 'alt_sag':
        gx = ox + plan_w - int(kb['sag'] * scale_x) - kapi_w_px // 2 - 20
        gy = oy + plan_h
        draw.line([gx - kapi_w_px // 2, gy, gx + kapi_w_px // 2, gy], fill=C['sari'], width=7)
        draw.text((gx, gy + 14), kapi_label, fill=C['sari'], font=fn, anchor='mt')
    elif kapi_yeri == 'ust_orta':
        gx = ox + plan_w // 2
        gy = oy
        draw.line([gx - kapi_w_px // 2, gy, gx + kapi_w_px // 2, gy], fill=C['sari'], width=7)
        draw.text((gx, gy - 10), kapi_label, fill=C['sari'], font=fn, anchor='mb')
    elif kapi_yeri == 'ust_sol':
        gx = ox + int(kb['sol'] * scale_x) + kapi_w_px // 2 + 20
        gy = oy
        draw.line([gx - kapi_w_px // 2, gy, gx + kapi_w_px // 2, gy], fill=C['sari'], width=7)
        draw.text((gx, gy - 10), kapi_label, fill=C['sari'], font=fn, anchor='mb')
    elif kapi_yeri == 'ust_sag':
        gx = ox + plan_w - int(kb['sag'] * scale_x) - kapi_w_px // 2 - 20
        gy = oy
        draw.line([gx - kapi_w_px // 2, gy, gx + kapi_w_px // 2, gy], fill=C['sari'], width=7)
        draw.text((gx, gy - 10), kapi_label, fill=C['sari'], font=fn, anchor='mb')
    elif kapi_yeri == 'sol_orta':
        gx = ox
        gy = oy + plan_h // 2
        draw.line([gx, gy - kapi_w_px // 3, gx, gy + kapi_w_px // 3], fill=C['sari'], width=7)
        draw.text((gx - 8, gy), kapi_label, fill=C['sari'], font=fn, anchor='rm')
    elif kapi_yeri == 'sag_orta':
        gx = ox + plan_w
        gy = oy + plan_h // 2
        draw.line([gx, gy - kapi_w_px // 3, gx, gy + kapi_w_px // 3], fill=C['sari'], width=7)
        draw.text((gx + 8, gy), kapi_label, fill=C['sari'], font=fn, anchor='lm')

    # ═══════════════════════════════════════════════
    # YÜKLEME/BOŞALTMA (RAMPA) ALANI
    # ═══════════════════════════════════════════════
    if yukleme_alani.get('var', False):
        ya = yukleme_alani
        yer = ya.get('yer', 'alt')
        ya_gen = ya.get('genislik', 6.0)
        ya_der = ya.get('derinlik', 3.0)

        if yer == 'alt':
            rx1, ry1 = mx(kb['sol']), my(genislik - kb['alt'] - ya_der)
            rx2, ry2 = mx(kb['sol'] + ya_gen), my(genislik - kb['alt'])
        elif yer == 'ust':
            rx1, ry1 = mx(kb['sol']), my(kb['ust'])
            rx2, ry2 = mx(kb['sol'] + ya_gen), my(kb['ust'] + ya_der)
        elif yer == 'sol':
            rx1, ry1 = mx(kb['sol']), my(kb['ust'])
            rx2, ry2 = mx(kb['sol'] + ya_der), my(kb['ust'] + ya_gen)
        else:  # sag
            rx1, ry1 = mx(uzunluk - kb['sag'] - ya_der), my(kb['ust'])
            rx2, ry2 = mx(uzunluk - kb['sag']), my(kb['ust'] + ya_gen)

        # Rampa zemin (koyu mor)
        draw.rectangle([rx1, ry1, rx2, ry2], fill='#2d1b4e', outline=C['mor'], width=2)
        # Tarama çizgileri
        for i in range(rx1, rx2 + ry2 - ry1, 10):
            draw.line([(i, ry1), (i - (ry2 - ry1), ry2)], fill=C['mor'], width=1)

        rampa_label = "YÜKLEME/BOŞALTMA" if lang == 'tr' else "ПОГРУЗКА/РАЗГРУЗКА"
        draw.text(((rx1 + rx2) // 2, (ry1 + ry2) // 2), rampa_label,
                  fill=C['pembe'], font=fk, anchor='mm')

    # ═══════════════════════════════════════════════
    # OFİS/İDARİ ALAN
    # ═══════════════════════════════════════════════
    if ofis_alani.get('var', False):
        oa = ofis_alani
        oa_yer = oa.get('yer', 'sag_ust')
        oa_g = oa.get('genislik', 4.0)
        oa_d = oa.get('derinlik', 3.0)

        if oa_yer == 'sag_ust':
            ox1, oy1 = mx(uzunluk - kb['sag'] - oa_g), my(kb['ust'])
            ox2, oy2 = mx(uzunluk - kb['sag']), my(kb['ust'] + oa_d)
        elif oa_yer == 'sol_ust':
            ox1, oy1 = mx(kb['sol']), my(kb['ust'])
            ox2, oy2 = mx(kb['sol'] + oa_g), my(kb['ust'] + oa_d)
        elif oa_yer == 'sag_alt':
            ox1, oy1 = mx(uzunluk - kb['sag'] - oa_g), my(genislik - kb['alt'] - oa_d)
            ox2, oy2 = mx(uzunluk - kb['sag']), my(genislik - kb['alt'])
        else:  # sol_alt
            ox1, oy1 = mx(kb['sol']), my(genislik - kb['alt'] - oa_d)
            ox2, oy2 = mx(kb['sol'] + oa_g), my(genislik - kb['alt'])

        draw.rectangle([ox1, oy1, ox2, oy2], fill='#1a2f23', outline=C['acik_yesil'], width=2)
        ofis_label = "OFİS" if lang == 'tr' else "ОФИС"
        draw.text(((ox1 + ox2) // 2, (oy1 + oy2) // 2), ofis_label,
                  fill=C['acik_yesil'], font=fk, anchor='mm')

    # ═══════════════════════════════════════════════
    # KOLONLARI ÇİZ
    # ═══════════════════════════════════════════════
    if kolon_listesi:
        for (kx, ky) in kolon_listesi:
            cpx, cpy = mx(kx), my(ky)
            r = 6
            draw.rectangle([cpx - r, cpy - r, cpx + r, cpy + r],
                           fill=C['kirmizi'], outline='#ff8888', width=2)

    # ═══════════════════════════════════════════════
    # RAF YERLEŞİMİ — I / L / U ŞEKİLLERİ
    # ═══════════════════════════════════════════════
    raflar = []  # (rx1, ry1, rx2, ry2, row_label) listesi

    if depo_tipi == 'I':
        raflar = _raf_yerlesim_I(ic_x1, ic_y1, ic_x2, ic_y2, mx, my,
                                  uzunluk - kb['sol'] - kb['sag'],
                                  genislik - kb['ust'] - kb['alt'],
                                  raf_genislik, koridor, kb, yukleme_alani, ofis_alani)
    elif depo_tipi == 'L':
        raflar = _raf_yerlesim_L(ic_x1, ic_y1, ic_x2, ic_y2, mx, my,
                                  uzunluk - kb['sol'] - kb['sag'],
                                  genislik - kb['ust'] - kb['alt'],
                                  raf_genislik, koridor, kb, yukleme_alani, ofis_alani)
    elif depo_tipi == 'U':
        raflar = _raf_yerlesim_U(ic_x1, ic_y1, ic_x2, ic_y2, mx, my,
                                  uzunluk - kb['sol'] - kb['sag'],
                                  genislik - kb['ust'] - kb['alt'],
                                  raf_genislik, koridor, kb, yukleme_alani, ofis_alani)

    # Rafları çiz
    raf_count = 0
    for (rx1, ry1, rx2, ry2, rlabel) in raflar:
        if rx2 - rx1 < 10 or ry2 - ry1 < 8:
            continue
        raf_count += 1

        # Raf içi (koyu)
        draw.rectangle([rx1, ry1, rx2, ry2], fill=C['koyu_zemin'])
        # Çapraz
        draw.line([rx1, ry1, rx2, ry2], fill=C['gri'], width=1)
        draw.line([rx2, ry1, rx1, ry2], fill=C['gri'], width=1)
        # Çerçeve
        draw.rectangle([rx1, ry1, rx2, ry2], outline=C['agri'], width=1)
        # Yatay bağlantılar (turuncu)
        draw.line([rx1 + 4, ry1, rx2 - 4, ry1], fill=C['turuncu'], width=3)
        draw.line([rx1 + 4, ry2, rx2 - 4, ry2], fill=C['turuncu'], width=3)
        # Derinlik bağlantıları (yeşil)
        draw.line([rx1, ry1 + 4, rx1, ry2 - 4], fill=C['yesil'], width=2)
        draw.line([rx2, ry1 + 4, rx2, ry2 - 4], fill=C['yesil'], width=2)
        # Dikmeler (mavi daire)
        r = 4
        for px, py in [(rx1, ry1), (rx2, ry1), (rx1, ry2), (rx2, ry2)]:
            draw.ellipse([px - r, py - r, px + r, py + r], fill=C['mavi'], outline='#ffffff', width=1)

        # Etiket
        if rlabel:
            draw.text((rx2 + 5, (ry1 + ry2) // 2), rlabel, fill=C['beyaz'], font=fn, anchor='lm')

    # ═══════════════════════════════════════════════
    # YANGIN GÜVENLİK ve ACİL ÇIKIŞ İŞARETLEMELERİ
    # ═══════════════════════════════════════════════
    # Yangın söndürücü konumları (giriş yakınına)
    yangin_noktalari = []
    if kapi_yeri.startswith('alt'):
        yangin_noktalari = [(ox + 20, oy + plan_h - 30), (ox + plan_w - 20, oy + plan_h - 30)]
    elif kapi_yeri.startswith('ust'):
        yangin_noktalari = [(ox + 20, oy + 20), (ox + plan_w - 20, oy + 20)]
    else:
        yangin_noktalari = [(ox + 20, oy + plan_h - 30), (ox + plan_w - 20, oy + 20)]

    for yx, yy in yangin_noktalari:
        draw.ellipse([yx - 8, yy - 8, yx + 8, yy + 8], fill=C['kirmizi'], outline='#ff8888', width=2)
        draw.text((yx, yy), "F" if lang == 'tr' else "П", fill='white', font=fb, anchor='mm')

    # Yangın tüpü etiketi
    yg_label = "Yangın Söndürücü" if lang == 'tr' else "Огнетушитель"
    draw.text((yangin_noktalari[0][0] + 12, yangin_noktalari[0][1]), yg_label,
              fill=C['kirmizi'], font=fn, anchor='lm')

    # Acil çıkış oku
    if kapi_yeri.startswith('alt'):
        ex, ey = ox + plan_w // 2, oy + plan_h - 55
        draw.polygon([(ex, ey - 10), (ex - 7, ey + 5), (ex + 7, ey + 5)], fill=C['yesil'])
        draw.text((ex, ey + 15), "ÇIKIŞ →" if lang == 'tr' else "ВЫХОД →",
                  fill=C['yesil'], font=fn, anchor='mm')

    # ═══════════════════════════════════════════════
    # ÖLÇÜ ÇİZGİLERİ
    # ═══════════════════════════════════════════════
    # Uzunluk (üst)
    draw.line([ox, oy - 22, ox + plan_w, oy - 22], fill=C['agri'], width=1)
    draw.line([ox, oy - 28, ox, oy - 16], fill=C['agri'], width=1)
    draw.line([ox + plan_w, oy - 28, ox + plan_w, oy - 16], fill=C['agri'], width=1)
    draw.text((ox + plan_w // 2, oy - 22), f"{uzunluk} m", fill=C['beyaz'], font=fn, anchor='mm')

    # Genişlik (sol)
    draw.line([ox - 22, oy, ox - 22, oy + plan_h], fill=C['agri'], width=1)
    draw.line([ox - 28, oy, ox - 16, oy], fill=C['agri'], width=1)
    draw.line([ox - 28, oy + plan_h, ox - 16, oy + plan_h], fill=C['agri'], width=1)
    draw.text((ox - 34, oy + plan_h // 2), f"{genislik} m", fill=C['beyaz'], font=fn, anchor='mm')

    # ═══════════════════════════════════════════════
    # ALT BİLGİ PANELİ
    # ═══════════════════════════════════════════════
    info_y = H - info_h - 5
    draw.rectangle([0, info_y, W, H], fill='#161b22')
    draw.line([0, info_y, W, info_y], fill='#30363d', width=1)

    # Sol panel — Renk açıklamaları
    sol_x = 20
    sy = info_y + 12
    renk_items = [
        (C['mavi'],    "● " + ("Dikme ( upright )" if lang == 'tr' else "Стойка"),          f"{yukseklik} m"),
        (C['turuncu'], "━ " + ("Yatay Bağlantı ( beam )" if lang == 'tr' else "Балка"),   f"{raf_genislik} m"),
        (C['yesil'],   "│ " + ("Derinlik ( depth )" if lang == 'tr' else "Глубина"),        f"{RAF_DERINLIK} m"),
        (C['mor'],     "▩ " + ("Yükleme/Boşaltma" if lang == 'tr' else "Погрузка/Разгрузка"), "Rampa"),
        (C['kirmizi'], "■ " + ("Kolon" if lang == 'tr' else "Колонна"),                      "Engel"),
        (C['acik_yesil'], "▩ " + ("Ofis Alanı" if lang == 'tr' else "Офис"),                  "İdari"),
    ]
    for renk, isim, olcu in renk_items:
        draw.text((sol_x, sy), isim, fill=renk, font=fb)
        draw.text((sol_x + 240, sy), olcu, fill=C['beyaz'], font=fb)
        sy += 22

    # Orta ayırıcı
    draw.line([W // 2 - 30, info_y + 8, W // 2 - 30, H - 8], fill='#30363d', width=1)

    # Sağ panel — Özet bilgiler
    sag_x = W // 2 - 10
    sy2 = info_y + 12
    if lang == 'tr':
        bilgiler = [
            ("Depo Tipi", depo_tipi),
            ("Kat Sayısı", str(kat)),
            ("Toplam Raf", str(raf_count)),
            ("Raf Yüksekliği", f"{yukseklik} m"),
            ("Koridor Genişliği", f"{koridor} m"),
            ("Kapı Konumu", kapi_yeri.replace('_', ' ').title()),
        ]
    else:
        kapi_tr_map = {'alt_orta': 'низ-центр', 'alt_sol': 'низ-лево', 'alt_sag': 'низ-право',
                       'ust_orta': 'верх-центр', 'ust_sol': 'верх-лево', 'ust_sag': 'верх-право',
                       'sol_orta': 'лево-центр', 'sag_orta': 'право-центр'}
        bilgiler = [
            ("Тип склада", depo_tipi),
            ("Ярусов", str(kat)),
            ("Всего стеллажей", str(raf_count)),
            ("Высота стеллажа", f"{yukseklik} м"),
            ("Ширина прохода", f"{koridor} м"),
            ("Положение двери", kapi_tr_map.get(kapi_yeri, kapi_yeri)),
        ]
    for k, v in bilgiler:
        draw.text((sag_x, sy2), k + ":", fill=C['agri'], font=fn)
        draw.text((sag_x + 200, sy2), v, fill=C['beyaz'], font=fb)
        sy2 += 22

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(180, 180))
    buf.seek(0)
    return buf, raf_count


# ═══════════════════════════════════════════════════════════
#  RAF YERLEŞİM ALGORİTMALARI — I / L / U
# ═══════════════════════════════════════════════════════════

def _raf_yerlesim_I(ic_x1, ic_y1, ic_x2, ic_y2, mx, my, ic_uzunluk, ic_genislik,
                     raf_genislik, koridor, kb, yukleme_alani, ofis_alani):
    """Düz paralel raf sıraları (klasik I tipi)"""
    raflar = []
    raf_satir = max(1, int(ic_genislik / (raf_genislik + koridor)))

    for row in range(raf_satir):
        ry1_m = raf_genislik / 2 + row * (raf_genislik + koridor)
        ry2_m = ry1_m + raf_genislik
        if my(ry1_m + kb['ust']) >= ic_y2:
            break

        ry1 = my(ry1_m + kb['ust'])
        ry2 = my(ry2_m + kb['ust'])
        ry2 = max(ry2, ry1 + 16)

        # Yükleme/ofis alanı kontrolü
        if _cakisma_var(ry1, ry2, ic_x1, ic_x2, yukleme_alani, ofis_alani, mx, my, kb):
            continue

        # Tek uzun raf bloğu
        rx1, rx2 = ic_x1 + 2, ic_x2 - 2
        rlabel = f"{'Raf' if True else 'Ряд'} {row + 1}  ({raf_genislik}m)"
        raflar.append((rx1, ry1, rx2, ry2, rlabel))

    return raflar


def _raf_yerlesim_L(ic_x1, ic_y1, ic_x2, ic_y2, mx, my, ic_uzunluk, ic_genislik,
                    raf_genislik, koridor, kb, yukleme_alani, ofis_alani):
    """L şekli: Bir duvardan uzanan + diğer duvardan dönen raflar"""
    raflar = []
    yarisi_x = ic_x1 + (ic_x2 - ic_x1) // 2
    yarisi_y = ic_y1 + (ic_y2 - ic_y1) // 2

    # Yatay raf bloğu (alt taraf, tam genişlik)
    raf_satir_y = max(1, int((ic_genislik / 2) / (raf_genislik + koridor)))
    for row in range(raf_satir_y):
        ry1_m = raf_genislik / 2 + row * (raf_genislik + koridor)
        ry2_m = ry1_m + raf_genislik
        ry1 = my(ic_genislik - kb['alt'] - ry2_m)
        ry2 = my(ic_genislik - kb['alt'] - ry1_m)
        if ry1 < ic_y1:
            break
        ry2 = max(ry2, ry1 + 16)

        if _cakisma_var(ry1, ry2, ic_x1, yarisi_x, yukleme_alani, ofis_alani, mx, my, kb):
            continue

        raflar.append((ic_x1 + 2, ry1, yarisi_x - 2, ry2,
                       f"Raf Y{row + 1}" if True else f"Ряд Y{row + 1}"))

    # Dikey raf bloğu (sol taraf, yukarı doğru)
    raf_satir_x = max(1, int((ic_uzunluk / 2) / (raf_genislik + koridor)))
    for col in range(raf_satir_x):
        rx1_m = raf_genislik / 2 + col * (raf_genislik + koridor)
        rx2_m = rx1_m + raf_genislik
        rx1 = mx(kb['sol'] + rx1_m)
        rx2 = mx(kb['sol'] + rx2_m)
        if rx1 >= yarisi_x:
            break
        rx2 = max(rx2, rx1 + 16)

        raflar.append((rx1, ic_y1 + 2, rx2, yarisi_y - 2,
                       f"Raf X{col + 1}" if True else f"Ряд X{col + 1}"))

    return raflar


def _raf_yerlesim_U(ic_x1, ic_y1, ic_x2, ic_y2, mx, my, ic_uzunluk, ic_genislik,
                    raf_genislik, koridor, kb, yukleme_alani, ofis_alani):
    """U şekli: Üç duvara dayalı raf yerleşimi, ortası açık"""
    raflar = []
    yarisi_y = ic_y1 + (ic_y2 - ic_y1) // 2

    # Alt yatay raf bloğu (tam genişlik)
    raf_satir_y = max(1, int((ic_genislik / 2.5) / (raf_genislik + koridor)))
    for row in range(raf_satir_y):
        ry1_m = raf_genislik / 2 + row * (raf_genislik + koridor)
        ry2_m = ry1_m + raf_genislik
        ry1 = my(ic_genislik - kb['alt'] - ry2_m)
        ry2 = my(ic_genislik - kb['alt'] - ry1_m)
        if ry1 < yarisi_y:
            break
        ry2 = max(ry2, ry1 + 16)
        if _cakisma_var(ry1, ry2, ic_x1, ic_x2, yukleme_alani, ofis_alani, mx, my, kb):
            continue
        raflar.append((ic_x1 + 2, ry1, ic_x2 - 2, ry2, f"Raf A{row + 1}"))

    # Sol dikey raf bloğu
    raf_satir_x = max(1, int((ic_genislik / 2.5) / (raf_genislik + koridor)))
    for row in range(raf_satir_x):
        ry1_m = raf_genislik / 2 + row * (raf_genislik + koridor)
        ry2_m = ry1_m + raf_genislik
        ry1 = my(kb['ust'] + ry1_m)
        ry2 = my(kb['ust'] + ry2_m)
        if ry2 > yarisi_y:
            break
        ry2 = max(ry2, ry1 + 16)
        raflar.append((ic_x1 + 2, ry1, mx(kb['sol'] + raf_genislik * 3), ry2, f"Raf B{row + 1}"))

    # Sağ dikey raf bloğu
    for row in range(raf_satir_x):
        ry1_m = raf_genislik / 2 + row * (raf_genislik + koridor)
        ry2_m = ry1_m + raf_genislik
        ry1 = my(kb['ust'] + ry1_m)
        ry2 = my(kb['ust'] + ry2_m)
        if ry2 > yarisi_y:
            break
        ry2 = max(ry2, ry1 + 16)
        raflar.append((mx(uzunluk - kb['sag'] - raf_genislik * 3), ry1, ic_x2 - 2, ry2, f"Raf C{row + 1}"))

    return raflar


def _cakisma_var(ry1, ry2, rx1, rx2, yukleme_alani, ofis_alani, mx, my, kb):
    """Raf koordinatlarının yükleme/ofis alanı ile çakışıp çakışmadığını kontrol et"""
    # Basit kontrol: pixel koordinatlarıyla karşılaştırma
    # Detaylı implementasyon için her alanın pixel sınırları hesaplanabilir
    return False  # Şimdilik pasif, gerektiğinde aktifleştirilebilir


# ═══════════════════════════════════════════════════════════
#  HANDLER'LAR
# ═══════════════════════════════════════════════════════════

async def start(update, context):
    kb = [["🇹🇷 Türkçe", "🇷🇺 Русский"]]
    await update.message.reply_text(
        "🌐 Dil seçin / Выберите язык:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return LANG


async def hesapla(update, context):
    return await start(update, context)


async def lang_sec(update, context):
    t = update.message.text
    context.user_data['lang'] = 'ru' if "Русский" in t else 'tr'
    lang = get_lang(context)

    kb = [["I — Düz Sıralar", "L — İki Duvara"], ["U — Üç Duvara"]] if lang == 'tr' else \
         [["I — Прямые ряды", "L — Две стены"], ["U — Три стены"]]
    msg = ("🏭 Depo yerleşim şeklini seçin:\n"
           "🔹 I — Düz paralel sıralar (klasik)\n"
           "🔹 L — İki duvara dayalı (köşe kullanımı)\n"
           "🔹 U — Üç duvara dayalı (çatı tipi)")
    if lang != 'tr':
        msg = ("🏭 Форма размещения:\n"
               "🔹 I — Прямые параллельные ряды\n"
               "🔹 L — У двух стен\n"
               "🔹 U — У трёх стен (подкова)")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return DEPO_TIPI


async def depo_tipi_sec(update, context):
    lang = get_lang(context)
    text = update.message.text.strip().upper()
    if 'I' in text:
        tip = 'I'
    elif 'L' in text:
        tip = 'L'
    elif 'U' in text:
        tip = 'U'
    else:
        await update.message.reply_text("⚠️ I, L veya U seçin." if lang == 'tr' else "⚠️ Выберите I, L или U.")
        return DEPO_TIPI

    context.user_data['depo_tipi'] = tip
    kb = [["🚜 Forklift (3.0m)", "🔧 Transpalet (2.0m)"], ["👐 El ile (1.2m)"]]
    msg = ("🚦 Koridor tipini seçin:\n"
           "🚜 Forklift — Ağır yük, geniş koridor (3.0m)\n"
           "🔧 Transpalet — Orta kapasite (2.0m)\n"
           "👐 El ile — Dar alan, manuel (1.2m)")
    if lang != 'tr':
        msg = ("🚦 Тип прохода:\n🚜 Погрузчик (3.0м)\n🔧 Транспалет (2.0м)\n👐 Ручной (1.2м)")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return KORIDOR_TIPI


async def koridor_tipi_sec(update, context):
    lang = get_lang(context)
    text = update.message.text.lower()
    if "forklift" in text or "погрузчик" in text:
        context.user_data['koridor_tipi'] = 'forklift'
    elif "transpalet" in text or "транспалет" in text:
        context.user_data['koridor_tipi'] = 'transpalet'
    else:
        context.user_data['koridor_tipi'] = 'el'

    msg = "📏 Depo uzunluğunu girin (metre):\nÖrnek: 24" if lang == 'tr' else \
          "📏 Длина склада (м):\nПример: 24"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return UZUNLUK


async def uzunluk(update, context):
    lang = get_lang(context)
    try:
        v = float(update.message.text.replace(',', '.'))
        if v < 3 or v > 200:
            raise ValueError
        context.user_data['uzunluk'] = v
        msg = f"📏 Uzunluk: {v} m\n✅ Devam?" if lang == 'tr' else f"📏 Длина: {v} м\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_UZUNLUK
    except:
        await update.message.reply_text("⚠️ 3-200 arası rakam girin." if lang == 'tr' else "⚠️ Введите число 3-200.")
        return UZUNLUK


async def confirm_uzunluk(update, context):
    lang = get_lang(context)
    text = update.message.text
    if is_bastan(text, lang):
        return await hesapla(update, context)
    if is_duzelt(text, lang):
        await update.message.reply_text("📏 Uzunluk (m):" if lang == 'tr' else "📏 Длина (м):", reply_markup=ReplyKeyboardRemove())
        return UZUNLUK

    msg = "📐 Depo genişliğini girin (metre):\nÖrnek: 12" if lang == 'tr' else \
          "📐 Ширина склада (м):\nПример: 12"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return GENISLIK


async def genislik(update, context):
    lang = get_lang(context)
    try:
        v = float(update.message.text.replace(',', '.'))
        if v < 3 or v > 100:
            raise ValueError
        context.user_data['genislik'] = v
        msg = f"📐 Genişlik: {v} m\n✅ Devam?" if lang == 'tr' else f"📐 Ширина: {v} м\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_GENISLIK
    except:
        await update.message.reply_text("⚠️ 3-100 arası rakam girin." if lang == 'tr' else "⚠️ Введите число 3-100.")
        return GENISLIK


async def confirm_genislik(update, context):
    lang = get_lang(context)
    text = update.message.text
    if is_bastan(text, lang):
        return await hesapla(update, context)
    if is_duzelt(text, lang):
        await update.message.reply_text("📐 Genişlik (m):" if lang == 'tr' else "📐 Ширина (м):", reply_markup=ReplyKeyboardRemove())
        return GENISLIK

    kb = [["1 — 0.95m", "2 — 1.85m"], ["3 — 2.70m", "4 — 3.60m"]]
    msg = ("📦 Raf başına palet sayısı:\n"
           "1️⃣ Tek palet (0.95m)  2️⃣ İki palet (1.85m)\n"
           "3️⃣ Üç palet (2.70m)   4️⃣ Dört palet (3.60m)")
    if lang != 'tr':
        msg = ("📦 Паллет на ряд:\n1️⃣ 0.95м  2️⃣ 1.85м\n3️⃣ 2.70м  4️⃣ 3.60м")
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return PALET


async def palet(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text.strip()[0])
        if v not in [1, 2, 3, 4]:
            raise ValueError
        context.user_data['palet'] = v
        rg = PALET_GENISLIK[v]
        msg = f"📦 Palet: {v} adet ({rg}m genişlik)\n✅ Devam?" if lang == 'tr' else f"📦 Паллет: {v} ({rg}м)\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_PALET
    except:
        await update.message.reply_text("⚠️ 1, 2, 3 veya 4 girin." if lang == 'tr' else "⚠️ Введите 1, 2, 3 или 4.")
        return PALET


async def confirm_palet(update, context):
    lang = get_lang(context)
    text = update.message.text
    if is_bastan(text, lang):
        return await hesapla(update, context)
    if is_duzelt(text, lang):
        kb = [["1", "2"], ["3", "4"]]
        await update.message.reply_text("📦 Palet:" if lang == 'tr' else "📦 Паллет:",
                                        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        return PALET

    msg = "🏗 Kat sayısı:\nÖrnek: 4" if lang == 'tr' else "🏗 Количество ярусов:\nПример: 4"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return KAT


async def kat(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text)
        if v < 1 or v > 15:
            raise ValueError
        context.user_data['kat'] = v
        msg = f"🏗 Kat: {v}\n✅ Devam?" if lang == 'tr' else f"🏗 Ярусов: {v}\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_KAT
    except:
        await update.message.reply_text("⚠️ 1-15 arası rakam girin." if lang == 'tr' else "⚠️ Введите число 1-15.")
        return KAT


async def confirm_kat(update, context):
    lang = get_lang(context)
    text = update.message.text
    if is_bastan(text, lang):
        return await hesapla(update, context)
    if is_duzelt(text, lang):
        await update.message.reply_text("🏗 Kat sayısı:" if lang == 'tr' else "🏗 Ярусов:", reply_markup=ReplyKeyboardRemove())
        return KAT

    msg = "📏 Raf yüksekliği (metre):\nÖrnek: 5.5" if lang == 'tr' else "📏 Высота стеллажа (м):\nПример: 5.5"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return YUKSEKLIK


async def yukseklik(update, context):
    lang = get_lang(context)
    try:
        v = float(update.message.text.replace(',', '.'))
        if v < 1.5 or v > 20:
            raise ValueError
        context.user_data['yukseklik'] = v
        msg = f"📏 Yükseklik: {v} m\n✅ Devam?" if lang == 'tr' else f"📏 Высота: {v} м\n✅ Продолжить?"
        await update.message.reply_text(msg, reply_markup=devam_kb(lang))
        return CONFIRM_YUKSEKLIK
    except:
        await update.message.reply_text("⚠️ 1.5-20 arası rakam girin." if lang == 'tr' else "⚠️ Введите число 1.5-20.")
        return YUKSEKLIK


async def confirm_yukseklik(update, context):
    lang = get_lang(context)
    text = update.message.text
    if is_bastan(text, lang):
        return await hesapla(update, context)
    if is_duzelt(text, lang):
        await update.message.reply_text("📏 Yükseklik (m):" if lang == 'tr' else "📏 Высота (м):", reply_markup=ReplyKeyboardRemove())
        return YUKSEKLIK

    # Kapı yeri seçimi
    kb = [
        ["⬇️ Alt Orta", "⬇️ Alt Sol", "⬇️ Alt Sağ"],
        ["⬆️ Üst Orta", "⬆️ Üst Sol", "⬆️ Üst Sağ"],
        ["⬅️ Sol Orta", "➡️ Sağ Orta"]
    ] if lang == 'tr' else [
        ["⬇️ Низ-Центр", "⬇️ Низ-Лево", "⬇️ Низ-Право"],
        ["⬆️ Верх-Центр", "⬆️ Верх-Лево", "⬆️ Верх-Право"],
        ["⬅️ Лево-Центр", "➡️ Право-Центр"]
    ]
    msg = ("🚪 Ana kapı (giriş) konumunu seçin:\n"
           "Depo planında giriş neresinde olacak?")
    if lang != 'tr':
        msg = "🚪 Выберите положение входной двери:"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return KAPI_YERI


async def kapi_yeri_sec(update, context):
    lang = get_lang(context)
    text = update.message.text.lower()

    kapi_map = {
        'alt o': 'alt_orta', 'alt s': 'alt_sol', 'alt_sa': 'alt_sag',
        'üst o': 'ust_orta', 'üst s': 'ust_sol', 'üst_sa': 'ust_sag',
        'sol o': 'sol_orta', 'sağ o': 'sag_orta',
        'низ-ц': 'alt_orta', 'низ-л': 'alt_sol', 'низ-п': 'alt_sag',
        'верх-ц': 'ust_orta', 'верх-л': 'ust_sol', 'верх-п': 'ust_sag',
        'лево-ц': 'sol_orta', 'право-ц': 'sag_orta'
    }

    kapi_yeri = 'alt_orta'
    for key, val in kapi_map.items():
        if key in text:
            kapi_yeri = val
            break

    context.user_data['kapi_yeri'] = kapi_yeri

    kb = [["0.5m", "1.0m"], ["1.5m", "2.0m"], ["Özel (yazın)" if lang == 'tr' else "Другой"]]
    msg = ("📐 Duvar kenar boşlukları (güvenlik mesafesi):\n"
           "Raflar ile duvar arasında ne kadar boşluk bırakılsın?\n"
           "(Yangın güvenliği ve hava sirkülasyonu için önerilir)")
    if lang != 'tr':
        msg = "📐 Отступ от стен (м):\n(Рекомендуется для пожарной безопасности)"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return KENAR_BOSLUK


async def kenar_bosluk_sec(update, context):
    lang = get_lang(context)
    text = update.message.text.replace(',', '.').replace('m', '').strip()
    try:
        v = float(text) if text not in ['', 'Другой', 'Özel'] else 1.0
    except:
        v = 1.0

    context.user_data['kenar_bosluk'] = {'ust': v, 'alt': v, 'sol': v, 'sag': v}

    kb = [["✅ Var", "❌ Yok"]] if lang == 'tr' else [["✅ Есть", "❌ Нет"]]
    msg = ("🚛 Yükleme/Boşaltma (rampa) alanı olsun mu?\n"
           "Tır veya kamyon için yanaşma/dock alanı.")
    if lang != 'tr':
        msg = "🚛 Зона погрузки/разгрузки (рампа)?"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return YUKLEME_ALANI


async def yukleme_alani_sec(update, context):
    lang = get_lang(context)
    text = update.message.text.lower()
    if "var" in text or "есть" in text or "✅" in text:
        context.user_data['yukleme_alani'] = {
            'var': True, 'yer': 'alt', 'genislik': min(context.user_data.get('uzunluk', 20) * 0.4, 8.0),
            'derinlik': 3.5
        }
    else:
        context.user_data['yukleme_alani'] = {'var': False}

    kb = [["✅ Var", "❌ Yok"]] if lang == 'tr' else [["✅ Есть", "❌ Нет"]]
    msg = ("🏢 Ofis/İdari alan olsun mu?\n"
           "Depo içinde küçük bir yönetim/ofis köşesi.")
    if lang != 'tr':
        msg = "🏢 Офисная зона?"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return OFIS_ALANI


async def ofis_alani_sec(update, context):
    lang = get_lang(context)
    text = update.message.text.lower()
    if "var" in text or "есть" in text or "✅" in text:
        context.user_data['ofis_alani'] = {
            'var': True, 'yer': 'sag_ust', 'genislik': 4.0, 'derinlik': 3.0
        }
    else:
        context.user_data['ofis_alani'] = {'var': False}

    kb = [["✅ Var", "❌ Yok"]] if lang == 'tr' else [["✅ Есть", "❌ Нет"]]
    msg = ("🔴 Depoda kolon (taşıyıcı direk) var mı?\n"
           "Kolonlar raf yerleşimini etkiler.")
    if lang != 'tr':
        msg = "🔴 Есть колонны (несущие столбы)?"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
    return KOLON_VAR


async def kolon_var_sec(update, context):
    lang = get_lang(context)
    text = update.message.text.lower()
    if "var" in text or "есть" in text or "✅" in text:
        await update.message.reply_text(
            "🔴 Kolon sayısı ve konumlarını metre cinsinden girin:\n"
            "Örnek format: 2 kolon, (5,4) ve (15,8)" if lang == 'tr' else
            "🔴 Введите количество и координаты колонн (м):\nПример: 2 колонны, (5,4) и (15,8)",
            reply_markup=ReplyKeyboardRemove())
        return KOLON_ADET
    else:
        context.user_data['kolon_listesi'] = []
        return await _cizim_hazirla(update, context)


async def kolon_adet(update, context):
    lang = get_lang(context)
    text = update.message.text
    # Basit parser: parantez içindeki sayıları çıkar
    import re
    sayilar = re.findall(r'\((\d+[.,]?\d*)\s*,\s*(\d+[.,]?\d*)\)', text)
    kolonlar = []
    for sx, sy in sayilar:
        kolonlar.append((float(sx.replace(',', '.')), float(sy.replace(',', '.'))))

    context.user_data['kolon_listesi'] = kolonlar
    return await _cizim_hazirla(update, context)


async def _cizim_hazirla(update, context):
    ""Çizim için tüm verileri topla ve çizimi yap"""
    lang = get_lang(context)
    d = context.user_data

    raf_genislik = PALET_GENISLIK[d['palet']]
    koridor = KORIDOR_GENISLIK[d['koridor_tipi']]

    await update.message.reply_text(
        "⏳ Teknik çizim hazırlanıyor...\n"
        "Raf yerleşimi, kapı konumu, yükleme alanı ve güvenlik unsurları çiziliyor."
        if lang == 'tr' else
        "⏳ Подготовка технического чертежа...",
        reply_markup=ReplyKeyboardRemove())

    try:
        resim_buf, raf_adet = teknik_resim_ciz(
            d['uzunluk'], d['genislik'], raf_genislik, koridor, d['kat'], d['yukseklik'],
            d['depo_tipi'], d.get('kapi_yeri', 'alt_orta'),
            d.get('kenar_bosluk', {'ust': 1.0, 'alt': 1.0, 'sol': 1.0, 'sag': 1.0}),
            d.get('yukleme_alani', {'var': False}),
            d.get('kolon_listesi', []),
            d.get('ofis_alani', {'var': False}),
            lang
        )

        kb = [["/hesapla Yeni Çizim" if lang == 'tr' else "/raschet Новый чертёж"]]
        if lang == 'tr':
            cap = (f"📐 TEKNİK ÇİZİM TAMAMLANDI\n"
                   f"{'━' * 30}\n"
                   f"📐 Depo: {d['uzunluk']}m × {d['genislik']}m\n"
                   f"🏭 Yerleşim Tipi: {d['depo_tipi']}-şekli\n"
                   f"🚦 Koridor: {d['koridor_tipi']} ({koridor}m)\n"
                   f"📦 Raf: {raf_adet} adet × {d['kat']} kat = {raf_adet * d['kat']} palet yeri\n"
                   f"🚪 Kapı: {d.get('kapi_yeri', 'alt_orta').replace('_', ' ')}\n"
                   f"📏 Raf boyutu: {raf_genislik}m × {RAF_DERINLIK}m × {d['yukseklik']}m\n"
                   f"{'━' * 30}\n"
                   f"✅ Yeni çizim için /hesapla")
        else:
            cap = (f"📐 ЧЕРТЁЖ ГОТОВ\n"
                   f"{'━' * 30}\n"
                   f"📐 Склад: {d['uzunluk']}м × {d['genislik']}м\n"
                   f"🏭 Тип: {d['depo_tipi']}\n"
                   f"🚦 Проход: {d['koridor_tipi']} ({koridor}м)\n"
                   f"📦 Стеллажи: {raf_adet} шт × {d['kat']} яр. = {raf_adet * d['kat']} паллетомест\n"
                   f"🚪 Дверь: {d.get('kapi_yeri', 'alt_orta')}\n"
                   f"📏 Размер: {raf_genislik}м × {RAF_DERINLIK}м × {d['yukseklik']}м\n"
                   f"{'━' * 30}\n"
                   f"✅ /raschet для нового чертежа")

        await update.message.reply_photo(photo=resim_buf, caption=cap,
                                         reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Çizim hatası: {e}")

    return ConversationHandler.END


async def iptal(update, context):
    lang = get_lang(context)
    msg = "❌ İptal edildi. /hesapla ile başlayın." if lang == 'tr' else "❌ Отменено. Напишите /raschet."
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════
#  ANA UYGULAMA
# ═══════════════════════════════════════════════════════════

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
            LANG:              [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_sec)],
            DEPO_TIPI:         [MessageHandler(filters.TEXT & ~filters.COMMAND, depo_tipi_sec)],
            KORIDOR_TIPI:      [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_tipi_sec)],
            UZUNLUK:           [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk)],
            CONFIRM_UZUNLUK:   [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_uzunluk)],
            GENISLIK:          [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik)],
            CONFIRM_GENISLIK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_genislik)],
            PALET:             [MessageHandler(filters.TEXT & ~filters.COMMAND, palet)],
            CONFIRM_PALET:     [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_palet)],
            KAT:               [MessageHandler(filters.TEXT & ~filters.COMMAND, kat)],
            CONFIRM_KAT:       [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_kat)],
            YUKSEKLIK:         [MessageHandler(filters.TEXT & ~filters.COMMAND, yukseklik)],
            CONFIRM_YUKSEKLIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_yukseklik)],
            KAPI_YERI:         [MessageHandler(filters.TEXT & ~filters.COMMAND, kapi_yeri_sec)],
            KENAR_BOSLUK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_sec)],
            YUKLEME_ALANI:     [MessageHandler(filters.TEXT & ~filters.COMMAND, yukleme_alani_sec)],
            OFIS_ALANI:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ofis_alani_sec)],
            KOLON_VAR:         [MessageHandler(filters.TEXT & ~filters.COMMAND, kolon_var_sec)],
            KOLON_ADET:        [MessageHandler(filters.TEXT & ~filters.COMMAND, kolon_adet)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
