# ADR-0008: electron-builder (NSIS) + PyInstaller Packaging

- **Status:** Proposed (to ratify at the Phase 0 kickoff)
- **Date:** 2026-10-20
- **Deciders:** Gokul J (owner), Navin Jairam M (lead)

## Context

Users install a normal Windows app. It contains a Node/Electron app and a Python
sidecar, must update itself, and must not require Python, Node or Docker on the user's
PC. Packaging is the riskiest DevOps work, so it must start in Phase 0.

## Decision

- **Sidecar:** PyInstaller **one-folder** build (`services/sidecar/packaging/ascend-sidecar.spec`) on
  `windows-latest` in CI; ONNX Runtime included, PyTorch excluded.
- **App:** **electron-builder** NSIS **per-user** installer (no admin rights); the
  sidecar folder goes into `extraResources`; `AppUserModelID` set for toasts.
- **Updates:** **electron-updater** against **GitHub Releases** with blockmap
  differential downloads, `stable` and `beta` channels.
- **Integrity:** SHA-256 checksums and a CycloneDX SBOM attached to every release;
  Electron fuses set at build time.
- **Signing:** unsigned at first (SmartScreen warning documented); evaluate Azure
  Artifact Signing (Basic $9.99/month per Microsoft's pricing page; eligibility for an
  individual in India **unverified**) before any public launch.
- Owner: Gokul (automation), Navin (release decisions). Process:
  [release-process.md](../../operations/release-process.md).

## Consequences

### Positive

- Users need nothing pre-installed except (optionally) Ollama.
- Per-user install avoids UAC prompts; updates are small (blockmap).
- GitHub Releases is free for public repos and doubles as the update server.

### Negative / Trade-offs

- Large installer (Electron + Python runtime; ~150–250 MB, estimate).
- PyInstaller binaries can trigger antivirus false positives (edge case E2).
- Unsigned builds show SmartScreen warnings until reputation or signing.

## Alternatives Considered

| Option | Why rejected |
|---|---|
| PyInstaller one-file | Slower start (unpacks each launch) and more antivirus false positives. |
| Nuitka | Faster binaries but longer, harder builds; revisit if start time is a problem. |
| MSIX / Microsoft Store | Store review and packaging constraints; sidecar process model is harder. |
| Squirrel.Windows | Older; electron-builder NSIS is better maintained for this use. |
| Ship Python via an embedded distribution + pip at first run | Needs network at install; fragile. |
