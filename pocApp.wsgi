activate_this = '/poc/flask/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/poc/app/")

from app import app
