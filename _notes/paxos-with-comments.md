---
layout: post
title: 《Paxos Made Simple》论文翻译和注解
tags: paxos distributed-system
date: 2022-07-13
update: 2022-07-19
---

> Note:
>
> paxos算法最初在论文《The Part-Time Parliament》中提出，比较难理解，Lamport在《Paxos Made Simple》中做了重新描述，相对易于理解。
> 以下是对《Paxos Made Simple》的全文翻译，力求忠于原论文。译者的个人理解以及说明以本段相同的格式插入在各章节。

## 1 引言
很多人认为实现容错分布式系统的Paxos算法比较难懂，可能因为原始的描述对很多读者来说非常晦涩。实际上，它是最简单和显然的分布式算法之一。它的核心是个共识算法 - [5]中的‘synod’算法。
下节显示这个共识算法几乎是从我们想让它满足的特性中必然产生的。最后一节解释了完整的Paxos算法，它从在状态机方法中如何取得共识这个简单应用中推出，状态机方法可以用来构建分布式系统。
该方法是众所周知的，因为这是在分布式系统理论中经常引用的文章[4]的主题。

## 2 共识算法
### 2.1 问题描述
假设一组进程，这些进程可以提议值。共识算法确保能选定某一个选定的值。如果没有提议值，那么也不会选定值。如果值被选定，那么进程应该可以学习到该值。共识的safety需求如下：

* 只有被提议的值才可能被选定
* 只能选定一个值
* 进程在值被选定之后才会学习到该值

我们这里不说明精确的liveness需求。但是，liveness的目标是保证某些提议的值最终被选定，而且，如果选定了一个值，进程最终可以学习到该值。我们令共识算法中的三个角色由三种agent来执行：proposer, acceptor和learner。在实现中，某个进程可以有多个角色，但是这里我们并不关心角色到进程的映射关系。

假设agent可以通过发消息来进行通信。我们使用典型的异步，非拜占庭模型，即：

* agent的执行速度任意，可能因停止或重启而失败。所有agent都可能在一个值被选定之后失败，然后重启，因此除非失败后重启的agent可以记住之前的某些信息，否则没有解法。
* 消息可能延迟任意长时间，重复，丢失，但是不会损坏。

### 2.2 选定一个值
选定一个值最简单的方式是只有一个acceptor。proposer给acceptor发送一个提议，acceptor选定它收到的第一个值。这个方案虽然简单，但是一旦这个acceptor故障就无法继续。

所以我们尝试另外一个选定值的方案。现在我们使用多个acceptor。proposer给一组acceptor发送提议。一个acceptor可以接受该值。当足够多的acceptor接受同一个值时，这个值就被选定。
多少acceptor才能足够？我们选取任何一个多数子集，因为任何两个多数子集都有至少一个相同的acceptor，如果acceptor最多只能接受一个值，那么就可以保证只有一个值被选定。

在不存在失败和消息丢失的情况下，即使只有一个proposer 提议了一个值，我们也需要可以选定一个值。这需要：

*P1. acceptor必须接受它收到的第一个提议。*

这个需求会引起一个问题。不同的proposer在大概同时可以提议不同的值，那么有可能有以下情况：每个acceptor都接受了一个值，但是没有值被大多数acceptor接受。即使只有两个提议的值，如果每个都被一半的acceptor接受，一个acceptor的失败都可能导致无法选定一个值。

P1和值只有在多数acceptor接受的情况下才能被选定的需求隐含了一个acceptor必须被允许接受多个提议。我们给每个提议指定一个号码，来标记acceptor可能接受的不同提议，因此提议包含号码和值。为了避免混淆，我们要求不同的提议有不同的号码。如何达成取决于实现，暂时我们假定如此。当某个提议被大多数acceptor接受时，这个提议的值被选定。在这种情况下，我们说这个提议（和它的值）被选定。

我们允许选定多个提议，但是必须保证所有选定提议的值相同。通过引入提议号码，我们要保证：

*P2 如果一个值为v的提议已经被选定，任何被选定的号码更高的提议的值也需要是v。*

因为号码是全序的，P2保证了关键的safety特性，即只能选定一个值。

> Note:
>
> 每个提议需要包含号码和值。
>
> 每个提议有不同提议号码是指号码全局不同，即使不同的proposer提出的提议号码也不能相同。
>
> 为什么允许选定多个提议？因为无法限制选定一个提议后就不会提出/收到新的提议。从单个acceptor的角度，它并不知道一个提议已经被选定，它只是根据一定的规则接受提议。
> 而且，从后文可以知道，选定提议后learner也不一定学习到；不同的proposer可以同时提出提议等。

一个提议只有被至少一个acceptor接受，才能被选定。因此，可以通过满足以下条件来满足P2：

*P2a. 如果一个值为v的提议已经被选定，任何acceptor接受的更高号码的提议的值都是v。*

我们仍然需要P1来确保有提议被选定。因为通信是异步的，即使某个acceptor c没有收到任何提议，提议也可能被选定。假设一个新的proposer回归，提议了一个号码更高的值，但是与之前选定的值不同。P1要求c接受这个提议，但这违反了P2a。要同时满足P1和P2a，需要把P2a强化为：

*P2b. 如果一个值为v的提议已经选定，那么任何proposer提议的更高号码的proposal的值为v。*

因为一个提议必须有proposer提出才能被acceptor接受，所以P2b隐含了P2a，进而隐含了P2。

> Note:
>
> P1和P2a无法同时满足，把P2a强化为P2b。满足P2b一定满足P2a，反之不然。

为了找出如何满足P2b，我们先来考虑我们怎么证明它。
假设已选定提议(m, v)，那么我们要证明任何号码n>m的提议的值也是v。
通过对n使用归纳法可以更容易的证明这点。如果有以下额外条件，我们可以证明号码为n的提议的值为v：
号码在m..(n-1)的每个提议的值都为v，其中i..j表示从i到j的号码集合。
如果号码为m的提议被选定，则一定有某个acceptor组C，其中包含了大多数acceptor，而且其中的每个acceptor都接受了这个提议。结合归纳假设，m被选定的假设隐含了：

C中的每个acceptor都接受了号码在m..(n-1)之间的一个的提议，而且被任何acceptor接受的号码在m..(n-1)中的每个提议的值为v。

因为任意包含大多数acceptor的集合S都包含至少一个C中的acceptor，我们可得满足以下不变式可保证号码为n的提议值为v：

*P2c. 对任意v和n，如果提议(n,v)被提出，那么有一个包含大多数acceptor的集合S，满足(a)S中的acceptor都没有接受号码比n小的提议，或者(b) 被S中的acceptor接受的号码比n小的所有提议中号码最高的提议的值也是v。*

通过保证P2c不变式可以满足P2b。

> Note:
>
> 转述一下P2c：对于任意被提出的提议(n, v)，都存在某个多数派acceptor集合S，满足上述a或b。
>
> 满足P2c不变式即可满足P2b的证明：
>
> 在提议(m, v)被选定且满足P2c不变式的情况下，我们对提议(n, Vn)进行归纳(其中n>m)：
>
> 1. Vm = v
> 2. 对任意提议(n, Vn)，如果提议Vm == Vn-1 == v，那么Vn == v
>
> 根据数学归纳法，则有对任意n>=m，都有Vn==v。其中Vi表示号码为i的提议的值。
>
> Ref： 数学归纳法
>
> * https://en.wikipedia.org/wiki/Mathematical_induction
> * https://www.zhihu.com/question/65412135

为了保证P2c不变式，proposer要想提出号码为n的提议，就必须知道所有号码小于n的提议中号码最大的提议，这些提议已经或者将要被某些多数派acceptor所接受。知道已经被接受的提议很容易，预测将要被接受的提议比较难。为了规避预测将来，proproser通过要求不能有这种提议被接受来达到这一点。换句话说，proposer要求acceptor不能再接受号码小于n的提议。因此proposer采用如下算法提出提议：

1. proposer选择一个新的提议号码n然后给某些acceptor集合中的每个成员发送请求，要求他们以下回应：
   a)承诺不再接受号码小于n的提议
   b)如果有已经接受的号码小于n的提议，回复该提议。
   把这个请求称为号码为n的prepare请求
2. 如果这个proposer从acceptor的某个多数派收到了请求的回复，那么它可以提议(n, v)，其中v是所有回复中号码最高的提议的值，或者如果回复中没有提议，那么由该proposer选择值。

proposer通过给某个集合的acceptor发送一个‘接受提议’的请求来提出提议。（这里的acceptor集合跟上述初始请求中的集合可以不一样。）把这个请求称为accept请求。

上面描述了proposer的算法。acceptor呢？它可能从proposer收到两种请求：prepare请求和accept请求。acceptor可以忽略任何请求，而不会违反安全性。
那么，我们只需要关注它什么时候被允许回复一个请求。acceptor总是可以回复prepare请求。acceptor可以回复一个accept请求来接受这个请求，当且仅当它没有承诺不接受该请求。换句话说：

*P1a. acceptor可以接受号码为n的提议，当且仅当它还没有回复号码大于n的prepare请求。*
注意到P1a包含P1。

> Note: 如何理解P1a 包含 P1?
>
> *P1. acceptor必须接受它收到的第一个提议*
>
> P1提出时还没有把提议可拆分成prepare和accept两个请求，也没有可以不接受某些请求的这种概念。
> 在当前context下，应该把P1重新表述为：acceptor必须接受它收到的第一个*可接受的*提议。而P1a其实意味着acceptor接受所有*可接受的*提议。从而，满足P1a就一定会满足P1。
> stackexcnahge 上有个这个问题的讨论：https://cs.stackexchange.com/questions/77112/paxos-made-simple-two-details/152907

> Note:
>
> P2可以保证safety特性，但是P1满足不了liveness。P1只能保证没有消息丢失/乱序情况下的liveness。P1a提供了更好的结果，但也不能保证liveness。如2.4讨论的情况下

我们现在有了选定一个值的完整算法，而且可以满足safety特性 -- 前提是唯一的提议号码。通过一点小的优化得到最终算法。
假设一个acceptor收到了号码为n的prepare请求，但是它已经回复了号码大于n的prepare请求，因此已经承诺不会接受任何号码为n的新提议。那么这个acceptor不应该回复这个新的prepare请求，因为它不会接受这个proposer将会提出的号码为n的提议。因此我们让acceptor忽略这种prepare请求。acceptor也应该忽略它已经接受的提议的prepare请求。

通过这个优化，acceptor只需要记住它已经接受的最高号码的请求以及它已经回复的prepare请求的最高号码。因为P2c必须保持不变性，即使失败，acceptor必须记住这个信息，即使它失败后重启。
注意proposer总是可以废弃一个提议并且忘记它，只要它不会使用同样的号码提出另一个提议。

把proposer和acceptor的动作放到一起，算法可以分为两个阶段：

1. Phase 1.
   * proposer选择提议号码n，给acceptor的大多数发送号码为n的prepare请求
   * 如果一个acceptor收到号码为n的prepare请求，且n大于它已经回复的任何prepare请求，它回复该请求，回复内容为承诺不会接受任何小于n的提议，以及它已经接受的最高号码的提议（如果有）。
2. Phase 2.
   * 如果proposer从某个多数派收到了号码为n的prepare请求的回复，它给这些acceptor发送accept请求，内容为提议(n, v)，其中v是这些回复中号码最高的提议的值，或者如果回复中没有提议，那么由该proposer选择的值。
   * 如果acceptor收到accept请求，其提议号码为n，它接受该提议，除非已经回复了一个更高号码的prepare请求。

proposer可以提出多个提议，只要每个提议都遵循如上算法。它可以在协议过程中的任何时间废弃一个提议。（正确性仍会保证，即使请求和/或回复可能在提议废弃后才到达。）如果有proposer已经开始提出更高号码的提议，那么最好废弃当前提议。因此，如果acceptor因为已经收到了更高号码的prepare请求而忽略了prepare或accept请求，那么它最好通知proposer。然后该proposer废弃该提议。这是个性能优化，不会影响正确性。

> Note: 怎么理解已选定一个值?
>
> 一旦某个多数派acceptor 接受了某个提议，就已经选定了这个提议的值，即使因为各种原因，部分或全部learner没有学习到该值。

> Note:
>
> acceptor的phase 1和2需要是串行的。否则，假如 acceptor在处理号码为n的prepare请求，同时在处理号码为n-1的accept请求，而且它已经接受了n-2的accept请求。在prepare请求的处理中，它不能直接回复提议n-2，因为它有可能会接受n-1。如果它在回复n的prepare之后接受了n-1提议，它的回复就是错误的，因为它承诺了不会接受小于n的提议。
>
> 根本原因是两个阶段acceptor逻辑有race。acceptor的两个阶段中需要共享数据：`已接受的提议`和`可以接受的最高提议号码`。

> Note: 2.2节整体思路
>
> 论文2.2节的基本逻辑是从需求反推条件。比如为了为了满足safety，满足P2是一种可能性，进而反推出P2a，P2b，P2c，最终得到一个可操作的算法。
> 反推出来的都是充分条件而不一定是必要条件。比如也许不一定只有P2b才能满足P2a，有可能通过其他条件也可以。
>
> 注意到算法最终落在各agent的每个步骤都只需要本地的信息，因为agent可操作的步骤只能使用它本地的信息，否则需要更多通信。
>
> P2/P2a/P2b 都有个前提，‘如果一个提议被选定’，但是对acceptor或proposer来说，它无法准确知道这个信息(如上所说，一个值被选定并不意味着其他agent会了解到这个信息)。P2c非常巧妙地绕开了这一点，是的agent只需要自己本地的信息就可做出决定。

### 2.3 学习选定的值
要想学习一个选定的值，learner必须知道一个提议被多数acceptor接受。最明显的算法是对任何acceptor,当它接受提议时，给所有learner回复，把该提议发送给他们。这允许learner尽快发现选定的值，但是它需要每个acceptor给每个learner响应——响应的总数量是acceptor数量和learner数量的乘积。

非拜占庭错误的假设使得learner可以从其他的learner学习到接受的值。我们可以让acceptor把响应回复给一个特殊的learner，然后该learner在值被选定后通知其他learner。这种方法需要额外一次交互，所有learner才能学习到选定的值。这个方法可靠性也更低，因为这个特殊的learner可能失败。但是它需要的响应数执行acceptor数量和learner数量之和。

更通用的，acceptor可以给一组特殊的learner发送响应。其中的每个learner在值被选定后都可以通知所有其他learner。这个特殊集合的learner数量越多，会带来更高的可靠性和更高的通信复杂性代价。

因为消息丢失，有可能值被选定，但是没有任何learner学习到。learner可以询问acceptor接受了什么提议，但是acceptor失败可能导致不可能确定是否有一个多数派接受了某个提议。在这种情况下，learner只有在新的提议被选定后才能知道选定的值。如果一个learner想知道是否有值被选定，它可以使用上述算法要求proposer提出提议。

> Note:
>
> 如上所述，learner可能没有学习到某个选定的proposal的值，但是它可以通过向acceptor询问或者要求proposer重新提议来最终学习到。
> 但是learner怎么知道有新的值要学习？正常情况下，不需要learner主动去学习，上面的几种方案中，都会把选定的值主动通知给learner。
> 但是消息丢失，learner没有学习到的情况下，可以通过某些方法（比如检测超时或者检测网络分区恢复等），由learner在某些条件下触发主动学习。
>
> 怎么知道所有learner都已经学习到了选定的值？不需要所有learner都学习到。理论上learner可以在选定后任何时间在paxos算法框架内学习到选定的值。
> 实际实现中工程上需要其他方案来解决，比如镜像/直接同步，来避免需要永远保留算法的状态。

### 2.4 Progress
很容易构造一个场景，两个proposer各自一直提出提议，提议号码一直增加，但是无法选定某个值。Proposer p 提出号码为n1的提议，并完成phase 1。然后另一个proposer q 完成phase1，提议号n2>n1。p的phase 2 中acceptor不会接受号码为n1的的提议，因为这些acceptor都已经承诺不会接受号码小于n2的提议。然后 p 使用新的号码为n3的提议开始phase1, 其中n3>n2，导致q的phase2中，accept请求被忽略。以此循环。

为了保证活性，必须选择一个特殊的proposer，只有这个proposer才会尝试提出提议。如果这个特殊的proposer可以和acceptor中的大多数成功通信，而且它使用的提议号比其他已使用过的都大，那么它可以成功提出一个被接受的提议。如果它知道已有其他更高号码的proposal，它只需废弃当前提议，并提起一个更高号码的提议。这个proposer最终总可以选定一个足够大的提议号码。

如果系统的足够部分(proposer, acceptor, 通信网络)工作正常，liveness可以通过选举一个特殊的proposer来达成。论文[1]的结果说明选举proposer的可靠算法必须使用随机或实时--例如超时。但是不管选举是否成功，safety都是可保证的。

### 2.5 实现
Paxos 算法[5] 假定了一个进程网络。在它的共识算法中，每个进程都作为proposer，acceptor和learner角色。算法选择一个leader来作为特殊proposer和特殊 learner。Paxos共识算法和上述算法是完全等价的，其中请求和响应作为一般消息来发送。（响应消息使用对应的提议号码来标记以防止混淆）。持久存储在失败后可以保留数据，用来维护acceptor必须记住的数据。acceptor在发送响应之前在持久存储上记录要发送的响应。

剩余的问题是如何保证任何两个提议的号码不能一样。不同的proposer在不相交的号码集合中选择号码，因此两个不同的proposer提出的提议号码肯定不同。每个proposer在持久存储中记录它试图提出的提议的最大号码，然后在新的提议使用更大的号码。

> Note:
>
> 无法保证所有提议的号码随时间全局递增。从物理学上来讲，时间不是绝对的，而且信息的传递需要时间，从不同proposer的视角，提议的顺序可能是不一样的，没有一个全局视角可以确认提议的顺序。
> 但是这不会影响算法的正确性。 acceptor可以直接忽略低号码的提议，或者提醒proposer已经有更高号码的提议（2.2节末提到的性能优化）。
>
> 工程实现上，实现几乎全局递增并不很难，例如可以把提议号跟时间戳相关。在leader切换不频繁以及时间同步的情况下，基本可以实现全局递增。

## 3 实现一个状态机
实现一个分布式系统的简单方式是实现为一组client向一个中心化的server提交命令。这个server可以被描述为一个确定性状态机，它以一定的顺序执行client命令。状态机有当前状态，每一步以一个命令作为输入，生成输出和新状态。例如，一个分布式银行系统的client可能是出纳，状态机状态可能包含所有用户的账户余额。取款可以通过执行状态机命令：当且仅当余额大于等于取款额时，从余额里减掉取款额，输出为新余额和旧余额。

使用单个中心化server的实现中，如果这个server失败，整个系统就失败。因此我们使用一组server，每个server独立实现状态机。因为状态机是确定性的，如果执行相同的命令，所有的server会产生同样的状态序列和输出。那么执行命令的client可以使用任何server的输出。

为了保证所有server执行相同的状态机命令序列，我们实现paxos共识算法的一系列不同的实例。第i个实例选定的值作为该序列中的第i个状态机命令。
在算法的每个实例中，每个server都有所有角色（proposer, acceptor, learner）。到目前为止，假设server集合是固定的，因此共识算法的所有实例使用的是同样的agent集合。

正常操作中，某个server被选举为leader，它在算法的所有实例中都作为特殊proposer（只有该proposer才会提出提议）。client给leader发送命令，leader决定每个命令在序列中的位置。
如果leader决定某个client命令应该是第135个命令，它会把这个命令作为共识算法第135个实例的值。这通常会成功，也会因失败或有另外一个server也认为自己是leader，但是认为第135个命令不一样而失败。
但是共识算法保证了最多只有一个命令可能被选定为第135个。

> Note: 怎么识别不同实例?
>
> 在各个请求中添加一个实例号。

这个方法的效率的关键在于，在paxos共识算法中，直到phase 2才选择要提议的值。如前所述，在proposer的phase 1完成后，要提议的值要么已经确定，要么proposer可以任意提议一个值。

接下来先描述paxos状态机实现在正常操作下如何工作的。然后讨论可能出问题的地方。考虑当之前的leader 失败，新leader被选举的情况下会发生什么。（系统启动是一个特殊情况，这种情况下任何命令都还没有提议。）

新leader，作为共识算法所有实例中的learner, 应该知道绝大多数已经被选定的命令。假设它知道命令1-134, 138, 139, 即共识算法的第1-134, 138, 139实例选定的值。（后面我们说明命令序列中这种空缺是如何产生的。）然后它执行135-137以及大于139的实例的phase 1。（后文描述怎么做。）假设这些执行的结果只确定了实例135和140提议的值，没有确定其他实例的。leader接着会执行135和140的phase2, 然后选定了135和140的命令。

这个leader，以及其他学习到这个leader知道的命令的其他server，现在可以执行命令1-135。但是，它不能执行命令138-140，虽然它也知道这些命令，因为命令136和137还没有被选定。这个leader可以把client请求的接下来两个命令作为136和137命令。作为替代，我们也可以通过提议两个noop命令（不会改变状态机状态）来立即填充空缺。（通过执行共识算法的136和137实例的phase 2。）一旦这些noop 命令被选定，138-140也可以被执行。

> Note: 为什么由leader来决定命令对应的位置，而不是client？
>
> 个人理解取决于业务逻辑。如果只是为了实现确定性状态机，只要保证所有server的顺序一致即可。实际应用中可能是写顺序日志，这种情况下，顺序应该是在paxos算法之外决定的。
> 本文没有讨论到client的逻辑，例如如何处理命令结果（从任一server都可以获取，但是需要考虑失败情况以及没有达成共识情况：例如leader接到client命令后就失败了，没有发出提议）。这些应该也是跟业务逻辑有关，是共识算法之外的内容。

现在已经选定了命令1-140。leader也完成了大于140的共识算法实例的phase 1，可以在这些实例的phase 2中提议任何值。它把命令号141赋予client请求的下一个命令，并把他作为共识算法141实例的值。把下一个收到的client命令作为命令142，以此类推。

这个leader可以在它知道到它提议的141命令被选定之前就提议命令142。有可能它发送的提议命令141的所有消息都丢失了，有可能在任何其他server学习到leader提议的命令141之前命令142被选定。当leader没能收到141 phase2消息的预期回复时，它会重传这些消息。如果一切正常，它提议的命令会被选定。但是，它有可能失败，导致选定命令的序列有缺口。总之，假设一个leader可能提前收到a个命令 - 即，它可以在命令1 ~ i被选定后提议命令i+1到i+a。最多可能产生a-1个命令缺口。

新选定的leader可以为无限多的共识算法实例执行phase 1——在上面的场景中，为实例135-137以及大于139的实例。为了达到这个目标， 新leader可以为所有实例使用相同的提议号，那么可以通过发送单个相当短的消息给其他server。在phase 1，acceptor只有在它已经收到其他proposer的phase2 message时才会回复除了简单的OK外的其他内容。（在当前场景下，只有实例135和140是这种情况。）因此，server（作为acceptor）可以给所有实例回复一个相当短的消息。执行这些无限多的实例的phase 1没有问题。

> Note:
>
> 相当于把所有实例的phase 1合并在一起，使用同一个提议号。上面的例子中，phase1的acceptor回复内容为：135和140的已接受的最高号码提议，其他所有实例的OK。
> 实现上，prepare的时候使用的提议号n在单个server上是递增的，跟具体哪个paxos实例无关。

因为leader失败以及重新选举leader应该是极少情况，执行一个状态机命令的有效代价（即在命令/值上取得共识）是执行共识算法phase 2 的代价。[2]显示paxos共识算法在故障存在情况下达成一致的算法中是代价最小的。因此paxos算法本质上是最优的。

上述系统一般操作的讨论假定一直有单个leader，除了在当前leader失败和选举新leader的间隙。在异常情况下，leader选举可能失败。如果没有server作为leader，那么没有新命令被提议。如果多个server认为他们是leader，那么他们都可能在同一个共识算法实例中提议值，这会使得有可能无法选定值。但是，safety是保证了的 —— 两个不同的server永远不会在第i个状态机命令上不一致。单个leader的选举只是为了保证活性。

> Note:
>
> paxos算法中把leader选举和共识算法分开讨论，paxos本身并没有涉及到如何选举leader。单一leader可以保证活性，但是永远有且只有一个leader本身是无法保证的。
> 实际工程实现中的leader也并不需要保证一时刻只能有一个。有多个的情况下只是影响性能，而不会影响正确性。
> 所以可以有很简单的方案来实现leader选举，例如在proposer和acceptor在一起的情况下，某个agent如果收到其他proposer提出的的accept 请求消息，这个agent的proposer就暂停提议，相当于放弃当leader。

如果server集合可以变化，那么必须有某种方法决定哪些server实现共识算法的哪些实例。最简单的方式是通过状态机本身来实现。server的当前集合可以作为状态的一部分，可以通过普通的状态机命令来修改。我们可以允许leader提前获取a个命令，通过让执行实例i+a的server集合作为执行第i个状态机命令的状态。这给任意复杂的重配置算法提供了一个简单的实现。

> Note:
>
> 章节3的状态机实现就是multi paxos。这篇论文只是没有明确提出multi paxos/basic paxos这种说法。在2007年《paxos made live》论文中已经在使用这种说法，在这之前也有，之后明显变多（根据google scholar搜索结果）

## 参考文献
[1] Michael J. Fischer, Nancy Lynch, and Michael S. Paterson. Impossibility of distributed consensus with one faulty process. Journal of the ACM, 32(2):374–382, April 1985.

[2] Idit Keidar and Sergio Rajsbaum. On the cost of fault-tolerant consensus when there are no faults—a tutorial. TechnicalReport MIT-LCS-TR-821, Laboratory for Computer Science, Massachusetts Institute Technology, Cambridge, MA, 02139, May 2001. also published in SIGACT News 32(2) (June 2001).

[3] Leslie Lamport. The implementation of reliable distributed multiprocess systems. Computer Networks, 2:95–114, 1978.

[4] Leslie Lamport. Time, clocks, and the ordering of events in a distributed system. Communications of the ACM, 21(7):558–565, July 1978.

[5] Leslie Lamport. The part-time parliament. ACM Transactions on Computer Systems, 16(2):133–169, May 1998.
