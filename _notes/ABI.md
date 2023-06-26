---
layout: post
title: ABI与调用约定
tags: [ABI, "calling convention"]
date: 2023-06-26
update: 2023-06-26
---

ABI(Application Binary Interface) 是指二进制模块之间的接口，比如用户程序调用库函数或系统调用。
通过约定ABI，达到在二进制级别的互操作。相比一般而言的API，ABI处于更底层。

ABI 主要包含[wikipedia](https://en.wikipedia.org/wiki/Application_binary_interface)：
* 处理器架构相关，例如指令集，内存访问（分页，栈，虚拟内存，对齐等）
* 调用约定：例如函数参数如何传递，寄存器如何使用
* 系统调用
* 完整的操作系统ABI还应该包括目标文件，二进制文件等的格式

## 不同架构下的ABI标准：
### x86_64
[Microsoft x64 ABI](https://learn.microsoft.com/en-us/cpp/build/x64-software-conventions)

[System V ABI](https://gitlab.com/x86-psABIs/x86-64-ABI/) [下载](https://gitlab.com/x86-psABIs/x86-64-ABI/-/jobs/artifacts/master/raw/x86-64-ABI/abi.pdf?job=build)

## Calling Convention
调用约定是ABI的重要组成部分。例如当C语言用户程序调用库函数时，调用方与被调用方可以是在不同机器使用不同的编译器编译的。两者必须遵循一致的调用约定才能正确调用。
以x86_64为例，上述ms和sysv的ABI各自定义了调用约定。简单对比如下：

|                        | sysv abi                                                               | ms abi                                                                 |
|------------------------|------------------------------------------------------------------------|------------------------------------------------------------------------|
| 参数传递               | 前六个整形或指针参数通过RDI, RSI, RDX, RCX, R8, R9传递；剩余参数通过栈 | 前四个参数通过寄存器传递，例如整型通过rcx, rdx, r8, r9；剩余参数通过栈 |
| 返回值                 | rax(最多64位)或rax和rdx(最多128位)                                     | rax(最多64位)                                                          |
| callee-saved registers | RBP, RBX, RSP, R12, R13, R14, R15                                      | RBX, RBP, RDI, RSI, RSP, R12, R13, R14, R15, XMM6:XMM15                |
| caller-saved registers | RAX, RCX, RDX, RSI, RDI, R8, R9, R10, R11, XMM0:XMM16                  | RAX, RCX, RDX, R8, R9, R10, R11, XMM0:XMM5                             |

> Note:
>
> 上述表格内容不完整，具体细节请参考ABI文档。

考虑如下C程序，`__attribute__((sysv_abi))`指定使用哪种ABI，gcc和clang都支持该语法。
```
__attribute__((sysv_abi)) int foo(int x, int y);

__attribute__((ms_abi)) void bar(int x, int y){
    int a = 3;
    foo(a,4);
}

void main(void) {
    bar(1, 2);
    foo(4, 5);
}
```
gcc 编译对应的汇编结果如下，可以看到参数传递，返回值等都按照上述calling convention生成了对应的汇编代码。

**save-restore寄存器**

一个值得注意的点是，生成的代码中，对于caller/callee-saved register处理时，为了提高效率，并不会save-restore所有寄存器，而只是保存必要的寄存器。
例如在`main`中，并没有保存sysv abi中定义的caller-saved register。
因为编译器可以推断出来，即使`foo, bar`中修改了这些寄存器(如RCX)的值，对程序的正确性也没有影响，因为：
1. `main`函数中，在调用`bar`和`foo`后没有使用到这些寄存器。
2. `main`的caller如果使用了`RCX`，它需要自己save-restore RCX的值，因为RCX是caller-saved。

但是我们可以看到`bar`的汇编代码中在调用`foo`前后分别对`RDI, RSI, XMM6:XMM15`这些寄存器做了save和restore的操作。原因如下：
以RDI为例，RDI在sysv abi中是caller saved，但在ms abi中是callee saved。
所以如果`foo`中修改了RDI，它并不会在返回前恢复RDI的值，所以`bar`无法确定调用`foo`后RDI的值有没有被修改。
而对于`bar`来说，它本身要依照ms abi的约定，RDI是callee saved，`main`调用`bar`后预期是RDI没有修改。
为了保证RDI在bar返回时没有被修改，它就需要保存并恢复RDI的值。

同理其他寄存器。

```
bar:
        pushq   %rbp
        movq    %rsp, %rbp
        pushq   %rdi
        pushq   %rsi
        subq    $176, %rsp
        movaps  %xmm6, 16(%rsp)
        movaps  %xmm7, 32(%rsp)
        movaps  %xmm8, 48(%rsp)
        movaps  %xmm9, -128(%rbp)
        movaps  %xmm10, -112(%rbp)
        movaps  %xmm11, -96(%rbp)
        movaps  %xmm12, -80(%rbp)
        movaps  %xmm13, -64(%rbp)
        movaps  %xmm14, -48(%rbp)
        movaps  %xmm15, -32(%rbp)
        movl    %ecx, 16(%rbp)
        movl    %edx, 24(%rbp)
        movl    $3, -180(%rbp)
        movl    -180(%rbp), %eax
        movl    $4, %esi
        movl    %eax, %edi
        call    foo
        nop
        movaps  16(%rsp), %xmm6
        movaps  32(%rsp), %xmm7
        movaps  48(%rsp), %xmm8
        movaps  -128(%rbp), %xmm9
        movaps  -112(%rbp), %xmm10
        movaps  -96(%rbp), %xmm11
        movaps  -80(%rbp), %xmm12
        movaps  -64(%rbp), %xmm13
        movaps  -48(%rbp), %xmm14
        movaps  -32(%rbp), %xmm15
        addq    $176, %rsp
        popq    %rsi
        popq    %rdi
        popq    %rbp
        ret
main:
        pushq   %rbp
        movq    %rsp, %rbp
        subq    $32, %rsp
        movl    $2, %edx
        movl    $1, %ecx
        call    bar
        addq    $32, %rsp
        movl    $5, %esi
        movl    $4, %edi
        call    foo
        nop
        leave
        ret
```

### 其他
在kernel开发中，根据处理器规则，有些函数可能无法遵循上述调用约定，如：
* 中断处理函数：因为中断可以在任何指令处发生和处理，所以中断处理函数返回前需要保证恢复所有可能被修改的寄存器
* 系统调用：x86_64中如果使用`syscall/sysret`实现系统调用，rcx, r11的值会被修改。Linux下的实现可参考[Linux下系统调用实现]({% link _notes/syscall.md %})

## References
- ABI
  * <https://en.wikipedia.org/wiki/Application_binary_interface>
- calling convention
  * <https://stackoverflow.com/questions/69869519/is-it-possible-to-change-calling-convention-in-gcc-for-x64>
  * <https://en.wikipedia.org/wiki/Calling_convention>
  * [ms-abi Register volatility and preservation](https://learn.microsoft.com/en-us/cpp/build/x64-software-conventions?view=msvc-170#register-volatility-and-preservation)
  * <https://wiki.osdev.org/Calling_Conventions>
- Other
  * [Compiler Explorer](https://godbolt.org/z/bqsWavEGb)
