---
layout: post
title: Not a golang cheatsheet
tags: golang
date: 2022-10-12
update: 2022-10-12
---

## module
Go 1.11 新引入的依赖管理系统，区别于原来完全依赖`GOPATH`的方式。自1.16版本起，无论有无go.mod文件，都默认为module-aware模式。（环境变量GO111MODULE默认为on，之前默认为auto）。
module-aware模式下，go get等下载的包还是会存到`GOPATH`下。

<https://insujang.github.io/2020-04-04/go-modules/>

## go get vs. go install
`go get` 会下载并安装package，并更新go.mod文件。使用`-d`参数只下载包和更新go.mod。`-d`也会在未来版本变成默认开启。

`go install`是当前推荐的安装命令，安装到`GOPATH/bin`下。`go install`可以指定具体版本，这种情况下不需要从当前目录或父目录的go.mod获取。如果本地没有对应包，`go install`也会下载。

## go 升级到1.19后执行命令报错

例如`controller-gen`命令报错如下：
```
/path/to/bin/controller-gen object:headerFile="hack/boilerplate.go.txt" paths="./..."
/usr/lib/go/src/sync/atomic/type.go:39:16: expected ']', found any
/usr/lib/go/src/sync/atomic/type.go:39:19: expected ';', found ']'
/usr/lib/go/src/sync/atomic/type.go:39:19: expected type, found ']'
/usr/lib/go/src/sync/atomic/type.go:45:34: expected declaration, found 'return'
/usr/lib/go/src/sync/atomic/type.go:39:16: expected ']', found any
/usr/lib/go/src/sync/atomic/type.go:39:19: expected ';', found ']'
/usr/lib/go/src/sync/atomic/type.go:39:19: expected type, found ']'
/usr/lib/go/src/sync/atomic/type.go:45:34: expected declaration, found 'return'
/usr/lib/go/src/sync/atomic/type.go:39:16: expected ']', found any
/usr/lib/go/src/sync/atomic/type.go:39:19: expected ';', found ']'
/usr/lib/go/src/sync/atomic/type.go:39:19: expected type, found ']'
/usr/lib/go/src/sync/atomic/type.go:45:34: expected declaration, found 'return'
Error: not all generators ran successfully
```

原因是`controller-gen`是用低版本（1.16）编译的，当时版本不支持泛型。它处理1.19的type.go中的泛型代码会直接报错。解决方案：用新版本的go 重新编译安装`controller-gen`命令即可。
