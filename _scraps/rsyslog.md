---
layout: post
title:  Rsyslog Notes
date: 2020-03-03
update: 2020-03-03
tags: syslog
---

## Syslog Protocol
Syslog protocol 在[RFC5424](https://tools.ietf.org/html/rfc5424)
(obseletes [RFC3164](https://tools.ietf.org/html/rfc3164))中定义。
主要定义了消息的格式，而支持的传输层协议在[RFC5425](https://tools.ietf.org/html/rfc5425) (TLS-based)
和[RFC5426](https://tools.ietf.org/html/rfc5426) (UDP-based)描述

syslog协议中的消息格式的解析和说明网上文章很多，或者直接看RFC，不再赘述。

syslog协议主要的实现有sysklogd，syslog-ng和rsyslog。本文主要涉及[rsyslog](www.rsyslog.com/doc/)。

## Rsyslog
Rsyslog线上文档已经很丰富，本文仅对使用中的一些基本事项简单总结，快速入口备忘。具体的使用还需要查询文档。

### 配置文件格式
rsyslog支持三种配置格式，basic，advanced和legacy。三种格式可以在同一个配置文件共存。在网上看到的各种说明，各种格式的都有，很容易搞不清楚。在官方文档
https://www.rsyslog.com/doc/master/configuration/conf_formats.html 中有很清晰的描述。

**base，即sysklogd格式**：对于简单的匹配facility/severity规则，建议采用这种形式，例如

```
kern.crit     /dev/console
mail.*;mail.!=info   /var/adm/mail
```
**advanced(RainerScript)**：从v6版本引入，除了上述用base格式的地方，都推荐用这种方式，例如

```
template(name="DynamicFile" type="string"
        string="/var/log/remote/%fromhost-ip%/%syslogtag:R,ERE,1,DFLT:([A-Za-z][A-Za-z0-9_./-]*)--end%.log")
action(type="omfile" dynaFile="DynamicFile")
```
**legacy**: 对v7之后版本不推荐使用，但是部分module可能还不支持advanced格式，需要继续使用legacy格式。legacy格式所有指令都以`$`开头。例如

```
$ModLoad imjournal # provides access to the systemd journal
$IMJournalStateFile imjournal.state
```
CentOS 7 默认带的rsyslog.conf还是使用的该格式。

### Rsyslog 与 systemd共存
官方文档：https://www.rsyslog.com/doc/v8-stable/configuration/modules/imuxsock.html#imuxsock-systemd-details-label

以CentOS 7上默认配置为例，rsyslog.conf中相关配置为：
```
$ModLoad imuxsock # provides support for local system logging (e.g. via logger command)
# Turn off message reception via local log socket;
# local messages are retrieved through imjournal now.
$OmitLocalLogging on

$ModLoad imjournal # provides access to the systemd journal
$IMJournalStateFile imjournal.state
```

- /dev/log 是systemd-journald.socket管理的，rsyslog会检测到systemd而不会管理/dev/log。
- rsyslog 通过`imjournal` module把journald的日志导入到rsyslog
- `OmintLocalLogging on`指令让rsyslog不监听system log socket（默认为/dev/log）。
   如果该项设为`off`，会从/dev/log收取日志。所以在`imjournal`同时使用的情况下，日志文件中会有重复。

### ruleset
官方文档 https://www.rsyslog.com/doc/v8-stable/concepts/multi_ruleset.html

ruleset是管理多组rule的有效手段。例如，把所有网络进来的日志和本地日志分开存储，可以使用如下规则。
通过input指定ruleset，然后在ruleset中指定action。

```
module(load="imudp")
input(type="imudp" port="514" ruleset="remote")
module(load="imtcp")
input(type="imtcp" port="514" ruleset="remote")

template(name="DynamicFile" type="string"
        string="/var/log/remote/%fromhost-ip%/%syslogtag:R,ERE,1,DFLT:([A-Za-z][A-Za-z0-9_./-]*)--end%.log")

ruleset(name="remote"){
    action(type="omfile" dynaFile="DynamicFile")
}

```

syslog client
---------------

- shell 下可以使用logger命令测试
- glibc使用syslog函数(`man 3 syslog`)
- Python 可以直接使用`syslog`库，也可以设置logging 使用syslog
