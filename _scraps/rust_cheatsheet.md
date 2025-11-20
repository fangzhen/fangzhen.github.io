---
layout: post
title: Rust & Cargo 一些特性概述 & 参考索引
tags: rust cargo
date: 2022-09-12
update: 2023-03-13
---

本文不是rust入门或手册，只是一些对我个人来说容易忘记或混淆的点的整理。

* TOC
{:toc}

## 语言与编译器(rustc)
### Edition
Edition 机制为了**保证后向兼容**。不同的edition可能有不兼容的修改。例如`async`在2018 edition变成关键字，在2015 edition可以作为普通变量名。通过在Cargo.toml中指定edition=2018，rust编译时会按照2018的语法来进行编译。

Edition机制**不会保证前向兼容**。比如feature在stablize后，stable channel新版本的rust可以直接使用，但是旧版本仍不能用。

[官方文档](https://doc.rust-lang.org/edition-guide/editions/index.html)

### Rust Unstable Feature
[rust unstable reference](https://doc.rust-lang.org/beta/unstable-book/)
Unstable Feature 分为三类：
1. compiler flags: 通过`-Z<flag>`指定，例如`-Zcodegen-backend=<path>`

2. language features:

   这些是编译器feature，通过`#![feature]`指定。
   feature的列表在源码的`src/rustc_feature/`下，
   [`accepted.rs`](https://doc.rust-lang.org/nightly/nightly-rustc/src/rustc_feature/accepted.rs.html)是已经stable的feature列表，
   [`active.rs`](https://doc.rust-lang.org/nightly/nightly-rustc/src/rustc_feature/active.rs.html)是unstable的feature列表。
   随着rust的开发，有些feature会从unstable变成stable，参考<https://rustc-dev-guide.rust-lang.org/stabilization_guide.html>

3. library features:

   library feature是定义在rustc standard library的feature，使用`#[unstable]` 等attribute 定义。
   目前只支持 rust 源码树中的library定义。外部crate中的library不能自定义feature(<https://github.com/rust-lang/rfcs/issues/1491>)。
   `unstable`等attribute的使用以及stabilizing library feature参考 <https://rustc-dev-guide.rust-lang.org/stability.html>。
   在源码中使用也是通过 #![feature]指定。

   unstable feature不能用于stable channel。

cargo也有`unstable`和`feature`，可以参考下面cargo部分。

### Attributes
<https://doc.rust-lang.org/reference/attributes.html>

Attribute 是一种通用的metadata，用于向编译器提供额外的信息或指令，以改变代码的编译方式或行为。
Attribute 可以应用于整个 crate、模块、函数、结构体、枚举等各种项(item)，在编译时处理。
形如`#[Attr]`(outer attributes, 应用于紧随其后的项)或`#![Attr]`(inner attributes, 应用于包含它的项)

可以分为四类
- Builtin attributes, 例如`cfg`，`test`， `derive`等。`#![feature]`也是一种builtin attribute。
- Macro attrbutes，通过`attribute macro`定义的attribute。
- Derive macro helper attributes，用于在`Derive macro`中定义额外attributes。
- Tool attributes，外部工具如`rustfmt`等定义。

#### Derive Attribute
<https://doc.rust-lang.org/reference/attributes/derive.html>

`derive` attribute用于给数据结构自动生成item（例如方法等）。例如给struct生成Clone trait的方法。可以使用`Derive macro`给自己的tait定义额外的`derive`。

### Macros
<https://doc.rust-lang.org/reference/macros.html>

*编译时*扩展macro，并替换macro定义。rust中有两种方式定义macro：
1. `Macros by Example` define new syntax in a higher-level, declarative way.
   使用`macro_rules!`宏声明式来定义。`by example`可以理解为这种定义方式比较直观，以类似举例的方式来定义宏。
2. `Procedural Macros` define function-like macros, custom derives, and custom attributes using functions that operate on input tokens.
   这种定义方式直接处理`TokenStream`，输出新的`TokenStream`。分为三种：
   - Function-like macros - custom!(...)
   - Derive macros - #[derive(CustomDerive)]
   - Attribute macros - #[CustomAttribute]

### 条件编译
<https://doc.rust-lang.org/reference/conditional-compilation.html>

条件编译的选项是在编译时确定和生效的。

#### 设置配置选项：
  部分选项是编译器自动设置，其他选项是编译时传给编译器的，可以通过以下两种方式。
  - rustc 通过`--cfg`参数指定。 形式可以是name或者k=v对，例如`unix`，`foo="bar"`
    有一些预定义的option，如`target_arch`等。
  - cargo.toml `[feature]` section中定义的feature或者可选依赖自动变成key是`feature=<feature>`的option。

#### 条件编译形式
   以下三种形式都是根据指定的选项来进行不同的条件编译。
   - cfg attribute
   - cfg_attr attribute
   - cfg macro

## Cargo
<https://doc.rust-lang.org/cargo/index.html>

cargo 是rust的包管理器。用于包的依赖管理，编译，分发等。

### package manifest
<https://doc.rust-lang.org/cargo/reference/manifest.html>

package manifest指的是包中的cargo.toml文件，包含包的信息，例如名字，版本，依赖，target等。
cargo targets是指cargo的build产物，如library, binary, example等。

除了这些target，很多时候平台相关的配置也称为target。例如平台相关的依赖，就是使用类似`[target.'cfg(unix)'.dependencies]`的section。
平台相关的条件也通过`<cfg> expression`来指定。

### cargo configuration
<https://doc.rust-lang.org/cargo/reference/config.html>

除了cargo manifest, 还有一类配置文件，`config.toml`，称为configuration。cargo configuration可以定义在包级别，也可以定义在全局配置中，而cargo.toml只能定义在包级别。
其中[target] table 用于指定平台相关的设置。可以使用`<cfg> expression` 或者平台`<triple>`类进行匹配。

个人理解，cargo configuration一般是对build工具本身的配置，例如cargo的命令aliases，网络代理，环境变量等。而cargo manifest主要是对package的配置。

### package feature
<https://doc.rust-lang.org/cargo/reference/features.html>

cargo.toml中可以定义[feature] section，定义包的feature。可以在build或者添加依赖时指定feature。根据feature可以进行条件编译。例如`#[cfg(feature = "webp")]`

### cargo unstable feature
<https://doc.rust-lang.org/cargo/reference/unstable.html>

cargo unstable feature是指cargo本身的unstable feature。只有nightly channel的cargo可以使用。通过cargo 命令行 `-Z` 参数或者`config.toml`中[unstable] section指定。

### profile
<https://doc.rust-lang.org/cargo/reference/profiles.html>

profile提供一个修改编译参数的方案，可以认为一个profile定义了一组编译选项。通过选择不同的profile，自动应用该profile代表的一组编译选项。
cargo有四个内置profile：`dev`, `release`, `test`, `bench`。默认会根据不同的cargo命令自动使用不同的profile。。

profile的配置可以在cargo.toml中修改，会被config.toml中的相应配置覆盖。依赖中定义的profile会被覆盖，只有当前root worksapce的profile配置才会使用。

## Rustup
<https://rust-lang.github.io/rustup/index.html>

`rustup` 是rust release的管理工具。

rustup 管理的某个rust installation称为toolchain。可以给toolchain配置channel，component等。
`cargo +nightly build` 使用`nightly` toolchain。

可以在项目目录中通过`rust-toolchain`或`rust-toolchain.toml`来指定当前项目使用的toolchain。

## Platform Support

### 概述
<https://doc.rust-lang.org/nightly/rustc/platform-support.html>

Rust对平台的支持分为三级（Tier）：
- Tier 1: guaranteed to work
- Tier 2: guaranteed to build
- Tier 3: Rust codebase 有支持，但Rust项目不会针对对应平台自动build或测试。

支持的平台用“Target Triple”来表示，如`x86_64-unknown-linux-gnu`、`aarch64-apple-darwin`。


**Target 主要功能是为rustc指定一些codegen和linking的参数**。为了实现这一点，主要有几种方式：

1. builtin target triple的默认配置或自定义target json。
   - 使用`rustc --print target-list`列出所有的builtin target triple。
   - 使用`rustc --print target-spec-json --target <target-triple>`可以输出target具体的json内容。
   - 自定义target json可以通过内置target的json结合代码或文档(如<https://doc.rust-lang.org/beta/nightly-rustc/rustc_target/spec/index.html>)来编写自己的target。
   - cargo和rustc都可以通过target 三元组或json文件指定target。

2. 通过cargo的config.toml也可以指定target相关的参数，覆盖三元组的默认配置。参考
   <https://doc.rust-lang.org/cargo/reference/config.html?highlight=target#target>
   应该注意，cargo的`[target]` table和target 三元组或target json文件虽然有关系，但不是直接对应的（并不是相同的字段直接覆盖）。

3. 直接指定rustc参数的方式。
   上述两种方式最终也是通过rustc的选项生效。
   <https://doc.rust-lang.org/rustc/codegen-options/index.html>

### toolchain 和target的关系
toolchain对应的是当前机器上的rust工具链，如cargo，rustc，rust-analyzer，也就是对应的工具要在本地运行；而target是当前代码要编译的目标环境，跟本地的环境没关系。

例如x86_64的linux机器上开发要运行在aarch64的linux下的应用，那么有可能
toolchain为stable-x86_64-unknown-linux-gnu，
target为aarch64-unknown-linux-gnu。

所以toolchain的完整格式虽然为`<channel>[-<date>][-<host>]`，但一般只需指定channel为stable/nightly。
