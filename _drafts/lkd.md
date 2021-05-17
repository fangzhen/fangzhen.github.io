
中断: 硬件 -> 处理器 -> 操作系统 处理器怎么通知操作系统的？或者说怎么注册到某个中断handler
syscall 通过软中断
exception： 处理器产生的

中断在中断上下文
syscall 在process context？ how？也是从中断handler进来的 software interrupt not softirq
exception and syscall 进入kernel space

中断处理过程发生其他中断，上下文如何切换？

注册：driver通过request_irq 注册到某个interrupt number
https://stackoverflow.com/questions/7135915/which-context-are-softirq-and-tasklet-in
上下文切换 具体做了什么 interrupt process kernel context 具体什么区别

shared interrupt handler：所有handler是依次执行的，handler自己判断自己是否处理，不处理退出。

注：系统调用是通过叫software interruppt的软件中断（一种异常）来实现的，跟软中断（softirq）没有关系。

kernel 进程/用户进程

进程调度程序运行在哪？

signal处理

kernel preemption

kernel threads do not have an address space

interrupt context - what address space?
kernel mode - all share same address space?


/proc /sys 各自放哪些文件？


Memory Management
struct page: represents physical memory. One instance for each physical page.
why x86-32 has 896M high-mem boundery?

gfp -> get free pages


driver and firmware
driver run in CPU, fireware run in devices.
firmwares in /lib/firmware is uploaded by kernel on driver's request.
how firmware is loaded:
https://wiki.ubuntu.com/Kernel/Firmware
https://yi-jyun.blogspot.com/2017/04/linux-kernel-firmware.html

https://unix.stackexchange.com/questions/359989/what-is-firmware-in-linux-terminology?answertab=active#tab-top
This software(firmware) used to be stored in ROM (of various types) attached to the relevant controller, but to reduce costs and make upgrades simpler, controllers now tend to rely on the host operating system to load their firmware for them.

https://unix.stackexchange.com/questions/90727/why-do-some-drivers-still-require-firmware

memory:
get page table
https://github.com/rjmccabe3701/LinuxViewPageTables/commit/e2cb0f6810b11a25ff2d5f8aa50ff32dcbb8805e

https://www.kernel.org/doc/Documentation/arm64/memory.txt
https://www.kernel.org/doc/Documentation/x86/x86_64/mm.txt


动态链接静态链接

oops panic

sync & lock

interrupt-safe
SMP-safe
preempt-safe

bottom halves; tasklet softirq worker queue


locks: spin lock. semaphore, mutex
whoever locked a mutex must unlock it.

process scheduler run as a process? kernel thread? something else
