---
layout: post
title: emacs for myself
tags: ["emacs"]
date: 2023-12-08
---
## 启动
### Emacs server + emacs client
emaclient desktop
https://debbugs.gnu.org/cgi/bugreport.cgi?bug=41719
https://www.reddit.com/r/emacs/comments/ia2yv4/how_can_i_set_wm_class_for_emacs_27/
https://unix.stackexchange.com/questions/521019/specifying-the-wm-class-of-a-program
https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html

## 非默认配置
### Clickable text 行为
当用鼠标选择链接的部分字符时，看不到选择区域，选中区域的颜色被链接的高亮显示覆盖。比如在markdown mode，Help mode下

![选中但鼠标不在链接上](../assets/static/emacs_link_region1.png)

下图选中了相同文本，但鼠标在链接上时，根本看不出来被选中的文本是什么。
![选中但鼠标在链接上](../assets/static/emacs_link_region2.png)

Emacs 显示文本时，实际的显示结果会[根据不同的配置合并后显示](https://www.gnu.org/software/emacs/manual/html_node/elisp/Displaying-Faces.html)。
例如markdown 模式下的链接，选中部分文本时，`describe-text-properties`结果为：
```
Text content at position 2286:


There are 2 overlays here:
 From 2241 to 2358
  face                 hl-line
  priority             -50
  window               #<window 5 on ...>
 From 2286 to 2290
  face                 region
  priority             (nil . 100)
  window               #<window 5 on ...>


There are text properties here:
  face                 (highlight-symbol-face markdown-url-face)
  font-lock-multiline  t
  fontified            t
  invisible            markdown-markup
  keymap               [Show]
  mouse-face           markdown-highlight-face
```
跟这个显示结果相关的是：
文本的face和mouse-faces属性分别是文本日常的显示以及鼠标在文本上是的显示。
overlay中定义的face和mouse-face比文本上直接定义的优先级高，多个overlay也根据优先级排序。
所以上面结果最终显示在当前文本上的face和mouse-face分别是`region`和`markdown-highlight-face`

当使用键盘选中区域时，按照`region` face显示，可以看出来选中区域。
但是当用鼠标选中区域时，因为鼠标目前在当前链接位置，会根据mouse-face按照`markdown-highlight-face`显示，这是就没法看出来选中区域了。

> face为`region`的overlay的优先级的值为特殊形式
> <https://www.gnu.org/software/emacs/manual/html_node/elisp/Overlay-Properties.html> 的说明。
> 达到的效果大概是希望选中区域比较大时，选中区域内部还可以显示不同的face。

解决方案：
1. 设置`mouse-highlight`变量为nil，设置后鼠标hover到链接上时，mouse-face不再生效。
2. 设置1后，鼠标hover到链接时没有反馈，可能容易误点。
   - 可以把`mouse-1-click-follows-link`设置为nil，这样只有鼠标中键(mouse-2)点击时才会访问链接。
   - 可以设置链接文本的pointer text-properties，设置为手型。这种方式基本上需要每个mode单独处理，而且mode很可能并没有变量或hook可以设置。比如markdown mode可以修改markdown.el，在相关的位置增加`'pointer 'hand`。
   ```
              ;; Link part (without face)
           (lp (list 'keymap markdown-mode-mouse-map
                     'pointer 'hand
                     'mouse-face 'markdown-highlight-face
                     'font-lock-multiline t
                     'help-echo (if title (concat title "\n" url) url)))
           ;; URL part
           (up (list 'keymap markdown-mode-mouse-map
                     'invisible 'markdown-markup
                     'pointer 'hand
                     'mouse-face 'markdown-highlight-face
                     'font-lock-multiline t))
   ```
[Defining Clickable Text](https://www.gnu.org/software/emacs/manual/html_node/elisp/Clickable-Text.html)
Emacs下很多链接的实现是基于[Button](https://www.gnu.org/software/emacs/manual/html_node/elisp/Buttons.html)的。

## Programming
### 自动补全
[company-mode](http://company-mode.github.io/)是一个补全框架，设计了模块化frontend和backend接口可以用来对接不同的补全方案。
frontend用来显示与交互，backend用来产生补全的候选词。company本身提供的backend已经基本可以满足需求。

company的后端就是一个函数，company框架通过传递不同的参数实现与后端的交互。
后端函数接收的第一个参数称为命令，根据命令的不同，还可能有更多可选参数。
必须实现的两个command是prefix和candidates。前者返回当前光标处该后端进行补全的prefix，后者返回候选词列表。
需要prefix命令的原因是company框架本身可能会对prefix进行一些预处理，比如prefix长度大于一定阈值才会进行补全。
company框架本身不直接提供prefix，因为不同后端的补全逻辑不同，它的prefix也会不同。

## org-mode
https://thackl.github.io/blogging-with-emacs-org-mode-and-jekyll

https://orgmode.org/worg/org-tutorials/org-jekyll.html

https://emacs.stackexchange.com/questions/19850/how-to-achieve-dynamic-projects-without-fixed-paths-for-publishing-from-org-mode

关闭默认的toc, 否则front matter就不在第一行了
#+OPTIONS: toc:nil
#+TOC: headlines 2

org mode里使用dot
https://orgmode.org/worg/org-contrib/babel/languages/ob-doc-dot.html


### beamer制作幻灯片

M-x: org-beamer-export-to-pdf

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

### 导出为html时生成的div id一直变化
主要相关代码
```
org-export-new-reference
org-export-get-reference
```
org-mode-publish会给Headings等生成crossrefs，并缓存在本地的`.org-timestamps/`目录下。
在`.org`文档的相关部分没做修改的情况下，包含在crossrefs中的id可以保持不变。(前提是可以访问到之前的缓存)。
但是其他的id会一直变化，如special block。

没有找到好的方案可以保留之前的id。完整解决需要修改orgmode生成html的逻辑。暂时用的方案为：
使用如下代码，在生成的html中删除掉id字段。没有全部删除是因为Headings等生成的id有时候还是有用的，而且在上面提到的可以获取到之前生成的crossref的情况下，这些id会保留。
```
(defun org-html-body-remove-id (output)
  "Remove random ID attributes generated by Org."
  (replace-regexp-in-string
     " id=\"[[:alpha:]-]*org[[:alnum:]]\\{7\\}\""
     ""
     output t))
(advice-add 'org-html-special-block :filter-return #'org-html-body-remove-id)
(advice-add 'org-html-paragraph :filter-return #'org-html-body-remove-id)
```

相关讨论：
https://emacs.stackexchange.com/questions/36366/disable-auto-id-generation-in-org-mode-html-export
https://jeffkreeftmeijer.com/ox-html-stable-ids/

### add caption to images generated by a code block
https://emacs.stackexchange.com/questions/12150/add-caption-to-an-image-generated-by-a-code-block

### 默认居中图片
https://emacs.stackexchange.com/questions/41534/alignment-of-images-in-html-export
在orgmode文档开头添加
`#+HTML_HEAD_EXTRA: <style> .figure p {text-align: right;}</style>`

但是我是publish到jekyll中，用了body-only，没有上面的header。
可以在jekyll的main.scss中添加
```scss
.figure p {text-align: center;}
```

## 日常使用cheatsheet
| forward-list(C-M-n)                             | 向下移动到下一组成对出现的组，如下一个右括号，右引号 |
| backward-list(C-M-p)                            | 向上移动到下一组成对出现的组，如上一个左括号，左引号 |
| rectangle-number-lines(C-x r N)                 | 给选中行插入行号                                     |
| eval-region/eval-buffer/eval-last-sexp(C-x C-e) | 执行选中行/执行当前buffer/光标处的elisp代码          |

## Wish lists
- ivy-switch-buffer 添加projectile文件
  https://emacs.stackexchange.com/questions/62342/can-ivy-switch-buffer-add-the-current-projects-files-via-projectile
  目前不好实现

- 保存的自定义配置 会把所有配置改到custom.el，有些讨论
  https://emacs.stackexchange.com/questions/15069/how-to-not-save-duplicate-information-in-customize
  https://debbugs.gnu.org/cgi/bugreport.cgi?bug=21355 emacs 28 解决，可能可以解决这个而问题。
  https://www.reddit.com/r/emacs/comments/g46sg2/a_solution_to_the_agony_of_customsetvariables_and/
