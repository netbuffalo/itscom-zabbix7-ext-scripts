#!/bin/sh
LANG=C

WORKDIR="/lib/zabbix/externalscripts/cmts_linecard_status" 
SCRIPTDIR="/lib/zabbix/externalscripts" 
PW="iki2kan" 
ENPW="Ku1tan64" 
DATE=`date +%Y%m%d%H%M`

#cbr1-aoba-LC(192.168.41.167)
python ${SCRIPTDIR}/telnet.py -t 192.168.41.167 -p ${PW} -e -ep ${ENPW} -c "show redundancy linecard all" > ${WORKDIR}/cbr1-aoba_linecard.log.${DATE}
if grep -q "Active" ${WORKDIR}/cbr1-aoba_linecard.log.${DATE} ; then
 mv -f ${WORKDIR}/cbr1-aoba_linecard.log.${DATE} ${WORKDIR}/cbr1-aoba_linecard.log
fi

#cbr1-aoba-SUP(192.168.41.167)
python ${SCRIPTDIR}/telnet.py -t 192.168.41.167 -p ${PW} -e -ep ${ENPW} -c "show redundancy | inc Location" > ${WORKDIR}/cbr1-aoba_SUP.log.${DATE}
if grep -q "Active" ${WORKDIR}/cbr1-aoba_SUP.log.${DATE} ; then
 mv -f ${WORKDIR}/cbr1-aoba_SUP.log.${DATE} ${WORKDIR}/cbr1-aoba_SUP.log
fi

#cbr2-aoba-LC(192.168.41.184)
python ${SCRIPTDIR}/telnet.py -t 192.168.41.184 -p ${PW} -e -ep ${ENPW} -c "show redundancy linecard all" > ${WORKDIR}/cbr2-aoba_linecard.log.${DATE}
if grep -q "Active" ${WORKDIR}/cbr2-aoba_linecard.log.${DATE} ; then
 mv -f ${WORKDIR}/cbr2-aoba_linecard.log.${DATE} ${WORKDIR}/cbr2-aoba_linecard.log
fi

#cbr2-aoba-SUP(192.168.41.184)
python ${SCRIPTDIR}/telnet.py -t 192.168.41.184 -p ${PW} -e -ep ${ENPW} -c "show redundancy | inc Location" > ${WORKDIR}/cbr2-aoba_SUP.log.${DATE}
if grep -q "Active" ${WORKDIR}/cbr2-aoba_SUP.log.${DATE} ; then
 mv -f ${WORKDIR}/cbr2-aoba_SUP.log.${DATE} ${WORKDIR}/cbr2-aoba_SUP.log
fi
