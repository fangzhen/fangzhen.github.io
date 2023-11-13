---
layout: post
title: 非严格语义与惰性求值
tags: ["lazy evaluation", "non-strict semantics"]
date: 2023-11-13
---

非严格语义(no-strict semantics)：即使一个表达式的某些子表达式没有值，该表达式也可以有值。

惰性求值(lazy evaluation)：只有当一个表达式的结果需要的时候，才会去求值该表达式。

例如，对于haskell代码：
```
noreturn :: Integer -> Integer
noreturn x = negate (noreturn x)
```

haskell中对于表达式 `elem 2 [2, 4, noreturn 5]`的值为true。

python中类似的代码，
```
def noreturn(x):
    while True:
        x = -x

    return x # not reached

```
`2 in [2,4,noreturn(5)]`无法计算出结果。

非严格语义意味着归约(求值)顺序是从外到内，而严格语义是从内到外。
归约顺序跟语义相关是因为：假如一个表达式无法正常结束(例如死循环或错误)，称为到bottom。从内到外的顺序意味这一定会执行到这个表达式，而且这个bottom会扩散到外部。而从外到内的归约，有些表达式可能会被外部归约省掉，而不会被求值，从而不会到bottom。

对于上述haskell表达式`elem 2 [2, 4, noreturn 5]`，可以使用惰性求值，依次`2, 4, noreturn 5`，然后在求值到2就有了结果，不需要继续求值；
理论上也可以并行求值子表达式，然后丢弃不需要的值，也可以实现非严格语义。例如对上面的表达式，`2, 4, noreturn 5`并行求值，这样在`noreturn 5`成功求值之前，也可以得到结果。
这两种方式都能实现非严格语义。

**惰性求值是一种操作语义，指表达式如何被求值。而非严格语义是一种指称语义，指表达式是否有值，以及值是什么，而不是值怎么计算出来。**

实践上，非严格语义一般用惰性求值来实现，所以在有些地方两者也会混用。

但是实际情况也有些微妙的地方。例如除了上述内外的求值顺序，还可能要考虑的是同级的求值顺序。
在haskell(的GHC 实现)中，`2 in [2,4,noreturn(5)]`是可以求值为True的，但`2 in [noreturn(5), 2, 4]`无法求值。实际的结果相当于前者是非严格语义，后者是严格语义。一般情况下，这种coner case不太需要考虑。

### 设计考量
1. 性能：
  惰性求值可以用[`thunk`](https://wiki.haskell.org/Thunk)来实现。thunk数据结构包含要计算表达式所需要的任何值，加上一个指向自己的指针。当结果实际需要时，求值引擎计算表达式的值，并用结果替换thunk，从而以后使用该chunk不用重复求值（[Sharing](https://wiki.haskell.org/Sharing)）。  
  惰性求值只有在需要时才去求值，但它不一定带来性能提升，相反，很多场景下带来的是性能下降。因为确定一个表达式什么时候以及是否需要求值(例如上述Thunk的实现)需要额外时间会带来额外的性能负担。另一方面，很多情况下，(经过优化的程序)在惰性求值的情况下，能最终省略的求值微不足道。

2. 非严格语义可以让你把数据的生产和消费分开，进而写出更简洁和可组合的代码。例如要构造一个素数序列，但定义时不确定会需要多少素数，在python中可以使用generator特性来定义素数序列，在haskell中就可以不需要额外特性。另外很多语言中对逻辑运算符的短路求值，也是相当于对逻辑运算符使用了非严格语义。

3. 惰性求值让我们可以处理无限或未定义的数据结构，只要我们不需要求值或处理这些部分。例如Y combinator的实现。

## References：
- https://wiki.haskell.org/Lazy_evaluation
- https://wiki.haskell.org/Non-strict_semantics
