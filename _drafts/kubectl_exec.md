kubernetes 总体架构和代码目录结构 https://www.guoshaohe.com/cloud-computing/kubernetes-source-read/1249

kubectl exec 较详细实现：https://cloud.tencent.com/developer/article/1632735
http://www.xuyasong.com/?p=1908
https://www.cnblogs.com/gaorong/p/11873114.html

kubectl:
ExecOptions.Run():exec.go
  DefaultRemoteExecutor().Execute:exec.go
    remotecommandserver.NewSPDYExecutor():remotecommand.go
    streamExecutor.Stream():remotecommand.go
      streamProtocolV4.stream():remotecommand/v4.go
        streamProtocolV4.createStreams():remotecommand/v4.go
          streamProtocolV3.createStreams():v3.go
            streamProtocolV2.createStreams():v2.go
        watchErrorStream():errorstream.go
        p.copyStdout():v2.go
          io.Copy():

apiserver:
ExecRest.Connect():rest/subresources.go
  ExecLocation():pod/strategy.go
    streamLocation():

kubelet:
Server.getExec():server.go
  Kubelet.GetExec():kubelet_pods.go
    kubeGenericRuntimeManager.GetExec:kuberuntime_container.go
      instrumentedRuntimeService.Exec:instrumented_service.go
        RemoteRuntimeService.Exec():remote_runtime.go
          runtimeServiceClient.Exec:cri-api/.../api.pb.go
            Invoke(ctx, "/runtime.v1alpha2.RuntimeService/Exec", in, out, opts...


error stream 怎么用的？

复现问题
重启kubectl连接的apiserver即可复现kubectl exec exit code = 0。
猜测可能因为server端重启，tcp connection正常关闭，io.copy是正常EOF结束，并不会出问题

如果网络中断会keepalive探测 - 结果未知


tips

编译kubectl binary，带debug信息；
make kubectl GOLDFLAGS=""

连远程
sudo iptables -t nat -I  OUTPUT -d 10.20.0.3/32 -p tcp -m tcp --dport 6443 -j DNAT --to-destination 172.45.0.101
sudo iptables -t nat -I POSTROUTING -d 172.45.0.101/32 -p tcp -m tcp --dport 6443 -j MASQUERADE
