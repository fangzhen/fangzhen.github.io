---
layout: post
title: linux 下arp相关内核参数
date: 2024-02-05
tags: arp
---

## 发送arp请求
### arp_announce
arp_announce 用于控制Linux在对外发送arp请求时，如何选择arp请求包的源IP地址。
先看[kernel 文档](https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt)：
```
arp_announce - INTEGER
	Define different restriction levels for announcing the local
	source IP address from IP packets in ARP requests sent on
	interface:
	0 - (default) Use any local address, configured on any interface
	1 - Try to avoid local addresses that are not in the target's
	subnet for this interface. This mode is useful when target
	hosts reachable via this interface require the source IP
	address in ARP requests to be part of their logical network
	configured on the receiving interface. When we generate the
	request we will check all our subnets that include the
	target IP and will preserve the source address if it is from
	such subnet. If there is no such subnet we select source
	address according to the rules for level 2.
	2 - Always use the best local address for this target.
	In this mode we ignore the source address in the IP packet
	and try to select local address that we prefer for talks with
	the target host. Such local address is selected by looking
	for primary IP addresses on all our subnets on the outgoing
	interface that include the target IP address. If no suitable
	local address is found we select the first local address
	we have on the outgoing interface or on all other interfaces,
	with the hope we will receive reply for our request and
	even sometimes no matter the source IP address we announce.

	The max value from conf/{all,interface}/arp_announce is used.

	Increasing the restriction level gives more chance for
	receiving answer from the resolved target while decreasing
	the level announces more valid sender's information.
```
arp请求的发送，大部分情况下是在发送IP包时，需要对端的MAC地址，而本地没有或者需要更新，就需要发送arp请求。这种情况下，在kernel arp处理时，能获取到对应IP包的相关信息。
当然，也可能直接构造arp包来发送，这时候，就没有IP包的信息。

该参数只是控制arp request的源IP，而源MAC是确定的，就是要发包的网卡的MAC地址。对于IP请求引发的arp请求，根据路由就可以确定要从哪个网卡发包；否则，需要指定网卡。
在kernel使用该参数时，arp包的目的IP，源MAC都已经确定。

- 0: kernel默认值，可以使用任何当前节点上的地址。实际上，(如果有)会直接使用IP包的源地址。
- 1: 如果目的IP和IP包的源地址都在当前网卡某个IP的子网中，则使用IP包的源地址。如果没有，fallback到2的逻辑。
- 2: 不考虑IP包的源地址，如果目标地址在当前网卡某个primary IP的子网内，使用该primary IP。如果不存在，选择当前网卡或所有网卡的第一个IP。

下面的内核代码片段可以帮助理解上面的逻辑：
```c
// net/ipv4/arp.c
static void arp_solicit(struct neighbour *neigh, struct sk_buff *skb)
{
...
	switch (IN_DEV_ARP_ANNOUNCE(in_dev)) {
	default:
	case 0:		/* By default announce any local IP */
		if (skb && inet_addr_type_dev_table(dev_net(dev), dev,
					  ip_hdr(skb)->saddr) == RTN_LOCAL)
			saddr = ip_hdr(skb)->saddr;
		break;
	case 1:		/* Restrict announcements of saddr in same subnet */
		if (!skb)
			break;
		saddr = ip_hdr(skb)->saddr;
		if (inet_addr_type_dev_table(dev_net(dev), dev,
					     saddr) == RTN_LOCAL) {
			/* saddr should be known to target */
			if (inet_addr_onlink(in_dev, target, saddr)) //如果设备in_dev上有某个子网使得target和saddr都属于该子网。(target和saddr都是不包含子网的IP地址)
				break;
		}
		saddr = 0;
		break;
	case 2:		/* Avoid secondary IPs, get a primary/preferred one */
		break;
	}
	rcu_read_unlock();

	if (!saddr)
		saddr = inet_select_addr(dev, target, RT_SCOPE_LINK);
...
}
```

arp_announce的值为1和2的区别比较微妙，举几个例子：
```
node1：
eth0: 192.168.20.2/24 192.168.20.13/24(secondary)
eth1: 192.168.10.2/24 192.168.20.12/24

route:
192.168.20.0/24 dev eth0 proto kernel scope link src 192.168.20.2
```
对于 `ping -I 192.168.20.12 192.168.20.20`，ICMP的源IP是`192.168.20.12`，根据路由表，arp包从eth0发出。当eth0的arp_announce取不同值时，arp的源IP为：

0: 192.168.20.12
1: 192.168.20.12 - 目的IP `20.20`和ICMP的源IP `20.12`都在eth0的192.168.20.2/24的子网，所以使用ICMP的源IP(eth1的IP)。
2: 192.168.20.2 - 不考虑ICMP的源IP，`20.20`在eth0的`192.168.20.2/24`子网，所以使用`20.2`作为源IP。

ping -I 192.168.10.2 192.168.20.20，ICMP的源IP是`192.168.10.2`

0: 192.168.10.2
1: 192.168.20.2 - 目的ip20.20和源IP 10.2不属于eth0的某个子网，fallback 到2
2: 192.168.20.2 - 目的ip不属于eth0的某个primary IP的子网，使用eth0的第一个IP

ping -I 192.168.20.13 192.168.20.20，ICMP的源IP是`192.168.20.13`

0: 192.168.20.13
1: 192.168.20.13: `20.13`和`20.20`都属于eth0的subnet
2: 192.168.20.2: 20.13属于eth0 IP 192.168.20.2/24的subnet，使用该IP。

> 关于Primary IP
> 这里的primary ip指的是kernel中`IFA_F_SECONDARY`flag为0，反之为secondary ip。
> ```
> #define IFA_F_SECONDARY            0x01
> ```
> secondary IP最初应该是为了单个网卡上配置多个IP地址，[IP-Aliasing](https://www.kernel.org/doc/html/v5.3/networking/alias.html)，现在已经不需要通过IP-aliasing来配置多个IP了，但是这个方式还可用。
> 通过这种方式配置的IP地址就是secondary ip。
> ```
> # ifconfig eth0:0 200.1.1.1 up
> ```
> 通过`ip`命令指定ip的时候无法指定ip是否是secondary。如果同一个网卡上存在相同网段的ip，新配置的ip就会自动变成secondary。如果原来的primary被删除，secondary ip会自动变成primary ip。

## 接收与arp回复
### arp_filter 与rp_filter
```
rp_filter - INTEGER
	0 - No source validation.
	1 - Strict mode as defined in RFC3704 Strict Reverse Path
	    Each incoming packet is tested against the FIB and if the interface
	    is not the best reverse path the packet check will fail.
	    By default failed packets are discarded.
	2 - Loose mode as defined in RFC3704 Loose Reverse Path
	    Each incoming packet's source address is also tested against the FIB
	    and if the source address is not reachable via any interface
	    the packet check will fail.

	Current recommended practice in RFC3704 is to enable strict mode
	to prevent IP spoofing from DDos attacks. If using asymmetric routing
	or other complicated routing, then loose mode is recommended.

	Default value is 0. Note that some distributions enable it
	in startup scripts.

arp_filter - BOOLEAN
	1 - Allows you to have multiple network interfaces on the same
	subnet, and have the ARPs for each interface be answered
	based on whether or not the kernel would route a packet from
	the ARP'd IP out that interface (therefore you must use source
	based routing for this to work). In other words it allows control
	of which cards (usually 1) will respond to an arp request.

	0 - (default) The kernel can respond to arp requests with addresses
	from other interfaces. This may seem wrong but it usually makes
	sense, because it increases the chance of successful communication.
	IP addresses are owned by the complete host on Linux, not by
	particular interfaces. Only for more complex setups like load-
	balancing, does this behaviour cause problems.

```

主要根据源IP来决定如何应答。

rp_filter 不止对arp包生效，也对其他网络包生效。两者对于arp reply的限制类似。

rp_filter:
0: 没有验证
1：如果回包不从当前网卡发出，验证失败，丢弃包。
2：如果源地址从当前节点所有网卡都不可达，验证失败，丢弃包。

arp_filter
0：可以针对其他网卡的IP回复ARP请求
1：如果路由到ARP的源IP的包从该网卡发出，才发送arp reply。

看起来似乎rp_filter和arp_filter 取0或1的时候，行为应该是一致的

```
node1：
eth0: 192.168.20.2/24 192.168.20.13/24(secondary)
eth1: 192.168.10.2/24 192.168.20.12/24

route:
192.168.20.0/24 dev eth0 proto kernel scope link src 192.168.20.2

node2：
eth0: 192.168.20.100/24 192.168.80.100/24
```

从node-2向node1发送arp请求，如果源地址用192.168.20.100，如`arping -s 192.168.20.100 -I eth0 192.168.20.12`
```
rp_filter和arp_filter至少一个是1, 另一个是0: 只会收到eth0的回包。因为根据node1的路由规则，到192.168.20.100的回包从eth0发出；
rp_filter=2, arp_filter=0: 会收到eth0和eth1的回包，因为根据node-1的路由规，192.168.20.100可达，所以所有网卡都会reply
rp_filter=0, arp_filter=0：会受到eth0和eth1的回包。不需要验证，当前节点有目标Ip，就会reply。
```
如果源地址用192.168.80.100，即`arping -s 192.168.80.100 -I eth0 192.168.20.12`
```
rp_filter和arp_filter至少一个是1, 另一个是0: 不会收到回包，因为没有到192.168.80.100的路由；
rp_filter=2, arp_filter=0: 不会收到回包，因为没有到192.168.80.100的路由；
rp_filter=0, arp_filter=0：会受到eth0和eth1的回包。不需要验证，当前节点有目标Ip，就会reply。
```

### arp_ignore
```
arp_ignore - INTEGER
	Define different modes for sending replies in response to
	received ARP requests that resolve local target IP addresses:
	0 - (default): reply for any local target IP address, configured
	on any interface
	1 - reply only if the target IP address is local address
	configured on the incoming interface
	2 - reply only if the target IP address is local address
	configured on the incoming interface and both with the
	sender's IP address are part from same subnet on this interface
	3 - do not reply for local addresses configured with scope host,
	only resolutions for global and link addresses are replied
	4-7 - reserved
	8 - do not reply for all local addresses
```
主要根据目标IP来决定如何应答。

0：没有限制，给当前节点上的所有IP应答
1：只有目标IP在当前网卡才应答
2：目标IP在当前网卡而且源IP属于目标IP的子网。
3. 如果目标IP的scope是host，则不应答
8：任何IP都不应答

arping -s 192.168.80.100 -I eth0 192.168.20.12
```
0：eth0和eth1都应答
1：eth1应答
2：无应答，因为192.168.80.100不在eth1的网段；如果源地址用192.168.20.100, 则eth1应答。
```
## References
- https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt
- https://unix.stackexchange.com/questions/512371/best-way-to-filter-limit-arp-packets-on-embedded-linux
  - tcpdump只dump arp reply的包：`tcpdump -i eth0 arp and arp[6:2] == 2`
- [filter arp包](https://unix.stackexchange.com/questions/512371/best-way-to-filter-limit-arp-packets-on-embedded-linux)
  - 推荐使用nft
