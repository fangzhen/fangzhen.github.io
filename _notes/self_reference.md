---
layout: post
title: 自指
tags:
date: 2023-11-20
---
[自指(self-reference)](https://en.wikipedia.org/wiki/Self-reference)是指一个概念直接或间接地引用自己或自己的属性。
在语言学，逻辑学，数学，计算机科学，哲学，艺术等领域都有很多例子。

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

## 递归与不动点
数学上，不动点是指一个值在某个变换下不变，即为不动点。对于函数来说，即满足`f(x)=x`的点。不动点可能存在也可能不存在。

在计算机科学的组合逻辑中，[不动点组合子](https://en.wikipedia.org/wiki/Fixed-point_combinator)是一个高阶函数，返回作为参数的函数的不动点。

在经典无类型的lambda演算中，函数都有不动点。(为什么？)

> In the classical untyped lambda calculus, every function has a fixed point.
> https://en.wikipedia.org/wiki/Fixed-point_combinator

> Note：

> 下文中伪代码大致采用了haskell的语法，如函数定义，函数调用，lambda表达式。

如果f有一个不动点，根据不动点的定义(对f的不动点 `fix f`应用f，依然等于不动点)，即：
```
fix f = f (fix f)
```

labmda演算中，函数体内部无法直接引用函数本身，因而无法直接支持递归。使用不动点组合子，可以实现递归。
考虑一个函数f和它的(假想的)递归版本r，我们可以用r来实现f：
```
f r x = r x
```
x表示其他参数，上式把r作为额外参数传递给f，并直接在f的实现中调用r。
从而可以得到`f r = r`，所以，`r`即为`f`的不动点。
也就是说，通过求如上形式定义的函数`f`的不动点，我们就得到了它的递归版本。

### Y combinator
其中一个不动点组合子为Y组合子，最初由[Haskell Curry](https://en.wikipedia.org/wiki/Haskell_Curry)提出。

下面我从构造递归函数出发，推导出Y组合子的定义。

```
f r x = F r x : F r x表示实际的函数体实现。例如 ract n = n * ract n-1

```
要实现递归调用，关键是在函数体内获得自己的引用，为此，可以把函数本身作为参数。

所以，我们构造一个函数g，第一个参数h的类型是函数，在g的函数体中，使用参数h。
`g h x = G h x`
在调用g时，我们把g本身作为第一个参数， 即`g g`，就相当于做到了递归调用g。
但是可以看出来，这种只实现了一次递归调用，`g g`展开后变成 `G g x`，对它求值无法继续递归调用。
为此，`g`更新为：
```
g h x = G (h h) x
```
此时`g g x = G (g g) x = G (G (g g)) x = ...`，**`g g`就是一个递归函数。**

我们要使用g 构造任意非递归函数f的递归版本r，只需要让`G=f`，即`g g x = f (g g) x`，那么g的函数体应该写为
```
g h x = f (h h) x
```
注意这里的`f`对于`g`来说是自由变量(或者说类似环境变量，想像一下闭包)，并不是`g`的参数。

我们得到了`f`的递归版本`r = g g`。

从而，我们构造出了y组合子：
```
y f = g g where g h = f (h h)
```
即
```
y = \f -> (\h -> f (h h)) (\h -> f (h h))
```

> 个人认为构造y组合子的上述推导从直观上最容易理解。还有很多不同的方法。TODO

使用y组合子可以得到递归函数`r = y f`。

> 应当注意，对于非递归形式的函数`f`，我们能得到f的递归版本`r = y f`，但是并没有给出r的实际实现。y组合子虽然很神奇，但没那么神奇：)
> 但是我们确实又能使用`r`。

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

TODO haskell版：
``` rec.hs
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

## 停机问题
H(P, I)：图灵机P在输入I下会不会停止
G(P)：H(P, P)? loop: halt
G(G) 推出矛盾

对角线 P I

## 哥德尔不完备定理
任何关于数论可证性概念的系统中都含有不可证的真命题。

在系统中构造出命题：这个命题是不可证明的

如果该命题是假的，一个假命题是不能被证明的，而命题的内容声称命题可以证明，所以这种情况不可能发生。
那么该命题是真的，根据命题内容，它不可证明，即存在一个真的命题，但不可证明；

对角线 命题和证明

> 这个非形式化证明是通过构造一个不可证的真命题来实现的。而证明该命题可以构造出来本身也不容易。


## References
* 不动点
  - https://stackoverflow.com/questions/4273413/y-combinator-in-haskell
  - https://en.wikipedia.org/wiki/Fixed-point_combinator
  - [魂断不动点](https://deathking.github.io/2015/03/21/all-about-y-combinator/)
  - https://dreamsongs.com/Files/WhyOfY.pdf

* [康托尔、哥德尔、图灵——永恒的金色对角线](http://mindhacks.cn/2006/10/15/cantor-godel-turing-an-eternal-golden-diagonal/):
  这篇文章试图把停机问题，哥德尔定理，Y组合子都用康托尔对角线方法统一起来，并声称从哥德尔定理可以很容易地推出Y组合子。
  我个人没看出来Y组合子和对角线方法或哥德尔定理的联系。文章中对哥德尔定理和Y组合子的描述不太理解。
* [哥德尔机](https://www.luogu.com.cn/blog/user3296/yi-zhong-zi-bian-cheng-ji-tong-ge-de-er-ji)
