
android SDK包含多个包，https://developer.android.com/tools 包含了命令行工具和包的概述。

通过yay安装cmdline tools, 包含sdk-manager
$ yay -S android-sdk-cmdline-tools-latest

其他包大部分也可以通过aur安装，或通过sdk-manager安装。

$ yay -S android-sdk-build-tools android-sdk-platform-tools android-platform android-emulator android-google-apis-playstore-x86-64-system-image

## 权限
https://wiki.archlinux.org/title/android
The AUR packages install the SDK in /opt/android-sdk/. This directory has root permissions, so keep in mind to run sdk manager as root. If you intend to use it as a regular user, create the android-sdk users group, add your user.

# groupadd android-sdk
# gpasswd -a <user> android-sdk

Set an access control list to let members of the newly created group write into the android-sdk folder. As running sdkmanager can also create new files, set the ACL as default ACL. the X in the default group entry means "allow execution if executable by the owner (or anyone else)"

# setfacl -R -m g:android-sdk:rwx /opt/android-sdk
# setfacl -d -m g:android-sdk:rwX /opt/android-sdk

Re-login or as <user> log your terminal in to the newly created group:

$ newgrp android-sdk

## Accept license
$ sdkmanager --licenses

> 如果上面权限配置没配，需要sudo。如果没权限也不报错，只是实际没效果。。

## flutter
https://docs.flutter.dev/get-started/install/linux/android?tab=download

$ export PUB_HOSTED_URL=https://pub.flutter-io.cn;
export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn

$ yay -S flutter-bin

## hello world
$ flutter create myself_app

$ flutter emulators --create
$ flutter emulators --launch 'flutter emulator'

虚机设备起来之后，flutter devices可以看到

$ flutter devices
Found 2 connected devices:
  sdk gphone64 x86 64 (mobile) • emulator-5554 • android-x64 • Android 13 (API 33) (emulator)
  Linux (desktop)              • linux         • linux-x64   • Manjaro Linux 6.6.30-2-MANJARO

$ flutter run
Launching lib/main.dart on sdk gphone64 x86 64 in debug mode...


https://github.com/imaNNeo/fl_chart/issues/71
