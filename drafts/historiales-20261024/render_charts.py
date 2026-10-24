"""Own charts from frozen CSV only: pip install -r requirements.txt; python render_charts.py."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

from reproduce import read_rows, analyse

ROOT = Path(__file__).resolve().parent
COLORS = {'background': '#101f33', 'text': '#e9f0f7', 'muted': '#b7c9da',
          'MEDIA': '#68c9f5', 'ALTA': '#ffc36b', 'INCIERTO': '#b7c9da', 'ABIERTO': '#7de2b0'}
plt.rcParams.update({'font.family': ['DejaVu Sans', 'Arial', 'sans-serif'], 'font.size': 12,
                     'text.color': COLORS['text'], 'axes.labelcolor': COLORS['muted'],
                     'xtick.color': COLORS['muted'], 'ytick.color': COLORS['muted'],
                     'axes.edgecolor': '#4d647b', 'axes.facecolor': COLORS['background'],
                     'figure.facecolor': COLORS['background'], 'svg.fonttype': 'none',
                     'svg.hashsalt': 'ormuz-history-editorial-20261024'})


def save(fig, name, screenshots):
    fig.savefig(ROOT/name, format='svg', metadata={'Date': None, 'Creator': 'Estrecho Ormuz; frozen monitor CSV; Matplotlib'})
    path = ROOT/name
    path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',
                    encoding='utf-8', newline='\n')
    if screenshots:
        screenshots.mkdir(parents=True, exist_ok=True)
        fig.savefig(screenshots/Path(name).with_suffix('.png'), dpi=140)
    plt.close(fig)


def render(screenshots=None):
    result = analyse(read_rows())
    dots = result['plot_rows']
    for lang in ('es', 'en'):
        es = lang == 'es'
        fig, axes = plt.subplots(2, 1, figsize=(14, 7.5), sharex=True)
        fig.subplots_adjust(left=.075, right=.975, top=.82, bottom=.17, hspace=.65)
        for ax, model in zip(axes, ('legacy', 'v7')):
            group = [r for r in dots if r['model'] == model]
            key = 'state' if model == 'legacy' else 'confidence'
            labels = ('INCIERTO', 'ABIERTO') if model == 'legacy' else ('MEDIA', 'ALTA')
            for label in labels:
                selected = [r for r in group if r[key] == label]
                x = [datetime.fromisoformat(r['day_utc']).replace(tzinfo=timezone.utc) for r in selected]
                y = [r['stack'] for r in selected]
                ax.scatter(x, y, s=22 if label in {'INCIERTO', 'MEDIA'} else 28,
                           marker='o' if label in {'INCIERTO', 'MEDIA'} else 'D',
                           color=COLORS[label], linewidths=0, zorder=3)
            ax.set_ylim(.35, result['daily_max_records'][model]+.8)
            ax.set_yticks([1, 3, 5, 7] if model == 'legacy' else [1, 3, 5])
            ax.set_ylabel('Apilado diario' if es else 'Daily stack', fontsize=11)
            ax.set_title((('Motor anterior' if es else 'Earlier engine') if model == 'legacy' else 'V7')
                         + f'  ·  {len(group)} '+('registros' if es else 'records'), loc='left', pad=32, fontsize=14)
            if model == 'legacy':
                names = ['INCIERTO · 51', 'ABIERTO · 3'] if es else ['INCIERTO (uncertain) · 51', 'ABIERTO (open) · 3']
            else:
                names = ['MEDIA · 47', 'ALTA · 2'] if es else ['MEDIA (medium) · 47', 'ALTA (high) · 2']
            handles = [Line2D([0], [0], marker='o' if i == 0 else 'D', linestyle='none',
                              markerfacecolor=COLORS[label], markeredgewidth=0, markersize=6)
                       for i, label in enumerate(labels)]
            ax.legend(handles, names, loc='lower left', bbox_to_anchor=(0, 1.005),
                      ncol=2, frameon=False, labelcolor=COLORS['muted'], fontsize=11, borderaxespad=0)
            ax.grid(axis='x', color='#63778b', alpha=.2)
            ax.spines[['top', 'right']].set_visible(False)
        axes[-1].set_xlim(datetime(2026, 7, 10, tzinfo=timezone.utc), datetime(2026, 10, 24, tzinfo=timezone.utc))
        axes[-1].xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2, tz=timezone.utc))
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%d/%m', tz=timezone.utc))
        axes[-1].set_xlabel('Día UTC · julio–octubre de 2026' if es else 'UTC day · July–October 2026', labelpad=12)
        fig.suptitle('Cada punto es una decisión guardada' if es else 'Each dot is a retained decision',
                     x=.075, y=.965, ha='left', fontsize=20, weight='bold')
        fig.text(.075, .91, '103 puntos en dos modelos; no se unen ni se interpolan.' if es else
                 '103 dots across two models; no connecting lines or interpolation.', color=COLORS['muted'], fontsize=13)
        fig.text(.075, .06, 'Fuente: archivos congelados del proyecto · horas exactas en CSV · apilado para evitar solapes' if es else
                 'Source: frozen project archives · exact times in CSV · stacked to prevent overlap', fontsize=11, color=COLORS['muted'])
        save(fig, f'history-timeline-{lang}.svg', screenshots)

        fig, ax = plt.subplots(figsize=(10, 4.4))
        fig.subplots_adjust(left=.19, right=.93, top=.69, bottom=.25)
        ax.barh([1, 0], [47, 2], color=[COLORS['MEDIA'], COLORS['ALTA']], height=.42)
        ax.set_yticks([1, 0], ['MEDIA · media', 'ALTA · alta'] if es else ['MEDIA · medium', 'ALTA · high'])
        ax.set_xlim(0, 51)
        ax.set_xticks([0, 10, 20, 30, 40, 49])
        for y, value in ((1, 47), (0, 2)):
            ax.text(value+.7, y, str(value), va='center', fontsize=17, weight='bold')
        ax.set_xlabel('Registros V7 conservados' if es else 'Retained V7 records', labelpad=10)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis='x', color='#63778b', alpha=.2)
        fig.suptitle('La confianza no fue uniforme' if es else 'Confidence was not uniform',
                     x=.055, y=.94, ha='left', fontsize=20, weight='bold')
        fig.text(.055, .81, '7 agosto–21 octubre 2026 · 49 registros · etiquetas del modelo' if es else
                 '7 August–21 October 2026 · 49 records · model labels', fontsize=12, color=COLORS['muted'])
        fig.text(.055, .07, 'Fuente: archivo V7 congelado · confianza no equivale a precisión estadística' if es else
                 'Source: frozen V7 archive · confidence is not statistical accuracy', fontsize=11, color=COLORS['muted'])
        save(fig, f'history-confidence-{lang}.svg', screenshots)
        # A two-bar comparison fits on a phone; unlike the timeline it needs no panning.
        fig, ax = plt.subplots(figsize=(5, 4.5))
        fig.subplots_adjust(left=.25, right=.88, top=.62, bottom=.25)
        ax.barh([1, 0], [47, 2], color=[COLORS['MEDIA'], COLORS['ALTA']], height=.4)
        ax.set_yticks([1, 0], ['MEDIA', 'ALTA'], fontsize=14)
        ax.set_xlim(0, 54)
        ax.set_xticks([0, 25, 49], ['0', '25', '49'], fontsize=14)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        for y, value in ((1, 47), (0, 2)):
            ax.text(value+1, y, str(value), va='center', fontsize=18, weight='bold')
        fig.suptitle('Dos niveles de\nconfianza' if es else 'Confidence was\nnot uniform',
                     x=.06, y=.95, ha='left', fontsize=20, weight='bold')
        fig.text(.06, .72, 'V7 · 49 registros' if es else 'V7 · 49 records', fontsize=14, color=COLORS['muted'])
        fig.text(.06, .09, 'Etiquetas, no precisión' if es else 'Labels, not accuracy', fontsize=14, color=COLORS['muted'])
        save(fig, f'history-confidence-mobile-{lang}.svg', screenshots)
    return collision_audit()


def collision_audit():
    """Measure the actual SVG marker centres, not only uniqueness of CSV timestamps."""
    ns = {'s': 'http://www.w3.org/2000/svg'}
    report = {'coordinate_units': 'SVG viewBox units; timeline minimum CSS width 1040 px',
              'maximum_marker_diameter_svg_units': 8.0,
              'diameter_bound': 'Conservative bound; largest diamond is about 7.49 SVG units wide', 'files': {}}
    for lang in ('es', 'en'):
        path = ROOT/f'history-timeline-{lang}.svg'
        tree = ET.parse(path)
        panels = []
        for ax in tree.findall('.//s:g', ns):
            if not ax.get('id', '').startswith('axes_'):
                continue
            points = [(float(u.get('x')), float(u.get('y')))
                      for collection in ax.findall('./s:g', ns) if collection.get('id', '').startswith('PathCollection_')
                      for u in collection.findall('.//s:use', ns)]
            distance = min(math.dist(a, b) for i, a in enumerate(points) for b in points[i+1:])
            panels.append({'markers': len(points), 'unique_centres': len(set(points)),
                           'minimum_centre_distance': round(distance, 6),
                           'overlap': distance < report['maximum_marker_diameter_svg_units']})
        assert [p['markers'] for p in panels] == [54, 49], panels
        assert all(not p['overlap'] and p['unique_centres'] == p['markers'] for p in panels), panels
        report['files'][path.name] = panels
    (ROOT/'chart-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--png-output', type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.png_output), indent=2))
