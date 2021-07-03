# rust & cargo 一些特性概述 & 参考索引

## edition
2015 2018 2021 https://doc.rust-lang.org/edition-guide/editions/index.html
edition 机制为了保证*后向兼容*。不同的edition可能有不兼容的修改。例如async在2018 edition变成关键字，在2015 edition可以作为普通变量名。通过在Cargo.toml中指定edition=2018，rust编译时会按照2018的语法来进行编译。
edition机制*不会保证前向兼容*。比如feature在stablize后，stable channel新版本的rust可以直接使用，但是旧版本仍不能用。

## Unstable
rust unstable reference: <https://doc.rust-lang.org/beta/unstable-book/>
三类：
1.  compiler flags
   通过-Z<flag>指定，例如-Zcodegen-backend=<path>
2. language features
   这些是编译器feature，通过 #![feature]指定。
   feature的列表在源码的`src/rustc_feature/`下，`accepted.rs`是已经stable的feature列表，`active.rs`是unstable的feature列表。随着rust的开发过程，有些feature会从unstable变成stable，参考<https://rustc-dev-guide.rust-lang.org/stabilization_guide.html>

3. library feature
   library feature是定义在rustc standard library的feature，使用`#[unstable]` 等attribute 定义。目前只支持 rust 源码树中的library定义。外部crate中的library不能自定义feature(<https://github.com/rust-lang/rfcs/issues/1491>)
   unstable 等attribute的使用以及stabilizing library feature参考 <https://rustc-dev-guide.rust-lang.org/stability.html>
   也是通过 #![feature]指定。

`error[E0734]: stability attributes may not be used outside of the standard library`

unstable feature不能用于stable channel。

```
error[E0554]: `#![feature]` may not be used on the stable release channel
```

cargo也有`unstable`和`feature`，跟这里的没有关系。

## attribute
<https://doc.rust-lang.org/reference/attributes.html>
attribute是一种通用的metadata，形如`#[Attr]`或`#！[Attr]`，编译时处理。分为四类
- Builtin attributes, 例如`cfg`，`test`， `derive`等。
- Macro attrbutes，通过`attribute macro`定义的attribute。
- Derive macro helper attributes，用于在`Derive macro`中定义额外attributes。
- Tool attributes，外部工具如`rustfmt`等定义。

## macros
<https://doc.rust-lang.org/reference/macros.html>
*编译时*扩展macro，并替换macro定义。rust中有两种方式定义macro：
1. `Macros by Example` define new syntax in a higher-level, declarative way.
   使用`macro_rules!`宏声明式来定义。`by example`可以理解为这种定义方式比较直观，以类似举例的方式来定义宏。
2. `Procedural Macros` define function-like macros, custom derives, and custom attributes using functions that operate on input tokens.
   这种定义方式直接处理`TokenStream`，输出新的`TokenStream`。分为三种：
   - Function-like macros - custom!(...)
   - Derive macros - #[derive(CustomDerive)]
   - Attribute macros - #[CustomAttribute]

## Derive
<https://doc.rust-lang.org/reference/attributes/derive.html>
`derive` attribute用于给数据结构自动生成item（例如方法等）。例如给struct生成Clone trait的方法。可以使用`Derive macro`给自己的tait定义额外的`derive`。

## conditional complication
<https://doc.rust-lang.org/reference/conditional-compilation.html>
条件编译的选项是在编译时确定和生效的。

### configuration options:
  形式可以是name或者k-v对，例如`unix`，`foo="bar"`
  rustc 通过`--cfg`参数指定。
  cargo.toml [feature] section中定义的feature或者可选依赖自动变成key是`feature=<feature>`的option。
  有一些预定义的option，如`target_arch`等。

### cfg语法
    cfg attribute： cfg expression还可以用于dependency
    cfg_attr attribute
    cfg macro

## cargo
<https://doc.rust-lang.org/cargo/index.html>
cargo 是rust的包管理器。用于包的依赖管理，编译，分发等。不是编译器。

### package manifest
<https://doc.rust-lang.org/cargo/reference/manifest.html>
package manifest指的是包中的cargo.toml文件，包含包的信息，例如名字，版本，依赖，target等
cargo targets是指cargo的build产物，如library, binary, example等。
除了这些target，很多时候平台相关的配置也称为target。例如平台相关的依赖，就是使用类似`[target.'cfg(unix)'.dependencies]`的section。平台相关的条件也通过<cfg> expression来指定。

### cargo configuration
<https://doc.rust-lang.org/cargo/reference/config.html>
除了cargo manifest, 还有一类配置文件，`config.toml`，称为configuration。cargo configuration可以定义在包级别，也可以定义在全局配置中，而cargo.toml只能定义在包级别。
个人理解，cargo configuration一般是对build过程本身的配置，例如cargo的命令aliases，网络代码，环境变量等。
[target] table 用于指定平台相关的设置。可以使用<cfg> expression 或者平台<triple>类进行匹配。

### package feature
<https://doc.rust-lang.org/cargo/reference/features.html>
cargo.toml中可以定义[feature] section，定义包的feature。可以在build或者添加依赖时指定feature。根据feature可以进行条件编译。例如`#[cfg(feature = "webp")]`

### cargo unstable feature
<https://doc.rust-lang.org/cargo/reference/unstable.html>
cargo unstable feature是指cargo本身的unstable feature。只有nightly channel的cargo可以使用。通过cargo 命令行 `-Z` 参数或者`config.toml`中[unstable] section指定。

### profile
<https://doc.rust-lang.org/cargo/reference/profiles.html>
profile提供一个修改编译参数等的方案。cargo有四个内置profile：`dev`, `release`, `test`, `bench`。默认会根据不同的cargo命令自动使用不同的profile。
profile 在cargo.toml中定义，会被config.toml中的相应配置覆盖。依赖中定义的profile会被覆盖，只有当前root worksapce的profile配置才会使用。

## rustup
<https://rust-lang.github.io/rustup/index.html>
rustup 是rust release的管理工具。
rustup 管理的某个`rust installation`称为toolchain。可以给toolchain配置channel，component等。
cargo +nightly build 使用`nightly` toolchain。
可以在项目目录中通过`rust-toolchain`或`rust-toolchain.toml`来指定当前项目使用的toolchain。
