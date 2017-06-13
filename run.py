#!flask/bin/python
import logging
from datetime import datetime
from app import app

if __name__ == '__main__':
 hdlr = logging.FileHandler('/poc/app/server.log')
 formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
 hdlr.setFormatter(formatter)
 app.logger.addHandler(hdlr)
 app.logger.setLevel(logging.INFO)
 app.run(host='0.0.0.0', port=8080, debug=True)
