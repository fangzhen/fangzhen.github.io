---
layout: post
title:  "vip切换导致celery连接卡住问题"
tags: iptables vip
date: 2018-11-19
update: 2021-06-29
---

## 问题描述
系统中使用celery通过rabbitmq 集群接收任务后执行。问题现象是celery不再执行任何任务，重启服务可恢复。

[//]: # (EAS-19150)

### 环境信息
```
kubernetes 1.9
celery 3.1.19
rabbitmq 3.7.0，使用社区集群方案。
rabbitmq 运行在pod中，通过NodePort方式对外提供服务。集群使用keepalived维护了一个vip，celery通过vip:port 方式连接。
```

## 直接原因 & Workaround
开始一直没有找到问题的重现步骤，但是总会偶尔重现，而且都是在rabbitmq集群环境中重现，单节点的rabbitmq没有重现。

首先怀疑的是rabbitmq集群和celery之间连接的问题。

在出问题的环境上strace，可以看到卡在了`recvfrom`系统调用上。

```
[root@node-1 ~]# strace -p 29085
strace: Process 29085 attached
recvfrom(3,
```

使用gdb attatch到 celery进程，查看python调用栈：
```
(gdb) py-list
 272            recv = self._quick_recv
 273            rbuf = self._read_buffer
 274            try:
 275                while len(rbuf) < n:
 276                    try:
>277                        s = recv(n - len(rbuf))
 278                    except socket.error as exc:
 279                        if not initial and exc.errno in _errnos:
 280                            continue
 281                        raise
 282                    if not s:

(gdb) py-bt
#5 Frame 0x38df550, for file /usr/lib/python2.7/site-packages/amqp/transport.py, line 277, in _read (self=<TCPTransport(_quick_recv=<built-in method recv of _socket.socket object at remote 0x3a045a0>, sock=<_socketobject at remote 0x3a69520>, _write=<instancemethod at remote 0x3a8d460>, connected=True, _read_buffer='') at remote 0x3a02550>, n=7, initial=True, _errnos=(11, 4), recv=<built-in method recv of _socket.socket object at remote 0x3a045a0>, rbuf='')
    s = recv(n - len(rbuf))
#9 Frame 0x38df310, for file /usr/lib/python2.7/site-packages/amqp/transport.py, line 154, in read_frame (self=<TCPTransport(_quick_recv=<built-in method recv of _socket.socket object at remote 0x3a045a0>, sock=<_socketobject at remote 0x3a69520>, _write=<instancemethod at remote 0x3a8d460>, connected=True, _read_buffer='') at remote 0x3a02550>, unpack=<built-in function unpack>, read=<instancemethod at remote 0x3a6c690>, read_frame_buffer='')
    frame_header = read(7, True)
#13 Frame 0x38df0f0, for file /usr/lib/python2.7/site-packages/amqp/method_framing.py, line 107, in _next_method (self=<MethodReader(bytes_recv=0, heartbeats=0, partial_messages={}, _quick_get=<built-in method popleft of collections.deque object at remote 0x3a694b0>, queue=<collections.deque at remote 0x3a694b0>, source=<TCPTransport(_quick_recv=<built-in method recv of _socket.socket object at remote 0x3a045a0>, sock=<_socketobject at remote 0x3a69520>, _write=<instancemethod at remote 0x3a8d460>, connected=True, _read_buffer='') at remote 0x3a02550>, running=False, expected_types={}, _quick_put=<built-in method append of collections.deque object at remote 0x3a694b0>) at remote 0x3a66150>, queue=<collections.deque at remote 0x3a694b0>, put=<built-in method append of collections.deque object at remote 0x3a694b0>, read_frame=<instancemethod at remote 0x39f7c30>)
    frame_type, channel, payload = read_frame()

... 以下略
```

查看celery 代码可以看到这个地方是amqp client 发送了8字节的协议头之后等待server的回应，但是一直没有收到。但是socket没有设置超时，所以一直卡在了这个位置。相当于celery还没有完成到rabbitmq的连接，所以也接收不到任务。

到此为止，可以通过设置socket timeout来workaround该问题，如果超时重连，需要修改celery代码。

## 根本原因追踪

### 复现问题
目前仍然不能确认根本原因，尝试对rabbitmq集群或单个rabbitmq实例重启测试，一直没有复现该问题，推测 rabbitmq 集群问题的可能性不大，需要换方向。

如前所述，amqp client 连接rabbitmq server使用的是vip:NodePort来连接的，而vip有可能在几个节点之间漂移，因此怀疑连接卡住有可能跟vip切换有关。
尝试通过切换vip来重现问题，果然可以重现。

vip是keepalived来管理的，为了不影响环境中其他服务，简单修改下keepalived的检测脚本，把vip配置为检测8978端口，把vip配置在8978端口开放的节点上。
```
    vrrp_script check_for_vip
    {
        script "/usr/bin/curl 127.0.0.1:8978"
        interval 2
        fall 2
    }

```
使用下面的脚本来尝试重现，测试发现运行几分钟就会卡在`celery -A coaster.conductor.app inspect ping`上，问题重现。

```
for n in 1 2 3; do
      ssh node-$n "ps aux | grep [S]imple | awk '{print \$2}' | xargs kill"
done

wait_celery(){
   while true; do
     sleep 3
     online_celery=$(celery -A coaster.conductor.app inspect ping | grep celery | wc -l)
     [ $online_celery -eq 4 ] && break  # -eq num 需要改成环境中节点数+1
   done
}

loop_inf(){
  while true; do
    for n in 1 2 3; do # node 1 2 3 是rabbitmq集群所在的三个节点
      ssh node-$n "nohup python -m SimpleHTTPServer 8978 &>pserver.nohup </dev/null &"
      wait_celery # 等待celery重连到rabbitmq
      # kill 掉8978端口，强制vip切换，celery重连
      ssh node-$n "ps aux | grep [S]imple | awk '{print \$2}' | xargs kill"
      sleep 4
    done
  done
}

( set -x;  loop_inf ) |& while IFS= read line; do echo "$(date -Ins) $line"; done

```

### 岔路

环境中的NodePort转发是kube-proxy服务通过更新iptables规则来实现。怀疑kube-proxy的iptables实现是不是可能有bug。

比如多条规则写入是顺序的，有一定的时间差，导致网络packet经过的是一条不一致的iptable规则链。
查阅了kube-proxy的实现，对iptables规则的写入都是通过iptables-restore来做的，
[iptables-restore会在单个原子操作中restore所有的规则](https://www.tummy.com/blogs/2010/01/16/iptables-restore-is-in-the-atomic-age/)，
理论上不应该有规则写入一部分而导致的不一致问题。


### 踏上正途
查看从celery到rabbitmq server的整个tcp链条是否有问题。

看下卡住的celery进程所在节点上连接到rabbitmq NodePort的连接：
```
[root@node-1 ~]# ss -np  '( dport = 32672 )' | cat
Netid  State      Recv-Q Send-Q Local Address:Port               Peer Address:Port
tcp    ESTAB      0      0      10.20.0.6:59558              10.20.0.6:32672               users:(("python2",pid=61475,fd=39))
tcp    ESTAB      0      0      10.20.0.3:48598              10.20.0.6:32672               users:(("celery",pid=29085,fd=3))
```
#### 正常连接
对正常的连接（59558端口），rabbitmq日志会有对应的连接，可以看到ip:port其实已经是经过NAT之后的了。
```
[root@node-1 ~]# kubectl logs -nopenstack rabbitmq-0 -nopenstack | grep 59558
2018-11-20 22:36:36.904 [info] <0.5560.184> accepting AMQP connection <0.5560.184> (192.168.20.3:59558 -> 10.233.65.134:5672)
2018-11-20 22:36:36.907 [info] <0.5560.184> connection <0.5560.184> (192.168.20.3:59558 -> 10.233.65.134:5672): user 'rabbitmq' authenticated and granted access to vhost '/'
```
在rabbitmq-0 容器里也可以看到59558的连接，跟上述rabbitmq日志里是吻合的。
```
[root@node-1 ~]# kubectl exec -it -nopenstack rabbitmq-0 -- ss -np  '( dport = 59558 )'
Netid State      Recv-Q Send-Q                                                          Local Address:Port                                                                         Peer Address:Port
tcp   ESTAB      0      0                                                        ::ffff:10.233.65.134:5672                                                                  ::ffff:192.168.20.3:59558               users:(("beam.smp",pid=139,fd=85))
```

#### 异常连接
但是对于celery的连接48598，在rabbitmq pod中通过ss找不到对端的连接信息，在rabbitmq日志里也没有相关日志。

而在物理节点上却可以看到对端连接，而且连接的Peer Address就是celery服务原始没有NAT的ip和端口。
```
[root@node-1 ~]# ss -np  '( dport = 48598 )'
Netid State      Recv-Q Send-Q                                                          Local Address:Port                                                                         Peer Address:Port
tcp   ESTAB      8      0                                                            ::ffff:10.20.0.6:32672                                                                    ::ffff:10.20.0.3:48598
```
进一步发现连接的进程是hyperkube，而不是rabbitmq server。
```
[root@node-1 ~]# lsof -i:32672
COMMAND     PID USER   FD   TYPE    DEVICE SIZE/OFF NODE NAME

hyperkube 26876 root    8u  IPv6 217745983      0t0  TCP *:32672 (LISTEN)
```
所以可以看到，本来应该通过NodePort的iptables规则之后连rabbitmq的连接实际没有连接到rabbitmq服务，而是连到了kube-proxy上。该连接的Recv-Q 值是8，正好是amqp协议的请求头大小。

### 根本原因
回过头来看kube-proxy设置的iptables规则，挑出相关的规则如下：
```
rule1： -A OUTPUT -m comment --comment "kubernetes service portals" -j KUBE-SERVICES
...
rule2： -A KUBE-NODEPORTS -p tcp -m comment --comment "openstack/rabbitmq:public" -m tcp --dport 32672 -j KUBE-MARK-MASQ
-A KUBE-NODEPORTS -p tcp -m comment --comment "openstack/rabbitmq:public" -m tcp --dport 32672 -j KUBE-SVC-3NR3PRWB562QV3AI
...
rule3： -A KUBE-SERVICES -m comment --comment "kubernetes service nodeports; NOTE: this must be the last rule in this chain" -m addrtype --dst-type LOCAL -j KUBE-NODEPORTS
```
简单解释一下，访问NodePort的连接先经过rule1跳转到KUBE-SERVICES chain，然后匹配rule3跳转到 KUBE-NODEPORTS chain，再往后就是正常匹配KUBE-NODEPORTS链中的规则，转发到不同的pod。

推测问题出在这个匹配过程中，rule3有个条件是`--dst-type LOCAL`，是指目的地址是本机的包。正常来说，如果vip在本机，从本机访问vip的包会匹配该规则，没有任何问题。经过OUTPUT链之后流量分发到不同节点。

出问题的情况，rule3 这条规则匹配的时候，vip还没有配置到本机，所以该规则没匹配。在OUTPUT链之后，会经过系统的Routing Decision，根据路由选择包的下一跳。此时路由选择的时候，vip已经
配置上，kernel认为这个包应该发往本机，会走到INPUT 链，但是这个过程中是没有NAT的，所以直接连接上了。

#### 侧面印证
为了进一步印证，在iptables规则加上LOG
```
iptables -I INPUT 1 -d 10.20.0.6/32 -p tcp -m tcp --dport 32672 -j LOG --log-prefix "INPUT_LOG_10.20.0.6" --log-level 7
iptables -I OUTPUT 1 -d 10.20.0.6/32 -p tcp -m tcp --dport 32672 -j LOG --log-prefix "OUTPUT_LOG_10.20.0.6" --log-level 7
```
可以看到如下日志：正常情况下，vip不在本机，只有OUTPUT有个日志（第一行），但是出问题的情况下， OUTPUT之后有一个INPUT日志，跟上述的分析吻合。
```
Nov 20 22:36:36 node-1.domain.tld kernel: OUTPUT_LOG_10.20.0.6IN= OUT=br-roller SRC=10.20.0.3 DST=10.20.0.6 LEN=60 TOS=0x00 PREC=0x00 TTL=64 ID=13624 DF PROTO=TCP SPT=48598 DPT=32672 WINDOW=29200 RES=0x00 SYN URGP=0
Nov 20 22:36:38 node-1.domain.tld kernel: OUTPUT_LOG_10.20.0.6IN= OUT=lo SRC=10.20.0.3 DST=10.20.0.6 LEN=60 TOS=0x00 PREC=0x00 TTL=64 ID=13625 DF PROTO=TCP SPT=48598 DPT=32672 WINDOW=29200 RES=0x00 SYN URGP=0
Nov 20 22:36:38 node-1.domain.tld kernel: INPUT_LOG_10.20.0.6IN=lo OUT= MAC=00:00:00:00:00:00:00:00:00:00:00:00:08:00 SRC=10.20.0.3 DST=10.20.0.6 LEN=60 TOS=0x00 PREC=0x00 TTL=64 ID=13625 DF PROTO=TCP SPT=48598 DPT=32672 WINDOW=29200 RES=0x00 SYN URGP=0
```

#### 遗留问题
1. kube-proxy 为什么要监听NodePort的端口。
2. 从代码层面论证上述原因的可能性。

## 总结
这个case前前后后经过挺长时间才完全弄明白，从workaround到最终找到根本原因。涉及到的技术也比较宽泛，包括：
1. 业务 celery
2. 中间件 rabbitmq
3. iptables
4. 网络：tcp 连接，路由
5. kubenetes

另一方面，这个问题暴露出一些架构上的问题，例如：
* celery（amqp库）在连接卡住的情况下不能及时出错，导致整个服务卡住。进而，因为没有使用keepalive而导致连接卡住的问题有很多。
* kube-proxy在这种corner case的情况下问题如何规避。
* vip的使用需要更加谨慎。
