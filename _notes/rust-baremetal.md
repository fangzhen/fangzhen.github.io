---
layout: post
title: 构建在Baremetal上直接运行的Rust程序
tags: rust os
date: 2021-05-13
update: 2023-03-14
---

操作系统内核内核无法像上层应用一样使用操作系统提供的功能。
创建操作系统内核的第一步是构建可以不依赖操作系统直接运行在baremetal上的程序。

本文主要对构建可以Baremetal上直接运行的Rust程序所需要做的事情做个记录和说明。

## 不使用 stdlib
stdlib会依赖底层操作系统功能，如线程，io等。使用`#![no_std]`来禁用掉standard library

## Entry point
虽然用户程序入口是`main`，但是在`main`执行前需要进行一定的初始化工作，如setup stack，传入参数等。
对于典型的链接了stdlib的rust程序来说，程序从C runtime的`crt0`开始，然后执行rust runtime的entrypoint(`#[start]`)。然后才调用到用户编写的`main`函数。

C runtime和Rust runtime 都是对操作系统内核有依赖的，所以我们要避免使用。
例如，它的内存初始化需要基于操作系统提供的虚拟内存，而kernel需要直接与物理内存打交道。

用`#![no_main]`来指定我们不定义`main`函数。
然后，我们需要定义linker默认的入口点为`_start`，同时要使用`#[no_mangle]` 防止rustc mangle 函数名，如下定义了程序入口点：
```
#[no_mangle]
pub extern "C" fn _start() -> ! {
```

## build-std
虽然不能利用操作系统特性，我们可以利用rust语言本身的特性，这些特性有些由core crate提供，如`Option`s。通常来说，应该使用rustc自带的core binary。如果对于自定义的target,或者不想使用预编译的binary,可以重新编译core crate。需要使用cargo的unstable特性：

如下指定重新编译`core` library，并指定了`compiler-builtins-mem`，以避免在core 中依赖操作系统相关的内存管理。

```
# .cargo/config
[unstable]
build-std = ["core"]
build-std-features = ["compiler-builtins-mem"]
```
```
# ./rust-toolchain
[toolchain]
channel = "nightly"
components = ["rust-src"]
```

## Targets
rust支持不同的target，rustc会根据target生成不同的编译选项。
使用以下命令可以列出内置的target和target 的json spec：
```
rustc --print target-list
rustc -Z unstable-options --print target-spec-json --target x86_64-unknown-linux-gnu
```
对于x86_64的baremetal程序，可以直接使用`x86_64-unknown-none`这个target。
```
$ rustc +nightly -Z unstable-options --print target-spec-json --target x86_64-unknown-none
{
  "arch": "x86_64",
  "code-model": "kernel",
  "cpu": "x86-64",
  "data-layout": "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128",
  "disable-redzone": true,
  "features": "-mmx,-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-3dnow,-3dnowa,-avx,-avx2,+soft-float",
  "is-builtin": true,
  "linker": "rust-lld",
  "linker-flavor": "ld.lld",
  "llvm-target": "x86_64-unknown-none-elf",
  "max-atomic-width": 64,
  "panic-strategy": "abort",
  "position-independent-executables": true,
  "relro-level": "full",
  "stack-probes": {
    "kind": "inline-or-call",
    "min-llvm-version-for-inline": [
      16,
      0,
      0
    ]
  },
  "static-position-independent-executables": true,
  "supported-sanitizers": [
    "kcfi",
    "kernel-address"
  ],
  "target-pointer-width": "64"
}
```

另外可以用`cargo rustc -- --print link-args`来显示rustc生成的linker命令和参数。

## Language items
rustc 有一些可插拔的操作，没有hardcode在语言本身，而是在库中提供实现。库中的实现通过`#[lang = "..."]`来标记，这些操作被称为language items。可参考<https://doc.rust-lang.org/beta/unstable-book/language-features/lang-items.html>

其中有两个是rustc假定存在的，在不使用stdlib的情况下，需要我们自己来定义。
1. `rust_eh_personality`。通过在target中设置`"panic-strategy": "abort",`，来禁用stack unwinding，可以不需要该函数。
2. `panic_impl`，可以通过`#[panic_handler]`来实现：
```
#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
```

## Red zone
`x86_64-unknown-none`target还有个配置`"disable-redzone": true`也值得一提。

简单来说redzone是一种[System_V_ABI](https://wiki.osdev.org/System_V_ABI) 的calling convention的一个优化，可以使用栈顶之外的128字节。这样在叶子函数(leaf function)中可以不移动栈指针使用栈外的128字节。
但是在CPU中断的情况下，中断handler中不知道sp之外的空间被使用了，所以在中断handler中可能会破坏原来的栈桢。因此在kernel中必须关闭redzone。

## 结语
本文的内容基本只能保证可以编译出来一个baremetal的rust程序，还无法实际执行任何有意义的代码。例如在执行入口函数`_start`之前，我们需要stack已经初始化（因为rustc编译出的二进制有这个假定）。对于x86_64程序来说，当前处于real mode/protect mode/long mode等也都很重要。
在x86_64架构生态下，BIOS和UEFI固件提供了类似的基础。

## Reference
* 从一步一步的错误出发，引出baremetal 程序需要的配置。非常清晰和详细，也是本文参考最多的。
  - <https://os.phil-opp.com/freestanding-rust-binary/>
  - <https://os.phil-opp.com/minimal-rust-kernel/>

* 关于language item和不使用stdlib说明可参考：
  <https://doc.rust-lang.org/beta/unstable-book/language-features/lang-items.html>
