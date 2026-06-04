import os, logging, io, math
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, UZUNLUK, GENISLIK, DEPO_YUK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_GENISLIK, GIRIS_BOSLUK,
 KENAR_BOSLUK, KORIDOR_TIPI, PALET, KAT, RAF_YUK) = range(14)

PALET_GENISLIK = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_GENISLIK = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}
DERINLIK = 1.1  # sabit

def get_lang(c): return c.user_data.get('lang', 'tr')
def kb(rows): return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)

def hesapla_layout(d):
    """
    Raflar KAPIYA DIK uzanır.
    Koridorlar KAPIYA PARALEL uzanır.
    
    Kapı alt duvarda ise:
      - Raflar yukari dogru uzanir (derinlik yonunde = genislik yonunde)
      - Koridorlar yatay (uzunluk yonunde)
      - Raf genisligi = raf_g (uzunluk yonunde, koridora paralel)
      - Raf derinligi = 1.1m (genislik yonunde, kapiya dik)
    """
    uzunluk  = d['uzunluk']
    genislik = d['genislik']
    raf_g    = PALET_GENISLIK[d['palet']]
    koridor  = KORIDOR_GENISLIK[d['koridor_tipi']]
    kb2      = d.get('kenar_bosluk', 0.0)
    g_duvar  = d.get('giris_duvar', 'alt')
    g_bosluk = d.get('giris_bosluk', 3.0)
    kat      = d['kat']

    # Kullanilabilir alan (yükleme alani hariç)
    # Kapıya dik: raflar kapidan uzağa dogru uzaniyor
    # Kapıya paralel yön: koridorlar bu yonde
    
    if g_duvar in ['alt', 'ust']:
        # Uzunluk boyunca koridorlar, genislik boyunca raflar uzaniyor
        paralel_uzunluk = uzunluk - kb2 * 2      # koridor yonu
        dik_uzunluk     = genislik - kb2 * 2 - g_bosluk  # raf uzama yonu
    else:
        paralel_uzunluk = genislik - kb2 * 2
        dik_uzunluk     = uzunluk - kb2 * 2 - g_bosluk

    paralel_uzunluk = max(paralel_uzunluk, 0.1)
    dik_uzunluk     = max(dik_uzunluk, 0.1)

    # Paralel yonde kac raf sirasi yan yana sigacak
    # Her raf birimi: raf_g genisliginde (paralel yonde)
    raf_yan = max(1, int(paralel_uzunluk / raf_g))

    # ---- SECENEK 1: U_MAKS ----
    # Sol duvar + sag duvar + arka duvar + orta sirt sirta bloklar
    # Sol ve sag duvara: DERINLIK kalinliginda, raf_yan adet
    # Arka duvara: raf_yan adet (tek sira)
    # Ortaya: sirt sirta ciftler, aralarinda koridor
    
    # Dik yonde kalan ic alan (sol+sag duvar raflari cikarinca)
    ic_alan = dik_uzunluk - DERINLIK * 2 - koridor * 2  # iki yanin koriodoru
    
    # Arka duvara raf (kapinin karsisi)
    arka_raf = raf_yan
    
    # Orta sirt sirta bloklar
    blok_derinlik = DERINLIK * 2  # sirt sirta = 2.2m
    orta_blok_sayisi = 0
    kalan_ic = ic_alan - DERINLIK  # arka duvar rafindan sonra
    if kalan_ic > 0:
        orta_blok_sayisi = max(0, int(kalan_ic / (blok_derinlik + koridor)))
    
    u_orta_raf = raf_yan * 2  # sol+sag
    u_orta_raf += arka_raf    # arka
    u_orta_raf += orta_blok_sayisi * 2 * raf_yan  # orta bloklar
    
    # Raf alani hesabi
    u_raf_alani = (
        DERINLIK * paralel_uzunluk * 2 +  # sol + sag
        raf_g * paralel_uzunluk +          # arka
        orta_blok_sayisi * blok_derinlik * paralel_uzunluk
    )
    
    # ---- SECENEK 2: I_MAKS ----
    # Sadece sirt sirta cift bloklar, duvara bitisik yok
    # Ilk blok duvara yakin (kb2 + bosluk sonra)
    i_blok_sayisi = max(1, int(dik_uzunluk / (blok_derinlik + koridor)))
    i_toplam_raf  = i_blok_sayisi * 2 * raf_yan
    i_raf_alani   = i_blok_sayisi * blok_derinlik * paralel_uzunluk

    # Depo verimi
    depo_alani = uzunluk * genislik
    if g_duvar in ['alt','ust']:
        yukleme_alani = uzunluk * g_bosluk
    else:
        yukleme_alani = genislik * g_bosluk

    u_verim = round(u_raf_alani / depo_alani * 100, 1)
    i_verim = round(i_raf_alani / depo_alani * 100, 1)

    u_kapasite = u_orta_raf * kat * d['palet']  # yaklasik
    i_kapasite = i_toplam_raf * kat * d['palet']

    return {
        'U_MAKS': {
            'tip': 'U_MAKS',
            'toplam': u_orta_raf,
            'raf_yan': raf_yan,
            'orta_blok': orta_blok_sayisi,
            'arka_raf': arka_raf,
            'raf_alani': round(u_raf_alani, 1),
            'verim': u_verim,
            'kapasite': u_kapasite,
            'paralel': paralel_uzunluk,
            'dik': dik_uzunluk,
            'yukleme_alani': round(yukleme_alani, 1),
            'depo_alani': depo_alani,
        },
        'I_MAKS': {
            'tip': 'I_MAKS',
            'toplam': i_toplam_raf,
            'raf_yan': raf_yan,
            'blok_sayisi': i_blok_sayisi,
            'raf_alani': round(i_raf_alani, 1),
            'verim': i_verim,
            'kapasite': i_kapasite,
            'paralel': paralel_uzunluk,
            'dik': dik_uzunluk,
            'yukleme_alani': round(yukleme_alani, 1),
            'depo_alani': depo_alani,
        }
    }

def ciz_raf(draw, rx1, ry1, rx2, ry2):
    """Kapıya dik raf: uzun kenar paralel yonde, kisa kenar dik yonde."""
    draw.rectangle([rx1, ry1, rx2, ry2], fill='#0a1628')
    draw.line([rx1, ry1, rx2, ry2], fill='#1e2a3a', width=1)
    draw.line([rx2, ry1, rx1, ry2], fill='#1e2a3a', width=1)
    draw.rectangle([rx1, ry1, rx2, ry2], outline='#304060', width=1)
    # Yatay baglanti: uzun kenar (sol-sag = paralel yonde)
    draw.line([rx1, ry1+4, rx1, ry2-4], fill='#ff8c42', width=3)
    draw.line([rx2, ry1+4, rx2, ry2-4], fill='#ff8c42', width=3)
    # Derinlik: kisa kenar (ust-alt = kapiya dik)
    draw.line([rx1+4, ry1, rx2-4, ry1], fill='#4ade80', width=2)
    draw.line([rx1+4, ry2, rx2-4, ry2], fill='#4ade80', width=2)
    # Dikmeler
    r = 4
    for px, py in [(rx1,ry1),(rx2,ry1),(rx1,ry2),(rx2,ry2)]:
        draw.ellipse([px-r,py-r,px+r,py+r], fill='#4a9eff', outline='white', width=1)

def oy(draw, x1,x2,y,txt,f,renk):
    draw.line([x1,y,x2,y],fill=renk,width=1)
    draw.line([x1,y-4,x1,y+4],fill=renk,width=2)
    draw.line([x2,y-4,x2,y+4],fill=renk,width=2)
    draw.text(((x1+x2)//2,y-5),txt,fill=renk,font=f,anchor='mb')

def od(draw,x,y1,y2,txt,f,renk):
    draw.line([x,y1,x,y2],fill=renk,width=1)
    draw.line([x-4,y1,x+4,y1],fill=renk,width=2)
    draw.line([x-4,y2,x+4,y2],fill=renk,width=2)
    draw.text((x+5,(y1+y2)//2),txt,fill=renk,font=f,anchor='lm')

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
    g_bosluk = d.get('giris_bosluk', 3.0)
    g_gen    = d.get('giris_genislik', 4.0)
    tip      = sec['tip']

    if g_duvar in ['alt','ust']:
        yukleme_en  = uzunluk
        yukleme_boy = g_bosluk
    else:
        yukleme_en  = g_bosluk
        yukleme_boy = genislik
    yukleme_m2 = round(yukleme_en * yukleme_boy, 1)

    W, H = 1200, 940
    img  = Image.new('RGB', (W, H), '#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        fn  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        ft  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
        fsm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        fxs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except:
        fb = fn = ft = fsm = fxs = ImageFont.load_default()

    BEYAZ  = '#e8e8e8'
    AGRI   = '#505070'
    SARI   = '#ffd700'
    SINIR  = '#00b4d8'
    MOR    = '#c084fc'
    YESIL2 = '#22c55e'
    TURUNCU= '#ff8c42'
    YESIL  = '#4ade80'
    MAVI   = '#4a9eff'
    KIRMIZI= '#ff6b6b'

    INFO_H = 160
    pl, pt, pr, pb = 80, 55, 130, INFO_H + 45
    pw = W - pl - pr
    ph = H - pt - pb
    ox, oy_val = pl, pt
    sx = pw / uzunluk
    sy = ph / genislik

    tip_adi = {
        'U_MAKS': ('U-MAKS: Duvar + Orta', 'U-МАКС: Стены + Центр'),
        'I_MAKS': ('I-MAKS: Sirt Sirta Bloklar', 'I-МАКС: Блоки спина к спине'),
    }

    # BASLIK
    draw.rectangle([0,0,W,42], fill='#161b22')
    t_ad = tip_adi.get(tip,(tip,tip))[1 if lang=='ru' else 0]
    if lang=='tr':
        baslik = f"SECENEK {sira}/{toplam_sira}  ●  {t_ad}  ●  {sec['toplam']} raf  ●  Verim: %{sec['verim']}"
    else:
        baslik = f"ВАРИАНТ {sira}/{toplam_sira}  ●  {t_ad}  ●  {sec['toplam']} стелл.  ●  КПД: {sec['verim']}%"
    draw.text((W//2,21), baslik, fill=SARI, font=ft, anchor='mm')

    # DEPO SINIRI
    draw.rectangle([ox,oy_val,ox+pw,oy_val+ph], outline=SINIR, width=3)
    draw.rectangle([ox+2,oy_val+2,ox+pw-2,oy_val+ph-2], outline='#1a3a5c', width=1)

    # KAPI & YUKLEME ALANI
    G = max(int(g_gen*sx), 35)
    kapi_lbl = "GİRİŞ/ÇIKIŞ" if lang=='tr' else "ВХОД/ВЫХОД"
    gx = gy = 0
    if g_duvar in ['alt','ust']:
        if g_konum=='orta': gx=ox+pw//2
        elif g_konum=='sol': gx=ox+int(g_mesafe*sx)+G//2
        else: gx=ox+pw-int(g_mesafe*sx)-G//2
    else:
        if g_konum=='orta': gy=oy_val+ph//2
        elif g_konum=='ust': gy=oy_val+int(g_mesafe*sy)+G//2
        else: gy=oy_val+ph-int(g_mesafe*sy)-G//2

    bp_y = int(g_bosluk*sy)
    bp_x = int(g_bosluk*sx)

    def yuk_alani_ciz(g_dv):
        zona = f"YUKLEME/BOSALTMA ALANI\n{yukleme_en}×{yukleme_boy}m = {yukleme_m2}m²" if lang=='tr' else f"ЗОНА ПОГРУЗКИ/РАЗГРУЗКИ\n{yukleme_en}×{yukleme_boy}м = {yukleme_m2}м²"
        if g_dv=='alt':
            draw.rectangle([ox+3,oy_val+ph-bp_y,ox+pw-3,oy_val+ph-3], fill='#031a0d', outline=YESIL2, width=2)
            draw.text((ox+pw//2,oy_val+ph-bp_y//2-8), "YUKLEME/BOSALTMA" if lang=='tr' else "ЗОНА ПОГРУЗКИ", fill=YESIL2, font=fsm, anchor='mm')
            draw.text((ox+pw//2,oy_val+ph-bp_y//2+8), f"{yukleme_en}×{yukleme_boy}m={yukleme_m2}m²", fill=YESIL2, font=fb, anchor='mm')
            od(draw,ox+pw+8,oy_val+ph-bp_y,oy_val+ph,f"{g_bosluk}m",fsm,YESIL2)
            oy_fn(draw,gx,bp_y,G,g_gen,g_mesafe,g_konum,lang,kapi_lbl,fsm,SARI,ox,pw,oy_val,ph,'alt')
        elif g_dv=='ust':
            draw.rectangle([ox+3,oy_val+3,ox+pw-3,oy_val+bp_y], fill='#031a0d', outline=YESIL2, width=2)
            draw.text((ox+pw//2,oy_val+bp_y//2-8), "YUKLEME/BOSALTMA" if lang=='tr' else "ЗОНА ПОГРУЗКИ", fill=YESIL2, font=fsm, anchor='mm')
            draw.text((ox+pw//2,oy_val+bp_y//2+8), f"{yukleme_en}×{yukleme_boy}m={yukleme_m2}m²", fill=YESIL2, font=fb, anchor='mm')
            od(draw,ox+pw+8,oy_val,oy_val+bp_y,f"{g_bosluk}m",fsm,YESIL2)
            oy_fn(draw,gx,bp_y,G,g_gen,g_mesafe,g_konum,lang,kapi_lbl,fsm,SARI,ox,pw,oy_val,ph,'ust')
        elif g_dv=='sol':
            draw.rectangle([ox+3,oy_val+3,ox+bp_x,oy_val+ph-3], fill='#031a0d', outline=YESIL2, width=2)
            draw.text((ox+bp_x//2,oy_val+ph//2-8), "YUKLEME" if lang=='tr' else "ЗОНА", fill=YESIL2, font=fsm, anchor='mm')
            draw.text((ox+bp_x//2,oy_val+ph//2+8), f"{yukleme_m2}m²", fill=YESIL2, font=fb, anchor='mm')
            oy(draw,ox,ox+bp_x,oy_val+ph+8,f"{g_bosluk}m",fsm,YESIL2)
            oy_fn(draw,gx,bp_y,G,g_gen,g_mesafe,g_konum,lang,kapi_lbl,fsm,SARI,ox,pw,oy_val,ph,'sol',gy=gy)
        else:
            draw.rectangle([ox+pw-bp_x,oy_val+3,ox+pw-3,oy_val+ph-3], fill='#031a0d', outline=YESIL2, width=2)
            draw.text((ox+pw-bp_x//2,oy_val+ph//2-8), "YUKLEME" if lang=='tr' else "ЗОНА", fill=YESIL2, font=fsm, anchor='mm')
            draw.text((ox+pw-bp_x//2,oy_val+ph//2+8), f"{yukleme_m2}m²", fill=YESIL2, font=fb, anchor='mm')
            oy(draw,ox+pw-bp_x,ox+pw,oy_val+ph+8,f"{g_bosluk}m",fsm,YESIL2)
            oy_fn(draw,gx,bp_y,G,g_gen,g_mesafe,g_konum,lang,kapi_lbl,fsm,SARI,ox,pw,oy_val,ph,'sag',gy=gy)

    def oy_fn(draw,gx,bp_y,G,g_gen,g_mesafe,g_konum,lang,kapi_lbl,fsm,SARI,ox,pw,oy_v,ph,gd,gy=0):
        if gd=='alt':
            draw.line([gx-G//2,oy_v+ph,gx+G//2,oy_v+ph],fill=SARI,width=8)
            draw.text((gx,oy_v+ph+10),kapi_lbl,fill=SARI,font=fsm,anchor='mt')
            oy(draw,gx-G//2,gx+G//2,oy_v+ph+24,f"{g_gen}m",fsm,SARI)
            if g_mesafe>0 and g_konum!='orta':
                if g_konum=='sol': oy(draw,ox,gx-G//2,oy_v+ph+38,f"{g_mesafe}m",fsm,BEYAZ)
                else: oy(draw,gx+G//2,ox+pw,oy_v+ph+38,f"{g_mesafe}m",fsm,BEYAZ)
        elif gd=='ust':
            draw.line([gx-G//2,oy_v,gx+G//2,oy_v],fill=SARI,width=8)
            draw.text((gx,oy_v-10),kapi_lbl,fill=SARI,font=fsm,anchor='mb')
            oy(draw,gx-G//2,gx+G//2,oy_v-22,f"{g_gen}m",fsm,SARI)
        elif gd=='sol':
            draw.line([ox,gy-G//2,ox,gy+G//2],fill=SARI,width=8)
            draw.text((ox-8,gy),kapi_lbl,fill=SARI,font=fsm,anchor='rm')
            od(draw,ox-35,gy-G//2,gy+G//2,f"{g_gen}m",fsm,SARI)
        else:
            draw.line([ox+pw,gy-G//2,ox+pw,gy+G//2],fill=SARI,width=8)
            draw.text((ox+pw+8,gy),kapi_lbl,fill=SARI,font=fsm,anchor='lm')
            od(draw,ox+pw+25,gy-G//2,gy+G//2,f"{g_gen}m",fsm,SARI)

    yuk_alani_ciz(g_duvar)

    # RAF ALAN SINIRI
    rax1 = ox+int(kb2*sx); ray1 = oy_val+int(kb2*sy)
    rax2 = ox+pw-int(kb2*sx); ray2 = oy_val+ph-int(kb2*sy)
    if g_duvar=='alt':   ray2 -= bp_y
    elif g_duvar=='ust': ray1 += bp_y
    elif g_duvar=='sol': rax1 += bp_x
    else:                rax2 -= bp_x

    raf_g_px  = max(int(raf_g*sx), 8)
    derinlik_px = max(int(DERINLIK*sy), 6)
    koridor_px  = max(int(koridor*sy), 4)
    blok_px   = derinlik_px * 2

    raflar = []
    raf_yan = sec['raf_yan']

    if tip == 'U_MAKS':
        # Raflar kapiya DIK: dik yonunde uzaniyorlar
        # Arka duvara bitisik raf (kapinin karsisi)
        if g_duvar == 'alt':
            # Arka = ust
            arka_ry1 = ray1
            arka_ry2 = arka_ry1 + derinlik_px
            for i in range(raf_yan):
                rx1r = rax1+int(i*raf_g*sx)
                rx2r = min(rx1r+raf_g_px-1, rax2)
                if rx1r>=rax2: break
                raflar.append((rx1r,arka_ry1,rx2r,arka_ry2,'arka'))
            draw.text((ox+pw+5,(arka_ry1+arka_ry2)//2),"Arka" if lang=='tr' else "Зад",fill=BEYAZ,font=fxs,anchor='lm')

            # Sol duvara (sol = soldan 1.1m)
            sol_rx1 = rax1; sol_rx2 = rax1+derinlik_px
            # Sag duvara
            sag_rx1 = rax2-derinlik_px; sag_rx2 = rax2

            sol_sag_basla = arka_ry2 + koridor_px
            for i in range(raf_yan):
                ry1r = sol_sag_basla+int(i*raf_g*sy)
                ry2r = min(ry1r+raf_g_px-1, ray2)
                if ry1r>=ray2: break
                raflar.append((sol_rx1,ry1r,sol_rx2,ry2r,'sol'))
                raflar.append((sag_rx1,ry1r,sag_rx2,ry2r,'sag'))

            # Orta sirt sirta bloklar
            orta_x1 = sol_rx2 + koridor_px
            orta_x2 = sag_rx1 - koridor_px
            if orta_x2 > orta_x1:
                y_pos = arka_ry2 + koridor_px
                for blk in range(sec['orta_blok']):
                    # Sirt sirta: once ust sira sonra alt sira
                    # Ust sira
                    ry1_b = y_pos
                    ry2_b = ry1_b + derinlik_px
                    # Alt sira
                    ry1_b2 = ry2_b
                    ry2_b2 = ry1_b2 + derinlik_px
                    for i in range(raf_yan):
                        rx1r=rax1+int(i*raf_g*sx); rx2r=min(rx1r+raf_g_px-1,rax2)
                        if rx1r>=rax2: break
                        # Sadece orta alan icinde
                        if rx1r >= orta_x1-5 or rx2r <= orta_x2+5:
                            raflar.append((rx1r,ry1_b,rx2r,ry2_b,'orta'))
                            raflar.append((rx1r,ry1_b2,rx2r,ry2_b2,'orta'))
                    # Blok etiketi
                    draw.text((ox+pw+5,(ry1_b+ry2_b2)//2),f"B{blk+1}",fill=MOR,font=fxs,anchor='lm')
                    od(draw,ox+pw+5,ry1_b,ry2_b2,f"{DERINLIK*2}m",fxs,MOR)
                    y_pos = ry2_b2 + koridor_px

        # Diger duvarlar icin (ust, sol, sag) benzer mantik
        else:
            # Basit yerlesim
            y_pos = ray1
            for blk in range(max(1,sec['orta_blok'])):
                ry1_b=y_pos; ry2_b=ry1_b+derinlik_px
                ry1_b2=ry2_b; ry2_b2=ry1_b2+derinlik_px
                for i in range(raf_yan):
                    rx1r=rax1+int(i*raf_g*sx); rx2r=min(rx1r+raf_g_px-1,rax2)
                    if rx1r>=rax2: break
                    raflar.append((rx1r,ry1_b,rx2r,ry2_b,'orta'))
                    raflar.append((rx1r,ry1_b2,rx2r,ry2_b2,'orta'))
                y_pos=ry2_b2+koridor_px
                if y_pos>ray2: break

    elif tip == 'I_MAKS':
        # Sadece sirt sirta bloklar, esit aralikli
        if g_duvar == 'alt':
            y_pos = ray1
            for blk in range(sec['blok_sayisi']):
                ry1_b=y_pos; ry2_b=ry1_b+derinlik_px
                ry1_b2=ry2_b; ry2_b2=ry1_b2+derinlik_px
                if ry2_b2>ray2: break
                for i in range(raf_yan):
                    rx1r=rax1+int(i*raf_g*sx); rx2r=min(rx1r+raf_g_px-1,rax2)
                    if rx1r>=rax2: break
                    raflar.append((rx1r,ry1_b,rx2r,ry2_b,'blok'))
                    raflar.append((rx1r,ry1_b2,rx2r,ry2_b2,'blok'))
                draw.text((ox+pw+5,(ry1_b+ry2_b2)//2),f"B{blk+1}",fill=MOR,font=fxs,anchor='lm')
                od(draw,ox+pw+5,ry1_b,ry2_b2,f"{DERINLIK*2:.1f}m",fxs,MOR)
                if blk>0:
                    prev_y2=ry1_b-koridor_px
                    od(draw,ox+pw+18,prev_y2,ry1_b,f"{koridor}m",fxs,MOR)
                y_pos=ry2_b2+koridor_px
        else:
            y_pos=ray1
            for blk in range(sec['blok_sayisi']):
                ry1_b=y_pos; ry2_b=ry1_b+derinlik_px
                ry1_b2=ry2_b; ry2_b2=ry1_b2+derinlik_px
                if ry2_b2>ray2: break
                for i in range(raf_yan):
                    rx1r=rax1+int(i*raf_g*sx); rx2r=min(rx1r+raf_g_px-1,rax2)
                    if rx1r>=rax2: break
                    raflar.append((rx1r,ry1_b,rx2r,ry2_b,'blok'))
                    raflar.append((rx1r,ry1_b2,rx2r,ry2_b2,'blok'))
                y_pos=ry2_b2+koridor_px
                if y_pos>ray2: break

    # Raf olcusu
    if raf_yan>0:
        oy(draw,rax1,rax1+raf_g_px,ray1-14,f"{raf_g}m",fsm,MOR)
    od(draw,rax1-18,ray1,ray1+derinlik_px,f"{DERINLIK}m",fsm,YESIL)

    # Raflari ciz
    for r in raflar:
        ciz_raf(draw,r[0],r[1],r[2],r[3])

    dikme_say = len(raflar)*4
    yatay_say = len(raflar)*kat*2
    derinlik_say = len(raflar)*2

    # Ana olcular
    oy(draw,ox,ox+pw,oy_val-20,f"{uzunluk}m",fn,BEYAZ)
    od(draw,ox-20,oy_val,oy_val+ph,f"{genislik}m",fn,BEYAZ)

    # DEPO VERİMİ - cizim icinde sag ust kose
    verim_x = ox+pw-160; verim_y = oy_val+8
    draw.rectangle([verim_x,verim_y,verim_x+155,verim_y+75], fill='#0d1f35', outline=SINIR, width=1)
    if lang=='tr':
        draw.text((verim_x+78,verim_y+8),"DEPO VERİMİ",fill=SARI,font=fsm,anchor='mt')
        draw.text((verim_x+8,verim_y+22),f"Raf Alani:  {sec['raf_alani']} m²",fill=BEYAZ,font=fxs)
        draw.text((verim_x+8,verim_y+34),f"Yukleme:    {sec['yukleme_alani']} m²",fill=YESIL2,font=fxs)
        draw.text((verim_x+8,verim_y+46),f"Depo Alani: {sec['depo_alani']} m²",fill=AGRI,font=fxs)
        draw.text((verim_x+78,verim_y+60),f"%{sec['verim']} VERİM",fill=SARI,font=fb,anchor='mt')
    else:
        draw.text((verim_x+78,verim_y+8),"КПД СКЛАДА",fill=SARI,font=fsm,anchor='mt')
        draw.text((verim_x+8,verim_y+22),f"Площ.стелл: {sec['raf_alani']} м²",fill=BEYAZ,font=fxs)
        draw.text((verim_x+8,verim_y+34),f"Зона:       {sec['yukleme_alani']} м²",fill=YESIL2,font=fxs)
        draw.text((verim_x+8,verim_y+46),f"Площ.скл.:  {sec['depo_alani']} м²",fill=AGRI,font=fxs)
        draw.text((verim_x+78,verim_y+60),f"КПД: {sec['verim']}%",fill=SARI,font=fb,anchor='mt')

    # ALT BİLGİ
    iy = H-INFO_H
    draw.rectangle([0,iy,W,H],fill='#161b22')
    draw.line([0,iy,W,iy],fill='#404060',width=2)

    lx,ly=20,iy+14
    if lang=='tr':
        draw.text((lx,ly),"MALZEME LİSTESİ",fill=SARI,font=fb); ly+=22
        draw.text((lx,ly),"● Dikme:",fill=MAVI,font=fb)
        draw.text((lx+100,ly),f"1 adet={raf_yuk}m  |  {dikme_say} adet  |  Toplam: {round(dikme_say*raf_yuk,1)}m",fill=BEYAZ,font=fn); ly+=22
        draw.text((lx,ly),"━ Yatay Bag.:",fill=TURUNCU,font=fb)
        draw.text((lx+100,ly),f"1 adet={raf_g}m  |  {yatay_say} adet  |  Toplam: {round(yatay_say*raf_g,1)}m",fill=BEYAZ,font=fn); ly+=22
        draw.text((lx,ly),"| Derinlik:",fill=YESIL,font=fb)
        draw.text((lx+100,ly),f"1 adet=1.10m  |  {derinlik_say} adet  |  Toplam: {round(derinlik_say*1.1,1)}m",fill=BEYAZ,font=fn); ly+=22
        draw.text((lx,ly),"▦ Yukleme Alani:",fill=YESIL2,font=fb)
        draw.text((lx+130,ly),f"{yukleme_en}×{yukleme_boy}m = {yukleme_m2} m²",fill=YESIL2,font=fn); ly+=22
        draw.text((lx,ly),"↔ Koridor:",fill=MOR,font=fb)
        draw.text((lx+100,ly),f"{koridor}m  |  Kapi: {g_gen}m",fill=BEYAZ,font=fn)
    else:
        draw.text((lx,ly),"СПИСОК МАТЕРИАЛОВ",fill=SARI,font=fb); ly+=22
        draw.text((lx,ly),"● Стойка:",fill=MAVI,font=fb)
        draw.text((lx+90,ly),f"1 шт={raf_yuk}м  |  {dikme_say} шт  |  Итого: {round(dikme_say*raf_yuk,1)}м",fill=BEYAZ,font=fn); ly+=22
        draw.text((lx,ly),"━ Балка:",fill=TURUNCU,font=fb)
        draw.text((lx+90,ly),f"1 шт={raf_g}м  |  {yatay_say} шт  |  Итого: {round(yatay_say*raf_g,1)}м",fill=BEYAZ,font=fn); ly+=22
        draw.text((lx,ly),"| Глубина:",fill=YESIL,font=fb)
        draw.text((lx+90,ly),f"1 шт=1.10м  |  {derinlik_say} шт  |  Итого: {round(derinlik_say*1.1,1)}м",fill=BEYAZ,font=fn); ly+=22
        draw.text((lx,ly),"▦ Зона погрузки:",fill=YESIL2,font=fb)
        draw.text((lx+130,ly),f"{yukleme_en}×{yukleme_boy}м = {yukleme_m2} м²",fill=YESIL2,font=fn); ly+=22
        draw.text((lx,ly),"↔ Проход:",fill=MOR,font=fb)
        draw.text((lx+90,ly),f"{koridor}м  |  Ворота: {g_gen}м",fill=BEYAZ,font=fn)

    # Sag sutun - verim ozeti
    rx2b,ry2b=W//2+20,iy+14
    if lang=='tr':
        draw.text((rx2b,ry2b),"VERİM ANALİZİ",fill=SARI,font=fb); ry2b+=22
        kapasite=sec['toplam']*kat*d['palet']
        for k,v in [
            ("Toplam Raf",   str(sec['toplam'])),
            ("Palet Kap.",   f"{kapasite} palet"),
            ("Raf Alani",    f"{sec['raf_alani']} m²"),
            ("Depo Verimi",  f"%{sec['verim']}"),
            ("Kat / Raf Yuk.",f"{kat} / {raf_yuk}m"),
        ]:
            draw.text((rx2b,ry2b),f"{k}:",fill=AGRI,font=fn)
            draw.text((rx2b+165,ry2b),v,fill=BEYAZ,font=fb); ry2b+=22
    else:
        draw.text((rx2b,ry2b),"АНАЛИЗ КПД",fill=SARI,font=fb); ry2b+=22
        kapasite=sec['toplam']*kat*d['palet']
        for k,v in [
            ("Стеллажей",    str(sec['toplam'])),
            ("Ёмкость",      f"{kapasite} палл."),
            ("Пл.стеллажей", f"{sec['raf_alani']} м²"),
            ("КПД склада",   f"{sec['verim']}%"),
            ("Яр./Выс.",     f"{kat}/{raf_yuk}м"),
        ]:
            draw.text((rx2b,ry2b),f"{k}:",fill=AGRI,font=fn)
            draw.text((rx2b+165,ry2b),v,fill=BEYAZ,font=fb); ry2b+=22

    buf=io.BytesIO()
    img.save(buf,format='PNG',dpi=(150,150))
    buf.seek(0)
    return buf

# ---- HANDLERS ----
async def baslat(update, context):
    context.user_data.clear()
    await update.message.reply_text("Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce","🇷🇺 Russkiy"]]))
    return LANG

async def lang_sec(update, context):
    t=update.message.text
    context.user_data['lang']='ru' if "Russkiy" in t else 'tr'
    lang=get_lang(context)
    await update.message.reply_text("📏 Depo uzunlugu (m):\nOrnek: 20" if lang=='tr' else "📏 Длина склада (м):\nПример: 20",reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['uzunluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Depo genisligi (m):\nOrnek: 12" if lang=='tr' else "📐 Ширина склада (м):\nПример: 12")
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return UZUNLUK

async def genislik_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📏 Depo yuksekligi (m):\nOrnek: 6" if lang=='tr' else "📏 Высота склада (м):\nПример: 6")
        return DEPO_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GENISLIK

async def depo_yuk_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['depo_yukseklik']=float(update.message.text.replace(',','.'))
        if lang=='tr':
            await update.message.reply_text("🚪 Giris kapisi hangi duvarda?",reply_markup=kb([["Alt duvar","Ust duvar"],["Sol duvar","Sag duvar"]]))
        else:
            await update.message.reply_text("🚪 На какой стене вход?",reply_markup=kb([["Нижняя стена","Верхняя стена"],["Левая стена","Правая стена"]]))
        return GIRIS_DUVAR
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return DEPO_YUK

async def giris_duvar_h(update,context):
    lang=get_lang(context)
    t=update.message.text.lower()
    if "alt" in t or "нижн" in t: context.user_data['giris_duvar']='alt'
    elif "ust" in t or "верхн" in t: context.user_data['giris_duvar']='ust'
    elif "sol" in t or "лев" in t: context.user_data['giris_duvar']='sol'
    else: context.user_data['giris_duvar']='sag'
    if lang=='tr':
        await update.message.reply_text("🚪 Kapinin konumu?",reply_markup=kb([["Sol yakin","Orta","Sag yakin"]]))
    else:
        await update.message.reply_text("🚪 Где именно вход?",reply_markup=kb([["Левее","По центру","Правее"]]))
    return GIRIS_KONUM

async def giris_konum_h(update,context):
    lang=get_lang(context)
    t=update.message.text.lower()
    if "orta" in t or "центру" in t:
        context.user_data['giris_konum']='orta'; context.user_data['giris_mesafe']=0.0
    elif "sol" in t or "левее" in t: context.user_data['giris_konum']='sol'
    else: context.user_data['giris_konum']='sag'
    if context.user_data['giris_konum']=='orta':
        await update.message.reply_text("🚪 Kapi genisligi (m):\nOrnek: 4" if lang=='tr' else "🚪 Ширина ворот (м):\nПример: 4",reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    else:
        await update.message.reply_text("🚪 Koseden kac metre?\nOrnek: 2" if lang=='tr' else "🚪 Расстояние от угла (м)?\nПример: 2",reply_markup=ReplyKeyboardRemove())
        return GIRIS_MESAFE

async def giris_mesafe_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['giris_mesafe']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("🚪 Kapi genisligi (m):\nOrnek: 4" if lang=='tr' else "🚪 Ширина ворот (м):\nПример: 4",reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_MESAFE

async def giris_genislik_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['giris_genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("🏗 Yukleme/bosaltma alani (m):\nOrnek: 5" if lang=='tr' else "🏗 Зона погрузки/разгрузки (м):\nПример: 5",reply_markup=kb([["3","4","5","6","8"]]))
        return GIRIS_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_GENISLIK

async def giris_bosluk_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['giris_bosluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Raf-duvar arasi bosluk?\n0=bitisik" if lang=='tr' else "📐 Отступ от стен?\n0=вплотную",reply_markup=kb([["0","0.3","0.5"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return GIRIS_BOSLUK

async def kenar_bosluk_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['kenar_bosluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("🚦 Koridor tipi?\nForklift 3m | Transpalet 2m | El 1.2m" if lang=='tr' else "🚦 Тип прохода?\nПогрузчик 3м | Транспалет 2м | Ручной 1.2м",reply_markup=kb([["Forklift","Transpalet","El ile" if lang=='tr' else "Ruchnoy"]]))
        return KORIDOR_TIPI
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return KENAR_BOSLUK

async def koridor_h(update,context):
    lang=get_lang(context)
    t=update.message.text.lower()
    if "forklift" in t or "погрузчик" in t: context.user_data['koridor_tipi']='forklift'
    elif "transpalet" in t or "транспалет" in t: context.user_data['koridor_tipi']='transpalet'
    else: context.user_data['koridor_tipi']='el'
    await update.message.reply_text("📦 Raf basina palet?\n1=0.95m  2=1.85m\n3=2.70m  4=3.60m" if lang=='tr' else "📦 Паллет на ряд?\n1=0.95м  2=1.85м\n3=2.70м  4=3.60м",reply_markup=kb([["1","2"],["3","4"]]))
    return PALET

async def palet_h(update,context):
    lang=get_lang(context)
    try:
        v=int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet']=v
        await update.message.reply_text("🏗 Kat sayisi?\nOrnek: 3" if lang=='tr' else "🏗 Количество ярусов?\nПример: 3",reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1-4 girin." if lang=='tr' else "Введите 1-4.")
        return PALET

async def kat_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['kat']=int(update.message.text)
        await update.message.reply_text("📏 Raf yuksekligi (m)?\nOrnek: 5" if lang=='tr' else "📏 Высота стеллажа (м)?\nПример: 5")
        return RAF_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lang=='tr' else "Только цифры.")
        return KAT

async def raf_yuk_h(update,context):
    lang=get_lang(context)
    try:
        context.user_data['raf_yuk']=float(update.message.text.replace(',','.'))
        d=context.user_data
        layouts=hesapla_layout(d)
        await update.message.reply_text("⏳ 2 secenek hazirlaniyor..." if lang=='tr' else "⏳ Готовлю 2 варианта...",reply_markup=ReplyKeyboardRemove())

        secenekler=[layouts['U_MAKS'],layouts['I_MAKS']]
        secenekler.sort(key=lambda x: x['toplam'],reverse=True)

        for i,sec in enumerate(secenekler):
            resim=teknik_ciz(d,lang,sec,i+1,2)
            t_tr={'U_MAKS':'U-MAKS: Duvar+Orta','I_MAKS':'I-MAKS: Sirt Sirta'}
            t_ru={'U_MAKS':'U-МАКС: Стены+Центр','I_MAKS':'I-МАКС: Спина к спине'}
            t_ad=t_ru.get(sec['tip'],sec['tip']) if lang=='ru' else t_tr.get(sec['tip'],sec['tip'])
            kapasite=sec['toplam']*d['kat']*d['palet']
            if lang=='tr':
                cap=f"{'⭐ EN İYİ — ' if i==0 else ''}{i+1}. SECENEK: {t_ad}\nToplam raf: {sec['toplam']} | Kapasite: {kapasite} palet | Verim: %{sec['verim']}"
            else:
                cap=f"{'⭐ ЛУЧШИЙ — ' if i==0 else ''}{i+1}. ВАРИАНТ: {t_ad}\nСтеллажей: {sec['toplam']} | Ёмкость: {kapasite} палл. | КПД: {sec['verim']}%"
            await update.message.reply_photo(photo=resim,caption=cap)

        await update.message.reply_text("✅ Hazir! Fiyat icin: /hesapla" if lang=='tr' else "✅ Готово! Расчёт: /raschet")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

async def iptal(update,context):
    lang=get_lang(context)
    await update.message.reply_text("Iptal. /hesapla" if lang=='tr' else "Отменено. /raschet",reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    app=ApplicationBuilder().token(TOKEN).build()
    conv=ConversationHandler(
        entry_points=[CommandHandler('start',baslat),CommandHandler('hesapla',baslat),CommandHandler('raschet',baslat)],
        states={
            LANG:          [MessageHandler(filters.TEXT&~filters.COMMAND,lang_sec)],
            UZUNLUK:       [MessageHandler(filters.TEXT&~filters.COMMAND,uzunluk_h)],
            GENISLIK:      [MessageHandler(filters.TEXT&~filters.COMMAND,genislik_h)],
            DEPO_YUK:      [MessageHandler(filters.TEXT&~filters.COMMAND,depo_yuk_h)],
            GIRIS_DUVAR:   [MessageHandler(filters.TEXT&~filters.COMMAND,giris_duvar_h)],
            GIRIS_KONUM:   [MessageHandler(filters.TEXT&~filters.COMMAND,giris_konum_h)],
            GIRIS_MESAFE:  [MessageHandler(filters.TEXT&~filters.COMMAND,giris_mesafe_h)],
            GIRIS_GENISLIK:[MessageHandler(filters.TEXT&~filters.COMMAND,giris_genislik_h)],
            GIRIS_BOSLUK:  [MessageHandler(filters.TEXT&~filters.COMMAND,giris_bosluk_h)],
            KENAR_BOSLUK:  [MessageHandler(filters.TEXT&~filters.COMMAND,kenar_bosluk_h)],
            KORIDOR_TIPI:  [MessageHandler(filters.TEXT&~filters.COMMAND,koridor_h)],
            PALET:         [MessageHandler(filters.TEXT&~filters.COMMAND,palet_h)],
            KAT:           [MessageHandler(filters.TEXT&~filters.COMMAND,kat_h)],
            RAF_YUK:       [MessageHandler(filters.TEXT&~filters.COMMAND,raf_yuk_h)],
        },
        fallbacks=[CommandHandler('iptal',iptal)],
    )
    app.add_handler(conv)
    app.run_polling()
