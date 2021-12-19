twemproxy-ha 实现高可用：
1.监控nutcracker 进程是否挂掉，挂掉自动重启；
2.redis 分片实例发生主从切换时,修改nutcracker.yml,并重启nutcracker
