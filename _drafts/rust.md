
https://users.rust-lang.org/t/similar-items-in-core-and-std/60167/3

> std re-exports everything that core and alloc contain (but there's also things in std that only std contains.) Unless you're writing a no_std crate, you only need to worry about & use std. The “similar” items are actually exactly the same items, there's no difference.
