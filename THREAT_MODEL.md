# DriftWatch Threat Model

This document defines the target-system threat model for DriftWatch. Archive-processing and analysis-host protections are documented separately in `SECURITY.md`.

## 1. Security Objective

DriftWatch identifies security-sensitive behavioural drift between two supplied browser-extension versions and produces evidence intended to prioritize manual security review.

DriftWatch does not determine malicious intent. Its risk score is a deterministic review-priority signal, not malware probability.

## 2. Target System

The current implementation targets Chromium-style browser extensions and supports Manifest V2 and Manifest V3 fields where implemented by the static analyzers. Its unit of analysis is a supplied pair of extension archives representing V1 and V2. It extracts the archives under security limits, analyzes their manifests and source text statically, and compares the observed states.

The system does not install or execute extensions, emulate a browser runtime, observe live user interactions, inspect server-side processing, or continuously monitor an installed extension. Browser-store metadata, signing trust, native-host behaviour, non-Chromium browser semantics, raw CRX container handling through the web upload form, and semantic execution of WebAssembly are unsupported or limited.

## 3. Adversary / Change Scenarios

DriftWatch may be used to prioritize review of changes associated with:

- a malicious developer update;
- a compromised maintainer or publishing account;
- an extension ownership transfer;
- a compromised dependency or build pipeline;
- intentionally harmful functionality;
- benign feature growth that increases security exposure; or
- accidental permission, host-scope, API, or network expansion.

The observed static drift cannot by itself prove which scenario occurred or establish developer intent.

## 4. Baseline Assumption

V1 is a historical baseline, not a trusted-safe baseline. DriftWatch reports changes relative to V1; it does not certify V1 as benign or secure.

Harmful behaviour that already exists in V1 and remains materially unchanged in V2 may not appear as drift. This is a major limitation of pairwise differential analysis.

## 5. Observable Signals

The current implementation can observe and compare:

- manifest fields and selected manifest-configuration changes;
- required and optional permission drift;
- host-permission and host-scope drift;
- statically visible sensitive browser-API drift;
- statically visible network and external-destination indicators;
- bounded decoded endpoint indicators;
- obfuscation, entropy, encoding, and dynamic-code indicators;
- package and source-structure drift; and
- same-file source-to-sink heuristics where applicable.

These are static indicators. Their presence or absence is not conclusive evidence of runtime behaviour or intent.

## 6. Evasion / False-Negative Mechanisms

DriftWatch may miss or understate behaviour involving:

- delayed or time-triggered activation;
- environment-, account-, locale-, site-, or user-dependent behaviour;
- remote configuration or server-controlled feature activation;
- endpoints assembled only at runtime;
- dynamically constructed or downloaded code;
- encrypted payloads or strings decrypted only at runtime;
- dynamic imports or indirect module loading;
- multi-file, asynchronous, callback, or event-driven data flows;
- data flows that require semantic or interprocedural analysis;
- WebAssembly semantics;
- behaviour implemented primarily by remote servers;
- harmful behaviour already present and unchanged in both versions; or
- changes introduced and then removed in skipped intermediate versions.

Bundling, unsupported syntax, incomplete parsing, and analyzer failures can also reduce observable evidence. Analyzer availability must therefore be considered when interpreting a report.

## 7. False-Positive Mechanisms

Review-priority signals may be raised by legitimate changes such as:

- minification or ordinary production bundling;
- generated code or generated resource bundles;
- legitimate telemetry, update checks, or service integrations;
- embedded domain lists, rulesets, fixtures, or other datasets;
- dependency or build-tool updates;
- large generated-file changes;
- benign permission, host, or API additions;
- test, development, localhost, or documentation endpoints; or
- same-file source and sink co-occurrence without a feasible data flow.

These mechanisms are reasons for analyst review, not reasons to infer maliciousness.

## 8. Pairwise Comparison Limitations

Interpretation depends on correct version identity and ordering. Skipped versions, rollback comparisons, non-consecutive pairs, repackaged archives, ambiguous identities, or incorrect timestamps can distort the meaning of a delta. A baseline that already contains risky behaviour can make a later version appear unchanged. Pairwise results should therefore be interpreted with provenance, release history, and version-order evidence.

## 9. Claims Boundary

DriftWatch can report:

> Security-sensitive behavioural drift was detected and should be reviewed.

DriftWatch cannot automatically conclude:

> This extension is malicious.

Source-to-sink evidence does not prove exfiltration. Network indicators do not prove malicious communication. Obfuscation indicators do not prove malicious intent. A low score does not certify safety, and a high score is not malware probability.

## 10. Human Review Role

Manual security review is required to interpret developer intent, release context, code semantics, endpoint purpose, proportionality of new privileges, and whether observed changes are acceptable for the extension's function.

The completed scoped validation used two independent blind human reviewers and governed two-stage adjudication for their five disagreements. These judgments strengthen provenance and expose uncertainty; they do not determine developer intent or create objective malware ground truth. The resulting four-record Gold Set is small, single-class, and restricted from training and tuning. No final external-validation conclusion is claimed.
