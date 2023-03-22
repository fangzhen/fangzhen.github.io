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

targets uefi -> kernel


linux boot
ref:
* 一组文章介绍efistub的实现 https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzUxNDUwOTc0Nw==&action=getalbum&album_id=1376027174058278914&subscene=159&subscene=190&scenenote=https%3A%2F%2Fmp.weixin.qq.com%2Fs%3F__biz%3DMzUxNDUwOTc0Nw%3D%3D%26mid%3D2247484795%26idx%3D1%26sn%3De84efafdaa5ed62877eba44c8696b737%26chksm%3Df9459ba7ce3212b1f0e951205d408bb9e74ce33a2f93aa63259c61fdd7c1ef9c25f64ca37d83%26cur_album_id%3D1376027174058278914%26scene%3D190%23rd&nolastread=1#wechat_redirect
* Layout of bzImage & boot entry https://zhuanlan.zhihu.com/p/73077391
* x86 boot protocol https://www.kernel.org/doc/html/latest/x86/boot.html
* https://0xax.gitbooks.io/linux-insides/content/Booting/linux-bootstrap-1.html
* [Building an UEFI x64 kernel from scratch: A long trip to userspace](https://blog.llandsmeer.com/tech/2019/07/21/uefi-x64-userland.html)

大概过程：
efi 入口 header_64.S:efi_pe_entry
efi_main
 relocate_kernel
 exit_boot_service
 gdt
startup_64
 paging

