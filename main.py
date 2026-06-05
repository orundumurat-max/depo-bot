import os, logging, io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, UZUNLUK, GENISLIK, DEPO_YUK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_GENISLIK,
 YUK_EN, YUK_BOY,
 KENAR_BOSLUK, KORIDOR_TIPI, PALET, KAT, RAF_YUK) = range(15)

PALET_G  = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_G = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}
DERINLIK  = 1.1   # raf derinligi (koridorun yaninda, sabit)

def glang(c): return c.user_data.get('lang','tr')
def kb(r):    return ReplyKeyboardMarkup(r, one_time_keyboard=True, resize_keyboard=True)

# ═══════════════════════════════════════════════
#  HESAPLAMA
#  Koridorlar KAPIYA DIK uzaniyor.
#  Her koridor iki yaninda raf sirasi var.
#  Raf birimi: genislik = DERINLIK (koridorun yaninda 1.1m)
#              uzunluk  = palet_g (koridorun boyunca)
#  Kapı alttaysa:
#    - Koridorlar dikey (y yonu) uzaniyor
#    - Her koridor saginda ve solunda raf var
#    - Raf genisligi (x yonu) = palet_g
#    - Raf derinligi (y yonu) = DERINLIK = 1.1m
#    - Raf gruplar: [raf|koridor|raf] bloklari
# ═══════════════════════════════════════════════

def hesapla_layout(d):
    U   = d['uzunluk'];  G = d['genislik']
    pg  = PALET_G[d['palet']]
    kor = KORIDOR_G[d['koridor_tipi']]
    kb2 = d.get('kenar_bosluk', 0.0)
    gd  = d.get('giris_duvar', 'alt')
    yen = d.get('yuk_en', 5.0)
    ybo = d.get('yuk_boy', 5.0)
    kat = d['kat']

    # Yükleme alani kapiya dik yonde (boy), kapiya paralel yonde (en)
    # Kapı alt/ust: yükleme alani = uzunluk boyunca en, genislik yonunde boy
    if gd in ['alt','ust']:
        ef_uzun = U - kb2*2          # koridorun uzadigi yön (X)
        ef_gen  = G - kb2*2 - ybo   # koridorun uzunlugu (Y), yükleme cikarildi
        yuk_m2  = round(U * ybo, 1)
        yuk_goster_en = U; yuk_goster_boy = ybo
    else:
        ef_uzun = U - kb2*2 - ybo
        ef_gen  = G - kb2*2
        yuk_m2  = round(G * ybo, 1)
        yuk_goster_en = ybo; yuk_goster_boy = G

    ef_uzun = max(ef_uzun, 0.1)
    ef_gen  = max(ef_gen,  0.1)

    # Paralel yonde (X = uzunluk) kac raf yan yana: her raf pg genisliginde
    raf_x = max(1, int(ef_uzun / pg))

    # Dik yonde (Y = genislik) raf bloklari:
    # Her blok: DERINLIK + koridor + DERINLIK = 2*DERINLIK + koridor
    blok_boy = DERINLIK * 2 + kor   # bir raf ciftinin toplam genisligi

    # ── U_MAKS ──────────────────────────────────────
    # Kapiya dik koridorlar + duvar raflari
    # Sol duvar: 1 sira (X=0, derinlik = DERINLIK)
    # Sag duvar: 1 sira (X=max, derinlik = DERINLIK)
    # Ortada: sirt sirta raf bloklari (raf|kor|raf)
    # Arka duvar (kapinin karsisi): 1 sira
    ic_uzun = ef_uzun - DERINLIK*2 - kor*2  # sol+sag duvar raflari cikarildi
    ic_uzun = max(ic_uzun, 0)
    orta_blok_u = max(0, int(ic_uzun / blok_boy))

    u_raf_toplam = (
        max(1, int(ef_gen / pg)) +           # sol duvar
        max(1, int(ef_gen / pg)) +           # sag duvar
        max(1, int(ef_gen / pg)) +           # arka duvar
        orta_blok_u * 2 * max(1, int(ef_gen / pg))  # orta bloklar
    )
    u_alan = (
        DERINLIK * ef_gen * 2 +              # sol+sag
        pg * ef_uzun +                       # arka
        orta_blok_u * blok_boy * ef_gen
    )

    # ── I_MAKS ──────────────────────────────────────
    # Sadece sirt sirta raf bloklari (kapiya dik koridorlar)
    # Bloklar X yonunde yan yana
    i_blok = max(1, int(ef_uzun / blok_boy))
    i_raf_toplam = i_blok * 2 * max(1, int(ef_gen / pg))
    i_alan = i_blok * blok_boy * ef_gen

    depo_alani = round(U * G, 1)

    return {
        'U_MAKS': {
            'tip':'U_MAKS', 'toplam':u_raf_toplam,
            'raf_x':raf_x, 'orta_blok':orta_blok_u,
            'ef_uzun':ef_uzun, 'ef_gen':ef_gen,
            'raf_alani':round(min(u_alan, U*G*0.9),1),
            'depo_alani':depo_alani, 'yuk_m2':yuk_m2,
            'yuk_en':yuk_goster_en, 'yuk_boy':yuk_goster_boy,
            'verim':round(min(u_alan,U*G*0.9)/depo_alani*100,1),
            'kapasite':u_raf_toplam*kat*d['palet'],
        },
        'I_MAKS': {
            'tip':'I_MAKS', 'toplam':i_raf_toplam,
            'raf_x':raf_x, 'blok':i_blok,
            'ef_uzun':ef_uzun, 'ef_gen':ef_gen,
            'raf_alani':round(i_alan,1),
            'depo_alani':depo_alani, 'yuk_m2':yuk_m2,
            'yuk_en':yuk_goster_en, 'yuk_boy':yuk_goster_boy,
            'verim':round(i_alan/depo_alani*100,1),
            'kapasite':i_raf_toplam*kat*d['palet'],
        },
    }

# ═══════════════════════════════════════════════
#  RAF BİRİMİ ÇİZİMİ
#  Kapı altta ise:
#    x1..x2 = palet_g genisliginde (X yonu, koridorun boyunca)
#    y1..y2 = DERINLIK yuksekliginde (Y yonu, koridorun yaninda)
#  Yatay bağlantı: X yonunde UST ve ALT kenar (koridora bakan yuz)
#  Derinlik:       Y yonunde SOL ve SAG kenar
# ═══════════════════════════════════════════════

def ciz_raf(draw, x1, y1, x2, y2):
    draw.rectangle([x1,y1,x2,y2], fill='#081420')
    draw.line([x1,y1,x2,y2], fill='#1a2535', width=1)
    draw.line([x2,y1,x1,y2], fill='#1a2535', width=1)
    draw.rectangle([x1,y1,x2,y2], outline='#2a3a50', width=1)
    # Yatay baglanti: UST ve ALT kenar (koridora bakan yuz = raf on yuzu)
    draw.line([x1+3, y1, x2-3, y1], fill='#ff8c42', width=3)
    draw.line([x1+3, y2, x2-3, y2], fill='#ff8c42', width=3)
    # Derinlik: SOL ve SAG kenar
    draw.line([x1, y1+3, x1, y2-3], fill='#4ade80', width=2)
    draw.line([x2, y1+3, x2, y2-3], fill='#4ade80', width=2)
    # Dikmeler
    for px,py in [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]:
        draw.ellipse([px-4,py-4,px+4,py+4], fill='#4a9eff', outline='white', width=1)

def olcu_y(draw,x1,x2,y,t,f,c):
    draw.line([x1,y,x2,y],fill=c,width=1)
    draw.line([x1,y-4,x1,y+4],fill=c,width=2)
    draw.line([x2,y-4,x2,y+4],fill=c,width=2)
    draw.text(((x1+x2)//2,y-5),t,fill=c,font=f,anchor='mb')

def olcu_d(draw,x,y1,y2,t,f,c):
    draw.line([x,y1,x,y2],fill=c,width=1)
    draw.line([x-4,y1,x+4,y1],fill=c,width=2)
    draw.line([x-4,y2,x+4,y2],fill=c,width=2)
    draw.text((x+5,(y1+y2)//2),t,fill=c,font=f,anchor='lm')

# ═══════════════════════════════════════════════
#  TEKNİK ÇİZİM
# ═══════════════════════════════════════════════

def ciz_teknik(d, lg, sec, sira):
    U   = d['uzunluk'];  G = d['genislik']
    pg  = PALET_G[d['palet']]
    kor = KORIDOR_G[d['koridor_tipi']]
    kb2 = d.get('kenar_bosluk', 0.0)
    gd  = d.get('giris_duvar', 'alt')
    gk  = d.get('giris_konum', 'orta')
    gm  = d.get('giris_mesafe', 0.0)
    gg  = d.get('giris_genislik', 4.0)
    kat = d['kat'];  ry = d['raf_yuk']
    tip = sec['tip']
    yen = sec['yuk_en'];  ybo = sec['yuk_boy'];  ym2 = sec['yuk_m2']

    W,H = 1200, 960
    img  = Image.new('RGB',(W,H),'#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
        fn  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",12)
        ft  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",17)
        fsm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",10)
        fxs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",9)
    except:
        fb=fn=ft=fsm=fxs=ImageFont.load_default()

    W2='#e8e8e8'; AG='#505070'; SA='#ffd700'
    SI='#00b4d8'; MO='#c084fc'; YE='#22c55e'
    TU='#ff8c42'; GR='#4ade80'; MA='#4a9eff'

    INFO_H = 165
    pl,pt,pr,pb = 80,55,135,INFO_H+48
    pw = W-pl-pr;  ph = H-pt-pb
    ox = pl;  oy0 = pt
    sx = pw/U;  sy = ph/G

    # ── BAŞLIK ──────────────────────────────────
    draw.rectangle([0,0,W,42],fill='#161b22')
    tad = {'U_MAKS':('U-MAKS: Duvar+Orta','U-МАКС: Стены+Центр'),
           'I_MAKS':('I-MAKS: Sirt Sirta Koridorlar','I-МАКС: Проходы спина к спине')}
    tn = tad.get(tip,(tip,tip))[1 if lg=='ru' else 0]
    if lg=='tr':
        bl = f"SECENEK {sira}/2  ●  {tn}  ●  {sec['toplam']} raf  ●  Verim:%{sec['verim']}"
    else:
        bl = f"ВАРИАНТ {sira}/2  ●  {tn}  ●  {sec['toplam']} стелл.  ●  КПД:{sec['verim']}%"
    draw.text((W//2,21),bl,fill=SA,font=ft,anchor='mm')

    # ── DEPO SINIRI ─────────────────────────────
    draw.rectangle([ox,oy0,ox+pw,oy0+ph],outline=SI,width=3)
    draw.rectangle([ox+2,oy0+2,ox+pw-2,oy0+ph-2],outline='#1a3a5c',width=1)

    # ── KAPI KONUMU ─────────────────────────────
    Gpx = max(int(gg*sx),35)
    gx = gy = 0
    if gd in ['alt','ust']:
        if gk=='orta':  gx=ox+pw//2
        elif gk=='sol': gx=ox+int(gm*sx)+Gpx//2
        else:           gx=ox+pw-int(gm*sx)-Gpx//2
    else:
        if gk=='orta':  gy=oy0+ph//2
        elif gk=='ust': gy=oy0+int(gm*sy)+Gpx//2
        else:           gy=oy0+ph-int(gm*sy)-Gpx//2

    # ── YÜKLEME ALANI ───────────────────────────
    # Kapiya dik yonde (boy), kapiya paralel yonde kapıyı ortalar (en)
    if gd in ['alt','ust']:
        yuk_en_px  = int(yen*sx)
        yuk_boy_px = int(ybo*sy)
    else:
        yuk_en_px  = int(yen*sy)
        yuk_boy_px = int(ybo*sx)

    kapi_lbl = "GİRİŞ/ÇIKIŞ" if lg=='tr' else "ВХОД/ВЫХОД"
    zona = "YUKLEME/BOSALTMA" if lg=='tr' else "ЗОНА ПОГРУЗКИ"

    if gd=='alt':
        # Yükleme alani altta, kapi ortalanmis
        yx1 = gx - yuk_en_px//2;  yx2 = gx + yuk_en_px//2
        yx1 = max(ox+2,yx1);       yx2 = min(ox+pw-2,yx2)
        yy1 = oy0+ph-yuk_boy_px;   yy2 = oy0+ph-2
        draw.rectangle([yx1,yy1,yx2,yy2],fill='#031a0d',outline=YE,width=2)
        draw.text(((yx1+yx2)//2,(yy1+yy2)//2-8),zona,fill=YE,font=fxs,anchor='mm')
        draw.text(((yx1+yx2)//2,(yy1+yy2)//2+8),f"{yen}×{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
        olcu_y(draw,yx1,yx2,yy1-12,f"{yen}m",fsm,YE)
        olcu_d(draw,yx2+8,yy1,yy2,f"{ybo}m",fsm,YE)
        draw.line([gx-Gpx//2,oy0+ph,gx+Gpx//2,oy0+ph],fill=SA,width=8)
        draw.text((gx,oy0+ph+10),kapi_lbl,fill=SA,font=fsm,anchor='mt')
        olcu_y(draw,gx-Gpx//2,gx+Gpx//2,oy0+ph+24,f"{gg}m",fsm,SA)
        if gm>0 and gk!='orta':
            if gk=='sol': olcu_y(draw,ox,gx-Gpx//2,oy0+ph+38,f"{gm}m",fsm,W2)
            else: olcu_y(draw,gx+Gpx//2,ox+pw,oy0+ph+38,f"{gm}m",fsm,W2)

    elif gd=='ust':
        yx1=gx-yuk_en_px//2; yx2=gx+yuk_en_px//2
        yx1=max(ox+2,yx1); yx2=min(ox+pw-2,yx2)
        yy1=oy0+2; yy2=oy0+yuk_boy_px
        draw.rectangle([yx1,yy1,yx2,yy2],fill='#031a0d',outline=YE,width=2)
        draw.text(((yx1+yx2)//2,(yy1+yy2)//2-8),zona,fill=YE,font=fxs,anchor='mm')
        draw.text(((yx1+yx2)//2,(yy1+yy2)//2+8),f"{yen}×{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
        olcu_d(draw,yx2+8,yy1,yy2,f"{ybo}m",fsm,YE)
        draw.line([gx-Gpx//2,oy0,gx+Gpx//2,oy0],fill=SA,width=8)
        draw.text((gx,oy0-10),kapi_lbl,fill=SA,font=fsm,anchor='mb')
        olcu_y(draw,gx-Gpx//2,gx+Gpx//2,oy0-22,f"{gg}m",fsm,SA)

    elif gd=='sol':
        yy1=gy-yuk_en_px//2; yy2=gy+yuk_en_px//2
        yy1=max(oy0+2,yy1); yy2=min(oy0+ph-2,yy2)
        yx1=ox+2; yx2=ox+yuk_boy_px
        draw.rectangle([yx1,yy1,yx2,yy2],fill='#031a0d',outline=YE,width=2)
        draw.text(((yx1+yx2)//2,(yy1+yy2)//2-8),zona,fill=YE,font=fxs,anchor='mm')
        draw.text(((yx1+yx2)//2,(yy1+yy2)//2+8),f"{yen}×{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
        olcu_d(draw,yx1-12,yy1,yy2,f"{yen}m",fsm,YE)
        olcu_y(draw,yx1,yx2,yy2+12,f"{ybo}m",fsm,YE)
        draw.line([ox,gy-Gpx//2,ox,gy+Gpx//2],fill=SA,width=8)
        draw.text((ox-8,gy),kapi_lbl,fill=SA,font=fsm,anchor='rm')
        olcu_d(draw,ox-35,gy-Gpx//2,gy+Gpx//2,f"{gg}m",fsm,SA)
        if gm>0 and gk!='orta':
            if gk=='ust': olcu_d(draw,ox-50,oy0,gy-Gpx//2,f"{gm}m",fsm,W2)
            else: olcu_d(draw,ox-50,gy+Gpx//2,oy0+ph,f"{gm}m",fsm,W2)

    else:  # sag
        yy1=gy-yuk_en_px//2; yy2=gy+yuk_en_px//2
        yy1=max(oy0+2,yy1); yy2=min(oy0+ph-2,yy2)
        yx1=ox+pw-yuk_boy_px; yx2=ox+pw-2
        draw.rectangle([yx1,yy1,yx2,yy2],fill='#031a0d',outline=YE,width=2)
        draw.text(((yx1+yx2)//2,(yy1+yy2)//2-8),zona,fill=YE,font=fxs,anchor='mm')
        draw.text(((yx1+yx2)//2,(yy1+yy2)//2+8),f"{yen}×{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
        olcu_d(draw,yx2+8,yy1,yy2,f"{yen}m",fsm,YE)
        olcu_y(draw,yx1,yx2,yy2+12,f"{ybo}m",fsm,YE)
        draw.line([ox+pw,gy-Gpx//2,ox+pw,gy+Gpx//2],fill=SA,width=8)
        draw.text((ox+pw+8,gy),kapi_lbl,fill=SA,font=fsm,anchor='lm')
        olcu_d(draw,ox+pw+25,gy-Gpx//2,gy+Gpx//2,f"{gg}m",fsm,SA)
        if gm>0 and gk!='orta':
            if gk=='ust': olcu_d(draw,ox+pw+40,oy0,gy-Gpx//2,f"{gm}m",fsm,W2)
            else: olcu_d(draw,ox+pw+40,gy+Gpx//2,oy0+ph,f"{gm}m",fsm,W2)

    # ── RAF ALANI SINIRLARI ──────────────────────
    rax1=ox+int(kb2*sx); ray1=oy0+int(kb2*sy)
    rax2=ox+pw-int(kb2*sx); ray2=oy0+ph-int(kb2*sy)
    if   gd=='alt': ray2=min(ray2,yy1 if gd=='alt' else oy0+ph-int(d.get('yuk_boy',3)*sy))
    elif gd=='ust': ray1=max(ray1,yy2 if 'yy2' in dir() else oy0+int(d.get('yuk_boy',3)*sy))
    elif gd=='sol': rax1=max(rax1,yx2 if 'yx2' in dir() else ox+int(d.get('yuk_boy',3)*sx))
    else:           rax2=min(rax2,yx1 if 'yx1' in dir() else ox+pw-int(d.get('yuk_boy',3)*sx))

    # Yükleme alani duzeltmesi
    if gd=='alt':   ray2=oy0+ph-int(d.get('yuk_boy',3)*sy)-int(kb2*sy)
    elif gd=='ust': ray1=oy0+int(d.get('yuk_boy',3)*sy)+int(kb2*sy)
    elif gd=='sol': rax1=ox+int(d.get('yuk_boy',3)*sx)+int(kb2*sx)
    else:           rax2=ox+pw-int(d.get('yuk_boy',3)*sx)-int(kb2*sx)

    # Piksel dönüşümleri
    # Kapı alt/üst: X=uzunluk(paralel), Y=genislik(dik=koridorlar)
    # Kapı sol/sag: X=uzunluk(dik),    Y=genislik(paralel)
    if gd in ['alt','ust']:
        pg_px   = max(int(pg*sx),8)        # raf genisligi: X yonu (kapiya paralel)
        dr_px   = max(int(DERINLIK*sy),6)  # raf derinligi: Y yonu (kapiya dik)
        kor_px  = max(int(kor*sy),4)       # koridor: Y yonu (kapiya dik)
        blok_px = dr_px*2 + kor_px         # raf+kor+raf
    else:
        pg_px   = max(int(pg*sy),8)
        dr_px   = max(int(DERINLIK*sx),6)
        kor_px  = max(int(kor*sx),4)
        blok_px = dr_px*2 + kor_px

    raflar = []

    # ══════════════════════════════════════════
    # KAPIYA DIK KORIDOR = Y yonunde uzaniyor (kapı alt/ust icin)
    # Raf birimi: x genisligi=pg_px, y yuksekligi=dr_px
    # Blok: [raf_ust | koridor | raf_alt] y yonunde
    # X yonunde yan yana pg_px aralikli
    # ══════════════════════════════════════════

    if gd in ['alt','ust']:
        # X yonunde konum: her raf pg_px genisliginde
        # Y yonunde bloklar: [raf|kor|raf] tekrarlaniyor

        if tip=='I_MAKS':
            # Sadece sirt sirta bloklar
            # X yonunde blok_px araliklarla
            x_pos = rax1
            blk_no = 0
            while x_pos + dr_px*2 <= rax2 and blk_no < sec['blok']:
                bx1 = x_pos;       bx2 = bx1 + dr_px   # ilk raf derinligi
                bx3 = bx2 + kor_px; bx4 = bx3 + dr_px  # koridor sonra ikinci raf

                # Bu bloktaki raflari Y yonunde diz
                y_pos = ray1
                while y_pos + pg_px <= ray2:
                    # Sol taraf rafi (bx1..bx2, y_pos..y_pos+pg_px)
                    raflar.append((bx1, y_pos, bx2, y_pos+pg_px))
                    # Sag taraf rafi (bx3..bx4, y_pos..y_pos+pg_px)
                    raflar.append((bx3, y_pos, bx4, y_pos+pg_px))
                    y_pos += pg_px

                # Koridor olcusu
                olcu_y(draw, bx2, bx3, ray1-12, f"{kor}m", fsm, MO)
                # Derinlik olcusu
                olcu_d(draw, rax1-18, ray1, ray1+dr_px, f"{DERINLIK}m", fsm, GR)
                # Raf genisligi olcusu
                if blk_no==0:
                    olcu_d(draw, bx1-5, ray1, ray1+pg_px, f"{pg}m", fsm, MO)

                x_pos = bx4 + int(0.3*sx)  # bloklar arasi kucuk bosluk
                blk_no += 1

        elif tip=='U_MAKS':
            # Sol duvara bitisik raf (X=rax1..rax1+dr_px)
            # Sag duvara bitisik raf (X=rax2-dr_px..rax2)
            # Arka duvara bitisik raf (Y=ray1..ray1+dr_px veya ray2-dr_px..ray2)
            # Orta: sirt sirta bloklar

            sol_x1=rax1; sol_x2=rax1+dr_px
            sag_x1=rax2-dr_px; sag_x2=rax2

            # Arka duvar (kapinin karsisi)
            if gd=='alt':
                arka_y1=ray1; arka_y2=ray1+dr_px
            else:
                arka_y1=ray2-dr_px; arka_y2=ray2

            # Sol ve sag duvara raflar: Y yonunde pg_px aralikli
            y_pos=ray1
            while y_pos+pg_px<=ray2:
                raflar.append((sol_x1,y_pos,sol_x2,y_pos+pg_px))
                raflar.append((sag_x1,y_pos,sag_x2,y_pos+pg_px))
                y_pos+=pg_px

            # Arka duvara raflar: X yonunde pg_px aralikli (sol-sag arasi)
            x_pos=sol_x2+int(kor*sx)
            while x_pos+pg_px<=sag_x1-int(kor*sx):
                raflar.append((x_pos,arka_y1,x_pos+pg_px,arka_y2))
                x_pos+=pg_px

            # Derinlik olcusu
            olcu_d(draw,rax1-18,ray1,ray1+dr_px,f"{DERINLIK}m",fsm,GR)

            # Orta sirt sirta bloklar
            orta_x1=sol_x2+kor_px
            orta_x2=sag_x1-kor_px
            if gd=='alt':
                orta_y_start=arka_y2+kor_px
            else:
                orta_y_start=ray1

            x_pos=orta_x1
            blk_no=0
            while x_pos+dr_px*2+kor_px<=orta_x2 and blk_no<sec['orta_blok']:
                bx1=x_pos; bx2=bx1+dr_px
                bx3=bx2+kor_px; bx4=bx3+dr_px

                y_pos=orta_y_start
                while y_pos+pg_px<=ray2:
                    raflar.append((bx1,y_pos,bx2,y_pos+pg_px))
                    raflar.append((bx3,y_pos,bx4,y_pos+pg_px))
                    y_pos+=pg_px

                olcu_y(draw,bx2,bx3,orta_y_start-12,f"{kor}m",fsm,MO)
                x_pos=bx4+int(0.3*sx)
                blk_no+=1

    else:
        # Kapı sol/sag: koridorlar X yonunde uzaniyor
        # Y yonunde bloklar: [raf|kor|raf]
        if tip=='I_MAKS':
            y_pos=ray1
            blk_no=0
            while y_pos+dr_px*2+kor_px<=ray2 and blk_no<sec['blok']:
                by1=y_pos; by2=by1+dr_px
                by3=by2+kor_px; by4=by3+dr_px
                x_pos=rax1
                while x_pos+pg_px<=rax2:
                    raflar.append((x_pos,by1,x_pos+pg_px,by2))
                    raflar.append((x_pos,by3,x_pos+pg_px,by4))
                    x_pos+=pg_px
                y_pos=by4+int(0.3*sy)
                blk_no+=1

        elif tip=='U_MAKS':
            ust_y1=ray1; ust_y2=ray1+dr_px
            alt_y1=ray2-dr_px; alt_y2=ray2
            if gd=='sol':
                arka_x1=rax2-dr_px; arka_x2=rax2
            else:
                arka_x1=rax1; arka_x2=rax1+dr_px

            x_pos=rax1
            while x_pos+pg_px<=rax2:
                raflar.append((x_pos,ust_y1,x_pos+pg_px,ust_y2))
                raflar.append((x_pos,alt_y1,x_pos+pg_px,alt_y2))
                x_pos+=pg_px

            y_pos=ust_y2+int(kor*sy)
            while y_pos+pg_px<=alt_y1-int(kor*sy):
                raflar.append((arka_x1,y_pos,arka_x2,y_pos+pg_px))
                y_pos+=pg_px

            orta_y1=ust_y2+kor_px
            orta_y2=alt_y1-kor_px
            y_pos=orta_y1
            blk_no=0
            while y_pos+dr_px*2+kor_px<=orta_y2 and blk_no<sec['orta_blok']:
                by1=y_pos; by2=by1+dr_px
                by3=by2+kor_px; by4=by3+dr_px
                x_pos=rax1
                while x_pos+pg_px<=rax2:
                    raflar.append((x_pos,by1,x_pos+pg_px,by2))
                    raflar.append((x_pos,by3,x_pos+pg_px,by4))
                    x_pos+=pg_px
                y_pos=by4+int(0.3*sy)
                blk_no+=1

    # Raflari ciz
    for r in raflar:
        ciz_raf(draw,r[0],r[1],r[2],r[3])

    # Ana olcular
    olcu_y(draw,ox,ox+pw,oy0-20,f"{U}m",fn,W2)
    olcu_d(draw,ox-20,oy0,oy0+ph,f"{G}m",fn,W2)

    # Koridor yonu oku
    if gd in ['alt','ust']:
        mid_x = ox+pw//2
        draw.text((mid_x, oy0+ph//2), "↑↑ Koridor ↑↑" if lg=='tr' else "↑↑ Проход ↑↑", fill='#303050', font=fxs, anchor='mm')
    else:
        mid_y = oy0+ph//2
        draw.text((ox+pw//2, mid_y), "→→ Koridor →→" if lg=='tr' else "→→ Проход →→", fill='#303050', font=fxs, anchor='mm')

    # Depo verimi kutusu
    vx=ox+pw-168; vy=oy0+8
    draw.rectangle([vx,vy,vx+163,vy+82],fill='#0a1e35',outline=SI,width=1)
    if lg=='tr':
        draw.text((vx+82,vy+8),"DEPO VERİMİ",fill=SA,font=fsm,anchor='mt')
        draw.text((vx+6,vy+22),f"Raf Alani:   {sec['raf_alani']} m²",fill=W2,font=fxs)
        draw.text((vx+6,vy+34),f"Yukleme:     {sec['yuk_m2']} m²",fill=YE,font=fxs)
        draw.text((vx+6,vy+46),f"Depo Alani:  {sec['depo_alani']} m²",fill=AG,font=fxs)
        draw.text((vx+82,vy+62),f"%{sec['verim']} VERİM",fill=SA,font=fb,anchor='mt')
    else:
        draw.text((vx+82,vy+8),"КПД СКЛАДА",fill=SA,font=fsm,anchor='mt')
        draw.text((vx+6,vy+22),f"Пл.стелл.: {sec['raf_alani']} м²",fill=W2,font=fxs)
        draw.text((vx+6,vy+34),f"Зона:      {sec['yuk_m2']} м²",fill=YE,font=fxs)
        draw.text((vx+6,vy+46),f"Пл.склада: {sec['depo_alani']} м²",fill=AG,font=fxs)
        draw.text((vx+82,vy+62),f"КПД: {sec['verim']}%",fill=SA,font=fb,anchor='mt')

    # Alt bilgi
    iy=H-INFO_H
    draw.rectangle([0,iy,W,H],fill='#161b22')
    draw.line([0,iy,W,iy],fill='#404060',width=2)

    dk=len(raflar)*4; yt=len(raflar)*kat*2; dr=len(raflar)*2
    kap=sec['toplam']*kat*d['palet']

    lx,ly=20,iy+14
    if lg=='tr':
        draw.text((lx,ly),"MALZEME LİSTESİ",fill=SA,font=fb); ly+=22
        draw.text((lx,ly),"● Dikme:",fill=MA,font=fb)
        draw.text((lx+100,ly),f"1 adet={ry}m  |  {dk} adet  |  Toplam:{round(dk*ry,1)}m",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"━ Yatay Bag.:",fill=TU,font=fb)
        draw.text((lx+100,ly),f"1 adet={pg}m  |  {yt} adet  |  Toplam:{round(yt*pg,1)}m",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"| Derinlik:",fill=GR,font=fb)
        draw.text((lx+100,ly),f"1 adet=1.10m  |  {dr} adet  |  Toplam:{round(dr*1.1,1)}m",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"▦ Yukleme:",fill=YE,font=fb)
        draw.text((lx+100,ly),f"{yen}m × {ybo}m = {ym2} m²",fill=YE,font=fn); ly+=22
        draw.text((lx,ly),"↔ Koridor:",fill=MO,font=fb)
        draw.text((lx+100,ly),f"{kor}m  |  Kapi:{gg}m",fill=W2,font=fn)
    else:
        draw.text((lx,ly),"СПИСОК МАТЕРИАЛОВ",fill=SA,font=fb); ly+=22
        draw.text((lx,ly),"● Стойка:",fill=MA,font=fb)
        draw.text((lx+90,ly),f"1 шт={ry}м  |  {dk} шт  |  Итого:{round(dk*ry,1)}м",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"━ Балка:",fill=TU,font=fb)
        draw.text((lx+90,ly),f"1 шт={pg}м  |  {yt} шт  |  Итого:{round(yt*pg,1)}м",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"| Глубина:",fill=GR,font=fb)
        draw.text((lx+90,ly),f"1 шт=1.10м  |  {dr} шт  |  Итого:{round(dr*1.1,1)}м",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"▦ Зона:",fill=YE,font=fb)
        draw.text((lx+90,ly),f"{yen}м × {ybo}м = {ym2} м²",fill=YE,font=fn); ly+=22
        draw.text((lx,ly),"↔ Проход:",fill=MO,font=fb)
        draw.text((lx+90,ly),f"{kor}м  |  Ворота:{gg}м",fill=W2,font=fn)

    rx2b,ry2b=W//2+20,iy+14
    if lg=='tr':
        draw.text((rx2b,ry2b),"VERİM ANALİZİ",fill=SA,font=fb); ry2b+=22
        for k,v in [("Toplam Raf",str(sec['toplam'])),("Palet Kap.",f"{kap} palet"),
                    ("Raf Alani",f"{sec['raf_alani']} m²"),("Depo Verimi",f"%{sec['verim']}"),
                    ("Kat/Yuk.",f"{kat}/{ry}m")]:
            draw.text((rx2b,ry2b),f"{k}:",fill=AG,font=fn)
            draw.text((rx2b+170,ry2b),v,fill=W2,font=fb); ry2b+=22
    else:
        draw.text((rx2b,ry2b),"АНАЛИЗ КПД",fill=SA,font=fb); ry2b+=22
        for k,v in [("Стеллажей",str(sec['toplam'])),("Ёмкость",f"{kap} палл."),
                    ("Пл.стелл.",f"{sec['raf_alani']} м²"),("КПД",f"{sec['verim']}%"),
                    ("Ярус/Выс.",f"{kat}/{ry}м")]:
            draw.text((rx2b,ry2b),f"{k}:",fill=AG,font=fn)
            draw.text((rx2b+170,ry2b),v,fill=W2,font=fb); ry2b+=22

    buf=io.BytesIO()
    img.save(buf,format='PNG',dpi=(150,150))
    buf.seek(0)
    return buf

# ═══════════════════════════════════════════════
#  HANDLERS
# ═══════════════════════════════════════════════

async def baslat(update,context):
    context.user_data.clear()
    await update.message.reply_text("Dil secin / Выберите язык:",reply_markup=kb([["🇹🇷 Turkce","🇷🇺 Russkiy"]]))
    return LANG

async def lang_sec(update,context):
    t=update.message.text
    context.user_data['lang']='ru' if "Russkiy" in t else 'tr'
    lg=glang(context)
    await update.message.reply_text("📏 Depo uzunlugu (m):\nOrnek: 20" if lg=='tr' else "📏 Длина склада (м):\nПример: 20",reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['uzunluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Depo genisligi (m):\nOrnek: 12" if lg=='tr' else "📐 Ширина склада (м):\nПример: 12")
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return UZUNLUK

async def genislik_h(update,context):
    lg=glang(context)
    try:
        context.user_data['genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📏 Depo yuksekligi (m):\nOrnek: 6" if lg=='tr' else "📏 Высота склада (м):\nПример: 6")
        return DEPO_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GENISLIK

async def depo_yuk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['depo_yukseklik']=float(update.message.text.replace(',','.'))
        if lg=='tr':
            await update.message.reply_text("🚪 Giris kapisi hangi duvarda?",reply_markup=kb([["Alt duvar","Ust duvar"],["Sol duvar","Sag duvar"]]))
        else:
            await update.message.reply_text("🚪 На какой стене вход?",reply_markup=kb([["Нижняя стена","Верхняя стена"],["Левая стена","Правая стена"]]))
        return GIRIS_DUVAR
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return DEPO_YUK

async def giris_duvar_h(update,context):
    lg=glang(context)
    t=update.message.text.lower()
    if "alt" in t or "нижн" in t: context.user_data['giris_duvar']='alt'
    elif "ust" in t or "верхн" in t: context.user_data['giris_duvar']='ust'
    elif "sol" in t or "лев" in t: context.user_data['giris_duvar']='sol'
    else: context.user_data['giris_duvar']='sag'
    if lg=='tr':
        await update.message.reply_text("🚪 Kapinin konumu?",reply_markup=kb([["Sol yakin","Orta","Sag yakin"]]))
    else:
        await update.message.reply_text("🚪 Где именно вход?",reply_markup=kb([["Левее","По центру","Правее"]]))
    return GIRIS_KONUM

async def giris_konum_h(update,context):
    lg=glang(context)
    t=update.message.text.lower()
    if "orta" in t or "центру" in t:
        context.user_data['giris_konum']='orta'; context.user_data['giris_mesafe']=0.0
    elif "sol" in t or "левее" in t: context.user_data['giris_konum']='sol'
    else: context.user_data['giris_konum']='sag'
    if context.user_data['giris_konum']=='orta':
        await update.message.reply_text("🚪 Kapi genisligi (m):\nOrnek: 4" if lg=='tr' else "🚪 Ширина ворот (м):\nПример: 4",reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    else:
        await update.message.reply_text("🚪 Koseden kac metre?\nOrnek: 2" if lg=='tr' else "🚪 Расстояние от угла (м)?\nПример: 2",reply_markup=ReplyKeyboardRemove())
        return GIRIS_MESAFE

async def giris_mesafe_h(update,context):
    lg=glang(context)
    try:
        context.user_data['giris_mesafe']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("🚪 Kapi genisligi (m):\nOrnek: 4" if lg=='tr' else "🚪 Ширина ворот (м):\nПример: 4",reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GIRIS_MESAFE

async def giris_genislik_h(update,context):
    lg=glang(context)
    try:
        context.user_data['giris_genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Yukleme alani - EN kac metre?\nOrnek: 8" if lg=='tr' else "📐 Зона погрузки - ШИРИНА (м)?\nПример: 8",reply_markup=kb([["4","5","6","8","10"]]))
        return YUK_EN
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GIRIS_GENISLIK

async def yuk_en_h(update,context):
    lg=glang(context)
    try:
        context.user_data['yuk_en']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Yukleme alani - BOY kac metre?\nOrnek: 5" if lg=='tr' else "📐 Зона погрузки - ГЛУБИНА (м)?\nПример: 5",reply_markup=kb([["3","4","5","6","8"]]))
        return YUK_BOY
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return YUK_EN

async def yuk_boy_h(update,context):
    lg=glang(context)
    try:
        context.user_data['yuk_boy']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Raf-duvar arasi bosluk?\n0=bitisik" if lg=='tr' else "📐 Отступ от стен?\n0=вплотную",reply_markup=kb([["0","0.3","0.5"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return YUK_BOY

async def kenar_bosluk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['kenar_bosluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("🚦 Koridor tipi?\nForklift 3m | Transpalet 2m | El 1.2m" if lg=='tr' else "🚦 Тип прохода?\nПогрузчик 3м | Транспалет 2м | Ручной 1.2м",reply_markup=kb([["Forklift","Transpalet","El ile" if lg=='tr' else "Ruchnoy"]]))
        return KORIDOR_TIPI
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return KENAR_BOSLUK

async def koridor_h(update,context):
    lg=glang(context)
    t=update.message.text.lower()
    if "forklift" in t or "погрузчик" in t: context.user_data['koridor_tipi']='forklift'
    elif "transpalet" in t or "транспалет" in t: context.user_data['koridor_tipi']='transpalet'
    else: context.user_data['koridor_tipi']='el'
    await update.message.reply_text("📦 Raf basina palet?\n1=0.95m  2=1.85m\n3=2.70m  4=3.60m" if lg=='tr' else "📦 Паллет на ряд?\n1=0.95м  2=1.85м\n3=2.70м  4=3.60м",reply_markup=kb([["1","2"],["3","4"]]))
    return PALET

async def palet_h(update,context):
    lg=glang(context)
    try:
        v=int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet']=v
        await update.message.reply_text("🏗 Kat sayisi?\nOrnek: 3" if lg=='tr' else "🏗 Количество ярусов?\nПример: 3",reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1-4 girin." if lg=='tr' else "Введите 1-4.")
        return PALET

async def kat_h(update,context):
    lg=glang(context)
    try:
        context.user_data['kat']=int(update.message.text)
        await update.message.reply_text("📏 Raf yuksekligi (m)?\nOrnek: 5" if lg=='tr' else "📏 Высота стеллажа (м)?\nПример: 5")
        return RAF_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return KAT

async def raf_yuk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['raf_yuk']=float(update.message.text.replace(',','.'))
        d=context.user_data
        layouts=hesapla_layout(d)
        await update.message.reply_text("⏳ 2 secenek hazirlaniyor..." if lg=='tr' else "⏳ Готовлю 2 варианта...",reply_markup=ReplyKeyboardRemove())
        secs=[layouts['U_MAKS'],layouts['I_MAKS']]
        secs.sort(key=lambda x:x['toplam'],reverse=True)
        for i,sec in enumerate(secs):
            resim=ciz_teknik(d,lg,sec,i+1)
            ttr={'U_MAKS':'U-MAKS','I_MAKS':'I-MAKS'}
            tru={'U_MAKS':'U-МАКС','I_MAKS':'I-МАКС'}
            tn=tru.get(sec['tip']) if lg=='ru' else ttr.get(sec['tip'])
            kap=sec['toplam']*d['kat']*d['palet']
            if lg=='tr':
                cap=f"{'⭐ EN İYİ — ' if i==0 else ''}{i+1}. {tn}\nRaf:{sec['toplam']} | Kap:{kap} palet | Verim:%{sec['verim']}"
            else:
                cap=f"{'⭐ ЛУЧШИЙ — ' if i==0 else ''}{i+1}. {tn}\nСтелл:{sec['toplam']} | Ёмк:{kap} | КПД:{sec['verim']}%"
            await update.message.reply_photo(photo=resim,caption=cap)
        await update.message.reply_text("✅ Hazir! /hesapla" if lg=='tr' else "✅ Готово! /raschet")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

async def iptal(update,context):
    lg=glang(context)
    await update.message.reply_text("Iptal. /hesapla" if lg=='tr' else "Отменено. /raschet",reply_markup=ReplyKeyboardRemove())
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
            YUK_EN:        [MessageHandler(filters.TEXT&~filters.COMMAND,yuk_en_h)],
            YUK_BOY:       [MessageHandler(filters.TEXT&~filters.COMMAND,yuk_boy_h)],
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
