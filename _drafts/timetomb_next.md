**uefi target 下没有symbol的问题**
https://github.com/rust-lang/rust/issues/102537

next:
memory management
process management
  schedule
concurrency/synchronize
interrupt
system call
block
vfs


unwinding
memory setup & allocator
  memblock: free memory
  memory mapping vs allocation

内存分配结果 - Option or NULL
naming: slab / kmem_cache

idle
https://www.kernel.org/doc/html/v5.0/admin-guide/pm/cpuidle.html
https://unix.stackexchange.com/questions/361245/what-does-an-idle-cpu-process-do

memory references:
understanding the linux virtual memory management  https://www.kernel.org/doc/gorman/html/understand/index.html 基于2.6内核
https://docs.kernel.org/mm/physical_memory.html
https://www.kernel.org/doc/html/v5.6/vm/memory-model.html 物理内存的flat discontig sparse模型。

[Linux核心概念详解](https://s3.shizhz.me/) 调度器和内存管理
https://richardweiyang-2.gitbook.io/kernel-exploring 系统启动 内存管理 中断和异常
