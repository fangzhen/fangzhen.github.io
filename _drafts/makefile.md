
## Makefile文件组织

在大项目的情况下，难以在单个makefile维护所有的规则，一般采用分目录的方案，在子目录中创建和维护自己的makefile。

**需要注意的一点是 makefile 本身没有project的相关概念，它的处理都是基于单个makefile文件的。**

```
project
  main.c
  Makefile
  foo/
    foo.c
    Makefile
  bar/
    bar.c
    Makefile
```

我们希望依赖关系为：
```
foo/foo.c -> foo/foo ----> main
                       ^
              main.c --|
```

`foo/Makefile`如下，根据`foo.c`生成`foo`。
```
foo: foo.c
        cat $^ > $@
```
根目录下Makefile的写法：
1. 递归调用make来构建`foo`目录：
   ```
   main: main.c foo/foo
   	cat $^ > $@
   foo/foo:
   	$(MAKE) -c foo
   ```
   问题：如果foo.c更新，直接在根目录执行make，无法触发到main更新。原因是在根目录的Makefile中，`foo/foo`规则没有依赖，所以文件存在就不会触发recipe的执行。

2. 把`foo`定义为phony target。phony target每次都会执行：
   ```
   .PHONY: all foo
   all: main

   main: main.c foo
   	cat $< foo/foo > $@

   foo:
   	$(MAKE) -C $@
  ```
  此时，如果foo.c更新，直接在根目录执行make，因为在根目录Makefile中，`foo`是phony target, 所以会触发foo的recipe执行。

  但是有一个新问题：main的recipe每次都会执行，即使main.c, foo/foo.c都没有更新。原因也是因为`foo`是phony target，make每次执行都会把它当作有更新。

3. 非完美但可行的方案
   ```
   .PHONY: all foo
   all: main

   main: main.c foo/foo
   	cat $^ > $@

   foo/foo: foo ;

   foo:
   	$(MAKE) -C $@
   ```
  `foo/foo`设置为依赖`foo` phony target。这样如果`foo`的recipe没有更新`foo/foo`文件，就不会导致main更新。最终效果是main更新当且仅当main.c或foo/foo.c有更新。

  >
  > 根据(GNU make的manual)[https://www.gnu.org/software/make/manual/html_node/Phony-Targets.html]，phony target不应该作为真实文件的依赖，主要就是为了避免文件每次都被更新。
  > 但我们此处foo/foo文件target依赖了foo phony target，只是recipe为空。
  > 个人没有想到更好的方案。

make本身没有project的概念。当使用recursive make来管理项目构建时，总会使用各种各种的hack方案，其中坑其实比较多。还有一种使用`include`的非递归方案，相当于分文件/目录组织makefile，但是最终执行时是合并到一个文件的。请参考：

[Managing Large Projects](https://www.oreilly.com/library/view/managing-projects-with/0596006101/ch06.html)
和[Recursive Make Considered Harmful](https://aegis.sourceforge.net/auug97.pdf)(by Peter Mille)

[Linux Kernel Makefiles](https://docs.kernel.org/kbuild/makefiles.html)也是采用的非recursive方案。

## Other
https://stackoverflow.com/questions/31121698/gnu-makefile-preprocessor
