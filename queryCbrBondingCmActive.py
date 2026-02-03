#!/opt/pyenv/versions/2.7.18/bin/python
# -*- encoding: utf-8 -*-
#
# version    : 1.0.0
# author     : shosaka@ossbn.co.jp
# created at : 2017.01.15
# updated at : 2026.02.02

import traceback
import json
import os, sys
import hashlib
import time
import logging, logging.handlers
import sqlite3

def query():
    try:
        host = args[1]
        if_group_descr = args[2]
        bond_type = args[3]
        sql = None
        if bond_type == 'BONDED':
            sql = 'SELECT CM_ACTIVE_BONDED FROM BONDING_CM_ACTIVE WHERE SNMP_STATUS = 0 and IF_GROUP_DESCR = ?'
        elif bond_type == 'NON_BONDED':
            sql = 'SELECT CM_ACTIVE_NON_BONDED FROM BONDING_CM_ACTIVE WHERE SNMP_STATUS = 0 and IF_GROUP_DESCR = ?'

        cdir = os.path.abspath(os.path.dirname(__file__))
        db_file = 'cbr.cm.active.' + host + '.db'
        db_path = cdir + '/cache/' + db_file

        cm_active = None
        if os.path.isfile(db_path):
            with sqlite3.connect(db_path, isolation_level=None) as conn:
                cur = conn.cursor()
                #cur.execute('SELECT CM_ACTIVE_BONDED FROM BONDING_CM_ACTIVE WHERE IF_GROUP_DESCR = ?', (if_group_desc,))
                cur.execute(sql, (if_group_descr,))
                cm_active = cur.fetchone()
            if cm_active:
                print cm_active[0]
                logger.info("%s bonded cm active on %s: %s" % (if_group_descr, host, cm_active[0]))
            else:
                print "None (no data)"
                logger.warn("cbr bonding interface group not found: %s on %s" % (if_group_descr, host))
        else:
            raise(Exception("SqliteFileNotFound: %s for %s" % (db_path, host)))
    except Exception as e:
        logger.error("Oops! Exception caught:", exc_info=True)

if __name__ == '__main__':

    cdir = os.path.abspath(os.path.dirname(__file__))
    log_file = cdir + "/logs/query.cbrbonding.cmactive.log"
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

    query()

