

uefi application 是pecoff+格式，linux 代码中直接构建出对应的二进制格式。

linux kernel efi stub 相关的代码在5.7左右有过一次重构，重构后eboot.c的内容都移到了efi/libstub下。而且相关的优化一直在进行。本文参考的代码版本为6.2(tag v6.2)

### uefi image entry - efi_pe_entry
arch/x86/boot/header.S
```
pe_header:
coff_header:
	# Filled in by build.c
	.long	0x0000				# AddressOfEntryPoint
```
`arch/x86/boot/tools/build.c` 中填充实际的地址。该地址是pecoff格式文件的入口地址。EFI_BOOT_SERVICES.LoadImage() 加载UEFI image后会转到该地址继续执行。
build.c中会把该地址设置为efi_pe_entry。
```
	/*
	 * Address of entry point for PE/COFF executable
	 */
	put_unaligned_le32(text_start + efi_pe_entry, &buf[pe_header + 0x28]);
```

efi_pe_entry: drivers/firmware/efi/libstub/x86-stub.c
    efi_stub64_entry: compressed/head_64.S
      efi_main: drivers/firmware/efi/libstub/x86-stub.c
      startup_64: compressed/head_64.S

### efi_stub_entry
efi_stub64_entry 是另一个入口，根据[x86的linux boot protocol](https://www.kernel.org/doc/html/latest/x86/boot.html)，
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

### overview
efi_pe_entry调用efi_stub64_entry之前是传统bootloader做的事情，例如设置boot params
efi_stub_entry 是asm代码，需要注意calling convention。
efi_main 执行efi相关的一些初始化和配置工作。relocate_kernel，setup_graphics 等。
startup_64 最后的boot工作。包括setup gdt, paging(?)等。
  注意这个阶段kernel用到的内存，例如kernel stack, gdt, 页表等都是预先分配在kernel image的。这样使用起来比较方便。
```
# define BOOT_STACK_SIZE	0x4000
#   define BOOT_PGT_SIZE	(19*4096)
```

## Reference:

[Layout of bzImage](https://zhuanlan.zhihu.com/p/73077391)
该文章给出了bzImage的格式，代码来源，以及进入kernel的各种入口，从real mode, BIOS protected mode 到efi。
