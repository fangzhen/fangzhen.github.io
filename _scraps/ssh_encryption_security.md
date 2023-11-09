---
layout: post
title: ssh 中的密码学算法/概念
date: 2023-11-08
tags: ssh security rsa ecdh
---

## ssh中的使用
### Public Key Authentication
用于server端认证client端的身份。

ssh client可以通过公钥认证登陆系统。在ssh server的`~/.ssh/authorized_keys`文件中列出了server端已认证的公钥。ssh client通过`-i`参数指定使用的私钥。
请参考`PubkeyAcceptedAlgorithms`配置项。

### Host Key
用于client端确认server端的身份。

ssh server会生成对应不同签名算法的`/etc/ssh/ssh_host_*`密钥文件。ssh client通过`~/.ssh/known_hosts`记录已知的server地址与key的对应。
请参考`HostKeyAlgorithms`配置项。

上述两者都使用数字签名算法。ssh中使用的如rsa-sha2-512，ssh-ed25519-cert-v01@openssh.com等。

###  Key Exchange(KEX)
key exchange算法用来在不可信的信道中安全地交换加密密钥的算法。在ssh连接中，client和server使用KEX算法来协商两者在接下来的会话中使用的对称加密密钥。
ssh中可用的算法如ecdh-sha2-nistp256，curve25519-sha256。
请参考`KexAlgorithms`配置项。

### 会话内容加密
ssh的会话中可能交换大量数据，性能非常重要，需要使用对称加密算法。该密钥即使用上文中的KEX算法来协商的。常用的如chacha20-poly1305，AES等。请参考`Ciphers`配置项。

## 其他相关
前三者都是使用非对称加密，所以在算法上有一定的相关性。如ECDH, ECDSA分别是密钥交换算法和签名算法，但两者都基于椭圆曲线加密，利用里离散对数问题的难解性。

## References
* [Elliptic Curve Cryptography: ECDH and ECDSA](https://andrea.corbellini.name/2015/05/30/elliptic-curve-cryptography-ecdh-and-ecdsa/) 对ECDH和ECDSA的原理介绍以及使用demo。
* <https://security.stackexchange.com/questions/50878/ecdsa-vs-ecdh-vs-ed25519-vs-curve25519>
* <https://security.stackexchange.com/questions/172274/can-i-get-a-public-key-from-an-rsa-private-key> 在实践中，从private key中一般可以生成public key，但这不是算法保证的，而是实现以及标准相关的。
* [Understanding the SSH Encryption and Connection Process](https://www.digitalocean.com/community/tutorials/understanding-the-ssh-encryption-and-connection-process)
