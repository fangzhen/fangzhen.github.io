---
layout: post
title: Linux EFI Stub 启动流程(x86_64)
tags: linux boot x86_64
date: 2023-05-05
update: 2023-05-31
---

本文描述linux kernel在x86_64架构下，通过UEFI启动时的启动过程。

> linux kernel efi stub 相关的代码在v5.7有一次重构，重构后eboot.c的内容都移到了efi/libstub下。而且相关的优化一直在进行。本文参考的代码版本为v6.2

## Kernel image build
### 编译参数
```
$ ARCH=x86_64 make defconfig
*** Default configuration is based on 'x86_64_defconfig'
```
确认下`CONFIG_EFI_STUB`:
```
CONFIG_EFI_STUB=y
```

### bzImage
x86_64下kernel build的默认target是`arch/x86/boot/bzImage`，也是通过grub等bootloader引导系统时使用的kernel二进制文件。

根据makefile，从vmlinux最终生成bzImage的过程为：
```
vmlinux (静态链接的ELF可执行文件)->(objcopy)
arch/x86/boot/compressed/vmlinux.bin ->
arch/x86/boot/compressed/vmlinux.bin.gz ->
arch/x86/boot/compressed/piggy.o ->
arch/x86/boot/compressed/vmlinux (ELF格式) ->(objcopy -o binary)
arch/x86/boot/vmlinux.bin (Raw binary 格式) ->
arch/x86/boot/bzImage (setup.bin 和vmlinux.bin合成bzImage)
```

```
$ file arch/x86/boot/bzImage
arch/x86/boot/bzImage: Linux kernel x86 boot executable bzImage, version 6.2.0 (fangzhen@manjaro) #8 SMP PREEMPT_DYNAMIC Tue May  9 15:29:41 CST 2023, RO-rootFS, swap_dev 0XB, Normal VGA
```

> 命名真乱，不同目录下的vmlinux, vmlinux.bin完全是不同的意思

1. make默认build bzImage
   ```
   // arch/x86/Makefile
   # Default kernel to build
   all: bzImage
   ```
2. bzImage 由几个部分组装起来，参考：https://zhuanlan.zhihu.com/p/73077391
  逻辑上主要分为两部分： 1. boot部分 2. compressed vmlinux。
  boot部分主要由arch/x86/boot/下的代码编译而来
  linux kernel支持从几种不同入口进入，可以参考上面文章。

3. arch/x86/boot/compressed/vmlinux的链接说明
   * 使用`-pie --no-dynamic-linker`，构建位置无关，静态链接的可执行文件。需要位置无关代码是因为
     bzImage会被bootloader或uefi firmware加载到随机的位置，内存地址不确定。
   * 在linker script中确认 `.got`, `.plt`， `rela.*`节没有条目。因为在bzImage加载时，
     并没有做动态链接。所以要保证不需要动态链接。
   * 相关代码：
     ```
     // arch/x86/boot/compressed/Makefile
     # Compressed kernel should be built as PIE since it may be loaded at any
     # address by the bootloader.
     LDFLAGS_vmlinux := -pie $(call ld-option, --no-dynamic-linker)

     $ cat arch/x86/boot/compressed/.vmlinux.cmd
     $ cat arch/x86/boot/compressed/vmlinux.lds.S
     ...
             /*
              * Sections that should stay zero sized, which is safer to
              * explicitly check instead of blindly discarding.
              */
             .got : {
                     *(.got)
             }
             ASSERT(SIZEOF(.got) == 0, "Unexpected GOT entries detected!")

             .plt : {
                     *(.plt) *(.plt.*)
             }
             ASSERT(SIZEOF(.plt) == 0, "Unexpected run-time procedure linkages detected!")
     ```

### vmlinux
代码根目录下的vmlinux是kernel的主体，根据上节说明，vmlinux被压缩后包含在bzImage文件中。下文我们可以看到，kernel在boot阶段一步步把vmlinux解压出来放到内存正确位置，并把控制权转移到vmlinux。
```
// .vmlinux.cmd: vmlinux的ld参数，--emit-relocs 保留了relocation信息
cmd_vmlinux := scripts/link-vmlinux.sh "ld" "-m elf_x86_64 -z noexecstack --no-warn-rwx-segments" "--emit-relocs --discard-none -z max-page-size=0x200000 --build-id=sha1 --orphan-handling=error";  true
```
对应的linker script为：
```
//x86/kernel/vmlinux.lds.S

SECTIONS
{
	. = __START_KERNEL;
	phys_startup_64 = ABSOLUTE(startup_64 - LOAD_OFFSET);

	/* Text and read-only data */
	.text :  AT(ADDR(.text) - LOAD_OFFSET) {

// x86/include/asm/page_types.h
#define __START_KERNEL		(__START_KERNEL_map + __PHYSICAL_START)
```
计算出来__START_KERNEL的实际值为`0xffffffff81000000`。
`.text :  AT(ADDR(.text) - LOAD_OFFSET)` 计算出来.text section的LMA为`0x1000000`，也即vmlinux的program Header中显示的物理地址。

所以vmlinux没有编译链接为位置无关代码，虚拟地址的起始地址为`__START_KERNEL`。
但实际加载的虚拟地址可能不确定(比如开启KASLR)。在vmlinux被实际执行前会做重定位修正地址，见下文解压vmlinux后的`handle_relocations`。

-----------
<br/>
> **本文后续提到kernel的时候，会使用bzImage和vmlinux分别代表`arch/x86/boot/bzImage`和根目录的`vmlinux`。**

----------

## kernel Boot 过程概述
计算机从开机开始进入linux kernel，大致来说，控制权按如下顺序转移直到启动：
```
Firmware(如BIOS或UEFI) ->
bootloader(如grub)->
bzImage ->
vmlinux
```
本文主要分析UEFI Firmware下，`bzImage -> vmlinux` 这个过程，即从控制权转移到bzImage之前到进入vmlinux之后。

主要相关代码：

| arch/x86/boot/header.S         | bzImage header。包括uefi image的PE/COFF+文件头和[x86 Boot Protol](https://docs.kernel.org/x86/boot.html)定义的 Real-Mode Kernel Header（虽然叫Real-Mode，应该主要还是历史原因，历史上real-mode代码进来后要检查这些header。当前不管是bootloader进来还是通过efistub进来，这些header都是要用到的） |
| arch/x86/boot/compressed/*     | `compressed`可能是指该目录下主要是处理compresesed vmlinux相关的代码，包括解压，relocate等。                                                                                                                                                                                                     |
| drivers/firmware/efi/libstub/* | efi相关代码                                                                                                                                                                                                                                                                                     |
| arch/x86/                      | vmlinux中x86架构相关代码                                                                                                                                                                                                                                                                        |

Boot整体过程如下
```
efi_pe_entry: efi-dir/x86-stub.c - EFI 入口
    efi_stub64_entry: compressed-dir/head_64.S - EFI bootloader 入口
      efi_main: efi-dir/x86-stub.c - uefi相关初始化工作
        efi_relocate_kernel: efi-dir/relocate.c - 把bzImage移动到内存合适位置，并为后面解压vmlinux预留出足够的空间。
        exit_boot:efi-dir/x86-stub.c - 退出efi_boot_service
      startup_64: compressed-dir/head_64.S - 64bit 初始化。把bzImage中压缩的vmlinux解压出来，并跳转到vmlinux的入口。
            vmlinux中采用的是虚拟地址，所以还要提前配置好页表。

efi-dir: drivers/firmware/efi/libstub
compressed-dir: arch/x86/boot/compressed
```
下文对每个部分进行具体分析。

## EFI Stub 入口

对于UEFI启动的情况，有两个入口：

### efi_pe_entry
bzImage作为的uefi Image，由UEFI firmware直接执行。这种情况下可以不需要bootloader。
UEFI Image格式为pecoff+，文件头在header.S中定义。
```
// arch/x86/boot/header.S
#ifdef CONFIG_EFI_STUB
	.org	0x38
	#
	# Offset to the PE header.
	#
	.long	LINUX_PE_MAGIC
	.long	pe_header
#endif /* CONFIG_EFI_STUB */

	# Filled in by build.c
	.long	0x0000				# AddressOfEntryPoint
```
`AddressOfEntryPoint`在kernel build时由`arch/x86/boot/tools/build.c`计算填入。
该地址是pecoff格式文件的入口地址。EFI_BOOT_SERVICES.LoadImage() 加载UEFI image后会转到该地址继续执行。

efi_pe_entry的主要调用链如上，调用`efi_stub64_entry`之前是传统bootloader做的事情，例如设置boot params。
`efi_stub64_entry`是`efi_sub_entry`的别名，接下来我们看`efi_stub_entry`。

### efi_stub_entry
从uefi的bootloader进入，bootloader可以把bzImage放到某个内存位置，然后可以直接跳转到`uefi_stub_entry`。
efi_stub_entry需要符合[x86的linux boot protocol](https://www.kernel.org/doc/html/latest/x86/boot.html)规范，对应的是handover_offset指定的入口：
```
Field name: handover_offset
Offset/size: 0x264/4

    This field is the offset from the beginning of the kernel image to the EFI handover protocol entry point. Boot loaders using the EFI handover protocol to boot the kernel should jump to this offset.
```
build.c中把efi_stub64_entry的地址填入到上述位置。
```
static void efi_stub_entry_update(void){
...
	put_unaligned_le32(addr, &buf[0x264]);
}
```
当前的实现中`efi_stub_entry` 是汇编代码，需要注意calling convention。
它主要是顺序调用efi_main和startup_64。

## efi_main
执行efi相关的一些初始化和配置工作。relocate_kernel，setup_graphics 等。

### efi_relocate_kernel
```
//x86-stub.c / efi_main:

	if ((buffer_start < LOAD_PHYSICAL_ADDR)				     ||
	    (IS_ENABLED(CONFIG_X86_32) && buffer_end > KERNEL_IMAGE_SIZE)    ||
	    (IS_ENABLED(CONFIG_X86_64) && buffer_end > MAXMEM_X86_64_4LEVEL) ||
	    (image_offset == 0)) {
		extern char _bss[];

		status = efi_relocate_kernel(&bzimage_addr,
					     (unsigned long)_bss - bzimage_addr,
					     hdr->init_size,
					     hdr->pref_address,
					     hdr->kernel_alignment,
					     LOAD_PHYSICAL_ADDR);
...
```
在`CONFIG_PHYSICAL_START 0x1000000`之后的物理地址找一段连续内存，并把整个kernel（bzImage）移动过来。
移动的kernel 从startup_32开始，不包括pe-coff文件头。startup_32链接后的地址是0。
```
//compressed/vmlinux.lds.S
SECTIONS
{
	/* Be careful parts of head_64.S assume startup_32 is at
	 * address 0.
	 */
	. = 0;
	.head.text : {

```
分配的内存大小为init_size（boot protocol中定义 offset/size=0x260/4）。这段内存后面也要用来解压vmlinux。relocate之后的kernel起始地址会作为`efi_main`的返回值。

init_size的计算：大概是要在解压前后的kernel取较大值，保证有足够空间。
```
// boot/header.S
#define VO_INIT_SIZE	(VO__end - VO__text)
#if ZO_INIT_SIZE > VO_INIT_SIZE
# define INIT_SIZE ZO_INIT_SIZE
#else
# define INIT_SIZE VO_INIT_SIZE
#endif

init_size:		.long INIT_SIZE		# kernel initialization size
```

> **Note:**
> <br/>
> 如果bzImage是通过uefi firmware的`LoadImage`加载的，可能不需要relocate_kernel（上面代码中的if条件都不满足）。这种情况下，怎么保证buffer的内存连续？
>
> build.c中设置的uefi image 大小为init_sz，所以firmware load image的时候就会分配足够大的连续内存。
> ```
>     /* Size of image */
>     put_unaligned_le32(init_sz, &buf[pe_header + 0x50]);
> ```

### exit_boot
其中，会在调用exitBootService前获取uefi下的memory map，在exit之后转化成e820格式，结果存在boot_params中。
```
//x86-stub.c
exit_boot
  allocate_e820
  setup_e820
```
  此后不能再使用uefi firmware提供的内存管理功能，需要kernel自己来管理内存。此时
  **bzImage 被移动到物理地址CONFIG_PHYSICAL_START后的一段连续内存（buffer）中，分页开启，且为identity mapping；gdt/idt/页表/stack位于内存中某个位置，还是uefi firmware分配的，没有被kernel本身接管。**

## startup_64
最后的boot工作。从其他入口进来最终也会到此处，比如`startup_32`最后也jump到`startup_64`。
  注意这个阶段kernel会逐渐接管stack, heap, gdt, 页表等，而这些内存都是预先分配在bzImage的。例如：
```
# define BOOT_STACK_SIZE	0x4000
#   define BOOT_PGT_SIZE	(19*4096)
```

接下来把compressed vmlinuz拷贝到buffer末尾，先计算目的地址：
```
#ifdef CONFIG_RELOCATABLE
    # 把startup_32的当前运行时地址存放到rbp
	leaq	startup_32(%rip) /* - $startup_32 */, %rbp
#ifdef CONFIG_EFI_STUB
    # EFI_STUB的情况下，bzimage的起始位置跟startup_32的offset为image_offset
    # %rbp变成uefi image的起始地址。
    # 注意如果经过efi_relocate_kernel，image_offset已经被设置成了0。
    # 只有在uefi firmware加载efi stub，而且正好不需要relocate_kernel的情况下，rbp才会被修正。
	movl    image_offset(%rip), %eax
	subq	%rax, %rbp
    # %rbp 即buffer start
#endif
    # 以下几行把%rbp按kernel_alignment（2M）对齐
    # %rsi为boot_param的地址，通过参数传递给startup_64。
	movl	BP_kernel_alignment(%rsi), %eax
	decl	%eax
	addq	%rax, %rbp
	notq	%rax
	andq	%rax, %rbp
    # 保证%rbp >= LOAD_PHYSICAL_ADDR
	cmpq	$LOAD_PHYSICAL_ADDR, %rbp
	jae	1f
#endif  # end of CONFIG_RELOCATABLE
	movq	$LOAD_PHYSICAL_ADDR, %rbp
1:

	/* Target address to relocate to for decompression */
    # %rbx = init_size - _end + %rbp 即buffer end之前size为`_end`的空间。
    # 其中_end 在compressed/vmlinux.lds.S中定义，为startup_32到bzImage末尾的大小(page size对齐)。
	movl	BP_init_size(%rsi), %ebx
	subl	$ rva(_end), %ebx
	addq	%rbp, %rbx

	/* Set up the stack */
	leaq	rva(boot_stack_end)(%rbx), %rsp
```

拷贝的代码如下，把kernel从offset 0(startup_32) 到`_bss`的内容拷贝到`%rbx`起始的位置。

```
    # 汇编编译器对%rip做基址有特殊处理。
    # 基址为%rip时生成的offset为相对%rip的地址，其他寄存器是label本身的地址。
    # Reference（https://stackoverflow.com/questions/34058101/referencing-the-contents-of-a-memory-location-x86-addressing-modes）
	leaq	(_bss-8)(%rip), %rsi
	leaq	rva(_bss-8)(%rbx), %rdi
	movl	$(_bss - startup_32), %ecx
	shrl	$3, %ecx
	std
	rep	movsq
	cld
```

然后跳转到copy后的`.Lrelocated`位置(base address为`%rbx`)继续执行。
```
	leaq	rva(.Lrelocated)(%rbx), %rax
	jmp	*%rax
```
在`.Lrelocated`中主要调用`initialize_identity_maps`配置了identity map的页表；
`extract_kernel`解压bzImage中的compressed vmlinux，并跳转到解压后的kernel地址。

`extract_kernel`主要做了三件事
1. 解压vmlinux到buffer start。（如果开启kaslr，要选择一个随机地址）
2. `parse_elf`把类型为`LOAD`的segment移动到正确的内存位置。
3. `handle_relocations`. vmlinux 代码中的地址是链接的虚拟地址是假定虚拟地址从`__START_KERNEL`开始的，如果`CONFIG_x86_NEED_RELOCS`开启，需要修正这些地址。
需要修正的地址在生成vmlinuz的时候从elf文件的relocation部分生成（arch/x86/tools/relocs.c），接在vmlinux后面。
```
$(obj)/vmlinux.relocs: vmlinux FORCE
        $(call if_changed,relocs)
```

`vmlinux`链接是没有使用`-pie`参数，生成的不是位置无关代码。链接时已经把vmlinux中relocation部分对应的地址修改成了起始地址为`__START_KERNEL`对应的地址。但是实际vmlinux加载的地址不一定是从`__START_KERNEL`开始，所以这里`handle_relocations`相当于做了静态链接是做的重定位的工作，只是以实际的加载地址计算要被替换的地址。跟操作系统加载动态链接库或位置无关可执行的ELF文件是做的动态链接还不太一样。


## 进入vmlinux
### vmlinux 的入口

> **Note:**
>
> 本节的`startup_64`位于vmlinux(代码文件arch/x86/kernel/head_64.S)，跟上面boot 过程中bzImage里的`startup_64`(arch/x86/boot/compressed/head_64.S)没有关系。

实际入口代码是`startup_64`(x86/kernel/head_64.S)。kernel初始化做的事情很多，我们只看一下kernel代码如何从物理地址切换到链接的虚拟地址的。。

进入startup_64时，已经开启了分页，而且页表为identity map。**所以当前的RIP的地址和物理地址是相同的。**

从之前的vmlinux build部分我们知道，vmlinux实际的链接地址为`0xffffffff81000000`，而在上面`handle_relocations`里已经修正成了实际加载的预期虚拟地址。

所以接下来需要建立页表，让vmlinux的实际虚拟地址和预期的虚拟地址匹配，并跳转到对应的虚拟地址。

### 配置页表

主要实现在`kernel/head64.c` 的`__startup_64`中。
a. 设置上面虚拟地址空间的kernel text mapping段
b. 设置kernel的identity mapping。因为在转到新的页表前，当前代码还是运行在identity mapping的地址下的。当cr3切换后，RIP还是物理地址。

`__startup_64`中引用全局变量，都需要用fixup_pointer来修正指针，也是因为当前RIP还是物理地址。

### 使用新的页表，并跳转到新的虚拟地址。

```
// arch/x86/kernel/head_64.S

	/*
	 * Switch to new page-table
	 *
	 * For the boot CPU this switches to early_top_pgt which still has the
	 * indentity mappings present. The secondary CPUs will switch to the
	 * init_top_pgt here, away from the trampoline_pgd and unmap the
	 * indentity mapped ranges.
	 */
	movq	%rax, %cr3

	/*
	 * Do a global TLB flush after the CR3 switch to make sure the TLB
	 * entries from the identity mapping are flushed.
	 */
	movq	%cr4, %rcx
	movq	%rcx, %rax
	xorq	$X86_CR4_PGE, %rcx
	movq	%rcx, %cr4
	movq	%rax, %cr4

	/* Ensure I am executing from virtual addresses */
    # 这个地方jmp后RIP从物理地址变成了`0xffffffff81000000`起始的虚拟地址。
    # 注意到这里不是直接`jmp 1f`。直接`jmp 1f`的话编译后会变成相对地址jmp（opcode EB 或 E9），
    # 而这里的写法会编译成绝对地址跳转（opcode FF），跳转后RIP就变成了%rax里的虚拟地址。
    # `movq $1f, %rax` 把`1f`label的值放到rax中，即我们需要的地址。
    # 还要注意和`mov 1f, %rax`的区别。该指令是move 1f地址的值。
    # 这个jmp之后，页表中identity mapping的部分就没用了。
	movq	$1f, %rax
	ANNOTATE_RETPOLINE_SAFE
	jmp	*%rax
1:
```

到这里kernel的内存管理刚刚看见曙光，kernel使用到的内存都已经在kernel自己的视野之内，跟bootloader或者UEFI/BIOS没关系了。


## Reference:
* linux kernel v6.2
* [Layout of bzImage](https://zhuanlan.zhihu.com/p/73077391)
  该文章给出了bzImage的格式，代码来源，以及进入kernel的各种入口，包括real mode, BIOS protected mode，efi等。
* [x86 Instruction Reference](http://ref.x86asm.net/coder64.html)
* [内核页表成长记](https://richardweiyang-2.gitbook.io/kernel-exploring/00-evolution_of_kernel_pagetable)。
* 关于[identity mapping](https://github.com/0xAX/linux-insides/issues/544)的一个讨论
* [ELF重定位](https://www.jianshu.com/p/2055bd794e58)
* [How the kernel is compiled](https://0xax.gitbooks.io/linux-insides/content/Misc/linux-misc-2.html)
* kernel实现分析系列blog:
  * [kernel-exploring](https://richardweiyang-2.gitbook.io/kernel-exploring/)
  * [linux-insides](https://0xax.gitbooks.io/linux-insides/)
