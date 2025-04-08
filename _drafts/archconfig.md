---
layout: post
title: 通过git管理Linux的各种配置
tags: ["archlinux", "config"]
date: 2025-03-20
---

## 初衷
1. 重要数据备份
2. 在重装系统时，方便地恢复原配置

## 实现手段

通过创建一个独立的 Git 仓库来管理系统的配置文件，并使用 `git-crypt` 对敏感数据进行加密。以下是具体步骤：

1. 创建一个用于存储配置文件的 Git 仓库。
2. 设置 Git 别名，方便直接操作根目录下的配置文件。
3. 初始化 Git 仓库并配置忽略未跟踪文件。
4. 使用 `git-crypt` 对敏感数据进行加密，并生成密钥文件。

```bash
# 创建 Git 仓库目录
mkdir -p ~/develop/archconfig

# 设置 Git 别名
alias git-archconfig='git --git-dir=~/develop/archconfig/archconfig.git --work-tree=/'

# 初始化裸仓库
git init --bare ~/develop/archconfig/archconfig.git

# 配置忽略未跟踪文件
git-archconfig config status.showUntrackedFiles no

# 初始化 git-crypt 加密
git-archconfig crypt init

# 导出密钥文件
git-crypt export-key /path/to/key

# 克隆仓库后解锁加密文件
git-crypt unlock /path/to/key
```

## References
- https://stackoverflow.com/questions/2456954/git-encrypt-decrypt-remote-repository-files-while-push-pull
- https://github.com/AGWA/git-crypt
