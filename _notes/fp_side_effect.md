---
layout: post
title: IO monad 如何封装函数副作用
tags: haskell side-effect functional-programming
date: 2023-03-13
update: 2023-03-13
---

## 引言
本文对纯函数式语言中如何用Monad封装函数副作用进行介绍和分析。

本文需要对[编程范式](https://en.wikipedia.org/wiki/Programming_paradigm)和函数式编程有基本的了解。
最好对函数式编程中的[factor, applicative, moand概念](https://www.adit.io/posts/2013-04-17-functors,_applicatives,_and_monads_in_pictures.html)有所了解。

文中示例代码主要使用haskell，需要对haskell有一定的了解。

## 函数副作用

对于纯函数，同样的输入总会产生同样的输出，但是像很多IO功能，如`print`， `getchar`，它们的执行要在console上进行输出或者读取用户输入，但是并不体现在返回值上，也就是所谓的副作用。

对于副作用，主要解决两个问题：
1. 调用顺序。lazy evaluation带来的结果是编译器只计算为了得到最终结果必要的值，而计算过程可能打乱顺序。
2. 纯函数可以做Memoization优化。但是副作用在函数每次调用都需要实际被执行。

> 这里副作用跟有时候会讲到的变量可变性没有关系。有副作用的函数中，变量/参数仍然是immutable的。

**副作用本质上是因为函数执行是跟程序外部的真实世界相关联的，只不过在函数参数和返回上没有体现出来。**

因此为了把有副作用的函数改写为纯函数，我们可以给函数加个*超能力*，让函数把真实世界作为参数和返回值。
我们给任何有副作用的函数添加`RealWorld`参数和返回值（没有副作用的函数添加只会带来性能损失/复杂性提高，并不会带来正确性上的差别）。例如
```
getchar :: RealWorld -> (Char, RealWorld)
getchar r = magicGetcharAndChangeWorld(r)
```
理想状态下，`getchar`（或任何其他函数）可以类似改写，改写后就变成了纯函数。例如可以定义`get2chars`为
```
get2chars :: realWorld -> ([Char], RealWorld)
get2chars r1 = let c1, r2 = getchar(r1)
                   c2, r3 = getchar(r2) in
                   ([c1, c2], r3)
```

这个方案带来两个新问题：
1. 所有副作用函数都要加RealWorld 参数和返回值，侵入性强，而且难以维护；
   下文我们提到副作用函数，指的就是加了RealWorld参数和返回值的函数，技术上，它其实是纯函数。
   类型为`RealWorld -> (a, RealWorld)`。
2. `RealWorld`无法在程序内部具体表示和修改，因为按照定义，它的范畴是比程序更广的。所以最终需要`MagicGetcharsAndChangeWorld`从`realWorld`获取字符并返回`new realWorld`。它是最终连接程序内部世界与realworld的桥梁。

我们接下来考虑如何解决这两个新问题。

## IO monad

monad 用来解决第一个问题。下面代码是个示例：基本思路是使用 `MyIO` monad 把`RealWorld`相关的代码封装起来，使得业务代码不需要考虑`RealWorld`相关的逻辑，但是最终能达到顺序调用的目的。

```
type RealWorld = Int
realWorld = 1
count=40000000

countdown :: Int -> RealWorld -> ((), RealWorld )
countdown 1 r = ((), r)
countdown x r = countdown (x-1) r

data MyIO a = Act (RealWorld -> (a, RealWorld))
class MyMonad m where
    mreturn :: a -> m a                  -- "unit"
    (>->=)  :: m a -> (a -> m b) -> m b  -- "bind"
    (>->)  :: m a -> m b -> m b

instance MyMonad MyIO where
    m >->= k = Act $ \r1 -> let Act s1 = m
                                (x, r2) = s1 r1
                                Act s2 = k x
                                (y, r3) = s2 r2 in
                              (y, r3)
    m >-> k = Act $ \r1 -> let Act s1 = m
                               (_, r2) = s1 r1
                               Act s2 = k
                               (y, r3) = s2 r2 in
                             (y, r3)
    mreturn x = Act $ \r -> (x, r)

msleep :: MyIO ()
msleep = Act $ countdown count

mymain = msleep
--mymain = msleep >->= \x -> msleep
--mymain = msleep >-> msleep
main = let Act s = mymain
           (res, r) = s realWorld in
  print r
```

这个示例是对haskell中`IO`的简化实现，并演示以`mymain`作为程序入口，以`MyIO`封装函数副作用的使用。下面表格说明了示例中的实现与haskell中实现/概念的对应关系。

| 示例中的实现 | haskell 对应 | 说明|
| `MyMonad` | `Monad` | monad type class定义 |
| `MyIO` | `IO` | 封装 `RealWorld`的使用 |
| `msleep` | `getchar`等 | 任意返回`MyIO`类型的函数 |
| `mymain` | `main` | 使用`MyIO`的程序入口 |
| `countdown` | 无 | 模拟有副作用的函数（此处为时间消耗），没有haskell的实现对应。|
| `main` | 无 | 模拟编译器对main的执行，没有haskell的实现对应。 可以理解为编译器编译时调用`main`的处理逻辑|

> Note: `countdown`和`main`在本示例中用来模拟haskell语言之外的行为。

下面我们说明`MyIO`如何封装了副作用以及副作用是如何被执行的：
1. 总体来说，`main`把封装在`mymain`中的副作用解封出来并执行。

   `main`中，为了计算出`(res, r)`的值，我们看到以下依赖：`(res, r) -> s -> mymain`。`let`部分实际做的事情就是把封装在`MyIO`中的`s`拿出来，并以`realWorld`作为参数调用。`s`的类型是`RealWorld -> (a, RealWorld)`，是被封装有副作用的过程。

   在`countdown`有副作用的情况下，`msleep`本身还是pure的。`msleep`执行并不会实际执行`countdown`，而只是封装了它。在`mymain=msleep`时，`main`中被解封出来的s就是`countdown 40000000`，也就是在main中执行到`s realWorld`时才实际执行了`countdown`。

2. 再来看`>->=`的实现，看看`m >->= k`做了什么：

   总体来说，`m >->= k`把封装在`m`和`k x`中的副作用`s1`和`s2`合并为`s3`并封装。

   具体来说，它封装了另一个函数`s3`，该函数被调用时，`let`部分很明确的显示了整个执行步骤，可以看到变量有依赖，这决定了执行的顺序。例如在`s3`被调用时，有副作用的`s1`会在`s2`之前执行。而`m>->=k`本身还是pure的，它只是封装了s3。


我们可以注意到，返回`MyIO`的函数**本身还是纯函数，但是把副作用函数封装在了MyIO中**。通过解封装MyIO并执行里面的副作用函数，达到了顺序执行有副作用函数的效果。

`>->` 跟`>->=`类似，当我们需要顺序执行，但是后面的函数不依赖前面的结果时，可以简化。
例如上面示例中 `msleep >->= \x -> msleep`和`msleep >-> msleep`可以达到同样的效果。

## RealWorld 不real
显然我们不可能把真正的`realworld`传到程序内部，我们只可能尽可能小的部分，还要能达到目标。

回忆一下，我们引入RealWorld是为了解决两个问题：1. 执行顺序; 2. 避免Memoization.

在Monad解决了执行顺序的问题后，我们还需要解决Memoization的问题，在函数被多次执行时，需要确实被执行（比如上面例子中消耗时间）。例如当`s1 s2`和`r1 r2`分别相同的时候，调用`s3`时，`s1 r1`和`s2 r2`也需要两次都要执行。

这一点其实也已经满足。
背后的情况是，编译器GHC并不会记忆函数结果，即使使用相同的参数多次调用，每次都会重新计算。
我猜测GHC应该并没有对RealWorld做特殊处理,只是依赖了它不会记忆函数结果，就足够保证函数应该被执行的时候就会执行。

> 这里不会记忆的是有参数的函数。对于没有参数的函数，在haskell中，其实和变量没区别。
> 另一方面，副作用函数的类型是`RealWorld -> (a, RealWorld)`，它一定是有参数的。

可以看到上面的示例中，在`msleep >-> msleep`的情况下，`s1 r1`和`s2 r2`都是`(countdown 40000000) realWorld`，通过执行时间我们可以推测执行了两遍。

### 编译执行，记录一下执行时间
```
$ ghc -dynamic test2.hs  && time ./test2
```
mymain 在执行一次`msleep`和两次`msleep`的情况下，可以看到运行时间差不多翻倍。
```
# mymain = msleep
real    0m0.409s

# mymain = msleep >->= \x -> msleep
real    0m0.763s

# mymain = msleep >->= msleep
real    0m0.763s
```

作为对比
```
countdown 1 = ()
countdown x = countdown (x-1)

msleep = countdown 40000000

main = do
    print msleep
    print msleep  -- 执行print msleep 一次或多次并不会造成运行时间有显著差别
```

## 其他

### 怎么理解副作用
一方面，haskell作为纯函数语言，无法直接定义有副作用的函数；另一方面，我们把haskell函数`countdown`的执行时间作为函数副作用，并基于此演示了如何使用MyIO Monad 来封装副作用。

那么到底怎么来定义副作用呢？对程序之外的真实世界有影响？这太笼统了。比如函数执行都需要时间的，一般我们不把时间作为副作用，但是我们上面示例的countdown，就是把消耗时间当成了副作用。

反过来，我们可以这么定义有副作用的函数，如果我们希望对这个函数的调用：
1. 需要有确定的执行顺序
2. 多次调用的情况下，需要每次调用都实际执行
那么就认为这个函数有副作用。

在上面`MyIO`封装函数副作用的实现下，我们就需要把副作用函数的参数和返回值加上`RealWorld`类型，对`countdown`来说，就`从countdown :: Int -> ()`变成了 `countdown :: Int -> RealWorld -> ((), RealWorld )`，即变成了没有副作用的纯函数。然后再通过`MyIO`把`RealWorld`封装起来，让基于`countown`的函数无需处理`RealWorld`逻辑。

当然如果不用上面定义的`MyIO`，而用系统的`IO` Monad来实现我们把时间消耗作为副作用的`countdown`也可以，如下：
```
{-# LANGUAGE MagicHash #-}
{-# LANGUAGE UnboxedTuples #-}
import GHC.Prim
import GHC.Base

count=40000000

countdown :: Int -> State# RealWorld -> (# State# RealWorld, () #)
countdown 1 r = (# r, () #)
countdown x r = countdown (x-1) r

msleep :: IO ()
msleep = IO $ countdown count

--main = msleep -- use 0.368s
main = msleep >>= \x ->  msleep -- use 0.734s
```

副作用与Monad没有必然联系，只是类似`IO`Monad的实现把两者结合起来。

### Lazy Evaluation
```
countdown :: Int -> Int -> ((), Int )
countdown 1 r = ((), r)
countdown x r = countdown (x-1) r

count = 40000000

main = let (_, r1) = countdown count 1
           (res, r2) = countdown count r1
  in do
    print res
--    print r2
```

这段代码，在`print r2`这行是否被注释掉的不同情况下，执行时间分别为0.39s和0.78s。差不多是一半的时间。原因是没有`print r2`是就不需要计算r2的值，进而不需要计算r1的值，从而第一个`countdown`不用执行。

上面`MyIO` monad示例中，最后main函数如果`print r`改为`print res`，也会因为lazy eval而只会执行一次`countdown count`。

## references
* [GHC的IO实现](https://hackage.haskell.org/package/base-4.18.0.0/docs/src/GHC.Base.html#returnIO)
* [haskell wiki IO inside](https://wiki.haskell.org/IO_inside):
我参考这个文档比较多，但是最终思路不太一样。本文大概只涉及了这个文档关于IO Monad实现部分的内容（1,2,3）。

   文中给出的实现有个typo。`runIO m s` 应为`runIO m t1`
   ```
   instance Monad IO where
       m >>= k  = let runIO (Act m) = m in
                  Act $ \t1 -> case runIO m s of (x, t2) -> runIO (k x) t2
       return x = Act $ \t1 -> (x, t1)
   ```

* fuctors, applicatives, monads 介绍。
   <https://www.adit.io/posts/2013-04-17-functors,_applicatives,_and_monads_in_pictures.html>
* 范畴论是haskell中有些feature的数学基础。
  - <https://bartoszmilewski.com/2014/10/28/category-theory-for-programmers-the-preface/>
  - [segmentfault上对前两部分的翻译](https://segmentfault.com/t/%E8%8C%83%E7%95%B4%E8%AE%BA)
* haskell 基础
  - <http://learnyouahaskell.com/chapters>
  - <https://downloads.haskell.org/ghc/latest/docs/users_guide/exts/primitives.html>
* memoization:
  - <https://wiki.haskell.org/Memoization>
  - <http://conal.net/blog/posts/elegant-memoization-with-functional-memo-tries>
* 关于haskell里side effect跟monad相关的一些讨论
  - <https://stackoverflow.com/questions/2488646/why-are-side-effects-modeled-as-monads-in-haskell>
  - <https://news.ycombinator.com/item?id=16419877>
  - <https://stackoverflow.com/questions/4063778/in-what-sense-is-the-io-monad-pure>
  - <https://stackoverflow.com/questions/41829618/functional-programming-where-does-the-side-effect-actually-happen>
* 其他Moand
  - <https://wiki.haskell.org/All_About_Monads>
  - [详解函数式编程之Monad](https://netcan.github.io/2020/09/30/%E8%AF%A6%E8%A7%A3%E5%87%BD%E6%95%B0%E5%BC%8F%E7%BC%96%E7%A8%8B%E4%B9%8BMonad/)
