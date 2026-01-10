# Project Snapshot: Vare Re-Initialization

**Date:** 2026-01-10
**Version Tag:** v0.5.0 (Proposed)

## Key Changes in This Release

### 1. UI/UX Standardization
- **Global Font Weight System**: Implemented strictly typed `WeightScale` (BASE, MD, LG, XL) across the entire app.
  - Page Titles: `XL` (W_700)
  - Section Headers: `MD` (W_500)
  - Labels: `BASE` (W_400)
- **Component Styling**:
  - `FluentDropdown` styles fixed to ensure options inherit correct font family and weight.
  - `AboutDialog` and other modals updated to use `ThemeManager` correctly.
  - Replaced hardcoded `ft.FontWeight` values with semantic `WeightScale` constants.

### 2. Localization & Assets
- **Translation Fixes**: Corrected missing translation for `Length Penalty` ("長度懲罰").
- **Audit**: Verified synchronization of `log_` keys between localized JSON files and Python code.

### 3. Project Hygiene
- **Git Ignore**: Updated `.gitignore` to exclude `tests/` and `tools/` directories.
- **Cleanup**: Removed temporary audit scripts (`audit_locales.py`) and verification tools.

## Recommended Commit Message
```text
feat(ui): standardize font weights and fix localization

- Refactor entire UI to use strict WeightScale system
- Fix styling issues in Dropdowns and Dialogs
- Add missing translations for Advanced Settings
- Cleanup project structure and update .gitignore
```
