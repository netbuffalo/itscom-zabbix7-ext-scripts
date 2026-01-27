#!/opt/pyenv/versions/2.7.18/bin/python
# -*- coding: utf-8 -*-
#
# version    : 2.0.0
# author     : shosaka@ossbn.co.jp
# created at : 2016.11.10
# updated at : 2026.01.27

import json
import urllib2

class ZabbixAPIException (Exception):
    pass

class ZabbixAPI(object):

    def __init__(self, api_url, **args):
        # zabbix frontend url
        self.api_url = api_url

        self.request_id = 1
        if args.has_key('request_id'):
            self.request_id = args['request_id']

        self.jsonrpc = '2.0'
        if args.has_key('jsonrpc'):
            self.jsonrpc = args['jsonrpc']

        self.username = 'Admin'
        if args.has_key('username'):
            self.username = args['username']

        self.password = 'zabbix'
        if args.has_key('password'):
            self.password = args['password']

        self.token = None

    def auth(self, username, password):
        auth_json = {
            'jsonrpc': self.jsonrpc,
            'method': 'user.login',
            'id': self.request_id,
            'params': {
                'username': username,
                'password': password
                }
        }

        response = self.do_zabbix_api(auth_json)

        if response and 'result' in response:
            self.token = response['result']
            return self.token
        else:
            raise ZabbixAPIException("Authentication error occurred by %s!" % username)

    def do_zabbix_api(self, json_request):
        json_response = None
        req = urllib2.Request(self.api_url)
        req.add_header('Content-Type', 'application/json')
        res = urllib2.urlopen(req, json.dumps(json_request))
        if res.getcode() == 200: # is http status ok (200) ?
            data = json.loads(res.read())
            if 'error' in data:
                raise ZabbixAPIException(data['error']['data'])
            else:
                json_response = data
        else:
            raise ZabbixAPIException("HTTP status code is not success (%d)!" % res.getcode())

        res.close()

        return json_response


    def request(self, **args):

        if self.token is None:
            self.auth(self.username, self.password)

        req = {
            'jsonrpc': self.jsonrpc,
            'method': args['method'],
            'auth': self.token,
            'id': self.request_id,
            'params': args['params']
        }

        response = self.do_zabbix_api(req)

        if 'result' in response:
            return response['result']
        else:
            raise ZabbixAPIException("Zabbix API request failed. %s" % response)


if __name__ == '__main__':

    zabbix = ZabbixAPI('http://localhost/zabbix/api_jsonrpc.php', username='Admin', password='zabbix')

    query = {
            #'output': 'extend', # shorten (only id), refer, extend (all db fields)
            'output': ['host', 'status'],
            #'limit': 1000,
            'filter': {
                'status': [0, 1], # enable(0), disable(1)
                }
            }

    hosts = zabbix.request(method='host.get', params=query)

    for host in hosts:
        print(host)
