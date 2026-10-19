# Inner arena owner investigation — go/no-go (§16.6, decision checkpoint)

Inputs: the trace-off real-scene SDK span census ([`../allocator-history`](../allocator-history/README.md),
`sdkbase1`), the corrected real-scene 16 KiB request trace (`allocfix16b`), the historical
splash/title `allocmin` counters (kept as history only), and the earlier pool/VMA studies named
in roadmap §16.2. All read-only; no page was discarded and no allocator state was touched.

## Measured owner groups (real gameplay, SDK span-table view)

| Owner group | Pages swapped (game-idle / precleanup) | Pages resident | Proven reclaimable |
| --- | --- | --- | --- |
| SDK state-1 large allocated spans | 280.1 / 294.8 MiB | 466 / 457 MiB | **no** — live allocations |
| SDK state-2 free spans | 96.7 / 101.1 MiB | 41.5 / 32.3 MiB | **no contract proven** |
| SDK metadata/other (state 3, small) | ~0.4 MiB | ~7.3 MiB | n/a (metadata) |
| Inner Unity/IL2CPP objects inside allocated spans | unmeasured at object level | — | **unattributable read-only** |
| TransferMemory zero sparse copy | bounded, separate lever | — | **yes** (see `../transfer-sparse-repeat`) |

## Go/no-go table

| Candidate change | Proven reclaimable bytes | Est. peak-resident saving | Cost / correctness risk | Verdict |
| --- | --- | --- | --- | --- |
| Release SDK **allocated** (state-1) span pages | 0 | n/a | would discard live owners; forbidden | **NO-GO** |
| `madvise`/decommit SDK **free** (state-2) spans from the runtime | none — no free contract | ≤ ~33–41 MiB resident, and only at a quiescent point | allocator free-list links/metadata may live inside those pages; no allocator lock is exposed to the runtime; aliases/GPU/DMA reuse and re-zero semantics unproven; wrong timing corrupts the allocator | **NO-GO** without an SDK-level free-page contract |
| Object-level release of inner Unity/GC suballocations | unattributable with a bounded pass | unknown | requires IL2CPP object-metadata joins and collection/unload timing machinery — outside the bounded scope; residency=0/all-zero does not prove non-use | **STOP** |
| TransferMemory sparse zero backing | mechanism verified byte-exact; kernel-visible commit avoidance | (measured separately, net SwapPSS −24…−34 MiB in the earlier pair) | already the smallest, contract-backed lever | continue in §16.5 only |

Notes: the swap figures are page-accounting observations from sequential read-only snapshots
(no allocator lock), not atomically consistent numbers, and free spans' resident share is the
only part a decommit could physically save at the peak. The earlier complete-gameplay
"owner exclusion" from the withdrawn `allocmin` capture is not reused; the corrected 16 KiB
request trace hit its event/slot caps (`incomplete=1`), so no request census at that level is
used to excuse any owner.

## Decision (per the §16.6 stop rule)

One full allocator census plus repeated real-scene transitions could not identify a safe
reclaimable owner for the remaining anonymous swap. **Park zero-swap as an unsupported
resource target on this ~1 GiB device.** Deep memory R&D stops here; no SDK trace is lowered
further, no speculative `madvise`, no swap-off cold boot. Zero-swap remains **NOT ACHIEVED**
and the release contract is the swap-enabled qualified build option (§16.9 row F), pending the
§16.5 sparse outcome and the §16.3 acceptance gate.
