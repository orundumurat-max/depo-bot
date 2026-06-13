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
DR        = 1.1

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
    ib=max(1,int(ef_x/blok)); iry=max(1,int(ef_y/pg))
    i_raf=ib*2*iry; i_alan=ib*blok*ef_y
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

def raf_dik(draw, x1, y1, x2, y2):
    """Kapiya dik raf. Yesil=ust/alt(koridora paralel). Turuncu=sol/sag."""
    draw.rectangle([x1,y1,x2,y2],fill='#081420')
    draw.line([x1,y1,x2,y2],fill='#3a4a5a',width=2)
    draw.line([x2,y1,x1,y2],fill='#3a4a5a',width=2)
    draw.rectangle([x1,y1,x2,y2],outline='#3a4a60',width=1)
    draw.line([x1+2,y1,x2-2,y1],fill='#4ade80',width=3)
    draw.line([x1+2,y2,x2-2,y2],fill='#4ade80',width=3)
    draw.line([x1,y1+2,x1,y2-2],fill='#ff8c42',width=2)
    draw.line([x2,y1+2,x2,y2-2],fill='#ff8c42',width=2)
    for px,py in [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]:
        draw.ellipse([px-4,py-4,px+4,py+4],fill='#4a9eff',outline='white',width=1)

def raf_par(draw, x1, y1, x2, y2):
    """Kapiya paralel raf (arka duvar). Yesil=sol/sag. Turuncu=ust/alt."""
    draw.rectangle([x1,y1,x2,y2],fill='#081420')
    draw.line([x1,y1,x2,y2],fill='#3a4a5a',width=2)
    draw.line([x2,y1,x1,y2],fill='#3a4a5a',width=2)
    draw.rectangle([x1,y1,x2,y2],outline='#3a4a60',width=1)
    draw.line([x1,y1+2,x1,y2-2],fill='#4ade80',width=3)
    draw.line([x2,y1+2,x2,y2-2],fill='#4ade80',width=3)
    draw.line([x1+2,y1,x2-2,y1],fill='#ff8c42',width=2)
    draw.line([x1+2,y2,x2-2,y2],fill='#ff8c42',width=2)
    for px,py in [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]:
        draw.ellipse([px-4,py-4,px+4,py+4],fill='#4a9eff',outline='white',width=1)

def oy(draw,x1,x2,y,t,f,c,bold=False):
    draw.line([x1,y,x2,y],fill=c,width=1)
    draw.line([x1,y-5,x1,y+5],fill=c,width=2)
    draw.line([x2,y-5,x2,y+5],fill=c,width=2)
    draw.text(((x1+x2)//2,y-6),t,fill=c,font=f,anchor='mb')

def od(draw,x,y1,y2,t,f,c):
    draw.line([x,y1,x,y2],fill=c,width=1)
    draw.line([x-5,y1,x+5,y1],fill=c,width=2)
    draw.line([x-5,y2,x+5,y2],fill=c,width=2)
    draw.text((x+6,(y1+y2)//2),t,fill=c,font=f,anchor='lm')

def ciz(d,lg,sec,sira):
    U=d['uzunluk']; G=d['genislik']
    pg=PALET_G[d['palet']]; kor=KORIDOR_G[d['koridor_tipi']]
    kb2=d.get('kenar_bosluk',0.0)
    gk=d.get('giris_konum','orta'); gm=d.get('giris_mesafe',0.0)
    gg=d.get('giris_genislik',4.0)
    kat=d['kat']; ry=d['raf_yuk']
    tip=sec['tip']
    yen=sec['yuk_en']; ybo=sec['yuk_boy']; ym2=sec['yuk_m2']

    W,H=1280,1020
    img=Image.new('RGB',(W,H),'#0d1117')
    draw=ImageDraw.Draw(img)

    try:
        fb =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",15)
        fn =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",13)
        ft =ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",18)
        fsm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",12)
        fxs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",11)
        fti=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",13)
    except:
        fb=fn=ft=fsm=fxs=fti=ImageFont.load_default()

    W2='#e8e8e8'; AG='#606080'; SA='#ffd700'; SI='#00b4d8'
    MO='#c084fc'; YE='#22c55e'; TU='#ff8c42'; GR='#4ade80'; MA='#4a9eff'
    KIRMIZI='#ff6b6b'; ACIK='#8899aa'

    INFO_H=215
    pl,pt,pr,pb=85,58,55,INFO_H+52
    pw=W-pl-pr; ph=H-pt-pb
    ox=pl; oy0=pt
    sx=pw/U; sy=ph/G

    # BASLIK
    draw.rectangle([0,0,W,44],fill='#161b22')
    tad={'U_MAKS':('U-MAKS: Duvar+Orta','U-МАКС: Стены+Центр'),
         'I_MAKS':('I-MAKS: Sirt Sirta','I-МАКС: Спина к спине')}
    tn=tad.get(tip,(tip,tip))[1 if lg=='ru' else 0]
    bl=(f"SECENEK {sira}/2  |  {tn}  |  {sec['toplam']} raf  |  Verim:%{sec['verim']}" if lg=='tr'
        else f"ВАРИАНТ {sira}/2  |  {tn}  |  {sec['toplam']} стелл.  |  КПД:{sec['verim']}%")
    draw.text((W//2,22),bl,fill=SA,font=ft,anchor='mm')

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
    draw.text(((yx1+yx2)//2,(yy1+yy2)//2-9),
              "YUKLEME/BOSALTMA" if lg=='tr' else "ЗОНА ПОГРУЗКИ",fill=YE,font=fxs,anchor='mm')
    draw.text(((yx1+yx2)//2,(yy1+yy2)//2+9),
              f"{yen}x{ybo}m={ym2}m²",fill=YE,font=fb,anchor='mm')
    oy(draw,yx1,yx2,yy1-14,f"{yen}m",fsm,YE)
    od(draw,yx2+10,yy1,yy2,f"{ybo}m",fsm,YE)
    draw.line([gx-Gpx//2,oy0+ph,gx+Gpx//2,oy0+ph],fill=SA,width=9)
    kl="GİRİŞ/ÇIKIŞ" if lg=='tr' else "ВХОД/ВЫХОД"
    draw.text((gx,oy0+ph+11),kl,fill=SA,font=fsm,anchor='mt')
    oy(draw,gx-Gpx//2,gx+Gpx//2,oy0+ph+26,f"{gg}m",fsm,SA)
    if gm>0 and gk!='orta':
        if gk=='sol': oy(draw,ox,gx-Gpx//2,oy0+ph+42,f"{gm}m",fsm,W2)
        else: oy(draw,gx+Gpx//2,ox+pw,oy0+ph+42,f"{gm}m",fsm,W2)

    # ANA OLCULAR
    oy(draw,ox,ox+pw,oy0-22,f"{U}m",fn,W2)
    od(draw,ox-22,oy0,oy0+ph,f"{G}m",fn,W2)

    # RAF ALANI
    rax1=ox+int(kb2*sx); ray1=oy0+int(kb2*sy)
    rax2=ox+pw-int(kb2*sx); ray2=oy0+ph-int(ybo*sy)-int(kb2*sy)

    dr_x=max(int(DR*sx),5)
    pg_y=max(int(pg*sy),6)
    kor_x=max(int(kor*sx),4)
    blok_x=dr_x*2+kor_x
    pg_x=max(int(pg*sx),6)
    dr_y=max(int(DR*sy),5)

    raflar=[]

    if tip=='I_MAKS':
        # Bloklari X yonunde diz, son blok RAX2'ye yapistir
        toplam_blok_genislik = sec['ib'] * blok_x + (sec['ib']-1) * max(int(0.1*sx),2)
        # Son sira duvara yapismali: basa gore hesapla
        x_start = rax1
        x_bitis = rax2  # son blok buna dayanacak
        # Bloklari saga hizala (son sira duvara)
        toplam = sec['ib'] * blok_x
        bosluk_aralik = max(int(0.1*sx),2)
        if sec['ib'] > 1:
            # Esit aralikli yerlestir, son sira duvara
            toplam_w = sec['ib']*blok_x + (sec['ib']-1)*bosluk_aralik
            x_start = rax2 - toplam_w
            if x_start < rax1: x_start = rax1

        x=x_start; b=0
        blok_konumlari=[]
        while b < sec['ib']:
            bx1=x; bx2=bx1+dr_x; bx3=bx2+kor_x; bx4=bx3+dr_x
            if bx4 > rax2: break
            yp=ray1
            while yp+pg_y<=ray2:
                raflar.append((bx1,yp,bx2,yp+pg_y,0))
                raflar.append((bx3,yp,bx4,yp+pg_y,0))
                yp+=pg_y
            blok_konumlari.append((bx1,bx4,yp-pg_y))
            x=bx4+bosluk_aralik; b+=1

        # Olcular
        if blok_konumlari:
            # Ilk blogun yatay bag olcusu - ortada gorünür
            bx1,bx4,son_yp=blok_konumlari[0]
            bx2=bx1+dr_x; bx3=bx2+kor_x
            orta_y=(ray1+son_yp+pg_y)//2
            # Koridor olcusu
            oy(draw,bx2,bx3,ray1-16,f"{kor}m",fsm,MO)
            # Yatay bag olcusu (pg) - rafin ortasinda görünür
            oy(draw,bx1,bx2+dr_x,orta_y,f"{pg}m",fti,TU)
            # Derinlik olcusu
            od(draw,rax1-22,ray1,ray1+dr_x,f"{DR}m",fsm,GR)
            # Toplam raf uzunlugu (Y yonu)
            raf_uzun_m=round(sec['iry']*pg,1)
            od(draw,ox+pw+12,ray1,ray1+int(raf_uzun_m*sy),f"{raf_uzun_m}m",fsm,W2)
            # Toplam X uzunlugu
            oy(draw,x_start,x_start+int(b*blok_x*sx/sx),ray1-16,f"",fsm,ACIK)
            # Kalan bosluk saga
            if x_start > rax1:
                kalan_m=round((x_start-rax1)/sx,2)
                oy(draw,rax1,x_start,ray2+14,f"Bos:{kalan_m}m" if lg=='tr' else f"Св:{kalan_m}м",fxs,KIRMIZI)

    elif tip=='U_MAKS':
        # Sol/sag duvar - duvara yapistir
        sx1=rax1; sx2=rax1+dr_x
        rx1=rax2-dr_x; rx2=rax2
        ay1=ray1; ay2=ray1+dr_y

        # Sol duvar rafları
        yp=ray1
        while yp+pg_y<=ray2:
            raflar.append((sx1,yp,sx2,yp+pg_y,0)); yp+=pg_y
        sol_son_yp=yp

        # Sag duvar raflari
        yp=ray1
        while yp+pg_y<=ray2:
            raflar.append((rx1,yp,rx2,yp+pg_y,0)); yp+=pg_y

        # Arka duvar raflari (kapiya paralel)
        # Sag kenara yapistir
        xp_arka_bitis=rx1-kor_x
        xp_arka_bas=sx2+kor_x
        arka_toplam_w=xp_arka_bitis-xp_arka_bas
        n_arka=max(1,int(arka_toplam_w/pg_x))
        arka_x_start=xp_arka_bitis-n_arka*pg_x  # saga hizali
        if arka_x_start<xp_arka_bas: arka_x_start=xp_arka_bas
        xp=arka_x_start
        while xp+pg_x<=xp_arka_bitis:
            raflar.append((xp,ay1,xp+pg_x,ay2,1)); xp+=pg_x
        arka_son_x=xp

        # Arka duvar olculeri
        oy(draw,arka_x_start,arka_son_x,ay1-16,f"{round((arka_son_x-arka_x_start)/sx,1)}m",fsm,W2)
        od(draw,rax1-22,ay1,ay2,f"{DR}m",fsm,GR)
        # Arka raf yatay bag olcusu
        if n_arka>0:
            oy(draw,arka_x_start,arka_x_start+pg_x,(ay1+ay2)//2,f"{pg}m",fti,TU)

        # Sol raf olcusu
        od(draw,ox+pw+12,ray1,ray1+int(sec['rys']*pg*sy),f"{round(sec['rys']*pg,1)}m",fsm,W2)
        od(draw,rax1-22,ray1,ray1+pg_y,f"{pg}m",fsm,TU)

        # Koridor olcusu
        oy(draw,sx2,sx2+kor_x,ray1-16,f"{kor}m",fsm,MO)

        # ORTA BLOKLAR - sag duvara yapistir
        orta_x1=sx2+kor_x; orta_x2=rx1-kor_x
        oy_bas=ay2+kor_x

        # Kac blok sigacak
        blok_aralik=max(int(0.1*sx),2)
        avail=orta_x2-orta_x1
        n_blok=sec['ob']
        if n_blok>0:
            toplam_blok_w=n_blok*blok_x+(n_blok-1)*blok_aralik
            orta_x_start=orta_x2-toplam_blok_w
            if orta_x_start<orta_x1: orta_x_start=orta_x1
        else:
            orta_x_start=orta_x1

        xp=orta_x_start; b=0
        orta_blok_ler=[]
        while xp+blok_x<=orta_x2 and b<n_blok:
            bx1=xp; bx2=bx1+dr_x; bx3=bx2+kor_x; bx4=bx3+dr_x
            yp=oy_bas
            while yp+pg_y<=ray2:
                raflar.append((bx1,yp,bx2,yp+pg_y,0))
                raflar.append((bx3,yp,bx4,yp+pg_y,0))
                yp+=pg_y
            orta_blok_ler.append((bx1,bx4,yp-pg_y))
            xp=bx4+blok_aralik; b+=1

        if orta_blok_ler:
            bx1,bx4,son_yp=orta_blok_ler[0]
            bx2=bx1+dr_x; bx3=bx2+kor_x
            orta_yort=(oy_bas+son_yp+pg_y)//2
            oy(draw,bx2,bx3,oy_bas-16,f"{kor}m",fsm,MO)
            oy(draw,bx1,bx4,orta_yort,f"{pg}m",fti,TU)
            # Orta toplam uzunluk
            oy(draw,orta_x_start,xp-blok_aralik,oy_bas-16,
               f"{round((xp-blok_aralik-orta_x_start)/sx,1)}m",fxs,ACIK)

        # Kalan bosluklar
        if orta_x_start>orta_x1:
            kalan=round((orta_x_start-orta_x1)/sx,2)
            oy(draw,orta_x1,orta_x_start,ray2+14,
               f"Bos:{kalan}m" if lg=='tr' else f"Св:{kalan}м",fxs,KIRMIZI)
        if arka_x_start>xp_arka_bas:
            kalan2=round((arka_x_start-xp_arka_bas)/sx,2)
            oy(draw,xp_arka_bas,arka_x_start,ay2+12,
               f"Bos:{kalan2}m" if lg=='tr' else f"Св:{kalan2}м",fxs,KIRMIZI)

    # RAFLARI CIZ
    for r in raflar:
        if r[4]==0: raf_dik(draw,r[0],r[1],r[2],r[3])
        else:       raf_par(draw,r[0],r[1],r[2],r[3])

    # ALT BILGI
    iy=H-INFO_H
    draw.rectangle([0,iy,W,H],fill='#161b22')
    draw.line([0,iy,W,iy],fill='#404060',width=2)

    dk=len(raflar)*4
    yatay_adet=len(raflar)*2
    dk_metre=round(dk*ry,1)
    kap=sec['toplam']*kat*d['palet']
    sep='#303050'
    c1=20; c2=W//3+15; c3=W*2//3+15

    def satir(lx,ly,lbl,clr,val,vclr=None):
        draw.text((lx,ly),lbl,fill=clr,font=fb)
        draw.text((lx+105,ly),val,fill=vclr or W2,font=fn)
        return ly+22

    # SUTUN 1: MALZEME
    lx=c1; ly=iy+16
    draw.text((lx,ly),"MALZEME LİSTESİ" if lg=='tr' else "СПИСОК МАТЕРИАЛОВ",fill=SA,font=fb); ly+=24
    if lg=='tr':
        ly=satir(lx,ly,"● Dikme:",MA,f"1={ry}m | {dk} adet | Top:{dk_metre}m")
        ly=satir(lx,ly,"━ Derinlik:",GR,"1 adet = 1.10m (sabit)")
        ly=satir(lx,ly,"| Yatay Bag.:",TU,f"{yatay_adet} adet | {pg}m")
        ly=satir(lx,ly,"▦ Yukleme:",YE,f"{yen}x{ybo}m = {ym2}m²",YE)
        ly=satir(lx,ly,"↔ Koridor:",MO,f"{kor}m | Kapi:{gg}m | Kat:{kat}")
    else:
        ly=satir(lx,ly,"● Стойка:",MA,f"1={ry}м | {dk} шт | Ит:{dk_metre}м")
        ly=satir(lx,ly,"━ Глубина:",GR,"1 шт = 1.10м (фикс.)")
        ly=satir(lx,ly,"| Гориз.балка:",TU,f"{yatay_adet} шт | {pg}м")
        ly=satir(lx,ly,"▦ Зона:",YE,f"{yen}x{ybo}м = {ym2}м²",YE)
        ly=satir(lx,ly,"↔ Проход:",MO,f"{kor}м | Вор:{gg}м | Яр:{kat}")

    draw.line([c2-12,iy+12,c2-12,H-12],fill=sep,width=1)

    # SUTUN 2: VERIM ANALIZI
    lx=c2; ly=iy+16
    draw.text((lx,ly),"VERİM ANALİZİ" if lg=='tr' else "АНАЛИЗ КПД",fill=SA,font=fb); ly+=24
    if lg=='tr':
        for k,v in [("Toplam Raf",str(sec['toplam'])),("Palet Kap.",f"{kap} palet"),
                    ("Raf Alani",f"{sec['raf_alani']} m²"),("Kat",str(kat)),("Raf Yuk.",f"{ry}m")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+165,ly),v,fill=W2,font=fb); ly+=22
    else:
        for k,v in [("Стеллажей",str(sec['toplam'])),("Ёмкость",f"{kap} палл."),
                    ("Пл.стелл.",f"{sec['raf_alani']} м²"),("Ярусов",str(kat)),("Высота",f"{ry}м")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+165,ly),v,fill=W2,font=fb); ly+=22

    draw.line([c3-12,iy+12,c3-12,H-12],fill=sep,width=1)

    # SUTUN 3: DEPO VERIMI
    lx=c3; ly=iy+16
    draw.text((lx,ly),"DEPO VERİMİ" if lg=='tr' else "КПД СКЛАДА",fill=SA,font=fb); ly+=24
    bos=round(sec['depo_alani']-sec['raf_alani']-ym2,1)
    if lg=='tr':
        items=[("Depo Alani",f"{sec['depo_alani']} m²",W2),
               ("Raf Alani",f"{sec['raf_alani']} m²",W2),
               ("Yukleme",f"{ym2} m²",YE),
               ("Bos Alan",f"{bos} m²",AG),
               ("VERİM",f"%{sec['verim']}",SA)]
    else:
        items=[("Пл.склада",f"{sec['depo_alani']} м²",W2),
               ("Пл.стелл.",f"{sec['raf_alani']} м²",W2),
               ("Зона",f"{ym2} м²",YE),
               ("Своб.",f"{bos} м²",AG),
               ("КПД",f"{sec['verim']}%",SA)]
    for k,v,c in items:
        draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
        draw.text((lx+165,ly),v,fill=c,font=fb if k in ("VERİM","КПД") else fn); ly+=22

    buf=io.BytesIO()
    img.save(buf,format='PNG',dpi=(150,150))
    buf.seek(0)
    return buf

async def baslat(update,context):
    context.user_data.clear()
    await update.message.reply_text("Dil secin / Выберите язык:",
        reply_markup=kb([["🇹🇷 Turkce","🇷🇺 Russkiy"]]))
    return LANG

async def lang_sec(update,context):
    context.user_data['lang']='ru' if "Russkiy" in update.message.text else 'tr'
    lg=glang(context)
    await update.message.reply_text(
        "📏 Depo uzunlugu (m):\nOrnek: 20" if lg=='tr' else "📏 Длина склада (м):\nПример: 20",
        reply_markup=ReplyKeyboardRemove())
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
        await update.message.reply_text(
            "🚪 Kapi genisligi (m):\nOrnek: 4" if lg=='tr' else "🚪 Ширина ворот (м):\nПример: 4",
            reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    elif "sol" in t or "левее" in t: context.user_data['giris_konum']='sol'
    else: context.user_data['giris_konum']='sag'
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
            tn={'U_MAKS':'U-МАКС' if lg=='ru' else 'U-MAKS',
                'I_MAKS':'I-МАКС' if lg=='ru' else 'I-MAKS'}.get(sec['tip'],sec['tip'])
            kap=sec['toplam']*d['kat']*d['palet']
            cap=(f"{'⭐ EN İYİ — ' if i==0 else ''}{i+1}. {tn}\n"
                 f"Raf:{sec['toplam']} | Kap:{kap} palet | Verim:%{sec['verim']}" if lg=='tr'
                 else f"{'⭐ ЛУЧШИЙ — ' if i==0 else ''}{i+1}. {tn}\n"
                      f"Стелл:{sec['toplam']} | Ёмк:{kap} | КПД:{sec['verim']}%")
            await update.message.reply_photo(photo=resim,caption=cap)
        await update.message.reply_text("✅ Hazir! /hesapla" if lg=='tr' else "✅ Готово! /raschet")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

async def iptal(update,context):
    lg=glang(context)
    await update.message.reply_text("Iptal. /hesapla" if lg=='tr' else "Отменено. /raschet",
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
