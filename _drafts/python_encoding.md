---
layout: post
title: 编程语言中字符串、编码等
tags: python encoding
date: 2020-11-08
---

理论先行
=========
字符串编码问题的时候，我们需要注意区分几个概念

1. 字符串对象

   编程语言概念里的字符串对象。例如Python中的str/unicode；C中的char*。各种语言中对字符串的操作都是针对字符串对象的。

1. 字符串字面量（String literal）

   字符串字面量在源码文件中表示字符串值。例如Python2中

   ``` py2
   s1 = 'abc\n'    # 字符串，已换行符结尾
   s2 = u'我'      # Unicode字符串，只有一个字符，但是内部表示不只一个字节
   s3 = r'abc\n'   # 字符串，结尾两个字符分别是\和n
   ```

1. 字符串序列化，IO

   字符串对象从文件读出或写入，包括标准输入输出等。

   一般情况下，文件IO可以分为binary模式和text模式。text模式会做一些转化，例如换行符可能根据Linux/Windows平台写出文件时转化成\n或\r\n。
   对于Python来说，以text模式打开文件，read()返回的就是 `str`。
   如果以binary模式打开，read()返回的是字节数组。
   当然写入到文件是同样的规则。

   以text模式输入输出时就有可能涉及到字符串的encode/decode。

1. 运行时字符串在内存中的表示

   例如在C中，就是字节数组并以`\n`结尾；在 Python2 中，也可以认为是字符数组。Python3或者Python2的Unicode的内部表示可能分不同的情况（PEP-393）。
   可以参考下这个问题 https://stackoverflow.com/questions/26079392/how-is-unicode-represented-internally-in-python

   对语言的使用来说，一般情况下不需要关心内部表示。

Python 2 & 3
=============
python 2 & 3 的字符串差别非常大。

* Python 2 中, `str`实际上是以byte序列保存，组成单元是字节。另外类型`bytes` 是 `str`的别名。另外`unicode`类型是Unicode字符串，组成单元是Unicode字符。
* Python 3 中，`str`是Unicode字符串，组成单元是Unicode字符，跟Python 2中`unicode`类似。`bytes`是字节序列，跟Python 2中`str`类似。

PyCon 2012 上一个演讲，对Python2和Python3字符串编码相关讲的比较清楚了 https://nedbatchelder.com/text/unipain.html

Case Study
---------------

### String Literal
```
$ python2
Python 2.7.17 (default, Oct 20 2019, 00:00:00)
[GCC 9.2.1 20190827 (Red Hat 9.2.1-1)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> type('a')
<type 'str'>
>>> type(b'a')
<type 'str'>
>>> type(u'a')
<type 'unicode'>

$ python3
Python 3.7.5 (default, Oct 17 2019, 12:16:48)
[GCC 9.2.1 20190827 (Red Hat 9.2.1-1)] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> type('a')
<class 'str'>
>>> type(b'a')
<class 'bytes'>
>>> type(u'a')
<class 'str'>
```

### Text/binary mode

Python以text mode读入，返回为`str`，以binary模式读入，返回为`str`(Python2)， `bytes`(Python3)。

这里面会带来一些很微妙的兼容性问题。Python2中两种模式读入的数据类型是相同的，但Python3中不同。
例如，json.dump。Python3中被dump的对象中有bytes的话会失败。当然可以通过自定义json encoder来实现。

但这里需要理解的是为什么Python3中默认bytes不能json dump —— Python3中的bytes不是`str`，它俩的相互转化需要codec。
而默认情况下假设一个编码是不明智的。否则很可能把错误延后——很可能某个时候会发现系统中有乱码了。

Python 2

```
>>> json.dumps({'file_content': open('tmpp', 'r').read()})
'{"file_content": ""}'
>>> json.dumps({'file_content': open('tmpp', 'rb').read()})
'{"file_content": ""}'
```

Python 3

```
>>> json.dumps({'file_content': open('tmpp', 'r').read()})
'{"file_content": ""}'
>>> json.dumps({'file_content': open('tmpp', 'rb').read()})
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib64/python3.7/json/__init__.py", line 231, in dumps
    return _default_encoder.encode(obj)
  File "/usr/lib64/python3.7/json/encoder.py", line 199, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "/usr/lib64/python3.7/json/encoder.py", line 257, in iterencode
    return _iterencode(o, 0)
  File "/usr/lib64/python3.7/json/encoder.py", line 179, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
TypeError: Object of type bytes is not JSON serializable
'""'
```

### Stdin/Stdout & Codec

当涉及到stdin/stdout的时候甚至更加复杂。因为通常还会涉及到Terminal的编码，请看下面的例子：

```
# codec.py:
import sys
print('Python default encoding: %s' % sys.getdefaultencoding()) # utf-8
print('Stdin encoding: %s' % sys.stdin.encoding) # gbk
print('Stdout encoding: %s' % sys.stdout.encoding) # gbk
print('argv1: %s' % sys.argv[1]) # 乱码，原因：命令行参数读入后utf-8 decode成字符串：“你”，写入到stdout时是gbk编码，但shell显示是按utf-8 解码。
print('argv1 encode to utf-8:')
sys.stdout.buffer.write(sys.argv[1].encode('utf-8')) # 正确字符串，原因：写入stdout的时候用utf-8编码，而不是默认的gbk
print()
#data = sys.stdin.read() # UnicodeDecodeError: 'gbk' codec can't decode byte 0xa0 in position 2: illegal multibyte sequence
# 原因：python解码stdin输入是使用gbk，但shell给到python的字节串是utf-8编码的。
data = sys.stdin.buffer.read() # binary 模式从stdin读入。data中是utf-8编码后的字节串
print('Read from stdin binary %s' % data)
sys.stdout.buffer.write(data) # 正常字符串。python中没有做任何编码解码
print(data.decode('utf-8')) # 乱码。utf-8字节串按utf-8解码之后正常，然后输出到stdout，使用gbk编码。shell使用utf-8解码。
sys.stdout.buffer.write(data.decode('utf-8').encode('utf-8')) # 正常字符串。python中utf-8解码又编码后写入stdout，shell正常按utf-8解码
```

```
$ locale
LANG=en_US.UTF-8
LC_CTYPE="en_US.UTF-8"
LC_NUMERIC="en_US.UTF-8"
LC_TIME="en_US.UTF-8"
LC_COLLATE="en_US.UTF-8"
LC_MONETARY="en_US.UTF-8"
LC_MESSAGES="en_US.UTF-8"
LC_PAPER="en_US.UTF-8"
LC_NAME="en_US.UTF-8"
LC_ADDRESS="en_US.UTF-8"
LC_TELEPHONE="en_US.UTF-8"
LC_MEASUREMENT="en_US.UTF-8"
LC_IDENTIFICATION="en_US.UTF-8"
LC_ALL=
$ echo 你| PYTHONIOENCODING=gbk python -u codec.py 你
Python default encoding: utf-8
Stdin encoding: gbk
Stdout encoding: gbk
argv1: ��
argv1 encode to utf-8:
你
Read from stdin binary b'\xe4\xbd\xa0\n'
你
��

你
$ echo 你| PYTHONIOENCODING=gbk python -u codec.py 你 | hexdump -C
00000000  50 79 74 68 6f 6e 20 64  65 66 61 75 6c 74 20 65  |Python default e|
00000010  6e 63 6f 64 69 6e 67 3a  20 75 74 66 2d 38 0a 53  |ncoding: utf-8.S|
00000020  74 64 69 6e 20 65 6e 63  6f 64 69 6e 67 3a 20 67  |tdin encoding: g|
00000030  62 6b 0a 53 74 64 6f 75  74 20 65 6e 63 6f 64 69  |bk.Stdout encodi|
00000040  6e 67 3a 20 67 62 6b 0a  61 72 67 76 31 3a 20 c4  |ng: gbk.argv1: .|
00000050  e3 0a 61 72 67 76 31 20  65 6e 63 6f 64 65 20 74  |..argv1 encode t|
00000060  6f 20 75 74 66 2d 38 3a  0a e4 bd a0 0a 52 65 61  |o utf-8:.....Rea|
00000070  64 20 66 72 6f 6d 20 73  74 64 69 6e 20 62 69 6e  |d from stdin bin|
00000080  61 72 79 20 62 27 5c 78  65 34 5c 78 62 64 5c 78  |ary b'\xe4\xbd\x|
00000090  61 30 5c 6e 27 0a e4 bd  a0 0a c4 e3 0a 0a e4 bd  |a0\n'...........|
000000a0  a0 0a                                             |..|
000000a2
```
hexdump 的结果可以看到乱码两个位置的输出其实是 `你` 的gbk编码：`c4 e3`
