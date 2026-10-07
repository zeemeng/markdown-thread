# Heading with ==a highlight== [?h]

==Same line== [?r], ==no space==[?r], ==two spaces==  [?r] and
==wrapped before the anchor==
[?r]. A ==multi-line
highlight== [?r] counts too.

==Not directly before== the anchor [?p] is a point anchor, as is a bare [?p].
==First== [?r] [?p]: only the first token after a highlight is a range anchor.

Not anchors: ![?p], \[?p], [?p](https://example.com), [?p][ref], [text][?p].
[?missing] matches no thread and is plain text.

- ==list item one
- list item two== [?p]

> Quoted ==text== [?r] in an ordinary quote.

> [?h] Heading thread.

> [?r] Range thread.

> [?p] Point thread.
