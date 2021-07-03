分布式系统与并发

并发 -> 资源共享
因为有资源共享，所以需要同步
资源如何共享
单一资源 -- critical section; race condition;

多个资源 -- 死锁

手段 mutex，lock，monitor，read/write lock，semaphore, event


producer, consumer
resource: whole buffer
mutex on buffer should do


distributed system:
整体
https://cloud.tencent.com/developer/article/1422177
https://www.zhihu.com/question/23645117

consensus: paxos raft
consistency
http://blog.kongfy.com/2016/08/%E8%A2%AB%E8%AF%AF%E7%94%A8%E7%9A%84%E4%B8%80%E8%87%B4%E6%80%A7/
https://www.jiqizhixin.com/articles/2020-02-20-3
http://blog.kongfy.com/2016/05/%e5%88%86%e5%b8%83%e5%bc%8f%e5%85%b1%e8%af%86consensus%ef%bc%9aviewstamped%e3%80%81raft%e5%8f%8apaxos/


cap
https://stackoverflow.com/questions/12346326/cap-theorem-availability-and-partition-tolerance
https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/ - 值得看
https://codahale.com/you-cant-sacrifice-partition-tolerance/
http://ksat.me/a-plain-english-introduction-to-cap-theorem

单节点多进程和跨节点 本质区别是什么（通信不可靠？）

coroutine:
python/rust async/await
eventloop + yield/send/channel
refs: mio tokio
goroutine is beyond coroutine

共识：就单一事项达成一致意见
单一事项：一次leader election 数据库事务（单个事务？）


