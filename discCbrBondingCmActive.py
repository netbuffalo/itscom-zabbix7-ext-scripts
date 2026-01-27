#!/opt/pyenv/versions/2.7.18/bin/python
# -*- encoding: utf-8 -*-
#
# version    : 1.0.1
# author     : shosaka@ossbn.co.jp
# created at : 2017.01.15
# updated at : 2026.01.23

#from remoteDebug import EMail
import traceback
import json
import os, sys
import hashlib
import time
import logging, logging.handlers
import sqlite3

def discover():
    try:
        host = args[1]
        cdir = os.path.abspath(os.path.dirname(__file__))
        db_file = 'cbr.cm.active.' + host + '.db'
        db_path = cdir + '/cache/' + db_file

        # output for zabbix
        data = []
        json4zbx = {'data': data}

        if os.path.isfile(db_path):
            with sqlite3.connect(db_path, isolation_level=None) as conn:
                cur = conn.cursor()
                cur.execute('SELECT IF_GROUP_DESCR FROM BONDING_CM_ACTIVE')
                result_set = cur.fetchall()
                for row in result_set:
                    row4zbx = {} # json row
                    row4zbx['{#IF_GROUP_DESCR}'] =  str(row[0])
                    data.append(row4zbx)

        print json.dumps(json4zbx)
    except Exception as e:
        logger.error("Oops! Exception caught:", exc_info=True)

if __name__ == '__main__':

    cdir = os.path.abspath(os.path.dirname(__file__))
    log_file = cdir + "/logs/disc.cbrbonding.cmactive.log"
    log_level = logging.ERROR
    if os.path.exists(cdir + '/logs/_INFO_'):
        log_level = logging.INFO
    if os.path.exists(cdir + '/logs/_DEBUG_'):
        log_level = logging.DEBUG

    # logging
    logger = logging.getLogger()
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')

    rfh = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=2000000, # MB
        backupCount=5
    )

    rfh.setLevel(log_level)
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)

    args = sys.argv
    logger.info(args)

    discover()

