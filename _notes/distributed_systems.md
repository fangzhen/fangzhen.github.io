---
layout: post
title: 分布式算法概述
tags: ["distributed systems", "distribute algorithms"]
date: 2023-03-13
update: 2023-04-07
---

## 引言

## 分布式算法的系统基本模型
分布式算法是多个计算实体（下文不引起混淆的情况下都称为进程）协作解决某个问题的算法。
《分布式算法》(Nancy A. Lynch著)一书从几个维度(书中用的词是attributes)对系统进行建模，每个维度都有不同的值域。
各个维度取值后形成一个问题域，对于某个分布式算法来说，它的边界就由该问题域框定，即为该算法的系统模型。
换句话说，分布式算法在特定的系统模型下解决特定的问题。

本文中，对分布式算法建模如下：

* 运行环境/系统模型：
  1. 时序模型：同步/异步
  1. 进程间通信模型：如共享存储，远程过程调用，消息传递
  1. 故障模型：
     * 进程故障：进程停止；拜占庭故障
     * 通信故障：例如消息丢失；消息重复
* 目标问题：
  1. 要解决的问题：
     对于不同的问题当然要有不同的算法。分布式系统的复杂性也意味着目标问题的复杂性。
  1. 算法边界：
     * 真实世界有可能无法满足算法预设的系统模型。当系统模型被打破的情况下，算法会是什么行为。
     * CAP/FLP等定理说明不存在"完美"的算法，算法需要在不同维度进行取舍。例如在同样的模型下，2PC对故障的容忍程度不如paxos。
  1. 一致性模型：
     分布式系统对外提供服务，通常需要承诺一定的正确性。对于多副本的分布式系统，一致性是正确性的一部分。

当然，对分布式系统的系统模型不止这几个维度，对特定的问题来说，还会有更细分或特定于该领域的维度。
建立系统模型可以让我们对于目标问题的讨论有一定边界，而不至于无限发散。另一方面，系统模型应该能反应真实世界，否则不具有实用性。
每个算法/问题中对每个维度的设定甚至可能会有一些微妙的差别。比如时序模型分为同步/异步是非常粗略的区分，并不是二值的，而是一个区间连续的。

在该系统基本模型下，分布式算法与并发算法并没有本质的区别，只是对模型的设定有所区别。

### 分层模型
软件系统，通常抽象成不同的模块，模块之间通过外部接口来访问，不需要了解内部细节，以降低系统整体的复杂度。
当然也可以把不同模块组合起来可以形成一个更高层的系统，对该系统外部的使用者来说，仍然不需要连接内部的实现细节。
例如对数据库客户端来说，它不需要知道DBMS的实现，它只需要根据DBMS的ACID特性来编写业务逻辑。
对应用开发者来说，也不需要关心CPU cache是否miss。

当然，接口抽象不是万能的，比如在性能调优的场景下，可能需要了解内部实现细节。

在分布式系统中以分层模型的角度来抽象，让我们得以从系统内部和外部的不同视角来看待一个分布式系统。

## 同步/异步
关于同步/异步在不同文献和上下文中有各种不同的内涵，我们尝试列出有代表性的，并尝试指出他们的内在联系。
### 进程同步/异步执行

   [wikipedia](https://en.wikipedia.org/wiki/Synchronization_(computer_science))对进程同步的定义为：
   >  Process synchronization refers to the idea that multiple processes are to join up or handshake at a certain point, in order to reach an agreement or commit to a certain sequence of action.

### 同步/异步网络模型
1. lock-step 同步

   《分布式算法》书中第二章的同步网络模型是一种lock-step模型。在每一轮(round)**所有进程**接收消息，计算自身状态进行状态转移并发出消息。
   每个进程在每一轮的计算量，状态，接收和发送的消息是不受限制的，但是所有进程的轮次是同步的。

   如果要求各进程每一轮的操作完全一样，它可以作为一种fault-tolerant方案，例如[fault-tolerant](https://en.wikipedia.org/wiki/Fault_tolerance)里提到的lockstep fault-tolerant machine。

   除了硬件同步，还可以通过进程同步的软件方式来实现lockstep。

1. timeout 同步
   https://people.cs.umass.edu/~arun/cs677/reading/HT.pdf 这篇论文2.2-2.4节定义了同步和异步网络，《分布式系统》一书也采用了该定义。

   同步网络应该满足如下属性：

   > * 任意进程执行一步需要的时间有上限；
   > * 每个进程都有本地时钟，而且时间漂移有上限；
   > * 消息延迟有上限，而且不会丢失。

   上述几个条件都是使用超时机制检测crash的必要条件。反过来，异步模型不满足这些条件。或者满足部分条件，可以称为部分异步。

   可以认为该同步模型相比lockstep同步模型的同步要求更加宽松，lockstep同步模型中，所有进程的轮次都是严格相同的，而该模型中只是通过上述条件保证了超时机制的可能性。

   不同算法对时序模型的假设会有些微妙的差别，例如paxos等共识算法采用的异步网络模型跟本模型类似。

**本质上分布式算法就是并发进程间需要互相协调执行以完成一项任务，这个协调过程就是同步。**
一方面，系统模型提供了不同的能力来协助进程进行同步协调，例如上面提到的lockstep或者timeout。
另一方面，并发进程要利用系统模型提供的能力来进行协调。

## 一致性
从分层模型的视角看，分布式系统对外提供的接口需要包含正确性承诺。一致性承诺是正确性的重要方面。

### 强一致性
从系统外来看，强一致的系统看起来跟非分布式系统提供的语义是相同的，客户端/外部程序的视角没有区别。
有很多论文对各种不同分布式系统提出了强一致性模型，<https://jepsen.io/consistency>可以作为索引和参考。
应当注意，各种一致性模型提出于不同的分布式系统，不是完全适合放到一起来比较。

本节我们采用[Herlihy & Wing, 1990]提出的Linearizable一致性模型。该模型下，需要有全局真实时间，并发操作序列P等价于某个顺序操作序列S，
S中操作的真实时间顺序和任意外部程序内的操作顺序一致，且和所有外部操作的真实时间顺序一致。

Linearizable有全局真实时间的顺序要求。通过全局真实时间，可以比较跨进程的操作顺序。

在实际系统中，通过全局真实时间排序不一定能够满足，也不一定需要满足：
1. 相对论限制了并不是总能对并发操作的时间进行比较；
2. 在时间可比较的情况下，(几乎)没有算法会重排对应操作。

但Linearizable定义中的全局真实时间仍是有意义的：相对论限制了我们不能保证得到所有操作的全序，但是我们仍然可以获得真实时间下的偏序。该真实时间偏序至少包含：
1. 同一个外部进程内不同操作的先后顺序
2. 系统模型中可比较的其他时间顺序，这与系统设计有关。
   系统对正确性的建模直接影响对时间偏序的定义，或者反过来。（例如spanner使用的TrueTime，相对来说会更"全序"一些。）
   不同参考文献对strict serializable，external consistency，linearizable等词的使用也反应了这种差别，基本上没有一个完全一致的定义。

**与数据库事务Serializable隔离级别的关系：**
1. 一个事务可能有多个操作处理多个对象，Linearizable讨论的是单个操作处理单个对象。这应该不算本质区别，我们可以把一个事务抽象为一个操作。
1. 事务的可序列化要求多个事务的并发执行结果等价于这些事务某个顺序执行，它是比Linearizable更弱的要求，它没有要求等价的执行顺序和事务实际顺序一致。

可以把Strict Serializable理解为要求Serializable的同时也应该保证时间偏序。

### 弱一致性
非强一致的都应该算做弱一致性，并没有一个确切的指标。
总的来说，弱一致性的系统对外提供服务，对于外部程序来说，很可能需要感知和处理一致性问题。

### 不同的"一致性"表述
数据库事务的一致性是指数据库内部状态一致，没有逻辑错误，例如外键约束，uniq约束等，跟并发无关。
本节讲的一致性主要指分布式系统对外提供的外部接口，在时序下的一致性，一般跟并发有关。多副本系统的一致性一般指本节的一致性。

不同的一致性表述，一般和正确性有关，体现了(分布式)系统对外接口承诺的一部分。
不同论文中的一致性一般都是针对论文所涵盖的场景，并没有一个普遍接受的适用于所有系统的形式化的定义。

## 系统模型示例
本节列举一些常见的分布式算法或应用场景，并粗略给出这些场景的系统模型，以帮助对以上分布式算法的系统模型建立更具象的感受。

### FPGA
通过FPGA设计硬件电路，可以并行执行某些任务。一般来说，FPGA都会提供时钟，所有操作都是在同一个时钟下进行同步的。
可以建模为硬件层面的lockstep同步模型。

### 线程与协程
从技术上，线程与协程都可以作为并发的实现手段，所以抛开具体的算法，单独考虑线程和协程意义不大。
另一方面，协程是协作式多任务，线程是抢占式多任务。协程之间相比线程之间多了一层同步机制，协程的切换只会在协程主动yield时才发生。
从时序模型的角度来看，协程比线程更"同步"。
举例来说，通过协程来实现一个生产者消费者问题，类似下面[伪代码](https://en.wikipedia.org/wiki/Coroutine):
```
var q := new queue

coroutine produce
    loop
        while q is not full
            create some new items
            add the items to q
        yield to consume

coroutine consume
    loop
        while q is not empty
            remove some items from q
            use the items
        yield to produce

call produce
```
对于coroutine `product`和`consume`来说，它在访问`q`时可以直接访问，但是如果使用线程实现，就必须通过加锁或其他方式来同步两个线程以避免冲突。

### 哲学家就餐问题
哲学家就餐问题是一个经典的并发同步问题，系统模型可以归结为：

* 异步：不同哲学家无交谈，随时可能开始吃东西或思考；
* 共享存储：两个哲学家可能尝试拿同一支叉子；
* 无故障：不考虑单个哲学家的故障，例如哲学家离开。

类似的如生产者消费者问题，他们的系统模型类似，但要解决的问题不同，可能的算法也不同。

### 数据库事务
数据库事务系统模型归结为：
* 异步：事务发起是不受数据库管理系统控制的，不同数据库连接在任何时刻都可能开始一个事务；
* 共享存储：不同事务访问的是同一份数据；注意这里并不涉及数据的多副本；
* 故障：客户端进程可能崩溃而不提交事务。

#### 数据库事务隔离性
数据库事务的ACID特性与并发相关的主要是隔离性。

隔离性本质上是DBMS通过对数据的受控访问，简化客户端并发执行的逻辑。这与通过channel来进行数据传递以避免显式在临界区加锁在理念上有相通之处。

假设一个没有任何隔离级别承诺的数据库系统，所有访问某一行的进程都在临界区（事务开始到结束）加排他锁，这些进程对该行数据的访问就达到了可重复读级别。
当然，对数据库系统的使用场景来说，上述加锁方案并不太现实，尤其是不同业务都需要访问同一个数据库的时候。而且DBMS可以做很多优化。

> 事务的原子性：事务要么提交，要么不提交，不能提交一部分。原子性的语义跟事务是否并发没有关系，即使只有单个事务也要保证原子性。
>
> 另一方面，原子性可以看成是一个更基础的属性。CID的语义可以认为是建立在原子性基础上的。比如两个事务A, B序列化执行意味着执行顺序可能是AB或BA，但是不会考虑单个事务非原子执行的情况。

### CPU Cache一致性 - MESI协议
CPU和内存之间速度差别越来越大导致了CPU cache的引入。多核CPU拓扑中，每个CPU核心可能拥有自己独立的缓存。当上层应用访问内存时，就会存在CPU cache一致性问题。
可以把CPU Cache一致性系统模型归结为：
* 异步：不同CPU核心随时可能访问任意内存；
* 消息传递：MESI协议通过消息广播来在不同CPU之间传递消息；
* 无故障：MESI协议不考虑消息丢失或某个CPU不工作等故障。

### 共识问题
我们采用paxos论文中的共识算法定义：
假设一组进程，这些进程可以提议值。共识算法确保能选定某一个选定的值。如果没有提议值，那么也不会选定值。如果值被选定，那么进程应该可以学习到该值。
共识问题的系统模型归结为：
* 异步：不同进程各自独立执行；消息可能丢失，延迟任意长时间等；
* 消息传递：进程间通过消息传递通信；
* 故障：进程可能crash；消息链路可能断开；不会发生拜占庭故障。

相关算法：2PC, Paxos, Raft等算法，这些算法对系统模型的设定类似。

**共识与一致性的关系：**
共识算法是达成多副本强一致性的手段。共识算法从系统内部的视角，描述分布式系统内不同进程达成共识的方法。共识算法可以用来实现leader election，多副本强一致等。
一致性侧重于系统外部接口的视角来描述分布式系统给出的承诺。

## 时钟
## CAP、FLP
## 其他
安全性、性能

## References:
* 分布式系统书籍
  - Nancy A. Lynch, Distributed Algorithms: 本书是对分布式算法的全面介绍，并给出了大部分算法的数学证明。行文类似学术论文，严谨但读起来不太友好。
  - [Mikito Takada, Distributed Systems: For Fun and Profit](http://book.mixu.net/distsys/ http://book.mixu.net/distsys/single-page.html):
    本书也侧重于分布式算法，总共不到100页，基本涵盖了分布式算法的主要方面，包括系统建模，时间和顺序，多副本等，可读性强。
  - George Coulouris etc., Distributed Systems: Concepts and Design: 对分布书系统的方方面面进行介绍，不仅限于分布式算法。

* FLP
  - [Practical Understanding of FLP Impossibility for Distributed Consensus](https://levelup.gitconnected.com/practical-understanding-of-flp-impossibility-for-distributed-consensus-8886e73cdfe5)
  - https://www.cnblogs.com/firstdream/p/6585923.html
* CAP
  - C： all nodes see the same data at the same time. <- 要求所有节点。从结果的视角来描述？
  - 侧重点是可用性和一致性的妥协
  - https://timilearning.com/posts/ddia/part-two/chapter-9-1/ 里认为cap里的C是Linearizability
  - https://stackoverflow.com/questions/12346326/cap-theorem-availability-and-partition-tolerance
  - https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/ - 值得看
  - https://codahale.com/you-cant-sacrifice-partition-tolerance/
  - http://ksat.me/a-plain-english-introduction-to-cap-theorem
  - https://cloud.tencent.com/developer/article/1860632
  - http://www.hollischuang.com/archives/666
  - https://codahale.com/you-cant-sacrifice-partition-tolerance/


* 具体的分布式算法，paxos 2pc etc.
  - Paxos Made Simple
  - https://stackoverflow.com/questions/27304887/paxos-vs-two-phase-commit
  - https://medium.com/@predrag.gruevski/learn-by-example-how-paxos-and-two-phase-commit-differ-c9b139b700ef
  - [Discover Paxos via 2pc]https://blog.the-pans.com/discover-paxos/
  - [分布式系统的核心：共识问题](https://zhuanlan.zhihu.com/p/220311761)
  - [分布式共识](http://blog.kongfy.com/2016/05/%e5%88%86%e5%b8%83%e5%bc%8f%e5%85%b1%e8%af%86consensus%ef%bc%9aviewstamped%e3%80%81raft%e5%8f%8apaxos/)
    作者对共识问题进行了总结，包含系统模型，也设计raft, paxos等具体算法，值得看一下。
  - [从分布式一致性算法到区块链共识机制](https://mp.weixin.qq.com/s/LOUDWn7evcePCPGWar8vEA)

* 时钟：
  - 解决分布式系统下的先后顺序问题： 逻辑时钟 向量时钟 http://yang.observer/2020/07/26/time-lamport-logical-time/

* 一致性 & 序列化隔离级别
  - 论文：[lamport, 1979], [Herlihy & Wing, 1990]
  - https://jepsen.io/consistency 不同的一致性模型汇总和分类，可供参考。个人感觉对有的模型的描述不是很准确，好在都给出了原论文。
  - [FaunaDB对strict serializability的解释](https://fauna.com/blog/serializability-vs-strict-serializability-the-dirty-secret-of-database-isolation-levels)
  - https://hpi.de/fileadmin/user_upload/fachgebiete/naumann/lehre/WS2018/DDM/12_DDM_Consistency_and_Consensus.pdf 里面讲了linearizablity
  - https://timilearning.com/posts/ddia/part-two/chapter-9-1/#linearizability
  - https://timilearning.com/posts/consistency-models/
  - [被误用的一致性](http://blog.kongfy.com/2016/08/%E8%A2%AB%E8%AF%AF%E7%94%A8%E7%9A%84%E4%B8%80%E8%87%B4%E6%80%A7/):
    该博客包含对共识/多副本一致性/ACID的一致性的理解和澄清

* 并发模型
  - https://www.tedinski.com/2018/11/06/concurrency-models.html
  - 有些人强调应该把concurrency和parallelism明确区分开，两者是完全不同的问题。
  - https://ghcmutterings.wordpress.com/2009/10/06/parallelism-concurrency/
  - https://existentialtype.wordpress.com/2011/03/17/parallelism-is-not-concurrency/
  - https://www.tedinski.com/2018/10/16/concurrency-vs-parallelism.html
  - https://jenkov.com/tutorials/java-concurrency/concurrency-models.html
    [缓存更新的套路](https://coolshell.cn/articles/17416.html)
    涉及并发模型、分布式系统架构、计算机体系结构等的相关性思考，这也是本文的一个基本观点。


[lamport, 1979]: https://www.microsoft.com/en-us/research/uploads/prod/2016/12/How-to-Make-a-Multiprocessor-Computer-That-Correctly-Executes-Multiprocess-Programs.pdf
[Herlihy & Wing, 1990]: [Linearizability: A Correctness Condition for Concurrent Objects](https://cs.brown.edu/~mph/HerlihyW90/p463-herlihy.pdf)提出。
