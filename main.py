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
    sizes = [18, 15, 13, 12, 11, 13]
    bolds = [True, True, False, False, False, True]
    paths_b = [
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    paths_n = [
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    fonts = []
    for size, bold in zip(sizes, bolds):
        paths = paths_b if bold else paths_n
        f = None
        for p in paths:
            try: f = ImageFont.truetype(p, size); break
            except: pass
        fonts.append(f or ImageFont.load_default())
    return fonts  # ft, fb, fn, fsm, fxs, fti

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

# ═══════════════════════════════════════════
# İZOMETRİK ÇİZİM
# ═══════════════════════════════════════════

def iso(x, y, z, ox, oy, s=40):
    """3D -> 2D izometrik projeksiyon."""
    ix = ox + (x - y) * s * math.cos(math.radians(30))
    iy = oy - z * s + (x + y) * s * math.sin(math.radians(30))
    return (int(ix), int(iy))

def draw_box(draw, x, y, z, w, d, h, s, ox, oy,
             top_c, left_c, right_c, outline_c):
    """İzometrik kutu çiz. w=X, d=Y, h=Z."""
    # 8 köşe
    p000 = iso(x,   y,   z,   ox, oy, s)
    p100 = iso(x+w, y,   z,   ox, oy, s)
    p010 = iso(x,   y+d, z,   ox, oy, s)
    p110 = iso(x+w, y+d, z,   ox, oy, s)
    p001 = iso(x,   y,   z+h, ox, oy, s)
    p101 = iso(x+w, y,   z+h, ox, oy, s)
    p011 = iso(x,   y+d, z+h, ox, oy, s)
    p111 = iso(x+w, y+d, z+h, ox, oy, s)

    # Ust yuz
    draw.polygon([p001, p101, p111, p011], fill=top_c, outline=outline_c)
    # Sol yuz (y+ taraf)
    draw.polygon([p010, p110, p111, p011], fill=left_c, outline=outline_c)
    # Sag yuz (x+ taraf)
    draw.polygon([p100, p110, p111, p101], fill=right_c, outline=outline_c)

def draw_raf_iso(draw, rx, ry, rz, rw, rd, rh, kat, s, ox, oy, pg_renk):
    """Raf birimini izometrik olarak ciz."""
    # Alt cerceve (dikme)
    draw_box(draw, rx, ry, rz, rw, rd, 0.05, s, ox, oy,
             '#1a3a1a', '#0d2a0d', '#0a1f0a', '#2a5a2a')
    # Ust cerceve
    draw_box(draw, rx, ry, rz+rh-0.05, rw, rd, 0.05, s, ox, oy,
             '#1a3a1a', '#0d2a0d', '#0a1f0a', '#2a5a2a')
    # Dikmeler (4 kose)
    dik_w = 0.05
    for dx, dy in [(0,0),(rw-dik_w,0),(0,rd-dik_w),(rw-dik_w,rd-dik_w)]:
        draw_box(draw, rx+dx, ry+dy, rz, dik_w, dik_w, rh, s, ox, oy,
                 '#2a5a2a', '#1a3a1a', '#152e15', '#4a9eff')
    # Yatay baglantilar (her kat icin)
    for k in range(kat):
        kz = rz + (k+1) * rh / (kat+1)
        # On yatay baglanti (y=ry taraf)
        draw_box(draw, rx, ry, kz, rw, 0.04, 0.04, s, ox, oy,
                 pg_renk, pg_renk, pg_renk, '#000000')
        # Arka yatay baglanti
        draw_box(draw, rx, ry+rd-0.04, kz, rw, 0.04, 0.04, s, ox, oy,
                 pg_renk, pg_renk, pg_renk, '#000000')

def oy_label(draw, x1, x2, y, t, f, c):
    draw.line([x1,y,x2,y],fill=c,width=1)
    draw.line([x1,y-4,x1,y+4],fill=c,width=2)
    draw.line([x2,y-4,x2,y+4],fill=c,width=2)
    draw.text(((x1+x2)//2,y-5),t,fill=c,font=f,anchor='mb')

def od_label(draw, x, y1, y2, t, f, c):
    draw.line([x,y1,x,y2],fill=c,width=1)
    draw.line([x-4,y1,x+4,y1],fill=c,width=2)
    draw.line([x-4,y2,x+4,y2],fill=c,width=2)
    draw.text((x+5,(y1+y2)//2),t,fill=c,font=f,anchor='lm')

def ciz_iso(d, lg, sec, sira):
    U=d['uzunluk']; G=d['genislik']
    pg=PALET_G[d['palet']]; kor=KORIDOR_G[d['koridor_tipi']]
    kb2=d.get('kenar_bosluk',0.0)
    gk=d.get('giris_konum','orta'); gm=d.get('giris_mesafe',0.0)
    gg=d.get('giris_genislik',4.0)
    kat=d['kat']; ry_yuk=d['raf_yuk']
    tip=sec['tip']
    yen=sec['yuk_en']; ybo=sec['yuk_boy']; ym2=sec['yuk_m2']
    kb2v=d.get('kenar_bosluk',0.0)

    ft,fb,fn,fsm,fxs,fti = get_fonts()

    W,H=1400,1050
    img=Image.new('RGB',(W,H),'#0a0f1a')
    draw=ImageDraw.Draw(img)

    W2='#e8e8e8'; AG='#606080'; SA='#ffd700'; SI='#00b4d8'
    MO='#c084fc'; YE='#22c55e'; TU='#ff8c42'; GR='#4ade80'; MA='#4a9eff'
    INFO_H=210

    # İzometrik parametreler
    s = min(28, int(700/(U+G)))  # scale
    s = max(s, 12)
    raf_h = ry_yuk  # raf yuksekligi (Z)

    # Izometrik merkez noktasi
    iso_ox = W//2
    iso_oy = 420

    # BASLIK
    draw.rectangle([0,0,W,44],fill='#161b22')
    tad={'U_MAKS':('U-MAKS: Duvar+Orta','U-МАКС: Стены+Центр'),
         'I_MAKS':('I-MAKS: Sirt Sirta','I-МАКС: Спина к спине')}
    tn=tad.get(tip,(tip,tip))[1 if lg=='ru' else 0]
    bl=(f"İZOMETRİK  |  SECENEK {sira}/2  |  {tn}  |  {sec['toplam']} raf  |  Verim:%{sec['verim']}" if lg=='tr'
        else f"ИЗОМЕТРИЯ  |  ВАРИАНТ {sira}/2  |  {tn}  |  {sec['toplam']} стелл.  |  КПД:{sec['verim']}%")
    draw.text((W//2,22),bl,fill=SA,font=ft,anchor='mm')

    # DEPO TABANI (izometrik)
    dep_top  = (0.15,'#1a2a1a')
    dep_left = (0.15,'#162316')
    dep_right= (0.15,'#121e12')

    # Depo duvarlari (ince)
    draw_box(draw, 0, 0, 0, U, G, 0.1, s, iso_ox, iso_oy,
             '#0d1f0d', '#0a1a0a', '#081508', '#00b4d8')

    # Zemin
    p1=iso(0,0,0,iso_ox,iso_oy,s)
    p2=iso(U,0,0,iso_ox,iso_oy,s)
    p3=iso(U,G,0,iso_ox,iso_oy,s)
    p4=iso(0,G,0,iso_ox,iso_oy,s)
    draw.polygon([p1,p2,p3,p4],fill='#0d1520',outline='#00b4d8')

    # Duvarlar
    # Arka duvar (y=G)
    pw1=iso(0,G,0,iso_ox,iso_oy,s); pw2=iso(U,G,0,iso_ox,iso_oy,s)
    pw3=iso(U,G,raf_h*0.3,iso_ox,iso_oy,s); pw4=iso(0,G,raf_h*0.3,iso_ox,iso_oy,s)
    draw.polygon([pw1,pw2,pw3,pw4],fill='#0d1a0d',outline='#1a3a1a')
    # Sol duvar (x=0)
    ps1=iso(0,0,0,iso_ox,iso_oy,s); ps2=iso(0,G,0,iso_ox,iso_oy,s)
    ps3=iso(0,G,raf_h*0.3,iso_ox,iso_oy,s); ps4=iso(0,0,raf_h*0.3,iso_ox,iso_oy,s)
    draw.polygon([ps1,ps2,ps3,ps4],fill='#0a1508',outline='#1a3a1a')

    # YÜKLEME ALANI (zemin uzerinde, kapi tarafinda Y=0)
    if gk=='orta': gx_m=U/2
    elif gk=='sol': gx_m=gm+gg/2
    else: gx_m=U-gm-gg/2
    yuk_x1=max(0, gx_m-yen/2); yuk_x2=min(U, gx_m+yen/2)

    zy1=iso(yuk_x1,0,0.02,iso_ox,iso_oy,s)
    zy2=iso(yuk_x2,0,0.02,iso_ox,iso_oy,s)
    zy3=iso(yuk_x2,ybo,0.02,iso_ox,iso_oy,s)
    zy4=iso(yuk_x1,ybo,0.02,iso_ox,iso_oy,s)
    draw.polygon([zy1,zy2,zy3,zy4],fill='#031a0d',outline=YE)
    # Yukleme label
    zm=iso((yuk_x1+yuk_x2)/2, ybo/2, 0.1, iso_ox, iso_oy, s)
    draw.text(zm,f"{ym2}m²",fill=YE,font=fxs,anchor='mm')

    # KAPI
    kp1=iso(gx_m-gg/2,0,0,iso_ox,iso_oy,s)
    kp2=iso(gx_m+gg/2,0,0,iso_ox,iso_oy,s)
    kp3=iso(gx_m+gg/2,0,raf_h*0.25,iso_ox,iso_oy,s)
    kp4=iso(gx_m-gg/2,0,raf_h*0.25,iso_ox,iso_oy,s)
    draw.polygon([kp1,kp2,kp3,kp4],fill='#1a2a10',outline=SA)
    kpm=iso(gx_m,0,raf_h*0.12,iso_ox,iso_oy,s)
    draw.text(kpm,"G/C" if lg=='tr' else "В/В",fill=SA,font=fxs,anchor='mm')

    # RAFLARI CIZ
    ef_x=sec['ef_x']; ef_y=sec['ef_y']
    blok=DR*2+kor
    dr_m=DR; pg_m=pg; kor_m=kor

    # Raf renkleri
    TU_TOP=(80,60,20); TU_LEFT=(60,40,10); TU_RIGHT=(50,30,5)
    GR_TOP=(20,80,40); GR_LEFT=(10,60,25); GR_RIGHT=(5,50,20)

    x_off=kb2v; y_off=kb2v+ybo  # yükleme alanindan sonra basla

    if tip=='I_MAKS':
        blok_sayisi=sec['ib']
        # Bloklari X yonunde, sag duvara yapis
        toplam_w = blok_sayisi * blok
        x_start = kb2v + ef_x - toplam_w + (blok_sayisi-1)*0.1
        if x_start < kb2v: x_start = kb2v

        for b in range(blok_sayisi):
            bx = x_start + b*(blok+0.1)
            # Sol raf
            rx=bx; ry_pos=y_off
            while ry_pos+pg_m <= kb2v+ef_y:
                draw_raf_iso(draw, rx, ry_pos, 0, dr_m, pg_m, raf_h, kat, s, iso_ox, iso_oy,
                             '#ff8c42')
                ry_pos+=pg_m
            # Sag raf
            rx2=bx+dr_m+kor_m
            ry_pos=y_off
            while ry_pos+pg_m <= kb2v+ef_y:
                draw_raf_iso(draw, rx2, ry_pos, 0, dr_m, pg_m, raf_h, kat, s, iso_ox, iso_oy,
                             '#ff8c42')
                ry_pos+=pg_m

    elif tip=='U_MAKS':
        # Sol duvar (x=kb2v)
        ry_pos=y_off
        while ry_pos+pg_m <= kb2v+ef_y:
            draw_raf_iso(draw, kb2v, ry_pos, 0, dr_m, pg_m, raf_h, kat, s, iso_ox, iso_oy,
                         '#ff8c42')
            ry_pos+=pg_m

        # Sag duvar (x=kb2v+ef_x-dr_m)
        ry_pos=y_off
        while ry_pos+pg_m <= kb2v+ef_y:
            draw_raf_iso(draw, kb2v+ef_x-dr_m, ry_pos, 0, dr_m, pg_m, raf_h, kat, s, iso_ox, iso_oy,
                         '#ff8c42')
            ry_pos+=pg_m

        # Arka duvar (y=kb2v+ef_y-dr_m)
        # Arka duvar: kapiya paralel (pg X yonunde)
        ax_pos=kb2v+dr_m+kor_m
        while ax_pos+pg_m <= kb2v+ef_x-dr_m-kor_m:
            draw_raf_iso(draw, ax_pos, kb2v+ef_y-dr_m, 0, pg_m, dr_m, raf_h, kat, s, iso_ox, iso_oy,
                         '#4ade80')
            ax_pos+=pg_m

        # Orta bloklar
        ic_x=ef_x-DR*2-kor*2
        ob=max(0,int(ic_x/blok))
        orta_x1=kb2v+dr_m+kor_m
        orta_x2=kb2v+ef_x-dr_m-kor_m
        toplam_orta=ob*blok
        ox_start=orta_x2-toplam_orta
        if ox_start<orta_x1: ox_start=orta_x1
        for b in range(ob):
            bx=ox_start+b*blok
            ry_pos=y_off+DR+kor_m
            while ry_pos+pg_m <= kb2v+ef_y:
                draw_raf_iso(draw, bx, ry_pos, 0, dr_m, pg_m, raf_h, kat, s, iso_ox, iso_oy,
                             '#ff8c42')
                draw_raf_iso(draw, bx+dr_m+kor_m, ry_pos, 0, dr_m, pg_m, raf_h, kat, s, iso_ox, iso_oy,
                             '#ff8c42')
                ry_pos+=pg_m

    # ALT BILGI
    iy=H-INFO_H
    draw.rectangle([0,iy,W,H],fill='#161b22')
    draw.line([0,iy,W,iy],fill='#404060',width=2)

    dk=sec['toplam']*4
    yatay_adet=sec['toplam']*2
    dk_metre=round(dk*ry_yuk,1)
    kap=sec['toplam']*kat*d['palet']
    sep='#303050'; c1=20; c2=W//3+15; c3=W*2//3+15

    def satir(lx,ly,lbl,clr,val,vclr=None):
        draw.text((lx,ly),lbl,fill=clr,font=fb)
        draw.text((lx+115,ly),val,fill=vclr or W2,font=fn)
        return ly+22

    lx=c1; ly=iy+16
    draw.text((lx,ly),"MALZEME LİSTESİ" if lg=='tr' else "СПИСОК МАТЕРИАЛОВ",fill=SA,font=fb); ly+=24
    if lg=='tr':
        ly=satir(lx,ly,"● Dikme:",MA,f"1={ry_yuk}m | {dk} adet | Top:{dk_metre}m")
        ly=satir(lx,ly,"━ Derinlik:",GR,"1 adet = 1.10m (sabit)")
        ly=satir(lx,ly,"| Yatay Bag.:",TU,f"{yatay_adet} adet | {pg}m")
        ly=satir(lx,ly,"▦ Yukleme:",YE,f"{yen}x{ybo}m = {ym2}m²",YE)
        ly=satir(lx,ly,"↔ Koridor:",MO,f"{kor}m | Kapi:{gg}m | Kat:{kat}")
    else:
        ly=satir(lx,ly,"● Стойка:",MA,f"1={ry_yuk}м | {dk} шт | Ит:{dk_metre}м")
        ly=satir(lx,ly,"━ Глубина:",GR,"1 шт = 1.10м (фикс.)")
        ly=satir(lx,ly,"| Гориз.балка:",TU,f"{yatay_adet} шт | {pg}м")
        ly=satir(lx,ly,"▦ Зона:",YE,f"{yen}x{ybo}м = {ym2}м²",YE)
        ly=satir(lx,ly,"↔ Проход:",MO,f"{kor}м | Вор:{gg}м | Яр:{kat}")

    draw.line([c2-12,iy+12,c2-12,H-12],fill=sep,width=1)
    lx=c2; ly=iy+16
    draw.text((lx,ly),"VERİM ANALİZİ" if lg=='tr' else "АНАЛИЗ КПД",fill=SA,font=fb); ly+=24
    if lg=='tr':
        for k,v in [("Toplam Raf",str(sec['toplam'])),("Palet Kap.",f"{kap} palet"),
                    ("Raf Alani",f"{sec['raf_alani']} m²"),("Kat",str(kat)),("Raf Yuk.",f"{ry_yuk}m")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn); draw.text((lx+165,ly),v,fill=W2,font=fb); ly+=22
    else:
        for k,v in [("Стеллажей",str(sec['toplam'])),("Ёмкость",f"{kap} палл."),
                    ("Пл.стелл.",f"{sec['raf_alani']} м²"),("Ярусов",str(kat)),("Высота",f"{ry_yuk}м")]:
            draw.text((lx,ly),f"{k}:",fill=AG,font=fn); draw.text((lx+165,ly),v,fill=W2,font=fb); ly+=22

    draw.line([c3-12,iy+12,c3-12,H-12],fill=sep,width=1)
    lx=c3; ly=iy+16
    draw.text((lx,ly),"DEPO VERİMİ" if lg=='tr' else "КПД СКЛАДА",fill=SA,font=fb); ly+=24
    bos=round(sec['depo_alani']-sec['raf_alani']-ym2,1)
    items_tr=[("Depo Alani",f"{sec['depo_alani']} m²",W2),("Raf Alani",f"{sec['raf_alani']} m²",W2),
              ("Yukleme",f"{ym2} m²",YE),("Bos Alan",f"{bos} m²",AG),("VERİM",f"%{sec['verim']}",SA)]
    items_ru=[("Пл.склада",f"{sec['depo_alani']} м²",W2),("Пл.стелл.",f"{sec['raf_alani']} м²",W2),
              ("Зона",f"{ym2} м²",YE),("Своб.",f"{bos} м²",AG),("КПД",f"{sec['verim']}%",SA)]
    for k,v,c in (items_ru if lg=='ru' else items_tr):
        draw.text((lx,ly),f"{k}:",fill=AG,font=fn)
        draw.text((lx+165,ly),v,fill=c,font=fb if k in ("VERİM","КПД") else fn); ly+=22

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
            "⏳ 2 izometrik cizim hazirlaniyor..." if lg=='tr' else "⏳ Готовлю 2 изометрических чертежа...",
            reply_markup=ReplyKeyboardRemove())
        secs=[layouts['U_MAKS'],layouts['I_MAKS']]
        secs.sort(key=lambda x:x['toplam'],reverse=True)
        for i,sec in enumerate(secs):
            resim=ciz_iso(d,lg,sec,i+1)
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
