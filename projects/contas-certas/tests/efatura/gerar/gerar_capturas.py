# Gera capturas sintéticas da página «Deduções Provisórias em IRS» com dados FICTÍCIOS, em /tmp/ef.
# Requer: python3, playwright (chromium). Created by Redfox using Claude
import json, sys
from playwright.sync_api import sync_playwright
TILES=[("Despesas Gerais Familiares",2841.33,250.00),("Saúde",1234.56,185.18),("Educação",980.40,294.12),("Habitação",6000.00,502.00),
("Lares",0.00,0.00),("Reparação de Automóveis",412.10,11.56),("Restauração e Alojamento",1520.75,42.66),("Cabeleireiros",210.00,5.91),
("Atividades Veterinárias",95.20,2.67),("Transportes Públicos Coletivos",480.00,4.08),("Ginásios",360.00,10.12)]
def eur(v): s=f"{v:,.2f}".replace(",","X").replace(".",",").replace("X","."); return s+" €"
def html(dark, cols, layout):
    bg,fg,card,mut=("#1e1f22","#e8e8e8","#2b2d31","#a0a0a0") if dark else ("#f2f4f7","#1f2937","#ffffff","#6b7280")
    tiles=""
    for n,d,ded in TILES:
        if layout=="A": body=f'<div class="big">{eur(ded)}</div><div class="sm">Despesa: {eur(d)}</div>'
        elif layout=="B": body=f'<div class="sm">Valor da despesa</div><div class="mid">{eur(d)}</div><div class="sm">Dedução</div><div class="mid">{eur(ded)}</div>'
        else: body=f'<div class="mid">{eur(d)}</div><div class="mid">{eur(ded)}</div>'
        tiles+=f'<div class="t"><div class="h">{n}</div>{body}</div>'
    side='' if cols<3 else '<div class="side"><p>Início</p><p>Faturas</p><p>Saúde</p><p>Educação</p><p>Benefícios</p></div>'
    tot=sum(t[2] for t in TILES)
    return f'''<html><body style="margin:0;font-family:Arial,Helvetica,sans-serif;background:{bg};color:{fg}">
<style>.t{{background:{card};border-radius:6px;padding:14px;min-height:110px}} .h{{font-weight:bold;font-size:14px;margin-bottom:8px}}
.big{{font-size:22px;font-weight:bold}} .mid{{font-size:16px;margin:2px 0}} .sm{{font-size:12px;color:{mut}}}
.side{{width:170px;float:left;padding:10px;font-size:13px}} .main{{overflow:hidden;padding:16px}}
.g{{display:grid;grid-template-columns:repeat({cols},1fr);gap:12px}}</style>
<div style="padding:10px 16px;font-size:13px">e-fatura · NIF --------- · Adquirente</div>{side}
<div class="main"><h2 style="font-size:20px">Deduções Provisórias em IRS - 2026</h2>
<div style="font-size:16px;margin-bottom:12px">Total: {eur(tot)}</div><div class="g">{tiles}</div>
<p style="font-size:11px;color:{mut}">As despesas de saúde com IVA à taxa normal só são consideradas com receita médica. Valores provisórios de 01-01-2026 a 31-10-2026, 15% de dedução.</p></div></body></html>'''
cases=[("pc_claro",False,4,"A",1280,1.0),("pc_escuro",True,4,"A",1280,1.0),("pc_B",False,4,"B",1280,1.0),("pc_C",False,3,"C",1100,1.0),
("tlm_claro",False,2,"A",412,2.6),("tlm_escuro",True,2,"B",412,2.6),("pc_pequeno",False,4,"B",1280,0.75)]
with sync_playwright() as p:
    b=p.chromium.launch()
    for name,dark,cols,lay,w,dpr in cases:
        pg=b.new_page(viewport={"width":w,"height":800},device_scale_factor=dpr)
        open(f"/tmp/ef/{name}.html","w").write(html(dark,cols,lay)); pg.goto(f"file:///tmp/ef/{name}.html")
        pg.screenshot(path=f"/tmp/ef/{name}.png",full_page=True); pg.close()
    b.close()
json.dump({n:ded for n,_,ded in TILES},open("/tmp/ef/esperado.json","w"),ensure_ascii=False)
print("ok")
