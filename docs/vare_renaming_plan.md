# Vare Renaming Project - Implementation Plan

## Overview
Rename all legacy naming (`BreezeASR`, `Breeze`, `MyASR`) to the new brand name **Vare**.

> [!CAUTION]
> **External Model Names Must NOT Be Changed**
> The following are HuggingFace model identifiers and are NOT part of the app naming:
> - `SoybeanMilk/faster-whisper-Breeze-ASR-25`
> - `MediaTek-Research/Breeze-ASR-25`
> These must remain unchanged as they reference external resources.

---

## Phase 0: Pre-Flight Checklist

- [ ] Backup current state (git commit already done)
- [ ] Verify no unsaved changes: `git status`
- [ ] Document all rename targets (this file)

---

## Phase 1: Python Class & Variable Names (High Risk)

| File | Current | New | Type |
|------|---------|-----|------|
| `app.py:44` | `class BreezeASRApp` | `class VareApp` | Class definition |
| `main.py:10` | `from app import BreezeASRApp` | `from app import VareApp` | Import |
| `main.py:147` | `app = BreezeASRApp(page)` | `app = VareApp(page)` | Instantiation |
| `pages/task_page.py:16` | `from app import BreezeASRApp` | `from app import VareApp` | Import |
| `pages/task_page.py:29,34` | `BreezeASRApp` | `VareApp` | Type hint |
| `pages/settings_page.py:23,29` | `BreezeASRApp` | `VareApp` | Import + Type hint |
| `pages/logs_page.py:15,27,32` | `BreezeASRApp` | `VareApp` | Import + Type hint |

**Verification**: After this phase, run `python -c "from app import VareApp"` to confirm.

---

## Phase 2: User-Facing Display Strings (Low Risk)

| File | Current | New |
|------|---------|-----|
| `ui/layout.py:69` | `" Breeze ASR Pro"` | `" Vare"` |
| `main.py:2` | `Breeze ASR Pro - Application Entry Point` | `Vare - Application Entry Point` |
| `app.py:444` | `Breeze Team` | `Vare Team` |
| `features/transcription/services/transcribe.py:126` | `"Breeze ASR Transcription Tool"` | `"Vare Transcription Tool"` |

---

## Phase 3: Settings & Config Paths (Medium Risk)

| File | Current | New | Notes |
|------|---------|-----|-------|
| `core/settings.py:89` | `app_name = "MyASR"` | `app_name = "Vare"` | Affects %APPDATA%/Vare |

> [!WARNING]
> Changing `app_name` will change the settings storage path from `%APPDATA%/MyASR/` to `%APPDATA%/Vare/`.
> Migration logic should copy old settings to new location.

---

## Phase 4: Documentation Strings (Low Risk)

| File | Location | Current | New |
|------|----------|---------|-----|
| `faster_whisper.py:2` | Docstring | `Faster-Whisper Backend for CT2 Breeze-ASR-25` | `Faster-Whisper Backend for Vare` |
| `transcribe.py:15` | Docstring | `Transcribe audio/video files using Breeze-ASR-25` | `Transcribe audio/video files using Vare` |
| `srt_utils.py:107` | Test data | `今天要介紹的是 Breeze ASR` | `今天要介紹的是 Vare` |

---

## Phase 5: Locale Files (Low Risk)

Check if `app_title` in `locales/zh-tw.json` and `locales/en.json` needs updating.

---

## DO NOT CHANGE (External References)

| File | Line | Value | Reason |
|------|------|-------|--------|
| `basic_section.py:60,62,63` | Model options | `SoybeanMilk/faster-whisper-Breeze-ASR-25` | HuggingFace model ID |
| `faster_whisper.py:25,263` | Default model | `SoybeanMilk/faster-whisper-Breeze-ASR-25` | HuggingFace model ID |
| `settings.py:25` | Default | `SoybeanMilk/faster-whisper-Breeze-ASR-25` | HuggingFace model ID |
| `task_controller.py:146` | Default | `SoybeanMilk/faster-whisper-Breeze-ASR-25` | HuggingFace model ID |
| `transcribe.py:118` | Default | `SoybeanMilk/faster-whisper-Breeze-ASR-25` | HuggingFace model ID |
| `core/settings.json:5` | User data | Model name | User's saved preference |

---

## Execution Order

1. **Phase 1** (Class Names) - Most critical, requires all-or-nothing
2. **Phase 3** (Settings Path) - Implement migration before changing
3. **Phase 2** (Display Strings) - Safe, cosmetic
4. **Phase 4** (Docs) - Safe, cosmetic
5. **Phase 5** (Locales) - Check and update if needed

---

## Verification Plan

After each phase:
1. Run `python main.py` to verify app launches
2. Check Settings page loads
3. Verify no import errors in console

---

## Estimated Effort

| Phase | Files | Complexity | Risk |
|-------|-------|------------|------|
| Phase 1 | 5 | Medium | High |
| Phase 2 | 4 | Low | Low |
| Phase 3 | 1 | Medium | Medium |
| Phase 4 | 3 | Low | Low |
| Phase 5 | 2 | Low | Low |

**Total: ~15 files, ~50 line changes**
