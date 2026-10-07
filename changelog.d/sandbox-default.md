### Added
- Operating layer is sandbox-on by default: `install.sh --apply-operating-layer` sets `sandbox.enabled: true` and `sandbox.allowUnsandboxedCommands: false` and denies `Bash(rm -rf *)`, `Bash(rm -fr *)`, `Bash(rm -r *)`, `Bash(rm -R *)`, `Bash(sudo *)` (existing values win; deny list is merged). `--no-sandbox` opts out with a printed risk warning. Prevents the `rm -rf "$EMPTY"/*` class of host deletion.
- `operating_selfcheck.py` reports `sandbox-on: MISSING RED` when the sandbox is off or unsandboxed retry is allowed.
- Doctrine (operating-discipline item 8, lane preamble): never run delete/kill experiments on a host, never `rm -rf` a variable-built path; deny rules match command text only, the sandbox is the real boundary.
