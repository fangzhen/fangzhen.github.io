**uefi target 下没有symbol的问题**
https://github.com/rust-lang/rust/issues/102537

next:
re-organize code
non-identity mapping paging - then we can use physical address 0
kernel code/ kernel stack setup instead of uefi stack
back to kernel; syscall
physical memory model
interrupt
cpu exception
qemu debug
SMP

unwinding
memory setup & allocator
  memblock: free memory
  memory mapping vs allocation

idle
https://www.kernel.org/doc/html/v5.0/admin-guide/pm/cpuidle.html
https://unix.stackexchange.com/questions/361245/what-does-an-idle-cpu-process-do
