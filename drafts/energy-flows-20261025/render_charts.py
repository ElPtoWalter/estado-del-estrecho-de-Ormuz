"""Own SVG charts from the frozen EIA aggregate rows. No external images/fonts."""
from pathlib import Path
import io,json,sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import energy_data as data


def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'ormuz-energy-20261025',
        'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':12,'text.color':'#e9f0f7',
        'axes.labelcolor':'#b7c9da','xtick.color':'#b7c9da','ytick.color':'#e9f0f7',
        'axes.facecolor':'#101f33','figure.facecolor':'#101f33','axes.edgecolor':'#30475e'})
    rows,_=data.calculate();products={};checks={}
    for lang in ('es','en'):
        es=lang=='es';periods=[r['period'].replace('Q','T') if es else r['period'].replace('Q',' Q') for r in rows]
        for mobile in (False,True):
            fs=14 if mobile else 12
            fig,axes=plt.subplots(2,1,figsize=(4.5,10.5)) if mobile else plt.subplots(1,2,figsize=(13,6))
            fig.subplots_adjust(left=.24 if mobile else .10,right=.89 if mobile else .95,top=.78 if mobile else .73,bottom=.22 if mobile else .26,hspace=.65,wspace=.52)
            annotations=[];titles=[]
            for ax,key,color,title,unit,maximum,ticks in zip(axes,
                ['oil_million_barrels_per_day','lng_billion_cubic_feet_per_day'],['#68c9f5','#ffc36b'],
                ['Petróleo total' if es else 'Total oil','GNL' if es else 'LNG'],
                ['Millones de barriles/día' if es else 'Million barrels/day','Miles de millones\nde pies cúbicos/día' if es else 'Billion cubic feet/day'],
                [27,15],[range(0,26,5),range(0,13,4)]):
                values=[float(r[key]) for r in rows];y=np.arange(6)
                bars=ax.barh(y,values,height=.55,color=color)
                ax.set_yticks(y,periods,fontsize=fs);ax.invert_yaxis();ax.set_xlim(0,maximum);ax.set_xticks(list(ticks));ax.tick_params(axis='x',labelsize=fs-1)
                ax.set_xlabel(unit,fontsize=fs,labelpad=13);titles.append(ax.set_title(title,loc='left',fontsize=fs+3,pad=18,weight='bold'))
                ax.grid(axis='x',color='#30475e',alpha=.6);ax.set_axisbelow(True)
                for spine in ('top','right','left'):ax.spines[spine].set_visible(False)
                for bar,value in zip(bars,values):
                    label=f'{value:.1f}'.replace('.',',') if es else f'{value:.1f}'
                    annotations.append(ax.text(value+.30,bar.get_y()+bar.get_height()/2,label,va='center',fontsize=fs,weight='bold'))
            fig.suptitle('Dos unidades, seis trimestres' if es else 'Two units, six quarters',fontsize=18 if mobile else 23,x=.08 if mobile else .04,ha='left',y=.96,weight='bold')
            fig.text(.08 if mobile else .04,.90 if mobile else .89,'Medias diarias estimadas\n2025T1–2026T2' if es else 'Estimated daily averages\n2025 Q1–2026 Q2',fontsize=fs,color='#b7c9da',va='top')
            fig.text(.08 if mobile else .04,.025,('Fuente: EIA, tabla 4 · 12/08/2026\nAnálisis EIA basado en Vortexa.\nGráfico propio; no mide el tráfico de hoy.' if es else
                'Source: EIA, table 4 · 12 Aug 2026\nEIA analysis based on Vortexa.\nOwn chart; not a current traffic reading.'),fontsize=fs-2,color='#b7c9da',linespacing=1.5)
            name=f'energy-absolute-{lang}'+('-mobile' if mobile else '')+'.svg'
            products[name],checks[name]=save(fig,annotations,plt,matplotlib,rows,'absolute',titles)
            fig,ax=plt.subplots(figsize=(4.5,6.2) if mobile else (13,6.2));fig.subplots_adjust(left=.16 if mobile else .08,right=.91 if mobile else .91,top=.68 if mobile else .73,bottom=.25 if mobile else .23)
            x=np.arange(6);annotations=[]
            for key,color,marker,line,label in [('oil_index_2025q4_100','#68c9f5','o','-','Petróleo' if es else 'Oil'),
                                                   ('lng_index_2025q4_100','#ffc36b','D','--','GNL' if es else 'LNG')]:
                values=[float(r[key]) for r in rows]
                ax.plot(x,values,color=color,marker=marker,linestyle=line,linewidth=2.2,
                        markersize=8 if marker=='o' else 5,
                        markerfacecolor='none' if marker=='o' else color,markeredgewidth=1.5,label=label)
                endpoint=f'{values[-1]:.1f}'.replace('.',',') if es else f'{values[-1]:.1f}'
                annotations.append(ax.text(5.12,values[-1],endpoint,color=color,fontsize=fs,va='center',weight='bold'))
            ax.axhline(100,color='#b7c9da',linewidth=.9,alpha=.55)
            ax.set_ylim(0,130);ax.set_xlim(-.2,5.75);ax.set_yticks([0,25,50,75,100,125]);ax.tick_params(axis='y',labelsize=fs-1)
            short=[p.replace('2025','25').replace('2026','26').replace(' ','') for p in periods] if mobile else periods
            ax.set_xticks(x,short,fontsize=fs-2 if mobile else fs);ax.set_ylabel('Índice' if es else 'Index',fontsize=fs)
            ax.grid(axis='y',color='#30475e',alpha=.5);ax.set_axisbelow(True)
            for spine in ('top','right'):ax.spines[spine].set_visible(False)
            ax.legend(loc='lower left',bbox_to_anchor=(0,1.08),ncol=2,frameon=False,fontsize=fs)
            fig.suptitle('La misma base, distinta caída' if es else 'Same baseline, different declines',fontsize=17 if mobile else 23,x=.08 if mobile else .04,ha='left',y=.97,weight='bold')
            fig.text(.08 if mobile else .04,.89 if mobile else .89,'2025T4 = 100 en cada serie' if es else '2025 Q4 = 100 for each series',fontsize=fs,color='#b7c9da',va='top')
            fig.text(.08 if mobile else .04,.03,('Fuente: EIA, tabla 4 · 12/08/2026\nCálculo propio; sin unidades físicas comunes.\nPuntos trimestrales; no datos diarios.' if es else
                'Source: EIA, table 4 · 12 Aug 2026\nOwn calculation; no shared physical unit.\nQuarterly points, not daily observations.'),fontsize=fs-2,color='#b7c9da',linespacing=1.5)
            name=f'energy-index-{lang}'+('-mobile' if mobile else '')+'.svg'
            products[name],checks[name]=save(fig,annotations,plt,matplotlib,rows,'index')
    return products,checks


def save(fig,annotations,plt,matplotlib,rows,kind,titles=()):
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    boxes=[t.get_window_extent(renderer) for t in annotations]
    inside=all(b.x0>=0 and b.y0>=0 and b.x1<=fig.bbox.x1 and b.y1<=fig.bbox.y1 for b in boxes)
    overlap=any(a.overlaps(b) for i,a in enumerate(boxes) for b in boxes[i+1:])
    if not inside or overlap:raise ValueError('Chart value labels clip or overlap')
    decorations=list(fig.texts)+[a.xaxis.label for a in fig.axes]+list(titles)
    boxes2=[t.get_window_extent(renderer) for t in decorations if t.get_text()]
    text_overlap=any(a.overlaps(b) for i,a in enumerate(boxes2) for b in boxes2[i+1:])
    if text_overlap:raise ValueError('Chart title, units or source text overlap: '+repr([(a.get_text(),b.get_text()) for i,a in enumerate(decorations) for b in decorations[i+1:] if a.get_text() and b.get_text() and a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer))]))
    stream=io.StringIO();fig.savefig(stream,format='svg',metadata={'Date':None,'Creator':'Estrecho Ormuz; Matplotlib '+matplotlib.__version__})
    text=stream.getvalue();text=text.replace('<svg ',f'<svg role="img" aria-label="EIA 2025Q1–2026Q2; own {kind} chart" ',1)
    plt.close(fig)
    return text.encode(),{'quarters':6,'series':2,'value_labels':len(annotations),'value_label_overlap':overlap,'value_labels_within_figure':inside,'title_units_source_overlap':text_overlap,'index_marker_strategy':'Hollow oil circles and smaller filled LNG diamonds; exact shared baseline of 100 is not jittered' if kind=='index' else None,'matplotlib':matplotlib.__version__,'source_input_sha256_lf':data.sha(data.INPUT.read_bytes())}


if __name__=='__main__':
    files,audit=figures()
    for name,payload in files.items():(data.FOLDER/name).write_bytes(payload)
    (data.FOLDER/'chart-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Eight original SVGs generated: absolute and index, ES/EN, desktop/mobile. Value labels checked.')
