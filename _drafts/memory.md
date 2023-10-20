memblock
[A quick history of early-boot memory allocators](https://lwn.net/Articles/761215/)
https://www.kernel.org/doc/html/v4.19/core-api/boot-time-mm.html

内存系列 pagecache 零拷贝等，比较详细 https://plantegg.github.io/2020/01/15/Linux%20%E5%86%85%E5%AD%98%E9%97%AE%E9%A2%98%E6%B1%87%E6%80%BB/

memory in general
[Understanding The Linux Virtual Memory Manager by Mel Gorman]https://www.kernel.org/doc/gorman/pdf/understand.pdf
https://richardweiyang-2.gitbook.io/kernel-exploring/00-memory_a_bottom_up_view
[Linux核心概念详解]https://s3.shizhz.me memory部分
https://0xax.gitbooks.io/linux-insides/content/MM/

http://notemagnet.blogspot.com/2008/08/linux-write-cache-mystery.html
https://stackoverflow.com/questions/52067753/how-to-keep-executable-code-in-memory-even-under-memory-pressure-in-linux
https://askubuntu.com/questions/432809/why-is-kswapd0-running-on-a-computer-with-no-swap/432827#432827
https://zhuanlan.zhihu.com/p/95813254

slab
https://easystack.atlassian.net/browse/EAS-88771
SLUB: 整体比较清晰 https://www.cnblogs.com/tolimit/p/4654109.html
https://events.static.linuxfound.org/sites/events/files/slides/slaballocators.pdf
https://blog.csdn.net/u010246947/article/details/10133101
https://www.kernel.org/doc/gorman/html/understand/understand011.html
case study https://www.cnblogs.com/arnoldlu/p/11599232.html#pmap_process_memory_analysis https://blog.csdn.net/huifeidedabian/article/details/109071940

slab_alloc_node https://blog.csdn.net/hzj_001/article/details/99706159

meminfo https://segmentfault.com/a/1190000022518282

http://linuxperf.com/?cat=7

sysfs slab https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-kernel-slab

内存回收 drop cache https://zhuanlan.zhihu.com/p/93962657
自动内存回收 https://zhuanlan.zhihu.com/p/348873183
https://www.cnblogs.com/tolimit/p/5435068.html

slab unreclaimable? 什么情况下会是unreclaimable? 怎么回收？

kmalloc():include/linux/slab.h

 kmem_cache_alloc_trace(): mm/slub.c
   slab_alloc():mm/slub.c
     slab_alloc_node()
       slab_pre_alloc_hook()
         memcg_kmem_get_cache():mm/memcontrol.c
           cache_from_memcg_idx():mm/slab.h
       __slab_alloc():mm/slub.c
         ___slab_alloc() # slowpath


slab内存如何回收？

commit
```
commit 0715e6c516f106ed553828a671d30ad9a3431536
Author: Vlastimil Babka <vbabka@suse.cz>
Date:   Sat Mar 21 18:22:37 2020 -0700

    mm, slub: prevent kmalloc_node crashes and memory leaks

```

## Tips：
### centos 7 安装其他版本kernel
elrepo.org 社区维护了rhel系列的硬件相关的包，包含了最新的kernel.
http://elrepo.org/tiki/HomePage

### qemu 命令
qemu-system-x86_64 -name  test -machine pc-q35-6.0,accel=kvm -m 1024M  test.qcow2 -smp 4,sockets=2,dies=1,cores=1,threads=2 -object memory-backend-ram,id=ram-node0,size=1024M -numa node,nodeid=0,cpus=0-1,memdev=ram-node0 -numa node,nodeid=1,cpus=2-3
```
[root@localhost ~]# numactl --hardware
available: 2 nodes (0-1)
node 0 cpus: 0 1
node 0 size: 820 MB
node 0 free: 642 MB
node 1 cpus: 2 3
node 1 size: 0 MB
node 1 free: 0 MB
node distances:
node   0   1
  0:  10  20
  1:  20  10
```
guest numa topology 配置
https://www.cnblogs.com/allcloud/p/5021131.html

### kernel module 编写示例
https://www.cnblogs.com/aaronlinux/p/5459896.html

rmmod 失败问题
```
[root@node-11 fzh]# rmmod ms
rmmod: ERROR: could not remove 'ms': Device or resource busy
rmmod: ERROR: could not remove module ms: Device or resource busy
```
 https://goodcommand.readthedocs.io/zh_CN/latest/bs/rmmod_device_or_resource_busy.html
原因是build kernel和module用的gcc版本不一致：

kernel： `[    0.000000] Linux version 4.18.0-147.5.1.el8_1.5es.20.numa64.aarch64 (mockbuild@arm-kojid) (gcc version 8.3.1 20190311 (Red Hat 8.3.1-3) (GCC)) #1 SMP Fri Jul 9 09:46:55 UTC 2021`
本地：
```
[root@node-11 fzh]# gcc -v
Using built-in specs.
COLLECT_GCC=gcc
COLLECT_LTO_WRAPPER=/usr/libexec/gcc/aarch64-redhat-linux/4.8.5/lto-wrapper
Target: aarch64-redhat-linux
Configured with: ../configure --prefix=/usr --mandir=/usr/share/man --infodir=/usr/share/info --with-bugurl=http://bugzilla.redhat.com/bugzilla --enable-bootstrap --enable-shared --enable-threads=posix --enable-checking=release --with-system-zlib --enable-__cxa_atexit --disable-libunwind-exceptions --enable-gnu-unique-object --enable-linker-build-id --with-linker-hash-style=gnu --enable-languages=c,c++,objc,obj-c++,java,fortran,ada,lto --enable-plugin --enable-initfini-array --disable-libgcj --with-isl=/builddir/build/BUILD/gcc-4.8.5-20150702/obj-aarch64-redhat-linux/isl-install --with-cloog=/builddir/build/BUILD/gcc-4.8.5-20150702/obj-aarch64-redhat-linux/cloog-install --enable-gnu-indirect-function --build=aarch64-redhat-linux
Thread model: posix
gcc version 4.8.5 20150623 (Red Hat 4.8.5-39) (GCC)
```

更新本地的gcc版本，可以使用scl-rh repo中的gcc
```
wget http://mirror.centos.org/centos/7/extras/x86_64/Packages/centos-release-scl-rh-2-3.el7.centos.noarch.rpm
yum install devtoolset-8-gcc.aarch64

[root@node-11 fzh]# /opt/rh/devtoolset-8/root/usr/bin/gcc -v
Using built-in specs.
COLLECT_GCC=/opt/rh/devtoolset-8/root/usr/bin/gcc
COLLECT_LTO_WRAPPER=/opt/rh/devtoolset-8/root/usr/libexec/gcc/aarch64-redhat-linux/8/lto-wrapper
Target: aarch64-redhat-linux
Configured with: ../configure --enable-bootstrap --enable-languages=c,c++,fortran,lto --prefix=/opt/rh/devtoolset-8/root/usr --mandir=/opt/rh/devtoolset-8/root/usr/share/man --infodir=/opt/rh/devtoolset-8/root/usr/share/info --with-bugurl=http://bugzilla.redhat.com/bugzilla --enable-shared --enable-threads=posix --enable-checking=release --enable-multilib --with-system-zlib --enable-__cxa_atexit --disable-libunwind-exceptions --enable-gnu-unique-object --enable-linker-build-id --with-gcc-major-version-only --with-linker-hash-style=gnu --with-default-libstdcxx-abi=gcc4-compatible --enable-plugin --enable-initfini-array --with-isl=/builddir/build/BUILD/gcc-8.3.1-20190311/obj-aarch64-redhat-linux/isl-install --disable-libmpx --enable-gnu-indirect-function --build=aarch64-redhat-linux
Thread model: posix
gcc version 8.3.1 20190311 (Red Hat 8.3.1-3) (GCC)
```
修改Makefile的path，使用新版gcc，在Makefile中添加：
`export PATH := /opt/rh/devtoolset-8/root/usr/bin/:$(PATH)`

重新编译后就可以正常rmmod了。


### getcpu putcpu on_each_cpu
https://stackoverflow.com/questions/36288877/isolate-kernel-module-to-a-specific-core-using-cpuset
https://blog.csdn.net/Rafe_ma/article/details/72638509
https://stackoverflow.com/questions/34633600/how-to-execute-a-piece-of-kernel-code-on-all-cpus

### 获取pagesize
https://blog.csdn.net/zhanghaiyang9999/article/details/82144518
`getconf PAGESIZE`

