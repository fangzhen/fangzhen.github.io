---
layout: post
title: linux 下进程的组织结构及应用
tags: ssh openssh session process pgid pgrp
date: 2022-12-13
update: 2022-12-13
---

## Linux中进程组织结构
https://www.win.tue.nl/~aeb/linux/lk/lk-10.html 讲的比较简要且清晰。

### 进程创建与退出
使用`fork`系统调用创建进程。一般情况下，父进程需要wait子进程，否则子进程结束后就会变成`Z`状态，即进程表里还有条目，但是进程已经完成。

参考： <https://www.tutorialspoint.com/what-is-zombie-process-in-linux>

如果父进程没有wait，等父进程也退出后，子进程会被reparent。历史上，子进程总是被init(pid 1)进程收养。
Linux 3.4以后和有些BSD实现中，其他进程也可以通过`prctl` 系统调用设置`PR_SET_CHILD_SUBREAPER`参数，从而收养它的后代进程。

参考：<https://unix.stackexchange.com/questions/149319/new-parent-process-when-the-parent-process-dies>

如果希望父进程退出后，子进程也退出，类似逻辑需要在进程业务中自己实现，kernel不提供此类功能。

### session和 process group

参考：<https://www.informit.com/articles/article.aspx?p=397655&seqNum=6?>  
`man 2 setsid` `man 2 setpgid`

每个用户登陆系统后，可能要执行不同的任务，有些要后台执行，有些前台交互执行。
当用户从系统中登出的时候，操作系统可能需要结束用户运行的所有进程。
为了实现这类需求，Linux/Unix中除了简单的父子关系，也引入了进程组和会话来管理进程。

每个进程都通过`sid`和 `pgid`来标志它的会话和进程组。子进程的`sid`和`pgid`默认继承自父进程。
通过`setsid, setpgid` 系统调用可以设置`sid`和`pgid`。
同一个进程组中的进程只能属于一个会话。
通过`setsid`设置自己的`sid`为自己的`pid`的进程也成为session leader。

会话中的进程可以从终端中获取输入以及发送输出，该终端就是会话的控制终端（controlling termimal）。一个会话中有多个进程组时，只有一个进程组从终端获取输入，是为该终端的前台进程组。
当session leader 退出时，kernel会给该controlling terminal的前台进程组中的所有进程发送HUP信号。

**孤儿进程组**

如果某进程退出导致某个进程组新变成孤儿进程组，而且该孤儿进程组中有stopped的进程，那么该进程组中所有进程都会被发送`HUP`和`CONT`信号。

举个容易理解的例子：shell中启动一个任务，然后暂停该任务，然后通过kill -9杀掉shell进程，那么中止的任务也可以被清理掉。如果没有对孤儿进程组的处理，被stop的进程就会被永久留在系统中。
```
$ bash
$ sleep 101
^Z
[1]+  Stopped                 sleep 101
$ ps -o pid,sid,pgid,ppid,stat,command
    PID     SID    PGID    PPID STAT COMMAND
   6190    6190    6190    6152 Ss   /bin/bash
  97520    6190   97520    6190 S    bash
  97542    6190   97542   97520 T    sleep 101
  97543    6190   97543   97520 R+   ps -o pid,sid,pgid,ppid,stat,command
$ kill -9 97520
Killed
$ ps -o pid,sid,pgid,ppid,stat,command
    PID     SID    PGID    PPID STAT COMMAND
   6190    6190    6190    6152 Ss   /bin/bash
  97563    6190   97563    6190 R+   ps -o pid,sid,pgid,ppid,stat,command
```
上述示例中，如果后台执行任务，例如`sleep 101 &`，则不会被清理。

### kernel中相关数据结构

```
//include/linux/sched.h
struct task_struct {
    /* Real parent process: */
    struct task_struct __rcu	*real_parent;
    /* Recipient of SIGCHLD, wait4() reports: */
    struct task_struct __rcu	*parent;
    struct task_struct		*group_leader;
    struct signal_struct		*signal;
    ...
}

//include/linux/signal.h
struct signal_struct {
    struct pid *tty_old_pgrp;
    /* boolean value for session group leader */
    int leader;

    struct tty_struct *tty; /* NULL if no tty */
    ...
}

//kernel/sys.c includes impl of `setpgid, setsid` etc.
```

### login shell
shell作为用户登陆系统的一环运行，shell进程会作为session leader，而且分配controlling terminal。例如图形界面下通过终端仿真器（如Konsole）打开的终端或者ssh打开的伪终端。
而用户登陆后运行的shell(脚本)，就是non-login shell。

`w`列出当前登陆用户和正在执行的命令

参考 <https://unix.stackexchange.com/questions/50665/what-is-the-difference-between-interactive-shells-login-shells-non-login-shell>

> Note: systemd-logind里的session是个不同的概念，与本文的讨论无关。

## nohup如何工作

`nohup`经常被用于远程ssh连接时运行不想被中断的命令。关于`openssh`的行为下节再讨论。

可以把`nohup`执行过程大致分为两部分：

1. setup，包括但不限于以下动作：
   1. 设置`HUP`的singnal handler为ignore；
   2. 如果stdin/stdout/stderr是终端，重定向它们。
2. 通过execvp执行命令

参考：<https://unix.stackexchange.com/questions/316186/how-does-nohup-work>

那么，被`nohup`执行的命令一定能规避掉因`HUP`信号而退出吗？

答案是不能，`nohup`不能阻止信号发送到进程，只是把signal handler改成了`ignore`。
如果我们被`nohup`执行的命令重新定义`HUP`的signal hander，`HUP`信号仍然有会被处理。

例如下面的c程序，通过`kill -HUP <pid>`，仍然可以执行到hander function中。
看下面示例：

```
#include<stdio.h>
#include<signal.h>
#include<unistd.h>
void sig_handler(int signum){

  //Return type of the handler function should be void
  printf("\nInside handler function\n");
}

int main(){
//  signal(SIGINT,sig_handler); // Register signal handler
  signal(SIGHUP,sig_handler); // Register signal handler
  for(int i=1;;i++){    //Infinite loop
    printf("%d : Inside main function\n",i);
    fflush(stdout); // force flush to avoid no output in nohup,out
    sleep(1);  // Delay for 1 second
  }
  return 0;
}
```

执行结果如下：
```
...
20 : Inside main function
Inside handler function
21 : Inside main function
...
```

> Note：python的`signal.signal()`改`HUP`的hander是不行的，因为它修改的不是进程的signal handler，而是在python的signal hander内部逻辑做的修改。

## openssh 行为探究
> ssh版本和kernel版本为
> ```
> OpenSSH_9.1p1, OpenSSL 3.0.7 1 Nov 2022
> Linux manjaro 5.4.224-1-MANJARO #1 SMP PREEMPT Fri Nov 11 07:45:42 UTC 2022 x86_64 GNU/Linux
> ```

不深入openssh的实现细节，简单来说，ssh会登陆远程机器并在远程机器上执行命令。
ssh在远程机器上是否分配pseudo-terminal的情况下会有不同的行为，
```
-T      Disable pseudo-terminal allocation.

-t      Force pseudo-terminal allocation.  This can be used to execute arbitrary screen-based programs on a remote machine, which can be very useful, e.g. when implementing menu services.  Multiple
        -t options force tty allocation, even if ssh has no local tty.
```
默认不指定`-t/-T`参数的情况下，不指定命令会启动login shell并分配伪终端，直接执行命令不会分配。（测试看情况如此，没有代码级证据）。

```
$ ssh -p 202  fangzhen@127.0.0.1
$ ps -eo pid,ppid,sid,pgid,command --forest
    555       1     555     555 sshd: /usr/bin/sshd -D [listener] 0 of 10-100 startups
  13468     555   13468   13468  \_ sshd: fangzhen [priv]
  13470   13468   13468   13468      \_ sshd: fangzhen@pts/8
  13482   13470   13482   13482          \_ -bash
```
```
$ ssh -p 202  fangzhen@127.0.0.1 bash
$ ps -eo pid,ppid,sid,pgid,command --forest
    555       1     555     555 sshd: /usr/bin/sshd -D [listener] 0 of 10-100 startups
  13599     555   13599   13599  \_ sshd: fangzhen [priv]
  13601   13599   13599   13599      \_ sshd: fangzhen@notty
  13613   13601   13613   13613          \_ bash

```
可以看到，根据是否分配伪终端，sshd给ssh连接创建的子进程分中分别有`pts`和`notty`字样。伪终端下的bash进程为`-bash`，说明这个一个login shell。
另外注意到用户进程是自己的pgid和sid，并不会用上述sshd子进程的。

### ssh client和server断开时的行为
ssh断开大致可分为两种情况：

1. 网络没问题的情况下ssh client退出
2. 网络有问题的情况下，ssh client和server连接断开

> Note: 下面进程列表都是类似下面命令的结果截取：
>
> `ps -eo pid,ppid,sid,pgid,stat,command --forest | grep -B4 'slee[p]'`

#### 不分配伪终端

使用如下命令测试：

`$ ssh -T -p 202  fangzhen@127.0.0.1  "echo > /tmp/sshtest; trap 'echo int>>/tmp/sshtest; exit' INT; trap 'echo hup>>/tmp/sshtest; exit' HUP; trap 'echo term >> /tmp/sshtest; exit' TERM; trap 'echo pipe >> /tmp/sshtest; exit' PIPE; while true; do sleep 5 && echo 123; done"`

注意bash的信号处理，当通过`trap action SIGNAL`处理信号时：

1. 它会等当前执行的命令返回后才会执行trap的action；
2. 对应SIGNAL的handler就被改成了修改后的action，默认的handler不会执行，所以我们在trap action里都加上了exit。

**行为描述：**

1. 通过Ctrl-C或者kill ssh命令（ssh 命令收到INT, TERM, HUP, KILL等信号的情况下）

   ssh 命令会立即中断，`sshd: [priv]`和`sshd: notty`进程也会立即退出（推测是因为server侧检测到tcp连接断开），但是远程执行的命令不会立即退出。
   说明sshd不会发送信号给用户命令进程，但是在子进程执行到echo 命令输出时因为pipe已中断，由操作系统发送SIGPIPE信号。

   如果上述命令中 去掉`echo`命令，server侧的用户命令无法检查到连接已断开，会一直运行下去直到完成。也不会出发到上面session leader退出或孤儿进程组发送`HUP`信号的场景。

2. client与server间网络断开

   >Note: 通过iptables命令 `sudo iptables -I INPUT -p tcp --dport 202 -i lo -j DROP` 阻断client和server的数据连接
   >
   > 需要给sshd_config 添加如下配置，让server端快速检查到连接断开
   > ```
   > ClientAliveInterval 30
   > ClientAliveCountMax 1
   > ```
   >
   > 上述ssh命令执行后，再执行上述iptables命令。

   执行后kill掉客户侧ssh 命令并不会立即引起`sshd`侧的这个连接的`sshd: [priv]`和`sshd: notty`进程退出。
   当30s后，server端检测到连接已断开，会回到网络正常情况下client正常断开的处理逻辑（先是两个sshd进程退出，然后用户命令因为pipe断开而退出）。

#### 分配伪终端的情况

使用类似命令测试，只是改成`-t`参数分配伪终端：

`$ ssh -t -p 202  fangzhen@127.0.0.1  "echo > /tmp/sshtest; trap 'echo int>>/tmp/sshtest; exit' INT; trap 'echo hup>>/tmp/sshtest; exit' HUP; trap 'echo term >> /tmp/sshtest; exit' TERM; trap 'echo pipe >> /tmp/sshtest; exit' PIPE; while true; do sleep 5 && echo 123; done"`

**行为描述：**

1. kill客户侧ssh（TERM INT KILL HUP信号）

   kill命令执行后，客户侧ssh断开，server侧`sshd: [priv]`和`sshd: pts`进程退出并主动给用户命令进程(bash)发送hup信号，bash处理hup信号，等待`sleep 5`执行完，进入HUP的trap action，然后退出。
2. ssh命令启动后直接ctrl+c中断执行：

   这种情况下与没有伪终端情况下的`Ctrl+C`不一样。有伪终端的情况下，`Ctrl+C`按键实际上会发送到远程的伪终端。
   那么`bash`进程和`sleep`进程都会收到`INT` 信号而立即退出，而不是bash收到hup信号然后等待sleep执行完后退出。
3. client和server连接断开

  在server端检测到连接已经断开后，回到a中网络正常情况下的client断开逻辑。

### 远程命令中父进程先于子进程完成的情况(后台执行)
上面都是远程命令前台执行的情况下的异常断开情况下的行为。
我们要想命令在远程机器的后台执行，先弄清楚正常执行情况下，ssh client什么情况下才会正常返回：

1. 远程执行的命令退出，并收集远程命令的`exit code`作为ssh命令的`exit code`
2. 远程命令不再通过stdout和stderr返回数据

先看下不满足上述两个条件的情况：
1. sleep前台运行，stdout和stderr重定向。客户侧ssh命令5s后执行完成。
```
$ time ssh -T -p 202  fangzhen@127.0.0.1 "sleep 5 &>/dev/null "
real    0m5.208s
```
对应的 server 端的进程树：
```
  63183       1   63183   63183 Ss   sshd: /usr/bin/sshd -D [listener] 0 of 10-100 startups
  69997   63183   69997   69997 Ss    \_ sshd: fangzhen [priv]
  69999   69997   69997   69997 S         \_ sshd: fangzhen@notty
  70012   69999   70012   70012 Ss            \_ bash -c sleep 5 &>/dev/null 
  70013   70012   70012   70012 S                 \_ sleep 5
```

2. 保持stdout和stderr打开，但是进程后台运行：
```
$ time ssh -T -p 202  fangzhen@127.0.0.1 "sleep 5 &"
real    0m5.222s
```
server端sleep进程ppid为1，原因是sleep 后台运行，它的父进程bash很快退出了，它被init进程接管后父进程id变成1。
```
 104900       1  104899  104899 S    sleep 5
```

#### 没有伪终端情况下
结合上面两个命令，执行`ssh -T -p 202  fangzhen@127.0.0.1 "sleep 5 &>/dev/null &"`。该命令执行后，客户侧ssh命令迅速完成，不会等待5s之后才完成。

而且没有伪终端的情况下，在连接断开时，server侧不会给用户进程发信号，所以用户后台进程`sleep 5`可以继续运行。

#### 有伪终端的情况下：
`ssh -t -p 202  fangzhen@127.0.0.1 "sleep 5 &>/dev/null"`对应的server端进程如下：
```
  63183       1   63183   63183 Ss   sshd: /usr/bin/sshd -D [listener] 0 of 10-100 startups
  79835   63183   79835   79835 Ss    \_ sshd: fangzhen [priv]
  79837   79835   79835   79835 S         \_ sshd: fangzhen@pts/9
  79850   79837   79850   79850 Ss+           \_ bash -c sleep 5 &>/dev/null
  79851   79850   79850   79850 S+                \_ sleep 5
```

远程命令改为后台执行：`$ ssh -t -p 202  fangzhen@127.0.0.1 "sleep 5 &>/dev/null &"`，会发现客户侧ssh命令立即退出，但是server侧的sleep 命令也立即退出了。

原因是在sleep后台运行时，的`bash -c`进程很快执行完成，它是session leader，在session leader退出后，同一个session的所有前台子进程会收到HUP信号（kernel会发送），从而`sleep`也会退出。
在没有伪终端的情况下，也就没有前台进程，session leader退出不会给其他进程发`HUP`信号

**后台执行**

这时候`nohup`才派上用场了：
使用`$ ssh -t -p 202  fangzhen@127.0.0.1 "nohup sleep 5 &>/dev/null &"`可以在有伪终端的情况下后台运行命令。（<https://stackoverflow.com/a/2831449/2705629> 即为该方案）

实际上述也**可能**不行。这涉及到bash中后台运行的如何实现的。

个人猜测大致实现逻辑是 bash fork出子进程来运行用户命令，然后等调度到bash进程时会把fork出的子进程设置为后台job，并继续往下执行（或显示命令提示符）。
这时候就会有竞争：如果父bash进程退出的后，子进程`nohup xxx`还没有跑到忽略HUP信号，就会像上面没有nohup的命令一样因为收到HUP信号而退出。

workaround可以在后台命令后加一个sleep, 让父进程更晚退出，比如`$ ssh -t -p 202  fangzhen@127.0.0.1 "nohup sleep 5 &>/dev/null & sleep 1"`
或者等待`sleep 5`进程启动后再退出。

*TL;DR ssh后台执行*

<https://stackoverflow.com/questions/29142/getting-ssh-to-execute-a-command-in-the-background-on-target-machine/74793354#74793354>

> Notes:
> 1. `Ctrl-C`和`kill -INT <pid>`的区别：
> `Ctrl-C`会给前台进程组的所有进程发送INT信号。kill也可以向进程组发送信号，使用`kill -INT -<pid>`
> https://stackoverflow.com/questions/8398845/what-is-the-difference-between-ctrl-c-and-sigint
>
> 2. 使用`-f`参数可以让ssh client到后台运行，ssh和sshd的网络连接还是保持的。
