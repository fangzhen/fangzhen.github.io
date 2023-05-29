---
layout: post
title: 程序构建与执行 - 链接，重定位，地址无关代码
tags: ELF relocation ld PIC PIE
date: 2023-05-05
update: 2023-05-31
---
本文主要基于GCC编译器和Linux下ELF文件格式，讨论程序的构建和执行。

## 程序构建与执行
GCC把C/C++程序构建过程分成四个阶段：预处理，编译，汇编，链接。可以用不同参数控制构建过程(`-S, -E, -c`)。本文不涉及GCC构建的具体细节，下文中我们粗略把整个构建过程分为两个阶段：编译和链接。

1. 编译
   编译大概对应上述的预处理，编译，汇编阶段，编译的结果是目标文件（object file）。
   目标文件跟单个源文件是对应的，其中没有跨文件的信息。
2. 链接
   链接的过程是把多个目标文件和依赖库组合生成库或可执行文件的过程。链接时需要处理外部变量/函数的引用，进行地址空间规划等。

操作系统执行程序时，需要把可执行文件先加载到内存中，再执行程序的指令。

在现代Linux系统上，上述目标文件，库或可执行文件都采用ELF文件格式。

本文讨论的构建与执行过程中的主题主要包括：
### 静态/动态链接
程序实现时除了本身的业务逻辑，一般都会使用到外部库，比如，调用`printf`函数就需要libc库。
所以在链接时，除了链接目标文件，还需要指定库文件。

静态链接会把所有目标文件和静态链接库整合到目的文件中。
静态链接的可执行文件中，全局变量/函数等的**相对位置**都是确定的，因为不同的段在可执行文件中的位置已经排列好；运行时也不依赖外部库。
静态链接库就是把目标文件的简单打包。

libc等库会被很多linux上的程序使用，如果每个可执行文件都包含libc的副本，会造成磁盘和内存的浪费。而且libc库可能会有bug fix，如果静态链接的程序要修复对应的bug，就需要重新链接。因此有了动态链接。
动态链接时，不会把依赖的动态链接库包含在目的文件中。当操作系统加载时，才会按需把动态链接库加载到内存中。当然，动态链接库也可以依赖其他库。

### 重定位(Relocation)
目标文件 - 动态链接库/可执行文件 - 加载运行
在这个过程中，目标文件对全局符号的地址信息是所知最少的，它只有自己单个目标文件的信息。当访问不确定运行时地址的符号时，目标文件中需要保留地址占位以及替换策略，在链接和加载运行时替换成正确的地址。
ELF文件中的重定位用来实现这个目标。
简单来说，每个重定位项指出了如何把某个位置的数据替换为正确的实际值。而这个替换发生在链接或加载时。下面的地址无关代码的实现也依赖重定位。

### 地址无关代码
上面我们提到，动态链接库在程序加载时动态加载到内存中，无法在链接时确定加载的内存位置，**包括相对地址(相对程序计数器PC)和绝对地址(虚拟地址)**。
当访问全局符号时，需要进行符号解析。链接器允许多个模块/动态链接库中定义同名的符号，在链接时根据一定的规则来确定实际使用的符号。

所以当访问动态链接库的函数时，需要生成地址无关的代码，在程序/动态链接库加载时，才把实际的内存地址填充进去。

linux的ASLR需要pie的可执行文件，否则无法进行地址随机化。

| 访问全局符号的入口   | 动态链接全局函数                                                                                                             | 全局变量或静态链接全局函数                    | 参数             |
|----------------------|------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|------------------|
| 动态链接库           | 链接时不确定访问的符号来自哪，相对地址和绝对地址都不确定。实际地址为运行时符号解析后对应的函数在内存的加载地址               | 实际地址为运行时全局变量在.data或.bss段的地址 | `-fPIC  -shared` |
| 地址无关可执行文件   | 链接时可以完成符号解析，但动态链接库的加载地址不确定，相对地址和绝对地址都不确定；静态链接部分的相对地址确定，绝对地址不确定 | 全局变量在.data或.bss段，相对地址确定         | `-fPIE -pie`     |
| 非地址无关可执行文件 | 链接时完成符号解析，动态链接库的加载地址不确定，相对地址和绝对地址都不确定；静态链接部分都确定                               | .data或.bss段，相对地址和绝对地址都确定       | `-no-pie`        |

加载时可以动态修改数据段的内容，但代码段不能修改。链接时都可以修改。
地址无关代码目标就是避免加载时需要修改代码段内容，还需要能满足上面动态链接库和可执行文件的动态链接需要。

技术手段：
以指令`int a = global_b`为例：
1. 相对寻址：如果能在指令中以某种方式使用符号相对PC的地址，那么如果相对地址在链接时可确定，在生成目标文件的机器码时，生成相对寻址的机器码，在链接时修改。
   相对寻址不同指令集下的实现方案有很大区别。
   生成的汇编指令类似`mov m64, %rax`。m64对应global_b的内存地址。
1. GOT。如果在链接时相对地址也不确定，那么需要使用一个相对地址确定的中间变量中转。生成类似如下两条指令：`mov b_got %rbx; mov (%rbx) %rax`
   其中`b_got`为.got段分配的一块内存，（动态链接库或可执行文件有各自的.got段，不会合并）。在链接时第一条指令b_got替换为相对地址，b_got指向的内存位置在运行时被替换为实际的内存地址。

编译目标文件时，根据链接目标，需要生成满足要求的目标文件代码：
都不确定：GOT
相对地址确定：GOT/相对寻址
都确定：GOT/相对寻址/绝对寻址

替换内存地址是通过重定位来实现。

## 重定位示例和分析
没有特别说明，都是在x86_64环境下的测试结果。
```
$ gcc -v
...
Target: x86_64-pc-linux-gnu
gcc version 12.2.1 20230201 (GCC)
```
### 目标文件 & 静态链接库
```
// bar.c
int var_b = 0xabcd;
void foo() {}
void bar(){
  foo();
  int a = var_b;
}
```
```
$ gcc -c bar.c -o bar.o
$ file bar.o
bar.o: ELF 64-bit LSB relocatable, x86-64, version 1 (SYSV), not stripped

# linux下静态链接库就是把目标文件打包，没有特别的处理
$ ar rcs bar.a bar.o
$ file bar.a
bar.a: current ar archive
```

使用`objdump`或`readelf`可以看到relocation表的信息。可以看到`bar.o`的`.rela.text`表有两项，分别对应`foo`函数和`var_b`变量。
```
$ objdump -r bar.o

bar.o:     file format elf64-x86-64

RELOCATION RECORDS FOR [.text]:
OFFSET           TYPE              VALUE
0000000000000015 R_X86_64_PLT32    foo-0x0000000000000004
000000000000001b R_X86_64_PC32     var_b-0x0000000000000004
```
`objdump -Dr bar.o`反编译bar.o，相关部分如下。objdump也帮我们在反汇编的输出里带了重定位的信息。
后文我们都采用反汇编的输出。
```
Disassembly of section .text:

0000000000000000 <foo>:
   0:   55                      push   %rbp
   1:   48 89 e5                mov    %rsp,%rbp
   4:   90                      nop
   5:   5d                      pop    %rbp
   6:   c3                      ret

0000000000000007 <bar>:
   7:   55                      push   %rbp
   8:   48 89 e5                mov    %rsp,%rbp
   b:   48 83 ec 10             sub    $0x10,%rsp
   f:   b8 00 00 00 00          mov    $0x0,%eax
  14:   e8 00 00 00 00          call   19 <bar+0x12>
                        15: R_X86_64_PLT32      foo-0x4
  19:   8b 05 00 00 00 00       mov    0x0(%rip),%eax        # 1f <bar+0x18>
                        1b: R_X86_64_PC32       var_b-0x4
  1f:   89 45 fc                mov    %eax,-0x4(%rbp)
  22:   90                      nop
  23:   c9                      leave
  24:   c3                      ret
```

### 静态链接 & nopie
```
// test.c
int a = 10;
extern int var_b;
void bar();

int _start() {
   bar();
   int c = var_b;
}
```
```
$ gcc -nostdlib -static test.c bar.o -o test.nopie.static
$ file test.nopie.static
test.nopie.static: ELF 64-bit LSB executable, x86-64, version 1 (GNU/Linux), statically linked, BuildID[sha1]=556eca7cbd885e7107379217e2d9ec9c11fd7ada, for GNU/Linux 4.4.0, not stripped
```
```
$ objdump -Dr test.nopie.static
0000000000401000 <_start>:
  401000:       55                      push   %rbp
  401001:       48 89 e5                mov    %rsp,%rbp
  401004:       48 83 ec 10             sub    $0x10,%rsp
  401008:       b8 00 00 00 00          mov    $0x0,%eax
  40100d:       e8 13 00 00 00          call   401025 <bar>
  401012:       8b 05 ec 1f 00 00       mov    0x1fec(%rip),%eax        # 403004 <var_b>
  401018:       89 45 fc                mov    %eax,-0x4(%rbp)
  40101b:       90                      nop
  40101c:       c9                      leave
  40101d:       c3                      ret
...
000000000040101e <foo>:
  40101e:       55                      push   %rbp
  40101f:       48 89 e5                mov    %rsp,%rbp
  401022:       90                      nop
  401023:       5d                      pop    %rbp
  401024:       c3                      ret

0000000000401025 <bar>:
  401025:       55                      push   %rbp
  401026:       48 89 e5                mov    %rsp,%rbp
  401029:       48 83 ec 10             sub    $0x10,%rsp
  40102d:       b8 00 00 00 00          mov    $0x0,%eax
  401032:       e8 e7 ff ff ff          call   40101e <foo>
  401037:       8b 05 c7 1f 00 00       mov    0x1fc7(%rip),%eax        # 403004 <var_b>
  40103d:       89 45 fc                mov    %eax,-0x4(%rbp)
  401040:       90                      nop
  401041:       c9                      leave
  401042:       c3                      ret

...
Disassembly of section .data:

0000000000403000 <a>:
  403000:       0a 00                   or     (%rax),%al
        ...
0000000000403004 <var_b>:
  403004:       cd ab                   int    $0xab

```
从上面的反编译输出可以看出：
1. 静态链接：`bar.c`的编译后代码也直接包含在了二进制文件中;
2. 函数调用：`_start -> bar`, `bar -> foo`的目标地址修改成了对应的函数地址（相对地址，指令为`E8`）;
3. 全局数据 `var_b`在`.data` section，test.c和bar.c中对`var_b`的访问修改成了正确的地址。

上面2, 3条是链接时链接器对relocation的处理结果。
回顾一下，重定位做的事情就是根据重定位方案计算出实际地址，并把被替换位置的数据替换为该值。

#### 函数调用的relocation
以`bar.c`中`bar`对`foo`的调用为例，`objdump`的输出已经是解析之后的结果。主要包含几个信息：

1. r_offset: 要被替换的代码位置`P'`：offset为0x15的位置。可以看到在目标文件中这个位置都是0，只是做占位的；
2. r_info: 被调用的函数`foo`，(通过符号表index)和重定位类型`R_X86_64_PLT32`；
3. Addend: -4

不同的重定位类型计算目标值的方法不同。`R_X86_64_PLT32`的计算方法为`L+A-P`，其中：
* L: `foo`在目的文件中的地址
* A: Addend
* P: `P'`在目的文件中的位置
计算结果： `40101e + (-4)  - 401033 = -19 = ffffffe7`，和指令`401032:       e8 e7 ff ff ff          call   40101e <foo>`符合。

> Note: 关于L的值：
> 说明：按spec的说法应该是要给`foo`在目标文件中创建一个plt entry，由该plt entry跳转到`foo`，L为该plt entry的地址；实际上在当前情况下，`foo`是静态链接进来的，相对地址确定，plt entry没有必要，所以直接是`foo`的地址

> Note: addend为什么是-4以及为什么需要addend
> call 指令的相对偏移值是相对下一个指令地址的。而P到下个指令地址的偏移是4，所以需要`-4`修正才能跳转到正确的地址。而这个语义在编译器在生成目标文件时是知道的，链接器在做relocation是不需要了解，之需要根据relocation的要求-4即可。

#### 访问全局变量的relocation
`R_X86_64_PC32`类型的计算方法为`S+A-P`，其中A和P跟上面同样的意义，S指目标变量对应的symbol表中的对应值(即var_b的地址)。
计算结果`403004 + (-4) - 401039 = 1fc7`，与反汇编结果符合。

### 动态链接库
```
$ gcc -c -fPIC bar.c -o bar.pic.o
$ file bar.pic.o
bar.pic.o: ELF 64-bit LSB relocatable, x86-64, version 1 (SYSV), not stripped
$ gcc -shared bar.pic.o -o bar.so
$ file bar.so
bar.so: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, BuildID[sha1]=1f7d502d82fe47553b0d328eebfe5c813ca234fb, not stripped
```
```
$ objdump -Dr bar.pic.o
0000000000000007 <bar>:
   7:   55                      push   %rbp
   8:   48 89 e5                mov    %rsp,%rbp
   b:   48 83 ec 10             sub    $0x10,%rsp
   f:   b8 00 00 00 00          mov    $0x0,%eax
  14:   e8 00 00 00 00          call   19 <bar+0x12>
                        15: R_X86_64_PLT32      foo-0x4
  19:   48 8b 05 00 00 00 00    mov    0x0(%rip),%rax        # 20 <bar+0x19>
                        1c: R_X86_64_REX_GOTPCRELX      var_b-0x4
```
`bar.pic.o`中分别对`foo`和`var_b`的访问生成了两个relocation项。把`bar.pic.o`链接成`bar.so`时，对两个relocation进行处理。
```
$ objdump -Dr bar.so
Disassembly of section .plt:

0000000000001020 <foo@plt-0x10>:
    1020:       ff 35 ca 2f 00 00       push   0x2fca(%rip)        # 3ff0 <_GLOBAL_OFFSET_TABLE_+0x8>
    1026:       ff 25 cc 2f 00 00       jmp    *0x2fcc(%rip)        # 3ff8 <_GLOBAL_OFFSET_TABLE_+0x10>
    102c:       0f 1f 40 00             nopl   0x0(%rax)

0000000000001030 <foo@plt>:
    1030:       ff 25 ca 2f 00 00       jmp    *0x2fca(%rip)        # 4000 <foo@@Base+0x2ef7>
    1036:       68 00 00 00 00          push   $0x0
    103b:       e9 e0 ff ff ff          jmp    1020 <_init+0x20>

Disassembly of section .text:

0000000000001040 <foo-0xc9>:
    1040:       48 8d 3d d1 2f 00 00    lea    0x2fd1(%rip),%rdi        # 4018 <__TMC_END__>
...
0000000000001109 <foo>:
    1109:       55                      push   %rbp
    110a:       48 89 e5                mov    %rsp,%rbp
    110d:       90                      nop
    110e:       5d                      pop    %rbp
    110f:       c3                      ret

0000000000001110 <bar>:
    1110:       55                      push   %rbp
    1111:       48 89 e5                mov    %rsp,%rbp
    1114:       48 83 ec 10             sub    $0x10,%rsp
    1118:       b8 00 00 00 00          mov    $0x0,%eax
    111d:       e8 0e ff ff ff          call   1030 <foo@plt>
    1122:       48 8b 05 97 2e 00 00    mov    0x2e97(%rip),%rax        # 3fc0 <var_b@@Base-0x50>
    1129:       8b 00                   mov    (%rax),%eax
    112b:       89 45 fc                mov    %eax,-0x4(%rbp)
    112e:       90                      nop
    112f:       c9                      leave
    1130:       c3                      ret
...
Disassembly of section .got:

0000000000003fc0 <.got>:
        ...

Disassembly of section .got.plt:

0000000000003fe8 <_GLOBAL_OFFSET_TABLE_>:
    3fe8:       00 3e                   add    %bh,(%rsi)
        ...
    3ffe:       00 00                   add    %al,(%rax)
    4000:       36 10 00                ss adc %al,(%rax)
...
Disassembly of section .data:
        ...

0000000000004010 <var_b>:
    4010:       cd ab                   int    $0xab

```

**链接时对`bar`调用`foo`的重定位计算：**，类型跟上面一样`R_X86_64_PLT32`，计算结果：
`L+A-P = 1030 + (-4) - 111e = -f2 = ffffff0e`。
上面我们提到过，动态链接库中访问全局函数时，被访问的`foo`的绝对地址和相对地址都不确定，因此这里L的值是`.plt section`foo函数对应的地址`1030`。
`    1030:       ff 25 ca 2f 00 00       jmp    *0x2fca(%rip)        # 4000 <foo@@Base+0x2ef7>`
`.plt`中代码跳转到地址`0x4000`的内容对应的地址（注意跳转指令本身用的是相对地址）。

**加载时函数的重定位计算：**
`bar.so`中包含一条relocation信息：
```
000000004000  000600000007 R_X86_64_JUMP_SLO 0000000000001109 foo + 0
```
`R_X86_64_JUMP_SLOT`把地址`0x4000`的值替换成`foo`函数的实际地址。

在程序加载`bar.so`时动态链接后，上述relocation被处理后替换成`foo`被加载在内存的实际地址。综合起来，就相当于先跳转到plt，再跳转到`foo`。而`foo`的地址是程序运行时动态替换到`.got.plt`中的。

**链接时对全局变量`var_b`的重定位计算：**
类型`R_X86_64_REX_GOTPCRELX`对应的计算方法为：`G + GOT + A - P`，其中
* G: 对应变量在.got中的偏移；
* GOT: .got 节的地址
依赖bar.so的不同可执行文件加载时，bar.so的text节在内存中只存在一份，但是在不同进程中对应的虚拟地址是不同的。但是每个进程都的data节(运行时应该属于某个segment)不是共享的。
对于`R_X86_64_REX_GOTPCRELX`，链接器需要在bar.so的.got表中增加一项对应var_b，其值在加载时设置为`var_b`的实际内存地址，

计算结果 `0 + 3fc0 + (-4) - 1125 = 2e97`

> bar.so 在不同进程加载时，地址1122的指令已经不会再relocation了，所以.got和.text的相对地址也是固定的，然后加载时的.got第一个entry要改成var_b的实际地址（绝对地址）。
> executable + shared library，实际内存布局什么样的？data合并成一个，got不合并；所以var_b的偏移不确定，.got的偏移确定

**程序加载时，.got的之怎么替换成var_b的地址**：通过下面的relocation
```
Relocation section '.rela.dyn' at offset 0x4a0 contains 8 entries:
  Offset          Info           Type           Sym. Value    Sym. Name + Addend
000000003fc0  000700000006 R_X86_64_GLOB_DAT 0000000000004010 var_b + 0
```
类型`R_X86_64_GLOB_DAT`，计算公式为`S`，即对应的symbol的值。也就是把地址 `3fc0`替换成`var_b`的值。
综上，指令地址1122和1129两条指令总体效果就是通过两次访存把`var_b`的值存到`eax`寄存器。

## 地址无关代码示例和分析
前面对动态链接库的分析已经看到在x86_64下地址无关代码的实现方式。下面给出一些示例对上文地址无关代码进行一些具象的说明。

### 地址无关可执行文件(PIE)
上文已经对动态链接库中的地址无关代码的重定位进行了分析，本节看一下PIE在执行时的实际现象：
```
//main.c
#include<stdio.h>

int main() {
        printf("%p\n", main);
}
```

no-pie链接生成的二进制加载到固定的内存地址，而`-pie`生成的二进制每次加载的地址都不一样。ASLR需要PIE的可执行文件，否则无法进行地址随机化。
```
$ gcc -no-pie main.c -o main.no-pie
$ readelf -h main.no-pie  | grep Type
  Type:                              EXEC (Executable file)
$ ./main.no-pie
0x401126
$ ./main.no-pie
0x401126

$ gcc -pie -fPIE main.c -o main.pie
readelf -h main.pie  | grep Type
  Type:                              DYN (Position-Independent Executable file)
$ ./main.pie
0x559f078c4139
$ ./main.pie
0x55ce3e96a139
```

### 符号解析
本节不进入符号解析的细节，通过符号解析的一个简单示例，说明动态链接库(`-fPIC`)和可执行文件(`-fPIE`)访问全局符号时的差别。

链接时，不同目标文件或共享库中可能存在相同符号的多重定义。

回到上面的bar.c，它定义了`var_b`：
```
// bar.c
int var_b = 0xabcd;
void foo() {}
int bar(){
  foo();
  return var_b;
}

//main.c
#include<stdio.h>
int var_b = 0x100;
int bar();

int main() {
        printf("%p\n", bar());
}
```

如果直接生成可执行文件，会报错`var_b`重定义。
```
$ gcc test.c bar.c -o test.lderror
/usr/bin/ld: /tmp/cc80ua1K.o:(.data+0x0): multiple definition of `var_b'; /tmp/ccybOQy8.o:(.data+0x0): first defined here
collect2: error: ld returned 1 exit status
```
但是如果把bar.c先编译成动态链接库，程序可以正常执行，而且var_b的值是test.c中定义的0x100：

```
$ gcc -fPIC -shared bar.c -o bar.so
$ gcc test.c bar.so -o test
$ LD_LIBRARY_PATH=. ./test
0x100
```

通过生成的目标文件可以看出来PIC和PIE的差别。在`-fPIC`的情况下，**链接生成bar.so时**，bar中访问var_b时，还不能确定var_b的相对偏移(因为实际的var_b可能不是bar.c中定义的var_b)，所以生成的是`R_X86_64_REX_GOTPCRELX`类型的重定位，上文已经分析过，这种类型会在GOT section中生成一项，在程序运行时把实际的地址填进去。
而PIE的情况下，**链接test.lderror时**，链接bar.o能确定要访问的var_b在链接时可以确定（不确定会报错，如上例子），生成`R_X86_64_PC32`类型的relocation。
```
$ gcc -fPIC bar.c -c -o bar.o.pic
$ objdump -Dr bar.o.pic
  10:   e8 00 00 00 00          call   15 <bar+0xe>
                        11: R_X86_64_PLT32      foo-0x4
  15:   48 8b 05 00 00 00 00    mov    0x0(%rip),%rax        # 1c <bar+0x15>
                        18: R_X86_64_REX_GOTPCRELX      var_b-0x4

$ gcc -fPIE bar.c -c -o bar.o.pie
$ objdump -Dr bar.o.pic
  10:   e8 00 00 00 00          call   15 <bar+0xe>
                        11: R_X86_64_PLT32      foo-0x4
  15:   8b 05 00 00 00 00       mov    0x0(%rip),%eax        # 1b <bar+0x14>
                        17: R_X86_64_PC32       var_b-0x4
```

[why-i-cannot-compile-with-fpie-but-can-with-fpic](https://stackoverflow.com/a/47696436) 除了上面的区别，该链接中提到对于thread local变量的访问也有区别。


### 绝对地址 vs. 相对地址 vs. GOT
```
// test2.s
        .text
        .globl _start
_start:
        // 1. GOT
        movq  var_a@GOTPCREL(%rip), %rax
        movl (%rax), %eax
        // 2. address relative to rip
        movl  var_a(%rip), %eax
        // 3. absolute address
        movl  var_a, %eax

        .data
        .globl var_a
var_a:
        .long   10
```

```
$ gcc -c test2.s
$ objdump -Dr test2.o
...
0000000000000000 <_start>:
   0:   48 8b 05 00 00 00 00    mov    0x0(%rip),%rax        # 7 <_start+0x7>
                        3: R_X86_64_REX_GOTPCRELX       var_a-0x4
   7:   8b 00                   mov    (%rax),%eax
   9:   8b 05 00 00 00 00       mov    0x0(%rip),%eax        # f <_start+0xf>
                        b: R_X86_64_PC32        var_a-0x4
   f:   8b 04 25 00 00 00 00    mov    0x0,%eax
                        12: R_X86_64_32S        var_a

Disassembly of section .data:
0000000000000000 <var_a>:
   0:   0a 00                   or     (%rax),%al
```
上面汇编代码的三组`mov`指令都是把var_a变量的存到eax寄存器，但分别采用了GOT，相对rip地址和绝对地址三种方式来引用`var_a`。
可以看到在生成的目标文件中，对应三种relocation类型：
* 第一个生成的是`R_X86_64_GOTPCRELX`，在上文动态链接库的解析中已经看到过，会通过GOT添加条目来间接引用`var_a`，需要两条指令；
* 第二个生成的是`R_X86_64_PC32`类型，使用相对PC的地址替换，需要一条指令；
* 第三个生成的是`R_X86_64_32S`类型，使用对应绝对地址的值替换，需要一条指令

**可以正常链接为非地址无关的可执行文件，**第三组指令中的地址已经替换成了`var_a`的绝对地址。前两组指令也都完成了relocation指定的替换。
```
$ gcc -nostdlib -no-pie test2.o -o test2.nopie
$ objdump -Dr test2.nopie
0000000000401000 <_start>:
  401000:       48 c7 c0 00 20 40 00    mov    $0x402000,%rax
  401007:       8b 00                   mov    (%rax),%eax
  401009:       8b 05 f1 0f 00 00       mov    0xff1(%rip),%eax        # 402000 <var_a>
  40100f:       8b 04 25 00 20 40 00    mov    0x402000,%eax

Disassembly of section .data:

0000000000402000 <var_a>:
  402000:       0a 00                   or     (%rax),%al
```

**不能链接为地址无关的可执行文件，因为第三组mov指令引用了绝对地址**：
```
$ gcc -nostdlib -pie test2.o
/usr/bin/ld: test2.o: relocation R_X86_64_32S against symbol `var_a' can not be used when making a PIE object; recompile with -fPIE
/usr/bin/ld: failed to set dynamic section sizes: bad value
collect2: error: ld returned 1 exit status
```

**删除掉第三组指令，不能链接为动态链接库，因为第二组mov指令无法做到symbol interpose**：
```
$ gcc -shared test2.s -o test2.so
/usr/bin/ld: /tmp/ccM8fJFB.o: warning: relocation against `var_a' in read-only section `.text'
/usr/bin/ld: /tmp/ccM8fJFB.o: relocation R_X86_64_PC32 against symbol `var_a' can not be used when making a shared object; recompile with -fPIC
/usr/bin/ld: final link failed: bad value
collect2: error: ld returned 1 exit status
```

在x86_64架构上，对于gcc的`-fPIC`参数来说，需要生成类似第一组的代码；对于`-fPIE`，理论上可以生成第一组或第二组代码，但是性能上当然第二组更好；
对于两个参数都不指定的情况，理论上三组代码都可以，第二组和第三组性能相当，实际会生成第二组。

对于其他架构，编译器可以根据架构的指令集尽量生成最优的代码。例如相对rip寻址是x86_64独有的，x86并不具备，但x86架构支持基址寻址；
而aarch64架构的寻址方式以及指令集设计跟x86又有不同。

## References
* [ELF spec 1.2 (1995)](https://refspecs.linuxfoundation.org/elf/elf.pdf)
* [x86_64 ELF ABI 最新版(1.0, 2023)](https://gitlab.com/x86-psABIs/x86-64-ABI)

* reloction条目的数据结构为：
  ```
  typedef struct {
      Elf32_Addr r_offset;
      Elf32_Word r_info;
      Elf32_Sword r_addend;
  } Elf32_Rela;
  ```
* [ELF 文件结构](http://chuquan.me/2018/05/21/elf-introduce/)的简要说明，同系列文章还涉及到链接，符号解析等。
* Intel SDM V1, chapter 3.7 Oprand Addressing.
  > The following unique combination of address components is also available.

  > **RIP + Displacement** ⎯ In 64-bit mode, RIP-relative addressing uses a signed 32-bit displacement to
  calculate the effective address of the next instruction by sign-extend the 32-bit value and add to the 64-bit
  value in RIP.
* ARM 指令集
  * https://developer.arm.com/documentation/dui0802/a/A64-General-Instructions
  * [ARM64指令简易手册](https://tenloy.github.io/2021/04/17/Arm64-Handbook.html)
* [Anatomy of Linux dynamic libraries](https://developer.ibm.com/tutorials/l-dynamic-libraries/)
* gcc 编译阶段
  * (https://stackoverflow.com/questions/8527743/running-gccs-steps-manually-compiling-assembling-linking)
  * (https://www.linkedin.com/pulse/gcc-four-steps-compilation-alfredo-sampayo)

  ```
  gcc -E  --> Preprocessor, but don't compile
  gcc -S  --> Compile but don't assemble
  gcc -c  --> Preprocess, compile, and assemble, but don't link
  gcc with no switch will link your object files and generate the executable
  ```
* 动态链接转静态链接
  * https://stackoverflow.com/questions/725472/static-link-of-shared-library-function-in-gcc
  * 工具 [statifier](http://statifier.sf.net/) [Ermine](http://magicermine.com/)
* ELF 文件类型: pie的可执行文件和动态链接库的`e_type`都是`ET_DYN`。可参考(https://stackoverflow.com/a/55704865/2705629)
  gcc编译的pie文件会在dynamic section增加PIE的flag，例如，通过`readelf`可以看到。
  ```
  Dynamic section at offset 0x2f20 contains 9 entries:
    Tag        Type                         Name/Value
   ...
   0x000000006ffffffb (FLAGS_1)            Flags: PIE
  ```
* [Shared Library Symbol Conflicts (on Linux)](https://holtstrom.com/michael/blog/post/437/Shared-Library-Symbol-Conflicts-(on-Linux).html)
