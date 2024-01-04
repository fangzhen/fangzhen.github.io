
https://users.rust-lang.org/t/similar-items-in-core-and-std/60167/3

> std re-exports everything that core and alloc contain (but there's also things in std that only std contains.) Unless you're writing a no_std crate, you only need to worry about & use std. The “similar” items are actually exactly the same items, there's no difference.

## panic
### 错误处理
大概几类
1. 通过Option和Result或类似机制，通过检查返回值处理；
2. 通过panic!机制
3. 程序直接退出(相当于没有处理)

### panic
https://rustc-dev-guide.rust-lang.org/panic-implementation.html
rust中的panic实现

大概两个步骤：
1. 执行panic!宏
   core和std中分别定义了panic!宏，在默认的实现下，core中的panic实现最终也需要调用std中的实现，以保证一致性。
   调用实现了#[panic_handler] Attribute的函数进行panic处理，如果使用no_std，就需要自己定义该函数。
   panic_handler的返回类型是`!`，意味着不会返回，一般情况下最终应该是退出当前任务(线程)。
2. panic运行时
   std定义的panic_handler调用到panic运行时。rust提供了两个实现 panic_abort和panic_unwind。通过Cargo.toml或target json可以选择使用哪个。
   panic_abort比较简单，直接abort
   panic_unwind的实现就涉及到stack unwinding。如果panic 策略选择unwinding，还需要实现eh_personality language item。如果不用std，就需要自己实现。
   在unwinding路径下，可以通过`catch_unwind`来处理panic，而不必让panic导致整个线程退出。rust文档不建议利用这个方式实现try-catch的功能。catch_unwind的一个场景是ffi时，其他代码调用rust代码时，在rust代码边界使用。因为unwinding没有标准ABI，扩语言的情况下是未定义行为。
   `main`函数本身也wrap在`catch_unwind`内。

> This code is responsible for unwinding the stack, running any 'landing pads' associated with each frame (currently, running destructors), and transferring control to the `catch_unwind` frame.


https://doc.rust-lang.org/core/
https://doc.rust-lang.org/1.2.0/std/rt/unwind/index.html
https://doc.rust-lang.org/nomicon/unwinding.html
https://doc.rust-lang.org/std/panic/fn.catch_unwind.html
personality这个命名应该来自于gcc
  https://www.reddit.com/r/rust/comments/estvau/til_why_the_eh_personality_language_item_is/
  https://doc.rust-lang.org/1.2.0/std/rt/unwind/index.html

c++ unwinding：
https://stackoverflow.com/questions/2331316/what-is-stack-unwinding
https://www.bogotobogo.com/cplusplus/stackunwinding.php

## error[E0793]: reference to packed field is unaligned

错误代码示例，来自<https://doc.rust-lang.org/stable/error_codes/E0793.html>
```rust
use core::ptr::addr_of;
fn main() {
    #[repr(packed(2))]
    struct A {
        b: u32,
        c: u16,
        f: u8,
    }
    let a = A{b:100, c: 3, f: 1};
    let pb = (addr_of!(a.b)) as * mut u32; // 可以创建raw pointer
    &a.c; // pass
    &a.f; // pass
    &a.b; // error，编译错误信息见下面
    unsafe{&mut *pb}; //可以编译，但是UB
}
```

```
error[E0793]: reference to packed field is unaligned
  --> src/main.rs:14:5
   |
14 |     &a.b;
   |     ^^^^
   |
   = note: packed structs are only aligned by one byte, and many modern architectures penalize unaligned field accesses
   = note: creating a misaligned reference is undefined behavior (even if that reference is never dereferenced)
   = help: copy the field contents to a local variable, or replace the reference with a raw pointer and use `read_unaligned`/`write_unaligned` (loads and stores via `*p` must be properly aligned even when using raw pointers)

For more information about this error, try `rustc --explain E0793`.
```

这个错误本身的规则比较容易理解，对packed struct的字段的引用是未定义行为。有几个点值得注意：
1. 字段本身的类型的align大于packed指定的对齐时，才会错误，例如上面示例中，只有`&a.b`有错误，而`&a.f` `&a.f`是没问题的。
1. 创建misaligned reference就是UB，即使没有解引用。
1. unsafe 块中也会编译报错；但是对于指针的访问是可以在unsafe中的，虽然也是UB。

a. 为什么对misalign的地址的访问会是UB？
   在大部分架构上，对不同内存对齐的访问效率是不同的，例如，处理器访问4字节对齐的地址可能比1字节对齐的地址更快。在某些架构上，甚至无法寻址1字节对齐的地址。
   因此，编译器会做一些优化来处理。例如对于需要4字节对齐寻址的架构，访问单字节(例如类型为u8)的数据时，编译器需要读取包含该地址的4字节，再从中提取出需要的字节，因此性能会受到很大影响。
   而对于4字节(如u32)的数据时，编译器4字节对齐存储，访问时就不需要额外处理。这基于一个假设，就是访问4字节数据时的地址也是4字节对齐的。
   但是指针理论上可以保存任何值，如果misaligned，就会出现UB。
b. rust中创建misaligned reference就是UB，即使没有解引用
   rust中的reference必须是合法的，保证无法创建misaligned reference可以保证语义的完整，以及避免不必要的复杂度。
c. reference to packed field is unaligned
   这是一个比第一条更加严格的限制。packed field不一定misaligned；反过来，保证不能直接创建packed field的引用，可以保证从field创建的引用是对齐的。
d. `#[repr(align(1))]`为什么不会导致misaligned pointer
   根据[rust文档](https://doc.rust-lang.org/reference/type-layout.html)，指定的align如果比不指定时默认的小，align不会生效。
   > For align, if the specified alignment is less than the alignment of the type without the align modifier, then the alignment is unaffected.

References：
- [Type Layout](https://doc.rust-lang.org/reference/type-layout.html)：rust中的type layout文档，也包括了repr的align和pack参数说明。
- [未定义行为](https://doc.rust-lang.org/reference/behavior-considered-undefined.html#places-based-on-misaligned-pointers)：rust中UB的说明，也包含了misaligned pointer的一些说明。
- 更多关于misaligned pointer
  - https://stackoverflow.com/questions/20183094/what-is-a-misaligned-pointer
- [rust中reference和pointer的区别](https://ntietz.com/blog/rust-references-vs-pointers/)：简单来说，两者的底层表示是一样的，都是保存了某块内存的地址；区别主要在于语义层面上。
- [E0793](https://doc.rust-lang.org/stable/error_codes/E0793.html)
