---
layout: post
title: System Calls in Linux
tags: kernel glibc
date: 2020-08-30
update: 2021-07-01
---

系统调用是用户空间使用内核功能的一种主要方式，概念就不多说。以下分析基于以下版本：
```
kernel: v4.18
glibc: 2.30
Architecture: x86_64
```

Kernel Space 流程概述
---------------------
对x86_64下32位的system call，通过`__kernel_vsyscall` 来自动选择使用最优的方式（sysenter/syscall/int80）。
kenrel启动过程中，通过`apply_alternatives()`动态patch kernel image。
一般来说，用户程序调用库函数执行系统调用，glibc会通过vDSO中的`__kernel_vsyscall`来最终执行系统调用。

对x86_64下64bit system call，只有`syscall`指令，不需要`__kernel_vsyscall`来做选择。


```c
//file: arch/x86/entry/vdso/vma.c

void __init init_vdso_image(const struct vdso_image *image)
{
	BUG_ON(image->size % PAGE_SIZE != 0);

	apply_alternatives((struct alt_instr *)(image->data + image->alt),
			   (struct alt_instr *)(image->data + image->alt +
						image->alt_len));
}
```

如下代码选择使用哪个指令进入系统调用，（并设置好需要的寄存器，保存栈等工作）。

```gas
//file: arch/x86/entry/vdso/vdso32/system_call.S

__kernel_vsyscall:
...
	#define SYSENTER_SEQUENCE	"movl %esp, %ebp; sysenter"
	#define SYSCALL_SEQUENCE	"movl %ecx, %ebp; syscall"

#ifdef CONFIG_X86_64
	/* If SYSENTER (Intel) or SYSCALL32 (AMD) is available, use it. */
	ALTERNATIVE_2 "", SYSENTER_SEQUENCE, X86_FEATURE_SYSENTER32, \
	                  SYSCALL_SEQUENCE,  X86_FEATURE_SYSCALL32
#else
	ALTERNATIVE "", SYSENTER_SEQUENCE, X86_FEATURE_SEP
#endif

	/* Enter using int $0x80 */
	int	$0x80
...
```

不管哪个指令，调用之后从ring3进入ring0，并跳转到正确的位置继续执行。例如
`int 80` 需要设置中断门，`sysenter/syscall`等需要设置相应的寄存器。请看如下代码：


```c
// file: arch/x86/kernel/idt.c

#if defined(CONFIG_IA32_EMULATION)
	SYSG(IA32_SYSCALL_VECTOR,	entry_INT80_compat),
```


```c
// file: arch/x86/kernel/cpu/common.c

void syscall_init(void)
{
...
	if (static_cpu_has(X86_FEATURE_PTI))
		wrmsrl(MSR_LSTAR, SYSCALL64_entry_trampoline);
	else
		wrmsrl(MSR_LSTAR, (unsigned long)entry_SYSCALL_64);

#ifdef CONFIG_IA32_EMULATION
	wrmsrl(MSR_CSTAR, (unsigned long)entry_SYSCALL_compat);
	wrmsrl_safe(MSR_IA32_SYSENTER_CS, (u64)__KERNEL_CS);
	wrmsrl_safe(MSR_IA32_SYSENTER_ESP, (unsigned long)(cpu_entry_stack(cpu) + 1));
	wrmsrl_safe(MSR_IA32_SYSENTER_EIP, (u64)entry_SYSENTER_compat);
#endif
...
}
```

然后才到了真正处理系统调用的地方。

32位的实现中三个entry如下。如之前所述，这三个函数都应该是通过vDSO的`__kernel_vsyscall`调用过来。


```asm
// file: arch/x86/entry/entry_64_compat.S

ENTRY(entry_SYSENTER_compat) // sysenter & sysretl
ENTRY(entry_SYSCALL_compat)  // syscall  & sysretl
ENTRY(entry_INT80_compat)    // int 80   & iret
```
64bit：
```asm
// file: arch/x86/entry/entry_64.S

ENTRY(entry_SYSCALL_64_trampoline)
ENTRY(entry_SYSCALL_64)
```

调用到在`common.c`各自的入口函数，进而根据系统调用号调到每个系统调用。


```c
// file: arch/x86/entry/common.c

__visible void do_int80_syscall_32(struct pt_regs *regs)
__visible long do_fast_syscall_32(struct pt_regs *regs)
__visible void do_syscall_64(unsigned long nr, struct pt_regs *regs)
```

User Space (glibc) 实现概述
-----------------------------
根据 https://sourceware.org/glibc/wiki/SyscallWrappers, 在`glibc`中有两种syscall wrapper：

* Assembly syscalls： 定义在syscalls.list中，通过脚本make-syscalls.sh去生成系统调用。
* Macro Syscalls：一些复杂的system call，通过上面的方式不好处理的。

对x86_64架构下的程序来说，从如何调用到系统调用代码来看，有几种方式：

* vDSO：部分系统调用功能通过vDSO export到用户态不，glibc在调用时不会真正陷入内核态
* 对64位程序，直接通过syscall指令
* 对32位的程序，通过vDSO中的`__kernel_vsyscall`

例如对`open`库函数，64位程序下调用到`sysdeps/unix/sysv/linux/open64.c`，
`SYSCALL_CANCEL` 展开后会调用`syscall`指令。

```
int
__libc_open64 (const char *file, int oflag, ...)
{
  int mode = 0;

  if (__OPEN_NEEDS_MODE (oflag))
    {
      va_list arg;
      va_start (arg, oflag);
      mode = va_arg (arg, int);
      va_end (arg);
    }

  return SYSCALL_CANCEL (openat, AT_FDCWD, file, oflag | EXTRA_OPEN_FLAGS,
                         mode);
}
```
对`-m32`编译出的32位程序，会调用到`sysdeps/unix/sysv/linux/open.c`，
```
int
__libc_open (const char *file, int oflag, ...)
{
  int mode = 0;

  if (__OPEN_NEEDS_MODE (oflag))
    {
      va_list arg;
      va_start (arg, oflag);
      mode = va_arg (arg, int);
      va_end (arg);
    }

  return SYSCALL_CANCEL (openat, AT_FDCWD, file, oflag, mode);
}
```
静态链接的情况下，`SYSCALL_CANCEL`展开后会调用 `call *_dl_sysinfo`。
从`elf/setup-vdso.h`看到`_dl_sysinfo`初始化为vDSO中`__kernel_vsyscall`的地址。

vDSO
-------
virtual system call 是为了解决一些调用非常频繁，而实际上有不需要高权限的系统调用而提出的。
vDSO解决了最初vsystem call实现中的一些问题，例如只有固定个数，内存地址固定等问题。
vDSO是内核代码的一部分，但是被link到用户的内存空间，可以直接调用。
例如`gettimeofday`，调用的时候不会陷入到内核态。
另一个例子是上述`__kernel_vsyscall` 也是通过vDSO暴露出来的。


Tips
---------
* cross-compile glibc

    https://stackoverflow.com/questions/8004241/how-to-compile-glibc-32bit-on-an-x86-64-machine

    ```
    # build i686
    $ ../../src/glibc-2.6/configure --prefix=$HOME/glibc \
         --host=i686-linux-gnu \
         --build=i686-linux-gnu \
         CC="gcc -m32" CXX="g++ -m32" \
         CFLAGS="-O2 -march=i686" \
         CXXFLAGS="-O2 -march=i686"
    ```

    ```
    # build x86_64
    ../../src/glibc-2.6/configure --prefix=$HOME/glibc
    ```

* Get expanded macro for kernel

    ```
    https://lists.kernelnewbies.org/pipermail/kernelnewbies/2015-October/015234.html

    You may want to try following. That will expand all the macros in
    kernel/cpu.c file.

    # make kernel/cpu.i


    You may try with your required files.
    ```
    or use `save-temps=obj`
    https://stackoverflow.com/questions/23407635/append-compile-flags-to-cflags-and-cxxflags-while-configuration-make/23407800
    https://stackoverflow.com/questions/56429389/expand-macros-of-a-single-file-when-compiling-linux-kernel

    glibc:

    ```
    rm io/open.o
    make sysdep-CFLAGS='-save-temps=obj'
    ```

参考：
------

* https://blog.packagecloud.io/eng/2016/04/05/the-definitive-guide-to-linux-system-calls/#glibc-syscall-wrapper-internals  
   写的比较清晰详细，也基本涵盖了本文的内容以及更多背景，外延

* https://stackoverflow.com/questions/35115470/linux-syscall-libc-vdso-and-implementation-dissection  
   动态链接情况下glibc的宏展开过程

* https://0xax.gitbooks.io/linux-insides/content/SysCall/linux-syscall-3.html  
   对vDSO 介绍比较详细

* http://man7.org/linux/man-pages/man7/vdso.7.html  
   vDSO man page，列出了各个结构下vDSO functions

* https://cloud.tencent.com/developer/article/1492374  
  https://www.binss.me/blog/the-analysis-of-linux-system-call/  
   两篇比较细节的调用过程

* https://lwn.net/Articles/604287/  
   https://lwn.net/Articles/604515/  
   LWN "Anatomy of a system call", 也比较全面和系统。
