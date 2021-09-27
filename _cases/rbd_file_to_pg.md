---
layout: post
title: 定位PVC中文件对应的ceph pg
date: 2021-09-24
tags: rbd ceph
update: 2021-09-27
---

## 问题说明
我们kubenetes 集群的PVC使用rbd存储。希望针对PVC的某个文件，找到文件在ceph中对应的pg。

问题起因是发现PVC中有个文件有问题，检查发现checksum有问题，后来又莫名奇妙自己好了。怀疑有可能是某个副本的数据有不一致，又不想对整个集群做deep-scrub。所以找到对应的pg,只针对改pg做deep-scrub。

[//]: # (EAS-84967)

## 步骤
基本思路是先从文件系统层面找到文件在块设备上的存储位置，再根据该位置信息找到对应的rbd image的object。

1. 先在pod里先找到对应的PVC对应的rbd设备，以及要目标文件的inode：
   ```
   # mount | grep www
   /dev/rbd12 on /var/www/roller type ext4 (rw,relatime,stripe=1024)
   ()[root@node-6 roller]# ls -i /var/www/roller/test
   20 /var/www/roller/test
   ()[root@node-6 roller]# cat /var/www/roller/test
   file in pvc
   ```
可以看到对应的块设备是`rbd12`

3. 可以看到文件系统是`ext4`，我们需要登陆到rbd设备的节点上使用`debugfs`获取该文件所在的block信息。
   ```
   # debugfs -R "stat <20>" /dev/rbd12
   debugfs 1.42.9 (28-Dec-2013)
   Inode: 20   Type: regular    Mode:  0644   Flags: 0x80000
   Generation: 899572748    Version: 0x00000000:00000001
   User:     0   Group:     0   Size: 12
   File ACL: 0    Directory ACL: 0
   Links: 1   Blockcount: 8
   Fragment:  Address: 0    Number: 0    Size: 0
    ctime: 0x614da36e:6b0f803c -- Fri Sep 24 18:07:42 2021
    atime: 0x614da371:c52fdd84 -- Fri Sep 24 18:07:45 2021
    mtime: 0x614da36e:6b0f803c -- Fri Sep 24 18:07:42 2021
   crtime: 0x614da36e:65d0b870 -- Fri Sep 24 18:07:42 2021
   Size of extra inode fields: 32
   EXTENTS:
   (0):34355
   # tune2fs -l /dev/rbd12 |grep "^Block size:"
   Block size:               4096
   ```

4. 找到pv对应的rbd image
   ```
   # kubectl get pv -o yaml pvc-359fbaf6-8862-49e5-929f-25f0cbe1b328 | grep -E "image|pool"
       image: kubernetes-dynamic-pvc-c6e1121d-1cc2-11ec-a1a7-0a580ae80206
       pool: rbd
   ```

5. 获取rbd image的信息
   ```
   # kubectl exec -it -n openstack busybox-openstack-7dbf4f5656-gjt9s bash
   ()[root@busybox-openstack-7dbf4f5656-gjt9s /]#  rbd -p rbd info kubernetes-dynamic-pvc-c6e1121d-1cc2-11ec-a1a7-0a580ae80206
   rbd image 'kubernetes-dynamic-pvc-c6e1121d-1cc2-11ec-a1a7-0a580ae80206':
           size 100GiB in 25600 objects
           order 22 (4MiB objects)
           block_name_prefix: rbd_data.24e16b8b4567
           format: 2
           features: layering
           flags:
           create_timestamp: Fri Sep 24 07:05:43 2021
   ```
可以看到`block_name_prefix`和object 大小（4M）。

6. 至此，我们找到了文件`test`在文件系统内的位置以及rbd设备的信息，接下来就需要把两者能对应上。

   执行如下命令获取到rbd pool中所有的object：
   `# rados -p rbd ls > rados_ls`

7. 计算文件对应的pg 以及文件在pg内的偏移：

   上面看到文件系统block size为4086B，而object大小为4M。
   所以上述文件对应的object号是`34355/1024=33=21（16）`，
   对应的object为:
   ```
   # cat rados_ls | grep rbd_data.24e16b8b4567 | grep 0021
   rbd_data.24e16b8b4567.0000000000000021
   ```
   object内偏移：
   `34355-33*1024=563(block)`

   获取对应的object
   ```
   # rados -p rbd get rbd_data.24e16b8b4567.0000000000000021 rbd_data.24e16b8b4567.0000000000000021
   ```

   读取object在上述偏移出的内容，验证下获取到的内容跟最开始直接从文件中读取的是一致的，说明定位到的pg是正确的。
   ```
   # dd if=rbd_data.24e16b8b4567.0000000000000021 bs=4096 skip=563 | hexdump -C | head
   1+0 records in
   1+0 records out
   00000000  66 69 6c 65 20 69 6e 20  70 76 63 0a 00 00 00 00  |file in pvc.....|
   ```

8. 找到object后可以获取到pg等信息。
   ```
   # ceph osd map rbd  rbd_data.24e16b8b4567.0000000000000021
   osdmap e86 pool 'rbd' (4) object 'rbd_data.24e16b8b4567.0000000000000021' -> pg 4.c98d8c64 (4.24) -> up ([2,0,4], p2) acting ([2,0,4], p2)
   # ceph pg map 4.24
   osdmap e86 pg 4.24 (4.24) -> up [2,0,4] acting [2,0,4]
   ```

更多参考：
* <https://www.sebastien-han.fr/blog/2012/07/16/rbd-objects/>
* <https://hustcat.github.io/rbd-image-internal-in-ceph/>
* <https://ceph-users.ceph.narkive.com/0kQligB1/how-to-get-rbd-volume-to-pg-mapping>
* <https://ypdai.github.io/2019/02/26/%E5%A6%82%E4%BD%95%E5%A4%84%E7%90%86PG%20inconsistent%E7%8A%B6%E6%80%81/>
