## bash
$! pid of just started process
$$ 当前shell的pid，但是对subshell的情况下，$$不会更新。
$BASHPID bash中可以获取当前shell进程的pid, 子shell的情况下是子shell的pid


## markdown
<https://www.markdownguide.org/cheat-sheet/>

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
