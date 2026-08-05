# Attribution — Production ElevenLabs Bridge

This directory is a **vendored copy** of the community production bridge, imported into Agent-Stream so teams can use one repository for both evaluation (Node.js framework) and production telephony (Python bridge).

## Upstream

| | |
|---|---|
| **Repository** | https://github.com/Jitendra2603/exotel-elevenlabs-bridge |
| **Imported commit** | `ea3c3e4` (2026-03-23) |
| **Import method** | `git subtree` (history preserved in repo graph) |

## Original author

**Jitendra** — primary author of the production bridge  
- GitHub: [@Jitendra2603](https://github.com/Jitendra2603) / [@J11endra](https://github.com/J11endra)  
- Commits in upstream: initial bridge, background sound mixing, call transfer, AWS/GCP deployment scripts, regional endpoint support

Please direct fixes and features that belong in the shared bridge to the **upstream repo** when possible; Exotel will periodically sync subtree updates from there.

## View upstream commit history

From the Agent-Stream repo root:

```bash
git log --oneline --grep="elevenlabs-production" -1   # subtree import commit
git log --oneline ea3c3e4^..ea3c3e4                  # tip of imported tree
git log --format='%h %an <%ae> | %s' \
  $(git rev-parse 'ea3c3e4') --not $(git rev-parse 'ea3c3e4^')^@ 2>/dev/null || \
  git log --format='%h %an | %s' -7 elevenlabs-bridge/main
```

Or browse upstream directly:  
https://github.com/Jitendra2603/exotel-elevenlabs-bridge/commits/main

## License

Follow the license of the upstream repository. If no license file is present upstream, treat as MIT-compatible community contribution unless Exotel legal specifies otherwise.
