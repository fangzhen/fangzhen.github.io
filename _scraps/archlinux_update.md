---
layout: post
title: archlinux 升级后问题记录
tags: X openvpn hostname archlinux emacs
date: 2022-07-12
update: 2022-07-12
---

archlinux大概一年多没有升级，升级了一下，遇到一些问题，简单做个记录。

## 升级时某些包验证失败

`pacman -Syu`一些包报类似如下的错误：
```
error: virt-manager: signature from "Eli Schwartz <eschwartz@archlinux.org>" is unknown trust
:: File /var/cache/pacman/pkg/virt-manager-4.0.0-1-any.pkg.tar.zst is corrupted (invalid or corrupted package (PGP signature)).\
Do you want to delete it? [Y/n]
```
手动执行`pacman -S archlinux-keyring`后重新升级解决。
猜测是archlinux-keyring添加了新的keyring，这些包是新的keyring签名的，但是本地还没有安装，导致签名验证不通过。可能跟长时间没更新有关，中间跨度太大。

## proxychains ssh连接不上
最初发现问题是git pull报错。remote是git类型，通过ssh连接。关键错误为`ssh: Could not resolve hostname github.com: Unknown error`。
手动执行ssh也会报这个错。

```
$ proxychains git fetch origin
[proxychains] config file found: /etc/proxychains.conf
[proxychains] preloading /usr/lib/libproxychains4.so
[proxychains] DLL init: proxychains-ng 4.16
[proxychains] DLL init: proxychains-ng 4.16
ssh: Could not resolve hostname github.com: Unknown error
fatal: Could not read from remote repository.

Please make sure you have the correct access rights
and the repository exists.
```

社区bug：https://github.com/rofl0r/proxychains-ng/issues/439

kernel和glibc升级后引入的一个问题，需要打patch。

##  一旦连接openvpn，就无法打开任何新的窗口
这个问题开始比较摸不着头脑。现象是所有图形界面应用都无法打开，已经打开的不影响。桌面环境为KDE+Xorg。系统日志部分应用会coredump，部分会报错。类似：
```
Jul 10 20:09:23 loaclhost systemsettings[2588]: qt.qpa.xcb: could not connect to display :0
Jul 10 20:09:23 loaclhost systemsettings[2588]: qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
Jul 10 20:09:23 loaclhost systemsettings[2588]: This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

                                                Available platform plugins are: eglfs, linuxfb, minimal, minimalegl, offscreen, vnc, wayland-egl, wayland, wayland-xcomposite-egl, wayland-xcomposite-glx, xcb.
Jul 10 20:09:24 loaclhost systemd-coredump[2593]: [🡕] Process 2588 (systemsettings) of user 1000 dumped core.

                                                  Module linux-vdso.so.1 with build-id 45fe77beae9620c9a2857a8cddfe1dc14575d85e
                                                  Module libuuid.so.1 with build-id 032a21acd159ee3902605e9911be5f86a7df7df9
...
                                                  Module systemsettings with build-id e60e5df17ac4402b16274438ea6df6b890c21b86
                                                  Stack trace of thread 2588:
                                                  #0  0x00007fe02948e36c n/a (libc.so.6 + 0x8e36c)
                                                  #1  0x00007fe02943e838 raise (libc.so.6 + 0x3e838)
                                                  #2  0x00007fe029428535 abort (libc.so.6 + 0x28535)
                                                  #3  0x00007fe029c9fede _ZNK14QMessageLogger5fatalEPKcz (libQt5Core.so.5 + 0x9fede)
                                                  #4  0x00007fe02a33c9a5 _ZN22QGuiApplicationPrivate25createPlatformIntegrationEv (libQt5Gui.so.5 + 0x13c9a5)
                                                  #5  0x00007fe02a33d009 _ZN22QGuiApplicationPrivate21createEventDispatcherEv (libQt5Gui.so.5 + 0x13d009)
                                                  #6  0x00007fe029e9210b _ZN23QCoreApplicationPrivate4initEv (libQt5Core.so.5 + 0x29210b)
                                                  #7  0x00007fe02a33d0b9 _ZN22QGuiApplicationPrivate4initEv (libQt5Gui.so.5 + 0x13d0b9)
                                                  #8  0x00007fe02ab75e2e _ZN19QApplicationPrivate4initEv (libQt5Widgets.so.5 + 0x175e2e)
                                                  #9  0x0000555c2ca96185 n/a (systemsettings + 0xb185)
                                                  #10 0x00007fe029429290 n/a (libc.so.6 + 0x29290)
                                                  #11 0x00007fe02942934a __libc_start_main (libc.so.6 + 0x2934a)
                                                  #12 0x0000555c2ca974b5 n/a (systemsettings + 0xc4b5)
                                                  ELF object binary architecture: AMD x86-64
Jul 10 20:09:24 loaclhost systemd[1]: systemd-coredump@4-2590-0.service: Deactivated successfully.
```
在terminal里直接执行，报错为
```
$ dolphin
Authorization required, but no authorization protocol specified

qt.qpa.xcb: could not connect to display :0
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

Available platform plugins are: eglfs, linuxfb, minimal, minimalegl, offscreen, vnc, wayland-egl, wayland, wayland-xcomposite-egl, wayland-xcomposite-glx, xcb.

Aborted (core dumped)
```

最开始没注意到什么情况下会触发问题，看报错跟qt相关，这块又不太了解。网上找到的内容大部分不太相关。也没有解决。

后来发现一连公司的vpn就会复现，就是普通的openvpn。也没找到有价值的线索，只是觉得更加奇怪。

继续测试发现up/down vpn的tun设备就能复现。把设备down掉就正常，up起来就有问题。看日志发现设备up/down会触发NetworkManager的动作，才注意到有如下日志：
```
Jul 12 00:14:11 archlinux NetworkManager[4014]: <info>  [1657556051.8455] policy: set-hostname: set hostname to 'loaclhost' (from address lookup)
Jul 12 00:14:11 archlinux systemd[1]: Starting Hostname Service...
Jul 12 00:14:11 archlinux dbus-daemon[369]: [system] Successfully activated service 'org.freedesktop.hostname1'
```

也就是连vpn之后，NetworkManger把hostname改掉了。Xorg的xauth是有主机名信息的。

```
$ xauth list
archlinux/unix:0  MIT-MAGIC-COOKIE-1  d1315e597e75b073f4f829947d51b2bb
```

连vpn后，hostname被修改是因为我这个系统里没有配置static hostname，所以用的是transient hostname。通过hostnamectl或者边界/etc/hostname配置一下static hostname即可。

```
       systemd-hostnamed.service(8) and this tool distinguish three different hostnames: the high-level "pretty" hostname which might include all kinds of special characters (e.g. "Lennart's Laptop"), the "static"
       hostname which is the user-configured hostname (e.g. "lennarts-laptop"), and the transient hostname which is a fallback value received from network configuration (e.g. "node12345678"). If a static hostname is
       set to a valid value, then the transient hostname is not used.
```

## emacs升级后更新package

在package buffer下执行`U`，即`package-menu-mark-upgrades`后，message提示如下信息后就没有任何进展了，也没有package被标记为更新
```
Waiting on packages to refresh...
```

`package-menu-mark-upgrades`文档显示：
```
If there’s an async refresh operation in progress, the flags will
be placed as part of ‘package-menu--post-refresh’ instead of
immediately.
```
猜测是刷新操作没有完成。手动执行了下`package-refresh-contents`命令后正常了。
