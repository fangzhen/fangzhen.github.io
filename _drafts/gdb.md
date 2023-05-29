debuginfo 介绍
https://developers.redhat.com/articles/2022/01/10/gdb-developers-gnu-debugger-tutorial-part-2-all-about-debuginfo#

独立的debuginfo 文件名：
```
readelf -w /usr/bin/python
...
Contents of the .gnu_debuglink section (loaded from /usr/bin/python):

  Separate debug info file: python2.7-2.7.18-4.module+el8.4.0+403+9ae17a31.x86_64.debug
  CRC value: 0x95ccb0d
```

frame: 选择函数栈上某一帧

debug python时需要py-bt等命令，这些命令在python-debuginfo package中。一般gdb会自动加载。
```
(gdb) show auto-load
```

如果没有，可以手动使用source命令加载。
`(gdb) source /usr/lib/debug/usr/lib64/libpython2.7.so.1.0-2.7.18-4.module+el8.4.0+403+9ae17a31.x86_64.debug-gdb.py`



gdb
https://visualgdb.com/gdbreference/commands/set_filename-display
https://darkdust.net/files/GDB%20Cheat%20Sheet.pdf


sudo dnf --enablerepo=fedora-debuginfo install -y kernel-debuginfo


## gdb
see the call stack before main on Linux
(gdb) set backtrace past-main on

backtrace 里source file文件名的显示
set filename-display relative / absolute / basename
relative 是指相对编译目录的地址，默认值。

## misc
* cross-compile glibc

    https://stackoverflow.com/questions/8004241/how-to-compile-glibc-32bit-on-an-x86-64-machine

    ```
    # build i686
    $ ../../src/glibc-2.6/configure --prefix=$HOME/glibc \
         --host=i686-linux-gnu \
         --build=i686-linux-gnu \
         CC="gcc -m32" CXX="g++ -m32" \
         CFLAGS="-O2 -march=i686" \
         CXXFLAGS="-O2 -march=i686"
    ```

    ```
    # build x86_64
    ../../src/glibc-2.6/configure --prefix=$HOME/glibc
    ```

* Get expanded macro for kernel

    ```
    https://lists.kernelnewbies.org/pipermail/kernelnewbies/2015-October/015234.html

    You may want to try following. That will expand all the macros in
    kernel/cpu.c file.

    # make kernel/cpu.i


    You may try with your required files.
    ```
    or use `save-temps=obj`
    https://stackoverflow.com/questions/23407635/append-compile-flags-to-cflags-and-cxxflags-while-configuration-make/23407800
    https://stackoverflow.com/questions/56429389/expand-macros-of-a-single-file-when-compiling-linux-kernel

    glibc:

    ```
    rm io/open.o
    make sysdep-CFLAGS='-save-temps=obj'
    ```


## Debug UEFI application with qemu
基本思路： qemu支持`-gdb`参数启动gdb server。通过gdb或lldb可以远程调试。

可参考：
<https://wiki.osdev.org/Debugging_UEFI_applications_with_GDB>
<https://github.com/tianocore/tianocore.github.io/wiki/How-to-debug-OVMF-with-QEMU-using-GDB>
