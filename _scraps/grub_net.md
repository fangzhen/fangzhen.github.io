---
layout: post
title: grub2 pxe 启动配置文件搜索逻辑
date: 2024-01-31
tags: pxe grub2
---

之前遇到一个问题，虽然最后的原因跟grub没关系，不过在分析case的过程中看了下grub的相关实现，也借此记录一下。

## grub启动流程
grub启动的总体流程入口：`grub-core/kern/main.c:grub_main`，跟本case相关的启动过程主要有：
1. 设置root和prefix变量。
   * 对EFI环境，增加了`fw_path`变量[*]，用于替代`prefix`变量。`fw_path`被设置为grub二进制所在的路径。
1. 进入normal模式后，依次尝试使用fw_path和prefix搜索配置文件，直至找到一个配置文件[*]。搜索的逻辑为：
   * 对应实现在：`grub-core/net/net.c:grub_net_search_configfile`。会依次尝试以下文件：
     假设MAC地址为aa:bb:cc:dd:ee:ff，IP地址为10.20.0.6，IP对应的十六进制为`0A140006`
     ```
     $path/grub.cfg-01-aa-bb-cc-dd-ee-ff
     $path/grub.cfg-01-aa-bb-cc-dd-ee-ff
     $path/grub.cfg-0A140006
     $path/grub.cfg-0A14000
     $path/grub.cfg-0A1400
     $path/grub.cfg-0A140
     $path/grub.cfg-0A14
     $path/grub.cfg-0A1
     $path/grub.cfg-0A
     $path/grub.cfg-0
     $path/grub.cfg
     ```
   * 通过网络访问文件时，有重试，默认重试次数为`#define GRUB_NET_TRIES 40`。
1. 如果没找到配置文件，失败进入grub命令行，否则
1. 读取配置文件，并根据配置文件启动。

有一些逻辑不是在grub的上游代码中，而是在redhat系srpm的patch中提供的，包括：
1. `fw_path`相关的逻辑，参考<https://fedoraproject.org/wiki/Changes/UnifyGrubConfig>。
2. 根据MAC和IP地址搜索grub.cfg的逻辑。

## case study
### 问题描述
现象：通过PXE启动的节点偶尔出现下载配置文件失败，进入grub命令行。

从tftp侧的日志看，正常的情况下，固件下载grubaa64.efi后，grubaa64.efi启动，下载配置文件`grub.cfg-01-<mac>`
```
Jan 30 05:02:13 node-1 in.tftpd[11461]: RRQ from 10.20.0.5 filename grub/grubaa64.efi
Jan 30 05:02:13 node-1 in.tftpd[11461]: Client 10.20.0.5 finished grub/grubaa64.efi
Jan 30 05:02:13 node-1 in.tftpd[11463]: RRQ from 10.20.0.5 filename grub/grub.cfg-01-fa-16-3e-e5-d0-3d
Jan 30 05:02:13 node-1 in.tftpd[11463]: Client 10.20.0.5 finished grub/grub.cfg-01-fa-16-3e-e5-d0-3d
```
出问题的情况下，尝试下载了很多文件。
```
Jan 30 05:17:40 node-1 in.tftpd[11936]: RRQ from 10.20.0.6 filename grub/grubaa64.efi
Jan 30 05:17:40 node-1 in.tftpd[11936]: Client 10.20.0.6 finished grub/grubaa64.efi
Jan 30 05:18:12 node-1 in.tftpd[11985]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-01-fa-16-3e-d3-86-f6
Jan 30 05:18:12 node-1 in.tftpd[11985]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-01-fa-16-3e-d3-86-f6
Jan 30 05:18:12 node-1 in.tftpd[11986]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-0A140006
Jan 30 05:18:12 node-1 in.tftpd[11986]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-0A140006
Jan 30 05:18:12 node-1 in.tftpd[11987]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-0A14000
Jan 30 05:18:12 node-1 in.tftpd[11987]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-0A14000
Jan 30 05:18:12 node-1 in.tftpd[11988]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-0A1400
Jan 30 05:18:12 node-1 in.tftpd[11988]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-0A1400
Jan 30 05:18:12 node-1 in.tftpd[11989]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-0A140
Jan 30 05:18:12 node-1 in.tftpd[11989]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-0A140
Jan 30 05:18:12 node-1 in.tftpd[11990]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-0A14
Jan 30 05:18:12 node-1 in.tftpd[11990]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-0A14
Jan 30 05:18:12 node-1 in.tftpd[11991]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-0A1
Jan 30 05:18:12 node-1 in.tftpd[11991]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-0A1
Jan 30 05:18:12 node-1 in.tftpd[11992]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-0A
Jan 30 05:18:12 node-1 in.tftpd[11992]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-0A
Jan 30 05:18:12 node-1 in.tftpd[11993]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg-0
Jan 30 05:18:12 node-1 in.tftpd[11993]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg-0
Jan 30 05:18:12 node-1 in.tftpd[11994]: RRQ from 10.20.0.6 filename /EFI/BOOT/grub.cfg
Jan 30 05:18:12 node-1 in.tftpd[11994]: Client 10.20.0.6 File not found /EFI/BOOT/grub.cfg
```
### 问题分析
正常的情况下，下载`grub/grub.cfg-01-fa-16-3e-e5-d0-3d`就是上面流程中搜索grub文件时，尝试`$fw_path/grub.cfg-01-<mac>`，成功之后流程就往下走了。

异常的情况下，日志记录第一个下载的文件是`/EFI/BOOT/grub.cfg-01-fa-16-3e-d3-86-f6`，`EFI/BOOT`其实是`$prefix`的值，也就是尝试`$fw_path`失败之后开始尝试`prefix`下的文件。

其中有几个点值得注意：
1. 下载完grubaa64.efi之后，每次异常情况都是经过大概32秒的时间下载`/EFI/BOOT/grub.cfg-01-fa-16-3e-d3-86-f6`。从这点可以基本排除随机的网络问题，因为不应该每次都这么精准地卡点。
2. 猜测上条中间隔的32秒，grub在尝试`$fw_path`下的文件，根据上面的分析，grub会在`$fw_path`下根据MAC和IP尝试多个文件，但是从日志来看，每次出问题都是完全没有`$fw_path`相关的日志。
   - 后来看代码发现，这块grub实现上确实有小bug，在尝试`$fw_path/grub.cfg-01-<mac>`失败之后，在特定的代码路径下，会跳过`$fw_path`的后续尝试。

> 问题的原因后来定位到是跟tftp server所在节点的网络配置相关。grub在tftp下载前需要通过arp协议获取MAC地址。而tftp server的rp_filter被设置为1，导致所有网卡都会以自己的mac地址reply。
> 然而节点上的iptables规则禁止了某个网卡的请求，导致如果grub发送tftp请求使用的是该网卡的mac地址，就会失败。

## Reference
- grub2 source
- grub2 srpm (grub2-2.02-99)
