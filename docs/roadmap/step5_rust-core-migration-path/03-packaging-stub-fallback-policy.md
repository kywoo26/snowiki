# Packaging, Stub, and Fallback Policy

## Purpose

Define the non-performance policy that any future Rust extension must satisfy before Snowiki can ship it. This sub-step exists to keep packaging ergonomics, typing support, and operational fallback requirements from being deferred until after a native spike already exists.

## Scope

In scope:
- packaging strategy using PyO3 + maturin
- wheel policy for end-user installation
- type stub policy for the Python package surface
- decision on `abi3`
- dual-stack fallback and debug-surface requirements

Out of scope:
- writing build scripts or CI workflows now
- publishing wheels now
- implementing the Rust extension now
- changing the current Python-only runtime contract

## Non-goals

- Do not require users to install a Rust toolchain for normal use.
- Do not ship a native path without a guaranteed Python fallback.
- Do not hide native-load failures behind silent behavior changes.
- Do not grow a large opaque extension API that lacks Python typing or debug surfaces.

## Packaging strategy

### Build technology

Snowiki's native path should use:
- **PyO3** for Python bindings
- **maturin** for build and wheel packaging
- a **mixed Python + Rust package** where Python keeps the public orchestration surface and the extension provides only the hot-path kernels

### Why this is the preferred path

- it matches the provisional Step 5 decision record
- it keeps the Python package surface intact
- it offers the clearest route to wheels-first installation on Linux, macOS, and Windows

## Wheel policy

Snowiki should adopt a **wheels-first, no-toolchain-required** policy.

Required policy statements:
- supported end-user installs must succeed from published wheels on target platforms
- wheel availability is part of the release gate for any native-enabled release
- source builds may exist for maintainers, but they are not the primary user path
- absence or failure of the extension wheel must not make the package unusable

## `abi3` decision

### Current decision

- prefer **`abi3`** for the first native spike if the boundary remains narrow and declarative

### Rationale

- it reduces wheel matrix pressure
- it fits the intended small boundary surface
- it reinforces the requirement not to expose a large Python-version-sensitive native API

### Constraint

- if the boundary expands in a way that makes `abi3` impractical, Step 5 must record that explicitly before implementation approval rather than letting the decision drift silently

## Type stub policy

Snowiki should ship:
- checked-in `.pyi` files for the Python-facing native wrapper surface
- `py.typed` in the distributed package
- thin Python wrappers that present stable names and documentation around the extension boundary

Snowiki should not introduce custom stub-generation infrastructure unless the native API grows substantially beyond the small boundary currently proposed.

## Dual-stack fallback policy

### Required decision

- Snowiki will use a **dual-stack transition period**: pure Python path and optional Rust-accelerated path must coexist initially

### Required guarantees

1. the Python path remains functional when the extension is unavailable
2. tests can force Python-only execution for parity and debugging
3. runtime diagnostics can report whether Python or Rust executed
4. native-load failure degrades to Python behavior instead of aborting normal usage

### Why this is mandatory

- it protects install ergonomics
- it supports parity testing during migration
- it preserves debuggability when native behavior is opaque

## Debug-surface policy

Any native-enabled release must preserve or expose the following debug surfaces:
- `analyze`
- `explain`
- `describe_index_config`

These surfaces must work well enough to answer:
- what tokenizer/config is active
- why a query matched or did not match
- whether the Python or Rust path executed
- whether index compatibility requires rebuild

## Failure-handling policy

If the native extension fails to import, initialize, or validate compatibility:
- Snowiki must continue on the Python path
- the failure must be visible in diagnostics or logs
- users must not need to install a Rust toolchain to recover normal CLI behavior

## Deliverables

1. a documented packaging posture: PyO3 + maturin, mixed package, wheels first
2. an explicit `abi3` decision with conditions for revisiting it
3. a checked-in policy that `.pyi` + `py.typed` will cover the native wrapper surface
4. a fallback/debug policy that guarantees Python-path availability and inspection surfaces

## Acceptance criteria

This sub-step is complete only when all are true:

1. the packaging strategy explicitly uses PyO3 + maturin
2. the wheel policy makes clear that users do not need a Rust toolchain
3. the `abi3` decision is stated rather than implied
4. the dual-stack fallback policy guarantees a working Python path
5. required debug surfaces include `analyze`, `explain`, and `describe_index_config`

## Exit condition for implementation planning

Step 5 may proceed to an execution-ready native spike only if packaging policy still guarantees that users do not need a Rust toolchain and fallback to the Python path is guaranteed.
