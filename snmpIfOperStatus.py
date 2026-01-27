#!/opt/pyenv/versions/2.7.18/bin/python
# -*- encoding: utf-8 -*-
#
# version    : 1.1.1
# author     : shosaka@ossbn.co.jp
# created at : 2017.03.06
# updated at : 2026.01.27

from snmpTarget import SnmpTarget
from snmpTarget import SnmpNetworkException
#from remoteDebug import EMail
import traceback
import json
import os, sys
import logging, logging.handlers
from datetime import datetime
from zabbix_api import ZabbixAPI
import argparse


OID_IFDESCR = '1.3.6.1.2.1.2.2.1.2'
OID_IF_ADMIN_STATUS = '1.3.6.1.2.1.2.2.1.7'
OID_IF_OPER_STATUS = '1.3.6.1.2.1.2.2.1.8'
OID_IF_STATUS = OID_IF_OPER_STATUS
OID_IFX_ALIAS = '1.3.6.1.2.1.31.1.1.1.18'

IF_STATUS_UP = 1

ZBX_TRIGGER_PRIORITY_HIGH = 4
ZBX_STATUS_ENABLE = 0
ZBX_TRIGGER_PROBLEM = 1

ZBX_KEY_PATTERN = 'AUTO_HW_IF_STATUS'

def removePID(f):
    if os.path.isfile(f):
        os.remove(f)

def get_first_valuemap_by_name(**args):
    zabbix  = args['zabbix']
    name    = args['name']
    params = {
            'output': 'extend', # shorten (only id), refer, extend (all db fields)
            'search': {
                'name': name
                },
            #'limit': args.limit,
            }

    vms = zabbix.request(method='valuemap.get', params=params)
    valuemapid, name = None, None
    if len(vms) > 0:
        valuemapid  = vms[0]['valuemapid']
        name        = vms[0]['name']

    return valuemapid, name

def get_zabbix_if_auto_items(**args):
    hostname = args['hostname']
    params = {
            'output': ['name', 'status', 'snmp_oid', 'key_'],
            'selectTriggers':['description', 'status', 'value', 'lastchange', 'expression'],
            'search': {
                'key_': ZBX_KEY_PATTERN
                },
            'filter': {
                'host': hostname
                },
            'limit': 2500,
            }

    items = zabbix.request(method='item.get', params=params)

    ifitems = {}
    for item in items:
        itemid      = item['itemid']
        key_        = item['key_']
        name        = item['name']
        status      = item['status']
        snmp_oid    = item['snmp_oid']
        triggers    = item['triggers']
        ifitems[key_] = {
                'itemid': itemid,
                'name': name,
                'status': status,
                'key_': key_,
                'snmp_oid': snmp_oid,
                'triggers': triggers
                }

    return ifitems


def get_zabbix_host(**args):
    hostname = args['hostname']
    params = {
            'output': ['name'],
            'selectInterfaces': ['interfaceid','type','ip','dns','useip'],
            #'selectInterfaces': ['interfaceid','type'],
            'filter': {
                'host': [hostname]
                },
            }
    hosts = zabbix.request(method='host.get', params=params)
    zabbix_host = None
    for zh in hosts:
        hostid = zh['hostid']
        name   = zh['name']
        interfaces   = zh['interfaces']
        if name == hostname:
            zabbix_hostid = hostid
            for host_if in interfaces:
                if int(host_if['type']) == 2: # snmp if?
                    snmp_addr = None
                    if int(host_if['useip']) == 0: # dns
                        snmp_addr = host_if['dns']
                    else: # ip
                        snmp_addr = host_if['ip']
                    zabbix_host = {
                             'hostid': zabbix_hostid,
                             'interfaceid': host_if['interfaceid'],
                             'snmp_addr': snmp_addr
                             }
                    break
            break

    return zabbix_host

def create_if_auto_status(**args):
    # hostname
    hostname = args['hostname']
    # key
    key_ = args['key']
    # current if status
    ifstatus = args['ifstatus']
    # polling interval
    delay = 300
    if args.has_key('delay'):
        delay = args['delay']
    # count threshold
    count = 2
    if args.has_key('count'):
        count = args['count']
    # polling oid
    snmp_oid = OID_IF_STATUS + '.' + args['ifindex']
    # item and trigger name
    if_auto_name = args['ifdescr']

    # create item
    logger.info("creating new item %s on %s..." % (key_, hostname))
    params = {
            'hostid': args['hostid'],
            'name': if_auto_name,
            'key_': key_,
            'type': 20, # SNMPv1(1), SNMPv2(4)
            'value_type': 3, # numeric unsigned(3)
            'history': '7d',
            'trends': '30d',
            'interfaceid': args['interfaceid'],
            'delay': delay,
            'snmp_oid': snmp_oid,
#            'snmp_community': '{$SNMP_COMMUNITY}',
#            'valuemapid': ''
#            'delta': '1', # speed per second(1)
#            'formula': '8', # to bps
#            'multiplier': '1', # to bps
            }

    # add valuemapid
    if args.has_key('valuemapid'):
        params['valuemapid'] = args['valuemapid']

    # create item
    res = zabbix.request(method='item.create', params=params)

    # create trigger
    # major expression
    expression_major = ""
    exp_sign  = " = %s" % IF_STATUS_UP
    if ifstatus == IF_STATUS_UP: # current status is up?
        exp_sign  = " <> %s" % IF_STATUS_UP # not up(down) is alarm.

    i = 0
    for i in xrange(count):
        if i != 0:
            expression_major += " and "
        zbx_item_num = i + 1
        #expression_major += "{%s:%s.last(#%d)}%s" % (hostname, key_, zbx_item_num, exp_sign)
        expression_major += "last(/%s/%s,#%d)%s" % (hostname, key_, zbx_item_num, exp_sign)

    params = {
            'description': if_auto_name,
            'expression': expression_major,
            'priority': ZBX_TRIGGER_PRIORITY_HIGH,
            'comments': 'IFの状態が3時間変わらないまま本アラートが継続した場合、現在の状態を正として閾値を自動調整してアラートを復旧します。'
            }

    res = zabbix.request(method='trigger.create', params=params)


def update_snmp_oid(**args):
    params = {
            'itemid': args['itemid'],
            'snmp_oid': args['snmp_oid']
            }

    res = zabbix.request(method='item.update', params=params)


def update_item_name_with_trigger(**args):
    # update item name
    params = {
            'itemid': args['itemid'],
            'name': args['name']
            }

    res = zabbix.request(method='item.update', params=params)

    # update trigger description
    if args.has_key('triggers') and args['triggers']:
        triggers = args['triggers']
        for trigger in triggers:
            params = {
                    'triggerid': trigger['triggerid'],
                    'description': args['name']
                    }
            res = zabbix.request(method='trigger.update', params=params)

def update_trigger_expression(**args):
    # hostname
    hostname = args['hostname']
    # triggerid
    triggerid = args['triggerid']
    # key
    key_ = args['key']
    # current if status
    ifstatus = args['ifstatus']
    # count threshold
    count = 2
    if args.has_key('count'):
        delay = args['count']

    # major expression
    expression_major = ""
    exp_sign  = " = %s" % IF_STATUS_UP
    if ifstatus == IF_STATUS_UP: # current status is up?
        exp_sign  = " <> %s" % IF_STATUS_UP # not up(down) is alarm.

    i = 0
    for i in xrange(count):
        if i != 0:
            expression_major += " and "
        zbx_item_num = i + 1
        expression_major += "{%s:%s.last(#%d)}%s" % (hostname, key_, zbx_item_num, exp_sign)

    params = {
            'triggerid': triggerid,
            'expression': expression_major
            }

    res = zabbix.request(method='trigger.update', params=params)


def polling():

    try:
        community = args.community
        hostname = args.hostname

        # output for zabbix
        data = []
        json4zbx = {'data': data}

        # this scripts is used only snmp polliing.
        print json.dumps(json4zbx)
        sys.stdout.flush()
        sys.stderr.flush()

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

        pid = str(os.getpid())

        # get host info on zabbix. {'interfaceid': u'398', 'hostid': u'11032'}
        zabbix_host  =get_zabbix_host(hostname=hostname)
        if not zabbix_host:
            logger.error("snmp host %s is not found on zabbix server %s." % (hostname, args.zabbix))

        snmp_addr = zabbix_host['snmp_addr']

        logger.info("starting %s snmp if polling by pid %s..." % (hostname, pid))

        # variables
        iftable = {} # key: ifindex, value: values

        # start snmp polling.
        target = SnmpTarget(snmp_addr, community) # SNMP API

        # get ifdescr
        logger.info("polling ifdescr from %s by snmp..." % hostname)
        snmp_error, rows = target.nextWalk([OID_IFDESCR], 3, 2, 10000) # timeout(3), retries(2), maxRows(10000)
        for row in rows:
            ifindex   = str(row[0][0]).replace(OID_IFDESCR + '.', "")
            ifdescr   = str(row[0][1])
            iftable[ifindex] = {
                    'ifdescr': ifdescr,
                    'ifstatus': None,
                    'key_': '%s[%s]' % (ZBX_KEY_PATTERN, ifdescr)
                    }

        # get if status
        logger.info("polling ifstatus from %s by snmp..." % hostname)
        snmp_error, rows = target.nextWalk([OID_IF_STATUS], 3, 2, 10000) # timeout(3), retries(2), maxRows(10000)
        for row in rows:
            ifindex   = str(row[0][0]).replace(OID_IF_STATUS + '.', "")
            ifstatus  = int(row[0][1])
            if iftable.has_key(ifindex):
                iftable[ifindex]['ifstatus'] = ifstatus

        # get ifalias
        logger.info("polling ifalias from %s by snmp..." % hostname)
        snmp_error, rows = target.nextWalk([OID_IFX_ALIAS], 3, 2, 10000) # timeout(3), retries(2), maxRows(10000)
        for row in rows:
            ifindex   = str(row[0][0]).replace(OID_IFX_ALIAS + '.', "")
            ifalias   = str(row[0][1])
            if iftable.has_key(ifindex) and len(ifalias)>0:
                iftable[ifindex]['ifalias'] = ifalias

        # zabbix api polling.
        logger.info("starting zabbix item & trigger polling for %s by pid %s..." % (hostname, pid))
        # get interface auto status items on zabbix.
        ifitems = get_zabbix_if_auto_items(hostname=hostname)

        # get valuemap
        #valuemapid, name = get_first_valuemap_by_name(zabbix=zabbix, name='ifOperStatus')

        for ifindex, row in iftable.items():
            key_        = row['key_']
            ifdescr     = row['ifdescr']
            zbx_ifdescr = 'HW_' + ifdescr
            # update ifdescr by ifalias
            if row.has_key('ifalias'):
                zbx_ifdescr = zbx_ifdescr + ' ' + row['ifalias']
            ifstatus    = row['ifstatus']
            if ifitems.has_key(key_): # item already registered?
                itemid      = ifitems[key_]['itemid']
                name        = ifitems[key_]['name']
                item_status = int(ifitems[key_]['status'])
                snmp_oid    = ifitems[key_]['snmp_oid']
                triggers    = ifitems[key_]['triggers']
                # snmp_oid is correct?
                snmp_oid_should = OID_IF_STATUS + '.' + ifindex
                if not snmp_oid == snmp_oid_should:
                    logger.info("updating %s set snmp_oid = %s where host is %s..." % (name, snmp_oid_should, hostname))
                    update_snmp_oid(itemid=itemid, snmp_oid=snmp_oid_should)
                # item name is correct?
                if not name == zbx_ifdescr:
                    logger.info("updating %s set name = %s where host is %s..." % (name, zbx_ifdescr, hostname))
                    update_item_name_with_trigger(itemid=itemid, name=zbx_ifdescr, triggers=triggers)
                # enabled item?
                if item_status != ZBX_STATUS_ENABLE:
                    logger.info("item %s on %s is not enabled. ignored." % (name, hostname))
                    continue
                # current trigger value is problem?
                for trigger in triggers:
                    triggerid       = trigger['triggerid']
                    description     = trigger['description']
                    trigger_status  = int(trigger['status'])
                    trigger_value   = int(trigger['value'])
                    lastchange      = float(trigger['lastchange'])
                    if description == name:
                        if trigger_status == ZBX_STATUS_ENABLE and trigger_value == ZBX_TRIGGER_PROBLEM:
                        #if trigger_value == ZBX_TRIGGER_PROBLEM:
                            dt_now      = datetime.now()
                            dt_problem  = datetime.fromtimestamp(lastchange)
                            delta       = dt_now - dt_problem
                            if delta.total_seconds() > int(args.renew):
                                logger.info("updating trigger expression for %s on %s..." % (description, hostname))
                                update_trigger_expression(
                                        hostname    = hostname,
                                        triggerid   = triggerid,
                                        key         = key_,
                                        count       = int(args.count),
                                        ifstatus    = ifstatus)
                        break
            else:
                # create new item
                create_if_auto_status(
                        hostid      = zabbix_host['hostid'],
                        hostname    = hostname,
                        interfaceid = zabbix_host['interfaceid'],
                        key         = key_,
                        delay       = int(args.delay),
                        count       = int(args.count),
                        ifdescr     = zbx_ifdescr,
                        ifindex     = ifindex,
                        ifstatus    = ifstatus,
                        #valuemapid  = valuemapid
                        )
        logger.info("snmp if status auto discovery & setting for %s is completed." % hostname)
    except SnmpNetworkException as sne:
        logger.error("Oops! SnmpNetworkException caught:", exc_info=True)
    except Exception as e:
        logger.error("Oops! Exception caught:", exc_info=True)


if __name__ == '__main__':
    # parse options
    parser = argparse.ArgumentParser(description='coming soon?')
    parser.add_argument('-z', '-zserver', action="store", dest="zabbix", help="zabbix host", default="localhost")
    parser.add_argument('-u', '-zusername', action="store", dest="username", help="zabbix username", default="Admin")
    parser.add_argument('-p', '-zpassword', action="store", dest="password", help="zabbix password", default="zabbix")
    parser.add_argument('-com', '-community', action="store", dest="community", help="snmp community", default="public")
    parser.add_argument('-cnt', '-count', action="store", dest="count", help="count threshold", default=2)
    parser.add_argument('-d', '-delay', action="store", dest="delay", help="polling interval", default=300)
    parser.add_argument('-r', '-renew', action="store", dest="renew", help="renew expression seconds from problem", default=10800)
    parser.add_argument('-host', '-hostname', action="store", dest="hostname", help="zabbix host name", default="Your hostname")
    args = parser.parse_args()

    cdir = os.path.abspath(os.path.dirname(__file__))
    log_file = cdir + "/logs/auto.ifstatus.log"
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

    logger.info(sys.argv)

    # global variables
    zabbix_url = 'http://%s/zabbix/api_jsonrpc.php' % args.zabbix
    zabbix = ZabbixAPI(zabbix_url, username=args.username, password=args.password)

    polling()

