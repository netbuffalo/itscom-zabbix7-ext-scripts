#!/opt/pyenv/versions/2.7.18/bin/python
# -*- coding: utf-8 -*-

############################################
#オプション解析
############################################
def func_get_options():
    #モジュール定義
    from optparse import OptionParser

    #パーサー呼び出し
    parser = OptionParser()

    #オプション追加
    parser.add_option('-H', '--host', action='store', dest='host', type='string', help='ホスト名')
    parser.add_option('-i', '--ipaddr', action='store', dest='addr', type='string', help='IPアドレス')
    parser.add_option('-t', '--type', action='store', dest='cmts', type='string', help='CMTS種別')
    parser.add_option('-k', '--key', action='store', dest='key', type='string', help='アイテムキー')
    parser.add_option('-a', '--action', action='store', dest='action', type='string', help='スクリプト動作')

    #追加したオプションに指定している格納先変数のデフォルト値を設定
    parser.set_defaults(host=None, addr=None, cmts=None, key="Resource_CM_Active_CardSlot[<n>]", action=None)

    #オプション解析
    (options, args) = parser.parse_args()

    #オプションの値を返す(options.<変数>)
    return options.host, options.addr, options.cmts, options.key, options.action

############################################
#カスタムディスカバリ
############################################
def func_disc(cmts):
    if cmts == "c4" or cmts == "pc4" :
        data='{"data":['\
                '{ "{#SLOT}":"1" },'\
                '{ "{#SLOT}":"2" },'\
                '{ "{#SLOT}":"3" },'\
                '{ "{#SLOT}":"4" },'\
                '{ "{#SLOT}":"5" },'\
                '{ "{#SLOT}":"6" },'\
                '{ "{#SLOT}":"7" },'\
                '{ "{#SLOT}":"8" },'\
                '{ "{#SLOT}":"9" },'\
                '{ "{#SLOT}":"10" },'\
                '{ "{#SLOT}":"11" },'\
                '{ "{#SLOT}":"12" },'\
                '{ "{#SLOT}":"13" },'\
                '{ "{#SLOT}":"14" },'\
                '{ "{#SLOT}":"ALL" }'\
            ']}'
    elif cmts == "pubr":
        data='{"data":['\
                '{ "{#SLOT}":"5/0" },'\
                '{ "{#SLOT}":"5/1" },'\
                '{ "{#SLOT}":"6/0" },'\
                '{ "{#SLOT}":"6/1" },'\
                '{ "{#SLOT}":"7/0" },'\
                '{ "{#SLOT}":"7/1" },'\
                '{ "{#SLOT}":"8/0" },'\
                '{ "{#SLOT}":"8/1" },'\
                '{ "{#SLOT}":"ALL" }'\
            ']}'
    elif cmts == "cbr":
        data='{"data":['\
                '{ "{#SLOT}":"0" },'\
                '{ "{#SLOT}":"1" },'\
                '{ "{#SLOT}":"2" },'\
                '{ "{#SLOT}":"3" },'\
                '{ "{#SLOT}":"6" },'\
                '{ "{#SLOT}":"7" },'\
                '{ "{#SLOT}":"8" },'\
                '{ "{#SLOT}":"9" },'\
                '{ "{#SLOT}":"ALL" }'\
            ']}'

    print(data)

############################################
#CMTSモデム数取得
############################################
def func_get_modem_summary(adddr, cmts):
    #モジュール定義
    import telnetlib

    #変数初期化
    host = adddr
    cpass = "iki2kan"
    user = "bbsec"
    password = "testtest"
    command = "show cable modem summary"
    timeout = 60

    #Telnet実行からModulation Profileの取得まで
    #どこかでTimeOutが発生したら0を返して終了
    #Modulation Profileを取得できたら数値のみ返す
    try:
        #Telnet
        tn = telnetlib.Telnet(host,23,timeout)

        #ログイン->特権
        if cmts == "c4" or cmts == "pc4":
            tn.read_until("Login:",timeout)
            tn.write(user + "\n")

            tn.read_until("Password:",timeout)
            tn.write(password + "\n")
        elif cmts == "cbr" or cmts == "pubr":
            tn.read_until("Password:",timeout)
            tn.write(cpass + "\n")

            tn.read_until(">",timeout)
            tn.write("login\n")

            tn.read_until("Username:",timeout)
            tn.write(user + "\n")

            tn.read_until("Password:",timeout)
            tn.write(password + "\n")

            tn.read_until("#",timeout)
            tn.write("terminal length 0\n")

        #コマンド実行
        tn.read_until("#",timeout)
        tn.write(command + "\n")

        #情報部分抜粋
        result = tn.read_until("#",timeout)

        #ログアウト
        tn.write("exit\n")

        #セッションクローズ
        tn.close()

    except:
        #エラー時は一律 error
        result = "error"

    #返す
    return result

############################################
#スロット情報取得
############################################
def get_slot(cmts):
    #初期化
    if cmts == "c4" or cmts == "pc4":
        slot = (\
                '1', \
                '2', \
                '3', \
                '4', \
                '5', \
                '6', \
                '7', \
                '8', \
                '9', \
                '10', \
                '11', \
                '12', \
                '13', \
                '14' \
                )
    elif cmts == "pubr" :
        slot = (\
                '5/0', \
                '5/1', \
                '6/0', \
                '6/1', \
                '7/0', \
                '7/1', \
                '8/0', \
                '8/1' \
                )
    elif cmts == "cbr" :
        slot = (\
                '0', \
                '1', \
                '2', \
                '3', \
                '6', \
                '7', \
                '8', \
                '9' \
                )

    #返す
    return slot

############################################
#値成形
############################################
def get_data(cmsummary, cmts, slot):
    #モジュール定義
    import re

    #初期化
    if cmts == "c4" or cmts == "pc4":
        data = {\
                '1': -1, \
                '2': -1, \
                '3': -1, \
                '4': -1, \
                '5': -1, \
                '6': -1, \
                '7': -1, \
                '8': -1, \
                '9': -1, \
                '10': -1, \
                '11': -1, \
                '12': -1, \
                '13': -1, \
                '14': -1, \
                'ALL': -1 \
                }
        ptn = '\nSlot +<slot> +Total +[0-9]+ +([0-9]+).*'
    elif cmts == "pubr" :
        data = {\
                '5/0': -1, \
                '5/1': -1, \
                '6/0': -1, \
                '6/1': -1, \
                '7/0': -1, \
                '7/1': -1, \
                '8/0': -1, \
                '8/1': -1, \
                'ALL': -1 \
                }
        ptn = '\nC<slot>\/.\/U. +[0-9]+ +[0-9]+ +([0-9]+).*'
    elif cmts == "cbr" :
        data = {\
                '0': -1, \
                '1': -1, \
                '2': -1, \
                '3': -1, \
                '6': -1, \
                '7': -1, \
                '8': -1, \
                '9': -1, \
                'ALL': -1 \
                }
        ptn = '\nC<slot>\/0\/.\/U. +[0-9]+ +[0-9]+ +([0-9]+).*'

    #Telnet失敗していないなら集計
    if cmsummary != "error":
        #値抽出。searchで引っかかるならfindallで全てのマッチ結果を合計する。ALLへは...
        #1)Cisco CMTS => -1以外の結果を全て足す
        #2)Arris CMTS => Total値を別途参照する。ヒットしない場合は-1
        if cmts == "cbr" or cmts == "pubr":
            data['ALL'] = 0
        else:
            if re.search('\n +Total +[0-9]+ +[0-9]+.*', cmsummary):
                data['ALL'] = int(re.search('\n +Total +[0-9]+ +([0-9]+).*', cmsummary).group(1))
            else:
                data['ALL'] = -1

        for n in slot:
            pattern = re.compile(ptn.replace('<slot>', n.replace('/', '\/')))
            if pattern.search(cmsummary):
                workdata = pattern.findall(cmsummary)
                data[n] = 0
                for m in range(len(workdata)):
                    data[n] += int(workdata[m])
                if cmts == "cbr" or cmts == "pubr":
                    data['ALL'] += data[n]

    #返す
    return data

############################################
#トラッパーアイテムへ送る
############################################
def func_send_item(activecm, host, cmts, key, slot):
    #モジュール定義
    import socket

    #テンプレ
    template = '{"host": "<host>", "key": "<key>", "value": "<value>"}'

    #送信データの整形
    datastr = ''
    for n in slot:
        datastr += template.replace('<host>', host).replace('<key>', key.replace('<n>', n)).replace('<value>', str(activecm[n])) + ','
    datastr += template.replace('<host>', host).replace('<key>', key.replace('<n>', 'ALL')).replace('<value>', str(activecm['ALL']))

    #トラッパーアイテムへデータ送信
    client = socket.socket()
    client.connect(("127.0.0.1",10051))
    client.send('{"request": "sender data", "data": [' + datastr + ']}')
    response = client.recv(1024)
    client.close

    #結果表示
    print (response[13:])

############################################
#                  メイン
############################################
#コマンドライン引数チェック
host, adddr, cmts, key, action = func_get_options()

#CMTS種別が指定以外は終了
if cmts == "c4" or cmts == "pc4" or cmts == "cbr" or cmts == "pubr":
    #ディスカバリか判断
    if action == "disc":
        func_disc(cmts)
    else:
        cmsummary = func_get_modem_summary(adddr, cmts)
        slot = get_slot(cmts)
        activecm = get_data(cmsummary, cmts, slot)
        func_send_item(activecm, host, cmts, key, slot)
else:
    print("UNKNOWN CMTS")

