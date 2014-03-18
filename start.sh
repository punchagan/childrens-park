#!/bin/bash

SCRIPT="vir-santa/bin/park"
DIR=`dirname $0`
pushd $DIR > /dev/null

if [ `ps -ef|grep $SCRIPT|grep -v grep|wc -l` -lt 1 ]; then
    echo "Bot not running, Starting ..."
    $SCRIPT
elif [ `tail -1 park.log|grep -c -E "(WARNING - could not connect to server - aborting)|(Disconnected from server)|xmpp.protocol.SystemShutdown: (u'system-shutdown', '')"` -gt 0 ]; then
    pid=`ps -ef|grep $SCRIPT|head -1|tr -s " "|cut -d " " -f 2`
    echo "killing bot:" $pid
    kill -9 $pid
    sleep 60  #fixme: why is this here?
    $SCRIPT
else
    echo "Bot running..." > /dev/null
fi

popd > /dev/null
