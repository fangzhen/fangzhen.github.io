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

