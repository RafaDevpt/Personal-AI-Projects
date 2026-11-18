# Imita lerPalavrasImagem (src/lib/import/ocr.ts) com o tesseract CLI: 1.ª leitura no tamanho original e,
# se a letra for pequena (<16 px), 2.ª leitura ampliada. Uso: python3 ler_capturas.py captura.png saida.json
# Created by Redfox using Claude
import sys, json, subprocess, csv, io, statistics
from PIL import Image, ImageOps
src, out = sys.argv[1], sys.argv[2]
base = Image.open(src).convert("RGB")
def prep(f):
    g = ImageOps.grayscale(base)
    if abs(f-1)>0.01: g = g.resize((round(g.width*f), round(g.height*f)), Image.LANCZOS)
    hist=g.histogram(); n=sum(hist)
    if sum(i*h for i,h in enumerate(hist))/n < 128: g=ImageOps.invert(g)
    return ImageOps.autocontrast(g, cutoff=2)
def ocr(img):
    img.save("/tmp/ef/_p.png")
    tsv=subprocess.run(["tesseract","/tmp/ef/_p.png","-","-l","por","--psm","11","--dpi","300","tsv"],capture_output=True,text=True).stdout
    ws=[]
    for r in csv.DictReader(io.StringIO(tsv),delimiter="\t",quoting=csv.QUOTE_NONE):
        if r["level"]=="5" and r["text"].strip():
            x,y,w,h=int(r["left"]),int(r["top"]),int(r["width"]),int(r["height"]); ws.append({"text":r["text"],"x0":x,"y0":y,"x1":x+w,"y1":y+h})
    return ws
p1=ocr(prep(1)); passes=[p1]
h=statistics.median([w["y1"]-w["y0"] for w in p1]) if p1 else 0
if not p1 or h<16: passes.append(ocr(prep(min(3, 26/max(h,8)))))
json.dump(passes, open(out,"w"), ensure_ascii=False)
