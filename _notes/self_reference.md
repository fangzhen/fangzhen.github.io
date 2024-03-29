---
layout: post
title: 自指
tags: self-reference
date: 2023-11-20
update: 2023-12-21
---
[自指(self-reference)](https://en.wikipedia.org/wiki/Self-reference)是指一个概念直接或间接地引用自己或自己的属性。
在语言学，逻辑学，数学，计算机科学，哲学，艺术等领域都有很多例子。
本文仅列出一些自指的例子及进行一点简单的探讨。
* TOC
{:toc}

## 语言中自指的例子

这个句子有八个字。

语言自指悖论：
 - 这句话是假的。(括号外这句话是真的还是假的？)

开源社区中递归缩写的名字：
- GNU: GNU's Not Unix。由RMS发起的一个计划，旨在创建一个完全自由的类Unix操作系统。
- WINE: WINE Is Not an Emulator。它是一个允许在类Unix系统上运行Windows应用程序的兼容层。
- HURD: Hird of Unix-Replacing Daemons。GNU计划的操作系统内核。
  - Hird: Hurd of Interfaces Representing Depth

## 打印自身源码的程序
python版，关键在于`%r`可以输出原始字符串。
```python
me='me=%r\nprint(me %% me)'
print(me % me)
```

c版，关键在与字符串`s`中不要包含转义字符。
{%raw%}
[//]: # (使用raw是因为下面c代码包含连续的{ %，会被liquid当作tag处理)
```c
#include<stdio.h>
int main(){
  char* s="#include<stdio.h>%cint main(){%c  char* s=%c%s%c;%c  printf(s, 10, 10, 34, s, 34, 10, 10, 10);%c}%c";
  printf(s, 10, 10, 34, s, 34, 10, 10, 10);
}
```
{%endraw%}

## 理发师悖论与罗素悖论
理发师悖论：小城里的理发师为城里所有“不为自己理发的人”理发。
那么这个理发师是否要给自己理发？

罗素悖论是由英国哲学家和数学家伯特兰·罗素于1901年提出的一个集合论悖论，
其基本思想是：对于任意一个集合A，A要么是自身的元素，即A∈A；A要么不是自身的元素，即A∉A。根据康托尔集合论的概括原则，可将所有不是自身元素的集合构成一个集合S1，即S1={x:x∉x}。
那么这个集合S1是不是自身的元素？

理发师悖论经常被认为是罗素悖论的通俗版本。

## 递归与不动点
数学上，不动点是指一个值在某个变换下不变，即为不动点。对于函数来说，即满足`f(x)=x`的点。不动点可能存在也可能不存在。

在计算机科学的组合逻辑中，[不动点组合子](https://en.wikipedia.org/wiki/Fixed-point_combinator)是一个高阶函数，返回作为参数的函数的不动点。
根据[wikipedia](https://en.wikipedia.org/wiki/Fixed-point_combinator)，在经典无类型的λ演算中，函数都有不动点。(TODO：why)

> Note：
> 下文中伪代码大致采用了haskell的语法，如函数定义，函数调用，λ表达式等。

如果f有一个不动点，根据不动点的定义(对f的不动点 `fix f`应用f，依然等于不动点)，即：
```hs
fix f = f (fix f)
```

λ演算中，函数体内部无法直接引用函数本身，因而无法直接支持递归。使用不动点组合子，可以实现递归。
考虑一个函数f和它的(假想的)递归版本r，我们可以用r来实现f：
```hs
f r x = r x
```
x表示其他参数，上式把r作为额外参数传递给f，并直接在f的实现中调用r。
从而可以得到`f r = r`，所以，`r`即为`f`的不动点。

也就是说，对于以如上形式定义的函数`f`，通过获得它的不动点，我们就能得到它的递归版本，甚至不需要做具体实现。

### y combinator
其中一个不动点组合子为y组合子，最初由[Haskell Curry](https://en.wikipedia.org/wiki/Haskell_Curry)提出。

上面提到可以使用不动点用来构造递归函数。
反过来，我们可以利用递归来构造不动点组合子。

下面我就从一个函数构造它的递归函数的过程，一步步构造出y组合子。

1. 定义一个要构造其递归版本的非递归函数`f`，第一个参数`r`是其递归版本，`f`的函数实现中调用`r`。
   ```hs
   f r x = F[r, x] -- F[r, x]用来表示实际的函数体实现，这只是本文为了方便说明使用的一个记法。 例如阶乘函数：
   fact rfact n = if n == 1 then 1 else n * (rfact (n-1))
   ```

2. 要实现递归调用，需要在函数体内获得自己的引用，为此，可以把函数本身作为参数。
   所以，我们构造另一个函数`g`，第一个参数`h`的类型是函数，在`g`的函数体中，使用参数`h`。即：
   ```
   g h x = G[h, x]
   ```
   在调用`g`时，我们把`g`本身作为第一个参数， 即`g g`，就在函数实现中得到了自身的引用。
   但是可以看出来，这种只实现了一次递归调用，`g g`展开后变成 `G(g, x)`，对它求值无法继续递归调用。
   因此，`g`更新为：
   ```
   g h x = G[(h h), x]
   ```
   此时`g g x = G[(g g), x]`，从而**`g g`是一个递归函数。**

3. 结合两者，为了让`g g`成为我们想要的递归函数`r`，要让`g g`实现和`r`相同的功能
   (注意最后`f (g g) x`中的已经没有了`r`，因为`r`本身并没有实际定义)：
   ```
   g g x = r x = f r x = f (g g) x
   ```
   那么g的函数体`G[(h h), x]`的实际实现为：
   ```
   g h x = f (h h) x
   ```
   注意这里的`f`对于`g`来说是自由变量(或者说类似环境变量，想像一下闭包)，并不是`g`的参数。

   从而在上述`g`的实现下，我们得到了`f`的递归版本`r = g g`。

4. 综上，我们已经构造出了y组合子：
   ```
   y f = g g where g h = f (h h)
   ```
   即
   ```
   y = \f -> (\h -> f (h h)) (\h -> f (h h))
   ```

虽然上述过程只是从特定形式的函数构造递归版本的过程中构造出的y组合子，但构造出的y组合子是普适的。
有了y组合子，我们可以从`f`得到其递归函数`r = y f`。

> 个人认为构造y组合子的上述推导从直观上最容易理解。还有很多不同的方法。例如 <https://dreamsongs.com/Files/WhyOfY.pdf>。

应当注意，对于非递归形式的函数`f`，我们能得到f的递归版本`r = y f`，但是并没有给出r的实际实现。y组合子虽然很神奇，但没那么神奇：)
但是我们确实又能使用`r`。

**实例：阶乘**

以阶乘为例，可以看一下使用y组合子构造出递归实现`rfact`并计算的过程(使用不同的括号只是为了更容易地看出匹配的括号)：
```
fact rfact n = if n == 1 then 1 else n * (rfact (n-1))

rfact2 = y fact 2 =
(\h -> fact (h h)) (\h -> fact (h h)) 2 =
fact {[\h -> fact (h h)] [\h -> fact (h h)]} 2 =
2 * ( {[\h -> fact (h h)] [\h -> fact (h h)]} 1) =
2 * (fact {[\h -> fact (h h)] [\h -> fact (h h)]} 1) =
2 * (1) = 2
```
> 上面的过程采用了惰性求值，否则`fact {[\h -> fact (h h)] [\h -> fact (h h)]} 2`求值时先计算第一个参数(其实就是`rfact`)，会无限循环。
> 也就是上面说的，y 组合子没有给出递归函数rfact的具体实现，但我们可以使用rfact。

### y combinator的haskell实现 TODO
```hs
-- Mu :: (Mu a -> a) -> Mu a
newtype Mu a = Mu (Mu a -> a)

w :: (Mu a -> a) -> a
w h = h (Mu h)
-- 太强大以至于不真实的感觉 - Mu h封装了h, 用来作为参数传递。但是构造器又不用实际实现。

y :: (a -> a) -> a
y f = w (\(Mu x) -> f (w x))
-- y f = f . y f

p :: (Int -> Int) -> Int -> Int
p r n = if n == 0 then 1 else n* r (n-1)

newtype Rec a = In { out :: Rec a -> a }

y :: (a -> a) -> a
y = \f -> (\x -> f (out x x)) (In (\x -> f (out x x)))
```

## 哥德尔不完备定理
**哥德尔第一定理**：任何自洽的形式系統，只要蕴涵皮亚诺算术公理，就可以在其中构造在体系中不能被证明的真命题，因此通过推理演绎不能得到所有真命题（即体系是不完备的）。

非形式化的证明：
在系统中构造出命题：这个命题是不可证明的
如果该命题是假的，一个假命题是不能被证明的，而命题的内容声称命题可以证明，所以这种情况不可能发生。
那么该命题是真的，根据命题内容，它不可证明，即存在一个真的命题，但不可证明；

形式化证明要点：
1. 每个公式或命题都可以被赋予一个数，称为**哥德尔数**。例如，可以用如下方式构造哥德尔数：
   假设形式系统有100个符号，用0至99对这些符号进行编码，这样，一个命题的哥德尔数就是一个位数为公式长度的100进制的整数。
   因此一个数可能不对应公式或对应某个唯一的公式。
   因为系统包含所有正整数，所以这个编码可以包含所有公式。
   公式中表示自由变量的符号(例如使用x还是y)不影响其哥德尔数。
2. 一个证明可以看成有限的命题序列，所以可以用类似的方法把证明对应到一个数。
3. 构造哥德尔命题：
   a. 定义关系`q(n, G(F))`表示`n`不是`F(G(F))`的某个证明的哥德尔数，换句话说，哥德尔数为`n`的证明证明不了`F(G(F))`
   b. 那么命题`∀y q(y, G(F))`指出`F(G(F))`不可证明
   c. 定义公式`P(x)=∀y q(y, x)`，`x`是自由变量。公式描述的是：`F(G(F))`不可证明，其中`F`是哥德尔数`x`的对应公式。
   d. 构造命题`P(G(P))`，该命题的意思是`P(G(P))`不可证明。如果考虑该命题是否可证明，会导出矛盾：
      - 如果命题可证明，则说明命题为假，一致的系统不应该证明假的命题，导出矛盾；
      - 如果命题不可证明，说明命题为真，但是该真命题无法证明。

### 从哥德尔第一定理的证明推出y选择子
从另一种构造哥德尔命题的方式出发：
1. 定义公式`Q(x)`： 哥德尔数为`x`的命题是不可证明的。
2. 找到函数`G(Q(x))`的不动点，假设为`k`，即`G(Q(k))=k`，表示把`k`带入公式`Q(x)`得到的命题`Q(k)`的哥德尔数仍为`k`。
3. 那么考虑命题`Q(k)`，它其实与上面的`P(G(P))`是同样的命题。

从而，我们可以从两种构造哥德尔命题的方法中推导出不动点选择子。(注意下面我们省掉了函数到哥德尔数的转化，可以理解为函数指针)：
1. 定义函数`Q`，我们想求`Q`的不动点：
   ```hs
   Q x = <Statement x is  not provable>
   ```
2. 参考公式`P(x)`，构造函数`P`：
   ```hs
   P h = Q (h h) -- (h h)不可证明
   ```
3. 把`P`本身作为参数带入P，就得到了`Q`的不动点`P P`：
   ```hs
   P P = Q (P P) -- 命题`P P`不可证明，这本身就是命题`P P`
   ```
4. 从而，得到y选择子：
   ```
   y Q = P P where P h = Q (h h)
   ```

## 停机问题
停机问题（Halting Problem）是计算机科学中一个经典的问题，由艾伦·图灵（Alan Turing）在1936年提出。
该问题的陈述是：是否存在一个通用算法，对于任何给定的程序和输入，都可以判断程序是否会在有限步骤内停机。

停机问题的证明与哥德尔第一定理的证明有很多相似之处，都要指定编码规则以及构造自指寻找矛盾。

对角线法证明：
1. 假设存在一个算法H(P, I)，判断程序P在输入I下是否停机。
2. 构造一个表格，列出所有可能的程序和输入(对于P和I的编码可以使用类似哥德尔数的逻辑)。

   |    | I1 | I2 | .. |
   | P1 | H  | N  |    |
   | P2 | H  | H  |    |
   | .. |    |    |    |
3. 构造程序Pd，使得Pd在输入Ii上的结果与H(Pi, Ii)相反，即如果Pi在Ii上停机，那么Pd在Ii上不停机。
4. 因为上面的表格包含了所有程序和所有输入，所以Pd也在上面的表格中。
   那么考虑Pd在Id上是否停机，即下表“?”处。就会发现停机或不停机都有矛盾。

   |    | I1 | I2 | .. | Id | .. |
   | P1 | H  | N  |    | N  |    |
   | P2 | H  | H  |    | N  |    |
   | .. |    |    |    |    |    |
   | Pd | N  | N  |    | ?  |    |
   | .. |    |    |    |    |    |

## References
* 不动点
  - https://stackoverflow.com/questions/4273413/y-combinator-in-haskell
  - https://en.wikipedia.org/wiki/Fixed-point_combinator
  - [魂断不动点](https://deathking.github.io/2015/03/21/all-about-y-combinator/)
  - https://dreamsongs.com/Files/WhyOfY.pdf
* [康托尔、哥德尔、图灵——永恒的金色对角线](http://mindhacks.cn/2006/10/15/cantor-godel-turing-an-eternal-golden-diagonal/):
  这篇文章把停机问题，哥德尔定理，y组合子都用康托尔对角线方法统一起来。文章中对哥德尔定理推出y组合子的描述不太理解。但本文中个人觉得做了更清晰的阐述。
* [哥德尔机](https://www.luogu.com.cn/blog/user3296/yi-zhong-zi-bian-cheng-ji-tong-ge-de-er-ji)
* [wikipedia](https://en.wikipedia.org/wiki/Proof_sketch_for_G%C3%B6del's_first_incompleteness_theorem)对哥德尔第一定理的描述和证明
