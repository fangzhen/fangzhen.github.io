
reference:

现代PC中，大部分北桥功能继承在CPU中，南桥功能和部分北桥功能继承到了PCH， https://en.wikipedia.org/wiki/Southbridge_(computing)
https://en.wikipedia.org/wiki/Platform_Controller_Hub

5.9, 5.10 in pch datasheet https://www.intel.com/content/dam/www/public/us/en/documents/datasheets/9-series-chipset-pch-datasheet.pdf

中断控制器PIC / APIC https://en.wikipedia.org/wiki/Advanced_Programmable_Interrupt_Controller
功能都继承在PCH中

https://wiki.osdev.org/IOAPIC

intel core cpu datasheet https://www.mouser.com/datasheet/2/612/4th-gen-core-family-desktop-vol-1-datasheet-263629.pdf
APIC信号通过DMI接口跟CPU交互 2.3 & 6.6
