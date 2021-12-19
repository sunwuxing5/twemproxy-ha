#!/bin/bash


action=$1

TWEMPROXY_PATH=$(dirname `pwd`)

PROC=${TWEMPROXY_PATH}/sbin/nutcracker
TWEMPROXY_CONF=${TWEMPROXY_PATH}/conf/nutcracker.yml
TWEMPROXY_LOG=${TWEMPROXY_PATH}/log/twmproxy.log
TWEMPROXY_PID=${TWEMPROXY_PATH}/log/nutcracker.pid


function myecho(){
    msg="$1"
    echo -e "\033[32m ${msg} \033[0m"
}

function twemproxy_start(){
    twemproxy_status
    ret=$?
    if [[ $ret -eq 1 ]];then
        myecho "nutcracker has started!" 
        return 0
    fi
    $PROC -c ${TWEMPROXY_CONF} -d -v 6 -o ${TWEMPROXY_LOG} -p ${TWEMPROXY_PID}

    twemproxy_status
    ret=$?
    if [[ $ret -eq 1 ]];then
        myecho "nutcracker start successful!" 
    else
        myecho "nutcracker start fail !" 
    fi
}

function twemproxy_stop(){
    #pid=$(cat log/nutcracker.pid)
    #kill -15 $pid
    #rm -rf log/nutcracker.pid
    twemproxy_status
    ret=$?
    if [[ $ret -eq 0 ]];then
        myecho "nutcracker has stoped!" 
        return 0
    fi
    ps -ef|grep "sbin[/]nutcracker"|awk '{print $2}'|xargs -I {} kill -15 {}
    #pid=$(ps -ef|grep "sbin[/]nutcracker"|awk '{print $2}')
    #if [[ $pid ]];then
    #    kill -15 ${pid}
    #fi
    twemproxy_status
    ret=$?
    if [[ $ret -eq 0 ]];then
        myecho "nutcracker stop successful!" 
    else
        myecho "nutcracker stop fail !" 
    fi
    

}

function twemproxy_restart(){
    twemproxy_stop
    twemproxy_start
}

function twemproxy_status(){
    num=$(ps -ef|grep "sbin[/]nutcracker"|wc -l)
    return $num
}

case $action in
    start)
        myecho "twemproxy start"
        twemproxy_start
    ;;
    stop)
        myecho "twemproxy stop"
        twemproxy_stop
    ;;
    status)
        myecho "twemproxy status"
        twemproxy_status
        ret=$?
        if [[ $ret -eq 1 ]];then
            myecho "nutcracker is running!" 
        else
            myecho "nutcracker is not running!" 
        fi
    ;;
    restart)
        myecho "twemproxy restart"
        twemproxy_restart
    ;;
    *)
        myecho "Usage:./run.sh start|stop|restart|status !"
        exit 0
    ;;
esac
