import os
import sys
import traceback
from urllib.parse import parse_qs, urlencode

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app as flask_app

class VercelPathFix:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        raw_qs = environ.get('QUERY_STRING', '')
        qs = parse_qs(raw_qs, keep_blank_values=True)
        
        if '__path' in qs and qs['__path']:
            orig_path = qs['__path'][0]
            if not orig_path.startswith('/'):
                orig_path = '/' + orig_path
            environ['PATH_INFO'] = orig_path
            del qs['__path']
            environ['QUERY_STRING'] = urlencode(qs, doseq=True)
        elif environ.get('HTTP_X_MATCHED_PATH') and environ.get('HTTP_X_MATCHED_PATH') not in ['/api/index.py', '/api/index']:
            environ['PATH_INFO'] = environ['HTTP_X_MATCHED_PATH']
        else:
            path = environ.get('PATH_INFO', '')
            if path in ['/api/index.py', '/api/index', '']:
                environ['PATH_INFO'] = '/'
            elif path.startswith('/api/index.py/'):
                environ['PATH_INFO'] = path[len('/api/index.py'):]
            elif path.startswith('/api/index/'):
                environ['PATH_INFO'] = path[len('/api/index'):]

        try:
            return self.app(environ, start_response)
        except Exception as e:
            status = '500 Internal Server Error'
            tb = traceback.format_exc()
            response_headers = [('Content-Type', 'text/plain; charset=utf-8')]
            start_response(status, response_headers)
            return [f"Question Paper Studio - Vercel WSGI Handler Error:\n\n{tb}".encode('utf-8')]

app = VercelPathFix(flask_app)
