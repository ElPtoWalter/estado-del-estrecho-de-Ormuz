"""Own figures. Two questions, two languages, desktop/mobile; no EU risk ranking."""
import json,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
from matplotlib.ticker import FuncFormatter
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import spain_data as data
FOLDER=data.FOLDER
BG='#101f33';TEXT='#e9f0f7';MUTED='#b7c9da';BLUE='#68c9f5';AMBER='#ffc36b';GREEN='#7de2b0'
plt.rcParams.update({'font.family':['Arial','DejaVu Sans','sans-serif'],'svg.fonttype':'none','svg.hashsalt':'ormuz-spain-20261025','text.color':TEXT,'axes.labelcolor':MUTED,'xtick.color':MUTED,'ytick.color':MUTED})

def number(value,lang,digits=3):return format(float(value),f'.{digits}f').replace('.',',' if lang=='es' else '.')

def draw(kind,lang,mobile):
 es=lang=='es';values=data.calculate();size=(6,7.5) if mobile else (12,5.5)
 fig=plt.figure(figsize=size,facecolor=BG);fontsize=17 if mobile else 13
 ax=fig.add_axes([.10,.27,.83,.48] if mobile else [.08,.29,.85,.45],facecolor=BG)
 title=('El mismo suministro, otra base' if es else 'Same supply, different denominator') if kind=='denominators' else ('Tres lecturas en documentos de Enagás' if es else 'Three readings in Enagás documents')
 if mobile and kind=='discrepancy':title='Tres lecturas de Enagás' if es else 'Three Enagás readings'
 title_artist=fig.text(.08,.93,title,fontsize=19 if mobile else 21,fontweight='bold',va='top')
 note=('Cocientes propios · España · 2025' if es else 'Own quotients · Spain · 2025') if kind=='denominators' else ('Cuotas de aprovisionamiento · 2025' if es else 'Gas procurement shares · 2025')
 subtitle=fig.text(.08,.85,note,fontsize=14 if mobile else 12,color=MUTED,va='top')
 labels=[]
 if kind=='denominators':
  ax.set_xlim(0,3);ax.set_ylim(-.6,1.9)
  names=[('Total: 372.498 GWh' if es else 'All gas: 372,498 GWh'),('Solo GNL: 248.084 GWh' if es else 'LNG only: 248,084 GWh')]
  for y,name,key,color in zip((1,0),names,('es_total_share','es_lng_share'),(BLUE,AMBER)):
   v=float(values[key][0]);ax.barh(y,v,height=.30,color=color,zorder=3)
   labels.append(ax.text(0,y+.31,name,fontsize=fontsize,va='bottom',color=TEXT))
   labels.append(ax.text(v-.06,y,number(v,lang)+' %',fontsize=fontsize-1,ha='right',va='center',color='#081321',fontweight='bold',zorder=4))
  ax.set_xticks([0,1,2,3]);xlabel='Parte del denominador (%)' if es else 'Share of denominator (%)'
  source=('Numerador fijo: 6.403 GWh atribuidos a Catar.\nEnagás 2025, pp. 23–24. Elaboración propia.\nNo corrige la cuota del gráfico del PDF.' if es else 'Fixed numerator: 6,403 GWh attributed to Qatar.\nEnagás 2025, pp. 23–24. Own calculations.\nNot a correction to the PDF chart share.')
 else:
  ax.set_xlim(1.710,1.740);ax.set_ylim(-.5,2.8)
  rows=[(2,'Gráfico PDF · p. 25' if es else 'PDF chart · p. 25',1.735,'1,735 %' if es else '1.735 %',AMBER),
        (1,'Cociente mapa / total' if es else 'Map / total quotient',float(values['es_total_share'][0]),number(values['es_total_share'][0],lang,6)+' %',BLUE),
        (0,'Excel · Pág. 25!E12',float(values['excel_share'][0]),number(values['excel_share'][0],lang,6)+' %',GREEN)]
  for y,label,value,text,color in rows:
   ax.hlines(y,1.710,1.740,color='#30475e',lw=1)
   ax.scatter([value],[y],s=85,color=color,marker='D' if y==0 else 'o',zorder=4)
   labels.append(ax.text(1.710,y+.25,label,fontsize=fontsize,va='bottom'))
   labels.append(ax.text(1.740,y-.17,text,fontsize=fontsize-1,color=color,ha='right',va='top'))
  ax.set_xticks([1.710,1.720,1.730,1.740]);ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:number(x,lang,3)))
  xlabel='Cuota (%) · escala ampliada' if es else 'Share (%) · expanded scale'
  source=('Enagás 2025: PDF pp. 23–25 y Excel enlazado.\nCociente propio: 6.403 / 372.498 × 100.\nLa causa de la discrepancia sigue sin documentarse.' if es else 'Enagás 2025: PDF pp. 23–25 and linked workbook.\nOwn quotient: 6,403 / 372,498 × 100.\nThe cause of the discrepancy remains undocumented.')
 ax.set_yticks([]);ax.tick_params(axis='x',labelsize=16 if mobile else 11,length=0,pad=10)
 ax.set_xlabel(xlabel,fontsize=14 if mobile else 12,labelpad=13)
 ax.grid(axis='x',color='#30475e',alpha=.45,zorder=0)
 for spine in ax.spines.values():spine.set_visible(False)
 source_artist=fig.text(.08,.13,source,fontsize=14 if mobile else 11,color=MUTED,va='top',linespacing=1.5)
 fig.canvas.draw();renderer=fig.canvas.get_renderer()
 artists=[title_artist,subtitle,source_artist]+labels
 boxes=[a.get_window_extent(renderer) for a in artists]
 bounds=fig.bbox
 within=all(b.x0>=0 and b.y0>=0 and b.x1<=bounds.x1 and b.y1<=bounds.y1 for b in boxes)
 overlap=any(a.overlaps(b) for i,a in enumerate(boxes) for b in boxes[i+1:])
 if not within or overlap:raise ValueError(f'Chart text overflow/overlap: {kind} {lang} {mobile}')
 name=f'spain-{kind}-{lang}'+('-mobile' if mobile else '')+'.svg'
 path=FOLDER/name
 fig.savefig(path,format='svg',facecolor=BG,metadata={'Date':None,'Creator':'Estrecho Ormuz; own calculations and chart'})
 plt.close(fig)
 raw=path.read_text(encoding='utf-8');start=raw.index('>',raw.index('<svg'))+1
 raw=raw[:start]+f'<title>{title}</title><desc>2025. '+('Elaboración propia; datos y fórmulas en la metodología.' if es else 'Own chart; data and formulas in the methodology.')+'</desc>'+raw[start:]
 path.write_text(raw,encoding='utf-8',newline='\n')
 return {'source_input_sha256_lf':data.sha(data.INPUT.read_bytes()),'text_within_figure':within,'label_title_source_overlap':overlap,'matplotlib':matplotlib.__version__,'numpy':numpy.__version__,'eu_risk_comparison':False,'expanded_axis':kind=='discrepancy'}

if __name__=='__main__':
 audit={}
 for kind in ('denominators','discrepancy'):
  for lang in ('es','en'):
   for mobile in (False,True):
    name=f'spain-{kind}-{lang}'+('-mobile' if mobile else '')+'.svg';audit[name]=draw(kind,lang,mobile)
 (FOLDER/'chart-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Eight original SVGs generated; labels, titles and sources inspected for overlap.')
