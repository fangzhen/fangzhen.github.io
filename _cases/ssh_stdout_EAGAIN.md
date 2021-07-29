---
layout: post
title: 脚本中执行ssh之后，stdout `Resource temporarily unavailable`错误
date: 2021-07-27
tags: ssh
update: 2021-07-29
---

## 问题说明
以下是一个最简的复现脚本，执行会报错`Resource temporarily unavailable`：
```bash
#! /bin/bash
{
ssh localhost echo 123
cat /dev/zero
} | sleep 1

```
执行结果：
```
$ ./x.sh
Warning: Permanently added 'localhost' (ED25519) to the list of known hosts.
cat: write error: Resource temporarily unavailable
```
[//]: # (EAS-78029)
注: 原始问题没这么直接，最初出现问题是通过celery task执行一个shell脚本，shell脚本里调用的另一个python脚本，python脚本的print执行时报错Resource temporarily unavailable。

## 环境信息
```
openssh 8.0p1/8.6p1
```

## 问题调查
经过测试和调查，我们有：
1. `Resource temporarily unavailable`一般出现在nonblocking io的场景下，当缓冲区满了等情况下，设备不可用，返回`EAGAIN`，客户端应该收到后重试。
2. 没有管道的情况下，不会报错。
3. ssh命令注释掉的情况下，不会报错。

基于以上几点，怀疑是在ssh命令之后，`stdout`文件被设置了`O_NONBLOCK`flag，通过`proc/fdinfo`可以证实这一点：
```bash
[fangzhen@manjaro ssh-terminal]$ cat x.sh
#! /bin/bash
{
pid=$BASHPID
cat /proc/$pid/fdinfo/1 >&2
ssh localhost echo 123
cat /proc/$pid/fdinfo/1 >&2
cat /dev/zero
} | sleep 1

[fangzhen@manjaro ssh-terminal]$ ./x.sh
pos:    0
flags:  01
mnt_id: 13
Warning: Permanently added 'localhost' (ED25519) to the list of known hosts.
pos:    0
flags:  04001
mnt_id: 13
cat: write error: Resource temporarily unavailable
```

可以看到`stdout`的flag在ssh命令执行前后由`01`变成了`04001`。`04000`对应的flag正好就是`O_NONBLOCK`。

### 根本原因
基本可以确定是ssh命令的副作用，导致`bash`脚本本身的文件描述符的`flag`发生了变化。我们看下[openssh](https://github.com/openssh/openssh-portable) 8.6p1的相关代码：
```c
 1  //// file: ssh.c
 2 /* open new channel for a session */
 3 static int
 4 ssh_session2_open(struct ssh *ssh)
 5 {
 6         Channel *c;
 7         int window, packetmax, in, out, err;
 8
 9         if (stdin_null_flag) {
10                 in = open(_PATH_DEVNULL, O_RDONLY);
11         } else {
12                 in = dup(STDIN_FILENO);
13         }
14         out = dup(STDOUT_FILENO);
15         err = dup(STDERR_FILENO);
16
17         if (in == -1 || out == -1 || err == -1)
18                 fatal("dup() in/out/err failed");
19
20         /* enable nonblocking unless tty */
21         if (!isatty(in))
22                 set_nonblock(in);
23         if (!isatty(out))
24                 set_nonblock(out);
25         if (!isatty(err))
26                 set_nonblock(err);
27 //// ...
28 }
29 static int
30 ssh_session2(struct ssh *ssh, const struct ssh_conn_info *cinfo)
31 {
32 //// ...
33         if (!need_controlpersist_detach && stdfd_devnull(0, 1, 0) == -1)
34                 error_f("stdfd_devnull failed");
35 //// ...
36         return client_loop(ssh, tty_flag, tty_flag ?
37             options.escape_char : SSH_ESCAPECHAR_NONE, id);
38 }
39
40 ////file： clientloop.c
41 int
42 client_loop(struct ssh *ssh, int have_pty, int escape_char_arg,
43     int ssh2_chan_id)
44 {
45 //// ...
46         /* restore blocking io */
47         if (!isatty(fileno(stdin)))
48                 unset_nonblock(fileno(stdin));
49         if (!isatty(fileno(stdout)))
50                 unset_nonblock(fileno(stdout));
51         if (!isatty(fileno(stderr)))
52                 unset_nonblock(fileno(stderr));
53 //// ...
54 }
```

1. 在`ssh_session2_open`中dup了`stdin/stdout/stderr`，并且调用了`set_nonblock`（line 24）。
2. 在上面代码片段33行的地方，把`stdout`设置成了`devnull`
3. `client_loop`最后通过`unset_nonblock`试图恢复`O_NONBLOCK` flag（line 50）。

    `ssh -vvv`可以看到有输出`debug3: fd 1 is not O_NONBLOCK`。对应下面`unset_nonblock`实现中，在清除flag之前，发现`O_NONBLOCK` flag没有打开。
    就是因为上一步中`stdout`已经变成了`devnull`，所以实际上`stdout`并没有正确的被恢复。
```
int
unset_nonblock(int fd)
{
        int val;

        val = fcntl(fd, F_GETFL);
        if (val == -1) {
                error("fcntl(%d, F_GETFL): %s", fd, strerror(errno));
                return (-1);
        }
        if (!(val & O_NONBLOCK)) {
                debug3("fd %d is not O_NONBLOCK", fd);
                return (0);
        }
        debug("fd %d clearing O_NONBLOCK", fd);
        val &= ~O_NONBLOCK;
        if (fcntl(fd, F_SETFL, val) == -1) {
                debug("fcntl(%d, F_SETFL, ~O_NONBLOCK): %s",
                    fd, strerror(errno));
                return (-1);
        }
        return (0);
}
```

#### 社区bug report
社区在2021年有[bug report](https://bugzilla.mindrot.org/show_bug.cgi?id=3280)，已经fix。
基本思路保证上面第一步和第三步中的`fd`是同一个文件，不能因为`fd`指向了别的文件而导致检测失败。

### More: file descriptor & file description
在上面的测试脚本中，ssh进程是shell脚本的子进程，子进程对文件描述符的修改为什么会影响到父进程的文件描述符呢？

简单来说，进程都会维护一个文件描述符（file descriptor）表，进程通过文件描述符识别文件。进程通过文件描述符在kernel里维护的文件表（struct file）中找到对应的文件。
当fork进程或者dup/dup2的时候，只会复制进程的文件描述符，不会复制kernel中的file结构体。而像打开文件的flag，offset等是存放在file中的。

所以在上面ssh进程中修改stdout的flag，在父bash进程的打开文件中会受影响。

参考：
* <https://stackoverflow.com/questions/11733481/seeking-a-simple-description-regarding-file-descriptor-after-fork/11734354>
* <https://stackoverflow.com/questions/30226530/same-file-descriptor-after-fork>


