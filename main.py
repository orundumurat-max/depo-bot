<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Depo Raf Yerleşim Planı</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<style>
*{box-sizing:border-box;}
body{margin:0;background:#e9edf2;font-family:Arial,Helvetica,sans-serif;color:#1f2937;}
.app{max-width:760px;margin:auto;padding:12px;}
.header{background:#111827;color:white;padding:14px 16px;border-radius:8px 8px 0 0;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;}
.header h1{margin:0;font-size:17px;}
.header p{margin:4px 0 0;color:#cbd5e1;font-size:11px;}
.langBox select{height:32px;border-radius:4px;border:1px solid #475569;background:#1f2937;color:white;padding:0 6px;font-size:12px;}
.panel{background:white;border:1px solid #cbd5e1;padding:12px;display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.field{display:flex;flex-direction:column;gap:4px;min-width:0;}
.field label{font-size:10px;font-weight:bold;color:#475569;text-transform:uppercase;}
.field input,.field select{height:36px;border:1px solid #94a3b8;border-radius:4px;padding:0 8px;font-size:13px;background:white;width:100%;min-width:0;}
.field .row2{display:flex;gap:6px;}
.actions{background:#f8fafc;border:1px solid #cbd5e1;border-top:0;padding:10px;display:flex;flex-wrap:wrap;gap:8px;}
button{border:0;border-radius:6px;padding:10px 14px;font-weight:bold;cursor:pointer;font-size:13px;flex:1;min-width:110px;}
.btn-main{background:#111827;color:white;}
.btn-pdf{background:#b91c1c;color:white;}
.btn-share{background:#334155;color:white;}
button:hover{opacity:.88;}
.status{margin-top:8px;padding:10px 12px;background:#f1f5f9;border-left:4px solid #f97316;font-size:12.5px;line-height:1.5;}
.drawingWrap{margin-top:10px;background:white;border:1px solid #94a3b8;padding:8px;}
svg{display:block;width:100%;height:auto;background:#fff;}
.legend{margin-top:8px;background:white;border:1px solid #cbd5e1;padding:10px;display:flex;flex-wrap:wrap;gap:12px;font-size:11px;}
.legendItem{display:flex;align-items:center;gap:5px;}
.legendLine{width:26px;height:4px;flex-shrink:0;}
.costSection{margin-top:10px;background:white;border:1px solid #cbd5e1;border-radius:8px;padding:12px;}
.costSection h3{margin:0 0 10px;font-size:14px;}
.costRow{border-bottom:1px solid #e2e8f0;padding:8px 0;}
.costRow:last-child{border-bottom:0;}
.costLabel{font-size:12px;font-weight:bold;color:#334155;margin-bottom:6px;}
.costFields{display:flex;gap:6px;flex-wrap:wrap;}
.miniField{flex:1;min-width:64px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:4px 4px;text-align:center;}
.miniField label{display:block;font-size:8.5px;color:#64748b;text-transform:uppercase;}
.miniField input{width:100%;border:0;background:transparent;text-align:center;font-size:12.5px;padding:2px 0;}
.miniField span{font-size:12.5px;font-weight:bold;}
.costFoot{margin-top:8px;background:#f0fdf4;border:1px solid #16a34a;border-radius:6px;padding:8px 10px;display:flex;justify-content:space-between;font-weight:bold;color:#166534;font-size:14px;}
.outputBox{margin-top:10px;background:#f8fafc;border:1px solid #cbd5e1;border-radius:8px;padding:12px;}
.outputBox h3{margin:0 0 8px;font-size:14px;}
.footerNote{margin-top:8px;color:#64748b;font-size:10px;line-height:1.4;}
@media(min-width:520px){.panel{grid-template-columns:repeat(3,1fr);}}
</style>
</head>
<body>
<div class="app">

<div class="header">
    <div><h1 data-i18n="title">DEPO RAF YERLEŞİM PLANI</h1><p data-i18n="subtitle">Teknik yerleşim / kapasite optimizasyonu</p></div>
    <div class="langBox">
        <select id="dilSecim">
            <option value="tr">TR</option><option value="en">EN</option><option value="ru">RU</option>
        </select>
    </div>
</div>

<div class="panel">
    <div class="field"><label data-i18n="depoOlcu">Depo En × Boy (m)</label>
        <div class="row2"><input id="depoEn" type="number" value="39.83" step="0.01"><input id="depoBoy" type="number" value="28.09" step="0.01"></div>
    </div>
    <div class="field"><label data-i18n="yuklemeAlani">Yükleme Alanı En × Boy (m)</label>
        <div class="row2"><input id="yuklemeEn" type="number" value="30" step="0.01"><input id="yuklemeBoy" type="number" value="5" step="0.01"></div>
    </div>
    <div class="field">
        <label data-i18n="yerlesim">Yerleşim</label>
        <select id="yerlesimDuzen">
            <option value="AUTO" data-i18n="auto">Programın Önerdiği</option>
            <option value="I" data-i18n="iTipi">I Tipi</option>
            <option value="U" data-i18n="uTipi">U Tipi</option>
        </select>
    </div>
    <div class="field">
        <label data-i18n="koridor">Araç / Koridor (m)</label>
        <select id="aracTipi">
            <option value="1" data-i18n="elArabasi">El Arabası 1.00m</option>
            <option value="1.5" data-i18n="transpalet">Transpalet 1.50m</option>
            <option value="3.2" selected data-i18n="forklift">Forklift 3.20m</option>
            <option value="4" data-i18n="agirlikliForklift">Ağır Forklift 4.00m</option>
        </select>
    </div>
    <div class="field"><label data-i18n="rafModulu">Raf Modülü (m)</label>
        <select id="paletModul"><option value="1">1.00</option><option value="2.7" selected>2.70</option><option value="3.6">3.60</option><option value="4.5">4.50</option></select>
    </div>
    <div class="field"><label data-i18n="rafDerinligi">Raf Derinliği (m)</label><input id="rafDerinlik" type="number" value="1.10" step="0.01"></div>
    <div class="field"><label data-i18n="katSayisi">Kat Sayısı</label><input id="katSayisi" type="number" value="4" step="1" min="1"></div>
    <div class="field"><label data-i18n="dikmeYuksekligi">Dikme Yüksekliği (m)</label><input id="dikmeYukseklik" type="number" value="6" step="0.1"></div>
</div>

<div class="actions"><button class="btn-main" id="btnHesapla" data-i18n="hesapla">↻ HESAPLA</button></div>

<div class="status" id="statusBox">-</div>

<div id="outputSheet">
<div class="drawingWrap">
<svg id="depoSvg" viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <pattern id="voidPattern" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
            <rect width="9" height="9" fill="#fff5f5"/><line x1="0" y1="0" x2="0" y2="9" stroke="#f3a5a5" stroke-width="1.1"/>
        </pattern>
    </defs>
    <rect x="0" y="0" width="600" height="600" fill="#ffffff"/>
    <text id="svgInfo" x="10" y="16" font-size="10" font-weight="bold" fill="#111827">-</text>
    <g id="planGroup">
        <rect id="warehouse" x="10" y="30" width="580" height="560" fill="#ffffff" stroke="#111827" stroke-width="3.5"/>
        <g id="voidLayer"></g>
        <g id="rackLayer"></g>
        <g id="loadingLayer"></g>
        <g id="labelLayer"></g>
    </g>
</svg>
</div>

<div class="legend">
    <div class="legendItem"><span class="legendLine" style="background:#8fa3bd;border:1px solid #1e293b;"></span><span data-i18n="legendRafTxt">Raf gövdesi</span></div>
    <div class="legendItem"><span class="legendLine" style="background:#f97316;"></span><span data-i18n="legendYanTxt">Yan bağlantı</span></div>
    <div class="legendItem"><span class="legendLine" style="background:#16a34a;"></span><span data-i18n="legendYukTxt">Yükleme / kapı</span></div>
    <div class="legendItem"><span class="legendLine" style="background:#dc2626;"></span><span data-i18n="legendBosTxt">Boşluk</span></div>
</div>

<div class="costSection" id="costSection">
    <h3 data-i18n="malzemeBaslik">Malzeme ve Maliyet</h3>

    <div class="costRow"><div class="costLabel" data-i18n="dikme">Dikme (m)</div>
        <div class="costFields">
            <div class="miniField"><label data-i18n="adet">Adet</label><span id="mDikme">-</span></div>
            <div class="miniField"><label>€</label><input type="number" id="fiyatDikme" value="12"></div>
            <div class="miniField"><label data-i18n="tutar">Tutar</label><span id="tDikme">-</span></div>
        </div>
    </div>
    <div class="costRow"><div class="costLabel" data-i18n="yanBaglanti">Yan Bağlantı</div>
        <div class="costFields">
            <div class="miniField"><label data-i18n="adet">Adet</label><span id="mYan">-</span></div>
            <div class="miniField"><label>€</label><input type="number" id="fiyatYan" value="25"></div>
            <div class="miniField"><label data-i18n="tutar">Tutar</label><span id="tYan">-</span></div>
        </div>
    </div>
    <div class="costRow"><div class="costLabel" data-i18n="ankraj">Ankraj</div>
        <div class="costFields">
            <div class="miniField"><label data-i18n="adet">Adet</label><input type="number" id="ankrajAdet" value="0"></div>
            <div class="miniField"><label>€</label><input type="number" id="fiyatAnkraj" value="1"></div>
            <div class="miniField"><label data-i18n="tutar">Tutar</label><span id="tAnkraj">-</span></div>
        </div>
    </div>
    <div class="costRow"><div class="costLabel" data-i18n="zeminMetal">Zemin Düzeltme Metal</div>
        <div class="costFields">
            <div class="miniField"><label data-i18n="adet">Adet</label><input type="number" id="zeminAdet" value="0"></div>
            <div class="miniField"><label>€</label><input type="number" id="fiyatZemin" value="3"></div>
            <div class="miniField"><label data-i18n="tutar">Tutar</label><span id="tZemin">-</span></div>
        </div>
    </div>
    <div class="costRow"><div class="costLabel" data-i18n="montaj">Montaj</div>
        <div class="costFields">
            <div class="miniField"><label>€</label><input type="number" id="fiyatMontaj" value="500"></div>
            <div class="miniField"><label data-i18n="tutar">Tutar</label><span id="tMontaj">-</span></div>
        </div>
    </div>
    <div class="costRow"><div class="costLabel" data-i18n="transport">Transport</div>
        <div class="costFields">
            <div class="miniField"><label>€</label><input type="number" id="fiyatTransport" value="450"></div>
            <div class="miniField"><label data-i18n="tutar">Tutar</label><span id="tTransport">-</span></div>
        </div>
    </div>

    <div class="costFoot"><span data-i18n="toplam">TOPLAM</span><span id="tToplam">-</span></div>
</div>
</div>

<div class="outputBox">
    <h3 data-i18n="ciktiBaslik">Çıktı</h3>
    <div class="actions" style="border:0;padding:0;background:transparent;">
        <button class="btn-pdf" id="btnPdf" data-i18n="pdf">PDF ÇIKTI</button>
        <button class="btn-share" id="btnWhatsapp" data-i18n="whatsapp">WhatsApp</button>
        <button class="btn-share" id="btnTelegram" data-i18n="telegram">Telegram</button>
        <button class="btn-share" id="btnMail" data-i18n="eposta">E-posta</button>
    </div>
</div>

<div class="footerNote" data-i18n="footNote">Not: Kolon, sprinkler, yangın kaçışları ve yönetmelik şartları ayrıca kontrol edilmelidir.</div>

</div>

<script>
/* ================= DİL ================= */
var LANG = {
tr:{title:"DEPO RAF YERLEŞİM PLANI",subtitle:"Teknik yerleşim / kapasite optimizasyonu",depoOlcu:"Depo En × Boy (m)",
yuklemeAlani:"Yükleme Alanı En × Boy (m)",yerlesim:"Yerleşim",auto:"Programın Önerdiği",iTipi:"I Tipi",uTipi:"U Tipi",
koridor:"Araç / Koridor (m)",elArabasi:"El Arabası 1.00m",transpalet:"Transpalet 1.50m",forklift:"Forklift 3.20m",agirlikliForklift:"Ağır Forklift 4.00m",
rafModulu:"Raf Modülü (m)",rafDerinligi:"Raf Derinliği (m)",katSayisi:"Kat Sayısı",dikmeYuksekligi:"Dikme Yüksekliği (m)",hesapla:"↻ HESAPLA",
malzemeBaslik:"Malzeme ve Maliyet",dikme:"Dikme (m)",yanBaglanti:"Yan Bağlantı",ankraj:"Ankraj",zeminMetal:"Zemin Düzeltme Metal",
montaj:"Montaj",transport:"Transport",toplam:"TOPLAM",adet:"Adet",tutar:"Tutar",ciktiBaslik:"Çıktı",pdf:"PDF ÇIKTI",whatsapp:"WhatsApp",telegram:"Telegram",eposta:"E-posta",
legendRafTxt:"Raf gövdesi",legendYanTxt:"Yan bağlantı",legendYukTxt:"Yükleme / kapı",legendBosTxt:"Boşluk",
footNote:"Not: Kolon, sprinkler, yangın kaçışları ve yönetmelik şartları ayrıca kontrol edilmelidir.",
arac:"ARAÇ",personel:"PERSONEL",tipI:"I Tipi",tipU:"U Tipi",yonEn:"EN",yonBoy:"BOY",yerlesimLbl:"Yerleşim: ",
statusAuto:"Önerilen yerleşim uygulandı. ",statusMain:"Toplam MODUL raf modülü. Boşluk yaklaşık BOSLUK m².",
alertOlcu:"Depo ölçülerini kontrol edin.",alertYukleme:"Yükleme alanı depo boyundan küçük olmalı.",alertAlan:"Kullanılabilir alan kalmıyor.",
alertUygunYok:"Uygun yerleşim bulunamadı.",pdfHata:"PDF oluşturulamadı."},
en:{title:"WAREHOUSE RACK LAYOUT",subtitle:"Technical layout / capacity optimization",depoOlcu:"Warehouse W × L (m)",
yuklemeAlani:"Loading Area W × L (m)",yerlesim:"Layout",auto:"Program Suggestion",iTipi:"Type I",uTipi:"Type U",
koridor:"Vehicle / Aisle (m)",elArabasi:"Hand Truck 1.00m",transpalet:"Pallet Jack 1.50m",forklift:"Forklift 3.20m",agirlikliForklift:"Counterbalance 4.00m",
rafModulu:"Bay Width (m)",rafDerinligi:"Rack Depth (m)",katSayisi:"Levels",dikmeYuksekligi:"Upright Height (m)",hesapla:"↻ CALCULATE",
malzemeBaslik:"Materials and Cost",dikme:"Upright (m)",yanBaglanti:"Beam",ankraj:"Anchor",zeminMetal:"Floor Plate",
montaj:"Installation",transport:"Transport",toplam:"TOTAL",adet:"Qty",tutar:"Amount",ciktiBaslik:"Output",pdf:"EXPORT PDF",whatsapp:"WhatsApp",telegram:"Telegram",eposta:"Email",
legendRafTxt:"Rack body",legendYanTxt:"Beam",legendYukTxt:"Loading / door",legendBosTxt:"Unused",
footNote:"Note: Columns, sprinklers, fire exits and code compliance must be checked separately.",
arac:"VEHICLE",personel:"STAFF",tipI:"Type I",tipU:"Type U",yonEn:"WIDTH",yonBoy:"LENGTH",yerlesimLbl:"Layout: ",
statusAuto:"Suggested layout applied. ",statusMain:"Total MODUL rack bays. Unused approx. BOSLUK m².",
alertOlcu:"Check warehouse dimensions.",alertYukleme:"Loading area must be smaller than warehouse length.",alertAlan:"No usable area left.",
alertUygunYok:"No suitable layout found.",pdfHata:"Could not generate PDF."},
ru:{title:"ПЛАН СКЛАДСКИХ СТЕЛЛАЖЕЙ",subtitle:"Технический план / оптимизация вместимости",depoOlcu:"Склад Ш × Д (м)",
yuklemeAlani:"Зона погрузки Ш × Д (м)",yerlesim:"Планировка",auto:"Рекомендация",iTipi:"Тип I",uTipi:"Тип U",
koridor:"Техника / Проезд (м)",elArabasi:"Тележка 1.00м",transpalet:"Гидротележка 1.50м",forklift:"Погрузчик 3.20м",agirlikliForklift:"Противовес 4.00м",
rafModulu:"Модуль (м)",rafDerinligi:"Глубина (м)",katSayisi:"Ярусы",dikmeYuksekligi:"Высота стойки (м)",hesapla:"↻ РАССЧИТАТЬ",
malzemeBaslik:"Материалы и стоимость",dikme:"Стойки (м)",yanBaglanti:"Балки",ankraj:"Анкера",zeminMetal:"Опорные пластины",
montaj:"Монтаж",transport:"Транспорт",toplam:"ИТОГО",adet:"Кол-во",tutar:"Сумма",ciktiBaslik:"Вывод",pdf:"PDF",whatsapp:"WhatsApp",telegram:"Telegram",eposta:"Эл.почта",
legendRafTxt:"Стеллаж",legendYanTxt:"Балка",legendYukTxt:"Погрузка/дверь",legendBosTxt:"Пусто",
footNote:"Прим.: колонны, спринклеры, эвакуационные выходы и нормы проверяются отдельно.",
arac:"ТЕХНИКА",personel:"ПЕРСОНАЛ",tipI:"Тип I",tipU:"Тип U",yonEn:"Ш",yonBoy:"Д",yerlesimLbl:"Планировка: ",
statusAuto:"Применена рекомендованная планировка. ",statusMain:"Всего MODUL модулей. Неисп. ок. BOSLUK м².",
alertOlcu:"Проверьте размеры склада.",alertYukleme:"Зона погрузки должна быть меньше длины склада.",alertAlan:"Не осталось полезной площади.",
alertUygunYok:"Подходящая планировка не найдена.",pdfHata:"Не удалось создать PDF."}
};
var currentLang = "tr";
function t(key){ return (LANG[currentLang] && LANG[currentLang][key]) || key; }
function applyStaticTranslations(){
    var els = document.querySelectorAll("[data-i18n]");
    for (var i=0;i<els.length;i++) els[i].textContent = t(els[i].getAttribute("data-i18n"));
    document.title = t("title");
}
function setLanguage(lang){ currentLang = lang; applyStaticTranslations(); cizimYap(); }

/* ================= AYARLAR ================= */
const MARJIN = 0.50, KENAR_BOSLUK = 0.30, SIRT_BOSLUK = 0.10;

/* ================= SVG YARDIMCILARI ================= */
function svgEl(tag, attrs, text){
    attrs = attrs || {};
    var el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    if (text) el.textContent = text;
    return el;
}
function temizle(id){ document.getElementById(id).innerHTML = ""; }
function metre(v){ return Number(v).toFixed(2); }

/* küçük, ölçünün üstünde durduğu kompakt etiket (dışa taşan ok/ölçü çizgisi yok) */
function miniLabel(layer, cx, cy, text, color, bg){
    var w = Math.max(24, text.length*4.9+6);
    layer.appendChild(svgEl("rect",{x:cx-w/2,y:cy-7,width:w,height:12,rx:2.5,fill:bg||"#ffffff",stroke:"#94a3b8","stroke-width":0.6,opacity:0.95}));
    layer.appendChild(svgEl("text",{x:cx,y:cy+3,"text-anchor":"middle","font-size":7.6,"font-family":"Courier New, monospace","font-weight":"bold",fill:color||"#111827"},text));
}

/* ================= RAF ÇİZİMİ ================= */
function drawRackRun(layer, x, y, length, depth, modul, scale, horizontal, depthLabel){
    var w = horizontal ? length*scale : depth*scale;
    var h = horizontal ? depth*scale : length*scale;

    layer.appendChild(svgEl("rect",{x:x,y:y,width:w,height:h,fill:"#8fa3bd",stroke:"#1e293b","stroke-width":2}));

    var bayCount = Math.max(1, Math.floor(length/modul));
    for (var i=1;i<bayCount;i++){
        var pos = i*modul*scale;
        if (horizontal) layer.appendChild(svgEl("line",{x1:x+pos,y1:y,x2:x+pos,y2:y+h,stroke:"#1e293b","stroke-width":1.3}));
        else layer.appendChild(svgEl("line",{x1:x,y1:y+pos,x2:x+w,y2:y+pos,stroke:"#1e293b","stroke-width":1.3}));
    }
    var cc = "#f97316";
    if (horizontal){
        layer.appendChild(svgEl("line",{x1:x,y1:y+3,x2:x+w,y2:y+3,stroke:cc,"stroke-width":4}));
        layer.appendChild(svgEl("line",{x1:x,y1:y+h-3,x2:x+w,y2:y+h-3,stroke:cc,"stroke-width":4}));
    } else {
        layer.appendChild(svgEl("line",{x1:x+3,y1:y,x2:x+3,y2:y+h,stroke:cc,"stroke-width":4}));
        layer.appendChild(svgEl("line",{x1:x+w-3,y1:y,x2:x+w-3,y2:y+h,stroke:cc,"stroke-width":4}));
    }
    if (depthLabel) miniLabel(layer, x+w/2, y+h/2, depthLabel, "#1d4ed8", "#eff6ff");
    return { bayCount: bayCount, length: length };
}

function drawDoor(layer, hingeX, wallY, widthPx, label){
    layer.appendChild(svgEl("rect",{x:hingeX-1,y:wallY-3.5,width:widthPx+2,height:7,fill:"#fff"}));
    layer.appendChild(svgEl("line",{x1:hingeX,y1:wallY,x2:hingeX,y2:wallY-widthPx,stroke:"#111827","stroke-width":1.3}));
    layer.appendChild(svgEl("path",{d:"M "+hingeX+" "+(wallY-widthPx)+" A "+widthPx+" "+widthPx+" 0 0 1 "+(hingeX+widthPx)+" "+wallY,fill:"none",stroke:"#111827","stroke-width":0.9,"stroke-dasharray":"3,2"}));
    if (label) layer.appendChild(svgEl("text",{x:hingeX+widthPx/2,y:wallY+11,"text-anchor":"middle","font-size":6.5,fill:"#111827"},label));
}

/* ================= EKSEN PAKETLEME ================= */
function eksenPaketle(available, depth, koridor, mode){
    var rows = [], remaining = available;
    if (mode === "single"){
        var n = Math.max(0, Math.floor((available + koridor) / (depth + koridor)));
        for (var i=0;i<n;i++) rows.push(depth);
        var used = n>0 ? n*depth + (n-1)*koridor : 0;
        return { rows: rows, leftover: Math.max(0, available-used) };
    }
    var pairDepth = 2*depth + SIRT_BOSLUK;
    if (remaining >= depth){
        rows.push(depth); remaining -= depth;
        while (remaining >= koridor + depth){
            var afterC = remaining - koridor;
            if (afterC >= pairDepth + koridor + depth){ rows.push(pairDepth); remaining = afterC - pairDepth; }
            else if (afterC >= pairDepth){ rows.push(pairDepth); remaining = afterC - pairDepth; break; }
            else if (afterC >= depth){ rows.push(depth); remaining = afterC - depth; break; }
            else break;
        }
    }
    return { rows: rows, leftover: Math.max(0, remaining) };
}

/* ================= I / U HESAP ================= */
function hesaplaI(storageW, storageH, orientation, koridor, modul, rafD){
    var runAxis = orientation === "EN" ? storageW : storageH;
    var stackAxis = orientation === "EN" ? storageH : storageW;
    if (runAxis <= 0 || stackAxis <= 0) return null;
    var bays = Math.floor(runAxis / modul);
    if (bays <= 0) return null;
    var packed = eksenPaketle(stackAxis, rafD, koridor, "single");
    if (packed.rows.length === 0) return null;
    return { type:"I", orientation:orientation, bays:bays, runLength:bays*modul, runLeftover:runAxis-bays*modul,
        rows:packed.rows, stackLeftover:packed.leftover, total:packed.rows.length*bays };
}
function hesaplaU(storageW, storageH, koridor, modul, rafD){
    if (storageH <= rafD+koridor || storageW <= 2*rafD+2*koridor) return null;
    var backBays = Math.floor(storageW / modul);
    var sideLength = storageH - rafD - koridor;
    var leftBays = Math.floor(sideLength / modul);
    var interiorWidth = storageW - 2*rafD - 2*koridor;
    var interiorHeight = sideLength;
    var interiorBays=0, interiorRows=[], interiorLeftoverStack=0, interiorLeftoverRun=0, interiorTotal=0;
    if (interiorWidth > rafD && interiorHeight >= modul){
        interiorBays = Math.floor(interiorHeight/modul);
        interiorLeftoverRun = interiorHeight - interiorBays*modul;
        var packed = eksenPaketle(interiorWidth, rafD, koridor, "mixed");
        interiorRows = packed.rows; interiorLeftoverStack = packed.leftover;
        for (var i=0;i<interiorRows.length;i++) interiorTotal += (interiorRows[i] > rafD*1.5 ? 2 : 1) * interiorBays;
    }
    var total = backBays + leftBays*2 + interiorTotal;
    if (total <= 0) return null;
    return { type:"U", backBays:backBays, leftBays:leftBays, rightBays:leftBays, sideLength:sideLength,
        backLeftover: storageW-backBays*modul, sideLeftover: sideLength-leftBays*modul,
        interiorWidth:interiorWidth, interiorHeight:interiorHeight, interiorBays:interiorBays,
        interiorRows:interiorRows, interiorLeftoverStack:interiorLeftoverStack, interiorLeftoverRun:interiorLeftoverRun, total: total };
}

/* ================= MALZEME + MALİYET ================= */
function hesaplaMalzeme(layout, rafD, katSayisi){
    var uprights=0, beams=0;
    function ekle(bays){ uprights += 2*(bays+1); beams += 2*bays*katSayisi; }
    if (layout.type === "I"){ for (var i=0;i<layout.rows.length;i++) ekle(layout.bays); }
    else {
        ekle(layout.leftBays); ekle(layout.rightBays); ekle(layout.backBays);
        for (var j=0;j<layout.interiorRows.length;j++){
            var faces = layout.interiorRows[j] > rafD*1.5 ? 2 : 1;
            for (var f=0;f<faces;f++) ekle(layout.interiorBays);
        }
    }
    return { uprights: uprights, beams: beams };
}
function hesaplaMaliyet(){
    var mDikmeEl = document.getElementById("mDikme");
    var dikmeMetre = parseFloat(mDikmeEl.getAttribute("data-metre")) || 0;
    var yanAdet = parseFloat(document.getElementById("mYan").textContent) || 0;
    var fiyatDikme = parseFloat(document.getElementById("fiyatDikme").value) || 0;
    var fiyatYan = parseFloat(document.getElementById("fiyatYan").value) || 0;
    var ankrajAdet = parseFloat(document.getElementById("ankrajAdet").value) || 0;
    var fiyatAnkraj = parseFloat(document.getElementById("fiyatAnkraj").value) || 0;
    var zeminAdet = parseFloat(document.getElementById("zeminAdet").value) || 0;
    var fiyatZemin = parseFloat(document.getElementById("fiyatZemin").value) || 0;
    var fiyatMontaj = parseFloat(document.getElementById("fiyatMontaj").value) || 0;
    var fiyatTransport = parseFloat(document.getElementById("fiyatTransport").value) || 0;
    var tDikme = dikmeMetre*fiyatDikme, tYan = yanAdet*fiyatYan, tAnkraj = ankrajAdet*fiyatAnkraj, tZemin = zeminAdet*fiyatZemin;
    var toplam = tDikme+tYan+tAnkraj+tZemin+fiyatMontaj+fiyatTransport;
    var fmt = function(n){ return n.toLocaleString(undefined,{maximumFractionDigits:0})+" €"; };
    document.getElementById("tDikme").textContent = fmt(tDikme);
    document.getElementById("tYan").textContent = fmt(tYan);
    document.getElementById("tAnkraj").textContent = fmt(tAnkraj);
    document.getElementById("tZemin").textContent = fmt(tZemin);
    document.getElementById("tMontaj").textContent = fmt(fiyatMontaj);
    document.getElementById("tTransport").textContent = fmt(fiyatTransport);
    document.getElementById("tToplam").textContent = fmt(toplam);
}

/* ================= ANA HESAPLA + ÇİZ ================= */
function cizimYap(){
    var depoEn = parseFloat(document.getElementById("depoEn").value);
    var depoBoy = parseFloat(document.getElementById("depoBoy").value);
    var yuklemeEn = parseFloat(document.getElementById("yuklemeEn").value);
    var yuklemeBoy = parseFloat(document.getElementById("yuklemeBoy").value);
    var koridor = parseFloat(document.getElementById("aracTipi").value);
    var modul = parseFloat(document.getElementById("paletModul").value);
    var rafD = parseFloat(document.getElementById("rafDerinlik").value);
    var katSayisi = Math.max(1, Math.round(parseFloat(document.getElementById("katSayisi").value) || 1));
    var dikmeYukseklik = parseFloat(document.getElementById("dikmeYukseklik").value) || 0;
    var secim = document.getElementById("yerlesimDuzen").value;

    if (!depoEn || !depoBoy || !yuklemeBoy || depoEn<=0 || depoBoy<=0){ alert(t("alertOlcu")); return; }
    if (yuklemeBoy >= depoBoy){ alert(t("alertYukleme")); return; }

    var storageW = depoEn - 2*MARJIN;
    var storageH = depoBoy - yuklemeBoy - KENAR_BOSLUK - MARJIN;
    if (storageW <= 0 || storageH <= 0){ alert(t("alertAlan")); return; }

    var iEN = hesaplaI(storageW, storageH, "EN", koridor, modul, rafD);
    var iBOY = hesaplaI(storageW, storageH, "BOY", koridor, modul, rafD);
    var uType = hesaplaU(storageW, storageH, koridor, modul, rafD);
    var secenekler = [iEN, iBOY, uType].filter(function(x){ return x && x.total>0; });
    var layout = null;
    if (secim === "I") layout = [iEN,iBOY].filter(function(x){return x&&x.total>0;}).reduce(function(a,b){return (!a||b.total>a.total)?b:a;},null);
    else if (secim === "U") layout = uType;
    else layout = secenekler.reduce(function(a,b){return (!a||b.total>a.total)?b:a;},null);
    if (!layout){ alert(t("alertUygunYok")); return; }

    temizle("rackLayer"); temizle("loadingLayer"); temizle("voidLayer"); temizle("labelLayer");
    var rackLayer = document.getElementById("rackLayer");
    var loadingLayer = document.getElementById("loadingLayer");
    var voidLayer = document.getElementById("voidLayer");
    var labelLayer = document.getElementById("labelLayer");

    var pxX=10, pxY=30, pxW=580, pxH=560;
    var scale = Math.min(pxW/depoEn, pxH/depoBoy);
    var drawW = depoEn*scale, drawH = depoBoy*scale;
    var offsetX = pxX + (pxW-drawW)/2;
    var offsetY = pxY + (pxH-drawH)/2;

    var wh = document.getElementById("warehouse");
    wh.setAttribute("x",offsetX); wh.setAttribute("y",offsetY); wh.setAttribute("width",drawW); wh.setAttribute("height",drawH);
    document.getElementById("svgInfo").textContent = metre(depoEn)+" × "+metre(depoBoy)+" m  |  "+t(layout.type==="I"?"tipI":"tipU");

    var loadWidth = Math.min(yuklemeEn, depoEn);
    var loadWpx = loadWidth*scale, loadHpx = yuklemeBoy*scale;
    var loadX = offsetX + ((depoEn-loadWidth)/2)*scale;
    var loadY = offsetY + drawH - loadHpx;
    loadingLayer.appendChild(svgEl("rect",{x:loadX,y:loadY,width:loadWpx,height:loadHpx,fill:"#eff6ff",stroke:"#16a34a","stroke-width":1.5,"stroke-dasharray":"5,3"}));

    var wallY = offsetY+drawH;
    var vehicleW = Math.min(3.5, loadWidth*0.4), pedW=1.0, gapBtw=0.3;
    var doorStartX = loadX + loadWpx/2 - ((vehicleW+gapBtw+pedW)*scale)/2;
    drawDoor(loadingLayer, doorStartX, wallY, vehicleW*scale, t("arac"));
    drawDoor(loadingLayer, doorStartX+(vehicleW+gapBtw)*scale, wallY, pedW*scale, t("personel"));

    var storageLeft = offsetX + MARJIN*scale;
    var storageRight = offsetX + drawW - MARJIN*scale;
    var storageTop = offsetY + MARJIN*scale;
    var storageBottom = loadY - KENAR_BOSLUK*scale;
    var toplamBoslukM2 = 0;

    function voidBox(x,y,w,h,value){
        if (w<=0||h<=0) return;
        voidLayer.appendChild(svgEl("rect",{x:x,y:y,width:w,height:h,fill:"url(#voidPattern)",stroke:"#dc2626","stroke-width":1,"stroke-dasharray":"3,2"}));
        miniLabel(labelLayer, x+w/2, y+h/2, metre(value)+"m", "#b91c1c", "#fff");
    }

    if (layout.type === "I"){
        var isEN = layout.orientation === "EN";
        var runPx = layout.runLength*scale, cursor=0, positions=[];
        for (var i=0;i<layout.rows.length;i++){ if (i>0) cursor += koridor; positions.push({depth:layout.rows[i], start:cursor}); cursor += layout.rows[i]; }
        var stackUsedPx = cursor*scale;

        for (var r=0;r<positions.length;r++){
            var row = positions[r];
            var dLabel = r===0 ? metre(row.depth)+"m" : null;
            if (isEN) drawRackRun(rackLayer, storageLeft, storageTop+row.start*scale, layout.runLength, row.depth, modul, scale, true, dLabel);
            else drawRackRun(rackLayer, storageLeft+row.start*scale, storageTop, layout.runLength, row.depth, modul, scale, false, dLabel);
        }
        if (positions.length>1){
            var c0s = positions[0].start+positions[0].depth, c0e = positions[1].start;
            if (isEN) miniLabel(labelLayer, storageLeft+8, storageTop+((c0s+c0e)/2)*scale, metre(koridor)+"m", "#0f766e", "#f0fdfa");
            else miniLabel(labelLayer, storageLeft+((c0s+c0e)/2)*scale, storageTop+8, metre(koridor)+"m", "#0f766e", "#f0fdfa");
        }
        if (positions.length){
            if (isEN){
                miniLabel(labelLayer, storageLeft+runPx-30, storageTop+positions[0].depth*scale/2, metre(layout.runLength)+"m", "#7c2d12", "#fff7ed");
                miniLabel(labelLayer, storageLeft+modul*scale/2, storageTop+positions[0].depth*scale+10, metre(modul)+"m", "#7c2d12", "#fff7ed");
            } else {
                miniLabel(labelLayer, storageLeft+positions[0].depth*scale/2, storageTop+runPx-30, metre(layout.runLength)+"m", "#7c2d12", "#fff7ed");
                miniLabel(labelLayer, storageLeft+positions[0].depth*scale+18, storageTop+modul*scale/2, metre(modul)+"m", "#7c2d12", "#fff7ed");
            }
        }
        if (layout.runLeftover > 0.05){
            if (isEN) voidBox(storageLeft+runPx, storageTop, layout.runLeftover*scale, stackUsedPx, layout.runLeftover);
            else voidBox(storageLeft, storageTop+runPx, stackUsedPx, layout.runLeftover*scale, layout.runLeftover);
            toplamBoslukM2 += layout.runLeftover*cursor;
        }
        if (layout.stackLeftover > 0.05){
            if (isEN) voidBox(storageLeft, storageTop+stackUsedPx, runPx, layout.stackLeftover*scale, layout.stackLeftover);
            else voidBox(storageLeft+stackUsedPx, storageTop, layout.stackLeftover*scale, runPx, layout.stackLeftover);
            toplamBoslukM2 += layout.stackLeftover*layout.runLength;
        }
        document.getElementById("statusBox").setAttribute("data-layout", t("yerlesimLbl")+t("tipI")+" ("+(isEN?t("yonEn"):t("yonBoy"))+")");
    } else {
        var rafDpx = rafD*scale;
        var sideStartY = storageTop + rafDpx + koridor*scale;

        drawRackRun(rackLayer, storageLeft, storageTop, layout.backBays*modul, rafD, modul, scale, true, metre(rafD)+"m");
        drawRackRun(rackLayer, storageLeft, sideStartY, layout.leftBays*modul, rafD, modul, scale, false, null);
        drawRackRun(rackLayer, storageRight-rafDpx, sideStartY, layout.rightBays*modul, rafD, modul, scale, false, null);

        miniLabel(labelLayer, storageLeft+8, storageTop+rafDpx+(koridor*scale)/2, metre(koridor)+"m", "#0f766e", "#f0fdfa");
        miniLabel(labelLayer, storageLeft+8, sideStartY+layout.leftBays*modul*scale-14, metre(layout.leftBays*modul)+"m", "#7c2d12", "#fff7ed");
        miniLabel(labelLayer, storageLeft+8, sideStartY+modul*scale/2, metre(modul)+"m", "#7c2d12", "#fff7ed");

        var interiorLeft = storageLeft+rafDpx+koridor*scale;
        var interiorTop = sideStartY;
        if (layout.interiorRows.length){
            var icursor=0, ipositions=[];
            for (var j=0;j<layout.interiorRows.length;j++){ if (j>0) icursor += koridor; ipositions.push({depth:layout.interiorRows[j], start:icursor}); icursor += layout.interiorRows[j]; }
            var interiorRunPx = layout.interiorBays*modul*scale, interiorStackUsedPx = icursor*scale;
            for (var k=0;k<ipositions.length;k++){
                var irow = ipositions[k], ix = interiorLeft+irow.start*scale;
                drawRackRun(rackLayer, ix, interiorTop, layout.interiorBays*modul, irow.depth, modul, scale, false, k===0?metre(irow.depth)+"m":null);
                if (irow.depth > rafD*1.5){
                    var seamX = ix+rafDpx+(SIRT_BOSLUK*scale)/2;
                    rackLayer.appendChild(svgEl("line",{x1:seamX,y1:interiorTop,x2:seamX,y2:interiorTop+interiorRunPx,stroke:"#334155","stroke-width":1,"stroke-dasharray":"3,2"}));
                }
            }
            miniLabel(labelLayer, interiorLeft+interiorStackUsedPx/2, interiorTop+interiorRunPx-14, metre(layout.interiorBays*modul)+"m", "#7c2d12", "#fff7ed");
            if (layout.interiorLeftoverRun > 0.05){ voidBox(interiorLeft, interiorTop+interiorRunPx, interiorStackUsedPx, layout.interiorLeftoverRun*scale, layout.interiorLeftoverRun); toplamBoslukM2 += layout.interiorLeftoverRun*icursor; }
            if (layout.interiorLeftoverStack > 0.05){ voidBox(interiorLeft+interiorStackUsedPx, interiorTop, layout.interiorLeftoverStack*scale, interiorRunPx, layout.interiorLeftoverStack); toplamBoslukM2 += layout.interiorLeftoverStack*layout.interiorBays*modul; }
        }
        if (layout.sideLeftover > 0.05){
            voidBox(storageLeft, sideStartY+layout.leftBays*modul*scale, rafDpx, layout.sideLeftover*scale, layout.sideLeftover);
            voidBox(storageRight-rafDpx, sideStartY+layout.leftBays*modul*scale, rafDpx, layout.sideLeftover*scale, layout.sideLeftover);
            toplamBoslukM2 += layout.sideLeftover*rafD*2;
        }
        if (layout.backLeftover > 0.05){
            voidBox(storageLeft+layout.backBays*modul*scale, storageTop, layout.backLeftover*scale, rafDpx, layout.backLeftover);
            toplamBoslukM2 += layout.backLeftover*rafD;
        }
        document.getElementById("statusBox").setAttribute("data-layout", t("yerlesimLbl")+t("tipU"));
    }

    var malzeme = hesaplaMalzeme(layout, rafD, katSayisi);
    var dikmeMetre = malzeme.uprights * dikmeYukseklik;
    var mDikmeEl = document.getElementById("mDikme");
    mDikmeEl.textContent = malzeme.uprights;
    mDikmeEl.setAttribute("data-metre", dikmeMetre);
    document.getElementById("mYan").textContent = malzeme.beams;
    document.getElementById("ankrajAdet").value = malzeme.uprights;
    hesaplaMaliyet();

    var statusTxt = (secim==="AUTO" ? t("statusAuto") : "") + t("statusMain").replace("MODUL",layout.total).replace("BOSLUK",toplamBoslukM2.toFixed(1));
    document.getElementById("statusBox").innerHTML = document.getElementById("statusBox").getAttribute("data-layout")+" — "+statusTxt;
}

/* ================= PDF ================= */
function pdfOlustur(){
    var sheet = document.getElementById("outputSheet");
    html2canvas(sheet,{scale:2,backgroundColor:"#ffffff"}).then(function(canvas){
        var imgData = canvas.toDataURL("image/png");
        var jsPDFCtor = window.jspdf.jsPDF;
        var pdf = new jsPDFCtor({ orientation:"portrait", unit:"mm", format:"a4" });
        var pageW = pdf.internal.pageSize.getWidth(), pageH = pdf.internal.pageSize.getHeight();
        var imgW = pageW-10, imgH = imgW*canvas.height/canvas.width;
        if (imgH > pageH-10){ imgH = pageH-10; imgW = imgH*canvas.width/canvas.height; }
        pdf.addImage(imgData,"PNG",5,5,imgW,imgH);
        pdf.save("depo-raf-plani.pdf");
    }).catch(function(){ alert(t("pdfHata")); });
}
function ozetMetni(){ return encodeURIComponent(t("title")+"\n"+t("toplam")+": "+document.getElementById("tToplam").textContent); }
function whatsappPaylas(){ window.open("https://wa.me/?text="+ozetMetni(), "_blank"); }
function telegramPaylas(){ window.open("https://t.me/share/url?url=&text="+ozetMetni(), "_blank"); }
function mailPaylas(){ window.location.href = "mailto:?subject=Depo%20Raf%20Yerlesim%20Plani&body="+ozetMetni(); }

window.cizimYap = cizimYap; window.pdfOlustur = pdfOlustur;
window.whatsappPaylas = whatsappPaylas; window.telegramPaylas = telegramPaylas; window.mailPaylas = mailPaylas;

document.getElementById("btnHesapla").addEventListener("click", cizimYap);
document.getElementById("btnPdf").addEventListener("click", pdfOlustur);
document.getElementById("btnWhatsapp").addEventListener("click", whatsappPaylas);
document.getElementById("btnTelegram").addEventListener("click", telegramPaylas);
document.getElementById("btnMail").addEventListener("click", mailPaylas);
document.getElementById("dilSecim").addEventListener("change", function(e){ setLanguage(e.target.value); });
["fiyatDikme","fiyatYan","ankrajAdet","fiyatAnkraj","zeminAdet","fiyatZemin","fiyatMontaj","fiyatTransport"].forEach(function(id){
    document.getElementById(id).addEventListener("input", hesaplaMaliyet);
});
window.addEventListener("load", function(){ applyStaticTranslations(); cizimYap(); });
</script>
</body>
</html>
