```markdown
> [?fenced] Not a thread: inside a fenced code block.
>
> --> Alice
> Still code.

An anchor-like [?real] inside code.
```

~~~
[?real] in a tilde fence.
~~~

Inline `[?real]` code spans and <!-- [?real] --> comments are not anchors.
An unbalanced ``run` is no code span, so [?real] here is an anchor.
A span ``with ` inside [?real]`` hides its token.
<!--
> [?commented] A multi-line comment hides this quote.
>
> --> Alice
-->

> [?real] The only thread.
>
> --> Alice
> A message with code:
>
> ```text
> --> not a marker
> <-- not a marker
>
> +++ not a close
> ```
>
> <-- agent/model-x @ 2026-10-06T20:20-04:00
> Reply after the fence.

> An ordinary quote with code:
>
> ```
> [?real] stays code.
> ```

This [?real] is an anchor.

<!-- a comment that ends mid-line
> [?ghost] hidden --> visible text with an anchor [?real].
