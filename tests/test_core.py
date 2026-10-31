import concurrent.futures
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from plotcraft.formulas import Sheet
from plotcraft.model import default_project, validate
from plotcraft.render import render
from plotcraft.server import Handler


class FormulaTests(unittest.TestCase):
    def test_dependencies_and_functions(self):
        s = Sheet([['2', '3', '=SUM(A1:B2)'], ['4', '6', '=ROUND(AVERAGE(A1:B2)/3,2)'],
                   ['=MAX(A1:B2)-MIN(A1:B2)', '=COUNT(A1:B2)', '=A3*B3+10%3']])
        values, errors = s.calculate()
        self.assertEqual(errors, {})
        self.assertEqual(values[0][2], 15)
        self.assertEqual(values[1][2], 1.25)
        self.assertEqual(values[2], [4, 4, 17])

    def test_cycles_propagate(self):
        _, errors = Sheet([['=B1', '=A1', '=SUM(A1:B1)']]).calculate()
        self.assertEqual(set(errors), {'A1', 'B1', 'C1'})
        self.assertIn('Circular', errors['A1'])

    def test_rejects_code_and_bad_math(self):
        for raw in ['=__import__("os").system("id")', '=2**100000', '=1/0', '=A999', '=SUM(A1:Z99999999)', '=ROUND(2,1000)', '=[1,2]', '=True', '=1e100']:
            with self.subTest(raw=raw):
                self.assertIn('A1', Sheet([[raw]]).calculate()[1])

    def test_blank_and_text_ranges(self):
        values, errors = Sheet([['', 'hello', '=SUM(A1:B1)', '=COUNT(A1:B1)']]).calculate()
        self.assertFalse(errors)
        self.assertEqual(values[0][2:], [0, 1])

    def test_dependency_depth_bounded(self):
        cells = [[f'=A{i+2}'] for i in range(100)] + [['1']]
        self.assertTrue(Sheet(cells).calculate()[1])


class RenderTests(unittest.TestCase):
    def test_all_types_and_formats(self):
        for kind in ['bar', 'horizontal', 'line', 'area', 'stacked', 'scatter', 'donut']:
            p = default_project()
            p['chart']['type'] = kind
            p['chart']['labels'] = True
            if kind == 'scatter':
                for i, row in enumerate(p['cells']):
                    row[0] = str(i + 1)
            for fmt, signature in [('svg', b'<?xml'), ('png', b'\x89PNG'), ('pdf', b'%PDF')]:
                with self.subTest(kind=kind, fmt=fmt):
                    result, _, errors = render(p, fmt)
                    self.assertEqual(errors, {})
                    self.assertTrue(result.startswith(signature))
                    if fmt == 'svg':
                        self.assertIn(b'Built one month at a time.', result)

    def test_errors_block_export(self):
        p = default_project()
        p['cells'][0][1] = '=B1'
        result, _, errors = render(p)
        self.assertIsNone(result)
        self.assertIn('B1', errors)

    def test_donut_scatter_constraints(self):
        p = default_project()
        p['chart']['type'] = 'scatter'
        self.assertIn('chart', render(p)[2])
        p['chart']['type'] = 'donut'
        p['cells'][0][1] = '-2'
        self.assertIn('chart', render(p)[2])

    def test_concurrent_renders(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: render(default_project())[0], range(4)))
        self.assertTrue(all(x.startswith(b'<?xml') for x in results))

    def test_literal_text(self):
        p = default_project()
        p['chart']['title'] = '<script>alert(1)</script> $not math$'
        result = render(p)[0]
        self.assertNotIn(b'<script>', result)
        self.assertIn(b'&lt;script&gt;', result)

    def test_validation_limits(self):
        for key, value in [('width', 90000), ('opacity', float('nan')), ('colors', ['red']), ('font', '/etc/passwd'), ('series', [1, 1])]:
            p = default_project()
            p['chart'][key] = value
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError)):
                validate(p)
        p = default_project()
        p['cells'] *= 40
        with self.assertRaises(ValueError):
            validate(p)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, payload=None, headers=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.url + path, data=data, headers=headers or {'Content-Type': 'application/json'})
        return urllib.request.urlopen(request)

    def test_static_and_health(self):
        self.assertIn(b'Plotcraft', self.request('/').read())
        self.assertEqual(json.load(self.request('/api/health'))['status'], 'ok')
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/../server.py')
        self.assertEqual(error.exception.code, 404)

    def test_roundtrip_and_export(self):
        p = json.load(self.request('/api/default'))
        self.assertEqual(json.load(self.request('/api/validate', p)), p)
        result = json.load(self.request('/api/render', {'project': p}))
        self.assertEqual(result['values'][5][1], 88)
        self.assertIn('<svg', result['svg'])
        self.assertTrue(self.request('/api/export', {'project': p, 'format': 'png'}).read().startswith(b'\x89PNG'))

    def test_csv_quoted_unicode(self):
        p = json.load(self.request('/api/csv', {'csv': '\ufeffLabel,Value\r\n"Hello, SG",42\r\n你好,7'}))
        self.assertEqual(p['cells'], [['Hello, SG', '42'], ['你好', '7']])

    def test_invalid_requests_and_origin(self):
        for path, payload in [('/api/render', {'project': {}}), ('/api/validate', {'version': 1}), ('/api/csv', {'csv': 'A,B\n1,2,3'})]:
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                self.request(path, payload)
            self.assertEqual(error.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/render', {}, {'Content-Type': 'application/json', 'Origin': 'https://evil.invalid'})
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/', headers={'Host': 'evil.invalid'})
        self.assertEqual(error.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
