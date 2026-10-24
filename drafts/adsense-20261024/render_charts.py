"""Render only frozen CSV inputs: pip install -r requirements.txt; python render_charts.py."""
import csv
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).parent
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'text.color': '#e5edf6',
    'axes.labelcolor': '#c1d0e0', 'xtick.color': '#c1d0e0', 'ytick.color': '#c1d0e0',
    'axes.edgecolor': '#526278', 'axes.facecolor': '#101f33', 'figure.facecolor': '#101f33',
    'svg.hashsalt': 'ormuz-editorial-draft-20261024', 'svg.fonttype': 'none'})


def read(name):
    with (ROOT/name).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def save(fig, name):
    fig.savefig(ROOT/name, format='svg', bbox_inches='tight', metadata={'Date': None, 'Creator': 'Estrecho Ormuz; Matplotlib; frozen CSV inputs'})
    path=ROOT/name
    path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8', newline='\n')
    plt.close(fig)


def render():
    monitor=read('monitor-observations.csv'); energy=read('energy-context.csv'); exposure=read('spain-eu-context.csv')
    for lang in ('es','en'):
        es=lang=='es'
        fig, axes=plt.subplots(2,1,figsize=(11,5.8),sharex=True,layout='constrained')
        for ax, model in zip(axes,('legacy','v7')):
            rows=[row for row in monitor if row['model']==model]
            times=[datetime.fromisoformat(row['at'].replace('Z','+00:00')) for row in rows]
            values=[int(row['state']=='ABIERTO') if model=='legacy' else 0 for row in rows]
            ax.scatter(times,values,color='#73c9fa',s=34,alpha=.85)
            ax.set_ylim(-.5,1.5 if model=='legacy' else .5)
            ax.set_yticks([0,1] if model=='legacy' else [0],
                ['INCIERTO','ABIERTO'] if model=='legacy' else ['MUY RESTRINGIDO' if es else 'SEVERELY RESTRICTED'])
            ax.set_title((('Motor anterior' if es else 'Earlier engine') if model=='legacy' else 'V7')+f' · n={len(rows)}',loc='left',color='#e5edf6')
            ax.grid(axis='x',alpha=.15)
        axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        axes[-1].set_xlabel('Fecha del registro (UTC) · sin interpolación' if es else 'Record date (UTC) · no interpolation')
        fig.suptitle('Decisiones retenidas, no recuentos de buques' if es else 'Retained decisions, not vessel counts',fontsize=17)
        save(fig,f'history-{lang}.svg')

        fig,ax=plt.subplots(figsize=(11,5.3),layout='constrained')
        for key,label,color in [('oil_million_barrels_per_day','Petróleo' if es else 'Oil','#73c9fa'),('lng_billion_cubic_feet_per_day','GNL' if es else 'LNG','#f3b869')]:
            base=float(energy[3][key]); values=[float(row[key])/base*100 for row in energy]
            ax.plot(range(len(values)),values,marker='o',linewidth=2,color=color,label=label)
            ax.annotate(f'{values[-1]:.1f}',(len(values)-1,values[-1]),xytext=(8,0),textcoords='offset points',color=color)
        ax.set_xticks(range(len(energy)),[row['period'] for row in energy]);ax.set_ylim(0,125);ax.set_xlim(-.1,5.6)
        ax.axhline(100,alpha=.35,linestyle='--',color='white')
        ax.set_ylabel('Índice · 2025T4 = 100' if es else 'Index · 2025 Q4 = 100')
        ax.set_title('Flujos energéticos estimados por EIA · serie histórica' if es else 'EIA estimated energy flows · historical series',loc='left',pad=18,fontsize=16)
        legend=ax.legend(loc='upper center',facecolor='#101f33',edgecolor='#526278')
        for text in legend.get_texts():text.set_color('#e5edf6')
        ax.grid(axis='y',alpha=.15)
        fig.supxlabel('Transformación propia de EIA, tabla 4, 12/08/2026 · no son datos del monitor' if es else 'Own transformation of EIA table 4, 12 Aug 2026 · not monitor measurements',fontsize=10)
        save(fig,f'energy-{lang}.svg')

        fig,axes=plt.subplots(2,1,figsize=(11,5.4),layout='constrained')
        for ax,row in zip(axes,exposure):
            val=float(row['share_percent'])
            label=('España · Cuota publicada de aprovisionamiento' if es else 'Spain · Published procurement share') if row['geography']=='Spain' else ('UE · Valor de importaciones de GNL' if es else 'EU · LNG import value')
            ax.barh([0],[100],color='#2d4059',height=.4);ax.barh([0],[val],color='#73c9fa',height=.4)
            ax.set_yticks([]);ax.set_xlim(0,100);ax.set_xticks([0,25,50,75,100]);ax.set_xlabel('%',labelpad=0)
            ax.set_title(label+f' · 2025 · Qatar {val:g}%',loc='left',color='#e5edf6',fontsize=13)
            for side in ('left','top','right'):ax.spines[side].set_visible(False)
        fig.suptitle('Dos bases distintas: no es una clasificación de riesgo' if es else 'Different denominators: not a risk ranking',fontsize=16)
        fig.supxlabel('Fuentes: Enagás (España) · Eurostat (UE). Diseño y lectura propios.' if es else 'Sources: Enagás (Spain) · Eurostat (EU). Own design and interpretation.',fontsize=10)
        save(fig,f'exposure-{lang}.svg')


if __name__=='__main__':render()
