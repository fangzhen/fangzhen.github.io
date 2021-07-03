---
layout: post
title: rust baremetal
tags: rust os
date: 2021-05-13
update: 2021-09-27
---

# kernel需求
内核是在baremetal上直接运行的程序，无法利用任何操作系统提供的功能。
在操作系统环境下，rustc生成的可执行文件除了包含rust程序和依赖，还会包含一个小的运行时和standard library。
1. standard library会依赖底层操作系统功能，如线程，io等。所以也不能link进操作系统内核开发。
`#![no_std]`来禁用掉standard library
2. 运行时做一些初始化工作，例如setup堆栈，然后调用main函数。这些初始化动作是不适合操作系统内核的，例如，它的内存初始化需要基于操作系统提供的虚拟内存，而kernel需要直接与物理内存打交道。
 `#![no_main]`来告诉编译期我们不定义main函数。linker默认的入口点为_start,我们需要定义该函数。使用no_mangle 防止rustc mangle 函数名。
```
#[no_mangle]
pub extern "C" fn _start() -> ! {
```

# rust additions

## nightly
通过rust-toolchain文件指定本项目使用nightly channel。
```
[toolchain]
channel = "nightly"
components = ["rust-src"]
```

## target
rust支持不同的target，rustc会根据target生成不同的编译选项。默认x86的target都是有操作系统信息的，所以我们自定义一个target用于本项目的build。
列出内置的target和target 的json spec：
`rustc +nightly  --print target-list`
`rustc +nightly -Z unstable-options --print target-spec-json --target x86_64-unknown-linux-gnu`
例如，我们对于x86系统使用的target为 targets/x86_64.json

可以用`cargo rustc -- -Z print-link-args`来显示rustc生成的linker命令和参数。

## panic
注意到我们有设置`"panic-strategy": "abort",`，来禁用stack unwinding。
定义了panic_handler.
```
#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
```
// TODO 这块不太清晰

## core crate
虽然不能利用操作系统特性，我们可以利用rust语言本身的特性，这些特性有些由core crate提供，如Options。通常来说，应该使用rustc自带的core binary。但是对于自定义的target, 需要重新编译core crate。需要使用如下unstable特性：
```
[unstable]
build-std = ["core"]
```

# Other
## redzone
`"disable-redzone": true,`
简单来说redzone是一种优化，可以使用栈顶之外的128字节。在中断的情况下，handler中不知道sp之外的空间被使用了，所以根据sp访问内存有可能会破坏原来的栈桢。

## CPU feature
`"features": "-mmx,-sse"`

Refer：
https://os.phil-opp.com/freestanding-rust-binary/
https://os.phil-opp.com/minimal-rust-kernel/
从一步一步的错误出发，引出baremetal 程序需要的配置。
