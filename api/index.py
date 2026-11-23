import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app as flask_app

class VercelPathFix:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        matched = environ.get('HTTP_X_MATCHED_PATH')
        if matched and matched not in ['/api/index.py', '/api/index']:
            environ['PATH_INFO'] = matched
        else:
            path = environ.get('PATH_INFO', '')
            if path in ['/api/index.py', '/api/index', '']:
                environ['PATH_INFO'] = '/'
            elif path.startswith('/api/index.py/'):
                environ['PATH_INFO'] = path[len('/api/index.py'):]
            elif path.startswith('/api/index/'):
                environ['PATH_INFO'] = path[len('/api/index'):]

        return self.app(environ, start_response)

app = VercelPathFix(flask_app)
