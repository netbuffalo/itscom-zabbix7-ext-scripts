#!/opt/pyenv/versions/2.7.18/bin/python
# -*- coding: utf-8 -*-
#
# version    : 1.0.0
# author     : shosaka@ossbn.co.jp
# created at : 2022.08.31
# updated at :

import subprocess
import argparse
from datetime import datetime, timedelta

def main():
    # parse options
    parser = argparse.ArgumentParser(description='coming soon?')
    parser.add_argument('-l', '--log', action="store", dest="log", help="target log file", required=True)
    parser.add_argument('-k', '--keywords', action="store", dest="key", help="keywords in logs", required=True)

    args = parser.parse_args()

    now = datetime.now()

    try:
        grep = subprocess.Popen(('grep', args.key, args.log), stdout=subprocess.PIPE)
        output = subprocess.check_output(('tail', '-n1'), stdin=grep.stdout)
        grep.wait()
        words = output.strip()
        if len(words) == 0:
            return 2592000 # 30 days force.
        dt = None
        try:
            dt = datetime.strptime(words, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            remains = str(e).split('remains: ')[1]
            words = words.split(remains)[0]
            dt = datetime.strptime(words, '%Y-%m-%d %H:%M:%S')

        delta = now - dt
        print(int(delta.total_seconds()))
    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()

