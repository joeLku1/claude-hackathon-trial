"""Matplotlib renders the entire canvas, including annotations, in every format."""
import io
import threading
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
from .formulas import Sheet, address
from .model import validate

LOCK = threading.Lock()


def formatted(value, style, decimals=0):
    if style == 'percent':
        return f'{value:.{decimals}%}'
    if style == 'currency':
        return f'${value:,.{decimals}f}'
    if style == 'compact':
        for scale, suffix in ((1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'k')):
            if abs(value) >= scale:
                return f'{value / scale:.{decimals}f}{suffix}'
    return f'{value:,.{decimals}f}'


def render(project, fmt='svg'):
    if fmt not in ('svg', 'png', 'pdf'):
        raise ValueError('Choose SVG, PNG or PDF')
    p = validate(project)
    values, errors = Sheet(p['cells']).calculate()
    c = p['chart']
    data = []
    for col in c['series']:
        series = []
        for r, row in enumerate(values):
            value = row[col]
            if not isinstance(value, (int, float)):
                errors.setdefault(address(r, col), 'Chart series must contain numbers')
            series.append(value if isinstance(value, (int, float)) else 0)
        data.append(series)
    if c['type'] == 'scatter':
        if any(not isinstance(row[0], (int, float)) for row in values):
            errors['chart'] = 'Scatter charts need numbers in column A (X values)'
    if errors:
        return None, values, errors
    if c['type'] == 'donut' and (any(v < 0 for v in data[0]) or sum(data[0]) <= 0):
        return None, values, {'chart': 'Donut values must be nonnegative with a positive total'}
    with LOCK, matplotlib.rc_context({'font.family': c['font'], 'font.size': c['fontSize'],
                                     'text.color': c['foreground'], 'svg.fonttype': 'none',
                                     'text.parse_math': False, 'axes.unicode_minus': False}):
        fig = Figure(figsize=(c['width'] / 100, c['height'] / 100), dpi=100, facecolor=c['background'])
        ax = fig.add_axes([c['plotX'], 1 - c['plotY'] - c['plotHeight'], c['plotWidth'], c['plotHeight']], facecolor=c['background'])
        fig.text(0.075, 0.92, c['title'], fontsize=c['titleSize'], weight='bold', va='top')
        fig.text(0.075, 0.855, c['subtitle'], fontsize=c['fontSize'], va='top', alpha=0.7)
        labels = [str(row[0]) if not isinstance(row[0], float) else f'{row[0]:g}' for row in values]
        x = list(range(len(values)))
        colors = c['colors']
        positive, negative = [0.] * len(x), [0.] * len(x)
        for i, (col, y) in enumerate(zip(c['series'], data)):
            color = colors[i % len(colors)]
            kw = {'color': color, 'alpha': c['opacity'], 'label': p['headers'][col]}
            bars = None
            if c['type'] in ('bar', 'horizontal'):
                width = c['barWidth'] / len(data)
                offsets = [v - c['barWidth'] / 2 + width * (i + 0.5) for v in x]
                if c['type'] == 'bar':
                    bars = ax.bar(offsets, y, width=width * 0.9, **kw)
                else:
                    bars = ax.barh(offsets, y, height=width * 0.9, **kw)
            elif c['type'] == 'stacked':
                bottom = [positive[j] if v >= 0 else negative[j] for j, v in enumerate(y)]
                bars = ax.bar(x, y, bottom=bottom, width=c['barWidth'], **kw)
                for j, v in enumerate(y):
                    (positive if v >= 0 else negative)[j] += v
            elif c['type'] in ('line', 'area'):
                ax.plot(x, y, linewidth=c['lineWidth'], marker='o', markersize=c['markerSize'], **kw)
                if c['type'] == 'area':
                    ax.fill_between(x, y, color=color, alpha=c['opacity'] * 0.16)
            elif c['type'] == 'scatter':
                ax.scatter([r[0] for r in values], y, s=max(1, c['markerSize']) ** 2, **kw)
            elif c['type'] == 'donut':
                if i:
                    continue
                ax.pie(y, labels=labels, colors=[colors[j % len(colors)] for j in range(len(y))],
                       wedgeprops={'width': 0.35, 'edgecolor': c['background'], 'alpha': c['opacity']},
                       textprops={'color': c['foreground']},
                       autopct='%1.1f%%' if c['labels'] else None, startangle=90)
                ax.set_aspect('equal')
            if c['labels'] and bars is not None:
                ax.bar_label(bars, labels=[formatted(v, c['numberFormat'], c['decimals']) for v in y], padding=3, fontsize=max(8, c['fontSize'] - 2), color=c['foreground'])
            elif c['labels'] and c['type'] in ('line', 'area', 'scatter'):
                for j, v in enumerate(y):
                    ax.annotate(formatted(v, c['numberFormat'], c['decimals']),
                                ((values[j][0] if c['type'] == 'scatter' else j), v),
                                xytext=(0, 9), textcoords='offset points', ha='center', fontsize=max(8, c['fontSize'] - 2))
        if c['type'] != 'donut':
            horizontal = c['type'] == 'horizontal'
            if c['type'] != 'scatter':
                if horizontal:
                    ax.set_yticks(x, labels)
                    ax.invert_yaxis()
                else:
                    ax.set_xticks(x, labels, rotation=c['rotation'])
            axis = ax.xaxis if horizontal else ax.yaxis
            axis.set_major_formatter(FuncFormatter(lambda v, _: formatted(v, c['numberFormat'], c['decimals'])))
            axis.set_major_locator(MaxNLocator(nbins=6))
            ax.set_axisbelow(True)
            if c['grid']:
                ax.grid(axis='x' if horizontal else 'y', color=c['gridColor'], linewidth=0.8)
            ax.tick_params(colors=c['foreground'], length=0, pad=9)
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.set_xlabel(c['xlabel'], color=c['foreground'], labelpad=12)
            ax.set_ylabel(c['ylabel'], color=c['foreground'], labelpad=12)
            limits = {k: None if c[k] == '' else c[k] for k in ('ymin', 'ymax')}
            if any(v is not None for v in limits.values()):
                (ax.set_xlim if horizontal else ax.set_ylim)(limits['ymin'], limits['ymax'])
            ax.margins(y=0.15 if not horizontal else 0.05, x=0.05)
            if c['legend']:
                legend = ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(0, -0.13), ncol=min(4, len(data)), borderaxespad=0)
                for item in legend.get_texts():
                    item.set_color(c['foreground'])
        for n in p['annotations']:
            fig.text(n['x'], 1 - n['y'], n['text'], fontsize=n['size'], color=n['color'],
                     weight='bold' if n['bold'] else 'normal', va='top')
        output = io.BytesIO()
        fig.savefig(output, format=fmt, dpi=150 if fmt == 'png' else 100, facecolor=c['background'])
        fig.clear()
        return output.getvalue(), values, {}
