import os
import sys
import traceback
from urllib.parse import parse_qs, urlencode

# Ensure root directory is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

flask_app = None
import_error = None

try:
    from app import app as _flask_app
    flask_app = _flask_app
except Exception:
    import_error = traceback.format_exc()

def app(environ, start_response):
    global flask_app, import_error
    if flask_app is None:
        try:
            from app import app as _flask_app
            flask_app = _flask_app
        except Exception:
            import_error = traceback.format_exc()

    if flask_app is None:
        status = '500 Internal Server Error'
        response_headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        return [f"Question Paper Studio - Serverless Startup Error:\n\n{import_error}".encode('utf-8')]

    # Restore the original requested path from query string or headers
    raw_qs = environ.get('QUERY_STRING', '')
    qs = parse_qs(raw_qs, keep_blank_values=True)
    if '__path' in qs and qs['__path']:
        original_path = qs['__path'][0]
        if not original_path.startswith('/'):
            original_path = '/' + original_path
        environ['PATH_INFO'] = original_path
        del qs['__path']
        environ['QUERY_STRING'] = urlencode(qs, doseq=True)
    elif environ.get('HTTP_X_MATCHED_PATH'):
        environ['PATH_INFO'] = environ['HTTP_X_MATCHED_PATH']

    # Normalize entrypoint
    path = environ.get('PATH_INFO', '')
    if path in ['/api/index.py', '/api/index', '/api', '']:
        environ['PATH_INFO'] = '/'

    try:
        return flask_app(environ, start_response)
    except Exception as e:
        status = '500 Internal Server Error'
        tb = traceback.format_exc()
        response_headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        return [f"Question Paper Studio - Runtime Error:\n\n{tb}".encode('utf-8')]
