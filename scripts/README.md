# scripts/

Automation scripts: bootstrap (`eifctl init` equivalent), health checks
(`eifctl doctor` equivalent), knowledge-index generation, graph-freshness
checks, RTK-stats reporting, merge-gate enforcement.

Not populated yet. The private instance has working, tested versions of a
graph-freshness checker and a controlled merge-gate script; porting requires
removing private repo names and machine-specific paths from both the script
and its default config.
