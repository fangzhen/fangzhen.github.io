---
layout: post
title: Python C extension中Exception导致后续 Python 代码异常
tags: Python CPython
date: 2018-02-03
update: 2021-06-28
---

## 问题描述

项目中使用[python-dmidecode](https://github.com/nima/python-dmidecode/)获取机器的memory信息，大部分机器没问题，能正常获取到。但是在某些型号的机器上，操作返回值的时候抛`IndexError`。示例代码如下：

```
import dmidecode

dms = dmidecode.memory()
for m in dms:
  print m
```

输出如下，在循环中抛异常：
```
0x1115
...
0x1000
Traceback (most recent call last):
  File "t2.py", line 5, in <module>
    for m in dms:
IndexError: list assignment index out of range
```
同样诡异的是，如果在python交互命令行测试的话，`dmidecode.memory()` 可以正常返回，但是下一条语句都会报IndexError。即使只回车一下，不执行任何语句都会报错。

```
>>> import dmidecode
>>> dms=dmidecode.memory()
>>>
IndexError: list assignment index out of range
>>>
```

### 环境信息
```
CPython 2.7
```

## 问题排查

### 初步猜想

试图用`id`，`dir`等内建函数查看返回的python对象，发现这俩函数用在返回的对象上都会抛同样的`IndexError`。胡乱试一通，发现在`dmidecode.memory()`之后，很多语句都会抛同样的错误，看起来毫无关联。例如`time.sleep()`， 其他不相关list/tuple/dict等的 for 循环。但是`copy.deepcopy()`不会出错，而且运行完之后也不会再抛错了。看起来毫无规律。

猜测会不会是某些语句会触发gc，gc的过程中出错，导致看起来现象是随机的呢。尝试手动`gc.disable()`后在`dmidecode.memory()`之后调用`gc.collect()`会报异常，然后gc失败，直接core dump了。看起来现象也不一致。而且理论上gc也不是这么触发的。此路不通。

注意到 `dmidecode.memory` 是通过C extension来实现的。估计是遇到了什么corner case，导致python解释器内部有不一致，结合python的异常抛出机制导致在C extension 语句执行完后没有抛出异常，而是在后续语句中抛出了异常。
`python-dmidecode`主体是C写的，粗略看了一下，没有问题的方向，看不出问题在哪。对python 异常处理的实现也不太熟悉，也没有明确的方向。

### 为什么Exception随机出现

使用gdb可以attatch到运行的python进程上进行调试，使用gdb调试CPython的方法可以参考[^1][^2]：

之前测试我们看到`dmidecode.memory()`执行之后情况下都会抛异常出来，我们使用一段最简代码复现，debug看一下具体什么位置抛出的异常：

```
# filename: t.py

import dmidecode
import time

time.sleep(8) # Wait for gdb attatching
it = iter([])
dmidecode.memory()
next(it) # It is supposed to raise StopIteration Exception, But it raises IndexError
```
`python t.py &` 拿到pid，然后 `gdb /usr/bin/python -p <pid>` attatch到python进程。

next是个builtin方法，在CPython源码的`Python/bltinmodule.c` 实现，如下部分。
```
1105 static PyObject *
1106 builtin_next(PyObject *self, PyObject *args)
1107 {
1108     PyObject *it, *res;
1109     PyObject *def = NULL;
1110
1111     if (!PyArg_UnpackTuple(args, "next", 1, 2, &it, &def))
1112         return NULL;
1113     if (!PyIter_Check(it)) {
1114         PyErr_Format(PyExc_TypeError,
1115             "%.200s object is not an iterator",
1116             it->ob_type->tp_name);
1117         return NULL;
1118     }
1119
1120     res = (*it->ob_type->tp_iternext)(it); # retrieve current data under iterator
1121     if (res != NULL) {                     # Get expected data
1122         return res;
1123     } else if (def != NULL) {
1124         if (PyErr_Occurred()) {
1125             if (!PyErr_ExceptionMatches(PyExc_StopIteration))
1126                 return NULL;
1127             PyErr_Clear();
1128         }
1129         Py_INCREF(def);
1130         return def;
1131     } else if (PyErr_Occurred()) {         # No data returned, but some error occured
1132         return NULL;
1133     } else {                               # No data returned, and no error. Then we should
1134         PyErr_SetNone(PyExc_StopIteration); # raise StopIteration according to Iterator Protocol
1135         return NULL;
1136     }
1137 }
```
`1120` 行之后做了简单注释。debug发现 进入到了`1132`行。但是stepinto `1120`行并没有发现设置异常。而且在`1120`行之前，也就是实际去取数据之前已经有了异常。

这时候异常随机抛出的原因已经比较明显，python 代码里调用`dmidecode.memory()`虽然看起来正常返回了，但是它实际产生了异常，只不过在dmidecode的实现里没有去检查，导致异常被带到了之后的语句中。
那么在其他地方（例如上面`1131`行）处理异常的地方就会发现一个未预期的异常，然后抛出。

除了next其他很多实现都是类似的异常处理逻辑，所以很多受影响的代码看起来毫无关联。

[^1]: http://podoliaka.org/2016/04/10/debugging-cpython-gdb/
[^2]: https://devguide.python.org/gdb/

### 问题根源：python-dmidecode中的异常

那么接下来就要找[python-dmidecode](https://github.com/nima/python-dmidecode/)代码在什么地方引入了这个异常。

搜索 CPython代码发现，匹配上述`IndexError: list assignment index out of range` 的异常只有Objects/listobject.c出现，分别是`PyList_SetItem`和`list_ass_item`函数的两个地方。在C扩展中一般只会用到前者。
在python-dmidecode代码里找`PyList_SetItem`的出现，只有两处都在`xmlpythonizer.c`中。重新debug一下，在两个问题代码处设置条件断点，很容易找到问题出在904行。

```
903 if( idx != NULL ) {
904     PyList_SetItem(value, atoi(idx)-1,
905                    StringToPyObj(logp,
906                    map_p, valstr)
907                   );
908 }
```

```
(gdb) b /usr/src/debug/python-dmidecode-3.12.2/src/xmlpythonizer.c:987 if atoi(idx) >= map_p->fixed_list_size
Breakpoint 1 at 0x7fbe051557c5: file src/xmlpythonizer.c, line 987.
(gdb) b /usr/src/debug/python-dmidecode-3.12.2/src/xmlpythonizer.c:904 if atoi(idx) >= map_p->fixed_list_size
Breakpoint 2 at 0x7fbe05155abf: file src/xmlpythonizer.c, line 904.
```

然后根据debug信息很容易找到问题出在memory的‘Type Detail’。dmidecode根据pymap.xml里的定义预分配了一个大小是12的List，但是实际SetItem的时候index是13导致`IndexError`。
但是dmidecode在代码退出的时候没有检查是否有异常而直接返回到Python解释器了。

通过查看[smbios specification](https://www.dmtf.org/standards/smbios), ‘Type Detail’应该是15位的flag，按dmidecode的实现应该在pymap.xml中对应把12改成15。dmidecode.c中`dmi_memory_device_type_detail`函数中定义的flag数量是正确的。

### 总结

回过头来看这个case，`dmidecode.memory()`不会抛异常，而是到后面的语句才会抛异常，从而使问题从最开始变得非常不直观。加上对CPython的具体实现了解较少，比较难在最开始直接找到问题根源。

在Python 文档中其实有相关描述：

https://docs.python.org/2/c-api/exceptions.html

> If the error is not handled or carefully propagated, additional calls into the Python/C API may not behave as intended and may fail in mysterious ways.

这个问题不修改`python-dmidecode`源码的一个workaroud是在`dmidecode.memory()`加上try-except并在try块里触发一下这个IndexError。

## More： python 3 的优化

至于具体为什么在`dmidecode.memory()`后没有立即抛exception出来：

PyObject_Call中处理了`result == NULL && !PyErr_Occurred()`的情况，没有处理`result != NULL && PyErr_Occurred()` 的情况（本case中`dmidecode.memory()`调用后的情况），导致 `ceval.c`中不会进入`on_error`。这其实是一种不一致状态。

Objects/abstract.c:

```
PyObject *
PyObject_Call(PyObject *func, PyObject *arg, PyObject *kw)
{
    ternaryfunc call;

    if ((call = func->ob_type->tp_call) != NULL) {
        PyObject *result;
        if (Py_EnterRecursiveCall(" while calling a Python object"))
            return NULL;
        result = (*call)(func, arg, kw);
        Py_LeaveRecursiveCall();
        if (result == NULL && !PyErr_Occurred())
            PyErr_SetString(
                PyExc_SystemError,
                "NULL result without error in PyObject_Call");
        return result;
    }
    PyErr_Format(PyExc_TypeError, "'%.200s' object is not callable",
                 func->ob_type->tp_name);
    return NULL;
}
```

Python/ceval.c

```
        switch (opcode) {
...
        TARGET(CALL_FUNCTION)
        {
            PyObject **sp;
            PCALL(PCALL_ALL);
            sp = stack_pointer;
#ifdef WITH_TSC
            x = call_function(&sp, oparg, &intr0, &intr1);
#else
            x = call_function(&sp, oparg);
#endif
            stack_pointer = sp;
            PUSH(x);
            if (x != NULL) DISPATCH(); # （笔者注）x不为空，但PyErr_Occurred()为true，导致进入了DISPATCH，而没有进入on_error
            break;
        }
        } /* switch */

        on_error:
...
        if (why == WHY_EXCEPTION) {
            PyTraceBack_Here(f);

            if (tstate->c_tracefunc != NULL)
                call_exc_trace(tstate->c_tracefunc,
                               tstate->c_traceobj, f);
        }

```

目前看 Python 3.7 的代码，这个问题就得到了解决，会检查`result`和`PyErr_Occurred()`的各种组合：
```
PyObject*
_Py_CheckFunctionResult(PyObject *callable, PyObject *result, const char *where)
{
    int err_occurred = (PyErr_Occurred() != NULL);

    assert((callable != NULL) ^ (where != NULL));

    if (result == NULL) {
        if (!err_occurred) {
            if (callable)
                PyErr_Format(PyExc_SystemError,
                             "%R returned NULL without setting an error",
                             callable);
            else
                PyErr_Format(PyExc_SystemError,
                             "%s returned NULL without setting an error",
                             where);
            return NULL;
        }
    }
    else {
        if (err_occurred) {  # (笔者注) 此处检查result != NULL && error_occurred情况并处理，最终返回NULL
            Py_DECREF(result);

            if (callable) {
                _PyErr_FormatFromCause(PyExc_SystemError,
                        "%R returned a result with an error set",
                        callable);
            }
            else {
                _PyErr_FormatFromCause(PyExc_SystemError,
                        "%s returned a result with an error set",
                        where);
            }
            return NULL;
        }
    }
    return result;
}
```
所以看起来在 Python3 的情况下，`dmidecode.memory()`这行就会抛exception了，不会扩散到下面的语句中。
