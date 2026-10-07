The dispatcher ==polls every five seconds== [?why ticks] and then sleeps.

> [?why ticks] Why poll instead of reacting to events?
>
> <-- agent/model-x @ 2026-10-06T19:57-04:00
> Polling keeps the dispatcher stateless across restarts.
>
> --> Alice @ 2026-10-06T20:03
> Fair, but five seconds is slow.
>
> <-- agent/model-x @ 2026-10-06T20:05-04:00
> One second would cost about 2 % CPU; I can measure it.
>
> +++ Alice @ 2026-10-06 ! keep five seconds for now
