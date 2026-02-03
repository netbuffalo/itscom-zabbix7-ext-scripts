#!/opt/pyenv/versions/2.7.18/bin/python
# -*- coding: utf-8 -*-

import argparse
import os, sys
import logging, logging.handlers
import json,urllib2

def getLogger(**args):
    path = os.path.abspath(os.path.dirname(__file__))
    if 'path' in args and args['path']:
        path = args['path']

    _dir = '%s/logs' % path
    if not os.path.exists(_dir):
        os.mkdir(_dir)

    # logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) # default logging level
    formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    rfh = logging.handlers.RotatingFileHandler(
        filename='%s/%s' % (_dir, args['name']),
        maxBytes=2000000, # MB
        backupCount=5
    )

    rfh.setLevel(logging.INFO)
    rfh.setFormatter(formatter)
    logger.addHandler(rfh)

    if 'debug' in args and args['debug']:
        # override logging level
        rfh.setLevel(logging.DEBUG)
        # add standard out
        stdout = logging.StreamHandler()
        stdout.setLevel(logging.DEBUG)
        stdout.setFormatter(formatter)
        logger.addHandler(stdout)

    return logger

# C4/uBR/cBRボンディングなしのポート単位の形式
# <ifname sample>
#   Resource_cable-upstream 1/23.0_CM_Active
#   Resource_cable-upstream 2/0.0_CM_Active
def make_ifdata_per_port(mdifindex, tcsid, upstreams):
    data = []

    if len(upstreams) == 1:
        for upstream in upstreams:

            name = "Resource_" + upstream + "_CM_Active"
            row = {}
            row['{#NETWORK}'] = name.replace('  ', ' ')
            row['{#KEYS}'] = str(mdifindex) + ":" + str(tcsid)
            data.append(row)

    return data

# C4 ボンディングあり
# <ifname sample>
#   Resource_cable-upstream 1_U0.0-3.0_TOTAL_CM_Active
#   Resource_cable-upstream 1_U4.0-7.0_TOTAL_CM_Active
def make_ifdata_bonded(mdifindex, tcsid, upstreams, jponse):
    data = []

    if len(upstreams) <= 1:
        return data;

    ifname = ''
    portNumber = []
    
    keyList = []
    keyList.append(str(mdifindex) + ":" + str(tcsid))

    for upstream in upstreams:
        mdif, tcs = getId(jponse, upstream)
        keyList.append(str(mdif) + ":" + str(tcs))

        ifname = upstream.split('/')

        if len(ifname) == 2:

            portNumber.append(float(ifname[1]))

    name = "Resource_" + ifname[0] + "_U" + str(min(portNumber)) + "-" + str(max(portNumber)) + "_TOTAL_CM_Active"
    name = name.replace('  ', ' ')
    row = {}
    row['{#NETWORK}'] = name

    # keyがオール0:0のデータはappendしない
    for key in keyList:
        if key != '0:0':
            keys = ','.join(keyList)
            row['{#KEYS}'] = keys
            data.append(row)
            break;

    return data


# cBR Bonded/NonBondedのデータ作成
# <生成されるアイテム名サンプル>
#   Resource_Cable2/0/3-upstream0-3_CM_Active_Bonded
#   Resource_Cable2/0/3-upstream0-3_CM_Active_NonBonded
def make_cbr_ifdata_bonded(mdifindex, tcsid, upstreams, jponse):
    data = []

    # cbr
    if len(upstreams) > 1:
        ifname = ''
        portNumber = []
        keyList = []
        for upstream in upstreams:

            # nonbonded用
            mdif, tcs = getId(jponse, upstream)
            keyList.append(str(mdif) + ":" + str(tcs))
            keys = ','.join(keyList)


            if ifname == '':
                ifname = upstream[:upstream.find('upstream') + 8]
            portNumber.append(upstream[upstream.find('upstream') + 8:])

        name = ifname  + min(portNumber) + "-" + max(portNumber)
        name = name.replace('  ', ' ')

        row = {}
        row['{#NETWORK}'] = name
        row['{#KEYS}'] = str(mdifindex) + ":" + str(tcsid)
        # row['{#NETWORK_NONBONDED}'] = nameNonBonded
        row['{#KEYS_NONBONDED}'] = '0:0'

        # nonbonded用
        # keyがオール0:0のデータの場合は、デフォルト0:0とする
        for key in keyList:
            if key != '0:0':
                keys = ','.join(keyList)
                row['{#KEYS_NONBONDED}'] = keys
                break;

        data.append(row)

    return data

# cBR tocal cm active データ作成
# <ifname sample>
#   Resource_Total_CM_Active_Cable1/0/0
def make_cbr_ifdata_total_cm_active(jponse):
    data = []

    for j in jponse:
        upstreams = j['upstreams']
        ifname = ''
        for upstream in upstreams:
            if ifname == '':
                ifname = upstream[:upstream.find('-')]

            keyList = getId_beginWithIfName(jponse, ifname)
            keys = ','.join(keyList)

            name = "Resource_Total_CM_Active_" + ifname
            name = name.replace('  ', ' ')

            row = {}
            row['{#NETWORK}'] = name
            row['{#KEYS}'] = keys

            # 同じIF名が複数回出てくるため、生成したIF名が存在している場合はappendしないようにする
            isNotExist = True
            for d in data:
                if d['{#NETWORK}'] == name:
                    isNotExist = False
            
            if isNotExist:
                data.append(row)
    return data

# ifNameから名称が同じポート単位のmdifindexとtcsidを取得する
# 存在しない場合は0,0を返す
# 検索キーはCable2/0/3-upstream
def getId(jponse, searchName):
    for j in jponse:
        mdifindex = j['mdifindex']
        tcsid = j['tcsid']
        upstreams = j['upstreams']
        for upstream in upstreams:

            if len(upstreams) > 1:
                continue

            if upstream == searchName:

                return mdifindex, tcsid

    return 0, 0

# ifNameから名称が同じポート単位のmdifindexとtcsidを取得する
# 存在しない場合は0,0を返す
# 検索キーはCable1/0/0の形式
def getId_beginWithIfName(jponse, searchName):
    keyList = []
    for j in jponse:
        mdifindex = j['mdifindex']
        tcsid = j['tcsid']
        upstreams = j['upstreams']
        for upstream in upstreams:

            if upstream.find(searchName) == -1:
                continue

            if str(mdifindex) + ":" + str(tcsid) in keyList:
                continue

            keyList.append(str(mdifindex) + ":" + str(tcsid))

    if len(keyList) == 0:
        keyList = ["0:0"]

    return keyList

def main():
    # parse options
    parser = argparse.ArgumentParser(description='coming soon?')
    parser.add_argument('-s', '--server', action="store", dest="server", help="api server", default="localhost")
    parser.add_argument('-p', '--port', action="store", dest="port", help="api server port", default="9090")
    parser.add_argument('-H', '--host', action="store", dest="hostname", help="target hostname", default="")
    parser.add_argument('-c', '--cbr', action="store_true", dest="cbr", help="is cbr", default=False)
    parser.add_argument('-b', '--cbrbonded', action="store_true", dest="cbr_bonded", help="is cbr bonded and nonbonded", default=False)
    parser.add_argument('-t', '--cbrtotal', action="store_true", dest="cbr_total", help="is cbr cm active total", default=False)
    parser.add_argument('-n', '--net', action="store_true", dest="c4_net", help="is c4 net", default=False)

    parser.add_argument('-d', '--debug', action="store_true", dest="debug", help="run as debug mode", default=False)
    args = parser.parse_args()

    # home dir (script dir)
    home = os.path.abspath(os.path.dirname(__file__))

    # global logger
    global log
    logfile = '%s.log' % os.path.basename(__file__)
    log = getLogger(path=home, name=logfile, debug=args.debug)

    try:
        log.info('starting...')

        data = []
        lld = {'data': data}

        url = "http://%s:%s/api/v1/iface/%s" % (args.server, args.port, args.hostname)
        response = urllib2.urlopen(url)
        jponse = json.loads(response.read())

        if args.cbr_total:
            data.extend(make_cbr_ifdata_total_cm_active(jponse))
        else:
            for j in jponse:
                mdifindex = j['mdifindex']
                tcsid = j['tcsid']
                upstreams = j['upstreams']

                if args.cbr:
                    data.extend(make_ifdata_per_port(mdifindex, tcsid, upstreams))
                elif args.cbr_bonded:
                    data.extend(make_cbr_ifdata_bonded(mdifindex, tcsid, upstreams, jponse))
                elif args.c4_net:
                    data.extend(make_ifdata_bonded(mdifindex, tcsid, upstreams, jponse))
                else:
                    data.extend(make_ifdata_per_port(mdifindex, tcsid, upstreams))

        # output for zabbix LLD
        print(json.dumps(lld))
    except Exception as e:
        log.error("Oops! Exception caught:", exc_info=True)

if __name__ == '__main__':
    main()

