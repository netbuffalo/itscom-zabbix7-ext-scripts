#!/opt/pyenv/versions/2.7.18/bin/python
# -*- coding: utf-8 -*-
#
# version    : 1.0.1
# author     : shosaka@ossbn.co.jp
# created at : 2017.04.24
# updated at : 2026.02.02

import re
import telnetlib
import argparse

class Telnet:

    def __init__(self, host, **args):
        # target host
        self.host = host
        # username
        self.username = None if not args.has_key('username') else args['username']
        # password
        self.password = args['password']
        # target port
        self.port = 23 if not args.has_key('port') else args['port']
        self.timeout  = 30 if not args.has_key('timeout') else args['timeout']
        self._prompt_patterns = [
                #'(?:\n|.)+(Password|password|Login|login):[ ]*$'
                #'(?:\n|.)+(%|>|#|\$)[ ]*$',
                '(%|>|#|\$)[ ]*$', # standard prompt patterns.
                '(Password|password|Login|login|User name|Username|username):[ ]*$' # authentication prompt patterns.
                ]
        # encoding
        self.encode = 'utf8'
        if args.has_key('encode') and args['encode']:
            self.encode = args['encode']

        self.telnet   = telnetlib.Telnet(host, self.port)

    def get_prompt_pattern(self):
        return self._prompt_patterns

    def set_prompt_pattern(self, patterns):
        self._prompt_patterns = patterns

    def add_prompt_pattern(self, pattern):
        self._prompt_patterns.append(pattern)

    def login(self):
        if self.username:
            # wait for anything.
            response = self.telnet.expect(self._prompt_patterns, timeout=self.timeout)
            # if not match, response tuple is "(-1, None, text)"
            if response[0] >= 0: # match?
                self.telnet.write(self.username + '\r\n')
            else:
                self.close()
                raise Exception("TelnetLoginUserInputError")

        if self.password:
            response = self.telnet.expect(self._prompt_patterns, timeout=self.timeout)
            if response[0] >= 0: # match?
                self.telnet.write(self.password + '\r\n')
                response = self.telnet.expect(self._prompt_patterns, timeout=self.timeout)
                if response[0] != 0: # not match?
                    self.close()
                    raise Exception("TelnetPasswordAuthenticaionError")
            else:
                self.close()
                raise Exception("TelnetPasswordInputError")

    def _send(self, command):
        # write
        self.telnet.write(command + '\r\n')
        # wait for response
        return self.telnet.expect(self._prompt_patterns, timeout=self.timeout)

    def execute(self, command):
        response = self._send(command)
        # format
        outputs = []
        if len(response) > 2:
            characters = response[2].decode(self.encode)
            lines = characters.split('\n')
            for l in lines:
                outputs.append(l.strip())

        # is prompt found?
        if response[0] >= 0: # match?
            return outputs[1:len(outputs)-1] # delete first and end of line.
        else:
            return outputs[1:len(outputs)] # delete only first line.

    def close(self):
        self.telnet.close()

    def enable(self, **args):
        enable_command = 'enable'
        if args.has_key('command') and args['command']:
            enable_command = args['command']

        enable_password = self.password
        if args.has_key('password') and args['password']:
            enable_password = args['password']

        response = self._send(enable_command)
        outputs = response[2].decode(self.encode)
        if 'password' in outputs.lower():
            self.execute(enable_password)


def cut(line, delimiter):
    cut = []
    splited = line.split(delimiter)
    for s in splited:
        if len(s) > 0:
            cut.append(s.strip())

    return cut

def main():
    # parse options
    parser = argparse.ArgumentParser(description='coming soon?')
    parser.add_argument('-t', '--telnet', action="store", dest="host", help="telnet host", required=True)
    parser.add_argument('-u', '--username', action="store", dest="username", help="telnet username")
    parser.add_argument('-p', '--password', action="store", dest="password", help="telnet password", required=True)
    parser.add_argument('-c', '--command', action="store", dest="command", help="execute command", required=True)
    parser.add_argument('-e', '--enable', action="store_true", dest="enable", help="switch enable user")
    parser.add_argument('-ec', '--enable-command', action="store", dest="enable_command", help="enable command", default="enable")
    parser.add_argument('-ep', '--enable-password', action="store", dest="enable_password", help="enable password", default=None)
    parser.add_argument('-g', '--grep', action="store", dest="grep", help="grep", default=None)
    parser.add_argument('-d', '--delimiter', action="store", dest="delimiter", help="delimiter for cut", default=None)
    parser.add_argument('-f', '--field', action="store", dest="field", help="filed number for cut", default=None)
    parser.add_argument('-l', '--line', action="store_true", dest="lc", help="line count")
    parser.add_argument('-encoding', '--encoding', action="store", dest="encode", help="character encoding", default=None)
    args = parser.parse_args()

    tel = Telnet(args.host, username=args.username, password=args.password, encode=args.encode)
    tel.login()

    if args.enable:
        tel.enable(command=args.enable_command, password=args.enable_password)

    #outputs = tel.execute(args.command)
    outputs = []
    for cmd in args.command.split(';'):
        #if len(cmd) > 0:
        #    outputs += tel.execute(cmd)
        outputs += tel.execute(cmd)
    # close telnet connection
    tel.close()

    if args.grep: # grep output lines
        pattern = re.compile(args.grep)
        greped = []
        for line in outputs:
            if pattern.search(line):
                greped.append(line)
        outputs = greped

    if args.field: # cut line
        delimiter = ' ' if args.delimiter is None else args.delimiter
        fielded = []
        for line in outputs:
            splited = cut(line, delimiter)
            if len(splited) >= int(args.field):
                fielded.append(splited[int(args.field) - 1])
        outputs = fielded

    if args.lc:
        return len(outputs)
    else:
        return '\n'.join(outputs)

if __name__ == '__main__':
    # python telnet.py -t 192.168.0.218 -u root -p casa -c "show cable modem" -e
    print main()

