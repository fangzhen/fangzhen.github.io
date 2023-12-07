
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
$ bundle install # gems及依赖 会安装到 .gem/ruby/3.0.0/gems/ 目录

$ bundle exec jekyll serve
```

## org-mode
https://thackl.github.io/blogging-with-emacs-org-mode-and-jekyll

https://orgmode.org/worg/org-tutorials/org-jekyll.html

https://emacs.stackexchange.com/questions/19850/how-to-achieve-dynamic-projects-without-fixed-paths-for-publishing-from-org-mode

关闭默认的toc, 否则front matter就不在第一行了
#+OPTIONS: toc:nil
#+TOC: headlines 2

org mode里使用dot
https://orgmode.org/worg/org-contrib/babel/languages/ob-doc-dot.html


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


## org-mode beamer
org-mode导出pdf 中文：以下两个配置 https://emacs-china.org/t/topic/2540/12
#+LATEX_HEADER: \usepackage{ctex}
#+latex_compiler: xelatex


中文字体指南https://zhuanlan.zhihu.com/p/538459335

beamer默认字体是sans serif字体
https://tex.stackexchange.com/questions/79420/changing-font-style-using-beamer
\setsansfont{Liberation Serif}
#+LATEX_HEADER: \setCJKsansfont{SimSun}


https://emacs.stackexchange.com/questions/36837/org-mode-how-can-i-add-a-section-name-only-frame-to-beamer-slides

image scale
https://stackoverflow.com/questions/30138947/setting-width-or-height-for-graphics-in-beamer-only-works-with-png
https://tex.stackexchange.com/questions/17380/best-figure-size-adjustment-when-dealing-with-different-image-sizes
