# Sidebar: When Code Becomes Pixels — RMDA's CALL Chain Rendering

*Based on Hole #17 enigma (2021) by .ded^RMDA (Maxim Muchkaev).
256-byte intro for ZX Spectrum 48K. Source included with permission.*

---

## The Fastest Way to Fill a Screen

On the ZX Spectrum, the fastest way to write a byte to screen memory is
`LD (HL),A` at 7 T-states. With `INC HL` to advance the pointer, that's
13T per byte. For 6144 screen bytes: 79,872T ≈ 22.8ms per frame.

But there's a faster way. Much faster.

```z80
    LD   SP, $5800       ; stack pointer = end of screen
    CALL $XXXX           ; 17T — pushes return address to screen!
```

`CALL` does two things: it pushes the return address (PC+3) onto the
stack, then jumps to the target. If the stack pointer is aimed at screen
memory, the push **writes two bytes of pixel data as a side effect**.

**Cost: 8.5T per byte.** That's 35% faster than `LD (HL),A + INC HL`.

The "data" written is the address of the instruction after CALL — which
is determined by where the CALL instruction sits in memory. The pixel
pattern is literally the *address of the code itself*.

## How Hole #17 Works

The intro generates a screen full of random CALL instructions, then
executes them. Each CALL pushes its own address to screen memory,
creating a chaotic visual. The trick: the entire 42KB of RAM above the
screen ($5B00-$FFFF) is filled with a chain of CALL instructions, each
pointing to the next random location.

```
Memory layout after generation:

$5B00: CALL $A7F3    ← pushes $5B03 to screen, jumps to $A7F3
$5B03: (not a CALL — was overwritten by pRNG)
  ...
$A7F3: CALL $D821    ← pushes $A7F6 to screen, jumps to $D821
  ...
$D821: CALL $5B00    ← last CALL loops back to start
```

The generator works in three phases:

### Phase 1: Zero all RAM
```z80
clear:
    ld   (hl), e        ; E=0, zero this byte
    dec  hl              ; move backwards
    ld   a, h
    cp   #57             ; stop at $5700
    jr   nz, clear       ; hidden LD SP,HL embedded in JR!
```

Note the trick: `JR NZ, clear` assembles to bytes `20 FA`. When the JR
falls through (not taken), the CPU sees the next instruction starting at
the `FA` byte — which never happens here, but the label `clear` is
positioned so that during the attribute fill loop that follows, the `JR`
to `attr-1` hits `JR` one byte earlier, creating a hidden `LD SP,HL`
(opcode `31`) from the JR offset bytes. This is extreme size coding —
saving one byte by exploiting instruction alignment.

### Phase 2: Generate CALL chain with pRNG
```z80
newrnd:
    ld   (hl), #cd       ; write CALL opcode ($CD)
    inc  hl
    inc  hl
    ld   (hl), h         ; placeholder (non-zero to mark "used")
    dec  hl

rernd:
    call prnd             ; Patrik Rak CMWC pRNG → A = random byte
    cp   #5b              ; high byte must be ≥ $5B (above screen)
    jr   nc, next
    cpl                   ; if too low, just complement it!
                          ; $00-$5A → $FF-$A5 (always valid!)
next:
    ld   d, a             ; D = high byte of target address
    ; ...
    call prnd             ; low byte = any random value
    ld   e, a

    ; Check: is target address free (three zero bytes)?
    ld   a, (de)
    or   a
    jr   nz, rernd        ; occupied → try another random address
    ; ... check two more bytes ...

    ld   (hl), e          ; write target address into CALL
    ld   (hl), d
    ld   h, d             ; next CALL starts at target
    ld   l, e

    inc  bc               ; count generated CALLs
    ld   a, b
    cp   complexity       ; #EB ≈ 60,000 CALLs!
    jr   nz, newrnd
```

The `CPL` trick is brilliant: instead of looping to regenerate when the
random high byte is below $5B, it simply complements the byte. This maps
$00→$FF, $5A→$A5 — always valid. One instruction instead of a branch.

### Phase 3: Execute and render
```z80
    ld   sp, start_scr    ; SP → screen memory
    jp   (hl)              ; jump into the CALL chain!
```

Now every CALL in the chain pushes 2 bytes onto the screen-stack. The
interrupt handler resets SP periodically to create a scrolling effect.

### The pRNG: Patrik Rak's CMWC

The random generator is a Complement-Multiply-With-Carry (CMWC):

```z80
prnd:
    exx                    ; save main registers (EXX!)
    ld   hl, table         ; 10-byte state: 1 index + 1 carry + 8 table
    ld   a, (hl)           ; load index
    and  7
    inc  a
    ld   (hl), a           ; i = (i & 7) + 1
    inc  l
    ld   d, h
    add  a, l
    ld   e, a              ; DE → table[i]
    ld   a, (de)           ; y = table[i]
    ld   b, a
    ld   c, a
    ld   a, (hl)           ; A = carry
    sub  c                 ; \
    jr   nc, $+3           ;  } t = 253 × y + carry
    dec  b                 ;  } done by subtracting y three times
    sub  c                 ;  } from 256×y (= B:A initially)
    jr   nc, $+3           ;  }
    dec  b                 ;  }
    sub  c                 ;  }
    jr   nc, $+3           ;  }
    dec  b                 ; /
    ld   (hl), b           ; carry = t >> 8
    cpl                    ; result = ~(t & 0xFF)
    ld   (de), a           ; table[i] = result
    exx
    ret                    ; ~167T per random byte
```

Note: `EXX` is used to preserve the main register bank! The pRNG runs
entirely in the shadow bank (B'C'D'E'H'L'). This is exactly the dual-bank
technique — shadow registers as a separate computation context.

## What Makes This Remarkable

1. **Code IS data.** The pixel pattern is determined by the memory
   addresses where CALL instructions land. There's no separation between
   program and picture.

2. **The fastest screen write.** 8.5T per byte via CALL+PUSH, vs 13T for
   conventional LD+INC. 35% faster.

3. **Extreme size optimization.** Hidden `LD SP,HL` inside JR offsets.
   `CPL` instead of branch for address range clamping. Self-modifying
   pRNG table embedded after code.

4. **Dual-bank pRNG.** EXX isolates the random generator from the main
   program. No register conflicts, no save/restore overhead — just 4T to
   switch context.

5. **Everything fits in 256 bytes.** Screen generator, pRNG, interrupt
   handler, music player, keyboard input, and visual effects. Zero bytes
   wasted.

## The Brute-Force Opportunity

Maxim's approach: generate random CALL chains, hope for interesting visuals.
With GPU: test billions of pRNG seeds per second, score each screen for
visual quality (entropy, structure, symmetry, Hamming distance to target).

```
GPU SEED search:
  640 million seeds/second on RTX 4060 Ti
  4-byte seed space: exhaustive in 7 seconds
  5-byte seed space: 29 minutes
  Genetic algorithm: 10M evaluations in 16 milliseconds
```

This transforms "3 months of emulator at 10000%" into seconds on GPU.

---

*Hole #17 enigma placed at LoveByte 2021 (256 byte intro compo).
Full source: scene.org. Author: .ded^RMDA (Maxim Muchkaev), Samara, Russia.*
