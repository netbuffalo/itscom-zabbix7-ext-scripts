#!/opt/pyenv/versions/2.7.18/bin/python
# -*- encoding: utf-8 -*-
#
# version    : 1.1.0
# author     : shosaka@ossbn.co.jp
# created at : 2017.01.12
# updated at : 2026.01.23

from snmpTarget import SnmpTarget
from snmpTarget import SnmpNetworkException
#from remoteDebug import EMail
import traceback
import json
import os, sys
import hashlib
import atexit
import logging, logging.handlers
import sqlite3
from datetime import datetime


OID_IFDESCR = '1.3.6.1.2.1.2.2.1.2'
OID_DOCS_IF3_US_CHSET_CHLIST = '1.3.6.1.4.1.4491.2.1.20.1.22.1.2'
OID_CDX_CMTS_MTC_CM_REGISTERED = '1.3.6.1.4.1.9.9.116.1.7.1.1.4'
OID_CDX_IF_UP_CH_CM_REGISTERED = '1.3.6.1.4.1.9.9.116.1.4.1.1.5'

def removePID(f):
    if os.path.isfile(f):
        os.remove(f)

def polling():

    db_path = None

    try:
        community = args[1]
        host = args[2]
        #host_md5 = hashlib.md5(host).hexdigest()
        #db_file = 'cbr.cm.active.' + host_md5 + '.db'
        db_file = 'cbr.cm.active.' + host + '.db'
        db_path = cdir + '/cache/' + db_file
        #pid_path = cdir + '/run/cbr.cm.active.' + host_md5 + '.pid'
        pid_path = cdir + '/run/cbr.cm.active.' + host + '.pid'

        # output for zabbix
        data = []
        json4zbx = {'data': data}

        if os.path.isfile(db_path): # first discovery?
            # this scripts is used only snmp polliing. 
            print json.dumps(json4zbx)
        else:
            # first discovery. ouput empty data.
            print  json.dumps(json4zbx) # empty
            logger.debug(json4zbx)

            logger.info("starting first discovery for %s..." % host)
            # initialize host database
            with sqlite3.connect(db_path, isolation_level=None) as conn:
                cur = conn.cursor()
                # BONDING_CM_ACTIVE TABLE
                cur.execute('CREATE TABLE IF NOT EXISTS BONDING_CM_ACTIVE (BONDING_INDEX TEXT, IF_GROUP_DESCR TEXT, MACLAYER_DESCR TEXT, CM_ACTIVE_BONDED INTEGER, CM_ACTIVE_NON_BONDED INTEGER, SNMP_STATUS INTEGER DEFAULT 0, POLLED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
                # UP_CH_CM_ACTIVE TABLE
                cur.execute('CREATE TABLE IF NOT EXISTS UP_CH_CM_ACTIVE (BONDING_INDEX TEXT, IF_INDEX INTEGER, IF_DESCR TEXT, CM_ACTIVE INTEGER, SNMP_STATUS INTEGER DEFAULT 0, POLLED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')

        sys.stdout.flush()
        sys.stderr.flush()

        if os.path.isfile(pid_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(pid_path))
            nowtime = datetime.now()
            deltatime = nowtime - mtime
            delta_in_sec = deltatime.total_seconds()
            if delta_in_sec > 1200:
                logger.warn("force remove pid file for cbr(%s) ." % host)
                removePID(pid_path)
            else:
                logger.warn("cbr(%s) polling daemon already running(%d). exiting..." % (host, delta_in_sec))
                sys.exit(0)
            #raise(Exception(message % host))

        pid = os.fork()
        if pid > 0: # not polling daemon?
            # exit zabbix discovery session and run polling daemon.
            sys.exit(0) # exit zabbix session.

        # END OF ZABBIX LOW LEVEL DISCOVERY

        ###########################################################
        #   start child session. polling daemon code goes here.   #
        ###########################################################

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # redirect standard file descriptors
        si = file('/dev/null', 'r')
        so = file('/dev/null', 'a+')
        se = file('/dev/null', 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(removePID, pid_path) # remove pid file when child session die.
        pid = str(os.getpid())
        file(pid_path,'w+').write("%s\n" % pid)

        logger.info("starting cbr(%s) snmp polling by pid %s..." % (host, pid))

        cbr_cm_active_total = {}
        cbr_not_bonded_upstreams = [] # not bonded upstreams {active: x, ifindex: x, ifdescr: x}
        upstream2idx_maclayer_tcsid = {}

        # select cache data to reduce snmp polling.
        cache_maclayer_ifdescr = {}
        cache_upstream_ifdescr = {}
        with sqlite3.connect(db_path, isolation_level=None) as conn:
            cur = conn.cursor()
            cur.execute('SELECT BONDING_INDEX, MACLAYER_DESCR FROM BONDING_CM_ACTIVE')
            result_set = cur.fetchall()
            for row in result_set: # row -> (u'1195.61440', u'Cable6/0/2')
                idx_maclayer_tcsid = str(row[0])
                maclayer_ifindex = idx_maclayer_tcsid.split('.')[0]
                cache_maclayer_ifdescr[maclayer_ifindex] = row[1]

            cur.execute('SELECT IF_INDEX, IF_DESCR FROM UP_CH_CM_ACTIVE')
            result_set = cur.fetchall()
            for row in result_set:
                cache_upstream_ifdescr[str(row[0])] = row[1] # (u'192020', u'Cable6/0/2-upstream0')

        # start snmp polling.
        target = SnmpTarget(host, community) # SNMP API

        # get all bonding channel lists
        logger.info("getting docsIf3UsChSetChList from %s..." % host)
        snmp_error, rows = target.nextWalk([OID_DOCS_IF3_US_CHSET_CHLIST], 3, 2, 10000) # timeout(3), retries(2), maxRows(10000)
        for row in rows:
            idx_maclayer_tcsid = (str(row[0][0])).replace(OID_DOCS_IF3_US_CHSET_CHLIST + '.', "")
            chlist_in_hex = row[0][1] # OctetString(hexValue='01020304'), OctetString(hexValue='0a0b0c')
            # generate upstream names
            bonding = {}
            maclayer_ifindex,tcs_id = idx_maclayer_tcsid.split('.')
            bonding['maclayer_ifindex'] = maclayer_ifindex
            # convert string of hexadecimal values to list of integers.
            channels = map(ord, chlist_in_hex) #[1, 2, 3, 4]
            #bonding['channels'] = [ ch - 1 for ch in chlist ] #[0, 1, 2, 3]
            bonding['channels'] = channels
            # default bonded cm actve
            bonding['cm_active_bonded'] = 0
            # default non bonded cm actve
            bonding['cm_active_nonbonded'] = 0
            # default upstream channel interfaces
            bonding['up_ch_cm_active'] = []

            cbr_cm_active_total[idx_maclayer_tcsid] = bonding

        # get all cdx bonding cm registered
        logger.info("getting cdxCmtsMtcCmRegistered from %s..." % host)
        snmp_error, rows = target.nextWalk([OID_CDX_CMTS_MTC_CM_REGISTERED], 3, 2, 10000) # timeout(3), retries(2), maxRows(10000)
        for row in rows:
            idx_maclayer_tcsid = (str(row[0][0])).replace(OID_CDX_CMTS_MTC_CM_REGISTERED + '.', "")
            cm_active_bonded = int(row[0][1])
            if cbr_cm_active_total.has_key(idx_maclayer_tcsid):
                bonding = cbr_cm_active_total[idx_maclayer_tcsid]
                bonding['cm_active_bonded'] = bonding['cm_active_bonded'] + cm_active_bonded
            else:
                maclayer_ifindex,tcs_id = idx_maclayer_tcsid.split('.')
                if int(tcs_id) in [256, 512, 1024, 2048]:
                    bonding_tcs_id = 3840
                    bonding_key_set = "%s.%s" % (maclayer_ifindex, bonding_tcs_id)
                    if cbr_cm_active_total.has_key(bonding_key_set):
                        logger.warn("cm active using single us(%s) that compose bonding group(%s.3840) was found on %s." % (tcs_id, maclayer_ifindex, host))
                        bonding = cbr_cm_active_total[bonding_key_set]
                        bonding['cm_active_bonded'] = bonding['cm_active_bonded'] + cm_active_bonded
                elif int(tcs_id) in [4096, 8192, 16384, 32768]:
                    bonding_tcs_id = 61440
                    bonding_key_set = "%s.%s" % (maclayer_ifindex, bonding_tcs_id)
                    if cbr_cm_active_total.has_key(bonding_key_set):
                        logger.warn("cm active using single us(%s) that compose bonding group(%s.61440) was found on %s." % (tcs_id, maclayer_ifindex, host))
                        bonding = cbr_cm_active_total[bonding_key_set]
                        bonding['cm_active_bonded'] = bonding['cm_active_bonded'] + cm_active_bonded

        # get all cdx bonding cm registered
        logger.info("generating bonded item name for %s..." % host)
        maclayer2ifdescr = {}
        for idx_maclayer_tcsid, bonding in cbr_cm_active_total.items():
            maclayer_ifindex = bonding['maclayer_ifindex']
            if not maclayer2ifdescr.has_key(maclayer_ifindex): # maclayer description is already resolved?
                if cache_maclayer_ifdescr.has_key(maclayer_ifindex):
                    # resolve maclayer if description by database cache.
                    maclayer2ifdescr[maclayer_ifindex] = cache_maclayer_ifdescr[maclayer_ifindex]
                else:
                    # resolve maclayer if description by snmp polling.
                    snmp_error, varbinds = target.get([OID_IFDESCR + '.' + maclayer_ifindex], 3, 2) # oids, timeout, retries
                    maclayer2ifdescr[maclayer_ifindex] = str(varbinds[0][1])
            bonding['maclayer_ifdescr'] = maclayer2ifdescr[maclayer_ifindex]
            channels = bonding['channels']
            # generate bonded name: Cable6/0/2-upstream4-7
            us_min = str(channels[0]-1)
            us_max = str(channels[len(channels) - 1] - 1)
            bonding['if_group_descr'] = bonding['maclayer_ifdescr'] + '-upstream' + us_min + '-' + us_max
            # genrate upstream ifdescr to bonding id mappings
            for ch in channels:
                us = bonding['maclayer_ifdescr'] + '-upstream' + str(ch - 1)
                if upstream2idx_maclayer_tcsid.has_key(us):
                    logger.debug("duplicate %s for bonding ch set %s" % (us, str(channels)))
                    # duplicate upstream description entry between different maclayer&tcsid!
                    if bonding.has_key('cm_active_bonded') and bonding['cm_active_bonded'] > 0: # has bonded cm?
                        logger.debug("overwrite %s for bonding ch set %s" % (us, str(channels)))
                        # overwrite idx_maclayer_tcsid
                        upstream2idx_maclayer_tcsid[us] = idx_maclayer_tcsid
                else:
                    upstream2idx_maclayer_tcsid[us] = idx_maclayer_tcsid

        # get all cdxIfUpChannelCmRegistered
        logger.info("getting cdxIfUpChannelCmRegistered from %s..." % host)
        snmp_error, rows = target.nextWalk([OID_CDX_IF_UP_CH_CM_REGISTERED], 3, 2, 10000) # timeout(3), retries(2), maxRows(10000)
        for row in rows:
            us_ifindex = (str(row[0][0])).replace(OID_CDX_IF_UP_CH_CM_REGISTERED + '.', "")
            up_ch_cm_registered = int(row[0][1])
            snmp_us_ifdescr = None
            if cache_upstream_ifdescr.has_key(us_ifindex):
                snmp_us_ifdescr = cache_upstream_ifdescr[us_ifindex]
            else:
                snmp_error, varbinds = target.get([OID_IFDESCR + '.' + us_ifindex], 3, 2) # oids, timeout, retries
                snmp_us_ifdescr = str(varbinds[0][1])

            logger.debug("cdxIfUpChannelCmRegistered: %s on %s" % (up_ch_cm_registered, snmp_us_ifdescr))

            # find bonding id(maclayer-ifindex & tcsid) by upstream ifdescr.
            if upstream2idx_maclayer_tcsid.has_key(snmp_us_ifdescr): # this upstream is bonding interface?
                idx_maclayer_tcsid = upstream2idx_maclayer_tcsid[snmp_us_ifdescr]
                bonding = cbr_cm_active_total[idx_maclayer_tcsid]
                # store & calc non bonded cm active total.
                bonding['cm_active_nonbonded'] = bonding['cm_active_nonbonded'] + up_ch_cm_registered
                bonding['up_ch_cm_active'].append({'ifdescr': snmp_us_ifdescr, 'active': up_ch_cm_registered, 'ifindex': us_ifindex})
            else:
                # not bonding upstream?
                logger.warn("maclayer ifindex and tcsid not found for %s (%s) on %s. not bonded?" % (snmp_us_ifdescr, us_ifindex, host))
                cbr_not_bonded_upstreams.append({'ifdescr': snmp_us_ifdescr, 'active': up_ch_cm_registered, 'ifindex': us_ifindex})

        #logger.info(cbr_cm_active_total)
        #for k,v in cbr_cm_active_total.items():
        #    logger.info(v)

        # save summary data to use item query.
        logger.info("sqlite3: saving cm active data for %s on %s ..." % (host, db_file))
        with sqlite3.connect(db_path, isolation_level=None) as conn:
            cur = conn.cursor()
            # DELETE & INSERT rows
            cur.execute('begin')
            cur.execute('DELETE FROM BONDING_CM_ACTIVE')
            cur.execute('DELETE FROM UP_CH_CM_ACTIVE')
            # bonding
            for idx_maclayer_tcsid, bonding in cbr_cm_active_total.items():
                # INSERT INTO BONDING_CM_ACTIVE
                cur.execute(
                        'INSERT INTO BONDING_CM_ACTIVE (BONDING_INDEX, IF_GROUP_DESCR, MACLAYER_DESCR, CM_ACTIVE_BONDED, CM_ACTIVE_NON_BONDED) VALUES (?, ?, ?, ?, ?)',
                        (idx_maclayer_tcsid, bonding['if_group_descr'], bonding['maclayer_ifdescr'], bonding['cm_active_bonded'], bonding['cm_active_nonbonded'])
                        )
                # INSERT INTO UP_CH_CM_ACTIVE
                upstreams = bonding['up_ch_cm_active']
                for up in upstreams:
                    cur.execute(
                            'INSERT INTO UP_CH_CM_ACTIVE (BONDING_INDEX, IF_INDEX, IF_DESCR, CM_ACTIVE) VALUES (?, ?, ?, ?)',
                            (idx_maclayer_tcsid, up['ifindex'], up['ifdescr'], up['active'])
                            )
            # not bonding upstreams
            for not_bonding_up in cbr_not_bonded_upstreams:
                not_bonding_maclayer_tcsid = '0.0' # dummy bonding id
                cur.execute(
                        'INSERT INTO UP_CH_CM_ACTIVE (BONDING_INDEX, IF_INDEX, IF_DESCR, CM_ACTIVE) VALUES (?, ?, ?, ?)',
                        (not_bonding_maclayer_tcsid, not_bonding_up['ifindex'], not_bonding_up['ifdescr'], not_bonding_up['active'])
                        )

            cur.execute('commit')

        logger.info("one polling cycle for cbr(%s) was finished. pid: %s" % (host, pid))
    except SnmpNetworkException as sne:
        logger.error("Oops! SnmpNetworkException caught:", exc_info=True)
        #logger.info("sqlite3: deleting cmts %s cm active summary..." % host)
        logger.info("sqlite3: updating cmts %s cm active summary set snmp status to error(1)..." % host)
        try:
            with sqlite3.connect(db_path, isolation_level=None) as conn:
                # delete all rows to be item polling failed.
                cur = conn.cursor()
                cur.execute('begin')
                #cur.execute('DELETE FROM BONDING_CM_ACTIVE')
                #cur.execute('DELETE FROM UP_CH_CM_ACTIVE')
                cur.execute('UPDATE BONDING_CM_ACTIVE SET SNMP_STATUS=1')
                cur.execute('UPDATE UP_CH_CM_ACTIVE SET SNMP_STATUS=1')
                cur.execute('commit')
                logger.info("sqlite3: %s success" % host)
        except:
            logger.error("Oops! Exception caught:", exc_info=True)
    except Exception as e:
        logger.error("Oops! Exception caught:", exc_info=True)


if __name__ == '__main__':

    cdir = os.path.abspath(os.path.dirname(__file__))
    log_file = cdir + "/logs/snmp.cbrcmts.cmactive.log"
    #log_level = logging.ERROR
    log_level = logging.WARN
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

    polling()

