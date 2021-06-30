---
layout: post
title: Linux 中系统调用实现
tags: kernel glibc
date: 2020-08-30
update: 2021-08-30
---

* TOC
{:toc}

概述
----
kernel通过系统调用为用户空间提供一组接口，用户空间代码调用后陷入到内核态。系统调用使得用户空间可以受控使用内核功能。
本文分析基于以下版本：
```
Linux kernel: v4.18
glibc: 2.30
Architecture: x86_64
```
本文我们从kernel space和user space分别看一下`syscall`的实现和使用。涉及到的CPU架构主要为x86_64。

Kernel Space
------------
### x86架构系统调用实现概述
对x86体系来说，根据CPU特性，可能通过`sysenter/syscall/int 80`几种方式来实现系统调用。
不管哪种方式，用户态调用之后从ring3进入ring0，并跳转到正确的位置继续执行，并进行必要的context switch。

简单来说，kernel space的实现分为两部分：
1. **初始化**


   对于legacy的中断实现方式，需要设置中断门等，当通过软中断`int80`调用syscall时，入口函数设置为`entry_INT80_compat`。
   ```c
   // file: arch/x86/kernel/idt.c

   #if defined(CONFIG_IA32_EMULATION)
       SYSG(IA32_SYSCALL_VECTOR,	entry_INT80_compat),
   ```

   目前的CPU都支持所谓的fast syscall，提供专用的`syscall/sysret`或`sysenter/sysexit`指令来专门用于系统调用的实现。
   而`sysenter/syscall`等使用专用的寄存器来保存切换所需要的上下文信息，例如`CS/SS`寄存器，入口地址等。
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

   void cpu_init(void){
   ...
       syscall_init();
   ...
   }
   ```

   上述初始化在系统启动流程中被执行，例如`syscall_init`是在`cpu_init`中调用。

   *Q：`cpu_init`是per-cpu state的初始化，为什么把`syscall_init`放到`cpu_init`？*

   在开启了KPTI的情况下，系统调用入口初始化为`SYSCALL64_entry_trampoline`。这种情况下是每个CPU是不同的。

2. **具体系统调用的执行**

   用户空间调用系统调用时，根据不同的调用方式（`int 80/sysenter/syscall`），进入上述定义的入口。具体的定义在`entry_64_compat.S`和`entry_64.S`中。

   ```asm
   // file: arch/x86/entry/entry_64_compat.S
   ENTRY(entry_SYSENTER_compat) // sysenter & sysexit
   ENTRY(entry_SYSCALL_compat)  // syscall  & sysret
   ENTRY(entry_INT80_compat)    // int 80   & iret
   ```
   ```asm
   // file: arch/x86/entry/entry_64.S
   ENTRY(entry_SYSCALL_64_trampoline)
   ENTRY(entry_SYSCALL_64)
   ```

## x86_64架构64位系统调用的实现

### 背景信息
在64位长模式下，系统调用只提供了使用`syscall`指令这一种实现方式，相比32位兼容模式相比简单清晰了不少。
根据Intel sdm中对[syscall](https://www.felixcloutier.com/x86/syscall)，`syscall`指令从ring3 进入ring0：
1. 把`syscall`下一条指令的地址保存到`%rcx`，并从`IA32_LSTAR MSR`中加载`%rip`。
2. 把`%rflags`保存到`%r11`，然后使用`IA32_FMASK MSR`来mask `%rflags`
3. 从`IA32_STAR MSR`的`47:32`位中加载`CS`和`SS`段选择子。但是段描述符是固定值，而不会从GDT/LDT中加载。所以需要操作系统保持一致性。
4. `syscall`指令不会处理`%rsp`，即不会自动进行栈切换，需要操作系统来完成。

[sysret](https://www.felixcloutier.com/x86/syscall)从ring0返回ring3：
1. 从`%rcx`恢复`%rip`，从`%r11`恢复`rflags`，即上面`syscall`的逆过程。
2. 从`IA32_STAR MSR`的`63:48`位加载`CS`和`SS`段选择子。同样段描述符是固定值，而不会从GDT/LDT中加载。所以需要操作系统保持一致性。
3. 同样不会更新`%rsp`。

调用约定：

关于syscall的调用约定，可以参考
<https://stackoverflow.com/questions/2535989/what-are-the-calling-conventions-for-unix-linux-system-calls-and-user-space-f>
简单来说，
1. 参数通过`%rdi, %rsi, %rdx, %r10, %r8, %r9`这几个寄存器传递，最多六个参数，不会直接从栈上传值。
2. 调用时`%rax`存放系统调用号。
3. `%rcx, %r11`会被修改（见上面`syscall/sysret`指令的说明），`%rax`中存放系统调用结果或`errno`。其他寄存器的值都保留

### 初始化

1. 如下代码写入了`IA32_LSTAR MSR`和`IA32_FMASK MSR`，满足上述`syscall`指令1和2的要求。
   设置了系统调用的入口地址`entry_SYSCALL_64`，以及要屏蔽的flags（例如关闭中断`IF`）。
   ```
   // file: arch/x86/kernel/cpu/common.c

   void syscall_init(void)
   {
       wrmsrl(MSR_LSTAR, (unsigned long)entry_SYSCALL_64);
       /* Flags to clear on syscall */
       wrmsrl(MSR_SYSCALL_MASK,
              X86_EFLAGS_TF|X86_EFLAGS_DF|X86_EFLAGS_IF|
              X86_EFLAGS_IOPL|X86_EFLAGS_AC|X86_EFLAGS_NT);
   }
   ```
2. 我们看到`syscall`和`sysret`从`IA32_STAR MSR`的特定位加载`CS`/`SS`段选择子。`syscall`加载kernel段，`sysret`加载用户段。

   `IA32_STAR MSR`对应位的初始化在进程切换的时候会更新（TODO：应该是这样，没查阅代码）。`syscall/sysret`执行时并不会保存`CS/SS`的值。

   `GDT/LDT`初始化和切换时的段描述符也应该和指令要求的值相同。（TODO：应该是这样，没查阅代码）

3. `IA32_KERNEL_GS_BASE MSR`也需要在进程切换的时候更新。（`swapgs`指令使用，见下面）

### 单个syscall执行过程
用户空间代码通过`syscall`指令调用某个系统调用时，根据上一节的分析，会进入`entry_SYSCALL_64`。把这块实现分为三部分：
1. 调用`do_syscall_64`之前的准备工作。
2. 调用`do_syscall_64`。
3. 调用`do_syscall_64`之后，为返回用户空间做准备并返回用户空间。

#### 切换到kernel space后
先看一下前半部分，调用`do_syscall_64`之前的准备工作

```asm
    // file: arch/x86/entry/entry_64.S
  1 ENTRY(entry_SYSCALL_64)
  2 	UNWIND_HINT_EMPTY
  3 	/*
  4 	 * Interrupts are off on entry.
  5 	 * We do not frame this tiny irq-off block with TRACE_IRQS_OFF/ON,
  6 	 * it is too small to ever cause noticeable irq latency.
  7 	 */
  8
  9 	swapgs
 10 	/*
 11 	 * This path is only taken when PAGE_TABLE_ISOLATION is disabled so it
 12 	 * is not required to switch CR3.
 13 	 */
 14 	movq	%rsp, PER_CPU_VAR(rsp_scratch)
 15 	movq	PER_CPU_VAR(cpu_current_top_of_stack), %rsp
 16
 17 	/* Construct struct pt_regs on stack */
 18 	pushq	$__USER_DS			/* pt_regs->ss */
 19 	pushq	PER_CPU_VAR(rsp_scratch)	/* pt_regs->sp */
 20 	pushq	%r11				/* pt_regs->flags */
 21 	pushq	$__USER_CS			/* pt_regs->cs */
 22 	pushq	%rcx				/* pt_regs->ip */
 23 GLOBAL(entry_SYSCALL_64_after_hwframe)
 24 	pushq	%rax				/* pt_regs->orig_ax */
 25
 26 	PUSH_AND_CLEAR_REGS rax=$-ENOSYS
 27
 28 	TRACE_IRQS_OFF
 29
 30 	/* IRQs are off. */
 31 	movq	%rax, %rdi
 32 	movq	%rsp, %rsi
 33 	call	do_syscall_64		/* returns with IRQs disabled */
```

`syscall`指令执行的时候根据`MSR_SYSCALL_MASK`，已经disable了中断。

`swapgs`和`syscall`指令设计上成对使用。syscall指令不会自动切换rsp，如果切换到ring0需要使用stack的话，就需要操作系统来处理栈切换。
`swapgs`指令交换当前`%gs`寄存器和`IA32_KERNEL_GS_BASE MSR`。在此处的效果就是把kernel space的`%gs`和当前user space的`%gs`交换。

> Note:
>
> linux x86_64架构下userspace中`gs`如何使用是不确定的(https://www.kernel.org/doc/html/latest/x86/x86_64/fsgs.html)，
> 在kernel space中用于per cpu area(https://github.com/torvalds/linux/blob/master/arch/x86/include/asm/stackprotector.h):
>
> > The same segment is shared by percpu area and stack canary.  On
> > x86_64, percpu symbols are zero based and %gs (64-bit) points to the
> > base of percpu area.

接下来14-15行保存当前`%rsp`，并把当前进程的kernel stack指针加载到`%rsp`。`cpu_current_top_of_stack`在进程切换的时候更新（`arch/x86/kernel/process_64.c:switch_to`）。

这里注意一点，因为加载的是进程的kernel stack，系统调用是在进程上下文（process context）中执行的。

18-26行将用户空间寄存器压栈，存到struct pt_regs中。

到此为止已经完成了用户空间到内核空间的切换，主要几个部分：
* `syscall`指令本身完成ring3 -> ring0的切换，以及`CS：IP`的切换；
* `swapgs` 之后更新`rsp`完成用户堆栈到进程内核栈的切换；
* 用户寄存器入栈保存，初始化`pt_regs`;
接下来31-32行给do_syscall_64传参，接着33行调用。第一个参数是系统调用号，用户空间调用的时候通过rax传进来，第二个参数是上面构造的pt_regs的指针。这里就是直接调用c函数，使用一般的c调用约定。

#### 切换回用户空间的过程
我们在下一节再看一下具体某个系统调用是如何定义和执行的，先看一下系统调用完成后，切换回用户空间的过程。大体上来说是切换到内核空间的一个逆过程。

**检查确定是否可以通过`sysret`返回**

从37行开始，首先通过一系列的check，优先采用`sysret`指令快速返回，如果check不通过，fallback到`iret`方式。与进入内核空间的几个动作相反，需要切换回用户空间，从系统调用之后的指令继续执行。
这个检查是[15年一个patch](https://github.com/torvalds/linux/commit/2a23c6b8a9c42620182a2d2cfc7c16f6ff8c42b4)引入的，主要check了几个点：
1. 检查保存的`RCX`和`RIP`是否相等，`R11`和`RFLAGS`是否相等。
2. 保存的`CS`/`SS`是否有变化。
3. check`sysret`的 bug：`RIP`地址是canonical的；`RF` flag没有设置。

如果上述检查都通过，109行之后进入`sysret`的返回路径。

> Q： 1和2的检查是否必要，能否不检查从而可以进一步优化速度？
>
>   72行和102行检查保存的`CS`和`SS`有没有变化，是为了和`iret`路径的行为保持一致。因为`iret`路径的`%cs/%ss`是从栈上保存的`CS/SS`恢复的，而`sysret`是从`MSR`恢复的。
>
>   42行到46行，检查保存在栈上的RCX和RIP是否相等，如果不等进入`iret`的路径。42行同时把`RCX`的值恢复到了`%rcx`寄存器中。如果不检查，假设我们把42行到46行修改为如下两条指令：
>   ```
>   movq	RIP(%rsp), %rcx
>   movq	%rcx, %r11
>   ```
>   看起来符合`sysret`的要求，跟`iret`达到的效果一样，都可以返回到`RIP(%rsp)`的地址；也不影响下面几行对canonical 地址的检查。而且节省了两条指令（外加减少一次访存）。
>
>   但是这个改法会造成`RCX`被修改的情况下，`sysret`路径和`iret`路径的不一致，因为它实际上没有恢复`%rcx`的值。中断的情况下，返回到用户空间之前，所有的寄存器都应该恢复（因为需要对被中断的程序透明）。为保持兼容，`sysret`返回之前也需要恢复寄存器的值，而112行`POP_REGS pop_rdi=0 skip_r11rcx=1`跳过了`r11/rcx`的恢复，避免重复恢复两遍。
>
>   所以综合来看，上述改法会造成`sysret`和`iret`的行为不一致。而为了达到一致的行为（恢复`rcx`寄存器的值，且返回到相同的地址），目前的代码都是必要的。
>
>   对75-77行，`R11==RFLAGS`的检查来说是同样的道理。
>
>   理论上在`ptrace`（例如使用gdb调试）和`signal handler`的情况下，有可能修改栈上寄存器的值，遇到上面检查的这些情况。
>
>   [stack overflow上这个回答以及comments](https://stackoverflow.com/a/47997378/2705629)也有相关讨论

```
    //// file: arch/x86/entry/entry_64.S
 34
 35 	TRACE_IRQS_IRETQ		/* we're about to change IF */
 36
 37 	/*
 38 	 * Try to use SYSRET instead of IRET if we're returning to
 39 	 * a completely clean 64-bit userspace context.  If we're not,
 40 	 * go to the slow exit path.
 41 	 */
 42 	movq	RCX(%rsp), %rcx
 43 	movq	RIP(%rsp), %r11
 44
 45 	cmpq	%rcx, %r11	/* SYSRET requires RCX == RIP */
 46 	jne	swapgs_restore_regs_and_return_to_usermode
 47
 48
 49 	/*
 50 	 * On Intel CPUs, SYSRET with non-canonical RCX/RIP will #GP
 51 	 * in kernel space.  This essentially lets the user take over
 52 	 * the kernel, since userspace controls RSP.
 53 	 *
 54 	 * If width of "canonical tail" ever becomes variable, this will need
 55 	 * to be updated to remain correct on both old and new CPUs.
 56 	 *
 57 	 * Change top bits to match most significant bit (47th or 56th bit
 58 	 * depending on paging mode) in the address.
 59 	 */
 60 #ifdef CONFIG_X86_5LEVEL
 61 	ALTERNATIVE "shl $(64 - 48), %rcx; sar $(64 - 48), %rcx", \
 62 		"shl $(64 - 57), %rcx; sar $(64 - 57), %rcx", X86_FEATURE_LA57
 63 #else
 64 	shl	$(64 - (__VIRTUAL_MASK_SHIFT+1)), %rcx
 65 	sar	$(64 - (__VIRTUAL_MASK_SHIFT+1)), %rcx
 66 #endif
 67
 68 	/* If this changed %rcx, it was not canonical */
 69 	cmpq	%rcx, %r11
 70 	jne	swapgs_restore_regs_and_return_to_usermode
 71
 72 	cmpq	$__USER_CS, CS(%rsp)		/* CS must match SYSRET */
 73 	jne	swapgs_restore_regs_and_return_to_usermode
 74
 75 	movq	R11(%rsp), %r11
 76 	cmpq	%r11, EFLAGS(%rsp)		/* R11 == RFLAGS */
 77 	jne	swapgs_restore_regs_and_return_to_usermode
 78
 79 	/*
 80 	 * SYSCALL clears RF when it saves RFLAGS in R11 and SYSRET cannot
 81 	 * restore RF properly. If the slowpath sets it for whatever reason, we
 82 	 * need to restore it correctly.
 83 	 *
 84 	 * SYSRET can restore TF, but unlike IRET, restoring TF results in a
 85 	 * trap from userspace immediately after SYSRET.  This would cause an
 86 	 * infinite loop whenever #DB happens with register state that satisfies
 87 	 * the opportunistic SYSRET conditions.  For example, single-stepping
 88 	 * this user code:
 89 	 *
 90 	 *           movq	$stuck_here, %rcx
 91 	 *           pushfq
 92 	 *           popq %r11
 93 	 *   stuck_here:
 94 	 *
 95 	 * would never get past 'stuck_here'.
 96 	 */
 97 	testq	$(X86_EFLAGS_RF|X86_EFLAGS_TF), %r11
 98 	jnz	swapgs_restore_regs_and_return_to_usermode
 99
100 	/* nothing to check for RSP */
101
102 	cmpq	$__USER_DS, SS(%rsp)		/* SS must match SYSRET */
103 	jne	swapgs_restore_regs_and_return_to_usermode
109 syscall_return_via_sysret:
```

**`sysret`返回与寄存器恢复，栈切换**

接下来通过`syscall_return_via_sysret`切换回用户空间做了几件事：
1. 恢复寄存器`%rsp`和`%rdi`之外的所有寄存器，因为这两个寄存器下面还会用到。
2. 118行到132行，使用trampoline stack切换到用户空间。`%rsp`切换回用户栈。

> Q: 为什么需要使用trampoline stack？
> 首先，在不开启PTI的情况下，我认为是没必要的。不开启PTI的情况下，`sysret`返回用户空间不需要更新页表。
> `SWITCH_TO_USER_CR3_STACK`实际是空的。这时候使用trampoline stack不过是把`%rsp`，`%rdi`
> push后又pop出来，没什么实际作用。
>
> 在开启PTI的情况下，切换到用户空间需要切换页表。用户空间页表是没法访问内核栈的，
> 所以没法在切换回用户页表（`SWITCH_TO_USER_CR3_STACK`）后从内核栈上pop `%rsp`。
> 另一方面，`SWITCH_TO_USER_CR3_STACK`切换用户页表需要使用栈（或寄存器），所以也不能先恢复`%rsp`再切换页表。
> 否则切换到用户栈之后, `SWITCH_TO_USER_CR3_STACK`用到的寄存器就没法恢复了（因为原始值存储在内核栈上）。
> 解决方案就是现在这样使用trampoline stack做一个中转。

```
105 	/*
106 	 * We win! This label is here just for ease of understanding
107 	 * perf profiles. Nothing jumps here.
108 	 */
109 syscall_return_via_sysret:
110 	/* rcx and r11 are already restored (see code above) */
111 	UNWIND_HINT_EMPTY
112 	POP_REGS pop_rdi=0 skip_r11rcx=1
113
114 	/*
115 	 * Now all regs are restored except RSP and RDI.
116 	 * Save old stack pointer and switch to trampoline stack.
117 	 */
118 	movq	%rsp, %rdi
119 	movq	PER_CPU_VAR(cpu_tss_rw + TSS_sp0), %rsp
120
121 	pushq	RSP-RDI(%rdi)	/* RSP */
122 	pushq	(%rdi)		/* RDI */
123
124 	/*
125 	 * We are on the trampoline stack.  All regs except RDI are live.
126 	 * We can do future final exit work right here.
127 	 */
128 	SWITCH_TO_USER_CR3_STACK scratch_reg=%rdi
129
130 	popq	%rdi
131 	popq	%rsp
132 	USERGS_SYSRET64
133 END(entry_SYSCALL_64)
134
```

#### 执行系统调用 - `do_syscall_64`
回到中间的步骤，某个系统调用的调用过程。

第6行打开当前cpu的中断。允许在执行系统调用的过程中响应中断。这也是在process context中执行系统调用的好处。

19行根据系统调用号nr找到对应的系统调用（见下面`read`例子），regs作为参数传进去。结果存到`regs->ax`中。
函数最后调用`syscall_return_slowpath`，完成关闭中断等操作，为返回用户空间做准备。

```c
// file: arch/x86/entry/common.c
 1 __visible void do_syscall_64(unsigned long nr, struct pt_regs *regs)
 2 {
 3 	struct thread_info *ti;
 4
 5 	enter_from_user_mode();
 6 	local_irq_enable();
 7 	ti = current_thread_info();
 8 	if (READ_ONCE(ti->flags) & _TIF_WORK_SYSCALL_ENTRY)
 9 		nr = syscall_trace_enter(regs);
10
11 	/*
12 	 * NB: Native and x32 syscalls are dispatched from the same
13 	 * table.  The only functional difference is the x32 bit in
14 	 * regs->orig_ax, which changes the behavior of some syscalls.
15 	 */
16 	nr &= __SYSCALL_MASK;
17 	if (likely(nr < NR_syscalls)) {
18 		nr = array_index_nospec(nr, NR_syscalls);
19 		regs->ax = sys_call_table[nr](regs);
20 	}
21
22 	syscall_return_slowpath(regs);
23 }
```

**根据系统调用号找到entry并调用**

结合`syscall_64.c` 和`syscalls_64.h`来看。以`read`系统调用为例，
在`syscall_64.c`中定义了两次`__SYSCALL_64`宏。

1-2行展开后就是对每个系统调用的函数声明。

13行展开后变成`[0]=__x64_sys_read`等，即对`sys_call_table`的初始化，初始化为系统调用号对应的函数指针。

所以可以根据系统调用号`0`找到对应的定义`__x64_sys_read`。

```c
////file: linux/arch/x86/entry/syscall_64.c
 1 #define __SYSCALL_64(nr, sym, qual) extern asmlinkage long sym(const struct pt_regs *);
 2 #include <asm/syscalls_64.h>
 3 #undef __SYSCALL_64
 4
 5 #define __SYSCALL_64(nr, sym, qual) [nr] = sym,
 6
 7 asmlinkage const sys_call_ptr_t sys_call_table[__NR_syscall_max+1] = {
 8 	/*
 9 	 * Smells like a compiler bug -- it doesn't work
10 	 * when the & below is removed.
11 	 */
12 	[0 ... __NR_syscall_max] = &sys_ni_syscall,
13 #include <asm/syscalls_64.h>
14 };
```
```
17 ////file: linux/arch/x86/include/generated/asm/syscalls_64.h
18 #ifdef CONFIG_X86
19 __SYSCALL_64(0, __x64_sys_read, )
20 #else /* CONFIG_UML */
21 __SYSCALL_64(0, sys_read, )
```

**系统调用的定义**

继续看`__x64_sys_read`实现。`__x64_`开头这些entry不是直接定义的，而是通过`SYSCALL_DEFINE`（`linux/include/linux/syscalls.h`）宏展开后定义的。
关于`read`实际的业务逻辑本文不再赘述。

```c
////file: linux/fs/read_write.c
SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)
{
	return ksys_read(fd, buf, count);
}
```
例如`read`展开后如下（有大量简化）。从`regs`中取出来参数，并调用`ksys_read`。
```
long __x64_sys_read(const struct pt_regs *regs)
{
	return __se_sys_read(regs->di, regs->si, regs->dx);
}
static long __se_sys_read(unsigned int fd, char __user * buf, size_t count)
{
	long ret = __do_sys_read((unsigned int)fd, (char *)buf, (size_t)count);
	return ret;
}
static long
	__do_sys_read(unsigned int fd, char *buf, size_t count)
{
	return ksys_read(fd, buf, count);
}
```

User Space library (glibc) 实现
-----------------------------
对用户应用来说，一般也不会直接调用syscalls, 而是通过语言库的api来间接调用。
比如C library有glibc，newlib等。[rust目前直接使用C library链接](https://news.ycombinator.com/item?id=9435804)，
但是[linux的go实现可以不依赖C library](https://stackoverflow.com/questions/41720090/does-go-depend-on-c-runtime)。

根据 <https://sourceware.org/glibc/wiki/SyscallWrappers>, 在`glibc`中有三种syscall wrapper：

* Assembly syscalls： 定义在`syscalls.list`中，通过脚本`make-syscalls.sh`去生成系统调用。
* Macro Syscalls：一些复杂的system call，通过上面的方式不好处理的。
* Bespoke Syscalls： 有些系统调用比较特殊，用上述两种模式覆盖不了的情况下，需要单独实现。

本文我们仅对Macro syscalls做一些较详细的分析。

### Macro Syscalls
大部分系统调用的实现采用的这种方式。glibc提供一组macro来封装系统调用，给上层使用。
例如对`fopen`库函数，64位程序下调用到`__libc_open64`,调用链如下
```
libio/iofopen.c:_IO_new_fopen
 libio/iofopen.c:__fopen_internal
  libio/fileops.c:_IO_new_file_fopen
   libio/fileops.c:_IO_file_open
    sysdeps/unix/sysv/linux/open64.c:__libc_open64
```

```c
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
类似的，对`-m32`编译出的32位程序，会调用到`sysdeps/unix/sysv/linux/open.c:__libc_open`，同样会调用`SYSCALL_CANCEL`。

#### 宏展开
具体看一下`SYSCALL_CANCEL`的实现：
```c
//// file: sysdeps/unix/sysdep.h
#define __INLINE_SYSCALL0(name) \
  INLINE_SYSCALL (name, 0)
////  省略SYSCALL1..6
#define __INLINE_SYSCALL7(name, a1, a2, a3, a4, a5, a6, a7) \
  INLINE_SYSCALL (name, 7, a1, a2, a3, a4, a5, a6, a7)

#define __INLINE_SYSCALL_NARGS_X(a,b,c,d,e,f,g,h,n,...) n
#define __INLINE_SYSCALL_NARGS(...) \
  __INLINE_SYSCALL_NARGS_X (__VA_ARGS__,7,6,5,4,3,2,1,0,)
#define __INLINE_SYSCALL_DISP(b,...) \
  __SYSCALL_CONCAT (b,__INLINE_SYSCALL_NARGS(__VA_ARGS__))(__VA_ARGS__)

/* Issue a syscall defined by syscall number plus any other argument
   required.  Any error will be handled using arch defined macros and errno
   will be set accordingly.
   It is similar to INLINE_SYSCALL macro, but without the need to pass the
   expected argument number as second parameter.  */
#define INLINE_SYSCALL_CALL(...) \
  __INLINE_SYSCALL_DISP (__INLINE_SYSCALL, __VA_ARGS__)

#define SYSCALL_CANCEL(...) \
  ({									     \
    long int sc_ret;							     \
    if (SINGLE_THREAD_P) 						     \
      sc_ret = INLINE_SYSCALL_CALL (__VA_ARGS__); 			     \
    else								     \
      {									     \
	int sc_cancel_oldtype = LIBC_CANCEL_ASYNC ();			     \
	sc_ret = INLINE_SYSCALL_CALL (__VA_ARGS__);			     \
        LIBC_CANCEL_RESET (sc_cancel_oldtype);				     \
      }									     \
    sc_ret;								     \
  })
```

大概展开过程为：`SYSALL_CANCEL -> INLINE_SYSCALL_CALL -> INLINE_SYSCALL`。宏定义中计算传的参数个数，传给`INLINE_SYSCALL`。计算参数个数的方法还是比较巧妙的:)。
上面这部分是定义在`sysdep/unix/sysdep.h`中，与架构无关的。

继续看`INLINE_SYSCALL`的定义，就是架构相关的了，在不同的架构目录下。

#### x86_64

对x86_64，比较清晰，根据参数个数，调用`internal_syscall<nr>`，最终调用了`syscall`指令。参数也根据syscall 的调用约定放到规定的寄存器中。不需要保存寄存器的值，由kernel来负责保留。
```c
//// file: sysdeps/unix/sysv/linux/x86_64/sysdep.h
# define INLINE_SYSCALL(name, nr, args...) \
  ({									      \
    unsigned long int resultvar = INTERNAL_SYSCALL (name, , nr, args);	      \
    (long int) resultvar; })

#define INTERNAL_SYSCALL(name, err, nr, args...)			\
	internal_syscall##nr (SYS_ify (name), err, args)

#undef internal_syscall3
#define internal_syscall3(number, err, arg1, arg2, arg3)		\
({									\
    unsigned long int resultvar;					\
    TYPEFY (arg3, __arg3) = ARGIFY (arg3);			 	\
    TYPEFY (arg2, __arg2) = ARGIFY (arg2);			 	\
    TYPEFY (arg1, __arg1) = ARGIFY (arg1);			 	\
    register TYPEFY (arg3, _a3) asm ("rdx") = __arg3;			\
    register TYPEFY (arg2, _a2) asm ("rsi") = __arg2;			\
    register TYPEFY (arg1, _a1) asm ("rdi") = __arg1;			\
    asm volatile (							\
    "syscall\n\t"							\
    : "=a" (resultvar)							\
    : "0" (number), "r" (_a1), "r" (_a2), "r" (_a3)			\
    : "memory", REGISTERS_CLOBBERED_BY_SYSCALL);			\
    (long int) resultvar;						\
})
```

系统调用号使用`SYS_ify`宏获取。`__NR_##syscall_name`在系统的`/usr/include/asm/unistd.h`头文件中定义。
```
#define SYS_ify(syscall_name)	__NR_##syscall_name
```

#### i386

i386相对更复杂，从最初的`int 80`方式到后来intel的`sysenter`以及AMD的`syscall`不同的调用方式。
可以参考glibc源码的`sysdeps/unix/sysv/linux/i386/sysdep.h`，主要是`INTERNAL_SYSCALL_MAIN_INLINE`在不同的情况下会有不同的实现。

```
# define INLINE_SYSCALL(name, nr, args...) \
  ({									      \
    unsigned int resultvar = INTERNAL_SYSCALL (name, , nr, args);	      \
    : (int) resultvar; })

#define INTERNAL_SYSCALL(name, err, nr, args...) \
  ({									      \
    register unsigned int resultvar;					      \
    INTERNAL_SYSCALL_MAIN_##nr (name, err, args);			      \
    (int) resultvar; })
#define INTERNAL_SYSCALL_MAIN_0(name, err, args...) \
    INTERNAL_SYSCALL_MAIN_INLINE(name, err, 0, args)

#   define INTERNAL_SYSCALL_MAIN_INLINE(name, err, nr, args...) \
    LOADREGS_##nr(args)							\
    asm volatile (							\
    "call *_dl_sysinfo"							\
    : "=a" (resultvar)							\
    : "a" (__NR_##name) ASMARGS_##nr(args) : "memory", "cc")
```

例如在上述代码片段，`SYSCALL_CANCEL`展开后会调用 `call *_dl_sysinfo`。这个函数是kernel通过`vDSO`暴露出来的。
通过`_dl_sysinfo`，由kernel在启动后动态判断最优的调用syscall的方式。见下面`vDSO`章节的分析。

### glibc总结
个人理解，glibc采用三种不同的方式来实现syscall的调用，只是一种实现上的考量，是对kernel提供的系统调用的分类和抽象。
因为glibc支持不同插的CPU架构，kernel里对不同架构的系统调用的实现也不一样。glibc通过这三种抽象出来的模式可以更好的组织和管理代码。

对x86_64架构下的程序来说，不管是那种方式，从最终如何跟kernel的交互方式角度，有几种途径：

* vDSO：部分系统调用功能通过vDSO export到用户态，glibc在调用时不会真正陷入内核态
* 对64位程序，直接通过`syscall`指令
* 对32位的程序，根据编译选项调用通过vDSO中的`__kernel_vsyscall`，`syscall`或者`sysenter`。


vDSO
-----
为了解决一些调用非常频繁，而实际上有不需要高权限的系统调用而提出了vsyscall (virtual system call) 的方式来加速这些系统调用。但是vsyscall有一些限制，例如最多只有4个系统调用；对所有进程映射的地址相同等。
vDSO (virtual dynamic shared object)解决了最初vsystem call实现中的问题。
参考<https://stackoverflow.com/questions/19938324/what-are-vdso-and-vsyscall>

vDSO是内核代码的一部分，vDSO由kernel自动映射到所有用户空间中。通常用户程序不需要关注vDSO的使用，C library会自动使用vDSO中的功能。
例如`gettimeofday`，调用的时候不会陷入到内核态。另一个例子是上述`__kernel_vsyscall` 也是通过vDSO暴露出来的。

整体来说，kernel针对`gettimeofday`等系统调用优化实现，并且在进程启动的时候动态链接到每个进程中。glibc等库函数会优先调用vDSO中提供的系统调用以达到加速的目的。
我们分别从kernel和glibc两侧看一下。

### kernel实现

#### vDSO 定义
```c
//// file: linux arch/x86/entry/vdso/vclock_gettime.c
notrace int __vdso_gettimeofday(struct timeval *tv, struct timezone *tz)
{
	if (likely(tv != NULL)) {
		if (unlikely(do_realtime((struct timespec *)tv) == VCLOCK_NONE))
			return vdso_fallback_gtod(tv, tz);
		tv->tv_usec /= 1000;
	}
	if (unlikely(tz != NULL)) {
		tz->tz_minuteswest = gtod->tz_minuteswest;
		tz->tz_dsttime = gtod->tz_dsttime;
	}

	return 0;
}
int gettimeofday(struct timeval *, struct timezone *)
	__attribute__((weak, alias("__vdso_gettimeofday")));
```
#### kernel build

```
//// file: linux arch/x86/entry/vdso/Makefile
# files to link into the vdso
vobjs-y := vdso-note.o vclock_gettime.o vgetcpu.o
vobjs := $(foreach F,$(vobjs-y),$(obj)/$F)

$(obj)/%.so: OBJCOPYFLAGS := -S
$(obj)/%.so: $(obj)/%.so.dbg
	$(call if_changed,objcopy)
$(obj)/vdso64.so.dbg: $(obj)/vdso.lds $(vobjs) FORCE
	$(call if_changed,vdso)

$(obj)/vdso-image-%.c: $(obj)/vdso%.so.dbg $(obj)/vdso%.so $(obj)/vdso2c FORCE
	$(call if_changed,vdso2c)
```
kernel build流程中，先把`vclock_gettime.c`等这些定义build进`vdso64.so`, `vdso.64.so.dbg`镜像中，然后用`vdso2c`工具从镜像生成`vdso-image-64.c`，进而被build进kernel镜像中。
如下代码中，`vdso_image_64`变量中就包含了vdso的二进制（`vdso2c`处理过的）。

```c
//// file: linux arch/x86/entry/vdso/vdso-image-64.c
const struct vdso_image vdso_image_64 = {
	.data = raw_data,
	.size = 8192,
	.alt = 2997,
	.alt_len = 91,
	.sym_vvar_start = -12288,
	.sym_vvar_page = -12288,
	.sym_pvclock_page = -8192,
	.sym_hvclock_page = -4096,
};
```

#### 进程启动
我们查看linux上binary的动态链接库，会发现包含`linux-vdso`，例如：
```bash
$ ldd /usr/bin/uname
        linux-vdso.so.1 (0x00007ffff6118000)
        libc.so.6 => /usr/lib/libc.so.6 (0x00007f1fe821d000)
        /lib64/ld-linux-x86-64.so.2 => /usr/lib64/ld-linux-x86-64.so.2 (0x00007f1fe8423000)
```
kernel启动进程的时候，会把vdso map到进程地址空间(`map_vdso`)，并通过`auxiliary vector`传入地址(ARCH_DLINFO)。调用链如下：
```
fs/binfmt_elf.c:load_elf_binary
  ..vdso/vma.c:arch_setup_additional_pages
    ..vdso/vma.c:map_vdso_randomized
     ..vdso/vma.c:map_vdso

  fs/binfmt_elf.c:create_elf_tables
    ..elf.h:ARCH_DLINFO
```

```c
//// file: linux arch/x86/include/asm/elf.h
#define ARCH_DLINFO							\
do {									\
	if (vdso64_enabled)						\
		NEW_AUX_ENT(AT_SYSINFO_EHDR,				\
			    (unsigned long __force)current->mm->context.vdso); \
} while (0)

```

### glibc实现
glibc在需要调用系统调用的时候，需要能调用到vdso中定义的函数。整个过程大致为：

1. kernel创建进程进入用户空间执行，`ld-linux`会调用到`setup_vdso`，初始化vdso相关的变量`GLRO(dl_sysinfo_map)`等。调用的backtrace如下：

   ```
   #0  setup_vdso (first_preload=<synthetic pointer>, main_map=0x7ffff7ffe1a0) at ./setup-vdso.h:24
   #1  dl_main (phdr=<optimized out>, phnum=<optimized out>, user_entry=<optimized out>, auxv=<optimized out>) at rtld.c:1607
   #2  0x00007ffff7fec1e2 in _dl_sysdep_start (start_argptr=<optimized out>, dl_main=0x7ffff7fd34f0 <dl_main>) at ../elf/dl-sysdep.c:252
   #3  0x00007ffff7fd3041 in _dl_start_final (arg=0x7fffffffe3b0) at rtld.c:504
   #4  _dl_start (arg=0x7fffffffe3b0) at rtld.c:597
   #5  0x00007ffff7fd2098 in _start () from /lib64/ld-linux-x86-64.so.2
   ```

2. 针对某个syscall, 例如`gettimeofday`，会查找vdso中是否有定义，如果有，优先使用vdso中的定义。主要代码逻辑如下：

   ```
   # define HAVE_GETTIMEOFDAY_VSYSCALL     "__vdso_gettimeofday"

   ////file: glibc sysdeps/unix/sysv/linux/gettimeofday.c
     void *vdso_gettimeofday = dl_vdso_vsym (HAVE_GETTIMEOFDAY_VSYSCALL)
   libc_ifunc (__gettimeofday,
           vdso_gettimeofday ? VDSO_IFUNC_RET (vdso_gettimeofday)
       		      : (void *) __gettimeofday_syscall)

   ////file: glibc sysdeps/unix/sysv/linux/dl-vdso.h
   /* Functions for resolving symbols in the VDSO link map.  */
   static inline void *
   dl_vdso_vsym (const char *name)
   {
     struct link_map *map = GLRO (dl_sysinfo_map);
     if (map == NULL)
       return NULL;

     /* Use a WEAK REF so we don't error out if the symbol is not found.  */
     ElfW (Sym) wsym = { 0 };
     wsym.st_info = (unsigned char) ELFW (ST_INFO (STB_WEAK, STT_NOTYPE));

     struct r_found_version rfv = { VDSO_NAME, VDSO_HASH, 1, NULL };

     /* Search the scope of the vdso map.  */
     const ElfW (Sym) *ref = &wsym;
     lookup_t result = GLRO (dl_lookup_symbol_x) (name, map, &ref,
       				       map->l_local_scope,
       				       &rfv, 0, 0, NULL);
     return ref != NULL ? DL_SYMBOL_ADDRESS (result, ref) : NULL;
   }
   ```

### `__kernel_vsyscall`实现分析
对x86_64下32位的system call，通过vDSO函数`__kernel_vsyscall` 来自动选择使用最优的方式（`sysenter/syscall/int 80`）。
对x86_64下64bit system call，只有`syscall`指令，不需要`__kernel_vsyscall`来做选择。

我们上面看到32位程序调用syscall的时候，会通过`__kernel_vsyscall`来调用。`__kernel_vsyscall`也是通过vdso暴露出来的。

在`elf/setup-vdso.h:setup_vdso`中`_dl_sysinfo`初始化为vDSO中`__kernel_vsyscall`的地址。

使用`__kernel_vsyscall`的好处是可以让kernel来选择syscall的实现方式（int 80, sysenter, syscall）。我们看一下相关实现：

1. 首先，`__kernel_vsyscall`的定义中，根据CPU feature定义了alternative，选择`syscall`，`sysenter`或者`int 80`。

   `ALTERNATIVE`宏定义了在不同CPU feature的情况下，用新的指令替代旧指令，并记录在在`vmlinuz`中。

   ```
   ////file: linux arch/x86/entry/vdso/vdso32/system_call.S

   __kernel_vsyscall:
       CFI_STARTPROC
   //// ...
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
   GLOBAL(int80_landing_pad)
   //// ...
   ```

2. 然后kernel启动时，根据alternative的定义，动态替换相关指令。在`init_vdso_image`中，调用到了`apply_alternatives`。
   从而当glibc通过vdso调用`__kernel_vsyscall`时，实际调用的就是最优的指令。

   这样使用通用的binary（kernel和glibc），不需要在编译期就确定使用哪个指令实现syscall。

   ```c
   //// file: linux arch/x86/entry/vdso/vma.c
   void __init init_vdso_image(const struct vdso_image *image)
   {
       apply_alternatives((struct alt_instr *)(image->data + image->alt),
       		   (struct alt_instr *)(image->data + image->alt +
       					image->alt_len));
   }
   static int __init init_vdso(void)
   {
       init_vdso_image(&vdso_image_64);
   }
   subsys_initcall(init_vdso);
   ```

alternative 宏可参考：https://blog.csdn.net/choumin/article/details/115108813

更多参考：
------

* syscall 实现：

  - <https://blog.packagecloud.io/eng/2016/04/05/the-definitive-guide-to-linux-system-calls/>
  - <https://www.binss.me/blog/the-analysis-of-linux-system-call/>
     这两篇写syscall比较清晰详尽，也包含了一些背景。涵盖了x86 32位和64位下使用中断，`syscall`，`sysenter`等的不同实现。
  -  LWN "Anatomy of a system call", 也比较全面和系统。 <https://lwn.net/Articles/604515/> <https://lwn.net/Articles/604287/>
  - <https://stackoverflow.com/questions/35115470/linux-syscall-libc-vdso-and-implementation-dissection>
    动态链接情况下glibc的宏展开过程

* vDSO
  - <https://0xax.gitbooks.io/linux-insides/content/SysCall/linux-syscall-3.html>
  - <https://stackoverflow.com/questions/19938324/what-are-vdso-and-vsyscall>
  - <http://man7.org/linux/man-pages/man7/vdso.7.html>



* calling convention
  - <https://blog.csdn.net/qq_29328443/article/details/107232025>
  - <https://refspecs.linuxfoundation.org/elf/x86_64-abi-0.99.pdf>
  - <https://stackoverflow.com/questions/18133812/where-is-the-x86-64-system-v-abi-documented>
  - <https://stackoverflow.com/questions/2535989/what-are-the-calling-conventions-for-unix-linux-system-calls-and-user-space-f>
  - [linux/arch/x86/entry/calling.h](https://github.com/torvalds/linux/blob/master/arch/x86/entry/calling.h)


* KPTI
  - <https://www.kernel.org/doc/Documentation/x86/pti.txt>
  - <https://blog.csdn.net/pwl999/article/details/112686914>
  - <https://ctf-wiki.org/pwn/linux/kernel-mode/defense/isolation/user-kernel/kpti/#switch_to_user_cr3_stack>
