# twemproxy-ha 实现高可用：
## 1.监控nutcracker 进程是否挂掉，挂掉自动重启；
## 2.redis 分片实例发生主从切换时,修改nutcracker.yml,并重启nutcracker
## 3.在监听过程中,哨兵挂掉,会轮训连接其他可用的哨兵ip

