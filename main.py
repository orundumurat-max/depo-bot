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
DR        = 1.1  # raf derinligi

def glang(c): return c.user_data.get('lang','tr')
def kb(r):    return ReplyKeyboardMarkup(r, one_time_keyboard=True, resize_keyboard=True)

def hesapla(d):
    U=d['uzunluk']; G=d['genislik']
    pg=PALET_G[d['palet']]; kor=KORIDOR_G[d['koridor_tipi']]
    kb2=d.get('kenar_bosluk',0.0)
    yen=d.get('yuk_en',5.0); ybo=d.get('yuk_boy',5.0)
    kat=d['kat']
    ef_x=max(U-kb2*2,0.1); ef_y=max(G-kb2*2-ybo,0.1)
    yuk_m2=round(yen*ybo,1)
    blok=DR*2+kor
    # I_MAKS
    ib=max(1,int(ef_x/blok)); iry=max(1,int(ef_y/pg))
    i_raf=ib*2*iry; i_alan=ib*blok*ef_y
    # U_MAKS
    ic_x=ef_x-DR*2-kor*2
    ob=max(0,int(ic_x/blok)) if ic_x>0 else 0
    rys=max(1,int(ef_y/pg)); rxa=max(1,int(ef_x/pg))
    u_raf=rys+rys+rxa+ob*2*rys
    u_alan=DR*ef_y*2+DR*ef_x+ob*blok*ef_y
    da=round(U*G,1)
    b={'ef_x':ef_x,'ef_y':ef_y,'depo_alani':da,'yuk_m2':yuk_m2,'yuk_en':yen,'yuk_boy':ybo}
    return {
        'U_MAKS':{**b,'tip':'U_MAKS','toplam':u_raf,'rys':rys,'rxa':rxa,'ob':ob,
                  'raf_alani':round(min(u_alan,U*G*0.88),1),
                  'verim':round(min(u_alan,U*G*0.88)/da*100,1),'kapasite':u_raf*kat*d['palet']},
        'I_MAKS':{**b,'tip':'I_MAKS','toplam':i_raf,'iry':iry,'ib':ib,
                  'raf_alani':round(i_alan,1),
                  'verim':round(i_alan/da*100,1),'kapasite':i_raf*kat*d['palet']},
    }

def raf_koridor_paralel(draw, x1, y1, x2, y2):
    """
    Raf KAPIYA DIK, koridora PARALEL yatay baglanti.
    Raf birimi: x kisa (DR=1.1m), y uzun (pg)
    Turuncu (yatay bag): Y yonunde UST ve ALT kenar = koridora PARALEL
    Yesil (derinlik): X yonunde SOL ve SAG kenar
    """
    draw.rectangle([x1,y1,x2,y2],fill='#081420')
    draw.line([x1,y1,x2,y2],fill='#1a2535',width=1)
    draw.line([x2,y1,x1,y2],fill='#1a2535',width=1)
    draw.rectangle([x1,y1,x2,y2],outline='#2a3a50',width=1)
    # Turuncu: UST ve ALT (Y yonu = koridora paralel)
    draw.line([x1+2,y1,x2-2,y1],fill='#ff8c42',width=3)
    draw.line([x1+2,y2,x2-2,y2],fill='#ff8c42',width=3)
    # Yesil: SOL ve SAG (X yonu = koridora dik = raf derinligi)
    draw.line([x1,y1+2,x1,y2-2],fill='#4ade80',width=2)
    draw.line([x2,y1+2,x2,y2-2],fill='#4ade80',width=2)
    for px,py in [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]:
        draw.ellipse([px-4,py-4,px+4,py+4],fill='#4a9eff',outline='white',width=1)

def raf_kapi_paralel(draw, x1, y1, x2, y2):
    """
    Raf KAPIYA PARALEL (sadece U_MAKS arka duvar).
    Raf birimi: x uzun (pg), y kisa (DR=1.1m)
    Turuncu (yatay bag): X yonunde SOL ve SAG kenar = kapiya PARALEL
    Yesil (derinlik): Y yonunde UST ve ALT kenar
    """
    draw.rectangle([x1,y1,x2,y2],fill='#081420')
    draw.line([x1,y1,x2,y2],fill='#1a2535',width=1)
    draw.line([x2,y1,x1,y2],fill='#1a2535',width=1)
    draw.rectangle([x1,y1,x2,y2],outline='#2a3a50',width=1)
    # Turuncu: SOL ve SAG (X yonu = kapiya paralel)
    draw.line([x1,y1+2,x1,y2-2],fill='#ff8c42',width=3)
    draw.line([x2,y1+2,x2,y2-2],fill='#ff8c42',width=3)
    # Yesil: UST ve ALT (Y yonu = raf derinligi)
    draw.line([x1+2,y1,x2-2,y1],fill='#4ade80',width=2)
    draw.line([x1+2,y2,x2-2,y2],fill='#4ade80',width=2)
    for px,py in [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]:
        draw.ellipse([px-4,py-4,px+4,py+4],fill='#4a9eff',outline='white',width=1)

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

def ciz(d,lg,sec,sira):
    U=d['uzunluk']; G=d['genislik']
    pg=PALET_G[d['palet']]; kor=KORIDOR_G[d['koridor_tipi']]
    kb2=d.get('kenar_bosluk',0.0)
    gk=d.get('giris_konum','orta'); gm=d.get('giris_mesafe',0.0)
    gg=d.get('giris_genislik',4.0)
    kat=d['kat']; ry=d['raf_yuk']
    tip=sec['tip']
    yen=sec['yuk_en']; ybo=sec['yuk_boy']; ym2=sec['yuk_m2']

    W,H=1200,980
    img=Image.new('RGB',(W,H),'#0d1117')
    draw=ImageDraw.Draw(img)

    try:
        fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",13)
        fn=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
        ft=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",17)
        fsm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",10)
        fxs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",9)
    except:
        fb=fn=ft=fsm=fxs=ImageFont.load_default()

    W2='#e8e8e8'; AG='#505070'; SA='#ffd700'; SI='#00b4d8'
    MO='#c084fc'; YE='#22c55e'; TU='#ff8c42'; GR='#4ade80'; MA='#4a9eff'

    INFO_H=200
    pl,pt,pr,pb=80,55,50,INFO_H+48
    pw=W-pl-pr; ph=H-pt-pb
    ox=pl; oy0=pt
    sx=pw/U; sy=ph/G

    # BASLIK
    draw.rectangle([0,0,W,42],fill='#161b22')
    tad={'U_MAKS':('U-MAKS: Duvar+Orta','U-МАКС: Стены+Центр'),
         'I_MAKS':('I-MAKS: Sirt Sirta','I-МАКС: Спина к спине')}
    tn=tad.get(tip,(tip,tip))[1 if lg=='ru' else 0]
    bl=(f"SECENEK {sira}/2  |  {tn}  |  {sec['toplam']} raf  |  Verim:%{sec['verim']}" if lg=='tr'
        else f"ВАРИАНТ {sira}/2  |  {tn}  |  {sec['toplam']} стелл.  |  КПД:{sec['verim']}%")
    draw.text((W//2,21),bl,fill=SA,font=ft,anchor='mm')

    # DEPO
    draw.rectangle([ox,oy0,ox+pw,oy0+ph],outline=SI,width=3)
    draw.rectangle([ox+2,oy0+2,ox+pw-2,oy0+ph-2],outline='#1a3a5c',width=1)

    # KAPI
    Gpx=max(int(gg*sx),35)
    if gk=='orta':  gx=ox+pw//2
    elif gk=='sol': gx=ox+int(gm*sx)+Gpx//2
    else:           gx=ox+pw-int(gm*sx)-Gpx//2

    # YUKLEME ALANI
    yup=min(int(yen*sx),pw-4); ybp=int(ybo*sy)
    yx1=max(ox+2,gx-yup//2); yx2=min(ox+pw-2,gx+yup//2)
    yy1=oy0+ph-ybp; yy2=oy0+ph-2
    draw.rectangle([yx1,yy1,yx2,yy2],fill='#031a0d',outline=YE,width=2)
    draw.text(((yx1+yx2)//2,(yy1+yy2)//2-8),
              "YUKLEME/BOSALTMA" if lg=='tr' else "ЗОНА ПОГРУЗКИ",fill=YE,font=fxs,anchor='mm')
    draw.text(((yx1+yx2)//2,(yy1+yy2)//2+8),
              f"{yen}x{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
    oy(draw,yx1,yx2,yy1-12,f"{yen}m",fsm,YE)
    od(draw,yx2+8,yy1,yy2,f"{ybo}m",fsm,YE)
    draw.line([gx-Gpx//2,oy0+ph,gx+Gpx//2,oy0+ph],fill=SA,width=8)
    kl="GİRİŞ/ÇIKIŞ" if lg=='tr' else "ВХОД/ВЫХОД"
    draw.text((gx,oy0+ph+10),kl,fill=SA,font=fsm,anchor='mt')
    oy(draw,gx-Gpx//2,gx+Gpx//2,oy0+ph+24,f"{gg}m",fsm,SA)
    if gm>0 and gk!='orta':
        if gk=='sol': oy(draw,ox,gx-Gpx//2,oy0+ph+38,f"{gm}m",fsm,W2)
        else: oy(draw,gx+Gpx//2,ox+pw,oy0+ph+38,f"{gm}m",fsm,W2)

    # OLCULAR
    oy(draw,ox,ox+pw,oy0-20,f"{U}m",fn,W2)
    od(draw,ox-20,oy0,oy0+ph,f"{G}m",fn,W2)

    # RAF ALANI
    rax1=ox+int(kb2*sx); ray1=oy0+int(kb2*sy)
    rax2=ox+pw-int(kb2*sx); ray2=oy0+ph-int(ybo*sy)-int(kb2*sy)

    # Piksel boyutlari
    # Raf KAPIYA DIK: x=DR(1.1m kisa), y=pg(palet uzun)
    dr_x=max(int(DR*sx),5)   # derinlik X yonunde
    pg_y=max(int(pg*sy),6)   # palet genisligi Y yonunde
    kor_x=max(int(kor*sx),4) # koridor X yonunde
    blok_x=dr_x*2+kor_x      # sirt sirta blok

    # Arka duvar icin: x=pg(uzun), y=DR(kisa)
    pg_x=max(int(pg*sx),6)   # palet genisligi X yonunde (arka duvar)
    dr_y=max(int(DR*sy),5)   # derinlik Y yonunde (arka duvar)

    raflar=[]  # (x1,y1,x2,y2,fonk) fonk=0:koridor_paralel, 1:kapi_paralel

    if tip=='I_MAKS':
        # X yonunde sirt sirta bloklar
        # Turuncu UST/ALT = koridora paralel
        x=rax1; b=0
        while x+blok_x<=rax2 and b<sec['ib']:
            bx1=x; bx2=bx1+dr_x; bx3=bx2+kor_x; bx4=bx3+dr_x
            yp=ray1
            while yp+pg_y<=ray2:
                raflar.append((bx1,yp,bx2,yp+pg_y,0))
                raflar.append((bx3,yp,bx4,yp+pg_y,0))
                yp+=pg_y
            if b==0:
                oy(draw,bx2,bx3,ray1-14,f"{kor}m",fsm,MO)
                od(draw,rax1-18,ray1,ray1+dr_x,f"{DR}m",fsm,GR)
                od(draw,rax1-18,ray1,ray1+pg_y,f"{pg}m",fsm,MO)
            x=bx4+max(int(0.1*sx),2); b+=1

    elif tip=='U_MAKS':
        sx1=rax1; sx2=rax1+dr_x   # sol duvar
        rx1=rax2-dr_x; rx2=rax2   # sag duvar
        ay1=ray1; ay2=ray1+dr_y   # arka duvar Y siniri

        # SOL DUVAR: kapiya dik, turuncu=koridora paralel
        yp=ray1
        while yp+pg_y<=ray2:
            raflar.append((sx1,yp,sx2,yp+pg_y,0)); yp+=pg_y

        # SAG DUVAR: kapiya dik, turuncu=koridora paralel
        yp=ray1
        while yp+pg_y<=ray2:
            raflar.append((rx1,yp,rx2,yp+pg_y,0)); yp+=pg_y

        # ARKA DUVAR: kapiya PARALEL, turuncu=kapiya paralel
        # x boyutu=pg_x (uzun, X yonunde), y boyutu=dr_y (kisa, Y yonunde)
        xp=sx2+kor_x
        while xp+pg_x<=rx1-kor_x:
            raflar.append((xp,ay1,xp+pg_x,ay2,1)); xp+=pg_x

        od(draw,rax1-18,ray1,ray1+dr_x,f"{DR}m",fsm,GR)
        od(draw,rax1-18,ray1,ray1+pg_y,f"{pg}m",fsm,MO)
        oy(draw,sx2,sx2+kor_x,ray1-14,f"{kor}m",fsm,MO)

        # ORTA BLOKLAR: kapiya dik, turuncu=koridora paralel
        ox1=sx2+kor_x; ox2=rx1-kor_x
        oy_bas=ay2+kor_x
        xp=ox1; b=0
        while xp+blok_x<=ox2 and b<sec['ob']:
            bx1=xp; bx2=bx1+dr_x; bx3=bx2+kor_x; bx4=bx3+dr_x
            yp=oy_bas
            while yp+pg_y<=ray2:
                raflar.append((bx1,yp,bx2,yp+pg_y,0))
                raflar.append((bx3,yp,bx4,yp+pg_y,0))
                yp+=pg_y
            if b==0: oy(draw,bx2,bx3,oy_bas-14,f"{kor}m",fsm,MO)
            xp=bx4+max(int(0.1*sx),2); b+=1

    # CIZ
    for r in raflar:
        if r[4]==0: raf_koridor_paralel(draw,r[0],r[1],r[2],r[3])
        else:       raf_kapi_paralel(draw,r[0],r[1],r[2],r[3])

    # ALT BILGI
    iy=H-INFO_H
    draw.rectangle([0,iy,W,H],fill='#161b22')
    draw.line([0,iy,W,iy],fill='#404060',width=2)

    dk=len(raflar)*4; yt=len(raflar)*kat*2; ds=len(raflar)*2
    kap=sec['toplam']*kat*d['palet']
    sep='#303050'; c1=20; c2=W//3+10; c3=W*2//3+10

    # Sutun 1: Malzeme
    lx=c1; ly=iy+14
    if lg=='tr':
        draw.text((lx,ly),"MALZEME",fill=SA,font=fb); ly+=20
        for lbl,clr,val in [("● Dikme",MA,f"1={ry}m|{dk}x|Top:{round(dk*ry,1)}m"),
                             ("━ Yatay",TU,f"1={pg}m|{yt}x|Top:{round(yt*pg,1)}m"),
                             ("| Derinlik",GR,f"1=1.1m|{ds}x|Top:{round(ds*1.1,1)}m"),
                             ("▦ Yukleme",YE,f"{yen}x{ybo}m={ym2}m²"),
                             ("↔ Koridor",MO,f"{kor}m|Kapi:{gg}m|Kat:{kat}")]:
            draw.text((lx,ly),lbl+":",fill=clr,font=fb)
            draw.text((lx+88,ly),val,fill=W2,font=fn); ly+=18
    else:
        draw.text((lx,ly),"МАТЕРИАЛЫ",fill=SA,font=fb); ly+=20
        for lbl,clr,val in [("● Стойка",MA,f"1={ry}м|{dk}x|Ит:{round(dk*ry,1)}м"),
                             ("━ Балка",TU,f"1={pg}м|{yt}x|Ит:{round(yt*pg,1)}м"),
                             ("| Глубина",GR,f"1=1.1м|{ds}x|Ит:{round(ds*1.1,1)}м"),
                             ("▦ Зона",YE,f"{yen}x{ybo}м={ym2}м²"),
                             ("↔ Проход",MO,f"{kor}м|Вор:{gg}м|Яр:{kat}")]:
            draw.text((lx,ly),lbl+":",fill=clr,font=fb)
            draw.text((lx+85,ly),val,fill=W2,font=fn); ly+=18

    draw.line([c2-10,iy+10,c2-10,H-10],fill=sep,width=1)

    # Sutun 2: Verim analizi
    lx=c2; ly=iy+14
    if lg=='tr':
        draw.text((lx,ly),"VERİM ANALİZİ",fill=SA,font=fb); ly+=20
        for k,v in [("Toplam Raf",str(sec['toplam'])),("Palet Kap.",f"{kap} palet"),
                    ("Raf Alani",f"{sec['raf_alani']} m²"),("Kat",str(kat)),("Raf Yuk.",f"{ry}m")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+150,ly),v,fill=W2,font=fb); ly+=18
    else:
        draw.text((lx,ly),"АНАЛИЗ КПД",fill=SA,font=fb); ly+=20
        for k,v in [("Стеллажей",str(sec['toplam'])),("Ёмкость",f"{kap} палл."),
                    ("Пл.стелл.",f"{sec['raf_alani']} м²"),("Ярусов",str(kat)),("Высота",f"{ry}м")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+150,ly),v,fill=W2,font=fb); ly+=18

    draw.line([c3-10,iy+10,c3-10,H-10],fill=sep,width=1)

    # Sutun 3: Depo verimi
    lx=c3; ly=iy+14
    bos=round(sec['depo_alani']-sec['raf_alani']-ym2,1)
    if lg=='tr':
        draw.text((lx,ly),"DEPO VERİMİ",fill=SA,font=fb); ly+=20
        for k,v,c in [("Depo Alani",f"{sec['depo_alani']} m²",W2),
                      ("Raf Alani",f"{sec['raf_alani']} m²",W2),
                      ("Yukleme",f"{ym2} m²",YE),
                      ("Bos Alan",f"{bos} m²",AG),
                      ("VERİM",f"%{sec['verim']}",SA)]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx,ly+14),v,fill=c,font=fb if k=="VERİM" else fn); ly+=32
    else:
        draw.text((lx,ly),"КПД СКЛАДА",fill=SA,font=fb); ly+=20
        for k,v,c in [("Пл.склада",f"{sec['depo_alani']} м²",W2),
                      ("Пл.стелл.",f"{sec['raf_alani']} м²",W2),
                      ("Зона",f"{ym2} м²",YE),
                      ("Своб.",f"{bos} м²",AG),
                      ("КПД",f"{sec['verim']}%",SA)]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx,ly+14),v,fill=c,font=fb if k=="КПД" else fn); ly+=32

    buf=io.BytesIO()
    img.save(buf,format='PNG',dpi=(150,150))
    buf.seek(0)
    return buf

# HANDLERS

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
        context.user_data['giris_konum']='orta'; context.user_data['giris_mesafe']=0.0
    elif "sol" in t or "левее" in t: context.user_data['giris_konum']='sol'
    else: context.user_data['giris_konum']='sag'
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
        layouts=hesapla(d)
        await update.message.reply_text(
            "⏳ 2 secenek hazirlaniyor..." if lg=='tr' else "⏳ Готовлю 2 варианта...",
            reply_markup=ReplyKeyboardRemove())
        secs=[layouts['U_MAKS'],layouts['I_MAKS']]
        secs.sort(key=lambda x:x['toplam'],reverse=True)
        for i,sec in enumerate(secs):
            resim=ciz(d,lg,sec,i+1)
            tn={'U_MAKS':'U-МAKS' if lg=='ru' else 'U-MAKS',
                'I_MAKS':'I-МАКС' if lg=='ru' else 'I-MAKS'}.get(sec['tip'],sec['tip'])
            kap=sec['toplam']*d['kat']*d['palet']
            cap=(f"{'⭐ EN İYİ — ' if i==0 else ''}{i+1}. {tn}\n"
                 f"Raf:{sec['toplam']} | Kap:{kap} palet | Verim:%{sec['verim']}" if lg=='tr'
                 else f"{'⭐ ЛУЧШИЙ — ' if i==0 else ''}{i+1}. {tn}\n"
                      f"Стелл:{sec['toplam']} | Ёмк:{kap} | КПД:{sec['verim']}%")
            await update.message.reply_photo(photo=resim,caption=cap)
        await update.message.reply_text(
            "✅ Hazir! /hesapla" if lg=='tr' else "✅ Готово! /raschet")
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
