import os
import logging
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

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
    baslik = f"TEKNIK CIZIM | Tip: {depo_tipi}" if lang=='tr' else f"TEHNICESKIY CERTEZ | Tip: {depo_tipi}"
    draw.text((W//2, 19), baslik, fill=SARI, font=ft, anchor='mm')

    # Depo siniri - tipe gore
    if depo_tipi == 'I':
        draw.rectangle([ox, oy, ox+plan_w, oy+plan_h], outline=SINIR, width=3)

    elif depo_tipi == 'L':
        cut_w = int(plan_w * 0.4)
        cut_h = int(plan_h * 0.4)
        pts = [(ox,oy),(ox+plan_w-cut_w,oy),(ox+plan_w-cut_w,oy+cut_h),
               (ox+plan_w,oy+cut_h),(ox+plan_w,oy+plan_h),(ox,oy+plan_h),(ox,oy)]
        draw.polygon(pts, fill='#0d1117')
        for i in range(len(pts)-1):
            draw.line([pts[i], pts[i+1]], fill=SINIR, width=3)

    elif depo_tipi == 'U':
        cut_w = int(plan_w * 0.4)
        cut_x = ox + (plan_w - cut_w) // 2
        cut_h = int(plan_h * 0.35)
        pts = [(ox,oy),(cut_x,oy),(cut_x,oy+cut_h),(cut_x+cut_w,oy+cut_h),
               (cut_x+cut_w,oy),(ox+plan_w,oy),(ox+plan_w,oy+plan_h),(ox,oy+plan_h),(ox,oy)]
        draw.polygon(pts, fill='#0d1117')
        for i in range(len(pts)-1):
            draw.line([pts[i], pts[i+1]], fill=SINIR, width=3)

    # Giris kapisi
    G = 55
    if giris_duvar == 'alt':
        if giris_konum == 'orta': gx = ox + plan_w // 2
        elif giris_konum == 'sol': gx = ox + int(giris_mesafe * sx) + G//2
        else: gx = ox + plan_w - int(giris_mesafe * sx) - G//2
        draw.line([gx-G//2, oy+plan_h, gx+G//2, oy+plan_h], fill=SARI, width=7)
        draw.text((gx, oy+plan_h+8), "GIRIS" if lang=='tr' else "VHOD", fill=SARI, font=fn, anchor='mt')
        bosluk_px = int(giris_bosluk * sy)
        draw.rectangle([ox+2, oy+plan_h-bosluk_px, ox+plan_w-2, oy+plan_h-2], outline=KIRMIZI, width=1)
        draw.text((ox+plan_w//2, oy+plan_h-bosluk_px//2), f"{giris_bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')
    elif giris_duvar == 'ust':
        if giris_konum == 'orta': gx = ox + plan_w // 2
        elif giris_konum == 'sol': gx = ox + int(giris_mesafe * sx) + G//2
        else: gx = ox + plan_w - int(giris_mesafe * sx) - G//2
        draw.line([gx-G//2, oy, gx+G//2, oy], fill=SARI, width=7)
        draw.text((gx, oy-8), "GIRIS" if lang=='tr' else "VHOD", fill=SARI, font=fn, anchor='mb')
        bosluk_px = int(giris_bosluk * sy)
        draw.rectangle([ox+2, oy+2, ox+plan_w-2, oy+bosluk_px], outline=KIRMIZI, width=1)
        draw.text((ox+plan_w//2, oy+bosluk_px//2), f"{giris_bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')
    elif giris_duvar == 'sol':
        if giris_konum == 'orta': gy = oy + plan_h // 2
        elif giris_konum == 'ust': gy = oy + int(giris_mesafe * sy) + G//2
        else: gy = oy + plan_h - int(giris_mesafe * sy) - G//2
        draw.line([ox, gy-G//2, ox, gy+G//2], fill=SARI, width=7)
        draw.text((ox-8, gy), "GIRIS" if lang=='tr' else "VHOD", fill=SARI, font=fn, anchor='rm')
        bosluk_px = int(giris_bosluk * sx)
        draw.rectangle([ox+2, oy+2, ox+bosluk_px, oy+plan_h-2], outline=KIRMIZI, width=1)
        draw.text((ox+bosluk_px//2, oy+plan_h//2), f"{giris_bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')
    else:
        if giris_konum == 'orta': gy = oy + plan_h // 2
        elif giris_konum == 'ust': gy = oy + int(giris_mesafe * sy) + G//2
        else: gy = oy + plan_h - int(giris_mesafe * sy) - G//2
        draw.line([ox+plan_w, gy-G//2, ox+plan_w, gy+G//2], fill=SARI, width=7)
        draw.text((ox+plan_w+8, gy), "GIRIS" if lang=='tr' else "VHOD", fill=SARI, font=fn, anchor='lm')
        bosluk_px = int(giris_bosluk * sx)
        draw.rectangle([ox+plan_w-bosluk_px, oy+2, ox+plan_w-2, oy+plan_h-2], outline=KIRMIZI, width=1)
        draw.text((ox+plan_w-bosluk_px//2, oy+plan_h//2), f"{giris_bosluk}m", fill=KIRMIZI, font=fn, anchor='mm')

    # Raf alani
    raf_x1 = ox + int(kenar_bosluk * sx)
    raf_y1 = oy + int(kenar_bosluk * sy)
    raf_x2 = ox + plan_w - int(kenar_bosluk * sx)
    raf_y2 = oy + plan_h - int(kenar_bosluk * sy)

    if giris_duvar == 'alt': raf_y2 -= int(giris_bosluk * sy)
    elif giris_duvar == 'ust': raf_y1 += int(giris_bosluk * sy)
    elif giris_duvar == 'sol': raf_x1 += int(giris_bosluk * sx)
    else: raf_x2 -= int(giris_bosluk * sx)

    raf_alan_w = raf_x2 - raf_x1
    raf_alan_h = raf_y2 - raf_y1
    ef_genislik = raf_alan_h / sy
    ef_uzunluk = raf_alan_w / sx

    raf_satir = max(1, int(ef_genislik / (raf_genislik + koridor)))
    raf_perz = max(1, int(ef_uzunluk / 1.1))

    raflar = []
    for row in range(raf_satir):
        ry1 = raf_y1 + int((raf_genislik/2 + row*(raf_genislik+koridor)) * sy)
        ry2 = max(ry1 + int(raf_genislik * sy), ry1 + 14)
        for col in range(raf_perz):
            rx1 = raf_x1 + int(col * 1.1 * sx) + 1
            rx2 = max(raf_x1 + int((col+1) * 1.1 * sx) - 1, rx1 + 8)

            # L icin sag ust bolumu atla
            if depo_tipi == 'L':
                cut_w = int(plan_w * 0.4)
                cut_h = int(plan_h * 0.4)
                if rx2 > ox+plan_w-cut_w-5 and ry1 < oy+cut_h+5:
                    continue

            # U icin ust orta bolumu atla
            if depo_tipi == 'U':
                cut_w = int(plan_w * 0.4)
                cut_x = ox + (plan_w - cut_w) // 2
                cut_h = int(plan_h * 0.35)
                if rx1 > cut_x-5 and rx2 < cut_x+cut_w+5 and ry1 < oy+cut_h+5:
                    continue

            raflar.append((rx1, ry1, rx2, ry2, row, col))

    for (rx1, ry1, rx2, ry2, row, col) in raflar:
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

    # Raf ve koridor etiketleri
    satir_ry = {}
    for (rx1, ry1, rx2, ry2, row, col) in raflar:
        if col == 0:
            satir_ry[row] = (ry1, ry2)

    satirlar = sorted(satir_ry.keys())
    for i, row in enumerate(satirlar):
        ry1, ry2 = satir_ry[row]
        lbl = f"R{row+1}"
        draw.text((ox+plan_w+5, (ry1+ry2)//2), lbl, fill=BEYAZ, font=fn, anchor='lm')
        if i > 0:
            prev_ry2 = satir_ry[satirlar[i-1]][1]
            ky = (prev_ry2 + ry1) // 2
            draw.text((ox+plan_w+5, ky), f"{koridor}m", fill=MOR, font=fn, anchor='lm')

    toplam_raf = len(raflar)

    # Olcular
    draw.line([ox, oy-14, ox+plan_w, oy-14], fill=AGRI, width=1)
    draw.line([ox, oy-18, ox, oy-10], fill=AGRI, width=2)
    draw.line([ox+plan_w, oy-18, ox+plan_w, oy-10], fill=AGRI, width=2)
    draw.text((ox+plan_w//2, oy-14), f"{uzunluk}m", fill=BEYAZ, font=fn, anchor='mm')
    draw.line([ox-14, oy, ox-14, oy+plan_h], fill=AGRI, width=1)
    draw.line([ox-18, oy, ox-10, oy], fill=AGRI, width=2)
    draw.line([ox-18, oy+plan_h, ox-10, oy+plan_h], fill=AGRI, width=2)
    draw.text((ox-26, oy+plan_h//2), f"{genislik}m", fill=BEYAZ, font=fn, anchor='mm')

    # Alt bilgi
    iy = H - INFO_H
    draw.rectangle([0, iy, W, H], fill='#161b22')
    draw.line([0, iy, W, iy], fill='#30363d', width=1)

    lx, ly = 18, iy + 10
    items = [
        (MAVI,    ("Dikme" if lang=='tr' else "Stoyka"),      f"{yukseklik}m"),
        (TURUNCU, ("Yatay Bag." if lang=='tr' else "Balka"),  f"{raf_genislik}m"),
        (YESIL,   ("Derinlik" if lang=='tr' else "Glubina"),  "1.10m"),
        (MOR,     ("Koridor" if lang=='tr' else "Prokhod"),   f"{koridor}m"),
        (KIRMIZI, ("Giris Boslugu" if lang=='tr' else "Zona vkhoda"), f"{giris_bosluk}m"),
    ]
    for renk, isim, olcu in items:
        draw.text((lx, ly), f"- {isim}:", fill=renk, font=fb)
        draw.text((lx+165, ly), olcu, fill=BEYAZ, font=fb)
        ly += 21

    rx2b = W//2 + 10
    ry2b = iy + 10
    if lang == 'tr':
        bilgiler = [("Kat",str(kat)),("Satir",str(raf_satir)),("Sutun",str(raf_perz)),("Toplam",str(toplam_raf)),("Kenar",f"{kenar_bosluk}m")]
    else:
        bilgiler = [("Yarusov",str(kat)),("Ryadov",str(raf_satir)),("Kolonn",str(raf_perz)),("Itogo",str(toplam_raf)),("Otstup",f"{kenar_bosluk}m")]
    for k, v in bilgiler:
        draw.text((rx2b, ry2b), f"{k}:", fill=AGRI, font=fn)
        draw.text((rx2b+130, ry2b), v, fill=BEYAZ, font=fb)
        ry2b += 21

    buf = io.BytesIO()
    img.save(buf, format='PNG', dpi=(150, 150))
    buf.seek(0)
    return buf, raf_satir, raf_perz, toplam_raf

async def start(update, context):
    await update.message.reply_text("Dil secin / Viberite yazik:",
        reply_markup=kb([["TR Turkce", "RU Russkiy"]]))
    return LANG

async def hesapla(update, context):
    await update.message.reply_text("Dil secin / Viberite yazik:",
        reply_markup=kb([["TR Turkce", "RU Russkiy"]]))
    return LANG

async def lang_sec(update, context):
    t = update.message.text
    context.user_data['lang'] = 'ru' if "RU" in t else 'tr'
    lang = get_lang(context)
    msg = ("Depo sekli:\nI - Duz siralar\nL - Iki duvara bitisik\nU - Uc duvara bitisik"
           if lang=='tr' else
           "Forma sklada:\nI - Pryamye ryady\nL - Vdol dvukh sten\nU - Vdol trekh sten")
    await update.message.reply_text(msg, reply_markup=kb([["I","L","U"]]))
    return DEPO_TIPI

async def depo_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.strip().upper()[0]
    if t not in ['I','L','U']:
        await update.message.reply_text("I, L veya U secin." if lang=='tr' else "I, L ili U.")
        return DEPO_TIPI
    context.user_data['depo_tipi'] = t
    msg = ("Koridor tipi:\n1 Forklift 3.0m\n2 Transpalet 2.0m\n3 El ile 1.2m"
           if lang=='tr' else
           "Tip prokhoda:\n1 Pogruzchik 3.0m\n2 Transpalet 2.0m\n3 Ruchnoy 1.2m")
    await update.message.reply_text(msg, reply_markup=kb([["Forklift","Transpalet","El ile"]]))
    return KORIDOR_TIPI

async def koridor_tipi_sec(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "forklift" in t or "pogruz" in t: context.user_data['koridor_tipi'] = 'forklift'
    elif "transpalet" in t: context.user_data['koridor_tipi'] = 'transpalet'
    else: context.user_data['koridor_tipi'] = 'el'
    msg = "Depo uzunlugu (m) - Ornek: 20" if lang=='tr' else "Dlina sklada (m) - Primer: 20"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['uzunluk'] = float(update.message.text.replace(',','.'))
        msg = "Depo genisligi (m) - Ornek: 12" if lang=='tr' else "Shirina sklada (m) - Primer: 12"
        await update.message.reply_text(msg)
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam - Ornek: 20")
        return UZUNLUK

async def genislik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['genislik'] = float(update.message.text.replace(',','.'))
        msg = ("Palet sayisi:\n1 - 0.95m\n2 - 1.85m\n3 - 2.70m\n4 - 3.60m"
               if lang=='tr' else
               "Pallet na ryad:\n1 - 0.95m\n2 - 1.85m\n3 - 2.70m\n4 - 3.60m")
        await update.message.reply_text(msg, reply_markup=kb([["1","2"],["3","4"]]))
        return PALET
    except:
        await update.message.reply_text("Sadece rakam - Ornek: 12")
        return GENISLIK

async def palet_h(update, context):
    lang = get_lang(context)
    try:
        v = int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet'] = v
        msg = "Kat sayisi - Ornek: 3" if lang=='tr' else "Kolichestvo yarusov - Primer: 3"
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1, 2, 3 veya 4 girin.")
        return PALET

async def kat_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kat'] = int(update.message.text)
        msg = "Raf yuksekligi (m) - Ornek: 5" if lang=='tr' else "Vysota stellazha (m) - Primer: 5"
        await update.message.reply_text(msg)
        return YUKSEKLIK
    except:
        await update.message.reply_text("Sadece rakam - Ornek: 3")
        return KAT

async def yukseklik_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['yukseklik'] = float(update.message.text.replace(',','.'))
        msg = ("Giris kapisi hangi duvarda?\nAlt - Ust - Sol - Sag"
               if lang=='tr' else
               "Na kakoy stene vkhod?\nNiz - Verkh - Levo - Pravo")
        await update.message.reply_text(msg, reply_markup=kb([["Alt","Ust"],["Sol","Sag"]]))
        return GIRIS_DUVAR
    except:
        await update.message.reply_text("Sadece rakam - Ornek: 5")
        return YUKSEKLIK

async def giris_duvar_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "alt" in t or "niz" in t: context.user_data['giris_duvar'] = 'alt'
    elif "ust" in t or "verkh" in t: context.user_data['giris_duvar'] = 'ust'
    elif "sol" in t or "levo" in t: context.user_data['giris_duvar'] = 'sol'
    else: context.user_data['giris_duvar'] = 'sag'
    msg = ("Kapinin konumu?\nSol yakın - Orta - Sag yakin"
           if lang=='tr' else
           "Gde imenno vkhod?\nLevee - Centr - Pravee")
    await update.message.reply_text(msg, reply_markup=kb([["Sol yakin","Orta","Sag yakin"]]))
    return GIRIS_KONUM

async def giris_konum_h(update, context):
    lang = get_lang(context)
    t = update.message.text.lower()
    if "orta" in t or "centr" in t:
        context.user_data['giris_konum'] = 'orta'
        context.user_data['giris_mesafe'] = 0.0
        msg = ("Giris onunde bos alan kac metre?\nOrnek: 2"
               if lang=='tr' else
               "Zona pered vkhodom (m)?\nPrimer: 2")
        await update.message.reply_text(msg, reply_markup=kb([["1","2","3"]]))
        return GIRIS_BOSLUK
    elif "sol" in t or "lev" in t:
        context.user_data['giris_konum'] = 'sol'
    else:
        context.user_data['giris_konum'] = 'sag'
    msg = "Koseden kac metre uzakta? - Ornek: 2" if lang=='tr' else "Rasstoyaniye ot ugla (m)? - Primer: 2"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return GIRIS_MESAFE

async def giris_mesafe_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_mesafe'] = float(update.message.text.replace(',','.'))
        msg = ("Giris onunde bos alan kac metre?\nOrnek: 2"
               if lang=='tr' else
               "Zona pered vkhodom (m)?\nPrimer: 2")
        await update.message.reply_text(msg, reply_markup=kb([["1","2","3"]]))
        return GIRIS_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam - Ornek: 2")
        return GIRIS_MESAFE

async def giris_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['giris_bosluk'] = float(update.message.text.replace(',','.'))
        msg = ("Raf ile duvar arasi bosluk (m)?\n0 = duvara bitisik\nOrnek: 0.5"
               if lang=='tr' else
               "Otstup ot sten (m)?\n0 = vplotnutyu\nPrimer: 0.5")
        await update.message.reply_text(msg, reply_markup=kb([["0","0.5","1"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam - Ornek: 2")
        return GIRIS_BOSLUK

async def kenar_bosluk_h(update, context):
    lang = get_lang(context)
    try:
        context.user_data['kenar_bosluk'] = float(update.message.text.replace(',','.'))
        d = context.user_data
        await update.message.reply_text(
            "Teknik cizim hazirlaniyor..." if lang=='tr' else "Podgotovka chertezha...",
            reply_markup=ReplyKeyboardRemove()
        )
        resim, raf_satir, raf_perz, toplam = teknik_resim_ciz(d, lang)
        if lang=='tr':
            cap = (f"TEKNIK CIZIM\n"
                   f"Depo: {d['uzunluk']}x{d['genislik']}m | Tip: {d['depo_tipi']}\n"
                   f"Raf: {raf_satir} satir x {raf_perz} sutun = {toplam} adet\n"
                   f"Kat: {d['kat']} | Yukseklik: {d['yukseklik']}m\n"
                   f"Giris: {d['giris_duvar']} duvar\n"
                   f"Fiyat icin /hesapla")
        else:
            cap = (f"TEKHNICHESKIY CHERTEZH\n"
                   f"Sklad: {d['uzunluk']}x{d['genislik']}m | Tip: {d['depo_tipi']}\n"
                   f"Stellazhi: {raf_satir}x{raf_perz} = {toplam} sht\n"
                   f"Yarusov: {d['kat']} | Vysota: {d['yukseklik']}m\n"
                   f"Vkhod: {d['giris_duvar']}\n"
                   f"Raschet: /raschet")
        await update.message.reply_photo(photo=resim, caption=cap)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return KENAR_BOSLUK

async def iptal(update, context):
    await update.message.reply_text("Iptal. /hesapla ile baslayin.", reply_markup=ReplyKeyboardRemove())
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
            KORIDOR_TIPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, koridor_tipi_sec)],
            UZUNLUK:      [MessageHandler(filters.TEXT & ~filters.COMMAND, uzunluk_h)],
            GENISLIK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, genislik_h)],
            PALET:        [MessageHandler(filters.TEXT & ~filters.COMMAND, palet_h)],
            KAT:          [MessageHandler(filters.TEXT & ~filters.COMMAND, kat_h)],
            YUKSEKLIK:    [MessageHandler(filters.TEXT & ~filters.COMMAND, yukseklik_h)],
            GIRIS_DUVAR:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_duvar_h)],
            GIRIS_KONUM:  [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_konum_h)],
            GIRIS_MESAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_mesafe_h)],
            GIRIS_BOSLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, giris_bosluk_h)],
            KENAR_BOSLUK: [MessageHandler(filters.TEXT & ~filters.COMMAND, kenar_bosluk_h)],
        },
        fallbacks=[CommandHandler('iptal', iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
