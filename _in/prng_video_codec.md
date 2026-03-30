# PRNG Seed Compression: Theory, Limits, and Video Application

## Rate-Distortion Analysis

### Information Budget

Each layer = 1 seed = 16 bits = 2 bytes.
After K layers: **16K bits** total information about the image.

This is a hard ceiling: regardless of search quality, the decoded image
cannot contain more mutual information with the target than 16K bits.

### Convergence Curve

Empirical (Che Guevara, face4x, 128×96 binary):

```
Seeds    Bits    Error    Δ per seed
  1       16     36.2%    — (base 8×8)
  5       80     30.0%    −1.2%/seed
  21     336     26.7%    −0.2%/seed  ← diminishing returns begin
 213    3408     26.4%    −0.001%/seed ← near floor
```

**Floor**: ~25% for this LFSR family on this image class.
Below this, PRNG patterns don't correlate with residual error.

### When PRNG beats naive coding

16 bits of seed covers the ENTIRE image via LFSR expansion.
16 bits of raw data covers only 16 pixels (or 2 bytes of compressed stream).

PRNG wins when:
- ΔError per seed > ΔError per 16 raw bits
- Typically true for first 20-50 seeds
- Breaks even around 100-200 seeds (image-dependent)
- After that, raw/LZ wins

**Crossover test**: for each seed, measure ΔE. Compare with:
- 16 raw pixel bits → ΔE_raw = 16/total_pixels * 100% ≈ 0.13%
- If ΔE_prng > 0.13% → seed is "profitable"

### Joint-2 extends the profitable zone

Greedy: each seed extracts ~ΔE_greedy bits of information about target.
Joint-2: pair of seeds extracts more because XOR(A,B) creates patterns
that neither A nor B alone can express.

Empirically: joint-2 finds 15-68% better solutions for overlapping regions.
This pushes the "profitable zone" from ~200 seeds to maybe ~300+ seeds
before hitting the floor.

## Application to Video

### Keyframe + Delta Architecture

```
Keyframe:    K seeds × 2 bytes (full face4x descent, ~26% error)
Delta frame: D seeds × 2 bytes (XOR correction to new target)
```

Since inter-frame difference is sparse (~10% pixels change),
delta needs far fewer seeds than keyframe.

### Temporal Dithering (Stochastic Resonance)

**Key insight**: PRNG noise at 25+ fps becomes perceptual grayscale.

Each frame has ~30% random error. But across N frames, the human visual
system averages them. The temporal average has error √(0.3²/N):
- 1 frame: 30% error
- 4 frames: 15% perceived error
- 16 frames: 7.5% perceived error
- 64 frames: 3.75% perceived error

This is **stochastic resonance**: noise helps perception!

The correct metric for video quality is not per-frame error but
**error of temporal average over K frames** vs target.

### Ideal Content

Best for PRNG compression:
- **Low-frequency**: faces, silhouettes, gradients (PRNG captures coarse structure well)
- **1-bit or low bit-depth**: binary images, high-contrast art
- **Low-motion video**: small deltas, one seed covers inter-frame difference
- **Stylized**: demoscene, pixel art, animation (low entropy)

Worst:
- High-frequency texture (fur, foliage, water)
- Each residual remains high-entropy, PRNG can't correlate

### Decoder Complexity

```
Classical video decoder:     DCT + motion compensation + entropy coding
                             ~100KB code, needs multiply+accumulate

PRNG video decoder:          LFSR + XOR
                             ~200 bytes Z80 code, no multiply needed
                             Runs on ANY hardware from 1976 onward
```

**Asymmetric**: encode = GPU brute-force (minutes-hours), decode = trivial (microseconds).
Encode once, play everywhere.

### R-D Comparison Framework

To prove the method works, build Rate-Distortion curve:

```
X-axis: rate = seeds × 16 bits
Y-axis: distortion = MSE or SSIM (for video: temporal average over K frames)

Compare:
1. Our PRNG method (seeds → LFSR → XOR)
2. Naive baseline (raw pixels at same bitrate)
3. LZMA/zlib compressed at same bitrate
4. H.264/MJPEG at same bitrate (for video)
5. Shannon R(D) bound (theoretical limit)
```

If PRNG curve is below naive for first N seeds → method extracts structure.
Crossover point with LZ/H.264 = practical limit of the method.

### Estimated Bitrates

```
Content type       Seeds/frame  Bytes/frame  FPS  Bitrate
Static portrait    213          426          1    3.4 Kbps
Animation (5 kf)   213          426          5    17 Kbps
Video (delta)      20-40        40-80        10   3.2-6.4 Kbps
Video (delta)      20-40        40-80        25   8-16 Kbps
Bad Apple keys     85           170          5    6.8 Kbps
```

For comparison: H.264 at similar quality ≈ 10-50 Kbps for 128×96.
PRNG is competitive at very low bitrates on ideal content.

## Open Questions

1. **PRNG family**: would different generators (xorshift, PCG, chaotic maps)
   give better R-D curves than LFSR-16?
2. **Joint-K for K>2**: diminishing returns? Or does joint-3 unlock new patterns?
3. **Adaptive regions**: auto-detect face landmarks → custom segment layout per frame?
4. **Temporal coherence**: share seeds between similar frames → reduce delta rate?
5. **Perceptual loss**: optimize for SSIM not pixel error → better visual quality?

## Delta Codec: Masked Two-Layer Architecture

### Key Insight (from discussion)

For delta frames (inter-frame difference), coarse layer is BOTH data AND mask:

```
Layer 1 (coarse, 8×8): LFSR seed → XOR blocks where delta exists
  → This naturally marks WHERE changes happened (mask)
  → ~80 blocks changed out of 768 = sparse

Layer 2 (fine, 1×1): LFSR seed → XOR ONLY inside coarse-activated blocks
  → Fine correction restricted to active zone
  → Works on ~5000 pixels instead of 49152 = 10× better signal/noise
```

### Why masking is critical

Without mask: fine seed must be neutral on 80% of image (no change zones)
  → wastes "correlation budget" on staying quiet
  → 65536 seeds, most can't satisfy both "be quiet here" + "be active there"

With mask: fine seed only evaluated on active zone
  → ALL 65536 candidates are useful (none wasted on neutrality)
  → dramatically better search quality per seed

### Decoder

```z80
; Coarse pass (8×8)
call lfsr_xor_8x8        ; XOR coarse pattern, remember activated blocks
; generates 96-byte bitmask (768 blocks / 8 bits) as side effect

; Fine pass (1×1)  
call lfsr_xor_1x1_masked ; XOR fine pattern ONLY where bitmask is set
```

Cost: +20 bytes code for mask check. Data: 4 bytes (2 seeds).

### Joint-2 on coarse+fine

Coarse seed (u16) + fine seed (u16) searched jointly as u32:
- 65536² = 4.3B candidates
- Coarse and fine optimized TOGETHER knowing the mask
- 132 seconds GPU, 4 bytes data per delta frame

### Estimated delta-frame budget

```
Movement type     Coarse seeds  Fine seeds  Total bytes
Static (0% change)    0            0           0
Slow (5% change)      1            1           4
Medium (15% change)   1            2           6
Fast (30% change)     2            3          10
Scene cut             full keyframe          426
```

For 10fps video with slow-medium movement:
  ~5 bytes/frame × 10fps = 50 bytes/sec = 400 bps
  3 minutes = 9000 bytes = 8.8 KB (!!!)
