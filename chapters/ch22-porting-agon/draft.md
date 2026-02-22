# Chapter 22: Porting --- Agon Light 2

> "The same instruction set, a completely different machine."

You have built the game. Five levels, four enemy types, a boss fight, AY music with sound effects, a loading screen, and a menu system --- all running on a ZX Spectrum 128K at 3.5 MHz, in 128 kilobytes of banked memory, rendering through a ULA that has not changed since 1982. Every byte is accounted for. Every cycle is earned.

Now you are going to port it to a machine that has the same CPU instruction set, five times the clock speed, four times the memory, hardware sprites, hardware tilemap scrolling, an SD card for loading, and a 24-bit flat address space with no banking.

This should be easy.

It is not easy. It is *different* in ways that will surprise you, and the surprises teach you things about both machines that you would not learn any other way.

---

## Same ISA, Different World

The Agon Light 2 runs a Zilog eZ80 at 18.432 MHz with 512 KB of flat RAM. The eZ80 is a direct descendant of the Z80 --- it executes the entire Z80 instruction set, uses the same register names, the same flags, the same mnemonics. If you write `LD A,(HL)` on a Spectrum and `LD A,(HL)` on an Agon, the opcode is identical. The behaviour is identical. A Z80 programmer can sit down at an Agon and start writing code immediately.

But the Agon is not a fast Spectrum. It is a fundamentally different architecture wearing a familiar face. The differences fall into three categories:

**What the eZ80 adds.** 24-bit registers, 24-bit addressing, a 16 MB address space (of which 512 KB is populated), new instructions for 24-bit arithmetic, and a mode system (ADL vs Z80-compatible) that controls register width and address generation.

**What the VDP replaces.** The Spectrum's ULA --- the chip that reads video memory and paints the screen --- is replaced by a completely separate processor. The Agon's VDP is an ESP32 microcontroller running the FabGL graphics library. It handles display output, sprites, tilemaps, and audio. The eZ80 CPU communicates with the VDP over a high-speed serial link, sending command sequences. There is no shared video memory. You do not write pixels to an address; you send commands to a coprocessor.

**What disappears.** Banked memory, contended memory, the attribute grid, the interleaved screen layout, the 6,912-byte framebuffer, the border as a timing tool, direct framebuffer access, cycle-level raster synchronization. All gone.

To port our Spectrum game, we need to understand what transfers directly, what needs rewriting, and what needs rethinking from scratch.

---

## The Architecture at a Glance

Before diving into code, let us lay out the two machines side by side.

| Feature | ZX Spectrum 128K | Agon Light 2 |
|---------|-----------------|---------------|
| CPU | Z80A | eZ80 (Z80-compatible + ADL extensions) |
| Clock | 3.5 MHz (7 MHz on turbo clones) | 18.432 MHz |
| RAM | 128 KB (8 x 16 KB banks, switched via port $7FFD) | 512 KB flat (24-bit addressing) |
| Address space | 16-bit (64 KB visible at a time) | 24-bit (16 MB, 512 KB populated) |
| Video | ULA: 256x192, 8x8 attribute colour, direct memory-mapped | VDP (ESP32 + FabGL): multiple modes, up to 640x480, sprites, tilemaps |
| Framebuffer access | Direct: write to $4000--$5AFF | Indirect: send VDP commands over serial |
| Sprites | Software only | Hardware: up to 256, managed by VDP |
| Scrolling | Software only (shift entire framebuffer) | Hardware tilemap scrolling via VDP |
| Sound | AY-3-8910 (3 channels + noise) | VDP audio (ESP32 synthesis, multiple waveforms, ADSR) |
| Storage | Tape / DivMMC (esxDOS) | SD card (FAT32, MOS file API) |
| OS | None (bare metal) / esxDOS for file I/O | MOS (Machine Operating System) |
| Frame budget | ~71,680 T-states (Pentagon) | ~368,640 T-states (at 50 Hz) |

The frame budget ratio is roughly 5:1. But this understates the real difference, because many operations that consume CPU cycles on the Spectrum --- sprite rendering, screen scrolling, framebuffer management --- are offloaded to the VDP on the Agon. The eZ80 CPU spends its cycles on game logic, not pixel pushing.

---

## ADL Mode vs Z80-Compatible Mode

This is the single most important architectural concept for any Z80 programmer approaching the eZ80. Get it wrong and your code will crash in ways that are difficult to debug. Get it right and you unlock the full power of the chip.

The eZ80 has two operating modes:

**Z80-compatible mode (Z80 mode).** Registers are 16 bits wide. Addresses are 16 bits. The MBASE register provides the upper 8 bits of every address, effectively placing your 64 KB window somewhere in the 16 MB address space. Code behaves exactly like a standard Z80 --- `LD HL,$4000` loads a 16-bit value, `JP (HL)` jumps to a 16-bit address (with MBASE prepended), `PUSH HL` pushes 2 bytes onto the stack.

**ADL mode (Address Data Long).** Registers are 24 bits wide. Addresses are 24 bits. `LD HL,$040000` loads a 24-bit value, `JP (HL)` jumps to a full 24-bit address, `PUSH HL` pushes 3 bytes onto the stack. This is the native mode of the eZ80.

MOS boots the Agon in ADL mode. Your application starts in ADL mode. Most Agon software runs entirely in ADL mode. But Z80-compatible mode exists, and understanding the interaction between the two is critical.

### Why You Might Use Z80 Mode

If you are porting Z80 code from the Spectrum, you might think: "just switch to Z80 mode and run my existing code." This works, up to a point. Your 16-bit address calculations, your `DJNZ` loops, your `LDIR` block copies --- they all behave identically in Z80 mode. MBASE is set so that the 16-bit addresses map to the right region of the Agon's memory.

The problem is *interacting with everything else*. MOS API calls expect ADL mode. VDP commands are sent through MOS routines that assume 24-bit stack frames. If you are in Z80 mode and call a MOS routine, the stack frame will be wrong --- MOS pushes 3 bytes per return address, your Z80-mode code pushed 2. The result is stack corruption and a crash.

### The Mode Switching Mechanism

The eZ80 provides special prefixes for switching modes within a single instruction:

| Prefix | Effect |
|--------|--------|
| `.SIS` (suffix) | Execute the following instruction in Z80 mode (short registers, short addresses) |
| `.LIS` | Execute in: Long registers, Short addresses |
| `.SIL` | Execute in: Short registers, Long addresses |
| `.LIL` | Execute in ADL mode (long registers, long addresses) |

And for calls and jumps:

| Instruction | From mode | To mode |
|-------------|-----------|---------|
| `CALL.IS addr` | ADL | Z80 |
| `CALL.IL addr` | Z80 | ADL |

The `.IS` suffix means "Instruction Short" --- the call instruction itself uses short (16-bit) conventions for the return address. `.IL` means "Instruction Long" --- the call pushes a 24-bit return address.

Here is the practical pattern for calling MOS from Z80-mode code:

```z80
; In Z80-compatible mode, calling a MOS API function
; We need to switch to ADL mode for the call

    ; Method: use RST.LIL $08 (MOS API entry point)
    ; .LIL means "long instruction, long mode" ---
    ; pushes a 24-bit return address and enters ADL mode
    RST.LIL $08        ; call MOS API in ADL mode
    DB      mos_func   ; MOS function number follows
    ; MOS returns to us in Z80 mode (matching our caller)
```

MOS provides RST $08 as a unified API entry point. The `.LIL` suffix handles the mode transition cleanly. After the call, execution returns to your Z80-mode code with the correct stack state.

### The Practical Rule

For porting, the cleanest approach is: **run your game logic in ADL mode and translate your Z80 code to use 24-bit conventions from the start.** Do not try to run in Z80 mode and switch back and forth for every MOS call. The mode-switching overhead and the risk of stack mismatches are not worth it.

This means your port will not be a byte-for-byte copy of the Spectrum code. It will be a *translation*. The algorithms are the same. The logic is the same. The register usage is mostly the same. But every address is 24 bits wide, every stack push is 3 bytes, and every immediate address load carries an extra byte.

### The MBASE Trap

If you do use Z80 mode, MBASE determines the upper 8 bits of every memory address. On boot, MOS sets MBASE to $00, meaning Z80-mode addresses $0000--$FFFF map to physical addresses $000000--$00FFFF. If your code or data lives above $00FFFF (above the first 64 KB), Z80-mode code cannot reach it without changing MBASE.

This is a trap for Spectrum porters who think "I have 512 KB, I will put my level data at $080000." In Z80 mode, that address does not exist. You must either use ADL mode to access it or set MBASE to $08 (making addresses $0000--$FFFF map to $080000--$08FFFF). But changing MBASE affects *all* memory accesses, including instruction fetches --- so your code had better be in that region too, or you will jump into garbage.

The advice is simple: stay in ADL mode. Use the full 24-bit address space natively.

---

## What Transfers Directly

Not everything changes. A surprising amount of your Spectrum game logic ports with minimal modification.

### Game Logic and Entity System

The entity system from Chapter 18 --- the structure arrays holding X, Y, type, state, animation frame, velocity, health, and flags --- transfers almost verbatim. The main loop structure (HALT, input, update, render, repeat) is identical in concept, though the specific HALT and interrupt mechanism differs.

Here is the entity update loop on the Spectrum:

```z80
; Spectrum: Update all entities
; IX points to entity array, B = entity count
update_entities:
    ld   ix,entities
    ld   b,MAX_ENTITIES
.loop:
    ld   a,(ix+ENT_FLAGS)
    bit  0,a               ; bit 0 = active?
    jr   z,.skip

    call update_entity      ; process this entity

.skip:
    ld   de,ENT_SIZE        ; size of one entity struct
    add  ix,de              ; advance to next entity
    djnz .loop
    ret
```

And on the Agon:

```z80
; Agon (ADL mode): Update all entities
; IX points to entity array, B = entity count
update_entities:
    ld   ix,entities        ; 24-bit address, loaded as 3 bytes
    ld   b,MAX_ENTITIES
.loop:
    ld   a,(ix+ENT_FLAGS)
    bit  0,a
    jr   z,.skip

    call update_entity

.skip:
    ld   de,ENT_SIZE        ; DE is now 24-bit; ENT_SIZE may differ
    add  ix,de              ; 24-bit add
    djnz .loop
    ret
```

The logic is identical. The instructions are identical. The difference is that IX, DE, and the program counter are all 24 bits wide. The assembler handles the encoding --- `LD IX,entities` emits a 24-bit immediate instead of a 16-bit one. The entity struct itself might be identical, or you might widen the position fields to 24-bit for larger level maps. That is a design decision, not a porting constraint.

### AABB Collision Detection

The collision code from Chapter 19 transfers directly. AABB checks use 8-bit or 16-bit comparisons --- the same CP, SUB, and conditional jump instructions work identically on both machines.

```z80
; AABB collision check: identical on both platforms
; A = entity1.x, B = entity1.x + width
; C = entity2.x, D = entity2.x + width
check_overlap_x:
    ld   a,(ix+ENT_X)
    cp   (iy+ENT_X2)       ; entity1.x < entity2.x+width?
    ret  nc                 ; no overlap
    ld   a,(ix+ENT_X2)
    cp   (iy+ENT_X)        ; entity1.x+width > entity2.x?
    ret  c                  ; no overlap
    ; overlap on X axis confirmed
```

### Fixed-Point Arithmetic

All fixed-point 8.8 calculations --- gravity, velocity, friction, acceleration --- port without changes. The shift-and-add patterns, the 16-bit additions, the right-shift friction:

```z80
; Apply gravity: velocity_y += gravity
; Works identically on both platforms
    ld   a,(ix+ENT_VY_LO)
    add  a,GRAVITY_LO
    ld   (ix+ENT_VY_LO),a
    ld   a,(ix+ENT_VY_HI)
    adc  a,GRAVITY_HI
    ld   (ix+ENT_VY_HI),a
```

Byte-level arithmetic does not care whether the registers are notionally 16 or 24 bits wide. The accumulator is always 8 bits. Carry propagation works the same way.

### State Machine

The game state machine (title, menu, gameplay, pause, game over) uses a jump table indexed by state number. On the Spectrum:

```z80
; Spectrum: dispatch game state
    ld   a,(game_state)
    add  a,a               ; multiply by 2 (16-bit pointers)
    ld   e,a
    ld   d,0
    ld   hl,state_table
    add  hl,de
    ld   a,(hl)
    inc  hl
    ld   h,(hl)
    ld   l,a
    jp   (hl)

state_table:
    dw   state_title
    dw   state_menu
    dw   state_game
    dw   state_pause
    dw   state_gameover
```

On the Agon, the pointer table stores 24-bit addresses:

```z80
; Agon (ADL mode): dispatch game state
    ld   a,(game_state)
    ld   e,a
    ld   d,0               ; DE = state index (24-bit, upper byte zero)
    ld   hl,a              ; HL = state * 3
    add  hl,hl             ; HL = state * 2
    add  hl,de             ; HL = state * 3 (24-bit pointers)
    ld   de,state_table
    add  hl,de
    ld   hl,(hl)           ; load 24-bit pointer
    jp   (hl)

state_table:
    dl   state_title       ; DL = define long (24-bit)
    dl   state_menu
    dl   state_game
    dl   state_pause
    dl   state_gameover
```

The change: pointers are 3 bytes instead of 2, so the index multiplication changes from `*2` to `*3`, and the table uses `DL` (define long) instead of `DW` (define word). The logic is otherwise identical.

---

## What Needs Rewriting

### Rendering: From Framebuffer to VDP Commands

This is the largest single change in the port. On the Spectrum, rendering means writing bytes to video memory addresses. The entire rendering pipeline --- sprite drawing, screen clearing, tile painting, scrolling --- is CPU code that manipulates memory at $4000--$5AFF.

On the Agon, rendering means sending VDP command sequences. The VDP understands a protocol based on VDU byte streams (the same VDU command system used by BBC BASIC, extended with Agon-specific commands). You send a sequence of bytes to the VDP through MOS, and the ESP32 processes them.

#### Sprites

On the Spectrum (from Chapter 16), drawing a 16x16 masked sprite costs roughly 1,200 T-states of CPU time --- reading mask bytes, ANDing with the screen, ORing the sprite data, writing back. You do this for every sprite, every frame.

On the Agon, you upload the sprite bitmap *once*, and then move it by sending a position update:

```z80
; Agon: Create and position a hardware sprite
; Step 1: Upload sprite bitmap (done once at init)
;   VDU 23, 27, 4, spriteNum   ; select sprite
;   VDU 23, 27, 0, w, h        ; set dimensions
;   followed by pixel data

; Step 2: Move sprite (done every frame)
; VDU 23, 27, 4, spriteNum     ; select sprite
; VDU 23, 27, 13, x.lo, x.hi, y.lo, y.hi  ; set position

move_sprite:
    ; Send VDU command to move sprite
    ld   a,23
    rst  $10                ; MOS: output byte to VDP
    ld   a,27
    rst  $10
    ld   a,4               ; command: select sprite
    rst  $10
    ld   a,(sprite_num)
    rst  $10

    ld   a,23
    rst  $10
    ld   a,27
    rst  $10
    ld   a,13              ; command: move sprite to
    rst  $10

    ld   a,(sprite_x)      ; X low byte
    rst  $10
    ld   a,(sprite_x+1)    ; X high byte
    rst  $10
    ld   a,(sprite_y)      ; Y low byte
    rst  $10
    ld   a,(sprite_y+1)    ; Y high byte
    rst  $10

    ; VDU 23, 27, 15        ; show sprite (update display)
    ld   a,23
    rst  $10
    ld   a,27
    rst  $10
    ld   a,15
    rst  $10
    ret
```

Each `RST $10` sends one byte to the VDP through MOS. The total CPU cost of moving a sprite is approximately 13 bytes sent x ~30 T-states per RST call = ~390 T-states. Compare that to the Spectrum's ~1,200 T-states for a full masked sprite draw. And the Agon version does not need background save/restore --- the VDP composites sprites over the background automatically.

The trade-off: latency. The VDP processes commands asynchronously. Between sending the "move sprite" command and the sprite actually appearing at the new position, there is a serial transfer delay and a VDP processing delay. For smooth animation, you need to send all sprite updates early in the frame and trust that the VDP will process them before the next screen refresh.

#### Tilemap Scrolling

On the Spectrum, horizontal scrolling means shifting every byte of video memory left or right --- a chain of `RLC` or `RRC` instructions across hundreds of bytes, consuming a substantial fraction of the frame budget (we calculated the cost in Chapter 17). Vertical scrolling requires copying scan lines with awareness of the interleaved memory layout.

On the Agon, the VDP supports hardware tilemaps:

```z80
; Agon: Set up a tilemap (done once)
; VDU 23, 27, 20, tileWidth, tileHeight
; VDU 23, 27, 21, mapWidth.lo, mapWidth.hi, mapHeight.lo, mapHeight.hi

; Scroll the tilemap (every frame)
; VDU 23, 27, 24, offsetX.lo, offsetX.hi, offsetY.lo, offsetY.hi

scroll_tilemap:
    ld   a,23
    rst  $10
    ld   a,27
    rst  $10
    ld   a,24              ; command: set scroll offset
    rst  $10

    ld   hl,(scroll_x)
    ld   a,l
    rst  $10               ; offsetX low
    ld   a,h
    rst  $10               ; offsetX high
    ld   hl,(scroll_y)
    ld   a,l
    rst  $10               ; offsetY low
    ld   a,h
    rst  $10               ; offsetY high
    ret
```

Eight bytes sent. Perhaps 240 T-states of CPU time. On the Spectrum, a full-screen horizontal pixel scroll costs tens of thousands of T-states. The Agon does it in hardware for nearly free.

But you must set up the tilemap first: upload tile definitions, define the map dimensions, populate the map with tile indices. This is a one-time cost at level load, not a per-frame cost. On the Spectrum, your tile data lives in banked RAM and is rendered into the framebuffer by your own code. On the Agon, tile data lives in VDP memory and is rendered by the ESP32. Your role changes from "graphics engine programmer" to "VDP command sequencer."

#### Screen Layout

The entire nightmare of the Spectrum's interleaved screen layout --- the split addressing, the DOWN_HL routines, the careful calculations to convert (x, y) coordinates to memory addresses --- vanishes. The Agon's VDP works in screen coordinates. You say "draw at (100, 50)" and the VDP handles the rest.

This means the DOWN_HL routine from Chapter 2, the screen address lookup tables, the attribute address calculations --- none of it ports. It is simply deleted. The equivalent operation on the Agon is "send a coordinate pair to the VDP."

---

## What Needs Rethinking

Some Spectrum patterns are so deeply embedded in the game architecture that you cannot just rewrite the rendering layer. The *design* needs to change.

### Memory Architecture

On the Spectrum, you carefully planned which data goes in which bank:

- Banks 0--3: level data, tilesets, sprite graphics
- Banks 4--6: music patterns, sound effects, lookup tables
- Bank 7: shadow screen for double buffering

Every bank switch costs a port write and limits what code can see what data. The game architecture is shaped by the 16 KB window into a 128 KB space.

On the Agon, all 512 KB is visible simultaneously. There is no banking. There is no shadow screen trick (the VDP handles double buffering internally). You can have your entire game --- all five levels, all tilesets, all sprites, all music --- resident in memory at once. Level transitions do not require loading from tape or disk; you just point to a different region of RAM.

This is liberating, but it also removes a constraint that forced good architecture. On the Spectrum, you were forced to think about data locality, about what needed to be co-resident, about load sequences. On the Agon, you can be sloppy. Do not be sloppy. The Agon has 512 KB, not infinity. A well-organized memory map is still a virtue.

Typical Agon memory layout for the ported game:

```
$000000 - $00FFFF   MOS and system (reserved)
$040000 - $04FFFF   Game code (~64 KB)
$050000 - $06FFFF   Level data, all 5 levels (~128 KB)
$070000 - $07FFFF   Music and SFX data (~64 KB)
$080000 - $0FFFFF   Free / working buffers
```

Everything is addressable with a single `LD HL,$070000` --- no bank switching, no port writes.

### Loading

On the Spectrum, loading from tape is a minutes-long process with a distinctive audio signature. Even with DivMMC and esxDOS, file access is a sequence of RST $08 calls:

```z80
; Spectrum + esxDOS: load a file
    ld   a,'*'             ; current drive
    ld   ix,filename
    ld   b,$01             ; read-only
    rst  $08               ; esxDOS call
    DB   $9A               ; F_OPEN
    ; A = file handle

    ld   ix,buffer
    ld   bc,size
    rst  $08
    DB   $9D               ; F_READ
    ; Data loaded

    rst  $08
    DB   $9B               ; F_CLOSE
```

On the Agon, MOS provides a file API that reads directly from the SD card:

```z80
; Agon: load a file using MOS API
    ld   hl,filename       ; 24-bit pointer to filename string
    ld   de,buffer         ; 24-bit pointer to destination
    ld   bc,size           ; 24-bit max size
    ld   a,mos_fopen       ; MOS file open function
    rst  $08               ; MOS API call
    ; A = file handle

    ld   a,mos_fread       ; MOS file read function
    rst  $08
    ; Data loaded

    ld   a,mos_fclose
    rst  $08
```

The pattern is similar --- open, read, close --- but the Agon reads from FAT32 on an SD card, which is fast enough that you can load level data between scenes without a visible delay. No loading screens needed. No tape-loading routines. No block-loading optimization.

### Sound

The Spectrum's AY-3-8910 is programmed by writing directly to hardware registers through I/O ports. Every note, every envelope change, every noise burst is a specific register value written at a specific time.

The Agon's audio is handled by the VDP. You send sound commands over the same serial link used for graphics:

```z80
; Agon: play a note
; VDU 23, 0, 197, channel, volume, freq.lo, freq.hi, duration.lo, duration.hi

play_note:
    ld   a,23
    rst  $10
    xor  a                 ; 0
    rst  $10
    ld   a,197             ; sound command
    rst  $10
    ld   a,(channel)
    rst  $10
    ld   a,(volume)
    rst  $10
    ld   hl,(frequency)
    ld   a,l
    rst  $10
    ld   a,h
    rst  $10
    ld   hl,(duration)
    ld   a,l
    rst  $10
    ld   a,h
    rst  $10
    ret
```

The Agon's sound system supports multiple waveforms (sine, square, triangle, sawtooth, noise) and per-channel ADSR envelopes --- features the AY does not have. But the programming model is completely different. You cannot write raw register values; you send high-level note commands. Your AY music player --- the IM2 interrupt handler that reads pattern data and updates 14 AY registers every frame --- does not port at all. You need a new music driver that translates your pattern data into VDP sound commands.

One approach: write a thin abstraction layer that both platforms share.

```z80
; Abstract sound interface
; Spectrum implementation:
sound_play_note:
    ; A = channel, B = note, C = instrument
    ; ... look up AY register values, write to ports $FFFD/$BFFD
    ret

; Agon implementation:
sound_play_note:
    ; A = channel, B = note, C = instrument
    ; ... convert to VDP sound command, send via RST $10
    ret
```

Same call signature. Different internals. The game code calls `sound_play_note` without knowing which platform it is running on.

### Input

The Spectrum reads keyboard state by probing port $FE with half-row addresses in the accumulator. Kempston joystick is read from port $1F. These are raw I/O port reads with specific bit patterns.

The Agon reads keyboard state through MOS:

```z80
; Spectrum: read keyboard
    ld   a,$FD             ; half-row: Q W E R T
    in   a,($FE)
    bit  0,a               ; bit 0 = Q
    ; ...

; Agon: read keyboard via MOS
    ld   a,mos_getkey      ; MOS: get key state
    rst  $08
    ; A = key code, or 0 if no key pressed
```

The Spectrum gives you a bitmask of simultaneously pressed keys, ideal for game input (you can detect multiple keys at once). The Agon's MOS keyboard API is event-based: it gives you the most recent key pressed. For game input with simultaneous key detection, you typically use the MOS keyboard map --- a region of memory updated by MOS that reflects the state of all keys:

```z80
; Agon: read simultaneous keys from keyboard map
    ld   a,(mos_keymap+KEY_LEFT)   ; 1 if left arrow held, 0 if not
    or   a
    jr   z,.no_left
    ; move player left
.no_left:
    ld   a,(mos_keymap+KEY_RIGHT)
    or   a
    jr   z,.no_right
    ; move player right
.no_right:
```

This is functionally equivalent to the Spectrum's bitmask approach, just organized differently. The port is straightforward: replace port reads with memory reads from the keyboard map.

---

## eZ80 at 18 MHz: What Still Matters, What Does Not

The eZ80 is roughly five times faster than the Z80A in raw clock speed. But many eZ80 instructions also execute in fewer clock cycles than their Z80 equivalents --- single-byte register instructions often complete in 1 cycle instead of 4. The effective speedup for typical code is somewhere between 5x and 20x depending on the instruction mix.

This changes the optimization calculus dramatically.

### What Still Matters: Inner Loop Efficiency

Even at 18 MHz with 368,000 T-states per frame, the inner loop still matters for CPU-intensive operations. If you are doing collision checks against a tilemap, iterating over 200 entities, or processing AI state machines for dozens of enemies, the per-iteration cost of your hot loop adds up.

The core Z80 optimization techniques --- keeping values in registers instead of memory, using `INC L` instead of `INC HL` where possible, avoiding IX/IY indexed instructions for hot paths (they carry a 2-cycle prefix penalty on eZ80, just as they carry a 4-T-state penalty on Z80) --- still produce measurable improvements.

```z80
; Tight entity scan: same optimization principles on both platforms
; Prefer: register-to-register ops, direct addressing, DJNZ
; Avoid: IX-indexed loads in hot inner loops when possible

scan_entities_fast:
    ld   hl,entity_flags    ; pointer to flags array
    ld   b,MAX_ENTITIES
.loop:
    ld   a,(hl)
    bit  0,a
    call nz,process_entity
    inc  hl                 ; next entity flag (assume 1-byte stride)
    djnz .loop
    ret
```

This pattern --- minimal memory access, tight register usage, `DJNZ` loop control --- is optimal on both the Z80 at 3.5 MHz and the eZ80 at 18 MHz. Good code is good code.

### What Becomes Irrelevant: Memory Conservation Tricks

On the Spectrum, memory pressure drives much of the engineering. Pre-shifted sprites store 4 or 8 copies of each sprite, consuming 4x--8x the memory, as a speed/memory trade-off. Compression is mandatory for fitting demo data into 128 KB. Lookup tables are carefully sized to balance precision against memory cost. Bank switching adds architectural complexity for the sole purpose of addressing more than 64 KB at a time.

On the Agon, with 512 KB of flat RAM and SD card storage for anything that does not need to be resident, these conservation techniques are unnecessary. You can store 8 pre-shifted copies of every sprite without worrying about memory. You can keep all lookup tables at full precision. You can keep all five levels in RAM simultaneously.

This does not mean you should waste memory. But it means that optimization decisions driven by memory scarcity --- "should I use a 256-byte sine table or a 128-byte one?" --- become irrelevant. Use 256. Use 1,024 if the precision helps.

### What Becomes Irrelevant: Self-Modifying Code

On the Spectrum, self-modifying code (SMC) is a standard optimization technique. You write instructions that patch their own immediate operands to avoid memory lookups:

```z80
; Spectrum: self-modifying code for speed
    ld   a,0               ; operand patched at runtime
    ; ... (the $00 after LD A is overwritten with the real value)
```

On the eZ80, SMC still works (the eZ80 does not have an instruction cache that would invalidate), but the motivation is weaker. The extra cost of a memory load is smaller relative to the total frame budget. More importantly, MOS maps some memory regions as read-only, and certain Agon firmware versions may restrict execution of modified code depending on memory region. SMC is not prohibited on the Agon, but it is rarely necessary and can cause subtle problems.

### What Becomes Irrelevant: Stack Tricks for Rendering

On the Spectrum, abusing the stack pointer for fast screen fills (DI, set SP to screen address, PUSH data repeatedly) is a classic trick because PUSH writes 2 bytes in 11 T-states --- faster than any other write mechanism. On the Agon, you are not writing to a framebuffer at all. The VDP handles rendering. Stack tricks for display are meaningless.

---

## The Comparison Table

Here is the side-by-side comparison of the same game on both platforms. These numbers are representative of the platformer built in Chapters 21--22.

| Metric | ZX Spectrum 128K | Agon Light 2 |
|--------|-----------------|---------------|
| **Game code size** | ~12 KB | ~14 KB |
| **Rendering code** | ~5 KB (sprite engine, scroll, screen mgmt) | ~2 KB (VDP command sequences) |
| **Total code** | ~17 KB | ~16 KB |
| **Level data (all 5)** | ~40 KB (compressed, loaded per-level) | ~60 KB (uncompressed, all resident) |
| **Sprite/tile graphics** | ~20 KB (packed, 1bpp + masks) | ~80 KB (8bpp RGBA, uploaded to VDP) |
| **Music + SFX** | ~16 KB (PT3 + SFX tables) | ~20 KB (converted format + waveform data) |
| **Total data** | ~76 KB (fits in 128 KB with banking) | ~160 KB (fits in 512 KB easily) |
| **Compression needed?** | Yes, mandatory | No, optional |
| **Sprite draw cost** | ~1,200 T/sprite (software) | ~400 T/sprite (VDP commands) |
| **Scroll cost per frame** | ~15,000--30,000 T (software shift) | ~240 T (VDP offset command) |
| **Frame budget** | ~71,680 T | ~368,640 T |
| **Achievable fps** | 25--50 (depends on entity count) | 60 (VDP-limited, not CPU-limited) |
| **Dev complexity** | High (memory banking, screen layout, rendering engine) | Medium (VDP protocol, MOS API, ADL mode) |
| **Visual result** | Monochrome or 2-colour-per-cell sprites, attribute colour, 256x192 | Full colour sprites, smooth scrolling, 320x240 or higher |

The code size difference is instructive. On the Spectrum, the *rendering engine* is a substantial fraction of the codebase. On the Agon, VDP commands replace most of that code. But the Spectrum game is smaller in total data because everything is compressed and packed tightly. The Agon version uses more memory for richer assets (8-bit-per-pixel sprites instead of 1-bit-per-pixel with masks).

The frame budget comparison is the most striking number. The Agon game is *CPU-idle most of the frame*. After processing game logic, sending sprite updates, and handling input, the eZ80 has nothing to do until the next frame. On the Spectrum, you are fighting for every cycle to fit everything into the budget.

---

## The Porting Process: Step by Step

Here is the practical sequence for porting the Chapter 21 game to the Agon.

### Step 1: Set Up the Agon Project

Create a new project with the Agon toolchain. You will need:

- An eZ80 assembler (ez80asm or the Zilog ZDS tools)
- The MOS API header file (mos_api.inc) defining function numbers and constants
- A way to transfer the binary to the Agon (SD card or serial upload)

Your entry point is different from the Spectrum. Instead of `ORG $8000` with a raw JP to your start address, the Agon loads executables at $040000 and MOS passes control to that address:

```z80
; Agon: application entry point
    .ASSUME ADL=1          ; we are in ADL mode
    ORG  $040000

    JP   main              ; standard entry

main:
    ; Your game starts here
    ; ... initialize VDP, load assets, enter game loop
```

### Step 2: Replace the Rendering Layer

This is the bulk of the work. Delete the Spectrum rendering code and replace it with VDP command sequences:

1. **Upload sprite bitmaps to VDP.** Convert your 1bpp sprite data to the VDP's bitmap format (typically 8bpp RGBA). Send the pixel data using VDU 23,27 sprite definition commands.

2. **Upload tileset to VDP.** Convert your 8x8 tiles from Spectrum attribute format to the VDP's tile format. Define the tilemap dimensions and populate it with tile indices for the current level.

3. **Replace the sprite draw routine** with VDU 23,27 sprite position commands (as shown earlier).

4. **Replace the scroll routine** with VDU 23,27 tilemap scroll offset commands.

5. **Delete the screen address calculation code**, the DOWN_HL routine, the attribute address routines, and all direct framebuffer writes.

### Step 3: Translate the Game Logic

Walk through the game logic code (entity update, collision detection, physics, AI, state machine) and adjust for ADL mode:

- Change all `DW` (define word) to `DL` (define long) for address tables.
- Change pointer arithmetic from 16-bit to 24-bit where addresses are involved.
- Verify that `PUSH`/`POP` pairs are balanced --- each push is now 3 bytes, not 2.
- Check that `LDIR` and `LDDR` block copy counts are correct (BC is 24-bit in ADL mode; if your count fits in 16 bits, the upper byte must be zero).

### Step 4: Rewrite Sound

Write a new music driver that reads your pattern data and emits VDP sound commands instead of AY register writes. The pattern data format can remain the same; only the output stage changes.

### Step 5: Rewrite Input

Replace port reads with MOS keyboard map reads. The keymap approach is simple and provides simultaneous key detection.

### Step 6: Rewrite Loading

Replace esxDOS file operations with MOS file API calls. The pattern is similar; only the function numbers and calling convention differ.

### Step 7: Test and Tune

Run the game. Verify sprite positions, collision boxes, scrolling speed, sound timing. The VDP's asynchronous processing means that visual updates may arrive one frame later than expected --- adjust your game timing if needed.

---

## What Each Platform Forces You To Do Better

This is the real lesson of porting. Every platform has constraints that push you toward better engineering, but the constraints are different.

### The Spectrum Forces You To Be Efficient

When your frame budget is 71,680 T-states and your sprite engine alone consumes 12,000 of them, you learn to count cycles. You learn to use `INC L` instead of `INC HL`. You learn to unroll loops. You learn to pre-compute everything you can. You learn to think about data layout --- keeping related data in contiguous memory, aligning buffers to page boundaries, arranging structs so that the most-accessed fields have the smallest offsets.

This discipline transfers to every platform you will ever work on. The Spectrum teaches you what "efficient" really means at the instruction level, and that awareness never leaves you. Even on the Agon, where you have cycles to spare, writing tight inner loops is a habit worth keeping.

### The Spectrum Forces You To Be Creative

Attribute clash. Interleaved screen memory. A 6,912-byte framebuffer that looks like it was designed by a committee that never met. These constraints do not exist on the Agon, and their absence removes the creative pressure that produced some of the Spectrum's most distinctive visual techniques.

The multicolour hack, the 4-phase colour trick, attribute-only effects, screen-third flipping for double buffering --- these are solutions to problems that do not exist on the Agon. You will not invent them if you only program the Agon. The Spectrum's constraints are a school of creative problem-solving.

### The Agon Forces You To Think About Architecture

When memory is no longer scarce, when cycles are no longer tight, the remaining challenges are architectural. How do you structure a game loop that communicates with an asynchronous coprocessor? How do you time your VDP commands so that sprites move smoothly? How do you manage the pipeline of data flowing from CPU to VDP over serial?

The Agon teaches you about system design: separating concerns, managing latency, structuring command protocols, and building abstraction layers. These are software engineering skills that the Spectrum, with its "write directly to hardware" ethos, does not emphasize.

### The Agon Forces You To Care About Data

On the Spectrum, a 16x16 sprite is 32 bytes of pixel data plus 32 bytes of mask. On the Agon, the same sprite in 8bpp RGBA is 1,024 bytes. Multiply by 64 sprites across 4 animation frames and you have 256 KB of sprite data alone. Even with 512 KB, you start thinking about asset pipelines: how to convert, optimize, and manage large volumes of graphical data.

The Agon makes you a better *tool builder* --- writing converters, optimizers, asset pipeline scripts. The Spectrum makes you a better *optimizer* of the code itself. Both skills matter.

---

## A Note on eZ80 Instructions

The eZ80 adds several instructions that Z80 programmers will appreciate. The most useful for game development:

**LEA (Load Effective Address).** Compute an address from a base register plus an 8-bit signed displacement, without modifying the base register:

```z80
; eZ80: LEA IX, IY + offset
; Compute IX = IY + displacement without changing IY
    LEA  IX,IY+ENT_SIZE    ; IX points to next entity
```

On the Z80, this requires `PUSH IY` / `POP IX` / `LD DE,ENT_SIZE` / `ADD IX,DE` --- four instructions and 40+ T-states. LEA does it in one instruction.

**TST (Test Immediate).** AND the accumulator with an immediate value and set flags, without modifying A:

```z80
; eZ80: TST A, mask
; Test bits without destroying A
    TST  A,$80             ; test sign bit
    jr   nz,.negative      ; branch if bit 7 set, A unchanged
```

On the Z80, you would need `BIT 7,A` (which does not work with arbitrary masks) or `PUSH AF` / `AND mask` / `POP AF` (expensive).

**MLT (Multiply).** 8x8 unsigned multiply, result in a 16-bit register pair:

```z80
; eZ80: MLT BC
; B * C -> BC (16-bit result)
    ld   b,sprite_width
    ld   c,frame_number
    mlt  bc                ; BC = B * C
```

On the Z80, multiplication requires a loop or a lookup table. MLT is a single instruction. For game logic --- computing sprite offsets, tile map indices, animation frame positions --- this is a substantial simplification.

---

## Summary

- The Agon Light 2 runs the same Z80 instruction set as the Spectrum, but with 24-bit addressing (ADL mode), 512 KB flat RAM, hardware sprites and tilemaps via the VDP coprocessor, and a ~5x larger frame budget.
- **ADL mode** is the native mode. Run your game in ADL mode. Avoid Z80-compatible mode for anything other than running legacy code that cannot be converted. Mode switching via `.LIL`/`.SIS` suffixes is available but adds complexity and risk.
- **Game logic ports directly**: entity systems, collision detection, fixed-point physics, state machines, and AI all transfer with minimal changes (mainly widening pointers from 16-bit to 24-bit).
- **Rendering must be rewritten**: the Spectrum's direct framebuffer access is replaced by VDP command sequences for sprites, tilemaps, and scrolling. CPU rendering cost drops dramatically, but you now manage an asynchronous command pipeline.
- **Sound must be rewritten**: AY register writes are replaced by VDP sound commands. The pattern data can remain the same; only the output driver changes.
- **Memory architecture simplifies**: no banking, no shadow screen tricks, no compression mandated by scarcity. All assets can be resident simultaneously.
- **Spectrum tricks that become irrelevant on Agon**: self-modifying code for speed, stack-pointer rendering, pre-shifted sprite copies for memory/speed trade-offs, interleaved screen address calculations, attribute-based visual effects.
- **Spectrum tricks that still matter on Agon**: tight inner loops, register-efficient code, data-oriented struct layout, precomputed lookup tables.
- **Each platform teaches different skills**: the Spectrum teaches cycle-level efficiency and creative constraint-solving; the Agon teaches system architecture, coprocessor communication, and data pipeline management.
- **The eZ80 adds useful instructions**: LEA for address computation, MLT for hardware multiply, TST for non-destructive bit testing --- all simplifications that eliminate multi-instruction Z80 patterns.

---

> **Sources:** Zilog eZ80 CPU User Manual (UM0077); Agon Light 2 Official Documentation, The Byte Attic; Dean Belfield, "Agon Light --- Programming Guide" (breakintoprogram.co.uk); FabGL Library Documentation (fabgl.com); Agon MOS API Documentation (github.com/AgonConsole8/agon-docs); Chapters 15--21 of this book.
