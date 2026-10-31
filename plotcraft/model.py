"""Project schema validation shared by preview, import and export."""
import copy
import math
import re

PALETTE = ['#6260de', '#19a894', '#f0ad50', '#e47492', '#479ed1', '#a778c4']
DEFAULT = {
    'version': 1, 'name': 'A little growth story',
    'headers': ['Month', 'This year', 'Last year'],
    'cells': [['Jan', '28', '20'], ['Feb', '42', '25'], ['Mar', '38', '32'],
              ['Apr', '62', '41'], ['May', '74', '48'], ['Jun', '=SUM(B4:B5)/2+20', '54']],
    'cellStyles': {},
    'chart': {'type': 'bar', 'title': 'Small ideas. Big momentum.',
              'subtitle': 'Monthly community growth · a sample story', 'xlabel': '', 'ylabel': 'Members',
              'background': '#ffffff', 'foreground': '#263348', 'gridColor': '#e7eaf0',
              'colors': PALETTE, 'font': 'DejaVu Sans', 'fontSize': 12, 'titleSize': 25,
              'grid': True, 'legend': True, 'labels': False, 'lineWidth': 2.5,
              'markerSize': 6, 'barWidth': 0.72, 'opacity': 1, 'rotation': 0,
              'numberFormat': 'number', 'decimals': 0, 'width': 1200, 'height': 760,
              'plotX': 0.10, 'plotY': 0.21, 'plotWidth': 0.82, 'plotHeight': 0.56,
              'ymin': '', 'ymax': '', 'series': [1, 2]},
    'annotations': [{'text': 'Built one month at a time.', 'x': 0.10, 'y': 0.91,
                     'size': 12, 'color': '#68748a', 'bold': False}],
}


def default_project():
    return copy.deepcopy(DEFAULT)


def text(value, limit=250):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f'Text must be at most {limit} characters')
    return value


def number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'Number must be between {low} and {high}')
    return value


def color(value):
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise ValueError('Colors must use #RRGGBB')
    return value


def validate(data):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Expected a Plotcraft version 1 project')
    p = default_project()
    p['name'] = text(data.get('name', p['name']), 100)
    headers, cells = data.get('headers'), data.get('cells')
    if not isinstance(headers, list) or not 2 <= len(headers) <= 12:
        raise ValueError('Use 2–12 columns')
    p['headers'] = [text(h, 60) for h in headers]
    if not isinstance(cells, list) or not 1 <= len(cells) <= 200:
        raise ValueError('Use 1–200 data rows')
    p['cells'] = []
    for row in cells:
        if not isinstance(row, list) or len(row) != len(headers):
            raise ValueError('Each row must match the number of headers')
        p['cells'].append([text(v, 500) for v in row])
    c = data.get('chart', {})
    if not isinstance(c, dict):
        raise ValueError('Invalid chart settings')
    for key in ('title', 'subtitle', 'xlabel', 'ylabel'):
        p['chart'][key] = text(c.get(key, p['chart'][key]))
    for key in ('background', 'foreground', 'gridColor'):
        p['chart'][key] = color(c.get(key, p['chart'][key]))
    enums = {'type': ['bar', 'horizontal', 'stacked', 'line', 'area', 'scatter', 'donut'],
             'font': ['DejaVu Sans', 'DejaVu Serif', 'DejaVu Sans Mono'],
             'numberFormat': ['number', 'percent', 'currency', 'compact']}
    for key, options in enums.items():
        val = c.get(key, p['chart'][key])
        if val not in options:
            raise ValueError(f'Invalid {key}')
        p['chart'][key] = val
    ranges = {'fontSize': (8, 24), 'titleSize': (12, 44), 'lineWidth': (0.5, 8),
              'markerSize': (0, 16), 'barWidth': (0.1, 0.95), 'opacity': (0.1, 1),
              'rotation': (-90, 90), 'decimals': (0, 4), 'width': (600, 2000),
              'height': (400, 1600), 'plotX': (0.05, 0.4), 'plotY': (0.12, 0.4),
              'plotWidth': (0.3, 0.9), 'plotHeight': (0.2, 0.65)}
    for key, (low, high) in ranges.items():
        p['chart'][key] = number(c.get(key, p['chart'][key]), low, high)
    for key in ('width', 'height', 'decimals'):
        if p['chart'][key] != int(p['chart'][key]):
            raise ValueError(f'{key} must be an integer')
    if p['chart']['plotX'] + p['chart']['plotWidth'] > 0.97 or p['chart']['plotY'] + p['chart']['plotHeight'] > 0.88:
        raise ValueError('Plot must fit inside the canvas')
    for key in ('grid', 'legend', 'labels'):
        val = c.get(key, p['chart'][key])
        if type(val) is not bool:
            raise ValueError(f'{key} must be true or false')
        p['chart'][key] = val
    for key in ('ymin', 'ymax'):
        val = c.get(key, '')
        p['chart'][key] = '' if val == '' else number(val, -1e15, 1e15)
    if all(p['chart'][k] != '' for k in ('ymin', 'ymax')) and p['chart']['ymin'] >= p['chart']['ymax']:
        raise ValueError('Axis maximum must be greater than minimum')
    colors = c.get('colors', PALETTE)
    if not isinstance(colors, list) or not 1 <= len(colors) <= 12:
        raise ValueError('Use 1–12 palette colors')
    p['chart']['colors'] = [color(v) for v in colors]
    series = c.get('series', list(range(1, len(headers))))
    if not isinstance(series, list) or not series or len(series) > 11 or len(set(series)) != len(series):
        raise ValueError('Select at least one unique series')
    p['chart']['series'] = [int(number(v, 1, len(headers) - 1)) for v in series]
    if any(type(v) is not int for v in series):
        raise ValueError('Series indices must be integers')
    notes = data.get('annotations', [])
    if not isinstance(notes, list) or len(notes) > 20:
        raise ValueError('Use at most 20 annotations')
    p['annotations'] = []
    for n in notes:
        if not isinstance(n, dict):
            raise ValueError('Invalid annotation')
        p['annotations'].append({'text': text(n.get('text', ''), 200),
                                'x': number(n.get('x', 0.1), 0, 0.95),
                                'y': number(n.get('y', 0.5), 0, 0.98),
                                'size': number(n.get('size', 14), 8, 48),
                                'color': color(n.get('color', '#263348')),
                                'bold': n.get('bold') is True})
    styles = data.get('cellStyles', {})
    if not isinstance(styles, dict) or len(styles) > 2400:
        raise ValueError('Invalid cell styles')
    p['cellStyles'] = {}
    for ref, s in styles.items():
        if not re.fullmatch(r'[A-L][1-9][0-9]{0,2}', ref) or not isinstance(s, dict):
            raise ValueError('Invalid cell style address')
        fmt = s.get('format', 'number')
        if fmt not in enums['numberFormat']:
            raise ValueError('Invalid cell number format')
        p['cellStyles'][ref] = {'format': fmt, 'bold': s.get('bold') is True,
                                'background': color(s.get('background', '#ffffff'))}
    return p
