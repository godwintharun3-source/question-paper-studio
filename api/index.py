import os
import sys
import traceback

# Ensure root directory is in sys.path for Vercel serverless functions
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app as flask_app

def app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    # Strip rewrite prefixes if Vercel routed to /api or /api/index
    for prefix in ['/api/index.py', '/api/index', '/api']:
        if path == prefix:
            environ['PATH_INFO'] = '/'
            break
        elif path.startswith(prefix + '/'):
            environ['PATH_INFO'] = path[len(prefix):]
            break
    try:
        return flask_app(environ, start_response)
    except Exception as e:
        status = '500 Internal Server Error'
        tb = traceback.format_exc()
        response_headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        return [f"Vercel WSGI Handler Error: {e}\n\n{tb}".encode('utf-8')]
