---
layout: post
title: dnsmasq根据架构提供不同的Bootfile
date: 2023-10-19
tags: pxe dnsmasq
---

PXE的简单过程为：
1. 机器上电，从PXE启动；
2. 固件(BIOS或UEFI)发送dhcp请求，请求中包含[PXE相关的选项](https://datatracker.ietf.org/doc/html/rfc4578)；
3. DHCP server收到DHCP请求，返回DHCP response
4. PXE client收到DHCP回复，其中包含bootfile-name和bootfile-size。
5. PXE从DHCP server下载bootfile并执行。bootfile可能是bootloader，bootloader接下来加载kernel等。

## 根据架构提供不同的PXE启动文件
一个PXE/DHCP server可以给不同架构的机器提供服务。而不同架构有不同的指令集和执行环境，所以bootfile无法通用。
那么当DHCP server收到不同机器的DHCP请求时，如何判断应该返回哪个bootfile呢？

[RFC 4578](https://datatracker.ietf.org/doc/html/rfc4578)中定义了PXE的DHCP option。
其中包含了客户端系统架构选项，根据规范，PXE客户端的DHCP请求必须包含该选项。格式如下：

```
                Code  Len  16-bit Type
               +----+-----+-----+-----+
               | 93 |  n  | n1  | n2  |
               +----+-----+-----+-----+
```

`dnsmasq`支持通过该选项识别客户端架构，示例设置为：
```
dhcp-match=set:UEFI64_x86,option:client-arch,7
dhcp-boot=tag:UEFI64_x86,grub/grubx64.efi,boothost,10.10.10.1

# inspect the vendor class string and match the text to set the tag
dhcp-match=set:EFI_aarch64,option:client-arch,11
dhcp-boot=tag:EFI_aarch64,grub/grubaa64.efi,boothost,10.10.10.1
```
以上片段把client-arch为7的PXE 请求tag设置为UEFI64_x86，并使用bootfile grub/grubx64.efi，类似地，对aarch64,使用grubaa64.efi作为bootfile。

## References
* [RFC 4578](https://datatracker.ietf.org/doc/html/rfc4578)发布于2006年，其中定义的客户端架构只有0-9共10个。
  更新的支持PXE的架构没有包含其中，而且没有发布新的RFC。
  最新的分配可以在[iana](<https://www.iana.org/assignments/dhcpv6-parameters/dhcpv6-parameters.xhtml#processor-architecture>)查询。
* [pxe spec](http://www.pix.net/software/pxeboot/archive/pxespec.pdf)
* <https://stackoverflow.com/questions/58921055/pxe-boot-arch-field-dhcp-option-93>
