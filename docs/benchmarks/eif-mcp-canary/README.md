# Real-client canary status

All four clients are **configured-not-verified**. This means a reviewable
configuration template exists, not that a live server entry was installed.
[clients.json](clients.json) records observed CLI versions and sanitized outputs.
No home-directory client config was changed or used as a fixture.

`O-6 = 0`: host tool calls and human-visible elicitation are **NOT RUN**.
G2 has not passed. The owner and orchestrator will test Claude Code elicitation
after phase-one acceptance; all writer work is deferred to EIF-022b. A synthetic
SDK callback advertisement test checks only the SDK field, never human consent.
Host schema deferral remains unknown; measurements count the whole tools/list.

SDK in-memory/stdio and installed-wheel tests are ordinary model-free program
checks. They do not replace a real-client canary, model evaluation or a matched
behavioral comparison. No model token savings are established.
