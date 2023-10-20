---
layout: post
title: 使用iptables重定向特定流量到localhost
tags: iptables dnat nat
date: 2023-10-18
---

## Case说明
起因是想在虚拟机guest中访问Host上的一个服务，但是host上的服务只监听了localhost。

1. 添加iptables规则，把虚机中访问Host `192.168.122.1:1080`的目的地址转到`127.0.0.1`：
   ```
   sudo iptables -t nat -I PREROUTING -p tcp --dport 1080 -s 192.168.122.0/24 -d 192.168.122.1 -j DNAT --to 127.0.0.1
   ```

2. 但是上述命令执行后还不行，[还需要修改一个系统参数](https://unix.stackexchange.com/questions/111433/iptables-redirect-outside-requests-to-127-0-0-1)，
   其中`virbr0`是`192.168.122.1`所在的网络设备：
   ```
   sudo sysctl -w net.ipv4.conf.virbr0.route_localnet=1
   ```
   当然，另一个配置`net.ipv4.ip_forward=1`也需要正确。

> **持久化**
>
> iptables规则可以通过iptables-save 或手动编辑配置文件来持久化。(archlinux上文件为`/etc/iptables/iptables.rules`)。
>
> sysctl 规则写入`/etc/sysctl.d/`等来持久化。

## 关于route_localnet
[kernel documentation](https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt)的说明：

```
route_localnet - BOOLEAN
	Do not consider loopback addresses as martian source or destination
	while routing. This enables the use of 127/8 for local routing purposes.
	default FALSE
```
即不要loopback地址作为源或目的地址的报文当作火星报文。
简单来说，火星报文(martian packet)是指不该出现的报文。比如这里，以loopback地址为源地址或目的地址的包出现在了非`lo`端口上。

### 打开后的安全问题
[此处](https://security.stackexchange.com/questions/137602/what-are-the-security-implications-of-net-ipv4-conf-eth0-route-localnet-1-rout)有个讨论。
在我看来，主要的安全问题是打开后通过类似文首案例的方式其实打破了监听localhost带来的一些常规假设，比如只监听了localhost的服务应该只能被本地节点访问。
但实际上通过iptables规则，就实现了把localhost上的服务暴露出去。

这个看起来很不起眼的小问题，放到一个大系统里，就可能带来比较严重的安全漏洞。
例如kubernetes的[CVE-2020-8558](https://github.com/kubernetes/kubernetes/issues/92315)，就是因为kube-proxy默认打开了route_localnet，会导致无认证的api-server可能会被外部访问等问题。
相关讨论也可参考<https://github.com/kubernetes/kubernetes/issues/90259>。
