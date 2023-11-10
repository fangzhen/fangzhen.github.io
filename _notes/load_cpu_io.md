---
layout: post
title: Linux 系统负载，iowait，IO
date: 2023-11-10
tags: load iowait
---

## iowait
简单来说，iowait 是指CPU处于idle状态，而且至少有一个进行中的I/O操作。
iowait的值不够准确(或者说跟直觉不相符)，比如：
1. CPU不会等IO结束，而是会调度到可以运行的其他任务。
   例如：单核CPU，只有一个任务A，50%的时间等待IO，50%的时间使用CPU计算，那么iowait是50%；
   如果另外还有一个任务B，任务B一直使用CPU，没有IO操作，那么CPU会在任务AB间切换，iowait变成了0，但实际上任务A还是有一半的时间在等待IO。
2. 多核CPU系统中，等待IO的任务没有在任何CPU上执行，等IO ready之后它可能会被调度到不同于之前的CPU上运行，所以单个CPU的iowait不太有用。
3. 在某些情况下iowait的值会变小。(不太清楚具体情况，可能在多核下有race等情况，例如https://lkml.indiana.edu/hypermail/linux/kernel/1303.2/01398.html)
4. iowait高也不意味这系统一定有问题。例如执行`dd`等主要做IO的程序时，可能看到的iowait非常高。

### kernel如何获取CPU状态
linux的进程调度器需要管理CPU和进程状态。`task_struct`包含`in_iowait`字段，指示进程的iowait状态，进程调度时更新相关字段。
`cpu_usage_stat`记录CPU的使用情况，内核每次执行时钟中断处理中，会对CPU的使用情况进行统计。

`cpu_usage_stat`的相关统计是从开机累加的，所以像`vmstat`, `iostat`等工具一定间隔获取并计算可以得到过去一段时间的使用统计。

进程具体在什么情况下会被认为是等待IO完成，可能无法一概而论。大致来说，iowait指的是文件IO，包括对文件系统的读写，对磁盘块的读写等。一般来说，这些进程会处于D状态。
一般情况下网络(socket)，pipe, tty等IO不计入iowait，但是访问网络文件系统，如nfs是会计入的。

## 系统负载
简单来说，Linux下，系统负载不止包含可运行的任务，也包含处于uninterruptible sleep状态(D)的任务。Linux试图给出整体系统负载而不只是CPU负载。
可以使用`uptime`等命令查看1, 5, 15分钟的平均负载。

反过来，当系统负载高时，也不必然意味着CPU不够用，需要结合其他指标综合来看。

### Linux Uninterruptible Tasks
kernel中使用不可中断状态(TASK_UNINTERRUPTIBLE)来避免响应signal，也就是处于D状态的进程无法通过`kill`等命令杀死，只能等任务满足条件后回到可运行状态。
使用不可中断状态的主要是disk IO(例如direct IO 以及buffered IO中与disk交互的部分)和一些lock。

## Linux IO - 阻塞/非阻塞 同步/异步
**这几个词在不同的上下文/领域中的意思是不一致的。**

阻塞/非阻塞用于IO的情况比较多。比如`read()`系统调用，如果fd没有设置`O_NONBLOCK`flag，就会阻塞当前执行的进程，否则直接返回`EAGAGIN/EWOULDBLOCK`。
而同步本质上是指多个实体之前有互相协调，异步反之。从单一实体的角度来看，异步调用后直接返回，不等待结果。因此**异步通常有相关的机制来获取结果(达到同步的效果)。**
例如在Linux IO中，异步读是指调用立刻返回，而不等数据实际读取到，即使当时就有数据可读。

Linux的异步IO可能特指`aio`或者`io_uring`。

### IO 多路复用与io_uring
各种讲select，poll, epoll机制与实现的文章有很多，本文不再赘述。他们都是使用类似的思路解决如何实现高性能IO的问题。解决思路就是通过事件通知机制。
当进程需要同时访问多个IO时，可以不必阻塞/同步地挨个等待每个IO，而是当某个IO可用时，再去访问。比如服务器应答多个客户端等场景。
本质上是通过设置NONBLOCK flag + 内核事件通知来实现。

`io_uring`是linux在`aio`之后引入内核，提出/实现了一个通用且优雅的异步系统调用方案，而不只是像epoll用于网络，aio用于文件的受限方案。

## Reference:
* iowait
  - [What exactly is "iowait"?](https://blog.pregos.info/wp-content/uploads/2010/09/iowait.txt)
  - https://serverfault.com/questions/12679/can-anyone-explain-precisely-what-iowait-is
  - CPU可以处于不同状态：user, system, idle, iowait 等，可参考`man 5 procfs`。
  -  https://serverfault.com/questions/37441/does-iowait-include-time-waiting-for-network-calls>
* kernel如何判断CPU处于什么状态
  - <https://unix.stackexchange.com/questions/410628/how-does-a-cpu-know-there-is-io-pending>
  - <https://stackoverflow.com/questions/35402711/how-does-a-kernel-come-to-know-that-the-cpu-is-idle>
  - <https://www.kernel.org/doc/html/v5.0/admin-guide/pm/cpuidle.html>
* system load & Uninterruptible sleep
  - [Linux Load Averages: Solving the Mystery](http://www.brendangregg.com/blog/2017-08-08/linux-load-averages.html)：
    Brandan Gregg写的linux load的文章，讲了linux load average以及其他的性能分析指标。还考证了最初从CPU load改为system load的历史。
  - [What Is an Uninterruptible Process in Linux?](https://www.baeldung.com/linux/uninterruptible-process)
  - [High System Load with Low CPU Utilization on Linux?](https://tanelpoder.com/posts/high-system-load-low-cpu-utilization-on-linux/)：一个详细的分析实例。
* Linux IO
  - [io_uring is not an event system](https://despairlabs.com/blog/posts/2021-06-16-io-uring-is-not-an-event-system/)
  - [Async IO on Linux: select, poll, and epoll](https://jvns.ca/blog/2017/06/03/async-io-on-linux--select--poll--and-epoll/)
  - [Linux – IO Multiplexing – Select vs Poll vs Epoll](https://devarea.com/linux-io-multiplexing-select-vs-poll-vs-epoll/)：包含示例代码
  - [stackoverflow 上关于同步/异步 阻塞/非阻塞的讨论](https://stackoverflow.com/a/2625565/2705629)
  - [[译] Linux 异步 I/O 框架 io_uring：基本原理、程序示例与性能压测（2020）](http://arthurchiao.art/blog/intro-to-io-uring-zh)
