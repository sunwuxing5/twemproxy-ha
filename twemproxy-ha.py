
from multiprocessing import Process
import redis
import os
import sys
import time
from mylogger import Logger
import json
import yaml

# twemproxy 高可用方案,1,检测nutcracker 代理进程,挂掉自动重启
# 监视分片主从切换,当sentnel 执行failover 主从切换时,agent 自动重写twemproxy 配置,并重启
# 3. sentinel 其中一个挂掉后,会轮训连接下一个请求


class twemproxyHelper(Process):
    lastchangeTime=0
    __conn = ""
    def __init__(self,task):
        Process.__init__(self)
        self.__log = Logger('logs/twemproxy-ha.log',level='debug').logger
        self.channel = ['+switch-master']
        self.conf_file = "config.yml"
        confData = self.get_yaml_data()
        self.__log.info("reload config:" + str(confData))
        self.twemproxyConf = confData['twemproxyConf']
        self.twemproxyPid = confData['twemproxyPid']
        self.restartCmd = confData['restartCmd']
        self.sentinelIp = confData['sentinelIp']
        self.twemproxy_monitor_down = confData['twemproxy_monitor_down']
        self.twemproxy_sacn_internal = confData['twemproxy_sacn_internal']
        self.twemproxy_down_sacn_internal = confData['twemproxy_down_sacn_internal']

        self.lastip=0
        self.taskid=task
        #
        #if self.taskid == 2:
        self.init_redis_pubsub()



    def get_yaml_data(self):
        # 打开yaml文件
        with open(self.conf_file) as f:
            data = yaml.safe_load(f)
        return data

    def twemproxyConfChangeTime(self):
        fileinfo=os.stat(self.twemproxyConf)
        self.lastchangeTime = fileinfo.st_ctime

    def updateTwemproxyConfig(self,listmsg):
        oldMasterHost = listmsg[1]
        oldMasterPort = listmsg[2]
        newMasterHost = listmsg[3]
        newMasterPort = listmsg[4]
        #更改配置
        #cmd = "sed -n 's/{}:{}/{}:{}/gp' {}".format(oldMasterHost,oldMasterPort,newMasterHost,newMasterPort,self.twemproxyConf)
        cmd = "sed -i 's/{}:{}/{}:{}/g' {}".format(oldMasterHost,oldMasterPort,newMasterHost,newMasterPort,self.twemproxyConf)
        self.__log.info("change conf :" + cmd)
        self.__log.info("replace:use {}:{} replace {}:{}".format(newMasterHost,newMasterPort,oldMasterHost,oldMasterPort))
        res=os.system(cmd)
        return res

    def restartTwemproxy(self):
        self.__log.info("restart twemproxy :" + self.restartCmd)
        return os.system(self.restartCmd)

    #哨兵实例，中途挂掉，去尝试连接其他sentinel
    def init_redis_pubsub(self):
        trycnt = 0;
        while True:
            try:
                #self.__conn = redis.Redis(host='127.0.0.1',port=27379)
                self.__conn = redis.Redis(host=self.sentinelIp[self.lastip]['ip'],port=self.sentinelIp[self.lastip]['port'],socket_connect_timeout=3)
                self.__conn.ping()

                trycnt = trycnt + 1
                if trycnt>=3:
                    self.__log.info("init try connnection 超过3次 exit")
                    sys.exit(1)

            except Exception as e:
                time.sleep(1)
                self.__log.info(e)
            else:
                mmsg = "connct sentinel {}:{} !".format(self.sentinelIp[self.lastip]['ip'],
                                                        self.sentinelIp[self.lastip]['port'])
                self.__log.info(mmsg)
                break;
            finally:
                self.lastip = self.lastip + 1
                if self.lastip == len(self.sentinelIp):
                    self.lastip = 0
        self.__pubsub = self.__conn.pubsub()
        self.__pubsub.subscribe(self.channel)


    #监听主从切换的消息
    def momitor_switch_master(self):
       trycnt = 0
       while True:
           try:
               for item in self.__pubsub.listen():
                   # {'type': 'message', 'pattern': None, 'channel': b'+switch-master', 'data': b'mymaster 127.0.0.1 7379 127.0.0.1 7382'}
                   print(item)
                   if item['type'] != 'message':
                       self.__log.info("pubsub:"+ str(item))
                       continue
                   self.__log.info("switch-master:")
                   self.__log.info("pubsub:" + str(item))
                   msg = item['data'].decode('utf-8')
                   listmsg = msg.split(' ')
                   #print(listmsg)
                   if len(listmsg) == 5:
                       ret = self.updateTwemproxyConfig(listmsg)
                       if ret == 0:
                           self.restartTwemproxy()
               trycnt = trycnt + 1
               if trycnt >= 3:
                   self.__log.info("try connnection sentinel 超过3次 exit")
                   sys.exit(1)
               pass;


           except Exception as e:
               self.__log.info(e)
               self.init_redis_pubsub()
               pass


     #代理进程进行监控
    def twemproxy_is_run(self):
        pid =""
        try:
            with open(self.twemproxyPid) as f:
                pid=f.readline()
        except Exception as e:
            self.__log.info(e)
        if pid == "":
            return False
        try:
            os.kill(int(pid),0)
        except ProcessLookupError as e:
            return False
        return True
    
    def monitor_twemproxy_process(self):
        cnt=0
        while True:
            status=self.twemproxy_is_run()
            if not status:
                self.__log.info("twemproxy is not running!")
                cnt = cnt + 1
            else:
                cnt = 0
            if cnt >= self.twemproxy_monitor_down:
                cnt = 0
                self.__log.info("start:twemproxy has exited! now start twemproxy")
                os.system(self.restartCmd)
            if status:
                self.__log.info("twemproxy is running!")
                time.sleep(self.twemproxy_sacn_internal)
            else:
                #发现twemproxy 挂掉，扫描间隔，每2s 扫描一次
                time.sleep(self.twemproxy_down_sacn_internal)

    def run(self):
        if self.taskid==1:
            self.monitor_twemproxy_process()
        else:
            self.momitor_switch_master()

if __name__=="__main__":
    twemHelper2 = twemproxyHelper(2)
    twemHelper2.start()
    #父进程 监控 twemproxy 是否挂掉
    #twemHelper1 = twemproxyHelper(1)
    twemHelper2.monitor_twemproxy_process()
    twemHelper2.join()

