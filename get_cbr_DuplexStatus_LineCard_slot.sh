#!/bin/sh

CMTS=$1
SLOT=$2
WORKDIR="/lib/zabbix/externalscripts/cmts_linecard_status" 

#cat ${WORKDIR}/${CMTS}_linecard.log | sed 's/Stdby Warm/Stdby_Warm/' | sed 's/Stdby Cold/Stdby_Cold/' |sed 's/Stdby Hot/Stdby_Hot/'| grep ^${SLOT}
cat ${WORKDIR}/${CMTS}_linecard.log | sed 's/Stdby Warm/Stdby_Warm/' | sed 's/Stdby Cold/Stdby_Cold/' |sed 's/Stdby Hot/Stdby_Hot/'| grep ^${SLOT} | awk '{print $8}'

