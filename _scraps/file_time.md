---
layout: post
title: linux下文件的创建/修改/访问时间
tags: stat xfs ext4
date: 2022-10-12
update: 2022-10-12
---

先简单看个例子，通过stat命令可以查看文件的信息，例如在我一台机器上输出如下：

```
[root@node-1 ~]# stat /tmp/abc
  File: /tmp/abc
  Size: 0               Blocks: 0          IO Block: 4096   regular empty file
Device: fc00h/64512d    Inode: 7077921     Links: 1
Access: (0644/-rw-r--r--)  Uid: (    0/    root)   Gid: (    0/    root)
Access: 2022-10-11 19:56:32.054641946 +0800
Modify: 2022-10-11 19:56:32.054641946 +0800
Change: 2022-10-11 19:56:32.054641946 +0800
 Birth: -
```

### Access, Modify, Change 分别是什么时间？

Access：文件最近访问时间

Modify：文件最近修改时间，指文件内容的修改

Change：文件元数据最近修改时间，例如权限等信息

从实现角度来看，这些信息保存在`stat`数据结构中

> ```
> struct stat {
> dev_t     st_dev;     /* ID of device containing file */
>    ino_t     st_ino;     /* inode number */
>    mode_t    st_mode;    /* protection */
>    nlink_t   st_nlink;   /* number of hard links */
>    uid_t     st_uid;     /* user ID of owner */
>    gid_t     st_gid;     /* group ID of owner */
>    dev_t     st_rdev;    /* device ID (if special file) */
>    off_t     st_size;    /* total size, in bytes */
>    blksize_t st_blksize; /* blocksize for file system I/O */
>    blkcnt_t  st_blocks;  /* number of 512B blocks allocated */
>    time_t    st_atime;   /* time of last access */
>    time_t    st_mtime;   /* time of last modification */
>    time_t    st_ctime;   /* time of last status change */
> };
> ```

> `st_atime` is the access time, updated on read(2) calls (and probably also when open(2) opens a file for reading) — it is NOT updated when files are read via mmap(2). (Which is why I assume open(2) will mark the access time.)
>
> `st_mtime` is the data modification time, either via write(2) or truncate(2) or open(2) for writing. (Again, it is NOT updated when files are written via mmap(2).)
>
> `st_ctime` is the metadata modification time: when any of the other data in the struct stat gets modified.

### Access 时间为什么不更新
当我们多次访问一个文件时，（大概率）会发现Access时间没有更新：
```
$ stat --format %x /tmp/aaa; cat /tmp/aaa ; sleep 1; stat --format %x /tmp/aaa;
2022-10-12 18:20:02.038536124 +0800
2022-10-12 18:20:02.038536124 +0800
```

按POSIX标准对access time的语义，读取文件都需要更新atime，这就导致对读取文件会有写操作，对性能会有很大的影响。

所以Linux系统对access time的更新有优化，通过修改mount option可以影响access time的更新逻辑，（从kernel 2.6.30起）默认为relatime：
```
relatime
    Update inode access times relative to modify or change time. Access time is only updated if the previous access time was earlier than the current modify or change time. (Similar to noatime, but
    it doesn’t break mutt(1) or other applications that need to know if a file has been read since the last time it was modified.)

    Since Linux 2.6.30, the kernel defaults to the behavior provided by this option (unless noatime was specified), and the strictatime option is required to obtain traditional semantics. In
    addition, since Linux 2.6.30, the file’s last access time is always updated if it is more than 1 day old.

```

### Birth time 为什么没获取到？如何获取

可以看到上面命令结果中`Birth`是没有获取到的。这跟文件系统以及stat实现有关。ext4和xfs(V5之后)等文件系统都包含文件创建时间。
比较新版本的stat(coreutils)可以直接获取到：
```
$ stat --version
stat (GNU coreutils) 9.1
Copyright (C) 2022 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by Michael Meskes.
$ stat /
  File: /
  Size: 4096            Blocks: 16         IO Block: 4096   directory
Device: 259,2   Inode: 2           Links: 18
Access: (0755/drwxr-xr-x)  Uid: (    0/    root)   Gid: (    0/    root)
Access: 2021-03-20 09:04:15.216879724 +0800
Modify: 2022-07-25 17:20:58.660548772 +0800
Change: 2022-07-25 17:20:58.660548772 +0800
 Birth: 2021-03-20 09:02:41.000000000 +0800
```
如果stat没获取到，可以从文件系统中获取，例如：
**ext4**文件系统下：
```
# stat /root
  File: /root
  Size: 4096            Blocks: 8          IO Block: 4096   directory
Device: fd00h/64768d    Inode: 4718593     Links: 8
Access: (0755/drwxr-xr-x)  Uid: (    0/    root)   Gid: (    0/    root)
Access: 2022-10-11 15:11:45.513402484 +0800
Modify: 2022-10-11 15:11:43.098386915 +0800
Change: 2022-10-11 15:11:43.098386915 +0800
 Birth: -

# debugfs -R 'stat <4718593>' /dev/mapper/os-root
debugfs 1.45.6 (20-Mar-2020)
Inode: 4718593   Type: directory    Mode:  0755   Flags: 0x80000
Generation: 3748363516    Version: 0x00000000:00000054
User:     0   Group:     0   Project:     0   Size: 4096
File ACL: 0
Links: 8   Blockcount: 8
Fragment:  Address: 0    Number: 0    Size: 0
 ctime: 0x6345172f:17750f8c -- Tue Oct 11 15:11:43 2022
 atime: 0x63451731:7a6799d0 -- Tue Oct 11 15:11:45 2022
 mtime: 0x6345172f:17750f8c -- Tue Oct 11 15:11:43 2022
crtime: 0x6344e66f:bebc2000 -- Tue Oct 11 11:43:43 2022
Size of extra inode fields: 32
Inode checksum: 0x8ccd25cd
EXTENTS:
(0):18882592
```

**xfs**下：
```
[root@node-4 ~]# stat /root
  File: /root
  Size: 4096            Blocks: 8          IO Block: 4096   directory
Device: fc00h/64512d    Inode: 134336257   Links: 10
Access: (0550/dr-xr-x---)  Uid: (    0/    root)   Gid: (    0/    root)
Access: 2022-10-12 17:30:30.525916990 +0800
Modify: 2022-10-12 14:49:08.250803277 +0800
Change: 2022-10-12 14:49:08.250803277 +0800
 Birth: -
[root@node-4 ~]# xfs_db -r -c "inode 134336257" -c "p v3.crtime.sec" /dev/mapper/os-root
v3.crtime.sec = Tue Oct 11 05:50:57 2022

```

ref:  
<https://superuser.com/questions/464290/why-is-cat-not-changing-the-access-time>
<https://stackoverflow.com/questions/19551139/access-time-does-not-change-after-a-file-is-opened>
<https://unix.stackexchange.com/questions/2802/what-is-the-difference-between-modify-and-change-in-stat-command-context>  
<https://stackoverflow.com/questions/3385203/what-is-the-access-time-in-unix>
<https://unix.stackexchange.com/questions/50177/birth-is-empty-on-ext4/50184#50184>
<https://unix.stackexchange.com/questions/7562/what-file-systems-on-linux-store-the-creation-time/40093#40093>
