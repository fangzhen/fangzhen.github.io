
1. error 没有trace，难以定位到出错位置
https://stackoverflow.com/questions/33034241/how-to-get-the-stack-trace-pointing-to-actual-error-reason

2. ununsed 变量强制错误。在debug时不方便

3. 变量分配在栈或堆，在语言层面是未定义的。编译器会根据需要选择。
https://stackoverflow.com/questions/10866195/stack-vs-heap-allocation-of-structs-in-go-and-how-they-relate-to-garbage-collec
