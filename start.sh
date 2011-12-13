if [ `ps -ef|grep chatroom|grep -v grep|wc -l` -lt 1 ]
then
echo "Bot not running, Starting ..."
cd /home/punchagan/childrens-park/
/usr/bin/nohup ./vir-santa/bin/python chatroom.py &
fi
