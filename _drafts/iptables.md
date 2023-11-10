
官方文档：table和chain的顺序 [Chapter 6. Traversing of tables and chains](https://rlworkman.net/howtos/iptables/chunkyhtml/c962.html)
https://upload.wikimedia.org/wikipedia/commons/3/37/Netfilter-packet-flow.svg

Trace/LOG
-j LOG log当前rule

-j TRACE 从匹配的rule开始trace

比较新的iptables(nftables)实现不是log到kernel log，而是使用xtables-monitor -t 来获取日志
https://serverfault.com/questions/1109845/i-cannot-get-iptables-to-show-trace-logs

[iptables: The two variants and their relationship with nftables](https://developers.redhat.com/blog/2020/08/18/iptables-the-two-variants-and-their-relationship-with-nftables#)

man iptables-extensions

man nft
nft list ruleset

https://www.cyberciti.biz/tips/linux-iptables-how-to-flush-all-rules.html
