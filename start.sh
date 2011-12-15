cd /home/punchagan/childrens-park/
if [ `ps -ef|grep chatroom|grep -v grep|wc -l` -lt 1 ]; then
    echo "Bot not running, Starting ..."
    /usr/bin/nohup ./vir-santa/bin/python chatroom.py &
elif [ `tail -1 nohup.out|grep -c -E "(WARNING - could not connect to server - aborting)|(Disconnected from server)"` -gt 0 ]; then
    pid=`ps -ef|grep chatroom|head -1|tr -s " "|cut -d " " -f 2`
    echo "killing bot:" $pid
    kill -9 $pid
    sleep 60
    /usr/bin/nohup ./vir-santa/bin/python chatroom.py &
else
    echo "Bot running..."
fi
