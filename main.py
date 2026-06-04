import os, logging, io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, UZUNLUK, GENISLIK, DEPO_YUK,
 GIRIS_DUVAR, GIRIS_KONUM, GIRIS_MESAFE, GIRIS_GENISLIK,
 YUK_EN, YUK_BOY,
 KENAR_BOSLUK, KORIDOR_TIPI, PALET, KAT, RAF_YUK) = range(15)

PALET_G = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_G = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}
DERINLIK = 1.1

def lang(c): return c.user_data.get('lang', 'tr')
def kb(r): return ReplyKeyboardMarkup(r, one_time_keyboard=True, resize_keyboard=True)

# ─── HESAPLAMA ───────────────────────────────────────────────

def hesapla(d):
    U = d['uzunluk'];  G = d['genislik']
    pg = PALET_G[d['palet']]; kor = KORIDOR_G[d['koridor_tipi']]
    kb2 = d.get('kenar_bosluk', 0.0)
    gd  = d.get('giris_duvar', 'alt')
    yen = d.get('yuk_en', 5.0);  ybo = d.get('yuk_boy', 5.0)
    kat = d['kat']

    # Yükleme alanı: kapı yönünde boy, kapıya paralel yönde en
    # Kapı alt/üst ise: paralel=uzunluk boyunca, dik=genislik boyunca
    if gd in ['alt', 'ust']:
        # raflar genislik yonunde uzanir (kapiya dik)
        # koridorlar uzunluk yonunde (kapiya paralel)
        alan_paralel = U - kb2*2          # koridor yonu
        alan_dik     = G - kb2*2 - ybo   # raf uzama yonu (yükleme alani cikarinca)
        yuk_m2 = round(yen * ybo, 1)
    else:
        alan_paralel = G - kb2*2
        alan_dik     = U - kb2*2 - ybo
        yuk_m2 = round(yen * ybo, 1)

    alan_paralel = max(alan_paralel, 0.1)
    alan_dik     = max(alan_dik, 0.1)

    # Paralel yonde kac raf yan yana: her raf pg genisliginde
    raf_yan = max(1, int(alan_paralel / pg))
    blok    = DERINLIK * 2  # sirt sirta = 2.2m

    # ── U_MAKS ──────────────────────────────────
    # Arka duvar: 1 sira (dik yonun basi)
    # Sol/sag duvar: her biri 1 sira (paralel yonda)
    # Orta: sirt sirta bloklar
    ic_dik = alan_dik - DERINLIK - DERINLIK*2 - kor*3  # arka+2yan+koridorlar
    orta_blok = max(0, int(ic_dik / (blok + kor))) if ic_dik > 0 else 0

    u_raf  = raf_yan          # arka duvar
    u_raf += raf_yan * 2      # sol + sag (her biri raf_yan)  -- yaklasik
    u_raf += orta_blok * 2 * raf_yan

    u_alan = (DERINLIK * alan_paralel +       # arka
              DERINLIK * alan_dik * 2 +        # sol + sag (yaklasik)
              orta_blok * blok * alan_paralel)
    u_alan = min(u_alan, U*G*0.85)

    # ── I_MAKS ──────────────────────────────────
    i_blok = max(1, int(alan_dik / (blok + kor)))
    i_raf  = i_blok * 2 * raf_yan
    i_alan = i_blok * blok * alan_paralel

    depo_alani = round(U * G, 1)

    return {
        'U_MAKS': {
            'tip':'U_MAKS', 'toplam':u_raf,
            'raf_yan':raf_yan, 'orta_blok':orta_blok,
            'raf_alani':round(u_alan,1), 'depo_alani':depo_alani,
            'yuk_m2':yuk_m2, 'yuk_en':yen, 'yuk_boy':ybo,
            'verim':round(u_alan/depo_alani*100,1),
            'kapasite':u_raf*kat*d['palet'],
            'alan_paralel':alan_paralel, 'alan_dik':alan_dik,
        },
        'I_MAKS': {
            'tip':'I_MAKS', 'toplam':i_raf,
            'raf_yan':raf_yan, 'blok':i_blok,
            'raf_alani':round(i_alan,1), 'depo_alani':depo_alani,
            'yuk_m2':yuk_m2, 'yuk_en':yen, 'yuk_boy':ybo,
            'verim':round(i_alan/depo_alani*100,1),
            'kapasite':i_raf*kat*d['palet'],
            'alan_paralel':alan_paralel, 'alan_dik':alan_dik,
        },
    }

# ─── ÇİZİM ───────────────────────────────────────────────────

def oy(draw,x1,x2,y,t,f,c):
    draw.line([x1,y,x2,y],fill=c,width=1)
    draw.line([x1,y-4,x1,y+4],fill=c,width=2)
    draw.line([x2,y-4,x2,y+4],fill=c,width=2)
    draw.text(((x1+x2)//2,y-5),t,fill=c,font=f,anchor='mb')

def od(draw,x,y1,y2,t,f,c):
    draw.line([x,y1,x,y2],fill=c,width=1)
    draw.line([x-4,y1,x+4,y1],fill=c,width=2)
    draw.line([x-4,y2,x+4,y2],fill=c,width=2)
    draw.text((x+5,(y1+y2)//2),t,fill=c,font=f,anchor='lm')

def ciz_raf(draw, x1, y1, x2, y2):
    """
    Kapıya DIK raf.
    Kısa kenar = paralel yön (raf_g genislik)  → SOL/SAG kenar
    Uzun kenar = dik yön (DERINLIK)             → UST/ALT kenar
    Yatay bağlantı: SOL ve SAG kenarda (paralel)
    Derinlik:        ÜST ve ALT kenarda (dik)
    Dikmeler: 4 köşe
    """
    draw.rectangle([x1,y1,x2,y2], fill='#081420')
    draw.line([x1,y1,x2,y2], fill='#1e2a3a', width=1)
    draw.line([x2,y1,x1,y2], fill='#1e2a3a', width=1)
    draw.rectangle([x1,y1,x2,y2], outline='#304050', width=1)
    # Yatay baglanti: sol ve sag kenar (KAPIYA PARALEL YON)
    draw.line([x1,y1+3,x1,y2-3], fill='#ff8c42', width=3)
    draw.line([x2,y1+3,x2,y2-3], fill='#ff8c42', width=3)
    # Derinlik: ust ve alt kenar (KAPIYA DIK YON)
    draw.line([x1+3,y1,x2-3,y1], fill='#4ade80', width=2)
    draw.line([x1+3,y2,x2-3,y2], fill='#4ade80', width=2)
    # Dikmeler
    for px,py in [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]:
        draw.ellipse([px-4,py-4,px+4,py+4], fill='#4a9eff', outline='white', width=1)

def ciz_teknik(d, lg, sec, sira):
    U=d['uzunluk']; G=d['genislik']
    pg=PALET_G[d['palet']]; kor=KORIDOR_G[d['koridor_tipi']]
    kb2=d.get('kenar_bosluk',0.0)
    gd=d.get('giris_duvar','alt')
    gk=d.get('giris_konum','orta')
    gm=d.get('giris_mesafe',0.0)
    gg=d.get('giris_genislik',4.0)
    kat=d['kat']; ry=d['raf_yuk']
    tip=sec['tip']
    yen=sec['yuk_en']; ybo=sec['yuk_boy']; ym2=sec['yuk_m2']

    W,H=1200,960
    img=Image.new('RGB',(W,H),'#0d1117')
    draw=ImageDraw.Draw(img)

    try:
        fb =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
        fn =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",12)
        ft =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",17)
        fsm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",10)
        fxs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",9)
    except:
        fb=fn=ft=fsm=fxs=ImageFont.load_default()

    W2='#e8e8e8'; AG='#505070'; SA='#ffd700'
    SI='#00b4d8'; MO='#c084fc'; YE='#22c55e'
    TU='#ff8c42'; GR='#4ade80'; MA='#4a9eff'

    INFO_H=165
    pl,pt,pr,pb=80,55,135,INFO_H+48
    pw=W-pl-pr; ph=H-pt-pb
    ox=pl; oy0=pt
    sx=pw/U; sy=ph/G

    # ── BAŞLIK ─────────────────────────────────
    draw.rectangle([0,0,W,42],fill='#161b22')
    tad={'U_MAKS':('U-MAKS: Duvar+Orta','U-МАКС: Стены+Центр'),
         'I_MAKS':('I-MAKS: Sirt Sirta','I-МАКС: Спина к спине')}
    tn=tad.get(tip,(tip,tip))[1 if lg=='ru' else 0]
    if lg=='tr':
        bl=f"SECENEK {sira}/2  ●  {tn}  ●  {sec['toplam']} raf  ●  Verim: %{sec['verim']}"
    else:
        bl=f"ВАРИАНТ {sira}/2  ●  {tn}  ●  {sec['toplam']} стелл.  ●  КПД: {sec['verim']}%"
    draw.text((W//2,21),bl,fill=SA,font=ft,anchor='mm')

    # ── DEPO SINIRI ────────────────────────────
    draw.rectangle([ox,oy0,ox+pw,oy0+ph],outline=SI,width=3)
    draw.rectangle([ox+2,oy0+2,ox+pw-2,oy0+ph-2],outline='#1a3a5c',width=1)

    # ── KAPI & YÜKLEME ALANI ───────────────────
    # Kapi konumu
    Gpx=max(int(gg*sx),35)
    gx=gy=0
    if gd in ['alt','ust']:
        if gk=='orta': gx=ox+pw//2
        elif gk=='sol': gx=ox+int(gm*sx)+Gpx//2
        else: gx=ox+pw-int(gm*sx)-Gpx//2
    else:
        if gk=='orta': gy=oy0+ph//2
        elif gk=='ust': gy=oy0+int(gm*sy)+Gpx//2
        else: gy=oy0+ph-int(gm*sy)-Gpx//2

    # Yükleme alanı piksel boyutlari
    # Yükleme alani: en=kapiya paralel, boy=kapiya dik
    if gd in ['alt','ust']:
        yuk_en_px=int(yen*sx); yuk_boy_px=int(ybo*sy)
    else:
        yuk_en_px=int(yen*sy); yuk_boy_px=int(ybo*sx)

    kapi_lbl="GİRİŞ/ÇIKIŞ" if lg=='tr' else "ВХОД/ВЫХОД"
    zona="YUKLEME/BOSALTMA ALANI" if lg=='tr' else "ЗОНА ПОГРУЗКИ/РАЗГРУЗКИ"

    if gd=='alt':
        # Yükleme alani altta, kapi ortali
        yuk_x1=gx-yuk_en_px//2; yuk_x2=gx+yuk_en_px//2
        yuk_x1=max(ox+2,yuk_x1); yuk_x2=min(ox+pw-2,yuk_x2)
        yuk_y1=oy0+ph-yuk_boy_px; yuk_y2=oy0+ph-2
        draw.rectangle([yuk_x1,yuk_y1,yuk_x2,yuk_y2],fill='#031a0d',outline=YE,width=2)
        draw.text(((yuk_x1+yuk_x2)//2,(yuk_y1+yuk_y2)//2-8),zona,fill=YE,font=fxs,anchor='mm')
        draw.text(((yuk_x1+yuk_x2)//2,(yuk_y1+yuk_y2)//2+8),f"{yen}×{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
        oy(draw,yuk_x1,yuk_x2,yuk_y1-12,f"{yen}m",fsm,YE)
        od(draw,yuk_x2+8,yuk_y1,yuk_y2,f"{ybo}m",fsm,YE)
        # Kapi
        draw.line([gx-Gpx//2,oy0+ph,gx+Gpx//2,oy0+ph],fill=SA,width=8)
        draw.text((gx,oy0+ph+10),kapi_lbl,fill=SA,font=fsm,anchor='mt')
        oy(draw,gx-Gpx//2,gx+Gpx//2,oy0+ph+24,f"{gg}m",fsm,SA)
        if gm>0 and gk!='orta':
            if gk=='sol': oy(draw,ox,gx-Gpx//2,oy0+ph+38,f"{gm}m",fsm,W2)
            else: oy(draw,gx+Gpx//2,ox+pw,oy0+ph+38,f"{gm}m",fsm,W2)

    elif gd=='ust':
        yuk_x1=gx-yuk_en_px//2; yuk_x2=gx+yuk_en_px//2
        yuk_x1=max(ox+2,yuk_x1); yuk_x2=min(ox+pw-2,yuk_x2)
        yuk_y1=oy0+2; yuk_y2=oy0+yuk_boy_px
        draw.rectangle([yuk_x1,yuk_y1,yuk_x2,yuk_y2],fill='#031a0d',outline=YE,width=2)
        draw.text(((yuk_x1+yuk_x2)//2,(yuk_y1+yuk_y2)//2-8),zona,fill=YE,font=fxs,anchor='mm')
        draw.text(((yuk_x1+yuk_x2)//2,(yuk_y1+yuk_y2)//2+8),f"{yen}×{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
        oy(draw,yuk_x1,yuk_x2,yuk_y2+12,f"{yen}m",fsm,YE)
        od(draw,yuk_x2+8,yuk_y1,yuk_y2,f"{ybo}m",fsm,YE)
        draw.line([gx-Gpx//2,oy0,gx+Gpx//2,oy0],fill=SA,width=8)
        draw.text((gx,oy0-10),kapi_lbl,fill=SA,font=fsm,anchor='mb')
        oy(draw,gx-Gpx//2,gx+Gpx//2,oy0-22,f"{gg}m",fsm,SA)

    elif gd=='sol':
        yuk_y1=gy-yuk_en_px//2; yuk_y2=gy+yuk_en_px//2
        yuk_y1=max(oy0+2,yuk_y1); yuk_y2=min(oy0+ph-2,yuk_y2)
        yuk_x1=ox+2; yuk_x2=ox+yuk_boy_px
        draw.rectangle([yuk_x1,yuk_y1,yuk_x2,yuk_y2],fill='#031a0d',outline=YE,width=2)
        draw.text(((yuk_x1+yuk_x2)//2,(yuk_y1+yuk_y2)//2-8),zona,fill=YE,font=fxs,anchor='mm')
        draw.text(((yuk_x1+yuk_x2)//2,(yuk_y1+yuk_y2)//2+8),f"{yen}×{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
        oy(draw,yuk_x1,yuk_x2,yuk_y2+12,f"{ybo}m",fsm,YE)
        od(draw,yuk_x1-12,yuk_y1,yuk_y2,f"{yen}m",fsm,YE)
        draw.line([ox,gy-Gpx//2,ox,gy+Gpx//2],fill=SA,width=8)
        draw.text((ox-8,gy),kapi_lbl,fill=SA,font=fsm,anchor='rm')
        od(draw,ox-35,gy-Gpx//2,gy+Gpx//2,f"{gg}m",fsm,SA)
        if gm>0 and gk!='orta':
            if gk=='ust': od(draw,ox-50,oy0,gy-Gpx//2,f"{gm}m",fsm,W2)
            else: od(draw,ox-50,gy+Gpx//2,oy0+ph,f"{gm}m",fsm,W2)

    else:  # sag
        yuk_y1=gy-yuk_en_px//2; yuk_y2=gy+yuk_en_px//2
        yuk_y1=max(oy0+2,yuk_y1); yuk_y2=min(oy0+ph-2,yuk_y2)
        yuk_x1=ox+pw-yuk_boy_px; yuk_x2=ox+pw-2
        draw.rectangle([yuk_x1,yuk_y1,yuk_x2,yuk_y2],fill='#031a0d',outline=YE,width=2)
        draw.text(((yuk_x1+yuk_x2)//2,(yuk_y1+yuk_y2)//2-8),zona,fill=YE,font=fxs,anchor='mm')
        draw.text(((yuk_x1+yuk_x2)//2,(yuk_y1+yuk_y2)//2+8),f"{yen}×{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
        oy(draw,yuk_x1,yuk_x2,yuk_y2+12,f"{ybo}m",fsm,YE)
        od(draw,yuk_x2+8,yuk_y1,yuk_y2,f"{yen}m",fsm,YE)
        draw.line([ox+pw,gy-Gpx//2,ox+pw,gy+Gpx//2],fill=SA,width=8)
        draw.text((ox+pw+8,gy),kapi_lbl,fill=SA,font=fsm,anchor='lm')
        od(draw,ox+pw+25,gy-Gpx//2,gy+Gpx//2,f"{gg}m",fsm,SA)

    # ── RAF ALANI SINIRLARI ────────────────────
    # Raflar kapiya DIK: raf uzunlugu kapiya dik yonde
    # Raf genisligi pg (kapiya paralel yonde)
    rax1=ox+int(kb2*sx); ray1=oy0+int(kb2*sy)
    rax2=ox+pw-int(kb2*sx); ray2=oy0+ph-int(kb2*sy)

    # Yükleme alanini raf alanindan cikar
    if gd=='alt':   ray2=min(ray2, yuk_y1)
    elif gd=='ust': ray1=max(ray1, yuk_y2)
    elif gd=='sol': rax1=max(rax1, yuk_x2)
    else:           rax2=min(rax2, yuk_x1)

    # Piksel hesaplari
    # KAPIYA PARALEL = uzunluk yonu (sx)
    # KAPIYA DIK     = genislik yonu (sy)
    if gd in ['alt','ust']:
        pg_px   = max(int(pg*sx), 8)    # raf genisligi: paralel yonde
        derin_px= max(int(DERINLIK*sy),6) # derinlik: dik yonde
        kor_px  = max(int(kor*sy),4)      # koridor: dik yonde
        alan_w  = rax2-rax1              # paralel alan px
        alan_h  = ray2-ray1              # dik alan px
    else:
        pg_px   = max(int(pg*sy), 8)
        derin_px= max(int(DERINLIK*sx),6)
        kor_px  = max(int(kor*sx),4)
        alan_w  = rax2-rax1
        alan_h  = ray2-ray1

    blok_px = derin_px*2
    raflar  = []

    if tip=='U_MAKS':
        if gd in ['alt','ust']:
            # Raflar dik yonde (y yonu) uzaniyor
            # Paralel yonde (x yonu) yan yana pg_px aralikli
            # ── ARKA DUVAR (kapinin karsisi) ────
            if gd=='alt':
                arka_y1=ray1; arka_y2=ray1+derin_px
            else:
                arka_y1=ray2-derin_px; arka_y2=ray2
            for i in range(sec['raf_yan']):
                rx1=rax1+int(i*pg*sx)
                rx2=min(rx1+pg_px-1,rax2)
                if rx1>=rax2: break
                raflar.append((rx1,arka_y1,rx2,arka_y2))
            oy(draw,rax1,rax1+pg_px,arka_y1-12,f"{pg}m",fsm,MO)
            od(draw,rax1-18,arka_y1,arka_y2,f"{DERINLIK}m",fsm,GR)

            # ── SOL ve SAG DUVAR ─────────────────
            # Dik yonde raflar, fakat sol/sag duvara bitisik
            # Yani x yonu sabit (sol: rax1..rax1+derin_px), y yonu raf birimleri
            sol_x1=rax1; sol_x2=rax1+derin_px
            sag_x1=rax2-derin_px; sag_x2=rax2
            if gd=='alt':
                yan_y_start=arka_y2+kor_px; yan_y_end=ray2
            else:
                yan_y_start=ray1; yan_y_end=arka_y1-kor_px
            n_yan=max(1,int((yan_y_end-yan_y_start)/(pg_px+1)))
            for i in range(n_yan):
                ry1=yan_y_start+i*(pg_px+1)
                ry2=min(ry1+pg_px-1,yan_y_end)
                if ry1>=yan_y_end: break
                raflar.append((sol_x1,ry1,sol_x2,ry2))
                raflar.append((sag_x1,ry1,sag_x2,ry2))
            draw.text((ox+pw+5,(yan_y_start+yan_y_end)//2),"Sol/Sag" if lg=='tr' else "Л/П",fill=W2,font=fxs,anchor='lm')

            # ── ORTA SIRT SIRTA BLOKLAR ──────────
            orta_x1=sol_x2+kor_px; orta_x2=sag_x1-kor_px
            if gd=='alt':
                orta_y=arka_y2+kor_px
            else:
                orta_y=ray1
            for blk in range(sec['orta_blok']):
                if gd=='alt':
                    b_y1=orta_y; b_y2=b_y1+derin_px
                    b_y3=b_y2;   b_y4=b_y3+derin_px
                    if b_y4>ray2: break
                    next_y=b_y4+kor_px
                else:
                    b_y1=orta_y; b_y2=b_y1+derin_px
                    b_y3=b_y2;   b_y4=b_y3+derin_px
                    if b_y4>ray2: break
                    next_y=b_y4+kor_px
                # Sadece orta alanda
                for i in range(sec['raf_yan']):
                    rx1=rax1+int(i*pg*sx); rx2=min(rx1+pg_px-1,rax2)
                    if rx1>=rax2: break
                    if rx1>=orta_x1-5 and rx2<=orta_x2+5:
                        raflar.append((rx1,b_y1,rx2,b_y2))
                        raflar.append((rx1,b_y3,rx2,b_y4))
                draw.text((ox+pw+5,(b_y1+b_y4)//2),f"B{blk+1}",fill=MO,font=fxs,anchor='lm')
                od(draw,ox+pw+5,b_y1,b_y4,f"{DERINLIK*2:.1f}m",fxs,MO)
                orta_y=next_y
        else:
            # Sol/sag kapili durum (x yonu)
            if gd=='sol':
                arka_x1=rax2-derin_px; arka_x2=rax2
            else:
                arka_x1=rax1; arka_x2=rax1+derin_px
            for i in range(sec['raf_yan']):
                ry1=ray1+int(i*pg*sy); ry2=min(ry1+pg_px-1,ray2)
                if ry1>=ray2: break
                raflar.append((arka_x1,ry1,arka_x2,ry2))
            # Sol/sag
            ust_y1=ray1; ust_y2=ray1+derin_px
            alt_y1=ray2-derin_px; alt_y2=ray2
            if gd=='sol':
                yan_x_s=arka_x1-kor_px-derin_px; yan_x_e=arka_x1-kor_px
            else:
                yan_x_s=arka_x2+kor_px; yan_x_e=arka_x2+kor_px+derin_px
            n_yan=max(1,int(alan_w/(pg_px+1)))
            for i in range(n_yan):
                rx1=rax1+i*(pg_px+1); rx2=min(rx1+pg_px-1,rax2)
                if rx1>=rax2: break
                raflar.append((rx1,ust_y1,rx2,ust_y2))
                raflar.append((rx1,alt_y1,rx2,alt_y2))
            # Orta bloklar
            if gd=='sol': ox_blk=arka_x1-kor_px-blok_px
            else: ox_blk=arka_x2+kor_px
            for blk in range(sec['orta_blok']):
                if gd=='sol':
                    b_x1=ox_blk; b_x2=b_x1+derin_px
                    b_x3=b_x2; b_x4=b_x3+derin_px
                    if b_x1<rax1: break
                    ox_blk=b_x1-kor_px-blok_px
                else:
                    b_x1=ox_blk; b_x2=b_x1+derin_px
                    b_x3=b_x2; b_x4=b_x3+derin_px
                    if b_x4>rax2: break
                    ox_blk=b_x4+kor_px
                for i in range(sec['raf_yan']):
                    ry1=ray1+int(i*pg*sy); ry2=min(ry1+pg_px-1,ray2)
                    if ry1>=ray2: break
                    raflar.append((b_x1,ry1,b_x2,ry2))
                    raflar.append((b_x3,ry1,b_x4,ry2))

    elif tip=='I_MAKS':
        if gd in ['alt','ust']:
            if gd=='alt': y_pos=ray1
            else: y_pos=ray1
            for blk in range(sec['blok']):
                b_y1=y_pos; b_y2=b_y1+derin_px
                b_y3=b_y2;  b_y4=b_y3+derin_px
                if b_y4>ray2: break
                for i in range(sec['raf_yan']):
                    rx1=rax1+int(i*pg*sx); rx2=min(rx1+pg_px-1,rax2)
                    if rx1>=rax2: break
                    raflar.append((rx1,b_y1,rx2,b_y2))
                    raflar.append((rx1,b_y3,rx2,b_y4))
                draw.text((ox+pw+5,(b_y1+b_y4)//2),f"B{blk+1}",fill=MO,font=fxs,anchor='lm')
                od(draw,ox+pw+5,b_y1,b_y4,f"{DERINLIK*2:.1f}m",fxs,MO)
                if blk>0:
                    od(draw,ox+pw+18,b_y1-kor_px,b_y1,f"{kor}m",fxs,MO)
                y_pos=b_y4+kor_px
            oy(draw,rax1,rax1+pg_px,ray1-12,f"{pg}m",fsm,MO)
            od(draw,rax1-18,ray1,ray1+derin_px,f"{DERINLIK}m",fsm,GR)
        else:
            if gd=='sol': x_pos=rax2-blok_px
            else: x_pos=rax1
            for blk in range(sec['blok']):
                if gd=='sol':
                    b_x1=x_pos; b_x2=b_x1+derin_px
                    b_x3=b_x2; b_x4=b_x3+derin_px
                    if b_x1<rax1: break
                    next_x=b_x1-kor_px-blok_px
                else:
                    b_x1=x_pos; b_x2=b_x1+derin_px
                    b_x3=b_x2; b_x4=b_x3+derin_px
                    if b_x4>rax2: break
                    next_x=b_x4+kor_px
                for i in range(sec['raf_yan']):
                    ry1=ray1+int(i*pg*sy); ry2=min(ry1+pg_px-1,ray2)
                    if ry1>=ray2: break
                    raflar.append((b_x1,ry1,b_x2,ry2))
                    raflar.append((b_x3,ry1,b_x4,ry2))
                x_pos=next_x

    # Raflari ciz
    for r in raflar:
        ciz_raf(draw,r[0],r[1],r[2],r[3])

    # Ana ölçüler
    oy(draw,ox,ox+pw,oy0-20,f"{U}m",fn,W2)
    od(draw,ox-20,oy0,oy0+ph,f"{G}m",fn,W2)

    # ── DEPO VERİMİ KUTUSU (sag ust) ──────────
    vx=ox+pw-165; vy=oy0+8
    draw.rectangle([vx,vy,vx+160,vy+80],fill='#0a1e35',outline=SI,width=1)
    if lg=='tr':
        draw.text((vx+80,vy+8),"DEPO VERİMİ",fill=SA,font=fsm,anchor='mt')
        draw.text((vx+8,vy+22),f"Raf Alani:   {sec['raf_alani']} m²",fill=W2,font=fxs)
        draw.text((vx+8,vy+34),f"Yukleme:     {sec['yuk_m2']} m²",fill=YE,font=fxs)
        draw.text((vx+8,vy+46),f"Depo Alani:  {sec['depo_alani']} m²",fill=AG,font=fxs)
        draw.text((vx+80,vy+62),f"%{sec['verim']} VERİM",fill=SA,font=fb,anchor='mt')
    else:
        draw.text((vx+80,vy+8),"КПД СКЛАДА",fill=SA,font=fsm,anchor='mt')
        draw.text((vx+8,vy+22),f"Пл.стелл.: {sec['raf_alani']} м²",fill=W2,font=fxs)
        draw.text((vx+8,vy+34),f"Зона:      {sec['yuk_m2']} м²",fill=YE,font=fxs)
        draw.text((vx+8,vy+46),f"Пл.склада: {sec['depo_alani']} м²",fill=AG,font=fxs)
        draw.text((vx+80,vy+62),f"КПД: {sec['verim']}%",fill=SA,font=fb,anchor='mt')

    # ── ALT BİLGİ ──────────────────────────────
    iy=H-INFO_H
    draw.rectangle([0,iy,W,H],fill='#161b22')
    draw.line([0,iy,W,iy],fill='#404060',width=2)

    dk=sec['toplam']*4; yt=sec['toplam']*kat*2; dr=sec['toplam']*2
    kapasite=sec['toplam']*kat*d['palet']

    lx,ly=20,iy+14
    if lg=='tr':
        draw.text((lx,ly),"MALZEME LİSTESİ",fill=SA,font=fb); ly+=22
        draw.text((lx,ly),"● Dikme:",fill=MA,font=fb)
        draw.text((lx+100,ly),f"1 adet={ry}m  |  {dk} adet  |  Toplam: {round(dk*ry,1)}m",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"━ Yatay Bag.:",fill=TU,font=fb)
        draw.text((lx+100,ly),f"1 adet={pg}m  |  {yt} adet  |  Toplam: {round(yt*pg,1)}m",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"| Derinlik:",fill=GR,font=fb)
        draw.text((lx+100,ly),f"1 adet=1.10m  |  {dr} adet  |  Toplam: {round(dr*1.1,1)}m",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"▦ Yukleme:",fill=YE,font=fb)
        draw.text((lx+100,ly),f"{sec['yuk_en']}m × {sec['yuk_boy']}m = {sec['yuk_m2']} m²",fill=YE,font=fn); ly+=22
        draw.text((lx,ly),"↔ Koridor:",fill=MO,font=fb)
        draw.text((lx+100,ly),f"{kor}m  |  Kapi: {gg}m",fill=W2,font=fn)
    else:
        draw.text((lx,ly),"СПИСОК МАТЕРИАЛОВ",fill=SA,font=fb); ly+=22
        draw.text((lx,ly),"● Стойка:",fill=MA,font=fb)
        draw.text((lx+90,ly),f"1 шт={ry}м  |  {dk} шт  |  Итого: {round(dk*ry,1)}м",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"━ Балка:",fill=TU,font=fb)
        draw.text((lx+90,ly),f"1 шт={pg}м  |  {yt} шт  |  Итого: {round(yt*pg,1)}м",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"| Глубина:",fill=GR,font=fb)
        draw.text((lx+90,ly),f"1 шт=1.10м  |  {dr} шт  |  Итого: {round(dr*1.1,1)}м",fill=W2,font=fn); ly+=22
        draw.text((lx,ly),"▦ Зона:",fill=YE,font=fb)
        draw.text((lx+90,ly),f"{sec['yuk_en']}м × {sec['yuk_boy']}м = {sec['yuk_m2']} м²",fill=YE,font=fn); ly+=22
        draw.text((lx,ly),"↔ Проход:",fill=MO,font=fb)
        draw.text((lx+90,ly),f"{kor}м  |  Ворота: {gg}м",fill=W2,font=fn)

    rx2b,ry2b=W//2+20,iy+14
    if lg=='tr':
        draw.text((rx2b,ry2b),"VERİM ANALİZİ",fill=SA,font=fb); ry2b+=22
        for k,v in [("Toplam Raf",str(sec['toplam'])),
                    ("Palet Kap.",f"{kapasite} palet"),
                    ("Raf Alani",f"{sec['raf_alani']} m²"),
                    ("Depo Verimi",f"%{sec['verim']}"),
                    ("Kat / Yukseklik",f"{kat} / {ry}m")]:
            draw.text((rx2b,ry2b),f"{k}:",fill=AG,font=fn)
            draw.text((rx2b+170,ry2b),v,fill=W2,font=fb); ry2b+=22
    else:
        draw.text((rx2b,ry2b),"АНАЛИЗ КПД",fill=SA,font=fb); ry2b+=22
        for k,v in [("Стеллажей",str(sec['toplam'])),
                    ("Ёмкость",f"{kapasite} палл."),
                    ("Пл.стелл.",f"{sec['raf_alani']} м²"),
                    ("КПД",f"{sec['verim']}%"),
                    ("Ярусов/Высота",f"{kat}/{ry}м")]:
            draw.text((rx2b,ry2b),f"{k}:",fill=AG,font=fn)
            draw.text((rx2b+170,ry2b),v,fill=W2,font=fb); ry2b+=22

    buf=io.BytesIO()
    img.save(buf,format='PNG',dpi=(150,150))
    buf.seek(0)
    return buf

# ─── HANDLERS ────────────────────────────────────────────────

async def baslat(update,context):
    context.user_data.clear()
    await update.message.reply_text("Dil secin / Выберите язык:",reply_markup=kb([["🇹🇷 Turkce","🇷🇺 Russkiy"]]))
    return LANG

async def lang_sec(update,context):
    t=update.message.text
    context.user_data['lang']='ru' if "Russkiy" in t else 'tr'
    lg=lang(context)
    await update.message.reply_text("📏 Depo uzunlugu (m):\nOrnek: 20" if lg=='tr' else "📏 Длина склада (м):\nПример: 20",reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update,context):
    lg=lang(context)
    try:
        context.user_data['uzunluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Depo genisligi (m):\nOrnek: 12" if lg=='tr' else "📐 Ширина склада (м):\nПример: 12")
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return UZUNLUK

async def genislik_h(update,context):
    lg=lang(context)
    try:
        context.user_data['genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📏 Depo yuksekligi (m):\nOrnek: 6" if lg=='tr' else "📏 Высота склада (м):\nПример: 6")
        return DEPO_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GENISLIK

async def depo_yuk_h(update,context):
    lg=lang(context)
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
    lg=lang(context)
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
    lg=lang(context)
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
    lg=lang(context)
    try:
        context.user_data['giris_mesafe']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("🚪 Kapi genisligi (m):\nOrnek: 4" if lg=='tr' else "🚪 Ширина ворот (м):\nПример: 4",reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GIRIS_MESAFE

async def giris_genislik_h(update,context):
    lg=lang(context)
    try:
        context.user_data['giris_genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Yukleme alani - EN kac metre?\nOrnek: 8" if lg=='tr' else "📐 Зона погрузки - ШИРИНА (м)?\nПример: 8",reply_markup=kb([["4","5","6","8","10"]]))
        return YUK_EN
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GIRIS_GENISLIK

async def yuk_en_h(update,context):
    lg=lang(context)
    try:
        context.user_data['yuk_en']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Yukleme alani - BOY kac metre?\nOrnek: 5" if lg=='tr' else "📐 Зона погрузки - ГЛУБИНА (м)?\nПример: 5",reply_markup=kb([["3","4","5","6","8"]]))
        return YUK_BOY
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return YUK_EN

async def yuk_boy_h(update,context):
    lg=lang(context)
    try:
        context.user_data['yuk_boy']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("📐 Raf-duvar arasi bosluk?\n0=bitisik" if lg=='tr' else "📐 Отступ от стен?\n0=вплотную",reply_markup=kb([["0","0.3","0.5"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return YUK_BOY

async def kenar_bosluk_h(update,context):
    lg=lang(context)
    try:
        context.user_data['kenar_bosluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text("🚦 Koridor tipi?\nForklift 3m | Transpalet 2m | El 1.2m" if lg=='tr' else "🚦 Тип прохода?\nПогрузчик 3м | Транспалет 2м | Ручной 1.2м",reply_markup=kb([["Forklift","Transpalet","El ile" if lg=='tr' else "Ruchnoy"]]))
        return KORIDOR_TIPI
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return KENAR_BOSLUK

async def koridor_h(update,context):
    lg=lang(context)
    t=update.message.text.lower()
    if "forklift" in t or "погрузчик" in t: context.user_data['koridor_tipi']='forklift'
    elif "transpalet" in t or "транспалет" in t: context.user_data['koridor_tipi']='transpalet'
    else: context.user_data['koridor_tipi']='el'
    await update.message.reply_text("📦 Raf basina palet?\n1=0.95m  2=1.85m\n3=2.70m  4=3.60m" if lg=='tr' else "📦 Паллет на ряд?\n1=0.95м  2=1.85м\n3=2.70м  4=3.60м",reply_markup=kb([["1","2"],["3","4"]]))
    return PALET

async def palet_h(update,context):
    lg=lang(context)
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
    lg=lang(context)
    try:
        context.user_data['kat']=int(update.message.text)
        await update.message.reply_text("📏 Raf yuksekligi (m)?\nOrnek: 5" if lg=='tr' else "📏 Высота стеллажа (м)?\nПример: 5")
        return RAF_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return KAT

async def raf_yuk_h(update,context):
    lg=lang(context)
    try:
        context.user_data['raf_yuk']=float(update.message.text.replace(',','.'))
        d=context.user_data
        layouts=hesapla(d)
        await update.message.reply_text("⏳ 2 secenek hazirlaniyor..." if lg=='tr' else "⏳ Готовлю 2 варианта...",reply_markup=ReplyKeyboardRemove())
        secs=[layouts['U_MAKS'],layouts['I_MAKS']]
        secs.sort(key=lambda x:x['toplam'],reverse=True)
        for i,sec in enumerate(secs):
            resim=ciz_teknik(d,lg,sec,i+1)
            ttr={'U_MAKS':'U-MAKS','I_MAKS':'I-MAKS'}
            tru={'U_MAKS':'U-МАКС','I_MAKS':'I-МАКС'}
            tn=tru.get(sec['tip'],sec['tip']) if lg=='ru' else ttr.get(sec['tip'],sec['tip'])
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
    lg=lang(context)
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
