import os, logging, io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.environ.get("TOKEN")

(LANG, UZUNLUK, GENISLIK,
 GIRIS_KONUM, GIRIS_MESAFE, GIRIS_GENISLIK,
 YUK_EN, YUK_BOY,
 KENAR_BOSLUK, KORIDOR_TIPI, PALET, KAT, RAF_YUK) = range(13)

PALET_G   = {1: 0.95, 2: 1.85, 3: 2.7, 4: 3.6}
KORIDOR_G = {"forklift": 3.0, "transpalet": 2.0, "el": 1.2}
DERINLIK  = 1.1  # raf derinligi (koridora dik)

def glang(c): return c.user_data.get('lang','tr')
def kb(r):    return ReplyKeyboardMarkup(r, one_time_keyboard=True, resize_keyboard=True)

def hesapla_layout(d):
    U   = d['uzunluk'];  G = d['genislik']
    pg  = PALET_G[d['palet']]
    kor = KORIDOR_G[d['koridor_tipi']]
    kb2 = d.get('kenar_bosluk', 0.0)
    yen = d.get('yuk_en', 5.0)
    ybo = d.get('yuk_boy', 5.0)
    kat = d['kat']

    # Kapi hep altta (Y yonu)
    # Raflar KAPIYA DIK = Y yonunde uzaniyor (derinlik Y yonunde)
    # Koridorlar X yonunde uzaniyor (kapiya paralel)
    # Raf birimi: X=DERINLIK (1.1m), Y=pg (palet genisligi)
    # Yatay baglanti: Y yonunde ust/alt kenar = koridora PARALEL (X yonu)
    # NOT: Ust/alt kenar X yonunde = koridora paralel DOGRU

    ef_x = U - kb2*2           # X yonunde efektif alan
    ef_y = G - kb2*2 - ybo     # Y yonunde efektif alan (yukleme alani cikarildi)
    ef_x = max(ef_x, 0.1)
    ef_y = max(ef_y, 0.1)

    yuk_m2 = round(yen * ybo, 1)

    # X yonunde kac raf yan yana: her raf DERINLIK=1.1m kapiyor
    # Y yonunde her raf pg kapiyor (palet genisligi)
    # Koridorlar X yonunde (kapiya paralel)
    # Bir blok: [raf(DERINLIK) | koridor(kor) | raf(DERINLIK)] = 2*DERINLIK+kor genislikte X yonunde

    blok_x = DERINLIK*2 + kor   # bir sirt sirta blokun X genisligi

    # I_MAKS: X yonunde sirt sirta bloklar tekrar eder
    i_blok = max(1, int(ef_x / blok_x))
    i_raf_y = max(1, int(ef_y / pg))   # Y yonunde kac raf
    i_raf   = i_blok * 2 * i_raf_y
    i_alan  = i_blok * blok_x * ef_y

    # U_MAKS: sol+sag+arka duvar + orta bloklar
    # Sol duvar: X=0..DERINLIK, Y boyunca raflar
    # Sag duvar: X=max-DERINLIK..max
    # Arka duvar (ust): Y=0..DERINLIK, X boyunca raflar
    # Orta: sirt sirta bloklar
    ic_x       = ef_x - DERINLIK*2 - kor*2
    orta_blok  = max(0, int(ic_x / blok_x)) if ic_x > 0 else 0
    raf_y_say  = max(1, int(ef_y / pg))   # sol/sag icin Y yonunde
    raf_x_arka = max(1, int(ef_x / pg))   # arka icin X yonunde

    u_raf = (raf_y_say +                    # sol duvar
             raf_y_say +                    # sag duvar
             raf_x_arka +                   # arka duvar
             orta_blok * 2 * raf_y_say)     # orta bloklar
    u_alan = (DERINLIK*ef_y*2 +
              DERINLIK*ef_x +
              orta_blok*blok_x*ef_y)

    depo_alani = round(U*G, 1)

    return {
        'U_MAKS': {
            'tip':'U_MAKS', 'toplam':u_raf,
            'raf_y_say':raf_y_say, 'raf_x_arka':raf_x_arka, 'orta_blok':orta_blok,
            'ef_x':ef_x, 'ef_y':ef_y,
            'raf_alani':round(min(u_alan,U*G*0.88),1),
            'depo_alani':depo_alani, 'yuk_m2':yuk_m2,
            'yuk_en':yen, 'yuk_boy':ybo,
            'verim':round(min(u_alan,U*G*0.88)/depo_alani*100,1),
            'kapasite':u_raf*kat*d['palet'],
        },
        'I_MAKS': {
            'tip':'I_MAKS', 'toplam':i_raf,
            'raf_y_say':i_raf_y, 'blok':i_blok,
            'ef_x':ef_x, 'ef_y':ef_y,
            'raf_alani':round(i_alan,1),
            'depo_alani':depo_alani, 'yuk_m2':yuk_m2,
            'yuk_en':yen, 'yuk_boy':ybo,
            'verim':round(i_alan/depo_alani*100,1),
            'kapasite':i_raf*kat*d['palet'],
        },
    }

def ciz_raf(draw, x1, y1, x2, y2):
    """
    Raf birimi kapiya DIK:
      x1..x2 = DERINLIK (X yonu, 1.1m) - koridora DIK
      y1..y2 = pg (Y yonu, palet genisligi) - koridora PARALEL

    Yatay baglanti (turuncu) = Y yonunde UST ve ALT kenar
      -> koridora PARALEL (dogru! ambar gorevlisi yandan malzeme koyar)
    Derinlik (yesil) = X yonunde SOL ve SAG kenar
    """
    draw.rectangle([x1,y1,x2,y2], fill='#081420')
    draw.line([x1,y1,x2,y2], fill='#1a2535', width=1)
    draw.line([x2,y1,x1,y2], fill='#1a2535', width=1)
    draw.rectangle([x1,y1,x2,y2], outline='#2a3a50', width=1)
    # Yatay baglanti: UST ve ALT (Y yonu = koridora PARALEL)
    draw.line([x1+2, y1, x2-2, y1], fill='#ff8c42', width=3)
    draw.line([x1+2, y2, x2-2, y2], fill='#ff8c42', width=3)
    # Derinlik: SOL ve SAG (X yonu = koridora DIK)
    draw.line([x1, y1+2, x1, y2-2], fill='#4ade80', width=2)
    draw.line([x2, y1+2, x2, y2-2], fill='#4ade80', width=2)
    # Dikmeler
    for px,py in [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]:
        draw.ellipse([px-4,py-4,px+4,py+4], fill='#4a9eff', outline='white', width=1)

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

def ciz_teknik(d, lg, sec, sira):
    U   = d['uzunluk'];  G = d['genislik']
    pg  = PALET_G[d['palet']]
    kor = KORIDOR_G[d['koridor_tipi']]
    kb2 = d.get('kenar_bosluk', 0.0)
    gk  = d.get('giris_konum', 'orta')
    gm  = d.get('giris_mesafe', 0.0)
    gg  = d.get('giris_genislik', 4.0)
    kat = d['kat'];  ry = d['raf_yuk']
    tip = sec['tip']
    yen = sec['yuk_en'];  ybo = sec['yuk_boy'];  ym2 = sec['yuk_m2']

    W,H = 1200, 980
    img  = Image.new('RGB',(W,H),'#0d1117')
    draw = ImageDraw.Draw(img)

    try:
        fb =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",13)
        fn =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
        ft =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",17)
        fsm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",10)
        fxs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",9)
    except:
        fb=fn=ft=fsm=fxs=ImageFont.load_default()

    W2='#e8e8e8'; AG='#505070'; SA='#ffd700'
    SI='#00b4d8'; MO='#c084fc'; YE='#22c55e'
    TU='#ff8c42'; GR='#4ade80'; MA='#4a9eff'

    INFO_H = 200
    pl,pt,pr,pb = 80,55,50,INFO_H+48
    pw=W-pl-pr; ph=H-pt-pb
    ox=pl; oy0=pt
    sx=pw/U; sy=ph/G

    # BASLIK
    draw.rectangle([0,0,W,42],fill='#161b22')
    tad={'U_MAKS':('U-MAKS: Duvar+Orta','U-МАКС: Стены+Центр'),
         'I_MAKS':('I-MAKS: Sirt Sirta','I-МАКС: Спина к спине')}
    tn=tad.get(tip,(tip,tip))[1 if lg=='ru' else 0]
    if lg=='tr':
        bl=f"SECENEK {sira}/2  |  {tn}  |  {sec['toplam']} raf  |  Verim:%{sec['verim']}"
    else:
        bl=f"ВАРИАНТ {sira}/2  |  {tn}  |  {sec['toplam']} стелл.  |  КПД:{sec['verim']}%"
    draw.text((W//2,21),bl,fill=SA,font=ft,anchor='mm')

    # DEPO SINIRI
    draw.rectangle([ox,oy0,ox+pw,oy0+ph],outline=SI,width=3)
    draw.rectangle([ox+2,oy0+2,ox+pw-2,oy0+ph-2],outline='#1a3a5c',width=1)

    # KAPI (hep altta)
    Gpx=max(int(gg*sx),35)
    if gk=='orta':    gx=ox+pw//2
    elif gk=='sol':   gx=ox+int(gm*sx)+Gpx//2
    else:             gx=ox+pw-int(gm*sx)-Gpx//2

    # YUKLEME ALANI
    yuk_en_px  = min(int(yen*sx), pw-4)
    yuk_boy_px = int(ybo*sy)
    yx1=max(ox+2, gx-yuk_en_px//2)
    yx2=min(ox+pw-2, gx+yuk_en_px//2)
    yy1=oy0+ph-yuk_boy_px; yy2=oy0+ph-2

    draw.rectangle([yx1,yy1,yx2,yy2],fill='#031a0d',outline=YE,width=2)
    draw.text(((yx1+yx2)//2,(yy1+yy2)//2-8),
              "YUKLEME/BOSALTMA" if lg=='tr' else "ЗОНА ПОГРУЗКИ",
              fill=YE,font=fxs,anchor='mm')
    draw.text(((yx1+yx2)//2,(yy1+yy2)//2+8),
              f"{yen}x{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
    oy(draw,yx1,yx2,yy1-12,f"{yen}m",fsm,YE)
    od(draw,yx2+8,yy1,yy2,f"{ybo}m",fsm,YE)

    # KAPI GOSTER
    draw.line([gx-Gpx//2,oy0+ph,gx+Gpx//2,oy0+ph],fill=SA,width=8)
    kapi_lbl="GİRİŞ/ÇIKIŞ" if lg=='tr' else "ВХОД/ВЫХОД"
    draw.text((gx,oy0+ph+10),kapi_lbl,fill=SA,font=fsm,anchor='mt')
    oy(draw,gx-Gpx//2,gx+Gpx//2,oy0+ph+24,f"{gg}m",fsm,SA)
    if gm>0 and gk!='orta':
        if gk=='sol': oy(draw,ox,gx-Gpx//2,oy0+ph+38,f"{gm}m",fsm,W2)
        else: oy(draw,gx+Gpx//2,ox+pw,oy0+ph+38,f"{gm}m",fsm,W2)

    # ANA OLCULAR
    oy(draw,ox,ox+pw,oy0-20,f"{U}m",fn,W2)
    od(draw,ox-20,oy0,oy0+ph,f"{G}m",fn,W2)

    # RAF ALAN SINIRLARI
    rax1=ox+int(kb2*sx);    ray1=oy0+int(kb2*sy)
    rax2=ox+pw-int(kb2*sx); ray2=oy0+ph-int(ybo*sy)-int(kb2*sy)

    # Piksel donusumleri
    # X yonu: DERINLIK = raf derinligi (koridora dik)
    # Y yonu: pg = palet genisligi (koridora paralel)
    dr_px  = max(int(DERINLIK*sx), 5)   # DERINLIK X yonunde
    pg_px  = max(int(pg*sy), 6)         # palet genisligi Y yonunde
    kor_px = max(int(kor*sx), 4)        # koridor X yonunde
    blok_x_px = dr_px*2 + kor_px       # sirt sirta blok X genisligi

    raflar=[]

    if tip=='I_MAKS':
        # X yonunde sirt sirta bloklar
        # Her blok: [raf_sol(dr_px) | koridor(kor_px) | raf_sag(dr_px)]
        # Y yonunde pg_px aralikli raflar
        x_pos=rax1
        blk=0
        while x_pos+blok_x_px<=rax2 and blk<sec['blok']:
            bx1=x_pos;        bx2=bx1+dr_px
            bx3=bx2+kor_px;   bx4=bx3+dr_px

            y_pos=ray1
            while y_pos+pg_px<=ray2:
                raflar.append((bx1,y_pos,bx2,y_pos+pg_px))
                raflar.append((bx3,y_pos,bx4,y_pos+pg_px))
                y_pos+=pg_px

            # Koridor olcusu
            if blk==0:
                oy(draw,bx2,bx3,ray1-14,f"{kor}m",fsm,MO)
                od(draw,rax1-18,ray1,ray1+dr_px,f"{DERINLIK}m",fsm,GR)
                od(draw,rax1-18,ray1,ray1+pg_px,f"{pg}m",fsm,MO)

            x_pos=bx4+max(int(0.1*sx),2)
            blk+=1

    elif tip=='U_MAKS':
        # SOL DUVAR: X=rax1..rax1+dr_px, Y yonunde pg_px aralikli
        sol_x1=rax1;     sol_x2=rax1+dr_px
        # SAG DUVAR: X=rax2-dr_px..rax2
        sag_x1=rax2-dr_px; sag_x2=rax2
        # ARKA DUVAR (ust): Y=ray1..ray1+pg_px, X yonunde (kapiya paralel = Y yonu sabit)
        # Arka duvarda raf: X boyunca pg_px aralikli, Y=ray1..ray1+dr_px
        # Burada arka duvar raflari Y=ray1 den baslar, derinlik Y yonunde dr_px kadar
        # Ama arka duvar raflari X yonunde pg_px aralikli olmali
        # Dikkat: arka duvarda raf derinligi Y yonunde (kapiya dik = Y yonu)
        # Arka raf: X=sol_x2+kor_px..sag_x1-kor_px arasinda pg_px X aralikli, Y=ray1..ray1+dr_px
        # Hayir, arka duvarda raf KAPIYA DIK demek Y yonunde uzaniyor
        # Arka raf: derinlik X yonunde (duvara dik = sol/sag gibi), ama X'te pg araliginda

        # Sol ve sag duvara raflar
        y_pos=ray1
        while y_pos+pg_px<=ray2:
            raflar.append((sol_x1,y_pos,sol_x2,y_pos+pg_px))
            raflar.append((sag_x1,y_pos,sag_x2,y_pos+pg_px))
            y_pos+=pg_px

        # Arka duvara raflar (ust, kapinin karsisi)
        # Arka raf: sol/sag duvar arasi, Y=ray1..ray1+dr_px, X yonunde pg_px aralikli
        arka_y1=ray1; arka_y2=ray1+dr_px
        x_pos=sol_x2+kor_px
        while x_pos+pg_px<=sag_x1-kor_px:
            raflar.append((x_pos,arka_y1,x_pos+pg_px,arka_y2))
            x_pos+=pg_px

        # Olcular
        od(draw,rax1-18,ray1,ray1+dr_px,f"{DERINLIK}m",fsm,GR)
        od(draw,rax1-18,ray1,ray1+pg_px,f"{pg}m",fsm,MO)
        oy(draw,sol_x2,sol_x2+kor_px,ray1-14,f"{kor}m",fsm,MO)

        # ORTA SIRT SIRTA BLOKLAR
        orta_x1=sol_x2+kor_px
        orta_x2=sag_x1-kor_px
        orta_y_bas=arka_y2+kor_px

        x_pos=orta_x1
        blk=0
        while x_pos+blok_x_px<=orta_x2 and blk<sec['orta_blok']:
            bx1=x_pos;        bx2=bx1+dr_px
            bx3=bx2+kor_px;   bx4=bx3+dr_px

            y_pos=orta_y_bas
            while y_pos+pg_px<=ray2:
                raflar.append((bx1,y_pos,bx2,y_pos+pg_px))
                raflar.append((bx3,y_pos,bx4,y_pos+pg_px))
                y_pos+=pg_px

            if blk==0:
                oy(draw,bx2,bx3,orta_y_bas-14,f"{kor}m",fsm,MO)

            x_pos=bx4+max(int(0.1*sx),2)
            blk+=1

    # RAFLARI CIZ
    for r in raflar:
        ciz_raf(draw,r[0],r[1],r[2],r[3])

    # ALT BILGI - tek satirda soldan saga: Malzeme | Verim Analizi | Depo Verimi
    iy=H-INFO_H
    draw.rectangle([0,iy,W,H],fill='#161b22')
    draw.line([0,iy,W,iy],fill='#404060',width=2)

    dk=len(raflar)*4; yt=len(raflar)*kat*2; dr_say=len(raflar)*2
    kap=sec['toplam']*kat*d['palet']

    col1=20; col2=W//3+10; col3=W*2//3+10
    sep_color='#303050'

    # --- SUTUN 1: MALZEME LISTESI ---
    lx=col1; ly=iy+14
    if lg=='tr':
        draw.text((lx,ly),"MALZEME",fill=SA,font=fb); ly+=20
        draw.text((lx,ly),"● Dikme:",fill=MA,font=fb)
        draw.text((lx+85,ly),f"1={ry}m | {dk} adet | Top:{round(dk*ry,1)}m",fill=W2,font=fn); ly+=19
        draw.text((lx,ly),"━ Yatay:",fill=TU,font=fb)
        draw.text((lx+85,ly),f"1={pg}m | {yt} adet | Top:{round(yt*pg,1)}m",fill=W2,font=fn); ly+=19
        draw.text((lx,ly),"| Derinlik:",fill=GR,font=fb)
        draw.text((lx+85,ly),f"1=1.1m | {dr_say} adet | Top:{round(dr_say*1.1,1)}m",fill=W2,font=fn); ly+=19
        draw.text((lx,ly),"▦ Yukleme:",fill=YE,font=fb)
        draw.text((lx+85,ly),f"{yen}x{ybo}m = {ym2} m²",fill=YE,font=fn); ly+=19
        draw.text((lx,ly),"↔ Koridor:",fill=MO,font=fb)
        draw.text((lx+85,ly),f"{kor}m | Kapi:{gg}m | Kat:{kat}",fill=W2,font=fn)
    else:
        draw.text((lx,ly),"МАТЕРИАЛЫ",fill=SA,font=fb); ly+=20
        draw.text((lx,ly),"● Стойка:",fill=MA,font=fb)
        draw.text((lx+80,ly),f"1={ry}м | {dk} шт | Ит:{round(dk*ry,1)}м",fill=W2,font=fn); ly+=19
        draw.text((lx,ly),"━ Балка:",fill=TU,font=fb)
        draw.text((lx+80,ly),f"1={pg}м | {yt} шт | Ит:{round(yt*pg,1)}м",fill=W2,font=fn); ly+=19
        draw.text((lx,ly),"| Глубина:",fill=GR,font=fb)
        draw.text((lx+80,ly),f"1=1.1м | {dr_say} шт | Ит:{round(dr_say*1.1,1)}м",fill=W2,font=fn); ly+=19
        draw.text((lx,ly),"▦ Зона:",fill=YE,font=fb)
        draw.text((lx+80,ly),f"{yen}x{ybo}м = {ym2} м²",fill=YE,font=fn); ly+=19
        draw.text((lx,ly),"↔ Проход:",fill=MO,font=fb)
        draw.text((lx+80,ly),f"{kor}м | Вор:{gg}м | Яр:{kat}",fill=W2,font=fn)

    # Sutun ayiraci 1
    draw.line([col2-10,iy+10,col2-10,H-10],fill=sep_color,width=1)

    # --- SUTUN 2: VERIM ANALIZI ---
    lx=col2; ly=iy+14
    if lg=='tr':
        draw.text((lx,ly),"VERİM ANALİZİ",fill=SA,font=fb); ly+=20
        for k,v in [("Toplam Raf",str(sec['toplam'])),
                    ("Palet Kapasitesi",f"{kap} palet"),
                    ("Raf Alani",f"{sec['raf_alani']} m²"),
                    ("Kat Sayisi",str(kat)),
                    ("Raf Yuksekligi",f"{ry} m")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+160,ly),v,fill=W2,font=fb); ly+=19
    else:
        draw.text((lx,ly),"АНАЛИЗ КПД",fill=SA,font=fb); ly+=20
        for k,v in [("Стеллажей",str(sec['toplam'])),
                    ("Ёмкость",f"{kap} палл."),
                    ("Пл.стелл.",f"{sec['raf_alani']} м²"),
                    ("Ярусов",str(kat)),
                    ("Высота стелл.",f"{ry} м")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+160,ly),v,fill=W2,font=fb); ly+=19

    # Sutun ayiraci 2
    draw.line([col3-10,iy+10,col3-10,H-10],fill=sep_color,width=1)

    # --- SUTUN 3: DEPO VERIMI ---
    lx=col3; ly=iy+14
    if lg=='tr':
        draw.text((lx,ly),"DEPO VERİMİ",fill=SA,font=fb); ly+=20
        for k,v,c in [("Depo Alani",f"{sec['depo_alani']} m²",W2),
                      ("Raf Alani",f"{sec['raf_alani']} m²",W2),
                      ("Yukleme Alani",f"{ym2} m²",YE),
                      ("Bos Alan",f"{round(sec['depo_alani']-sec['raf_alani']-ym2,1)} m²",AG),
                      ("VERIM",f"%{sec['verim']}",SA)]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+160,ly),v,fill=c,font=fb if k=="VERIM" else fn); ly+=19
    else:
        draw.text((lx,ly),"КПД СКЛАДА",fill=SA,font=fb); ly+=20
        for k,v,c in [("Пл.склада",f"{sec['depo_alani']} м²",W2),
                      ("Пл.стелл.",f"{sec['raf_alani']} м²",W2),
                      ("Зона погр.",f"{ym2} м²",YE),
                      ("Своб.площ.",f"{round(sec['depo_alani']-sec['raf_alani']-ym2,1)} м²",AG),
                      ("КПД",f"{sec['verim']}%",SA)]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+160,ly),v,fill=c,font=fb if k=="КПД" else fn); ly+=19

    buf=io.BytesIO()
    img.save(buf,format='PNG',dpi=(150,150))
    buf.seek(0)
    return buf

# ── HANDLERS ──────────────────────────────────

async def baslat(update,context):
    context.user_data.clear()
    await update.message.reply_text("Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce","🇷🇺 Russkiy"]]))
    return LANG

async def lang_sec(update,context):
    t=update.message.text
    context.user_data['lang']='ru' if "Russkiy" in t else 'tr'
    lg=glang(context)
    await update.message.reply_text(
        "📏 Depo uzunlugu (m):\nOrnek: 20" if lg=='tr' else "📏 Длина склада (м):\nПример: 20",
        reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['uzunluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "📐 Depo genisligi (m):\nOrnek: 12" if lg=='tr' else "📐 Ширина склада (м):\nПример: 12")
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return UZUNLUK

async def genislik_h(update,context):
    lg=glang(context)
    try:
        context.user_data['genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "🚪 Kapinin konumu?" if lg=='tr' else "🚪 Расположение входа?",
            reply_markup=kb([["Sol yakin" if lg=='tr' else "Левее",
                              "Orta" if lg=='tr' else "По центру",
                              "Sag yakin" if lg=='tr' else "Правее"]]))
        return GIRIS_KONUM
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GENISLIK

async def giris_konum_h(update,context):
    lg=glang(context)
    t=update.message.text.lower()
    if "orta" in t or "центру" in t:
        context.user_data['giris_konum']='orta'
        context.user_data['giris_mesafe']=0.0
    elif "sol" in t or "левее" in t:
        context.user_data['giris_konum']='sol'
    else:
        context.user_data['giris_konum']='sag'
    if context.user_data['giris_konum']=='orta':
        await update.message.reply_text(
            "🚪 Kapi genisligi (m):\nOrnek: 4" if lg=='tr' else "🚪 Ширина ворот (м):\nПример: 4",
            reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    else:
        await update.message.reply_text(
            "🚪 Koseden kac metre?\nOrnek: 2" if lg=='tr' else "🚪 Расстояние от угла (м)?\nПример: 2",
            reply_markup=ReplyKeyboardRemove())
        return GIRIS_MESAFE

async def giris_mesafe_h(update,context):
    lg=glang(context)
    try:
        context.user_data['giris_mesafe']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "🚪 Kapi genisligi (m):\nOrnek: 4" if lg=='tr' else "🚪 Ширина ворот (м):\nПример: 4",
            reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GIRIS_MESAFE

async def giris_genislik_h(update,context):
    lg=glang(context)
    try:
        context.user_data['giris_genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "📐 Yukleme alani EN (m):\nOrnek: 8" if lg=='tr' else "📐 Зона погрузки ШИРИНА (м):\nПример: 8",
            reply_markup=kb([["4","6","8","10","12"]]))
        return YUK_EN
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return GIRIS_GENISLIK

async def yuk_en_h(update,context):
    lg=glang(context)
    try:
        context.user_data['yuk_en']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "📐 Yukleme alani BOY (m):\nOrnek: 5" if lg=='tr' else "📐 Зона погрузки ГЛУБИНА (м):\nПример: 5",
            reply_markup=kb([["3","4","5","6","8"]]))
        return YUK_BOY
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return YUK_EN

async def yuk_boy_h(update,context):
    lg=glang(context)
    try:
        context.user_data['yuk_boy']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "📐 Raf-duvar arasi bosluk?\n0=bitisik" if lg=='tr' else "📐 Отступ от стен?\n0=вплотную",
            reply_markup=kb([["0","0.3","0.5"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Только цифры.")
        return YUK_BOY

async def kenar_bosluk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['kenar_bosluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "🚦 Koridor tipi?\nForklift 3m | Transpalet 2m | El 1.2m" if lg=='tr' else
            "🚦 Тип прохода?\nПогрузчик 3м | Транспалет 2м | Ручной 1.2м",
            reply_markup=kb([["Forklift","Transpalet","El ile" if lg=='tr' else "Ruchnoy"]]))
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
    await update.message.reply_text(
        "📦 Raf basina palet?\n1=0.95m  2=1.85m\n3=2.70m  4=3.60m" if lg=='tr' else
        "📦 Паллет на ряд?\n1=0.95м  2=1.85м\n3=2.70м  4=3.60м",
        reply_markup=kb([["1","2"],["3","4"]]))
    return PALET

async def palet_h(update,context):
    lg=glang(context)
    try:
        v=int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet']=v
        await update.message.reply_text(
            "🏗 Kat sayisi?\nOrnek: 3" if lg=='tr' else "🏗 Количество ярусов?\nПример: 3",
            reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1-4 girin." if lg=='tr' else "Введите 1-4.")
        return PALET

async def kat_h(update,context):
    lg=glang(context)
    try:
        context.user_data['kat']=int(update.message.text)
        await update.message.reply_text(
            "📏 Raf yuksekligi (m)?\nOrnek: 5" if lg=='tr' else "📏 Высота стеллажа (м)?\nПример: 5")
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
        await update.message.reply_text(
            "⏳ 2 secenek hazirlaniyor..." if lg=='tr' else "⏳ Готовлю 2 варианта...",
            reply_markup=ReplyKeyboardRemove())
        secs=[layouts['U_MAKS'],layouts['I_MAKS']]
        secs.sort(key=lambda x:x['toplam'],reverse=True)
        for i,sec in enumerate(secs):
            resim=ciz_teknik(d,lg,sec,i+1)
            ttr={'U_MAKS':'U-MAKS','I_MAKS':'I-MAKS'}
            tru={'U_MAKS':'U-МАКС','I_MAKS':'I-МАКС'}
            tn=tru.get(sec['tip']) if lg=='ru' else ttr.get(sec['tip'])
            kap=sec['toplam']*d['kat']*d['palet']
            if lg=='tr':
                cap=(f"{'⭐ EN İYİ — ' if i==0 else ''}{i+1}. {tn}\n"
                     f"Raf:{sec['toplam']} | Kap:{kap} palet | Verim:%{sec['verim']}")
            else:
                cap=(f"{'⭐ ЛУЧШИЙ — ' if i==0 else ''}{i+1}. {tn}\n"
                     f"Стелл:{sec['toplam']} | Ёмк:{kap} | КПД:{sec['verim']}%")
            await update.message.reply_photo(photo=resim,caption=cap)
        await update.message.reply_text(
            "✅ Hazir! Yeni cizim: /hesapla" if lg=='tr' else "✅ Готово! Новый: /raschet")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

async def iptal(update,context):
    lg=glang(context)
    await update.message.reply_text(
        "Iptal. /hesapla" if lg=='tr' else "Отменено. /raschet",
        reply_markup=ReplyKeyboardRemove())
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
