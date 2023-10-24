---
layout: post
title: linux 下域名解析
date: 2023-10-24
tags: dns
---

简单来说，DNS(域名系统)是将域名映射为IP地址的服务，域名长度限制为255。DNS server使用TCP或UDP的53端口提供服务。

但是在实际使用中，DNS并不是IP地址与域名映射的唯一选择，例如在Linux下周知的/etc/hosts。
所以，在Linux下(其他操作系统下应该类似)，不能把域名/主机名解析和DNS协议混为一谈。

Linux下kernel中没有实现域名解析，而是在用户态实现。

## glibc的域名解析
glibc的`gethostbyname`等函数通过配置文件`/etc/nsswitch.conf`来指定域名解析时的方法和顺序。相关的配置项为`hosts：`行，例如：
```
hosts:      files dns myhostname
```
其中

* `files`指`/etc/hosts`文件
* `dns`指使用`/etc/resovl.conf`中指定的DNS server
* `myhostname`使得系统至少可以解析自己的hostname，即使其他方式，如 `/etc/hosts` 或 dns server 无法解析。

另外还有很多其他的关键字可用，如比较新的版本可以使用`resolve`来使用`systemd-resolved`服务来解析域名。
具体有哪些可用，跟glibc版本以及发行版有关，需要参考相关文档。

> `nsswitch.conf`: Name service switch configuration file
>
> 该文件不止包含域名解析的配置，还包含其他各种名字解析相关的配置。例如`group`，`passwd`分别配置用户组和用户密码从哪里读取。
>
> 另外，虽然glibc提供这个文件，但是其他应用也会使用。如Golang的域名解析也会使用，但是并不使用glibc的实现，所以实现逻辑可能会有细微差别。

可参考<https://unix.stackexchange.com/questions/738701/what-is-the-order-in-which-linux-resolves-dns>

## systemd-resolved 服务
`systemd-resolved`是`systemd`的一部分，实现了很多高级功能，它提供了三种接口进行域名解析：

* 原生的 Bus API，这是systemd-resolved 官方推荐的方案，包含最完整的特性。
* 通过glibc的API，即上文glibc域名解析中说的，需要在nsswitch.conf配置resolve。
* 服务会在127.0.0.53上启动一个本地的dns server。

## 非glibc的域名解析
* 绝大多数链接glibc的程序，会使用glibc的`gethostbyname`等API来解析域名，就会走glibc的逻辑；
* 上文提到的Golang等的程序，会自己实现，但是实现逻辑和glibc类似，最终行为也类似；
* `nslookup` / `dig`等工具，是为了测试DNS server的，会读取/etc/resolv.conf或手动指定；
* 其他应用，如浏览器等，也可能会自己实现域名解析；
* kernel中实现了一个调用用户态域名解析的机制。

整体来说，当遇到域名解析相关的问题时，需要具体问题具体分析。虽然域名解析看起来是一项网络基础功能，但它并没有项TCP/IP协议栈中的大部分协议一样直接由内核提供。
