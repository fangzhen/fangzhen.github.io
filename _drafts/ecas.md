before 2.1 -> 3.4.0 -> 4.0.2

centos 6->7 升级 3.4.0（Liberty）
  问题：OS/kernel需要升级
  不再跟社区
  upstream repo 维护 & 更新
  ES rpm维护 -> 引入jenkins； devops
  puppet脚本问题处理
    systemd

V4->V5融合架构 5.0.1-1
  问题：产品化程度低；客户侧部署不受控，没有标准化，大量时间耗费在解决客户问题；技术上容器化浪潮，产品整体架构重构；公司整体战略-重视超融合
  从零开始实现ECAS核心引擎coaster
    复用现有部署脚本
  新coaster-agent
  ECAS迁移
  重新设计产品逻辑
  新的产品质量流程和要求
  技术难题：
    celery等
  产品和工程难题：
    产品取舍，变化，优先级，最开始没有想清楚，产品没有工程和架构视野
    工程工作量预估，反过来影响产品取舍
  特点：
    可进化，可升级（ECAS可自我升级）
    受控部署，标准硬件，标准拓扑
    奠定了至今ECAS的基本形态

V5 认证架构 & 解决方案架构 V5.0.3-1
  目标：针对中大规模客户，非软硬一体
  大规模

V6 6.0.1 - 6.0.2
  ARM架构
  OTA与平台升级
    平台升级新实现
    OTA
  ess-automation独立
  coaster-agent优化
  一云多芯

V6 6.1.1
  拓扑与License分离


## 重构

coaster任务引擎
- subtask error后重试，状态仍显示error
- 信息展示：task 日志分散；部分日志存数据库 result字段，占用空间多，用处不大
- 重试次数不能修改 - conductor的三次重试；async client的重试等带来的问题
- timeout管理机制：timeout失败后进程可能还在；api侧timeout
- 对mariadb和rabbitmq依赖 - 这两者出问题，比较难report上来
- celery：版本低，需要升级
- 事务：授权过程等
- 上传license，即使license正常有时候失败：
- 疑难问题：EAS-72718 EAS-77701

代码组织
- 有一些其他组件的脚本维护在ECAS，如系统配置调整，grub参数，维护脚本等。
- ESS部署
- puppet脚本是否需要重写

操作系统安装：
- cobbler 相关

对外接口
- rest api慢（数据库访问慢；字段没有过滤；分页）node 列表，constraints等
- 其他组件调用ecas接口标准化（update_settings; custom-ark）
- PVC中的数据
- misc api的认证
- api接口文档

Dashboard & client：
需要根据新的ECP规范重写
多区域支持

功能需求：
- 界面配置：超售比，ntp, dns，dhcp范围
- 灵活角色配置
- 驱动支持

操作限制
- 操作限制的维护
- 操作限制的实现
- 友好的提示

测试：
- 自动化测试
- agent测试
- 大规模
  dry-run mode

License & 拓扑工具
- License中配置各种参数
- license工具的稳定性/可用性
- 拓扑工具需要模块化，可嵌入的。例如https://easystack.atlassian.net/browse/EAS-50360 （ESS检查磁盘配置是否合理） https://easystack.atlassian.net/browse/EAS-43704 （master需要奇数个）
- License工具权限管理

其他
- 对接，邮件配置等非核心功能的维护
- 变更：代码修改很难变更


https://ethercalc.easystack.cn/itay34upabwv

磁盘分区：
volume/manager.py:
reset()
  create_service_partition: 10M unallocated + 64*2M lvm meta

format_to_simple:
  size = raw_size - 10 - 128

format_to_full:
  pv_size = simple_pv_size + 64

root分区大小：
os_vg_size - 4G(swap)

lvm meta 实际并没有特别指定为64M,而是默认的1020K

pmanager:
 1M reserve
 24M bios_boot
 200M efi
 250M boot
以上相加<500M
其他分区往后排

修改后
去除lvm meta相关逻辑
去除10M unallocated
只管理boot,os,docker （boot & lvm）


本地cube build
1. tox.ini genconfig 指定python2。当前版本不支持python3
   `basepython=python2`
2. tox -e genconfig
3. 进入genconfig venv执行
   3.1 oslo-config-generator --config-file etc/oslo-config-generator/kolla-build.conf
   3.2 修改对应组件的代码地址和分支
   ```
   [topology-base]
   location = /home/fangzhen/develop/easystack/topology-operators
   reference = dev
   ```
   3.3 执行如下命令
sudo python tools/build.py topology-base --type source --skip-parent --base escloud-linux --registry hub.easystack.io --config-file ./etc/kolla/kolla-build.conf --namespace production --tag 5.0.1 --retries 0
4. 如果有依赖其他镜像，需要手动tag到正确版本，公司hub上tag不全
   4.1 /etc/hosts
   `172.38.0.2  hub.easystack.io`
   4.2
   ```
   docker pull hub.easystack.io/production/escloud-linux-source-base:6.0.1
   docker tag hub.easystack.io/production/escloud-linux-source-base:6.0.1 hub.easystack.io/production/escloud-linux-source-base:5.0.1
   ```


手动步骤：
1. rebuild: py2-pack, bootstrap image, iso
2. 更改heat template： 1. iso name 2. add to .bashrc: export ECAS_BACKEND=kubernetes


- import turbo resources
  make all
  bash sync.sh sync_turbo
- create envoironment
  roller env create --name test-topo --cluster-type=default
  修改网络vlan  kubectl edit clusters -n openstack
- edit topologybinding (node uuid) and preview
  `kubectl edit topology-binding -n openstack`
  kubectl patch topologybinding default -n openstack --type merge -p '{"spec": {"phase": "preview"}}'
  kubectl patch topologybinding default  -n openstack --type merge -p '{"status": {"preview": null}}'

- 在db中创建占位cluster，license等表有外键： ECAS_BACKEND=db roller env --create --cluster-type openstack --name stub

- # deploy: kubectl apply -f deploy-action
  roller deploy-changes --env 1
  重试
  kubectl patch collectiontask deploy-cluster -n ecas-orchestration --type merge -p '{"controlBlock": {"targetSeq": 2}}'

去掉vlan
```
python topology/turbo/src/turbo/tools/cd/generate_node_binding.py << EOF
base_tpl: aio_template.yaml
role_mapping:
  controller_all: [1]
output: /tmp/generated_binding.yaml

EOF
python topology/turbo/src/turbo/tools/cd/generate_node_binding.py << EOF
base_tpl: aio_template.yaml
role_mapping:
  compute_osd: [2]
output: /tmp/generated_binding.yaml

EOF

```

ess-automation: 一直有ecsnode modified 日志 timestamp 有更新？(611中也一直在更新，cpu frenquency？)
action label 由action controller添加，是否也该action controller删除
  维护/恢复失败等场景下，应该去掉action label，扩容失败不去掉？继续逻辑不一样
roller repo: 之前针对每个节点生成，现在直接用cobbler profile内容
CRD数据备份
部分集群无关数据是否不应该存到cluster cr？如roller node ip/mac

节点删除：
去掉了switch_mysql和remove_openstack任务（原来要更新estack-hagent），已经不需要
去掉 cleanup_host 应该不需要了？/etc/hosts没有node条目(删除节点时没有清理coredns中的node 解析)
去掉update_hosts_to_clusterIP：更新hub.easystack.io：应该不需要
remove_nodes: 原来通过cobbler删除&关机 - 改为命令cobbler remove
删除节点后 /etc/ethers /etc/dnsmasq.conf下面的记录还存在

对接包：
1 去掉render_ark_yaml 应该用不到了？
2 cleanup_packages 目前应该只有对接包会用，改为在对接包脚本中处理
3 对接包去掉对rpm 更新到repo的处理

对比：
1. 磁盘分区，网络配置
