> [?fields] Opener.
>
> --> Alice Smith @ 2026-10-06T20:03-04:00
> Name with a space, full timestamp.
>
> --> @alice:example.org
> A Matrix id is a name: the @ is followed by a letter.
>
> --> Alice @2026-10-06
> The @ may touch a digit.
>
> --> Alice @ yesterday
> Not a timestamp, so there is none.
>
> --> Alice @ 2026-10-06T20:03 trailing words
> Text after the timestamp is ignored.
>
> --> Alice @ 2026-10-06T20:03-04
> An incomplete offset is ignored too.
>
> <--
> A responder without a name or time.
>
> +++ ! wontfix
>
> --> Alice
> Reopen.
>
> +++ Alice ! see you @ home
>
> --> Alice
> Reopen.
>
> +++ Alice! Smith @ 2026-10-07
>
> --> Alice
> Reopen.
>
> +++ @ 2026-10-07T09:00Z ! done
