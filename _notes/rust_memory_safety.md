---
layout: post
title: Rust与内存安全
tags: ["rust", “memory safety”]
date: 2024-08-14
---
* TOC
{:toc}

## 内存安全 Memory Safety
[内存安全](https://en.wikipedia.org/wiki/Memory_safety)是指软件在处理内存访问时避免出现各种软件缺陷和安全漏洞。
以下列出一些常见的内存安全问题：
- 地址非法
  * 越界读写
  * 空指针
  * use after free
- 内容非法
  * 未初始化
  * 整数溢出或截断
- 内存管理问题
  * 未释放：内存泄漏
  * Double free
  * 栈耗尽：例如无限递归或分配过大的数据结构
- 竞争：竞争条件本身不直接是内存安全问题，但是对共享内存的并发读写可能导致上述内存安全问题。例如对数据的非原子读写导致读取到错误的数据。

总体上来说，**内存安全问题是软件逻辑错误的一类，技术上来说，它的边界并非严格明确。归根结底，没有任何语言能让程序员只能写出“逻辑正确的”代码还保持足够的可用性。**
只是代码逻辑不正确时，人们发现有很多问题有一些共性，并给这些问题归类，而其中一些就是所谓的内存安全问题。

进一步，通过在语言层面的一些限制，可以避免一些这类问题。
但即使声称内存安全的语言也无法解决所有内存安全相关的问题：一方面，如上所说，内存安全问题没有明确边界；另一方面，针对具体问题的解决方案都会涉及语言特性的权衡。

但是大部分高级语言确实提供了很多的特性来尽量避免内存安全问题。
这些特性带来一定的内存安全保证，降低了程序员的心智负担，避免写出某些错误的代码。例如垃圾回收机制让程序员在大部分情况下不需要考虑内存回收。
但同时也会损失一些灵活性，使得某些逻辑无法实现。比如大部分自动GC的语言无法精确控制某个对象的回收时机；Rust中不允许多个可变引用，而多个可变引用在很多使用场景下不会有什么问题。在进行系统软件开发时，直接操作指针是必要的，但很多有一定内存安全保证的语言都不允许直接操作指针。

> 考虑到现实世界的复杂性，所谓正确逻辑或内存安全也不是绝对的。
> 比如： <https://pages.mtu.edu/~djbyrne/does_memory_leak.html>
> > This sparked and interesting memory for me.  I was once working with a
> > customer who was producing on-board software for a missile.  In my analysis
> > of the code, I pointed out that they had a number of problems with storage
> > leaks.  Imagine my surprise when the customers chief software engineer said
> > "Of course it leaks".  He went on to point out that they had calculated the
> > amount of memory the application would leak in the total possible flight time
> > for the missile and then doubled that number.  They added this much
> > additional memory to the hardware to "support" the leaks.  Since the missile
> > will explode when it hits it's target or at the end of it's flight, the
> > ultimate in garbage collection is performed without programmer intervention.

了解内存安全之后，下文从一些特性出发，稍微细致地展示这一特性与内存安全的关联。

## Rust 基本概念：值(value)/变量(variable)/引用/可变性/所有权
```rust
// example for mutable
#![allow(unused)]
fn main() {
    struct FancyNum {
        num: u8,
    }
    let immut_num = FancyNum { num: 5 };
    let mut fancy_num = immut_num;    // move ownership and new owner is mutable
    fancy_num = FancyNum { num: 6 };  // re-assign
    fancy_num.num = 7;  // change value
    let fancy_ref = &mut fancy_num; // *fancy_ref is mutable, but fancy_ref is immutable
    fancy_ref.num=7;  // re-assign. auto-deref to (*fancy_ref).num
    *fancy_ref = FancyNum { num: 6 }; // change value
    // fancy_ref = &fancy_num; // error: since fancy_ref is immutable.
}
```
`fancy_num`是变量，它的值是`FancyNum { num: 5 }`。值是实际分配到内存(栈或堆)的实体，变量只是代码中引用值的符号。通过赋值，值的所有权赋给了变量。同一时刻，值必须**有且仅有**一个所有者。
`&fancy_num`生成变量的引用。也可以这么理解，`&fancy_num`实际上是另外一个值，就是`fancy_num`的引用(指针)，只是这个指针的所有权在`fancy_ref`，跟指针所指向的值没有关系，所以引用不会导致所有权转移。safe rust保证引用必须是合法的，这是引用跟裸指针的主要区别。

immutable有几个不同层面的含义：
- 对于变量：变量不可以重新赋值；以及变量对应的值**不可通过这个变量**改变。但是并不是变量对应的值不可修改（也就是说，不是常量）。由let后面的是否有mut指定。
- 对于引用：由&后是否有mut指定，是指能否通过这个引用修改对应变量的值。

另外，实现了[Copy Trait](https://doc.rust-lang.org/std/marker/trait.Copy.html)的类型在赋值时是copy语义，而不是默认的move语义。值被copy后变成了两个值，各自有一个所有者。

## 所有者
直接拿[E0506](https://doc.rust-lang.org/stable/error_codes/E0506.html)的示例：
```rust
#![allow(unused)]
fn main() {
struct FancyNum {
    num: u8,
}

let mut fancy_num = FancyNum { num: 5 };
let fancy_ref = &fancy_num;
fancy_num = FancyNum { num: 6 }; // error: cannot assign to `fancy_num` because it is borrowed
// let fancy_num = FancyNum { num: 6 }; // valid

println!("Num: {}, Ref: {}", fancy_num.num, fancy_ref.num);
}
```
因为`fancy_ref`没有`FancyNum{num: 5}`的所有权，如果允许`fancy_num`被重新赋值，`FancyNum{num: 5}`就没有所有者了，但它还有引用，不能drop掉。
不过需要注意一点的是shadow variable是可以的(代码中注释掉的那行)。可以理解为新旧变量是两个不同的变量，只是恰好使用的相同的名字，所以被shadow的变量在当前scope中还存在。
可以把引用理解成对变量的引用而不是变量背后的值的引用，当然从引用可以访问到背后的值，但是要通过引用的变量访问，而不是从引用直接访问。
当引用存在时，变量和值的拥有关系不能变化（变量不能拥有另外一个值或不再拥有值）。


Rust通过所有权来控制值的释放，当所有者离开作用域时，值会被drop。**这样把值的合法性判断转变成了所有者作用域的计算。**
这里的值不仅包含栈上分配的值，也包含堆上分配的值。

然而，有些情况下同一个值需要有多个所有者，因为在不同的情况下，释放值的时机可能不同，而在编译时，我们不知道哪个分支最后释放。

Rust语法上要求每个值有且只有一个所有者，编译器根据所有者变量的作用域来判断值的合法性。
另一方面我们希望在逻辑上实现多个所有者，当所有所有者都离开作用域后，值才不合法。
但语言本身的语法要求不能变。智能指针Rc是一个解决方案，它把实际值封装在`Rc`类型的变量。
借用[rust book](https://doc.rust-lang.org/book/ch15-04-rc.html)的例子：

```rust
enum List {
    Cons(i32, Rc<List>),
    Nil,
}

use crate::List::{Cons, Nil};
use std::rc::Rc;

fn main() {
    let a = Rc::new(Cons(5, Rc::new(Cons(10, Rc::new(Nil)))));
    let b = Cons(3, Rc::clone(&a));
    let c = Cons(4, Rc::clone(&a));
}
```
![Rust Rc](../assets/static/rust/trpl15-03.svg)

通过把链表元素(`i32`值)封装在`Rc`中，实现了逻辑上对`5`这个元素的多个所有者。但语法层面，每个`Rc<T>`类型本身是一个普通类型，编译器不需要特殊的所有权规则。每个`Rc`类型的值有一个`Rc`类型的变量做所有者。
通过`Rc`的内部实现逻辑在运行时保证通过`Rc`访问内部值时都是合法的，而且在某个内部值的所有`Rc`都drop时才drop掉内部值，也就在逻辑上实现了内部值的多所有者。
即使不实际看实现代码，也能反推出来，`Rc`的内部实现一定包含unsafe代码。

**总的来说，Rust编译器通过单一所有者的作用域判断对应值的合法性以及何时drop值。基于此，运行时代码可以(通过unsafe代码)把值封装在不同的智能指针中，实现需要的逻辑。**微妙的点在于，语言与编译器的行为(例如判断所有权、何时drop)是确定的，从而智能指针的行为（根据其实现）也是确定和受限的（受限于语言或编译器允许的范围，例如编译器调用drop的时机是无法修改的，能做的只是对Drop Trait的不同实现）。

## 生命周期
Rust中根据所有者的作用域决定值的合法性，而引用对值没有所有权。
因此Rust中每个引用都有生命周期，在其生命周期中，引用是合法的。
Rust编译器通过保证引用变量的作用域不能超出引用的生命周期来避免悬垂引用，保证引用总是合法的。

### 为什么需要生命周期标记
- 首先，**生命周期标记不是指定引用的生命周期，因为本质上(最长的)生命周期是由被引用的变量决定的**。
- 其次，理论上，个人认为即使没有生命周期标记，编译器也可以在编译期进行（不弱于当前有标记的）生命周期检查，避免不合法引用。当然可能实现上会更复杂。
- 最后，函数和结构体的生命周期标记更多是语言设计的选择。

接下来具体解释最后一点。

**函数**

对函数来说，生命周期标记实际上是函数签名的一部分，函数调用者不需要关注函数具体实现，就能根据函数签名知道返回值与参数的生命周期关系。这对于程序员是非常重要的。
想象一下如下调用，如果函数签名没有生命周期标记，程序员不知道`r`的生命周期（除非仔细地检查实现），那后面代码对`r`的使用也受影响。
而且`foo`的内部实现变化也可能影响到`r`的生命周期。
```rust
// function definition without lifetime annotation
// fn foo(x: &str, y: &str, z: &str) -> &str
let r = foo(&s1, &s2, &s3)
// lifetime of `r` is not clear to programmer, even compiler knows it.
```
另外，lifetime elision也是根据函数签名来推断生命周期标记，只是起到语法糖的作用。

**结构体**

对struct来说，因为引用字段的生命周期和struct变量本身的作用域可能不同，
而包含引用字段的struct实例作用域不能超出它的引用类型字段的生命周期，否则就会造成悬垂引用。
因此Rust从语法上要求结构体中必须有显式生命周期标记，故意提醒程序员不应轻易在结构体中使用引用。

另外，当struct用于函数签名时，由于函数签名中的生命周期标记是必要的，那就要求struct的每个引用字段都要有生命周期标记（因为返回值的生命周期可能与某个引用字段相同）。

参考：
- <https://www.reddit.com/r/rust/comments/y37h8u/why_does_rust_require_explicit_lifetimes/>
- <https://users.rust-lang.org/t/why-we-need-lifetime-annotation-in-a-struct/50495/9>

#### 理解生命周期标记语法
有了上面的铺垫，就更容易理解生命周期标记语法了。
* 对于函数来说，编译器通过生命周期标记推断返回值的生命周期。

  **对引用变量赋值确定了标记代表的生命周期**，例如检查x y的实参确定'a代表的lifetime是两者lifetime的重合部分，也就确定了返回值的生命周期。

  ```
  fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
      if x.len() > y.len() {
          x
      } else {
          y
      }
  }
  ```

* 对于struct，
比如下面的例子中，`announce_and_return_part`方法返回值的lifetime，如果不显式标记的话，因为lifetime elision，会跟`&self`相同，
但是因为返回的是`self.part`，我们可以标记为`'a`。这也是struct需要生命周期标记的原因，否则无法给方法的返回值指定为跟`self.part`相同的生命周期。

  注意`'a >= 'x`，因为struct实例的作用域(对应引用的生命周期)不会超出引用字段的生命周期。
另外`part`和`part3`使用了相同的生命周期标记，类似函数两个参数使用相同的生命周期标记，struct实例化后，`'a`的实际值取两者较小者。

  ```rust
  struct ImportantExcerpt<'a, 'b> {
      part: &'a str,
      part2: &'b str,
      part3: &'a str,
  }
  impl<'a, 'b> ImportantExcerpt<'a, 'b> {
  //  fn announce_and_return_part (&self, announcement: &str) -> &str { //compile error. without lifetime annotation, lifetime of return value is lifetime of self, instead of self.part
      fn announce_and_return_part<'x> (&'x self, announcement: & str) -> &'a str {
          println!("Attention please: {announcement}");
          self.part
      }
  }
  fn main() {
      let mut p = "tmp";
      {
          let mut i = ImportantExcerpt { part: "foo" , part2: "bar", part3: "baz"};
          p = i.announce_and_return_part("xxx");
      }
      println!("Returned: {p}")
  }
  ```

### 对Lifetime Elision的一点说明
Rust会根据一些内置的模式自动推断引用的生命周期(Lifetime Elision)，如果代码符合这些模式，就可以省略生命周期的指定。
但是自动推断的生命周期可能不是实际代码逻辑的需要，比如下面代码，如果`return_static`返回值不加`’static`声明，编译会报错，
因为编译器会自动标注为 `fn return_static(k: &'a str) -> &'a str`。
```rust
use std::thread;

fn return_static(k: &str) -> &'static str{
    if k == "hello" {
        return "world";
    } else {
        return "foo";
    }
}

fn main() {
    let k = String::from("hello");
    let result = return_static(&k);
    thread::spawn(move|| println!("The result is: {result}"));
}
```

## 值最多一个写者
Rust借用规则的结果是同一时刻，某个值最多只能有一个写者，而且写者是排它的。借用规则本质上可以理解为“读写锁”模式，为当通过一个变量可以修改某个值时(不管这个变量直接对应该值还是可以通过解引用对应该值)，这个变量便需要持有该值的写锁，否则持有读锁。锁的持有范围就是变量的作用域。

### 带来限制
一方面，这个规则可能带来一些限制，导致有些逻辑正确的代码无法编译。
例如在下面的示例代码中，编译会报错。但实际上，分析代码对`d`的使用，理论上不会有问题。

```rust
fn do_two<F, G>(mut c1: F, mut c2: G)
    where F: FnMut(), G: FnMut(){
    c1();
    c2();
}
fn mut_test(){
    let mut d = 1;
    let c1 = || d += 2;
    let c2 = || d *= 2;
    do_two(c1, c2);
}

fn main() {
    mut_test()
}
```

```
   Compiling playground v0.0.1 (/playground)
error[E0499]: cannot borrow `d` as mutable more than once at a time
  --> src/main.rs:21:14
   |
20 |     let c1 = || d += 2;
   |              -- - first borrow occurs due to use of `d` in closure
   |              |
   |              first mutable borrow occurs here
21 |     let c2 = || d *= 2;
   |              ^^ - second borrow occurs due to use of `d` in closure
   |              |
   |              second mutable borrow occurs here
22 |     do_two(c1, c2);
   |            -- first borrow later used here

For more information about this error, try `rustc --explain E0499`.
error: could not compile `playground` (bin "playground") due to 1 previous error
```

### 避免内存安全问题
另一方面，如果允许多个可变引用，即使在没有并发的情况下，也可能带来内存安全问题，下面举几个例子。

**防止访问枚举类型时出现类型不一致**

```
fn main() {
    enum StringOrInt {
        Str(String),
        Int(i64),
    }

    let mut x = StringOrInt::Str("Hi!".to_string()); // Create an instance of the `Str` variant with associated string "Hi!"
    let y = &mut x; // Create a mutable alias to x

    if let StringOrInt::Str(ref insides) = x {
        // If x is a `Str`, assign its inner data to the variable `insides`
        *y = StringOrInt::Int(1); // Set `*y` to `Int(1), therefore setting `x` to `Int(1)` too
        println!("x says: {}", insides); // Uh oh!
    }
}
```
  编译报错如下：
```
   Compiling playground v0.0.1 (/playground)
error[E0503]: cannot use `x` because it was mutably borrowed
  --> src/main.rs:10:12
   |
8  |     let y = &mut x; // Create a mutable alias to x
   |             ------ `x` is borrowed here
9  |
10 |     if let StringOrInt::Str(ref insides) = x {
   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ use of borrowed `x`
11 |         // If x is a `Str`, assign its inner data to the variable `insides`
12 |         *y = StringOrInt::Int(1); // Set `*y` to `Int(1), therefore setting `x` to `Int(1)` too
   |         -- borrow later used here

error[E0502]: cannot borrow `x.0` as immutable because it is also borrowed as mutable
  --> src/main.rs:10:29
   |
8  |     let y = &mut x; // Create a mutable alias to x
   |             ------ mutable borrow occurs here
9  |
10 |     if let StringOrInt::Str(ref insides) = x {
   |                             ^^^^^^^^^^^ immutable borrow occurs here
11 |         // If x is a `Str`, assign its inner data to the variable `insides`
12 |         *y = StringOrInt::Int(1); // Set `*y` to `Int(1), therefore setting `x` to `Int(1)` too
   |         -- mutable borrow later used here

Some errors have detailed explanations: E0502, E0503.
For more information about an error, try `rustc --explain E0502`.
error: could not compile `playground` (bin "playground") due to 2 previous errors
```

如果没有编译器对mutable reference的检查，上述代码在`*y = StringOrInt::Int(1)`这一行使得枚举的底层数据变成了Int，而下一行读取`insides`时还会按照String读取，就可能引起segfault。

**特定的swap实现**：
作为另外一个高层语义的例子，一个不需要中间变量交换两个整数值的实现如下：
```
fn swap(&mut x, &mut y) {
    *x = *x ^ *y;
    *y = *x ^ *y;
    *x = *x ^ *y;
}
```
这个实现有个限制是两个参数不能引用同一个值，否则结果是错误的。在rust中因为不允许多个可变引用，所以直接规避掉这个问题。
我更愿意把这种例子看成是不允许可变引用带来的副作用，它使得很多高层的不变式更容易实现。

**迭代时修改数据**：
在迭代时修改底层数据会导致迭代失效，可能导致未定义行为或非预期行为。
有些语言如java会进行runtime检查，有些如python可能会造成非预期的结果，但在rust中通过借用检查会导致编译失败。

**多个可变引用即使在没有数据访问的情况下也是UB**
根据[禁用`static mut`的引用](https://github.com/rust-lang/rust/issues/114447#issuecomment-2137998517)等issue里的讨论，多个可变引用即使在没有数据访问的情况下也是UB。在Rust [用户论坛上](https://users.rust-lang.org/t/why-multiple-mutable-reference-even-without-data-access-is-ub/118152)讨论了一下原因.简单总结一下，语言这么设计必然有背后的权衡。
* 首先，有数据访问的情况下不允许多个可变引用好处很多（比如本节上文的例子）。从而编译器也会基于没有多个可变引用的前提做各种可能的优化。实际程序中，有多个可变引用但没有数据访问的情况非常少，语言设计没必要为这种没用的极端情况而增加内存模型的复杂度。
* 编译器的实际实现中，[@farnz](https://users.rust-lang.org/t/why-multiple-mutable-reference-even-without-data-access-is-ub/118152/6)举了一个优化的例子。
  例如下面的代码片段，理论上编译器可能把bar函数对引用的操作转化为直接对值的操作，编译器可以把`x`的值在`foo`被调用之前就加载到寄存器。
  如果`foo`需要的是`x`的可变引用，编译器如果还这么优化，就可能产生竞争，因为`foo`调用之后，`x`的值可能变化。
  这就说明基于可变引用的作用域不能与其他引用重叠可以进行一些优化。

  继续看`foo(&mut x)`和`bar(r2)`两个调用不一定有冲突。因为`foo(&mut x)`不一定会对`x`做修改。但对编译器来说，如果在编译优化`main`时还要深入分析被调用函数的实际实现来决定优化逻辑，几乎不可能。回到上一条，语言设计中也是有权衡，没必要为了一些极端情况增加过多复杂性；况且有些情况静态分析根本不可能。
  ```rust
  fn bar(a: &i32) {
      a;
  }
  fn main() {
      let x = 4;
      let r2 = &x;
      foo(&x); // foo(&mut x);
      bar(r2);
  }
  ```


总的来说，RWLock机制的借用检查会带来一些易用性上的限制，但也会防止在某些情况下写出内存不安全或逻辑不正确的代码。
RWLock使得一些invariant成为可能(如上面代码片段中`insides`一直是String类型，而不会变成Int类型；迭代时底层数据集不会变)，那么其他rust代码可以基于这些不变式来设计；编译器可以基于此进行优化。否则没有RwLock带来的invariant，要实现相同的功能或约定(如使用Enum时避免非法引用；迭代时不能修改底层数据)就需要其他可能更复杂，性能更差的方案，如运行时检查。

## Closure
闭包在定义时就会捕获环境，而闭包的调用可能在定义后的任何地方。而函数只能在调用时使用调用时的环境。

技术上，可以把闭包当成一个实例化的结构体，结构体包含一个方法。当闭包被定义时，编译器自动生成一个结构体实例；闭包调用时，相当于调用结构体的方法。
1. 结构体的字段。每个字段对应闭包中使用的值，根据该值在闭包中如何使用以及是否move来确定结构体中该字段的类型：不可变引用，可变引用，获取所有权。
   即**被闭包捕获的环境**定义了该结构体。
2. 结构体方法。相比闭包定义，方法还有一个额外的参数是结构体实例自己（self）。根据**结构体实例（self）在闭包中如何使用**确定该参数的类型，这也是需要三个`Fn*` Trait的原因(注意move不影响这里的判断逻辑)。
   * 如果所有字段都只需要不可变引用或者没有使用任何字段，那么只需要传结构体的不可变引用，对应`Fn` Trait。它的函数签名是`extern "rust-call" fn call(&self, args: Args) -> Self::Output`；
   * 否则，如果有字段需要可变引用，那么需要传结构体的可变引用，对应`FnMut` Trait。函数签名是`extern "rust-call" fn call_mut(&mut self, args: Args) -> Self::Output`；
   * 否则，如果有字段需要获取所有权，那么需要把结构体所有权转移到方法，对应`FnOnce` Trait。函数签名是`extern "rust-call" fn call_once(self, args: Args) -> Self::Output`；

可以参考下面代码和注释更具体的理解。
``` rust
#![allow(unused)]
fn main() {
    let mut x: usize = 1;
    let mut c_fnmut = || x += 2; // corresponding struct: s_fnmut = (&mut x)
    //x+=2;   // error, since x is mutably borrowed before and used later.
    let t = &mut c_fnmut; // used here
    t(); // t itself can be immutable while t is a mutable reference of closure.
    // (&c_fnmut)(); // error, since fnmut need a mutable reference of closure

    let mut y: usize = 1;
    let mut c_fnmut = move || y += 2; // corresponding struct: s_fnmut = (y)
    //y+=2;   // error, since x is moved
    c_fnmut();
    c_fnmut(); // although y is moved into closure, the closure is FnMut, not FnOnce

    let mut v = vec![];
    let value = String::from("closure called");
    let c_fnonce = || v.push(value); // corresponding struct: s_fnonce = (value)
    //println!("{}", value); // error: since value is moved
    c_fnonce();
    // c_fnonce(); // error: c_fnonce is moved in first call.
}
```

通过上面分析可以看出来，闭包的实现并不需要任何针对闭包规定特殊的所有权或借用规则，就可以实现和普通代码相同的内存安全保证。

## Pin
所有权和借用检查主要解决内存何时分配与释放，以及避免只读引用使用过程中数据被修改。
智能指针，实现类似的语义保证，但是放宽部分限制。比如Rc，可以让单一value语义上有多个只读owner，在所有owner都离开作用域才释放内存(单一owner+多个只读引用无法达成同样的效果)。
这些在一定程度上都是“通用”的语义，根据变量或引用的性质(比如变量是否是所有者，引用可变或不可变)而设置的规则。
**维护的*不变式*可以(不严格地)概括为引用是合法的**。

程序逻辑中一个可能的*不变式*是值的内存位置改变不会影响值的语义。比如一个usize类型的值，通过赋值拷贝一份仍表示同样的数字。Rust编译器基于该不变式，会移动值(比如实现了Copy Trait的类型赋值; `mem::swap()`)。

但是在实际程序逻辑中，值的内存位置可能影响*更高层的语义*。例如
- 定义一个数据结构，它的值是它自己的内存地址。当值被移动到其他内存位置时，这个值就不合法了，如果把值当作地址去解引用，就会出现问题。
- 在FFI中，把值的指针传给了C代码的情况下，值如果被移动，会造成指针不合法。

这种跟内存位置有关的高层语义会涉及到对裸指针的解引用操作(因为跟内存地址有关)，一定会存在某些unsafe代码。

满足高层语义的正确性，有两个选择：
1. 程序逻辑中每次移动值，都修正值的内容，维护语义的正确；
2. 程序中不移动该值。

但Rust不会在移动值后通知用户程序，因此第一种选择在Rust中无法实现。
要使第二种选择理论上，Rust**不能任意move值**。如果没有语义上的move，编译器不能自己插入内存move的指令。换句话说，**编译器何时move值需要是可预测的。**
引用[pin](https://doc.rust-lang.org/std/pin/index.html)文档的说法：the compiler will not insert memory moves where no semantic move has occurred。

Rust提供了`std::pin`来帮助实现第二种选择。
使用`Pin<Ptr>`在指针外面包了一层。`Pin`不需要任何编译器特殊支持，但是需要使用者遵守库API的约定，维护值不会移动的不变式。
对Pin的更详细设计思想和使用方法请参考[文档](https://doc.rust-lang.org/std/pin/index.html)。

使用`std::pin`可以以统一的模式来处理需要Pin的数据结构；但理论上，通过小心实现程序逻辑，我们可以精细地按需实现想要的高层语义，包括不要移动值。

## 并发
Rust借用规则通过对变量作用域的静态分析，保证了一个值的唯一写者和读者作用域不会重叠。

背后的逻辑可以理解为：
把值作为临界资源，每个对值进行访问的变量的作用域作为临界区。进出临界区进行锁的获取与释放。如果是immutable，只需要读锁，否则需要写锁。
Rust的借用规则保证写者的作用域跟其他写者或读者都没有重叠，那么进入临界区时就一定可以拿到锁。
因此，**如果没有内部可变性**，静态分析就能保证运行时对值访问的RWLock模式，而**实际并不需要锁的获取与释放**

更具体地说，作用域以如下逻辑对应临界区（先不考虑static mut，对static mut的访问都是unsafe的）：
- 对于同步单线程的情况，某个作用域内代码是顺序执行的，不存在执行流从作用域离开又回来的情况，可以对应临界区；
- 对于async的单线程的情况，本质上来讲，async类似语法糖，编译器在async函数调用时自动生成Future对象，对Future对象的规则没什么特殊之处，跟同步单线程一样。
- 对于多线程的情况，Rust中，传给新线程的闭包生命周期是static的，因此闭包捕获环境时，
  * 如果是局部变量，就需要把所有权转移给闭包，闭包定义之后的代码无法获取到引用，相当于闭包定义前定义的变量的作用域到闭包定义为止；
    传给新线程的闭包可能在新线程启动后才可能执行，新旧线程的临界区在时间上没有重叠。
  * 如果是static变量，safe代码都是只读，临界区不会冲突；

```
pub fn spawn<F, T>(f: F) -> JoinHandle<T>
where
    F: FnOnce() -> T + Send + 'static,
    T: Send + 'static,
```

但是如果没有内部可变性，多线程只能有一个线程可以修改值，而且在线程创建时就确定了，这大大限制了多线程编程的能力。
在单线程下，如果没有内部可变性，对语言的限制也太多了，所以才有像`Rc`也需要内部可变性来突破默认借用规则的限制。

有内部可变性的情况下，就需要更多机制来保证运行时的RWLock模式成立。例如前面讲过的`Rc`，它的内部可变性在与对内部计数器的修改。
这时候，单线程与多线程就有区别了。在单线程下能保证运行时RWLock模式成立的实现，不意味着多线程下也成立。
还是以`Rc`为例，如果对内部计数器的修改不是原子的，多线程情况下就可能产生竞争。

因此，Rust引入了Send和Sync两个marker Trait，根据[rust nomicon](https://doc.rust-lang.org/nomicon/send-and-sync.html):
* A type is Send if it is safe to send it to another thread.
* A type is Sync if it is safe to share between threads (T is Sync if and only if &T is Send).

具体来解释一下：
- Send允许所有权转移到另一个线程。线程本身并不是所有者，而是线程执行的代码需要获取值的所有权，就认为是值被send给了某个线程。更具象地说，传给`spawn`的闭包捕获了某个变量的所有权，就是该变量对应的值被Send到了新的线程。
- 如何判断safe：个人认为safe主要有两类要求，使得多线程下保持其(跟单线程环境同样的)内部一致性，或者说保持其类型的不变式。
  * 通用要求：多线程访问时可以保证RWLock模式；
  * 个性要求：类型本身额外的语义约束。
- 无法说Send或Sync谁的要求更强。如果类型Sync，该类型的值可以在多个线程安全地并发访问；而Send要求可以转移所有权，不要求并发访问。
  一般来说，如果判断一个类型是否safe，只需要第一个RWLock要求，那么Sync的类型应该都Send。

一些例子：
- `!Send + !Sync`: `Rc`，因为其计数器的访问不是原子的。
- `!Send + Sync`: `MutexGuard`，是少有的Sync但不Send的例子。MutexGuard意味着当前线程持有锁，当变量移出作用域时，drop被调用，释放锁。它的语义要求获取锁和持有锁必须在同一线程中，所以`MutexGuard`类型的对象的所有者不能转移到其他线程。(技术上说，所有者所在的线程才会调用drop，该线程需要和持有锁的线程相同。)
- `Send + Sync`:
    * `Arc<T>`：当`T` `Send + Sync`时，`Arc<T>`才`Send + Sync`。首先`Arc`相比`Rc`，只是防止了对它自己的计数器访问的竞争，并不会影响它内部T类型值的访问。也就是说它只保证了自己计数器的线程安全，不能保证它的数据T的线程安全。
      - 为什么`Arc<T>`是`Send`和`Sync`，都要求`T` `Send+Sync`？
    因为不同线程克隆的`Arc<T>`共享同一个T类型的对象，因此要使`Arc<T>` `Send`，当`Arc<T>`的值被转移到另一个线程后，对变量解引用获取`&T`，因此需要`&T` `Send`，即`T` `Sync`。
    `Arc::into_inner(this: Arc<T, A>) -> Option<T>`等方法可以从`Arc`中抽取出内部值，也就是把ownership从`Arc`转移出来。因此类型`T`需要`Send`，才能进行所有权转移。
    另外当`Arc<T>` drop时，如果内部值没有强引用，内部值也需要drop，这时候也需要内部值的所有权，所以也需要`T` `Send`。
    同理，`Arc<T>` `Sync`也需要`T` `Send+Sync`。
    * `Mutex<T>` 在`T` `Send`的时候才`Send`和`Sync`。Mutex保证了内部值的访问都需要先拿到锁，所以不会有访问冲突。只要`T` `Send`，`T`的值的所有权可以在线程间转移，那么`T`就允许在不同线程间互斥访问。
- `Send + !Sync`： `RefCell<T>`没有对`T`类型的值的访问进行同步，只是提供了内部可变性，因此多线程如果可以同时访问，会造成竞争。但`RefCell`可以从一个线程Send到另一个线程，在新线程中还是独占访问，不存在并发问题。

`Arc`、`Rc`、`Mutex`、`RefCell`对`Send`、`Sync`trait的声明如下，供参考：
```rust
impl<T, A> Send for Arc<T, A>
where
    T: Sync + Send + ?Sized,
    A: Allocator + Send,
impl<T, A> Sync for Arc<T, A>
where
    T: Sync + Send + ?Sized,
    A: Allocator + Sync,

impl<T: ?Sized + Send> Send for Mutex<T>
impl<T: ?Sized + Send> Sync for Mutex<T>


impl<T, A> !Send for Rc<T, A>
where
    A: Allocator,
    T: ?Sized,
impl<T, A> !Sync for Rc<T, A>
where
    A: Allocator,
    T: ?Sized,

impl<T> Send for RefCell<T>
where
    T: Send + ?Sized,
1.0.0 · source§
impl<T> !Sync for RefCell<T>
where
    T: ?Sized,
```

一个简单的例子说明使用Arc+Mutex实现对内部整数的多线程访问。
```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0));
    let mut handles = vec![];

    for _ in 0..10 {
        let counter = Arc::clone(&counter);
        let handle = thread::spawn(move || {
            let mut num = counter.lock().unwrap();

            *num += 1;
        });
        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("Result: {}", *counter.lock().unwrap());
}
```

对于一般的数据结构设计来说，防止竞争主要有两种思路：
1. 原子类型。类似Arc之于Rc，把非线程安全的数据类型封装为另一个线程安全的对等类型。
2. 通过一个专门的wrap类型来控制数据访问。如通过Mutex<T>来实现对类型T数据的互斥访问，这样不需要对每个类型都创建一个对应的原子类型。
   这样传到另一个线程的是实现了Send的类型的实例，而不是被包裹的原始数据。

最后，`Send`和`Sync`是自动推断的trait，但是推断的`Send`和`Sync`不一定是正确的。理论上就不可能直接推断出来，但实践上，如果不是要实现智能指针和并发相关的数据结构（这种情况下，内部实现一般也不涉及到跟Send/Sync语义相关的逻辑），推断出来的一般都是正确的。引用Rust book：
> Send and Sync are also automatically derived traits. This means that, unlike every other trait, if a type is composed entirely of Send or Sync types, then it is Send or Sync. Almost all primitives are Send and Sync, and as a consequence pretty much all types you'll ever interact with are Send and Sync.

> Note that in and of itself it is impossible to incorrectly derive Send and Sync. Only types that are ascribed special meaning by other unsafe code can possibly cause trouble by being incorrectly Send or Sync.

## 关于static mut
### Rust中不同类型数据的分配与回收
Rust的内存分配与回收主要依赖所有者机制。通常情况下值在创建时进行内存分配，在所有者离开作用域后回收内存。通过自定义`drop`方法可以控制所有者离开作用域时的行为，实现特定的逻辑，如`Rc`、`Box`。另外与所有者机制近乎“平行”的方式还有两类：
- 静态编译进binary数据段(.bss等)的数据，例如
  * 语言实现的选择，如字符串字面量；
  * 业务逻辑上，设计成全局变量更自然。但是如果没有全局变量，大部分可以转为局部变量+参数传递的方式；
  * （如操作系统启动早期阶段）没有heap allocator，stack大小受限的情况下，大块内存编译进binary是一种选择。（如memblock系统的ALL_MEMBLOCK）；
  * 数据可能被外部访问，也就是把某块数据当成了某种二进制接口。例如bootloader引导操作系统kernel时，需要给操作系统传递一些信息。这个setup header可以链接到kernel binary的某个offset，bootloader可以直接写入。当kernel拿到控制权后，可以读取bootloader传递的数据；
  * 跟其他语言（如C）交互。
- 用户逻辑动态分配和释放，例如
  * 通过`std::alloc`的api分配和释放内存；（`Box` 等的实现也是这种方式，只不过标准库封装好了。）
  * 使用自定义的allocator进行分配和释放（如操作系统开发时）。
在Rust中访问这两类内存时，还是需要通过Rust的指针、引用等。例如第一类全局变量就可以通过`static`变量来访问。

### `static mut` 的问题及方案
所有对`static mut`变量及引用的使用都是unsafe的，主要原因是
1. 对于`static mut`变量，其作用域是全局，那对应的临界区就是整个程序。因为Rust允许多线程而且实际并没有锁，因此对`static mut`变量及其引用的使用必须是unsafe的。
2. 对`static mut`变量的引用和其他类型的引用在编译器角度没什么区别。上面讲到过，即使单线程，多个可变引用在Rust中也会引发UB。

[Rust 2024 Edition 已经禁止了直接引用`static mut`](https://github.com/rust-lang/rust/issues/114447)，推荐的方案是使用static + 内部可变性的类型，
如某种[cell类型](https://doc.rust-lang.org/core/cell/index.html)。

当然，只要有多线程修改全局共享变量的需求，问题就不可能自己神奇地消失。技术上，`&mut *ptr::addr_of_mut!(MY_STATIC_MUT)`可以直接替代 `&MY_STATIC_MUT`，原来多引用的问题依然存在。使用`UnsafeCell`也不能避免通过裸指针获取可变引用，原则上能做到和static mut同样的事情。
引用一些讨论中（
[Disallow *references* to static mut](https://github.com/rust-lang/rust/issues/114447)
[Consider deprecation of UB-happy static mut](https://github.com/rust-lang/rust/issues/53639)
[why-is-static-mut-bad](https://users.rust-lang.org/t/why-is-static-mut-bad/32888/2)
）的观点：
> >  Since you can get a *mut either way does it make any difference to safety?

> The differences are in whether you get a reference directly. *muts are allowed to alias, so you can make new ones all day long and keep them around -- the only problems are when you actually read or write through them. Whereas multiple independent live &muts at the same time is UB even without a data race. So that's the difference in footgun-ness.

> So it's basically a speed-bump. One can still write &mut *&raw mut STATIC, but one can also do &mut *STATIC.get() when using a non-mut UnsafeCell -- in unsafe code there'll always be enough rope for the user to hang themselves, but making them go through raw pointers should significantly reduce the risk of that happening accidentally.

> With the lint being tracked in #128794, I think we should close this issue: static mut in general is actually "fine", it's just 'static references that are so dangerous. Global mutable state is inherently dangerous, but it doesn't get fundamentally safer by using static S: SyncUnsafeCell instead of static mut. There might be some benefit to using &'static SyncUnsafeCell references instead of raw pointers, but not enough to fully deprecate static mut.

简单来说，使用内部可变类型的关键在于*不那么容易*引起UB。

在实际项目中具体如何使用，就没有一定之规了。**核心在于回到临界区的思考模式，知道Rust编译器/库层面帮我们避免了那些临界区竞争的可能，我们可以不用考虑；业务逻辑中还有那些可能有竞争，着力于思考这些竞争如何解决。**

有时候不能直接使用rust库的实现，例如`mutex`包含在std中，在`no_std`下无法使用；有的可能是业务逻辑不同，例如有些代码不可能有多线程并发访问，因此无需控制并发访问；或者可能性能上选择更优的方案。例如
1. `SyncOnceUnsafeCell`: 用于只set一次，后续都是获取不可变引用的变量
2. 通过`RefCell` 封装进新的struct。所有对内部变量的访问**都通过**该struct的pub方法。方法中注意不要多次获取内部变量的引用（例如可以在获取内部变量引用后调用内部变量的方法）。这样把可能的多次引用（会引起panic）都限制在struct的public方法中，易于避免问题以及排查问题。 在struct外部使用`get_inner/get_inner_mut`获取引用后及时销毁，避免在`get_inner/get_inner_mut`获取的引用作用域内把struct引用传到其他函数中。（因为进入被调用函数再追踪get_inner是否被重复调用几乎不可能。即使当时没有，未来随着代码演进也不一定没有，而未来代码修改时几乎不可能确切知道有没有reference）。

[2024 edition guide](https://doc.rust-lang.org/nightly/edition-guide/rust-2024/static-mut-references.html)关于禁用`static mut`引用的说明，包括问题原因以及替代方案等。
> Merely taking such a reference in violation of Rust's mutability XOR aliasing requirement has always been instantaneous undefined behavior, even if the reference is never read from or written to. Furthermore, upholding mutability XOR aliasing for a static mut **requires reasoning about your code globally**, which can be particularly difficult in the face of reentrancy and/or multithreading.

**Mutability XOR Aliasing**

## 杂项
### 在堆上创建对象
虽然Box用来作为heap上数据的指针，但是Box::new()会先在栈上创建数据，然后复制到堆上，因此并不够高效(虽然编译器有可能会优化)；而且当数据占用内存较多时，还有可能造成栈溢出。实际上，目前rust中没有safe的方法可以在创建时直接指定把数据放在堆上。

c++中，有[Placement new](https://en.cppreference.com/w/cpp/language/new#Placement_new)。
Rust 有个RFC在讨论:[Placement by Return](https://github.com/rust-lang/rfcs/pull/2884)

## 总结
归根结底，Rust的各种机制是语言设计的选择，其中有权衡和折中，没有银弹，没有完美的方案。即使是safe rust也不能保证完全没有内存安全问题。
对于程序员来说，重要的是理解背后的原理以及带来的好处和限制，充分利用语言特性，写出正确的内存安全的代码。

对于并发相关的问题，从并发模型中的临界区、RWLock的角度出发，对于理解Rust的借用和所有权机制以及Rust中各种智能指针、并发的设计很有益处。
理解Rust从语言机制的角度避免了哪些竞争条件，不同的库又解决了那些竞争的场景，同时带来了哪些限制，对于程序员在语言和库的基础上，实现正确的并发编程会有很大帮助。

## Reference
- https://stanford-cs242.github.io/f18/lectures/05-1-rust-memory-safety.html
- https://doc.rust-lang.org/book
- <https://www.reddit.com/r/rust/comments/11lmfg7/trying_to_understand_mutable_closures/>：为什么FnMut需要传mutable reference
- <https://manishearth.github.io/blog/2015/05/17/the-problem-with-shared-mutability/>
  > Aliasing with mutability in a sufficiently complex, single-threaded program is effectively the same thing as accessing data shared across multiple threads without a lock
- [Why impl Sync for Mutex requires T: Send](https://users.rust-lang.org/t/why-impl-sync-for-mutex-requires-t-send/12111): 解释中包含了回答者对Sync/Send的一些洞察，比较有启发性。
- <https://langdev.stackexchange.com/questions/2593/what-approaches-are-there-to-prevent-modifying-a-collection-while-iterating-over>
- <https://stackoverflow.com/questions/36136201/how-does-rust-guarantee-memory-safety-and-prevent-segfaults>
- <https://doc.rust-lang.org/nomicon/concurrency.html>
- <https://stackoverflow.com/questions/77934697/will-boxnew-make-a-copy-from-stack-to-heap>
- 未定义行为的一些参考：
  * <https://en.wikipedia.org/wiki/Undefined_behavior>
  * <https://en.wikipedia.org/wiki/Unspecified_behavior>
  * [GCC中实现定义行为的一个彩蛋](https://feross.org/gcc-ownage/)

  C/C++中，这种non-portable结构，大体是分为三类：Implementation-defined, unspecified, and undefined behavior.
  对于Implementation-defined行为，编译器必须选择一种行为并通过文档明确出来。例如整型的大小。
  对于unspecified行为，语言标准一般会给出一些可能的行为，编译器从中进行选择。例如c/c++中加法求值顺序。
  而Undefined行为一般是程序结构或数据的错误造成的，语言标准对于此类结构的具体实现没有任何要求。
