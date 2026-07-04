import os, logging, io, math
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

def get_fonts():
    paths_b = ["/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    paths_n = ["/usr/share/fonts/truetype/freefont/FreeSans.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    def ff(bold, size):
        for p in (paths_b if bold else paths_n):
            try: return ImageFont.truetype(p, size)
            except: pass
        return ImageFont.load_default()
    return ff(True,18), ff(True,15), ff(False,13), ff(False,12), ff(False,11), ff(True,13)

def hesapla(d):
    U=d['uzunluk']; G=d['genislik']
    pg=PALET_G[d['palet']]; kor=KORIDOR_G[d['koridor_tipi']]
    kb2=d.get('kenar_bosluk',0.0)
    yen=d.get('yuk_en',5.0); ybo=d.get('yuk_boy',5.0); kat=d['kat']
    ef_x=max(U-kb2*2,0.1); ef_y=max(G-kb2*2-ybo,0.1)
    yuk_m2=round(yen*ybo,1); blok=DR*2+kor
    ib=max(1,int(ef_x/blok)); iry=max(1,int(ef_y/pg))
    i_raf=ib*2*iry; i_alan=ib*blok*ef_y
    ic_x=ef_x-DR*2-kor*2
    ob=max(0,int(ic_x/blok)) if ic_x>0 else 0
    rys=max(1,int(ef_y/pg)); rxa=max(1,int(ef_x/pg))
    u_raf=rys*2+rxa+ob*2*rys; u_alan=DR*ef_y*2+DR*ef_x+ob*blok*ef_y
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

def iso_pt(x, y, z, ox, oy, s):
    ix = ox + (x - y) * s * math.cos(math.radians(30))
    iy = oy - z * s + (x + y) * s * math.sin(math.radians(30))
    return (int(ix), int(iy))

def draw_box(draw, x,y,z, w,d,h, s,ox,oy, top,left,right, outline='#000000'):
    p000=iso_pt(x,y,z,ox,oy,s); p100=iso_pt(x+w,y,z,ox,oy,s)
    p010=iso_pt(x,y+d,z,ox,oy,s); p110=iso_pt(x+w,y+d,z,ox,oy,s)
    p001=iso_pt(x,y,z+h,ox,oy,s); p101=iso_pt(x+w,y,z+h,ox,oy,s)
    p011=iso_pt(x,y+d,z+h,ox,oy,s); p111=iso_pt(x+w,y+d,z+h,ox,oy,s)
    draw.polygon([p001,p101,p111,p011],fill=top,outline=outline)
    draw.polygon([p010,p110,p111,p011],fill=left,outline=outline)
    draw.polygon([p100,p110,p111,p101],fill=right,outline=outline)

def draw_raf(draw, rx,ry,rz, rw,rd,rh, kat, s,ox,oy):
    TURUNCU='#ff8c42'; TU_D='#cc5500'; TU_R='#aa3300'
    GR='#4a9eff'; GR_D='#2255cc'; GR_R='#1a3399'
    DIKME_TOP='#2a6a2a'; DIKME_L='#1a4a1a'; DIKME_R='#122e12'

    dw=0.06  # dikme genisligi
    # 4 dikme
    for dx,dy in [(0,0),(rw-dw,0),(0,rd-dw),(rw-dw,rd-dw)]:
        draw_box(draw,rx+dx,ry+dy,rz,dw,dw,rh,s,ox,oy,
                 DIKME_TOP,DIKME_L,DIKME_R,'#4a9eff')

    # Alt ve ust cerceve (yatay, Y yonunde = derinlik baglayici)
    fw=0.05
    for zz in [rz, rz+rh-fw]:
        draw_box(draw,rx,ry,zz,rw,fw,fw,s,ox,oy,GR,GR_D,GR_R,'#001133')
        draw_box(draw,rx,ry+rd-fw,zz,rw,fw,fw,s,ox,oy,GR,GR_D,GR_R,'#001133')

    # Kat baglantilari (turuncu - X yonunde yan baglanti, her kat icin)
    for k in range(1, kat+1):
        kz = rz + k * rh / (kat+1)
        # On taraf (y=ry) - turuncu yan baglanti
        draw_box(draw,rx,ry,kz,rw,fw,fw,s,ox,oy,TURUNCU,TU_D,TU_R,'#330000')
        # Arka taraf (y=ry+rd)
        draw_box(draw,rx,ry+rd-fw,kz,rw,fw,fw,s,ox,oy,TURUNCU,TU_D,TU_R,'#330000')

def ciz_iso(d, lg, sec, sira):
    U=d['uzunluk']; G=d['genislik']
    pg=PALET_G[d['palet']]; kor=KORIDOR_G[d['koridor_tipi']]
    kb2=d.get('kenar_bosluk',0.0)
    gk=d.get('giris_konum','orta'); gm=d.get('giris_mesafe',0.0)
    gg=d.get('giris_genislik',4.0)
    kat=d['kat']; ry_h=d['raf_yuk']
    tip=sec['tip']
    yen=sec['yuk_en']; ybo=sec['yuk_boy']; ym2=sec['yuk_m2']
    kb2v=d.get('kenar_bosluk',0.0)

    ft,fb,fn,fsm,fxs,fti = get_fonts()

    W,H=1500,1100
    img=Image.new('RGB',(W,H),'#080e1a')
    draw=ImageDraw.Draw(img)

    W2='#e8e8e8'; AG='#606080'; SA='#ffd700'; SI='#00b4d8'
    MO='#c084fc'; YE='#22c55e'; TU='#ff8c42'; GR='#4ade80'; MA='#4a9eff'
    INFO_H=220

    # Scale - BUYUK
    s = max(18, min(45, int(550 / max(U, G))))

    iso_ox = W//2 - 50
    iso_oy = 480

    # BASLIK
    draw.rectangle([0,0,W,46],fill='#161b22')
    tad={'U_MAKS':('U-MAKS','U-МАКС'),'I_MAKS':('I-MAKS','I-МАКС')}
    tn=tad.get(tip,('?','?'))[1 if lg=='ru' else 0]
    bl=(f"IZOMETRIK CIZIM  |  SECENEK {sira}/2  |  {tn}  |  {sec['toplam']} raf  |  Verim:%{sec['verim']}" if lg=='tr'
        else f"ИЗОМЕТРИЯ  |  ВАРИАНТ {sira}/2  |  {tn}  |  {sec['toplam']} стелл.  |  КПД:{sec['verim']}%")
    draw.text((W//2,23),bl,fill=SA,font=ft,anchor='mm')

    # DEPO SINIRI - izometrik
    def depo_yuz(ya, yb, za, zb, xa, xb, clr, ol):
        pts=[]
        for x,y,z in [(xa,ya,za),(xb,ya,za),(xb,yb,za),(xa,yb,za)]:
            pts.append(iso_pt(x,y,z,iso_ox,iso_oy,s))
        draw.polygon(pts,fill=clr,outline=ol)

    # Zemin
    p1=iso_pt(0,0,0,iso_ox,iso_oy,s); p2=iso_pt(U,0,0,iso_ox,iso_oy,s)
    p3=iso_pt(U,G,0,iso_ox,iso_oy,s); p4=iso_pt(0,G,0,iso_ox,iso_oy,s)
    draw.polygon([p1,p2,p3,p4],fill='#0d1520',outline=SI)

    # Arka duvar (y=G)
    dh=ry_h*0.35
    pw=[iso_pt(0,G,0,iso_ox,iso_oy,s),iso_pt(U,G,0,iso_ox,iso_oy,s),
        iso_pt(U,G,dh,iso_ox,iso_oy,s),iso_pt(0,G,dh,iso_ox,iso_oy,s)]
    draw.polygon(pw,fill='#0c1a0c',outline='#1a4a1a')

    # Sol duvar (x=0)
    ps=[iso_pt(0,0,0,iso_ox,iso_oy,s),iso_pt(0,G,0,iso_ox,iso_oy,s),
        iso_pt(0,G,dh,iso_ox,iso_oy,s),iso_pt(0,0,dh,iso_ox,iso_oy,s)]
    draw.polygon(ps,fill='#0a1508',outline='#1a4a1a')

    # Depo kenari cizgileri
    for xa,ya,xb,yb in [(0,0,U,0),(U,0,U,G),(U,G,0,G),(0,G,0,0)]:
        draw.line([iso_pt(xa,ya,0,iso_ox,iso_oy,s),iso_pt(xb,yb,0,iso_ox,iso_oy,s)],fill=SI,width=2)

    # YUKLEME ALANI (yesil, zemin uzerinde)
    if gk=='orta': gx_m=U/2
    elif gk=='sol': gx_m=min(gm+gg/2, U)
    else: gx_m=max(U-gm-gg/2, 0)
    yx1=max(0,gx_m-yen/2); yx2=min(U,gx_m+yen/2)

    zy=[iso_pt(yx1,0,0.02,iso_ox,iso_oy,s),iso_pt(yx2,0,0.02,iso_ox,iso_oy,s),
        iso_pt(yx2,ybo,0.02,iso_ox,iso_oy,s),iso_pt(yx1,ybo,0.02,iso_ox,iso_oy,s)]
    draw.polygon(zy,fill='#052e16',outline=YE)
    zm=iso_pt((yx1+yx2)/2,ybo/2,0.1,iso_ox,iso_oy,s)
    draw.text(zm,f"{yen}x{ybo}m\n={ym2}m²",fill=YE,font=fsm,anchor='mm')

    # KAPI (sari)
    kp=[iso_pt(gx_m-gg/2,0,0,iso_ox,iso_oy,s),iso_pt(gx_m+gg/2,0,0,iso_ox,iso_oy,s),
        iso_pt(gx_m+gg/2,0,dh*0.8,iso_ox,iso_oy,s),iso_pt(gx_m-gg/2,0,dh*0.8,iso_ox,iso_oy,s)]
    draw.polygon(kp,fill='#1a2a08',outline=SA)
    kpm=iso_pt(gx_m,0,dh*0.4,iso_ox,iso_oy,s)
    draw.text(kpm,"GIRIS" if lg=='tr' else "ВХОД",fill=SA,font=fxs,anchor='mm')

    # ÖLÇÜ ETİKETLERİ (izometrik zemin uzerinde)
    # Depo uzunlugu (X ekseni)
    p_u1=iso_pt(0,0,-0.3,iso_ox,iso_oy,s); p_u2=iso_pt(U,0,-0.3,iso_ox,iso_oy,s)
    draw.line([p_u1,p_u2],fill=W2,width=1)
    draw.text(((p_u1[0]+p_u2[0])//2,(p_u1[1]+p_u2[1])//2-8),f"{U}m",fill=W2,font=fsm,anchor='mb')
    # Depo genisligi (Y ekseni)
    p_g1=iso_pt(0,0,-0.3,iso_ox,iso_oy,s); p_g2=iso_pt(0,G,-0.3,iso_ox,iso_oy,s)
    draw.line([p_g1,p_g2],fill=W2,width=1)
    draw.text(((p_g1[0]+p_g2[0])//2-8,(p_g1[1]+p_g2[1])//2),f"{G}m",fill=W2,font=fsm,anchor='rm')
    # Raf yuksekligi (Z ekseni)
    p_z1=iso_pt(0,0,0,iso_ox,iso_oy,s); p_z2=iso_pt(0,0,ry_h,iso_ox,iso_oy,s)
    draw.line([p_z1,p_z2],fill=SA,width=1)
    draw.text((p_z2[0]-5,p_z2[1]),f"{ry_h}m",fill=SA,font=fsm,anchor='rb')
    # Koridor
    kor_lbl_pt=iso_pt(U/2,ybo+kor/2,0.1,iso_ox,iso_oy,s)
    draw.text(kor_lbl_pt,f"Kor:{kor}m",fill=MO,font=fxs,anchor='mm')
    # Palet genisligi
    pg_lbl_pt=iso_pt(kb2v+DR/2,ybo+pg/2,ry_h+0.1,iso_ox,iso_oy,s)
    draw.text(pg_lbl_pt,f"{pg}m",fill=TU,font=fxs,anchor='mm')

    # RAFLARI CIZ
    ef_x=sec['ef_x']; ef_y=sec['ef_y']
    blok=DR*2+kor
    y_off=kb2v+ybo

    if tip=='I_MAKS':
        blok_sayisi=sec['ib']
        toplam_w=blok_sayisi*blok
        x_start=kb2v+ef_x-toplam_w
        if x_start<kb2v: x_start=kb2v

        for b in range(blok_sayisi):
            bx=x_start+b*blok
            # Sol raf
            ry_pos=y_off
            while ry_pos+pg<=kb2v+ef_y:
                draw_raf(draw,bx,ry_pos,0,DR,pg,ry_h,kat,s,iso_ox,iso_oy)
                ry_pos+=pg
            # Sag raf
            bx2=bx+DR+kor
            ry_pos=y_off
            while ry_pos+pg<=kb2v+ef_y:
                draw_raf(draw,bx2,ry_pos,0,DR,pg,ry_h,kat,s,iso_ox,iso_oy)
                ry_pos+=pg

    elif tip=='U_MAKS':
        # Sol duvar (x=kb2v)
        ry_pos=y_off
        while ry_pos+pg<=kb2v+ef_y:
            draw_raf(draw,kb2v,ry_pos,0,DR,pg,ry_h,kat,s,iso_ox,iso_oy)
            ry_pos+=pg
        # Sag duvar
        ry_pos=y_off
        while ry_pos+pg<=kb2v+ef_y:
            draw_raf(draw,kb2v+ef_x-DR,ry_pos,0,DR,pg,ry_h,kat,s,iso_ox,iso_oy)
            ry_pos+=pg
        # Arka duvar (kapiya paralel - pg X yonunde, DR Y yonunde)
        ax=kb2v+DR+kor
        while ax+pg<=kb2v+ef_x-DR-kor:
            draw_raf(draw,ax,kb2v+ef_y-DR,0,pg,DR,ry_h,kat,s,iso_ox,iso_oy)
            ax+=pg
        # Orta bloklar
        ob=sec['ob']
        ox1=kb2v+DR+kor; ox2=kb2v+ef_x-DR-kor
        if ob>0:
            toplam_orta=ob*blok
            ox_s=ox2-toplam_orta
            if ox_s<ox1: ox_s=ox1
            for b in range(ob):
                bx=ox_s+b*blok
                ry_pos=y_off+DR+kor
                while ry_pos+pg<=kb2v+ef_y:
                    draw_raf(draw,bx,ry_pos,0,DR,pg,ry_h,kat,s,iso_ox,iso_oy)
                    draw_raf(draw,bx+DR+kor,ry_pos,0,DR,pg,ry_h,kat,s,iso_ox,iso_oy)
                    ry_pos+=pg

    # Kat sayisi etiketi
    kat_pt=iso_pt(kb2v,y_off,ry_h+0.2,iso_ox,iso_oy,s)
    draw.text(kat_pt,f"{kat} KAT" if lg=='tr' else f"{kat} ЯР.",fill=SA,font=fb,anchor='mm')

    # ALT BILGI
    iy=H-INFO_H
    draw.rectangle([0,iy,W,H],fill='#161b22')
    draw.line([0,iy,W,iy],fill='#404060',width=2)

    dk=sec['toplam']*4; yatay_adet=sec['toplam']*2
    dk_metre=round(dk*ry_h,1); kap=sec['toplam']*kat*d['palet']
    sep='#303050'; c1=20; c2=W//3+15; c3=W*2//3+15

    # SUTUN 1: MALZEME
    lx=c1; ly=iy+16
    if lg=='tr':
        draw.text((lx,ly),"MALZEME LISTESI",fill=SA,font=fb); ly+=24
        for lbl,clr,val in [
            ("Dikme:",MA,f"1={ry_h}m | {dk} adet | Top:{dk_metre}m"),
            ("Derinlik:",GR,"1 adet = 1.10m (sabit)"),
            ("Yatay Bag.:",TU,f"{yatay_adet} adet | {pg}m"),
            ("Yukleme:",YE,f"{yen}x{ybo}m = {ym2}m2"),
            ("Koridor:",MO,f"{kor}m | Kapi:{gg}m | Kat:{kat}"),
        ]:
            draw.text((lx,ly),lbl,fill=clr,font=fb)
            draw.text((lx+120,ly),val,fill=W2,font=fn); ly+=22
    else:
        draw.text((lx,ly),"MATERIALY",fill=SA,font=fb); ly+=24
        for lbl,clr,val in [
            ("Stoyka:",MA,f"1={ry_h}m | {dk} sht | It:{dk_metre}m"),
            ("Glubina:",GR,"1 sht = 1.10m (fiks.)"),
            ("Gorizont.:",TU,f"{yatay_adet} sht | {pg}m"),
            ("Zona:",YE,f"{yen}x{ybo}m = {ym2}m2"),
            ("Prokhod:",MO,f"{kor}m | Vor:{gg}m | Yar:{kat}"),
        ]:
            draw.text((lx,ly),lbl,fill=clr,font=fb)
            draw.text((lx+120,ly),val,fill=W2,font=fn); ly+=22

    draw.line([c2-12,iy+12,c2-12,H-12],fill=sep,width=1)

    # SUTUN 2: VERIM
    lx=c2; ly=iy+16
    if lg=='tr':
        draw.text((lx,ly),"VERIM ANALIZI",fill=SA,font=fb); ly+=24
        for k,v in [("Toplam Raf",str(sec['toplam'])),("Palet Kap.",f"{kap} palet"),
                    ("Raf Alani",f"{sec['raf_alani']} m2"),("Kat",str(kat)),("Raf Yuk.",f"{ry_h}m")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+170,ly),v,fill=W2,font=fb); ly+=22
    else:
        draw.text((lx,ly),"ANALIZ KPD",fill=SA,font=fb); ly+=24
        for k,v in [("Stellazhey",str(sec['toplam'])),("Emkost",f"{kap} pall."),
                    ("Pl.stell.",f"{sec['raf_alani']} m2"),("Yarusov",str(kat)),("Vysota",f"{ry_h}m")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+170,ly),v,fill=W2,font=fb); ly+=22

    draw.line([c3-12,iy+12,c3-12,H-12],fill=sep,width=1)

    # SUTUN 3: DEPO VERIMI
    lx=c3; ly=iy+16
    bos=round(sec['depo_alani']-sec['raf_alani']-ym2,1)
    if lg=='tr':
        draw.text((lx,ly),"DEPO VERIMI",fill=SA,font=fb); ly+=24
        for k,v,c in [("Depo Alani",f"{sec['depo_alani']} m2",W2),
                      ("Raf Alani",f"{sec['raf_alani']} m2",W2),
                      ("Yukleme",f"{ym2} m2",YE),
                      ("Bos Alan",f"{bos} m2",AG),
                      ("VERIM",f"%{sec['verim']}",SA)]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+170,ly),v,fill=c,font=fb if k=="VERIM" else fn); ly+=22
    else:
        draw.text((lx,ly),"KPD SKLADA",fill=SA,font=fb); ly+=24
        for k,v,c in [("Pl.sklada",f"{sec['depo_alani']} m2",W2),
                      ("Pl.stell.",f"{sec['raf_alani']} m2",W2),
                      ("Zona",f"{ym2} m2",YE),
                      ("Svobodna",f"{bos} m2",AG),
                      ("KPD",f"{sec['verim']}%",SA)]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
            draw.text((lx+170,ly),v,fill=c,font=fb if k=="KPD" else fn); ly+=22

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
    context.user_data['lang']='ru' if "Russkiy" in update.message.text else 'tr'
    lg=glang(context)
    await update.message.reply_text(
        "📏 Depo uzunlugu (m):\nOrnek: 20" if lg=='tr' else "📏 Dlina sklada (m):\nPrimer: 20",
        reply_markup=ReplyKeyboardRemove())
    return UZUNLUK

async def uzunluk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['uzunluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "📐 Depo genisligi (m):\nOrnek: 12" if lg=='tr' else "📐 Shirina sklada (m):\nPrimer: 12")
        return GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Tolko tsifry.")
        return UZUNLUK

async def genislik_h(update,context):
    lg=glang(context)
    try:
        context.user_data['genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "🚪 Kapinin konumu?" if lg=='tr' else "🚪 Polozhenie vkhoda?",
            reply_markup=kb([["Sol yakin" if lg=='tr' else "Levee",
                              "Orta" if lg=='tr' else "Po tsentru",
                              "Sag yakin" if lg=='tr' else "Pravee"]]))
        return GIRIS_KONUM
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Tolko tsifry.")
        return GENISLIK

async def giris_konum_h(update,context):
    lg=glang(context)
    t=update.message.text.lower()
    if "orta" in t or "tsentru" in t or "центру" in t:
        context.user_data['giris_konum']='orta'; context.user_data['giris_mesafe']=0.0
        await update.message.reply_text(
            "🚪 Kapi genisligi (m):\nOrnek: 4" if lg=='tr' else "🚪 Shirina vorot (m):\nPrimer: 4",
            reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    elif "sol" in t or "levee" in t or "левее" in t: context.user_data['giris_konum']='sol'
    else: context.user_data['giris_konum']='sag'
    await update.message.reply_text(
        "🚪 Koseden kac metre?\nOrnek: 2" if lg=='tr' else "🚪 Rasstoyaniye ot ugla (m)?\nPrimer: 2",
        reply_markup=ReplyKeyboardRemove())
    return GIRIS_MESAFE

async def giris_mesafe_h(update,context):
    lg=glang(context)
    try:
        context.user_data['giris_mesafe']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "🚪 Kapi genisligi (m):\nOrnek: 4" if lg=='tr' else "🚪 Shirina vorot (m):\nPrimer: 4",
            reply_markup=kb([["3","4","5","6"]]))
        return GIRIS_GENISLIK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Tolko tsifry.")
        return GIRIS_MESAFE

async def giris_genislik_h(update,context):
    lg=glang(context)
    try:
        context.user_data['giris_genislik']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "📐 Yukleme alani EN (m):\nOrnek: 8" if lg=='tr' else "📐 Zona pogruzki SHIRINA (m):\nPrimer: 8",
            reply_markup=kb([["4","6","8","10","12"]]))
        return YUK_EN
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Tolko tsifry.")
        return GIRIS_GENISLIK

async def yuk_en_h(update,context):
    lg=glang(context)
    try:
        context.user_data['yuk_en']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "📐 Yukleme alani BOY (m):\nOrnek: 5" if lg=='tr' else "📐 Zona pogruzki GLUBINA (m):\nPrimer: 5",
            reply_markup=kb([["3","4","5","6","8"]]))
        return YUK_BOY
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Tolko tsifry.")
        return YUK_EN

async def yuk_boy_h(update,context):
    lg=glang(context)
    try:
        context.user_data['yuk_boy']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "📐 Raf-duvar arasi bosluk?\n0=bitisik" if lg=='tr' else "📐 Otstup ot sten?\n0=vplotnutyu",
            reply_markup=kb([["0","0.3","0.5"]]))
        return KENAR_BOSLUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Tolko tsifry.")
        return YUK_BOY

async def kenar_bosluk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['kenar_bosluk']=float(update.message.text.replace(',','.'))
        await update.message.reply_text(
            "🚦 Koridor tipi?\nForklift 3m | Transpalet 2m | El 1.2m" if lg=='tr' else
            "🚦 Tip prokhoda?\nPogruzchik 3m | Transpalet 2m | Ruchnoy 1.2m",
            reply_markup=kb([["Forklift","Transpalet","El ile" if lg=='tr' else "Ruchnoy"]]))
        return KORIDOR_TIPI
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Tolko tsifry.")
        return KENAR_BOSLUK

async def koridor_h(update,context):
    lg=glang(context)
    t=update.message.text.lower()
    if "forklift" in t or "pogruz" in t: context.user_data['koridor_tipi']='forklift'
    elif "transpalet" in t: context.user_data['koridor_tipi']='transpalet'
    else: context.user_data['koridor_tipi']='el'
    await update.message.reply_text(
        "📦 Raf basina palet?\n1=0.95m  2=1.85m\n3=2.70m  4=3.60m" if lg=='tr' else
        "📦 Pallet na ryad?\n1=0.95m  2=1.85m\n3=2.70m  4=3.60m",
        reply_markup=kb([["1","2"],["3","4"]]))
    return PALET

async def palet_h(update,context):
    lg=glang(context)
    try:
        v=int(update.message.text.strip()[0])
        if v not in [1,2,3,4]: raise ValueError
        context.user_data['palet']=v
        await update.message.reply_text(
            "🏗 Kat sayisi?\nOrnek: 3" if lg=='tr' else "🏗 Kolichestvo yarusov?\nPrimer: 3",
            reply_markup=ReplyKeyboardRemove())
        return KAT
    except:
        await update.message.reply_text("1-4 girin." if lg=='tr' else "Vvedite 1-4.")
        return PALET

async def kat_h(update,context):
    lg=glang(context)
    try:
        context.user_data['kat']=int(update.message.text)
        await update.message.reply_text(
            "📏 Raf yuksekligi (m)?\nOrnek: 5" if lg=='tr' else "📏 Vysota stellazha (m)?\nPrimer: 5")
        return RAF_YUK
    except:
        await update.message.reply_text("Sadece rakam." if lg=='tr' else "Tolko tsifry.")
        return KAT

async def raf_yuk_h(update,context):
    lg=glang(context)
    try:
        context.user_data['raf_yuk']=float(update.message.text.replace(',','.'))
        d=context.user_data
        layouts=hesapla(d)
        await update.message.reply_text(
            "⏳ 2 izometrik cizim hazirlaniyor..." if lg=='tr' else "⏳ Gotoviyu 2 izometricheskikh chertezha...",
            reply_markup=ReplyKeyboardRemove())
        secs=[layouts['U_MAKS'],layouts['I_MAKS']]
        secs.sort(key=lambda x:x['toplam'],reverse=True)
        for i,sec in enumerate(secs):
            resim=ciz_iso(d,lg,sec,i+1)
            tn={'U_MAKS':'U-MAKS','I_MAKS':'I-MAKS'}.get(sec['tip'],sec['tip'])
            kap=sec['toplam']*d['kat']*d['palet']
            if lg=='tr':
                cap=(f"{'STAR EN IYI — ' if i==0 else ''}{i+1}. {tn}\n"
                     f"Raf:{sec['toplam']} | Kap:{kap} palet | Verim:%{sec['verim']}")
            else:
                cap=(f"{'LUCHSHIY — ' if i==0 else ''}{i+1}. {tn}\n"
                     f"Stell:{sec['toplam']} | Emk:{kap} | KPD:{sec['verim']}%")
            await update.message.reply_photo(photo=resim,caption=cap)
        await update.message.reply_text("Hazir! /hesapla" if lg=='tr' else "Gotovo! /raschet")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return RAF_YUK

async def iptal(update,context):
    lg=glang(context)
    await update.message.reply_text("Iptal. /hesapla" if lg=='tr' else "Otmeneno. /raschet",
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
