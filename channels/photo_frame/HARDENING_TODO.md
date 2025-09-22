# Photo Frame Channel – Hardening & Follow‑Up Task List

Status: Deferred while focusing on Spotify channel stabilization
Scope: `image-frame-channel-mimir/channels/photo_frame/`
Goal: Capture all known/likely improvements so we can return later with a clear, prioritized plan.

---
## 1. Prioritized Task Overview

| Priority | Task | Summary Outcome |
|----------|------|-----------------|
| Critical | Import & module isolation refactor | Eliminate fragile try/except + sys.path hacks to prevent cross‑plugin contamination. |
| Critical | Complete/incomplete code branches audit | Ensure no silent no‑ops where omitted / placeholder blocks currently exist (validation, error paths). |
| High | Replace `print()` with structured logging | Consistent logger namespace + context for debugging in production. |
| High | Directory & config validation completion | Finish `_validate_api_integration()` missing body for required dirs handling. |
| High | Add manifest health fields | Add `healthy`, `diagnostics` to manifest for platform probing. |
| Medium | Router assembly hardening | Mirror Spotify channel explicit dynamic loader / clearer failure logs. |
| Medium | Image selection logic tests | Unit tests for ordering, randomization, distribution, cache reuse. |
| Medium | Cache policy formalization | Document and/or make `_cache_ttl_seconds` configurable; add purge strategy. |
| Medium | Metadata consistency & migrations | Detect / repair legacy records missing new fields (crop data, stats). |
| Low | Thumbnail regeneration commands | Expose admin endpoints to trigger `_regenerate_colocated_thumbnails` & `_rebuild_database_from_files`. |
| Low | Type annotations & mypy pass | Strengthen signatures; add `pyproject.toml` mypy config (if absent). |
| Low | Docstrings & API reference | Google-style docstrings for public methods; generate brief README feature map. |
| Low | Settings schema consolidation | Normalize settings acquisition (`_normalize_settings`) + unify canonical crop mode mapping. |
| Future | Pluggable ranking/rotation strategies | Strategy objects for rotation beyond added/random/custom. |
| Future | Background pre-render pipeline | Warm frequently requested resolutions in advance. |
| Future | Async I/O for heavy disk ops | Use thread pool or asyncio wrappers for large file operations. |
| Future | Content tagging / search | Extend gallery filtering with tags & simple query API. |

---
## 2. Detailed Task Descriptions

### 2.1 Critical
**A. Import & Module Isolation Refactor**  
Current: Multiple `try/except ImportError` blocks mutating `sys.path`.  
Plan: Introduce `_import_local(name, rel_path)` helper (importlib.spec_from_file_location) + namespaced module keys (e.g. `photoframe_models`). Remove all `sys.path.insert` calls. Purge generic `models`, `services`, `routes`, `utils` contamination if paths mismatch channel base.

**B. Incomplete Branch / Placeholder Audit**  
Review code where sections are indicated by comments or previously omitted (e.g., error handling inside `_validate_api_integration`, image selection fallback blocks, upload error branches). Ensure each branch either raises explicit exceptions or logs clearly.

### 2.2 High
**C. Structured Logging**  
Add: `logger = logging.getLogger("mimir.channels.photoframe")`. Replace prints with `logger.info/debug/warning/error` including context: `gallery_id`, `image_id`, `resolution`, `distribution_mode`.

**D. Directory & Config Validation Completion**  
Inside `_validate_api_integration`: For each required dir: create if missing (or raise). Log results. Verify `config["current_image"]` & `config["placeholder_image"]` paths exist; if not, initialize placeholder assets.

**E. Manifest Health Fields**  
Augment `get_manifest()` with:
```
"healthy": bool(last_error is None),
"diagnostics": {
  "last_error": self.last_error,
  "image_count": len(self.metadata.get_all_images()),
  "last_update": self.last_update,
  "cache_entries": len(self._render_cache),
}
```
Return degraded manifest on exception (already partially done) with explicit `healthy: False`.

### 2.3 Medium
**F. Router Assembly Hardening**  
Encapsulate route creation: `_build_router()` with try/except recording failure reason to `last_error`. Validate expected factories exist before inclusion.

**G. Image Selection & Distribution Tests**  
Test cases:
- Added order sequential progression
- Random order avoids immediate repeat
- Custom order respects gallery.content_ids sequence
- Distribution mode `current` returns same cached image until invalidated
- Crop mode canonicalization paths

**H. Cache Policy & Invalidation**  
Track entry insertion times. Periodic purge (lazy during request) when `now - inserted > ttl`. Optionally config-driven TTL.

**I. Metadata Repair / Migration Script**  
Add function to populate missing fields: `times_shown`, `last_shown_at`, crop fields defaults. Provide admin endpoint to trigger.

### 2.4 Low
**J. Admin Endpoints for Maintenance**  
Secure endpoints (e.g. `POST /admin/thumbnails/regenerate`, `POST /admin/database/rebuild`) returning task summary.

**K. Type Annotations & Static Checks**  
Add explicit return types, generics for lists/dicts. Run mypy; fix reveals (Optional handling, Any reductions).

**L. Docstrings & README**  
Add `README.md` summarizing architecture: services, selection pipeline, cache, gallery model, API surface.

**M. Settings Normalization Consolidation**  
Unify `_normalize_settings` & `_canonicalize_crop_mode` into a single validator that returns a dataclass or typed object.

### 2.5 Future Enhancements
**N. Strategy Pattern for Rotation**  
Abstract rotation into classes (e.g. `AddedOrderStrategy`, `LeastShownStrategy`). Allows extension without enlarging `request_image`.

**O. Pre-Rendering / Warm Cache**  
Background job generates images for all active galleries + popular resolutions.

**P. Tagging & Search**  
Extend metadata JSON to include tags; filter images by tag query.

**Q. Async / Concurrency Optimizations**  
Wrap file I/O and Pillow work in executors; batch metadata writes.

---
## 3. Acceptance Criteria Snapshot

| Task | Acceptance Criteria |
|------|---------------------|
| Import Refactor | No `sys.path.insert` in file; dynamic loads succeed under isolated loader; manifest served (200) post-change. |
| Logging | Zero bare print statements; logs show phase markers (INIT, ROUTER_BUILT, IMAGE_RENDER, ERROR). |
| Manifest Health | `healthy` key present; failure surfaces reason in `diagnostics.last_error`. |
| Selection Tests | All tests pass; no flakiness across ≥10 random-selection runs. |
| Cache Policy | Entries older than TTL purged; hit ratio metric available in diagnostics. |

---
## 4. Suggested Implementation Order (When Resumed)
1. Import isolation refactor (unblocks everything else)
2. Logging + directory/config validation
3. Manifest health augmentation
4. Router assembly hardening
5. Test harness (selection + cache + manifest)
6. Cache invalidation improvements
7. Admin maintenance endpoints
8. Type annotations & docstrings
9. Optional future enhancements

---
## 5. Risk Notes
- Delaying import refactor increases chance of subtle cross-plugin module leakage (especially if other plugins added). Mitigation: treat current state as temporary; avoid deploying new overlapping module names until refactor.
- Adding tests later may require fixture retrofits; budget time to abstract filesystem touches (e.g., temp dirs) early when resuming.

---
## 6. Quick Win Candidates (Fast Once Resuming)
- Logging replacement (mechanical search/replace) – low risk.
- Manifest health flags – localized change.
- Cache purge on access – minimal complexity.

---
## 7. Deferred Artifacts To Create
- `tests/test_selection.py`
- `tests/test_manifest.py`
- `tests/test_cache.py`
- `README.md` (channel architecture)
- Optional `maintenance.py` (thumbnails/database repair utilities)

---
## 8. Environment / Tooling Assumptions
- FastAPI runtime under central Mimir API loader (importlib-based) – necessitates explicit file-based imports.
- Pillow available for rendering & thumbnails.
- JSON metadata storage (no DB migrations needed) – safe to add new keys lazily.

---
## 9. Parking Lot (Questions for Later)
- Should gallery-specific settings override global per-field or full replace? (Clarify merge semantics.)
- Do we need per-gallery rotation strategies or global only?
- Is placeholder image customizable via API?
- Should thumbnail naming be standardized to a single pattern to simplify lookup?

---
## 10. Summary
This document freezes the current improvement backlog so focus can shift fully to stabilizing the Spotify channel. When returning, start with the critical import isolation refactor to align both channels under a unified, robust loading strategy.

> When ready to resume, search for the string `PHOTO_FRAME_RESUME_POINT` (add it when you open the file) to anchor new work.
