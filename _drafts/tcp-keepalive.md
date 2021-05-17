---
layout: post
title:  "tcp keepalive"
date: 2019-02-01
tags: network
---

busybox_warpper hang住问题
相关示例代码很简单

import requests
r = requests.get(req_url)
res = r.json()
hang 在了requests.open 上，原因是requests连接之后等待reponse。
测试时应该断开了br-mgmt网络或类似操作，导致连不上busybox了。默认没有超时也没有tcp keepalive，所以就一直等，在client这端看连接还在，但是busybox已经重启了。

http://docs.python-requests.org/en/master/user/advanced/#timeouts

Most requests to external servers should have a timeout attached, in case the server is not responding in a timely manner. By default, requests do not time out unless a timeout value is set explicitly. Without a timeout, your code may hang for minutes or more.
解决方案是给请求中用到的socket设置keepalive option。设置方法稍微有点hack，参考https://stackoverflow.com/a/35278688/7543666

没有直接设置requests.get()的timeout是因为busybox api的超时时间有的很长有的很短，没办法统一设置。

连上之后down掉busybox的网卡，一分钟左右会失败：
```
Traceback (most recent call last):
  File "x.py", line 21, in <module>
    r = s.get(url)
  File "/usr/lib/python2.7/site-packages/requests/sessions.py", line 488, in get
    return self.request('GET', url, **kwargs)
  File "/usr/lib/python2.7/site-packages/requests/sessions.py", line 475, in request
    resp = self.send(prep, **send_kwargs)
  File "/usr/lib/python2.7/site-packages/requests/sessions.py", line 596, in send
    r = adapter.send(request, **kwargs)
  File "/usr/lib/python2.7/site-packages/requests/adapters.py", line 499, in send
    raise ReadTimeout(e, request=request)
requests.exceptions.ReadTimeout: HTTPConnectionPool(host='busybox.openstack.svc.cluster.local', port=80): Read timed out. (read timeout=None)
```

https://zhuanlan.zhihu.com/p/28894266
cat /proc/net/ip_conntrack
cat /proc/net/nf_conntrack
http://veithen.io/2013/12/19/inspecting-socket-options-on-linux.html
http://tldp.org/HOWTO/TCP-Keepalive-HOWTO/overview.html

https://staaldraad.github.io/2017/12/20/netstat-without-netstat/


go http:
tcp keepalive https://nanxiao.me/en/a-brief-intro-of-tcp-keep-alive-in-gos-http-implementation/
http keepalive https://tonybai.com/2021/01/08/understand-how-http-package-deal-with-keep-alive-connection/
