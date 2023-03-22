---
layout: post
title: Rust 编写 UEFI 应用
tags: rust uefi
date: 2021-05-13
update: 2023-03-22
---

BIOS和UEFI是两种不同的固件标准，在x86/x86_64架构下，机器上电后需要先进入BIOS或UEFI，才能引导进操作系统。

本文对UEFI标准做个简单概述，并给出Rust下开发UEFI应用的说明。本文对应的具体代码见timetomb。

## UEFI
本文当前版本参考的[UEFI 标准](https://uefi.org/specifications) [2.10版本](https://uefi.org/specs/UEFI/2.10/)。
之前或之后版本大概率对本文内容没有影响。

本节对我们要用到的UEFI 标准内容和API做个简述。

### 概述
UEFI标准的目的是为不同架构/平台与OS之间提供一层抽象。让OS loader等避免深入到各种不同的硬件细节中。

UEFI的Boot Manger读取NVRAM变量来自动加载和执行UEFI image。通过写入NVRAM变量，可以控制系统启动条目，启动文件等。

UEFI Firmware之上运行的程序为UEFI image。其二进制格式为PE32+，但是header signature有修改。
UEFI image可以分为不同类型，包括UEFI application，UEFI boot service driver和UEFI runtime driver。主要是加载的内存类型以及运行退出后的处理等有区别。
UEFI OS loader是一种UEFI application，只是它实现上一般从UEFI firmware中获取控制权后不在返回。UEFI firmware对此并没有特殊处理。

UEFI firmware为UEFI image 提供了两类service：boot service和runtime service。UEFI image通过调用这些API可以标准化的使用firmware提供的功能。
顾名思义，runtime service在OS 运行期间还能调用，而boot service只能在boot期间调用(在调用ExitBootService之前)。

我们知道在普通操作系统的用户空间开发的应用，操作系统会给进程提供统一的运行环境，例如提供虚拟内存，处于ring 3特权级，开发者不需要关系这些底层细节。
在UEFI环境下，类似的也需要有个确定的执行环境配置。以下是x86_64下运行环境的一些说明，具体请参考spec。
- CPU处于uniprocessor模式。（UEFI spec引用的是2009版的Intel sdm第三卷8.4章的内容，笔者没找到这个版本的sdm。应该类似2016版本中的BSP。例如处于ring 0特权级）
- CPU 处于long mode；开启分页，但是虚拟地址和物理地址相同；开启中断

UEFI 规范也定义了在不同CPU架构下的calling convention。我们本文中不需要处理calling convention的细节，因为rust在编译时会帮我们处理。

### Entry Point
```
typedef
EFI_STATUS
(EFIAPI *EFI_IMAGE_ENTRY_POINT) (
  IN EFI_HANDLE                  ImageHandle,
  IN EFI_SYSTEM_TABLE            *SystemTable
  );
```
UEFI image的入口函数如上，Firmware加载UEFI image的时候会把两个参数传给该入口函数。
```
ImageHandle: firmware给当前UEFI image分配的handle
SystemTable: 指向EFI system table的指针。通过EFI system table可以访问UEFI firmware提供的各种服务(API)。
```
细节请参考spec。

### 内存相关函数
BootService中内存管理的API主要有以下几个：
```
AllocatePages: Allocates pages of a particular type.
FreePages: Frees allocated pages.
AllocatePool: Allocates a pool of a particular type
FreePool: Frees allocated pool
GetMemoryMap: Returns the current boot services memory map and memory map key.
```

应当注意，在UEFI image里显式分配的内存应该显式释放掉，UEFI image退出并不会像操作系统的进程退出一样自动回收内存。

UEFI会把内存分成不同的类型来管理，如`EfiBootServicesCode`，`EfiBootServicesData`。`EfiConventionalMemory`表示未分配的内存。

具体参数，用法等请参考spec的'Services - Boot Service' 章节。

> Note:
>
> **`GetMemoryMap`**获取当前的memory map。类似BIOS下的[e820](https://en.wikipedia.org/wiki/E820)。例如：
> ```
> Type: EfiConventionalMemory PhysicalStart: 0x0 VirtualStart: 0x0 Pages: 135 Attribute: 15 Address: 0x6742018
> Type: EfiBootServicesData PhysicalStart: 0x87000 VirtualStart: 0x0 Pages: 1 Attribute: 15 Address: 0x6742048
> Type: EfiConventionalMemory PhysicalStart: 0x88000 VirtualStart: 0x0 Pages: 24 Attribute: 15 Address: 0x6742078
> Type: EfiConventionalMemory PhysicalStart: 0x100000 VirtualStart: 0x0 Pages: 1792 Attribute: 15 Address: 0x67420a8
> Type: EfiACPIMemoryNVS PhysicalStart: 0x800000 VirtualStart: 0x0 Pages: 8 Attribute: 15 Address: 0x67420d8
> Type: EfiConventionalMemory PhysicalStart: 0x808000 VirtualStart: 0x0 Pages: 3 Attribute: 15 Address: 0x6742108
> Type: EfiACPIMemoryNVS PhysicalStart: 0x80b000 VirtualStart: 0x0 Pages: 1 Attribute: 15 Address: 0x6742138
> Type: EfiConventionalMemory PhysicalStart: 0x80c000 VirtualStart: 0x0 Pages: 4 Attribute: 15 Address: 0x6742168
> ...
> ```
> 应当注意，通过`AllocatePool`等分配或释放内存有可能造成memory map的变化。
>
> 函数调用，局部变量分配等栈上的内存使用应该不会造成memory map 变化。因为栈使用了EfiBootServicesData的内存，最小128k。x86_64架构下上栈向下生长，但[局部变量的顺序可能被编译器调整](https://stackoverflow.com/questions/54395558/why-do-subsequent-rust-variables-increment-the-stack-pointer-instead-of-decremen)。


> **`AllocatePool`**最后一个参数是二级指针`void **buffer`，指向分配的内存地址。原因是需要在`*buffer`中存储分配的内存地址，需要传指向`*buffer`的指针。对使用方来说，可以直接当作指针使用，避免类型转换。
>
> **`AllocatePages`** 最后一个参数`EFI_PHYSICAL_ADDRESS *Memory`，没有用二级指针。`EFI_PHYSICAL_ADDRESS`是`unit64`。
>
> 个人认为原因：1. memory不仅作为输出参数，也作为输入参数，语义上更接近于地址数值而不是指针；2. 结果 *memory一般不会直接作为指针使用，通过allocate page多半是要自己处理分配到的page，直接使用应该直接用allocate_pool了。

## Rust 实现说明
UEFI环境和[上一篇](./rust-baremetal.html)中的纯baremetal编程是有区别的。UEFI本身已经提供了一个运行环境和API。
Rust当前已经支持uefi platform，对应x86_64的target triple为`x86_64-unknown-uefi`。

### FFI
在Rust里调用UEFI firmware提供的服务或者firmware 调用image 的entry point，都需要使用Rst的FFI。

要调用firmware提供的服务，需要根据uefi spec的定义，把用到的数据类型和服务用rust struct表示出来。为了简单，我们对uefi spec做尽量少的封装，而且只封装用得到的部分。[uefi-rs](https://github.com/rust-osdev/uefi-rs)提供了比较完善的rust对uefi的封装。

以BootService为例，spec里定义的struct类型如下
```
#define EFI_BOOT_SERVICES_SIGNATURE 0x56524553544f4f42
#define EFI_BOOT_SERVICES_REVISION EFI_SPECIFICATION_VERSION

typedef struct {
  EFI_TABLE_HEADER     Hdr;

  //
  // Task Priority Services
  //
  EFI_RAISE_TPL        RaiseTPL;       // EFI 1.0+
  EFI_RESTORE_TPL      RestoreTPL;     // EFI 1.0+

    //
    // Memory Services
    //
    EFI_ALLOCATE_PAGES   AllocatePages;  // EFI 1.0+
    EFI_FREE_PAGES       FreePages;      // EFI 1.0+
    EFI_GET_MEMORY_MAP   GetMemoryMap;   // EFI 1.0+
...

typedef
EFI_STATUS
(EFIAPI \*EFI_GET_MEMORY_MAP) (
   IN OUT UINTN                  *MemoryMapSize,
   OUT EFI_MEMORY_DESCRIPTOR     *MemoryMap,
   OUT UINTN                     *MapKey,
   OUT UINTN                     *DescriptorSize,
   OUT UINT32                    *DescriptorVersion
  );
```
改写为rust struct主要遵循了下面几个规则：
- 结构体用`#[repr(C)]`修饰，以使用C内存布局。
- 为简化使用，所有字段都是public的。
- 不需要的字段不能直接忽略，但需要占位，以保证后续的字段有正确的偏移。
- 函数指针都用`unsafe extern "efiapi"`修饰。
- 函数参数：IN对应immutable的数据类型, `OUT`对应mutable的数据类型;
  根据实际情况选择对应的rust类型。对于指针，根据使用便利选择引用或者裸指针都可以。

例如，上面`BootService`对应的部分rust代码如下：
```
#[repr(C)]
pub struct BootServices {
    pub header: Header,

    // Task Priority services
    pub raise_tpl: Ignore,
    pub restore_tpl: Ignore,

    // Memory allocation functions
    pub allocate_pages: unsafe extern "efiapi" fn(
        alloc_ty: u32,
        mem_ty: MemoryType,
        count: usize,
        addr: &mut u64,
    ) -> Status,
    pub free_pages: unsafe extern "efiapi" fn(addr: u64, pages: usize) -> Status,
    pub get_memory_map: unsafe extern "efiapi" fn(
        size: &mut usize,
        map: *mut MemoryDescriptor,
        key: &mut MemoryMapKey,
        desc_size: &mut usize,
        desc_version: &mut u32,
    ) -> Status,
...
```

### Log to stdout
EFI system table中提供了向Console输出的能力。通过实现`fmt::Write`和`log::Log` trait达到通过日志api方便地输出内容到Console的效果。一个简单的实现请见`logger.rs`。

## 结语
本文的内容只是一个最简单的UEFI Application，获取UEFI下的memory map并输出到控制台。
有了这个基础，我们就可以考虑如何从UEFI转到操作系统Kernel了。

## Reference
* <https://en.wikipedia.org/wiki/UEFI>
* 开源UEFI固件实现：[tianocore/edk2](https://github.com/tianocore/edk2)
* [coreboot](https://doc.coreboot.org/)是另外一个开源固件项目。
* x86_64架构从上电到进入操作系统较详细的流程可参考（BIOS）：
  <https://0xax.gitbooks.io/linux-insides/content/Booting/linux-bootstrap-1.html>
* [从零开始UEFI裸机编程](https://kagurazakakotori.github.io/ubmp-cn/part1/basics/program.html)，
  比较详细地讲解了怎么阅读和使用uefi标准文档的API，并通过一个UEFI应用来介绍了很多常用功能。
* <https://blog.fpmurphy.com/2012/08/uefi-memory-v-e820-memory.html>
