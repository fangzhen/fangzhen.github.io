---
layout: post
title: uefi
tags: rust uefi
date: 2021-05-13
update: 2021-09-27
---

BIOS vs UEFI

启动流程
https://xinqiu.gitbooks.io/linux-insides-cn/content/Booting/linux-bootstrap-1.html

cpu mode

detect memorymap

References：
从零开始UEFI裸机编程，讲解了怎么读uefi spec.
https://kagurazakakotori.github.io/ubmp-cn/part1/basics/program.html

uefi spec https://uefi.org/specifications


impl core::fmt::Write to use writeln!

allocate_pool 最后一个参数是二级指针 void **buffer，原因是需要在*buffer中存储分配的内存地址，需要传指向*buffer的指针。
allocate_pages 最后一个参数 EFI_PHYSICAL_ADDRESS *Memory，没有用二级指针。EFI_PHYSICAL_ADDRESS 是unit64。猜测原因：1. memory不仅作为输出参数，也作为输入参数，语义上更接近于地址数值而不是指针（实际上指向的地址是无效的）；2. 结果 *memory一般不会直接作为指针使用，通过allocate page多半是要自己处理分配到的page，直接使用应该直接用allocate_pool了。

type cast //待确认
https://gcc.gnu.org/onlinedocs/gcc-3.3.6/gcc/Lvalues.html

```
You cannot take the address of an lvalue cast, because the use of its address would not work out coherently. Suppose that &(int)f were permitted, where f has type float. Then the following statement would try to store an integer bit-pattern where a floating point number belongs:

     *&(int)f = 1;


```
```
char c
&(int)c != &c

char *c
&(int*)c == &c
```
rust
https://doc.rust-lang.org/reference/expressions.html?highlight=lvalue#place-expressions-and-value-expressions
```
let p: *const u8 = ptr::null()
&(p as * const usize) as *const usize as usize != &p as *const *const u8 as usize
```

uefi memory map: 函数调用 局部变量等 会造成memory map 变化吗 - 不会。栈使用了EfiBootServicesData的内存，最小128k。x86环境上栈向下生长，但同一个函数中的局部变量的顺序可能被编译器调整。
https://stackoverflow.com/questions/54395558/why-do-subsequent-rust-variables-increment-the-stack-pointer-instead-of-decremen
https://stackoverflow.com/questions/664744/what-is-the-direction-of-stack-growth-in-most-modern-systems
https://en.wikipedia.org/wiki/Unified_Extensible_Firmware_Interface
exit_boot_service 调用后应该跳转到kernel的起始指令。setup内存（gdt,分页，初始化stack）应该在exit 之前？ exit之后当前继续在当前stack执行会有风险，如stack overflow,不过exit之前同样有风险。
物理内存管理
虚拟内存管理

uefi memory

Enable paging - efi-service memory identity mapped
Alloc page struct for physical pages; initial page struct
Alloc page for gdt; map in page table; lgdt
get_page for kernel
setup kernel stack
jump to kernel ; kernel takes control
invalidate uefi memory

TODO:
re-organize code

writeln!(st) -> st 需要是 mut ref -> 改成全局printk/log等类似方案？

targets uefi -> kernel

uefi spec: 2.3 calling convention. - x64 long mode & paging. 对x86_64架构，没有找到spec里有明确说明privilege level需要是ring0。

(((0x0ffULL) + (1ULL << (__builtin_ffsll(0x0ffULL) - 1))) & (((0x0ffULL) + (1ULL << (__builtin_ffsll(0x0ffULL) - 1))) - 1)) != 0

uefi impl：tianocore edk2  coreboot project Mu OVMF

ref:
Building an UEFI x64 kernel from scratch: A long trip to userspace
https://blog.llandsmeer.com/tech/2019/07/21/uefi-x64-userland.html

linux boot
ref: 一组文章介绍efistub的实现 https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzUxNDUwOTc0Nw==&action=getalbum&album_id=1376027174058278914&subscene=159&subscene=190&scenenote=https%3A%2F%2Fmp.weixin.qq.com%2Fs%3F__biz%3DMzUxNDUwOTc0Nw%3D%3D%26mid%3D2247484795%26idx%3D1%26sn%3De84efafdaa5ed62877eba44c8696b737%26chksm%3Df9459ba7ce3212b1f0e951205d408bb9e74ce33a2f93aa63259c61fdd7c1ef9c25f64ca37d83%26cur_album_id%3D1376027174058278914%26scene%3D190%23rd&nolastread=1#wechat_redirect
Layout of bzImage & boot entry https://zhuanlan.zhihu.com/p/73077391
x86 boot protocol https://www.kernel.org/doc/html/latest/x86/boot.html
https://0xax.gitbooks.io/linux-insides/content/Booting/linux-bootstrap-1.html

大概过程：
efi 入口 header_64.S:efi_pe_entry
efi_main
 relocate_kernel
 exit_boot_service
 gdt
startup_64
 paging

