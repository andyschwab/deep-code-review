# Addendum 2 (after the held-out runs; no effect on any result)

1. The privacy gate flagged a real place name inside positioning held-out scenario h23 (a writer-chosen city in the name of a fictional park). In the committed scenarios/positioning-heldout.json only, that city word was replaced by "Bay". The generators and judges saw the original text; the pre-edit file hash is the positioning-heldout line in SHA256-selection.txt, so the committed file no longer matches it. No output or judge record contains the name.
2. The SKILL.md edit that ships is the tested section plus one Verification bullet naming the new eval (the repository's doc-sync gate requires every eval id to appear in Verification). The bullet was not in the arm that was run (prompts/perun_positioning_a.txt).
