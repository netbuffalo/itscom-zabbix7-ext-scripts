#!/opt/pyenv/versions/2.7.18/bin/python
# -*- coding: utf-8 -*-
# version    : 1.1.1
# author     : shosaka@ossbn.co.jp
# created at : 2016.02.20
# updated at : 2016.02.20

from pysnmp.entity.rfc3413.oneliner import cmdgen

class SnmpNetworkException (Exception):
    pass

class SnmpTarget(object):

    def __init__(self, targetHost='localhost', community='public', port=161):
        self.targetHost = targetHost
        self.community = community
#        self.version = version
        self.port = port
        self.cmdGen = cmdgen.CommandGenerator()

    def get(self, oids=['.1.3.6.1.2.1.1.3.0'], timeout=3, retries=0):
        errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.getCmd(
            cmdgen.CommunityData(self.community),
            cmdgen.UdpTransportTarget((self.targetHost, self.port), timeout, retries),
            *oids
        )

        if errorIndication:
           # network error.
           # raise Exception(errorIndication)
            raise SnmpNetworkException(errorIndication)
        else:
#            if errorStatus:
#                raise Exception(errorStatus.prettyPrint())
#            else:
#                return varBinds
            return (errorStatus, varBinds)

    def nextWalk(self, oids=['.1.3.6.1.2.1.1.2.0'], timeout=3, retries=0,
            maxFetchRows=50):
        errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.nextCmd(
            cmdgen.CommunityData(self.community),
            cmdgen.UdpTransportTarget((self.targetHost, self.port), timeout, retries),
            *oids, maxRows=maxFetchRows)

        if errorIndication:
           # network error.
           # raise Exception(errorIndication)
            raise SnmpNetworkException(errorIndication)
        else:
#            if errorStatus:
#                # snmp error.
#                raise Exception(errorStatus.prettyPrint())
#            else:
#                return varBinds
            return (errorStatus, varBinds)

    def bulkWalk(self, oids=['.1.3.6.1.2.1.1.2.0'], timeout=3, retries=0,
            non_repeaters=0, max_repetitions=50):
        # Note:
        #   When more than 2 oids were set, probably bulkCmnd is wrong
        #   for handling repeaters and repetitions...
        errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.bulkCmd(
            cmdgen.CommunityData(self.community),
            cmdgen.UdpTransportTarget((self.targetHost, self.port), timeout, retries),
            non_repeaters, max_repetitions,
            *oids
        )

        if errorIndication:
           # network error.
           # raise Exception(errorIndication)
            raise SnmpNetworkException(errorIndication)
        else:
#            if errorStatus:
#                # snmp error.
#                raise Exception(errorStatus.prettyPrint())
#            else:
#                return varBinds
            return (errorStatus, varBinds)

if __name__ == '__main__':
    snmp = SnmpTarget('192.168.0.1', 'public')
    # snmpnext walk
    error, rows = snmp.nextWalk(['1.3.6.1.2.1.2.2.1.1', '1.3.6.1.2.1.2.2.1.2'])
    for row in rows:
        for col in row:
           print col[1], # value
        print ""


