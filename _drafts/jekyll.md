
流量统计
https://stackoverflow.com/questions/17207458/how-to-add-google-analytics-tracking-id-to-github-pages

https://tongji.baidu.com/web/help/article?id=175&type=0

状态
https://tongji.baidu.com/web/10000373299/overview/index?siteId=16938964


## 构建
```
$ bundle -v
Bundler version 2.4.20
$ ruby -v
ruby 3.0.6p216 (2023-03-30 revision 23a532679b) [x86_64-linux]

# bundle 默认会安装到系统目录，下面命令设置为gem默认的用户目录。
$ bundle config set --global path ~/.gem/ # 会更新 ~/.bundle/config 文件
# bundle 替换为国内源：
$ bundle config set --global mirror.https://rubygems.org https://mirrors.tuna.tsinghua.edu.cn/rubygems
$ bundle install # gems及依赖 会安装到 ~/.gem/ruby/3.0.0/gems/ 目录

$ bundle exec jekyll serve
```
## theme / css
org mode下
begin_NAME end_NAME

生成class 为NAME的div，在main.scss里让定义.note .NOTE的style，可以简单继承自blockquote
```
.note, .NOTE {
    @extend blockquote;
}
```

## graphviz
ordering=out https://stackoverflow.com/questions/9215803/graphviz-binary-tree-left-and-right-child
