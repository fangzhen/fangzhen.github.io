---
layout: post
title: bash读取和执行命令过程
date: 2023-10-19
tags: bash shell quote
---

以下文档和脚本都是以bash为基础的。
## shell 读取和执行命令过程概述

### shell读取和执行命令的过程
bash读取然后执行命令的过程主要分为以下几步:
1. 读取输入：a. 从shell脚本；b. 从`-c`参数；c. 从终端。
2. 把输入分解为单词和操作符，该步骤应用引号规则以及alias expansion。
3. 把token解析为简单或复杂命令。如识别保留字，解析为单个命令，管道命令等。
4. 执行shell expansion。按顺序包括以下步骤：
   1. 大括号扩展；
   2. tilde扩展：例如`~`扩展为home目录；不像变量扩展，双引号内的`~`不会扩展。
   3. 参数和变量扩展：例如把变量`${var}`替换为值
   4. 执行命令替换：即`$(cmd)`或`` `cmd` ``
   5. 算术扩展：即`$((expression))`
   6. 分词：使用`IFS`作为分隔符，把上面未被引用的扩展的结果进行切分。(例如`"$v"`的展开结果不会切分，但`$v`的展开结果会切分)。
   7. 文件名扩展，如扩展`* . [`等。
   8. 引号移除，用来清理所有未被引用且不是扩展结果的以下字符：`\'"`。例如`echo "123"`和`echo 123`传给echo的参数都是`123`，不带引号。
5. 执行IO重定向，并把重定向相关的部分从命令中移除。
6. 执行命令。
7. (Optionally)等待命令完成，获取命令返回值。

<https://www.gnu.org/software/bash/manual/html_node/Shell-Operation.html>

### 变量赋值
在shell的定义中，parameter 是存储值的实体，它可以是名字(变量，如`$name`)，数字(如`$1`)或特殊字符(如`$*`)。
其中变量赋值的格式为：`name=[value]`。变量的值也会进行扩展，与命令扩展稍有不同，只有以下几项：
tilde扩展，参数和变量扩展，命令替换，算术扩展，引号移除。

参考<https://www.gnu.org/software/bash/manual/html_node/Shell-Parameters.html>

## 实例
下面脚本里加了注释，通过实际命令主要演示了shell expansion过程的一些细节。
```
#!/bin/bash
var='ab";  $c'\' # var的值为(不包括首尾的`)`ab";  $c'`
echo  Got  "$var" # echo得到两个参数 Got 和 var的值，var中的所有字符都原样输出。
echo  Got  $var # echo得到两个参数 Got 和 var的值，但是var展开后会被分词(步骤4.6)，如果有空格，会被切分为多个参数；特殊字符会原样输出。

echo
echo Demo shell expansion
cmd="echo $var" # cmd变量的值是 echo 连接上var的值，因为步骤4.8，cmd变量中没有首尾的引号。
$cmd # 4.3 变量扩展 4.6分词。echo的参数为var分词后的结果。其他特殊字符原样输出。
"$cmd" # 4.3变量扩展后，因为`$cmd`在引号中，不会被分词。整个字符串作为命令，会报错命令找不到

echo
echo 'Demo Two-Round process'
# 对于`ssh`或`bash -c`等，它们获取一个字符串作为参数，并解析该字符串以执行。也就是需要经过两轮的解析。
bash -c "$cmd" # 第一轮处理后cmd的值展开后作为`-c`的参数，需要再次经过第二轮处理过程。第二轮会报错，因为引号没有闭合。

echo
echo 'Demo pass var to command in bash -c literally'
# 前面`echo Got "var"`已经演示了如何把var的值原样传给其他命令。
# 这里演示在两轮处理的情况下，如何把var的值原样传递。
# 基本思路是让第二轮处理时获取到的字符串中，var的值被单引号引起来，对于var中本身就有的单引号，
# 要单独转义。或者说，模拟写shell脚本时的写法。
# 假如var的值是X'Y，实际写脚本或命令是需要写成var='X'\''Y'。下面'${var//\'/\'\\\'\'}'就是做这个事情。
e_cmd="echo '${var//\'/\'\\\'\'}'"
bash -c "$e_cmd"
# ssh some_host "$e_cmd"

echo
echo Demo Tilde expansion
var="~root/abc" # ~在引号内，不会扩展
echo $var # Tilde扩展(4.2)在参数扩展(4.3)之前，所以~root没有扩展
bash -c "echo $var" # 同样能够经过两轮处理，第二轮中会把~root扩展为/root
```

执行结果如下：
```
Got ab";  $c'
Got ab"; $c'

Demo shell expansion
ab"; $c'
./cmd_test.sh: line 10: echo ab";  $c': command not found

Demo Two-Round process
bash: -c: line 1: unexpected EOF while looking for matching `"'
bash: -c: line 2: syntax error: unexpected end of file

Demo pass var to command in bash -c literally
ab";  $c'

Demo Tilde expansion
~root/abc
/root/abc
```
