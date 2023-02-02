分布式系统与并发

主体： 一组指令，caller - 数据库事务，临界区
客体： 被动根据指令返回数据或接受指令的数据，callee - io 数据库，共享变量
访问粒度：
  单一客体，访问不同部分？数据库 库/表/行/字段；生产者/消费者，访问buffer中某个元素
  多个客体，
目标：1. 每个单一主体视角下得到正确的结果 - 隔离性
     2. Avaliability/Performance
     2. 整体视角（有没有？）

有的资源可多副本：
  多副本强一致：CPU cache(?)，数据库强一致，对主体来说相当于单副本，无需额外处理；强一致达成-共识算法。 外部一致性
  非强一致：不同主体看到的快照不同。最终一致/补偿。
  多副本是时空视角下的多副本，最常见的不同节点的本地数据同步；单个节点下的快照技术也应该归为多副本，比如数据库中MVCC实现
  强一致=Linearizability+Serializability。多主体下的Linearizability：各主体对操作顺序和每个操作的结果达成一致，而无法确定绝对时间下的顺序
  多副本：内部主体：进行同步的进程；客体：被同步的数据

问题：
原子客体+单主体 ->
原子客体+多主体 -> 锁，事务：从单个主体角度，看不到其他主体的影响；综合所有主体作为客体，满足或不满足外部一致性
非原子客体+多主体 -> 锁的粒度，强度等满足不同模型（生产者消费者/哲学家就餐）不同隔离性级别；是否拜占庭；满足或不满足外部一致性。广义来说，实现了外部一致性的算法都可以成为共识算法？

多副本： - 非原子客体+多主体的一种形式
强一致/外部一致 - 单个原子客体对外还是原子客体 - 对内，通过共识算法来实现
非强一致 - 单个原子客体对外为非原子客体

锁：
  手段 mutex，lock，monitor，read/write lock，semaphore, event

partition vs replication

建模：
  在一定的限制条件内讨论
    如果现实不满足限制条件，算法应该以何种方式失败。能检测出来条件不满足，算法停止 vs. 检测不出来，给出错误结果
  任何限制条件的细微差别都可能导致不同的算法/性能优化/一致性/availability差异

原子性跟分布式什么关系？

data replicas -> 一致性 共识 -> data repliaca 和leader election 本质一样？

producer, consumer
resource: whole buffer
mutex on buffer should do


distributed system:
整体
https://cloud.tencent.com/developer/article/1422177
https://www.zhihu.com/question/23645117
http://book.mixu.net/distsys/ http://book.mixu.net/distsys/single-page.html

时钟：
解决分布式系统下的先后顺序问题： 逻辑时钟 向量时钟 http://yang.observer/2020/07/26/time-lamport-logical-time/

consistency
http://blog.kongfy.com/2016/08/%E8%A2%AB%E8%AF%AF%E7%94%A8%E7%9A%84%E4%B8%80%E8%87%B4%E6%80%A7/
https://www.jiqizhixin.com/articles/2020-02-20-3
http://blog.kongfy.com/2016/05/%e5%88%86%e5%b8%83%e5%bc%8f%e5%85%b1%e8%af%86consensus%ef%bc%9aviewstamped%e3%80%81raft%e5%8f%8apaxos/


cap
C： all nodes see the same data at the same time. <- 要求所有节点。从结果的视角来描述？
侧重点是可用性和一致性的妥协
https://timilearning.com/posts/ddia/part-two/chapter-9-1/ 里认为cap里的C是Linearizability
https://stackoverflow.com/questions/12346326/cap-theorem-availability-and-partition-tolerance
https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/ - 值得看
https://codahale.com/you-cant-sacrifice-partition-tolerance/
http://ksat.me/a-plain-english-introduction-to-cap-theorem

consensus：
就单一事项达成一致意见，不依赖中心节点
单一事项：一次leader election 数据库事务（单个事务？）
不要求所有节点可用 <-
共识算法是达成一致性的手段。共识侧重从过程的视角来描述。

consensus: paxos raft

DB ACID - 跟数据replica没关系，主要是多事务（并发）
C：内部一致性，数据库内部状态保持正确，满足数据完整性要求。


单节点多进程和跨节点 本质区别是什么（通信不可靠？）

coroutine:
python/rust async/await
eventloop + yield/send/channel
refs: mio tokio
goroutine is beyond coroutine

