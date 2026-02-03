#!/bin/sh

CMTS=$1
SLOT=$2
WORKDIR="/lib/zabbix/externalscripts/cmts_linecard_status" 

#cat ${WORKDIR}/${CMTS}_SUP.log | grep "slot $SLOT" 
cat ${WORKDIR}/${CMTS}_SUP.log | grep "slot $SLOT" | awk '{print $1}'
