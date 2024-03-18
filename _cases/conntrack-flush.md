---
layout: post
title: TCP连接非预期断开，报错`connection reset by peer`
date: 2024-03-18
tags: conntrack vip netfilter
update: 2024-03-18
---

## 问题现象
经过前期调查，对复现场景简化后，问题和现象如下：

1. 从一个节点连接一个服务端口，连接正常：
   ```
   # nc 10.232.3.28 8899
   ```


   > 解释一下网络连接情况
   >
   > 环境是kubernetes集群，使用flannel网络，路由转发。上述命令在节点上运行，连接另外一个节点上的pod内的服务：
   >
   > ```
   > +---+   +-----------------+
   > |   |   |         +-----+ |
   > |nc |-> | cni0 -> | pod | |
   > |   |   |         +-----+ |
   > +---+   +-----------------+
   > ```
   >
   > br-mgmt/node1(192.168.11.7) -- br-mgmt/node2(192.168.11.8) -- cni0(10.232.3.1) -- pod(10.232.3.28)
   >
   > 路由
   > ```
   > 10.232.3.0/24 via 192.168.11.8 dev br-mgmt
   > ```

2. 在node-的br-mgmt上添加IP `192.168.11.100/32`后删除该IP。
3. 在`nc`侧回车触发nc发送数据，发现`nc`报错显示`Connection reset by peer`。
   ```
   # nc 10.232.3.28 8899

   Ncat: Connection reset by peer.
   ```

   > 此处添加删除IP是模拟实际环境中VIP的迁移。最初发现问题时发现keepalived pod重启有概率引发该问题。

## 问题分析
1. 在执行`nc`的节点上`tcpdump`得到的结果
   ```
   12:47:29.084019 IP 192.168.11.7.31445 > 10.232.3.28.8899: Flags [S], seq 32386333, win 29200, options [mss 1460,sackOK,TS val 1553380737 ecr 0,nop,wscale 9], length 0
   12:47:29.084420 IP 10.232.3.28.8899 > 192.168.11.7.31445: Flags [S.], seq 3724549281, ack 32386334, win 28960, options [mss 1460,sackOK,TS val 1741645252 ecr 1553380737,nop,wscale 9], length 0
   12:47:29.084458 IP 192.168.11.7.31445 > 10.232.3.28.8899: Flags [.], ack 1, win 58, options [nop,nop,TS val 1553380738 ecr 1741645252], length 0

   ...

   12:54:23.596883 IP 192.168.11.7.35051 > 10.232.3.28.8899: Flags [P.], seq 32386334:32386335, ack 3724549282, win 58, options [nop,nop,TS val 1553795251 ecr 1741645252], length 1
   12:54:23.597757 IP 10.232.3.28.8899 > 192.168.11.7.35051: Flags [R], seq 3724549282, win 0, length 0
   ```

   前三个包对应复现步骤第一步，可以看到tcp 三次握手正常建立连接。

   最后两个包对应上面复现步骤的第三步。这两个包看起来有问题：client侧用另外一个端口发了一个包，然后server回了RST。从server侧来看，它是正常行为：收到了一个非法包，给对端发送RST。
   关键问题在于倒数第二个包是怎么回事。

2. 分析正常情况下的tcp连接，在`nc`的节点上通过`ss -ntp`查看连接，发现端口和`tcpdump`到的不一致
   ```
   ESTAB      0      0            192.168.11.7:33862           10.232.3.28:8899  users:(("nc",pid=4373,fd=3))
   ```
   发现节点上还有另外一条iptables规则，会masquerade目的地址是10.232.3.0/24的包。也就是从`nc`进程的视角，本次连接它用的端口是33862。系统SNAT为31445发出去跟nc本身无感知。
3. Linux下netfilter使用conntrack机制来跟踪连接，基于上条猜测跟conntrack有关。`conntrack -L`命令列出当前系统维护的连接，可以看到在出错之前存在两个端口之间的变换：
   ```
   tcp      6 86135 ESTABLISHED src=192.168.11.7 dst=10.232.3.28 sport=33862 dport=8899 src=10.232.3.28 dst=192.168.11.7 sport=8899 dport=31445 [ASSURED] mark=0 use=1
   ```
   而在第二步中删除IP之后，上面这条conntrack条目消失。同时还可以发现，少了不止这一个条目。

   此时问题已经可以解释了，因为conntrack缺失，当nc发送下一个tcp packet时，Linux把33862端口SNAT到了另外一个端口`35051`，也就是引起server端发送RST的包。server端发的RST包可以正常回到`nc`进程(因为新的conntrack已经建立)，就有了上述报错。
4. 但是conntrack条目丢失的原因还是不清楚。好在当时有另一条线索：另一个kernel版本的server上无法复现该问题。通过比较两个kernel的commit差异(conntrack关键字)，锁定了一个嫌疑patch：
   ```
   netfilter: masquerade: don't flush all conntracks if only one address deleted on device
   ```
   最终发现就是该patch做了修复。修复之前的实现是当网络设备上一个地址被删除时，该网络设备上所有的conntrack都被清除；修复后，只清理对应IP地址的conntrack。
