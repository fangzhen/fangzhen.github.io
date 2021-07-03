Load lisp file

https://stackoverflow.com/questions/2580650/how-can-i-reload-emacs-after-changing-it

You can use the command load-file (M-x load-file, then press return twice to accept the default filename, which is the current file being edited).

You can also just move the point to the end of any sexp and press C-xC-e to execute just that sexp. Usually it's not necessary to reload the whole file if you're just changing a line or two.

clangd
sudo dnf install clang-tools-extra

grub2.02
$ ./autogen.sh
$ ./configure
$ bear make

https://releases.llvm.org/9.0.0/tools/clang/tools/extra/docs/clangd/Installation.html

https://www.mortens.dev/blog/emacs-and-the-language-server-protocol/

clangd 用不了
8.0 不会index project
9.0 会自动index，但是很快coredump


https://github.com/porterjamesj/virtualenvwrapper.el/blob/5649028ea0c049cb7dfa2105285dee9c00d189fb/virtualenvwrapper.el#L93-L102
(projectile-project-root)



https://lists.fedoraproject.org/pipermail/devel/2012-January/160917.html

选中行并插入行号
https://emacs.stackexchange.com/questions/47633/elisp-program-to-insert-line-numbers-into-a-buffer
> Another way: C-x r N (verified). From emacswiki.org/emacs/NumberLines


emaclient desktop
https://debbugs.gnu.org/cgi/bugreport.cgi?bug=41719
https://www.reddit.com/r/emacs/comments/ia2yv4/how_can_i_set_wm_class_for_emacs_27/
https://unix.stackexchange.com/questions/521019/specifying-the-wm-class-of-a-program
https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html

recentf: 记录文件访问位置

保存的自定义配置 会把所有配置改到custom.el，有些讨论
https://emacs.stackexchange.com/questions/15069/how-to-not-save-duplicate-information-in-customize
https://debbugs.gnu.org/cgi/bugreport.cgi?bug=21355 emacs 28 解决，可能可以解决这个而问题。
https://www.reddit.com/r/emacs/comments/g46sg2/a_solution_to_the_agony_of_customsetvariables_and/

TODO:
emacs lsp: find implementation short cut

ivy-switch-buffer 添加projectile文件
https://emacs.stackexchange.com/questions/62342/can-ivy-switch-buffer-add-the-current-projects-files-via-projectile
目前不好实现