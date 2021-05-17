并发 -> 资源共享
因为有资源共享，所以需要同步
资源如何共享
单一资源 -- critical section; race condition;

多个资源 -- 死锁

手段 mutex，lock，monitor，read/write lock，semaphore, event


producer, consumer
resource: whole buffer
mutex on buffer should do