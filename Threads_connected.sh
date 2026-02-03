#!/bin/bash

username="zabbix"
password=""

if [ -z $password ];
then
    mysql -u $username -e "show status like 'Threads_connected'" | grep Threads | cut -f2
else
    mysql -u $username -p"$password" -e "show status like 'Threads_connected'" | grep Threads | cut -f2
fi
