# Chapter 21: Full Game -- ZX Spectrum 128K

> *"The only way to know if your engine works is to ship a game."*

---

You have sprites (Chapter 16). You have scrolling (Chapter 17). You have a game loop and entity system (Chapter 18). You have collisions, physics, and enemy AI (Chapter 19). You have AY music and sound effects (Chapter 11). You have compression (Chapter 14). You have 128K of banked RAM and know how to address every byte of it (Chapter 15).

Now you must put all of it into a single binary that loads from tape, shows a loading screen, presents a menu, plays five levels of a side-scrolling platformer with four enemy types and a boss, tracks high scores, and fits on a `.tap` file.

This is the integration chapter. No new techniques appear here. Instead, we face the problems that only emerge when every subsystem must coexist: memory contention between graphics banks and code, frame budgets that overflow when scrolling and sprites and music and AI all demand their share, build systems that must coordinate a dozen data conversion steps, and the thousand small decisions about what goes where in 128K of banked memory.

The game we are building is called *Ironclaw* -- a five-level side-scrolling platformer starring a mechanical cat navigating a series of increasingly hostile factory floors. The genre is deliberate: side-scrolling platformers demand every subsystem simultaneously and leave nowhere to hide. If the scrolling stutters, you see it. If the sprite rendering overflows the frame, you feel it. If the collision detection fails, the player falls through the floor. A platformer is the hardest integration test a Z80 game engine can face.

---

## 21.1 Project Architecture

Before writing a single line of Z80, you need a directory structure that scales. A 128K game with five levels, a tileset, sprite sheets, a music score, and sound effects generates dozens of data files. If you do not organise them from the start, you will drown.

### Directory Layout

```
ironclaw/
  src/
    main.a80           -- entry point, bank switching, state machine
    render.a80          -- tile renderer, scroll engine
    sprites.a80         -- sprite drawing routines (OR+AND masked)
    entities.a80        -- entity update, spawning, despawning
    physics.a80         -- gravity, friction, jump, collision response
    collisions.a80      -- AABB and tile collision checks
    ai.a80              -- enemy FSM: patrol, chase, attack, retreat, death
    player.a80          -- player input, state, animation
    hud.a80             -- score, lives, status bar
    menu.a80            -- title screen, options, high scores
    loader.a80          -- loading screen, tape/esxDOS loader
    music_driver.a80    -- PT3 player, interrupt handler
    sfx.a80             -- sound effects engine, channel stealing
    esxdos.a80          -- DivMMC file I/O wrappers
    banks.a80           -- bank switching macros and utilities
    defs.a80            -- constants, memory map, entity structure
  data/
    levels/             -- level tilemaps (compressed)
    tiles/              -- tileset graphics
    sprites/            -- sprite sheets (pre-shifted)
    music/              -- PT3 music files
    sfx/                -- SFX definition tables
    screens/            -- loading screen, title screen
  tools/
    png2tiles.py        -- PNG tileset converter
    png2sprites.py      -- PNG sprite sheet converter (generates shifts)
    map2bin.py          -- Tiled JSON/TMX to binary tilemap
    compress.py         -- wrapper around ZX0/Pletter compression
  build/                -- compiled output (gitignored)
  Makefile              -- the build system
```

Every source file focuses on one subsystem. Every data file passes through a conversion pipeline before it reaches the assembler. The `tools/` directory holds Python scripts that convert artist-friendly formats (PNG images, Tiled editor maps) into assembler-ready binary data.

### The Build System

The Makefile is the spine of the project. It must:

1. Convert all graphics from PNG to binary tile/sprite data
2. Convert level maps from Tiled format to binary tilemaps
3. Compress level data, graphics banks, and music with the appropriate compressor
4. Assemble all source files into a single binary
5. Generate the final `.tap` file with the correct loader

```makefile
# Ironclaw Makefile
ASM       = sjasmplus
COMPRESS  = zx0
PYTHON    = python3

# Data conversion
data/tiles/tileset.bin: data/tiles/tileset.png
	$(PYTHON) tools/png2tiles.py $< $@

data/sprites/player.bin: data/sprites/player.png
	$(PYTHON) tools/png2sprites.py --shifts 4 $< $@

data/levels/level%.bin: data/levels/level%.tmx
	$(PYTHON) tools/map2bin.py $< $@

# Compression (ZX0 for level data -- good ratio, small decompressor)
data/levels/level%.bin.zx0: data/levels/level%.bin
	$(COMPRESS) $< $@

# Compression (Pletter for graphics -- faster decompression)
data/tiles/tileset.bin.plt: data/tiles/tileset.bin
	pletter5 $< $@

# Assembly
build/ironclaw.tap: src/*.a80 data/levels/*.zx0 data/tiles/*.plt \
                    data/sprites/*.bin data/music/*.pt3
	$(ASM) --fullpath src/main.a80 --raw=build/ironclaw.tap

.PHONY: clean
clean:
	rm -rf build/ data/**/*.bin data/**/*.zx0 data/**/*.plt
```

The key insight is the data pipeline. The artist exports a PNG tileset from Aseprite. The `png2tiles.py` script slices it into 8x8 or 16x16 tiles, converts each to the Spectrum's interleaved pixel format, and writes a binary blob. The level designer exports a Tiled `.tmx` map. The `map2bin.py` script extracts the tile indices and writes a compact binary tilemap. The compressor squeezes each blob. Only then does the assembler `INCBIN` the result into the appropriate memory bank.

This pipeline means the game's content is always in editable form (PNG, TMX), and the build system handles every conversion automatically. Change a tile in the PNG, type `make`, and the new tile appears in the game.

---

## 21.2 Memory Map: 128K Bank Assignments

The ZX Spectrum 128K has eight 16KB RAM banks, numbered 0 through 7. At any moment, the CPU sees a 64KB address space:

```
$0000-$3FFF   ROM (16KB) -- BASIC or 128K editor ROM
$4000-$7FFF   Bank 5 (always) -- screen memory (normal screen)
$8000-$BFFF   Bank 2 (always) -- typically code
$C000-$FFFF   Switchable -- banks 0-7, selected via port $7FFD
```

Banks 5 and 2 are hardwired to `$4000` and `$8000` respectively. Only the top 16KB window (`$C000-$FFFF`) is switchable. The bank selection register at port `$7FFD` also controls which screen is displayed (bank 5 or bank 7) and which ROM page is active.

```z80
; Port $7FFD layout:
;   Bit 0-2:  Bank number for $C000-$FFFF (0-7)
;   Bit 3:    Screen select (0 = bank 5 normal, 1 = bank 7 shadow)
;   Bit 4:    ROM select (0 = 128K editor, 1 = 48K BASIC)
;   Bit 5:    Disable paging (PERMANENT -- cannot be undone without reset)
;   Bits 6-7: Unused

; Switch to bank N at $C000
; Input: A = bank number (0-7)
; Preserves: all registers except A
switch_bank:
    or   %00010000          ; ROM 1 (48K BASIC) -- keep this set
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a
    ret

last_bank_state:
    db   %00010000          ; default: bank 0, normal screen, ROM 1
```

The critical rule: **always store your last write to `$7FFD`** in a shadow variable. Port `$7FFD` is write-only -- you cannot read back the current state. If you need to change one bit (say, switch the screen) without disturbing the bank selection, you must read your shadow variable, modify the bit, write the result to both the port and the shadow.

### Ironclaw Bank Allocation

Here is how Ironclaw distributes its 128KB across the eight banks:

```
Bank 0 ($C000)  -- Level data: tilemaps for levels 1-2 (compressed)
                   Tileset graphics (compressed)
                   Decompression buffer

Bank 1 ($C000)  -- Level data: tilemaps for levels 3-5 (compressed)
                   Boss level data and patterns
                   Enemy spawn tables

Bank 2 ($8000)  -- FIXED: Main game code
                   Player logic, physics, collisions
                   Sprite routines, entity system
                   State machine, HUD
                   ~ 14KB code, 2KB tables/buffers

Bank 3 ($C000)  -- Sprite graphics (pre-shifted x4)
                   Player: 6 frames x 4 shifts = 24 variants
                   Enemies: 4 types x 4 frames x 4 shifts = 64 variants
                   Projectiles, particles, pickups
                   ~ 12KB total

Bank 4 ($C000)  -- Music: PT3 song data (title, levels 1-3)
                   PT3 player code (resident copy)

Bank 5 ($4000)  -- FIXED: Normal screen
                   Pixel data $4000-$57FF (6,144 bytes)
                   Attributes $5800-$5AFF (768 bytes)
                   Remaining ~9KB: interrupt handler, screen buffers

Bank 6 ($C000)  -- Music: PT3 song data (levels 4-5, boss, game over)
                   SFX definition tables
                   SFX engine code

Bank 7 ($4000)  -- Shadow screen (used for double buffering)
                   Also usable as 16KB data storage when
                   not actively double-buffering
```

<!-- figure: ch21_128k_bank_allocation -->
```
         ZX Spectrum 128K — Ironclaw Bank Allocation
         ═══════════════════════════════════════════

$0000 ┌─────────────────────────────┐
      │         ROM (16 KB)         │  BASIC / 128K editor
$4000 ├─────────────────────────────┤
      │    Bank 5 — FIXED           │  Screen pixels ($4000–$57FF)
      │    Normal screen            │  Attributes ($5800–$5AFF)
      │    + IM2 handler, buffers   │  ~9 KB free for interrupt code
$8000 ├─────────────────────────────┤
      │    Bank 2 — FIXED           │  Main game code (~14 KB)
      │    Player, physics, AI      │  Tables, buffers (~2 KB)
      │    Sprites, entities, HUD   │  Stack grows down from $BFFF
$C000 ├─────────────────────────────┤
      │    Switchable bank (0–7)    │  Selected via port $7FFD
      │    ┌───────────────────┐    │
      │    │ Bank 0: Levels 1–2│    │  Compressed tilemaps + tileset
      │    │ Bank 1: Levels 3–5│    │  Boss data, enemy spawns
      │    │ Bank 3: Sprites   │    │  Pre-shifted ×4 (24+64 variants)
      │    │ Bank 4: Music A   │    │  PT3: title, levels 1–3
      │    │ Bank 6: Music B   │    │  PT3: levels 4–5, boss; SFX
      │    │ Bank 7: Shadow scr│    │  Double buffer / data storage
      │    └───────────────────┘    │
$FFFF └─────────────────────────────┘

  Key: Banks 2 and 5 are always visible (hardwired).
       Only $C000–$FFFF is switchable.
       Port $7FFD is write-only — always shadow its state!
```

Several things to notice about this layout:

**Code lives in bank 2 (fixed).** Because bank 2 is always mapped at `$8000-$BFFF`, your main game code is always accessible. You never need to page in code -- only data. This eliminates the most dangerous class of banking bug: calling a routine that has been paged out.

**Sprite graphics in bank 3, separate from level data in banks 0-1.** When rendering a frame, the renderer needs both tile graphics (for the scrolling background) and sprite graphics (for entities). If both were in the same switchable bank, you would need to page back and forth mid-render. By placing them in separate banks, you can page in the tile data, render the background, then page in the sprite data and render all entities, with only two bank switches per frame.

**Music is split across banks 4 and 6.** The PT3 player runs during the interrupt handler, which fires once per frame. The interrupt handler must page in the music bank, update the AY registers, and page back to whatever bank the main loop was using. Splitting music across two banks means the interrupt handler must know which bank contains the current song. We handle this with a variable:

```z80
current_music_bank:
    db   4              ; bank 4 by default

im2_handler:
    push af
    push bc
    push de
    push hl
    push ix

    ; Save current bank state
    ld   a, (last_bank_state)
    push af

    ; Page in music bank
    ld   a, (current_music_bank)
    call switch_bank

    ; Update PT3 player -- writes AY registers
    call pt3_play

    ; Check for pending SFX
    call sfx_update

    ; Restore previous bank
    pop  af
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a

    pop  ix
    pop  hl
    pop  de
    pop  bc
    pop  af
    ei
    reti
```

**The shadow screen in bank 7** is available for double-buffering during scroll updates (as described in Chapter 17). When you are not actively double-buffering -- during the menu, between levels, during cutscenes -- bank 7 is 16KB of free storage. Ironclaw uses it to hold the decompressed tilemap of the current level during gameplay, freeing the switchable banks for graphics and music.

### The Stack

The stack lives at the top of bank 2's address space, growing downward from `$BFFF`. With ~14KB of code starting at `$8000`, the stack has approximately 2KB of room -- more than enough for normal call depth, but you must be vigilant. Deep recursion is not an option. If you are using stack-based sprite output (Chapter 16's PUSH method), remember that you are borrowing the stack pointer and must save and restore it with interrupts disabled.

---

## 21.3 The State Machine

A game is not one program. It is a sequence of modes -- title screen, menu, gameplay, pause, game over, high scores -- each with different input handling, different rendering, and different update logic. Chapter 18 introduced the state machine pattern. Here is how Ironclaw implements it at the top level.

```z80
; Game states
STATE_LOADER    equ  0
STATE_TITLE     equ  1
STATE_MENU      equ  2
STATE_GAMEPLAY  equ  3
STATE_PAUSE     equ  4
STATE_GAMEOVER  equ  5
STATE_HISCORE   equ  6
STATE_LEVELWIN  equ  7

; State handler table -- each entry is a 2-byte address
state_table:
    dw   state_loader       ; 0: loading screen + init
    dw   state_title        ; 1: title screen with animation
    dw   state_menu         ; 2: main menu (start, options, hiscores)
    dw   state_gameplay     ; 3: in-game
    dw   state_pause        ; 4: paused
    dw   state_gameover     ; 5: game over sequence
    dw   state_hiscore      ; 6: high score entry
    dw   state_levelwin     ; 7: level complete, advance

current_state:
    db   STATE_LOADER

; Main loop -- called once per frame after HALT
main_loop:
    halt                    ; wait for frame interrupt

    ; Dispatch to current state handler
    ld   a, (current_state)
    add  a, a              ; x2 for word index
    ld   l, a
    ld   h, 0
    ld   de, state_table
    add  hl, de
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = handler address
    jp   (hl)              ; jump to handler

; Each handler ends with:  jp main_loop
```

Each state handler owns the frame completely. The gameplay handler runs input, physics, AI, rendering, and HUD updates. The menu handler reads input and draws the menu. The pause handler simply waits for the unpause key, displaying a "PAUSED" overlay.

State transitions happen by writing a new value to `current_state`. The transition from `STATE_GAMEPLAY` to `STATE_PAUSE` requires no cleanup -- the game state is untouched, and returning to `STATE_GAMEPLAY` resumes exactly where you left off. But the transition from `STATE_GAMEOVER` to `STATE_HISCORE` requires checking whether the player's score qualifies, and the transition from `STATE_LEVELWIN` to `STATE_GAMEPLAY` requires loading and decompressing the next level's data.

---

## 21.4 The Gameplay Frame

This is where integration happens. During `STATE_GAMEPLAY`, every frame must execute the following, in order:

```
1. Read input                ~200 T-states
2. Update player physics     ~800 T-states
3. Update player state       ~400 T-states
4. Update enemies (AI+phys)  ~4,000 T-states (8 enemies)
5. Check collisions          ~2,000 T-states
6. Update projectiles        ~500 T-states
7. Scroll the viewport       ~8,000-15,000 T-states (depends on method)
8. Render background tiles   ~12,000 T-states (exposed column/row)
9. Erase old sprites         ~3,000 T-states (background restore)
10. Draw sprites             ~8,000 T-states (8 entities x ~1,000 each)
11. Update HUD               ~1,500 T-states
12. [Music plays in IM2]     ~3,000 T-states (interrupt handler)
                             ─────────────
                    Total:   ~43,400-50,400 T-states
```

On a Pentagon with 71,680 T-states per frame, that leaves 21,000-28,000 T-states of slack. That sounds comfortable, but it is deceptive. Those estimates are averages. When four enemies are on screen and the player is jumping across a gap with projectiles flying, the worst case can spike 20-30% above the average. Your slack is your safety margin.

The order matters. Input must come first -- you need the player's intent before simulating physics. Physics must precede collision detection -- you need to know where entities want to move before checking whether they can. Collision response must precede rendering -- you need final positions before drawing anything. And sprites must be drawn after the background, because sprites overlay the tiles.

### Reading Input

```z80
; Read keyboard and Kempston joystick
; Returns result in A: bit 0=right, 1=left, 2=down, 3=up, 4=fire
read_input:
    ld   d, 0              ; accumulate result

    ; Kempston joystick (active high)
    in   a, ($1F)          ; Kempston port
    and  %00011111         ; mask 5 bits: fire, up, down, left, right
    ld   d, a

    ; Keyboard: QAOP + space (merge with joystick)
    ; Q = up
    ld   bc, $FBFE         ; half-row Q-T
    in   a, (c)
    bit  0, a              ; Q key
    jr   nz, .not_q
    set  3, d              ; up
.not_q:
    ; O = left
    ld   b, $DF            ; half-row Y-P
    in   a, (c)
    bit  1, a              ; O key
    jr   nz, .not_o
    set  1, d              ; left
.not_o:
    ; P = right
    bit  0, a              ; P key (same half-row)
    jr   nz, .not_p
    set  0, d              ; right
.not_p:
    ; A = down
    ld   b, $FD            ; half-row A-G
    in   a, (c)
    bit  0, a              ; A key
    jr   nz, .not_a
    set  2, d              ; down
.not_a:
    ; Space = fire
    ld   b, $7F            ; half-row space-B
    in   a, (c)
    bit  0, a              ; space
    jr   nz, .not_fire
    set  4, d              ; fire
.not_fire:

    ld   a, d
    ld   (input_state), a
    ret
```

Note that keyboard reads use `IN A,(C)` with the half-row address in B. Each key maps to a bit in the result byte. Merging keyboard and joystick into a single byte means the rest of the game logic does not care which input device the player uses.

### The Scroll Engine

Scrolling is the most expensive operation in the frame. Chapter 17 covered the techniques in detail; here is how they integrate into the game.

Ironclaw uses the **combined scroll** method: character-granularity scrolling (8-pixel jumps) for the main viewport, with a pixel offset (0-7) within the current 8-pixel window for smooth visual movement. When the pixel offset reaches 8, the viewport shifts by one tile column and the offset resets to 0.

The viewport is 30 characters wide (240 pixels) and 20 characters tall (160 pixels), leaving room for a 2-character HUD at the top and bottom. The level tilemap is typically 256-512 tiles wide and 20 tiles tall.

When the viewport shifts by one tile column, the renderer must:

1. Copy 29 columns of the current screen one character left (or right)
2. Draw the newly exposed column of tiles from the tilemap

The column copy is an LDIR chain: 20 rows x 8 pixel lines x 29 bytes = 4,640 bytes at 21 T-states each = 97,440 T-states. That is more than an entire frame. This is why Chapter 17's shadow screen technique is essential.

```z80
; Shadow screen double-buffer scroll
; Frame N: display screen is bank 5, draw screen is bank 7
; 1. Draw the shifted background into bank 7
; 2. Flip: set bit 3 of $7FFD to display bank 7
; Frame N+1: display screen is bank 7, draw screen is bank 5
; 3. Draw the shifted background into bank 5
; 4. Flip: clear bit 3 of $7FFD to display bank 5

flip_screen:
    ld   a, (last_bank_state)
    xor  %00001000          ; toggle screen bit (bit 3)
    ld   (last_bank_state), a
    ld   bc, $7FFD
    out  (c), a
    ret
```

But even with double-buffering, the full column copy is expensive. Ironclaw optimises this by spreading the work: during smooth sub-tile scrolling (pixel offset 1-7), there is no column copy -- only the offset changes. The expensive column copy happens only on tile boundaries, roughly every 4-8 frames depending on the player's speed. Between those spikes, scroll rendering is nearly free.

When a tile boundary is crossed, the column copy can be spread across two frames using the double buffer: Frame N draws the top half of the shifted screen into the back buffer, Frame N+1 draws the bottom half and flips. The player sees a seamless scroll because the flip only happens when the back buffer is complete.

---

## 21.5 Sprite Integration

Ironclaw uses OR+AND masked sprites (Chapter 16, method 2) for all game entities. This is the standard technique: for each sprite pixel, AND with a mask byte to clear the background, then OR with the sprite data to set the pixels.

Each 16x16 sprite has four pre-shifted copies (Chapter 16, method 3), one for each 2-pixel horizontal alignment. This reduces per-pixel shifting from a runtime operation to a table lookup. The cost: each sprite frame requires 4 variants x 16 lines x 3 bytes/line (2 bytes data + 1 byte mask, widened to 3 bytes to handle shift overflow) = 192 bytes. But the rendering speed drops from ~1,500 T-states to ~1,000 T-states per sprite, and with 8-10 sprites on screen, that savings adds up.

Pre-shifted sprite data lives in bank 3. During the sprite rendering phase, the renderer pages in bank 3, iterates through all active entities, and draws each one:

```z80
; Draw all active entities
; Assumes bank 3 (sprite graphics) is paged in at $C000
render_entities:
    ld   ix, entity_array
    ld   b, MAX_ENTITIES

.loop:
    push bc

    ; Check if entity is active
    ld   a, (ix + ENT_FLAGS)
    bit  FLAG_ACTIVE, a
    jr   z, .skip

    ; Calculate screen position from world position and viewport
    ld   l, (ix + ENT_X)
    ld   h, (ix + ENT_X + 1)
    ld   de, (viewport_x)
    or   a                 ; clear carry
    sbc  hl, de            ; screen_x = world_x - viewport_x
    ; Check if on screen (0-239)
    bit  7, h
    jr   nz, .skip         ; off-screen left (negative)
    ld   a, h
    or   a
    jr   nz, .skip         ; off-screen right (> 255)
    ld   a, l
    cp   240
    jr   nc, .skip         ; off-screen right (240-255)

    ; Store screen X for sprite routine
    ld   (sprite_screen_x), a

    ; Y position (already in screen coordinates for simplicity)
    ld   a, (ix + ENT_Y)
    ld   (sprite_screen_y), a

    ; Look up sprite graphic address from type + frame + shift
    call get_sprite_address ; returns HL = address in bank 3

    ; Draw masked sprite at (sprite_screen_x, sprite_screen_y)
    call draw_sprite_masked

.skip:
    pop  bc
    ld   de, ENT_SIZE
    add  ix, de            ; next entity
    djnz .loop
    ret
```

### Background Restore (Dirty Rectangles)

Before drawing sprites at their new positions, you must erase them from their old positions. Ironclaw uses the dirty rectangle method from Chapter 16: before drawing a sprite, save the background beneath it to a buffer. Before the next frame's sprite rendering pass, restore those saved backgrounds.

```z80
; Dirty rectangle entry: 4 bytes
;   byte 0: screen address low
;   byte 1: screen address high
;   byte 2: width in bytes
;   byte 3: height in pixel lines

; Save background before drawing sprite
save_background:
    ; HL = screen address, B = height, C = width
    ld   de, bg_save_buffer
    ld   (bg_save_ptr), de
    ; ... copy rectangle from screen to buffer ...
    ret

; Restore all saved backgrounds (called before new sprite render pass)
restore_backgrounds:
    ld   hl, dirty_rect_list
    ld   b, (hl)           ; count of dirty rectangles
    inc  hl
    or   a
    ret  z                 ; no sprites last frame

.loop:
    push bc
    ; Read rectangle descriptor
    ld   e, (hl)
    inc  hl
    ld   d, (hl)           ; DE = screen address
    inc  hl
    ld   b, (hl)           ; B = height
    inc  hl
    ld   c, (hl)           ; C = width
    inc  hl
    push hl

    ; Copy saved background back to screen
    ; ... copy from bg_save_buffer to screen ...

    pop  hl
    pop  bc
    djnz .loop
    ret
```

The cost of dirty rectangles is proportional to the number and size of sprites. For 8 entities of 16x16 pixels (3 bytes wide after shift), saving and restoring costs roughly 8 x 16 x 3 x 2 (save + restore) x ~10 T-states/byte = ~7,680 T-states. Not cheap, but predictable.

---

## 21.6 Collisions, Physics, and AI in Context

Chapters 18 and 19 covered these systems in isolation. In the integrated game, the key challenge is ordering: which system runs first, and what data does each need from the others?

### Physics-Collision Loop

The physics update must interleave with collision detection. The pattern is:

```
1. Apply gravity:  velocity_y += GRAVITY
2. Apply input:    if (input_right) velocity_x += ACCEL
3. Horizontal move:
     a. new_x = x + velocity_x
     b. Check tile collisions at (new_x, y)
     c. If blocked: push back to tile boundary, velocity_x = 0
     d. Else: x = new_x
4. Vertical move:
     a. new_y = y + velocity_y
     b. Check tile collisions at (x, new_y)
     c. If blocked: push back, velocity_y = 0, set on_ground flag
     d. Else: y = new_y, clear on_ground flag
5. If (on_ground AND input_jump): velocity_y = -JUMP_FORCE
```

The horizontal and vertical moves are separate because collision response must handle each axis independently. If you move diagonally and hit a corner, you want to slide along the wall on one axis while stopping on the other. Checking both axes simultaneously leads to "sticking" bugs where the player gets trapped on corners.

All positions use 8.8 fixed-point format (Chapter 4): the high byte is the pixel coordinate, the low byte is the fractional part. Velocity values are also 8.8. This gives sub-pixel movement precision without requiring any multiplication in the core physics loop -- addition and shifting are sufficient.

```z80
; Apply gravity to entity at IX
; velocity_y is 16-bit signed, 8.8 fixed-point
apply_gravity:
    ld   l, (ix + ENT_VY)
    ld   h, (ix + ENT_VY + 1)
    ld   de, GRAVITY       ; e.g., $0040 = 0.25 pixels/frame/frame
    add  hl, de
    ; Clamp to terminal velocity
    ld   a, h
    cp   MAX_FALL_SPEED    ; e.g., 4 pixels/frame
    jr   c, .no_clamp
    ld   hl, MAX_FALL_SPEED * 256
.no_clamp:
    ld   (ix + ENT_VY), l
    ld   (ix + ENT_VY + 1), h
    ret
```

### Tile Collision

The tile collision check converts a pixel coordinate to a tile index, then looks up the tile type in the level's collision map:

```z80
; Check tile at pixel position (B=x, C=y)
; Returns: A = tile type (0=empty, 1=solid, 2=hazard, 3=platform)
check_tile:
    ; Convert pixel X to tile column: x / 8
    ld   a, b
    srl  a
    srl  a
    srl  a                 ; A = column (0-31)
    ld   l, a

    ; Convert pixel Y to tile row: y / 8
    ld   a, c
    srl  a
    srl  a
    srl  a                 ; A = row (0-23)

    ; Tile index = row * level_width + column
    ld   h, 0
    ld   d, h
    ld   e, a
    ; Multiply row by level_width (e.g., 256 = trivial: just use E as high byte)
    ; For level_width = 256: address = level_map + row * 256 + column
    ld   d, e              ; D = row = high byte of offset
    ld   e, l              ; E = column = low byte of offset
    ld   hl, level_collision_map
    add  hl, de
    ld   a, (hl)           ; A = tile type
    ret
```

For Ironclaw, level widths are set to 256 tiles. This is not a coincidence -- it makes the row multiplication trivial (the row number becomes the high byte of the offset). A 256-tile-wide level at 8 pixels per tile is 2,048 pixels, roughly 8.5 screens wide. For longer levels, you can use 512-tile width (multiply row by 2 via `SLA E : RL D`), though this costs a few extra T-states per lookup.

### Enemy AI

Each enemy type has a finite state machine (Chapter 19). The state is stored in the entity structure:

```z80
; Entity structure (16 bytes per entity)
ENT_X       equ  0    ; 16-bit, 8.8 fixed-point
ENT_Y       equ  2    ; 16-bit, 8.8 fixed-point
ENT_VX      equ  4    ; 16-bit, 8.8 fixed-point
ENT_VY      equ  6    ; 16-bit, 8.8 fixed-point
ENT_TYPE    equ  8    ; entity type (player, walker, flyer, shooter, boss)
ENT_STATE   equ  9    ; FSM state (idle, patrol, chase, attack, retreat, dying)
ENT_ANIM    equ  10   ; animation frame counter
ENT_HEALTH  equ  11   ; hit points
ENT_FLAGS   equ  12   ; bit flags: active, on_ground, facing_left, invuln, ...
ENT_TIMER   equ  13   ; general-purpose timer (attack cooldown, etc.)
ENT_AUX1    equ  14   ; type-specific data (patrol point, projectile type, etc.)
ENT_AUX2    equ  15   ; type-specific data
ENT_SIZE    equ  16

MAX_ENTITIES equ 16   ; player + 8 enemies + 7 projectiles
```

Ironclaw's four enemy types:

1. **Walker** -- Patrols between two points. When the player is within 64 pixels horizontally, switches to Chase state (walks toward player). Switches to Attack (contact damage) on collision. Returns to Patrol when player moves away or the enemy reaches a ledge.

2. **Flyer** -- Sine-wave vertical movement (using the sine table from Chapter 4). Ignores tile collisions. Chases the player horizontally when within range. Drops projectiles at intervals.

3. **Shooter** -- Stationary. Fires a horizontal projectile every N frames when the player is within line-of-sight (same tile row, no solid tiles between). The projectile is a separate entity allocated from the entity pool.

4. **Boss** -- Multi-phase FSM. Phase 1: patrol platform, fire spread shots. Phase 2 (below 50% health): faster movement, targeted shots, summons walkers. Phase 3 (below 25% health): enrage, continuous fire, screen shake.

The key optimisation from Chapter 19: AI does not run every frame. Enemy AI updates are distributed across frames using a simple round-robin:

```z80
; Update AI for subset of enemies each frame
; ai_frame_counter cycles 0, 1, 2, 0, 1, 2, ...
update_enemy_ai:
    ld   a, (ai_frame_counter)
    inc  a
    cp   3
    jr   c, .no_wrap
    xor  a
.no_wrap:
    ld   (ai_frame_counter), a

    ; Only update enemies where (entity_index % 3) == ai_frame_counter
    ld   ix, entity_array + ENT_SIZE  ; skip player (index 0)
    ld   b, MAX_ENTITIES - 1
    ld   c, 0              ; entity index counter

.loop:
    push bc
    ld   a, (ix + ENT_FLAGS)
    bit  FLAG_ACTIVE, a
    jr   z, .next

    ; Check if this entity's turn
    ld   a, c
    ld   e, 3
    call mod_a_e           ; A = entity_index % 3
    ld   b, a
    ld   a, (ai_frame_counter)
    cp   b
    jr   nz, .next

    ; Run AI for this entity
    call run_entity_ai     ; dispatch based on ENT_TYPE and ENT_STATE

.next:
    pop  bc
    inc  c
    ld   de, ENT_SIZE
    add  ix, de
    djnz .loop
    ret
```

This means each enemy's AI runs once every 3 frames. At 50 fps, that is still ~17 AI updates per second per enemy -- more than enough for responsive behaviour. The saving is significant: if AI costs ~500 T-states per enemy, running all 8 enemies every frame costs 4,000 T-states. Running 2-3 enemies per frame costs 1,000-1,500 T-states. Physics and collision detection still run every frame for smooth movement.

---

## 21.7 Sound Integration

### Music

The PT3 player runs inside the IM2 interrupt handler, as shown in section 21.2. The player occupies approximately 1.5-2KB of code and executes once per frame, taking ~2,500-3,500 T-states depending on the complexity of the current pattern row.

Each level has its own music track. When transitioning between levels, the game:

1. Fades out the current track (ramp AY volumes to 0 over 25 frames)
2. Pages in the appropriate music bank (bank 4 or 6)
3. Initialises the PT3 player with the new song's start address
4. Fades in

The PT3 data format is compact -- a typical 2-3 minute game music loop compresses to 2-4KB with Pletter, which is why two music banks (4 and 6) can hold all six tracks (title, five levels, boss, game over).

### Sound Effects

Sound effects use the priority-based channel stealing system from Chapter 11. When a sound effect triggers (player jumps, enemy dies, projectile fires), the SFX engine temporarily hijacks one AY channel, overriding whatever the music was doing on that channel. When the effect finishes, the channel returns to music control.

```z80
; SFX priority levels
SFX_JUMP       equ  1     ; low priority
SFX_PICKUP     equ  2
SFX_SHOOT      equ  3
SFX_HIT        equ  4
SFX_EXPLODE    equ  5     ; high priority
SFX_BOSS_DIE   equ  6     ; highest priority

; Trigger a sound effect
; A = SFX id
play_sfx:
    ; Check priority -- only play if higher than current SFX
    ld   hl, current_sfx_priority
    cp   (hl)
    ret  c                 ; current SFX has higher priority, ignore

    ; Set up SFX playback
    ld   (hl), a           ; update priority
    ; Look up SFX descriptor table
    add  a, a              ; x2 for word index
    ld   l, a
    ld   h, 0
    ld   de, sfx_table
    add  hl, de
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = SFX descriptor address

    ; SFX descriptor: duration (byte), channel (byte),
    ;                 then per-frame: freq_lo, freq_hi, volume, noise
    ld   a, (hl)
    ld   (sfx_frames_left), a
    inc  hl
    ld   a, (hl)
    ld   (sfx_channel), a
    inc  hl
    ld   (sfx_data_ptr), hl
    ret
```

The SFX update runs inside the interrupt handler, after the PT3 player. If an SFX is active, it overwrites the AY register values that the PT3 player just set for the stolen channel. This means the music continues to play correctly on the other two channels, and the stolen channel produces the sound effect.

SFX definitions are procedural tables rather than sampled audio. Each entry is a sequence of per-frame register values:

```z80
; SFX: player jump -- ascending frequency sweep on channel C
sfx_jump_data:
    db   8                 ; duration: 8 frames
    db   2                 ; channel C (0=A, 1=B, 2=C)
    ; Per-frame: freq_lo, freq_hi, volume
    db   $80, $01, 15      ; frame 1: low pitch, full volume
    db   $60, $01, 14      ; frame 2: slightly higher
    db   $40, $01, 13
    db   $20, $01, 12
    db   $00, $01, 10
    db   $E0, $00, 8
    db   $C0, $00, 5
    db   $A0, $00, 2       ; frame 8: high pitch, fading out
```

This approach uses negligible memory (8-20 bytes per effect) and negligible CPU time (a few dozen T-states per frame to write 3-4 AY register values).

---

## 21.8 Loading: Tape and DivMMC

A ZX Spectrum game must load somehow. In the 1980s, that meant tape. Today, most users have a DivMMC (or similar) SD card interface running esxDOS. Ironclaw supports both.

### The .tap File and BASIC Loader

The `.tap` file format is a sequence of data blocks, each preceded by a 2-byte length and a flag byte. A BASIC loader program (itself a block in the .tap) uses `LOAD "" CODE` commands to load each block to the correct address.

Ironclaw's .tap structure:

```
Block 0:  BASIC loader program (autorun line 10)
Block 1:  Loading screen (6912 bytes -> $4000)
Block 2:  Main code block (bank 2 content -> $8000)
Block 3:  Bank 0 data (level data + tiles, compressed)
Block 4:  Bank 1 data (more level data)
Block 5:  Bank 3 data (sprite graphics)
Block 6:  Bank 4 data (music tracks 1-3)
Block 7:  Bank 6 data (music tracks 4-6, SFX)
```

The BASIC loader:

```basic
10 CLEAR 32767
20 LOAD "" SCREEN$
30 LOAD "" CODE
40 BORDER 0: PAPER 0: INK 0: CLS
50 RANDOMIZE USR 32768
```

Line 10 sets RAMTOP below `$8000`, protecting our code from BASIC's stack. Line 20 loads the loading screen directly into screen memory (the Spectrum's `LOAD "" SCREEN$` does this automatically). Line 30 loads the main code block. Line 40 clears the screen. Line 50 jumps to our code at `$8000`.

But this only loads the main code block. The banked data (blocks 3-7) must be loaded by our own Z80 code, which pages in each bank and uses the ROM's tape loading routine:

```z80
; Load bank data from tape
; Called after main code is running
load_bank_data:
    ; Bank 0
    ld   a, 0
    call switch_bank
    ld   ix, $C000         ; load address
    ld   de, BANK0_SIZE    ; data length
    call load_tape_block

    ; Bank 1
    ld   a, 1
    call switch_bank
    ld   ix, $C000
    ld   de, BANK1_SIZE
    call load_tape_block

    ; ... repeat for banks 3, 4, 6 ...
    ret

; Load one tape block using ROM routine
; IX = address, DE = length
load_tape_block:
    ld   a, $FF            ; data block flag (not header)
    scf                    ; carry set = LOAD (not VERIFY)
    call $0556             ; ROM tape loading routine
    ret  nc                ; carry clear = load error
    ret
```

### esxDOS Loading (DivMMC)

For users with a DivMMC or similar hardware, loading from an SD card is dramatically faster and more reliable. The esxDOS API provides file operations through `RST $08` followed by a function number:

```z80
; esxDOS function codes
F_OPEN      equ  $9A
F_CLOSE     equ  $9B
F_READ      equ  $9D
F_WRITE     equ  $9E
F_SEEK      equ  $9F
F_OPENDIR   equ  $A3
F_READDIR   equ  $A4

; esxDOS open modes
FA_READ     equ  $01
FA_WRITE    equ  $06
FA_CREATE   equ  $0E

; Open a file
; IX = pointer to null-terminated filename
; Returns: A = file handle (or carry set on error)
esx_open:
    ld   a, '*'            ; use default drive
    ld   b, FA_READ        ; open for reading
    rst  $08
    db   F_OPEN
    ret

; Read bytes from file
; A = file handle, IX = destination address, BC = byte count
; Returns: BC = bytes actually read (or carry set on error)
esx_read:
    rst  $08
    db   F_READ
    ret

; Close a file
; A = file handle
esx_close:
    rst  $08
    db   F_CLOSE
    ret
```

Ironclaw detects whether esxDOS is present at startup by checking for the DivMMC signature. If present, it loads all data from files on the SD card instead of tape:

```z80
; Load game data from esxDOS
; All bank data stored in separate files on SD card
load_from_esxdos:
    ; Load bank 0: levels + tiles
    ld   a, 0
    call switch_bank
    ld   ix, filename_bank0
    call esx_open
    ret  c                 ; error -- fall back to tape
    push af                ; save file handle
    ld   ix, $C000
    ld   bc, BANK0_SIZE
    pop  af                ; A = file handle (esxDOS preserves this)
    push af
    call esx_read
    pop  af
    call esx_close

    ; Repeat for other banks...
    ; Bank 1
    ld   a, 1
    call switch_bank
    ld   ix, filename_bank1
    call esx_open
    ret  c
    ; ... (same pattern) ...

    ret

filename_bank0:  db "IRONCLAW.B0", 0
filename_bank1:  db "IRONCLAW.B1", 0
filename_bank3:  db "IRONCLAW.B3", 0
filename_bank4:  db "IRONCLAW.B4", 0
filename_bank6:  db "IRONCLAW.B6", 0
```

The detection code:

```z80
; Detect esxDOS presence
; Sets carry if esxDOS is NOT available
detect_esxdos:
    ; Try to open a nonexistent file -- if RST $08 returns
    ; without crashing, esxDOS is present
    ld   a, '*'
    ld   b, FA_READ
    ld   ix, test_filename
    rst  $08
    db   F_OPEN
    jr   c, .not_present   ; carry set = open failed, but esxDOS handled it
    ; File actually opened -- close it and return success
    call esx_close
    or   a                 ; clear carry
    ret
.not_present:
    ; esxDOS returned an error -- it IS present, just file not found
    ; Distinguish from "RST $08 went to ROM and crashed"
    ; by checking if we're still running. If we're here, esxDOS is present.
    or   a                 ; clear carry = esxDOS present
    ret

test_filename:  db "IRONCLAW.B0", 0
```

In practice, the safest detection method checks for the DivMMC's identification byte at a known trap address, or uses a known-safe RST $08 call. The method above works because if esxDOS is not present, `RST $08` jumps to the ROM's error handler, which for the 128K ROM at address `$0008` is a benign return that leaves carry clear. Production code should use a more robust check; the pattern above illustrates the concept.

---

## 21.9 Loading Screen, Menu, and High Scores

### Loading Screen

The loading screen is the player's first impression. It loads as `LOAD "" SCREEN$` in the BASIC loader, meaning it appears while the remaining data blocks are loading from tape. On esxDOS, the loading is fast enough that you may want to display the screen for a minimum duration:

```z80
show_loading_screen:
    ; Loading screen is already in screen memory ($4000) from BASIC loader
    ; If loading from esxDOS, load it explicitly:
    ld   ix, filename_screen
    call esx_open
    ret  c
    push af
    ld   ix, $4000
    ld   bc, 6912
    pop  af
    push af
    call esx_read
    pop  af
    call esx_close

    ; Minimum display time: 100 frames (2 seconds)
    ld   b, 100
.wait:
    halt
    djnz .wait
    ret

filename_screen: db "IRONCLAW.SCR", 0
```

The loading screen itself is a standard Spectrum screen file: 6,144 bytes of pixel data followed by 768 bytes of attributes, totalling 6,912 bytes. Create it in any Spectrum-compatible art tool (ZX Paintbrush, SEViewer, or Multipaint) or convert a modern image with a dithering tool.

### Title Screen and Menu

The title screen state displays the game logo and animated background, then transitions to the menu on any keypress:

```z80
state_title:
    ; Animate background (e.g., scrolling starfield, colour cycling)
    call title_animate

    ; Check for keypress
    xor  a
    in   a, ($FE)          ; read all keyboard half-rows at once
    cpl                    ; invert (keys are active low)
    and  $1F               ; mask 5 key bits
    jr   z, .no_key
    ld   a, STATE_MENU
    ld   (current_state), a
.no_key:
    jp   main_loop
```

The menu offers three options: Start Game, Options, High Scores. Navigation uses up/down keys, selection uses fire/enter. The menu is a simple state machine within the `STATE_MENU` handler:

```z80
menu_selection:
    db   0                 ; 0=Start, 1=Options, 2=HiScores

state_menu:
    ; Draw menu (only redraw on selection change)
    call draw_menu

    ; Read input
    call read_input
    ld   a, (input_state)

    ; Up
    bit  3, a
    jr   z, .not_up
    ld   a, (menu_selection)
    or   a
    jr   z, .not_up
    dec  a
    ld   (menu_selection), a
    call play_menu_beep
.not_up:

    ; Down
    ld   a, (input_state)
    bit  2, a
    jr   z, .not_down
    ld   a, (menu_selection)
    cp   2
    jr   z, .not_down
    inc  a
    ld   (menu_selection), a
    call play_menu_beep
.not_down:

    ; Fire / Enter
    ld   a, (input_state)
    bit  4, a
    jr   z, .no_fire
    ld   a, (menu_selection)
    or   a
    jr   nz, .not_start
    ; Start game
    call init_game
    ld   a, STATE_GAMEPLAY
    ld   (current_state), a
    jp   main_loop
.not_start:
    cp   1
    jr   nz, .not_options
    ; Options (toggle sound, controls, etc.)
    call show_options
    jp   main_loop
.not_options:
    ; High scores
    ld   a, STATE_HISCORE
    ld   (current_state), a
    jp   main_loop

.no_fire:
    jp   main_loop
```

### High Scores

High scores are stored in a 10-entry table in bank 2's data area:

```z80
; High score entry: 3 bytes name + 3 bytes BCD score = 6 bytes
; 10 entries = 60 bytes
HISCORE_COUNT equ 10
HISCORE_SIZE  equ 6

hiscore_table:
    ; Pre-filled defaults
    db   "ACE"
    db   $00, $50, $00     ; 005000 BCD
    db   "BOB"
    db   $00, $40, $00     ; 004000
    db   "CAT"
    db   $00, $30, $00     ; 003000
    ; ... 7 more entries ...
    ds   7 * HISCORE_SIZE, 0
```

Scores use BCD (Binary Coded Decimal) -- two decimal digits per byte, three bytes per score, giving a maximum of 999,999 points. BCD is preferable to binary for display because converting a 24-bit binary number to decimal on a Z80 requires expensive division. With BCD, the `DAA` instruction handles carry between digits automatically, and printing requires only masking nibbles:

```z80
; Add points to score
; DE = points to add (BCD, 2 bytes, max 9999)
add_score:
    ld   hl, player_score
    ld   a, (hl)
    add  a, e
    daa                    ; adjust for BCD
    ld   (hl), a
    inc  hl
    ld   a, (hl)
    adc  a, d
    daa
    ld   (hl), a
    inc  hl
    ld   a, (hl)
    adc  a, 0
    daa
    ld   (hl), a
    ret

player_score:
    db   0, 0, 0           ; 3 bytes BCD, little-endian
```

When the game ends, the code scans the high score table to see if the player's score qualifies. If it does, the game enters `STATE_HISCORE` for name entry (three characters, selected with up/down/fire).

On esxDOS systems, the high score table can be saved to the SD card. On tape systems, high scores persist only for the current session.

---

## 21.10 Level Loading and Decompression

When the player starts a level or completes one, the game must:

1. Page in the bank containing the level data (bank 0 for levels 1-2, bank 1 for levels 3-5)
2. Decompress the tilemap into bank 7 (the shadow screen bank, repurposed as a data buffer during level transitions)
3. Decompress the tile graphics into a buffer in bank 2 or bank 0
4. Initialise the entity array from the level's spawn table
5. Reset the viewport to the level's start position
6. Reset the scroll engine state

```z80
; Load and initialise level
; A = level number (0-4)
load_level:
    push af

    ; Determine which bank holds this level
    cp   2
    jr   nc, .bank1
    ; Levels 0-1: bank 0
    ld   a, 0
    call switch_bank
    pop  af
    push af
    ; Look up compressed data address
    add  a, a
    ld   l, a
    ld   h, 0
    ld   de, level_ptrs_bank0
    add  hl, de
    jr   .decompress
.bank1:
    ; Levels 2-4: bank 1
    ld   a, 1
    call switch_bank
    pop  af
    push af
    sub  2                 ; offset within bank 1
    add  a, a
    ld   l, a
    ld   h, 0
    ld   de, level_ptrs_bank1
    add  hl, de

.decompress:
    ; HL points to 2-byte address of compressed level data in current bank
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a              ; HL = compressed data source (in $C000-$FFFF)

    ; Decompress tilemap into bank 7
    ; First, save current bank and switch to bank 7
    ; BUT: bank 7 is at $4000 (shadow screen), not $C000
    ; We decompress to $C000 in a temporary bank, then copy
    ; OR: decompress directly into shadow screen at $4000

    ; Simpler approach: decompress into a buffer at $8000+ area
    ; (we have ~2KB free above our code in bank 2)
    ; For large levels, use bank 7 at $4000:
    ; Enable shadow screen banking, then write to $4000-$7FFF

    ld   de, level_buffer  ; destination in bank 2 work area
    call zx0_decompress    ; ZX0 decompressor: HL=src, DE=dest

    ; Initialise entities from spawn table
    pop  af                ; A = level number
    call init_level_entities

    ; Set viewport to level start
    ld   hl, 0
    ld   (viewport_x), hl
    ld   hl, 0
    ld   (viewport_y), hl

    ; Reset scroll state
    xor  a
    ld   (scroll_pixel_offset), a
    ld   (scroll_dirty), a

    ret
```

The choice of compressor matters here. Level data is loaded once per level (during a transition screen), so decompression speed is not critical -- we can afford Exomizer's ~250 T-states per byte for the best compression ratio. But tile graphics may need to be decompressed during gameplay (if tiles are banked), so Pletter's ~69 T-states per byte is preferable.

As discussed in Chapter 14, the decompressor code itself occupies memory. ZX0 at ~70 bytes is ideal for projects where code space is tight. Ironclaw includes both a ZX0 decompressor (for level data at load time) and a Pletter decompressor (for streamed tile data during gameplay).

---

## 21.11 Profiling with DeZog

You have written all the code. It compiles. It runs. The player walks, enemies patrol, tiles scroll, music plays. But the frame budget overflows on level 3, where six enemies and three projectiles are on screen simultaneously. The border stripe shows a red band that extends past the visible screen area. You are dropping frames.

This is where DeZog earns its place in your toolchain.

### What is DeZog?

DeZog is a VS Code extension that provides a full debugging environment for Z80 programs. It connects to emulators (ZEsarUX, CSpect, or its own internal simulator) and gives you:

- Breakpoints (address, conditional, logpoints)
- Step-through execution (step into, step over, step out)
- Register watches (all Z80 registers, updated in real time)
- Memory viewer (hex dump with live updates)
- Disassembly view
- Call stack
- **T-state counter** -- the profiling tool we need

### The Profiling Workflow

The border stripe tells you *that* you are over budget. DeZog tells you *where*.

**Step 1: Isolate the slow frame.** Set a conditional breakpoint at the start of the main loop that triggers only when a "frame overflow" flag is set. Add code to set this flag when the frame takes too long:

```z80
; At the end of the gameplay frame, before HALT:
    ; Check if we're still in the current frame
    ; (a simple approach: read the raster line via floating bus
    ;  or use a frame counter incremented by IM2)
    ld   a, (frame_overflow_flag)
    or   a
    jr   z, .ok
    ; Frame overflowed -- set debug breakpoint trigger
    nop                    ; <-- set DeZog breakpoint here
.ok:
```

**Step 2: Measure subsystem costs.** DeZog's T-state counter lets you measure the exact cost of any code section. Place the cursor at the start of `update_enemy_ai`, note the T-state counter, step over the call, and note the new counter value. The difference is the exact cost.

A systematic profiling pass measures each subsystem:

```
Subsystem            Measured T-states   Budget %
─────────────────────────────────────────────────
read_input                    187          0.3%
update_player_physics         743          1.0%
update_player_state           412          0.6%
update_enemy_ai             4,231          5.9%   <-- worst case
check_all_collisions        2,847          4.0%
update_projectiles            523          0.7%
scroll_viewport            12,456         17.4%   <-- expensive
render_exposed_tiles       11,892         16.6%   <-- expensive
restore_backgrounds         3,214          4.5%
draw_sprites               10,156         14.2%   <-- expensive
update_hud                  1,389          1.9%
[IM2 music interrupt]       3,102          4.3%
─────────────────────────────────────────────────
TOTAL                      51,152         71.4%
Slack                      20,528         28.6%
```

That is the average case. Now profile the worst case -- level 3, six enemies on screen, player near the right edge triggering a scroll:

```
Subsystem            Measured T-states   Budget %
─────────────────────────────────────────────────
read_input                    187          0.3%
update_player_physics         743          1.0%
update_player_state           412          0.6%
update_enemy_ai             5,891          8.2%   <-- 6 enemies active
check_all_collisions        4,156          5.8%   <-- more pairs
update_projectiles          1,247          1.7%   <-- 3 projectiles
scroll_viewport            14,892         20.8%   <-- scroll + new column
render_exposed_tiles       14,456         20.2%   <-- full column render
restore_backgrounds         4,821          6.7%
draw_sprites               13,892         19.4%   <-- 10 entities
update_hud                  1,389          1.9%
[IM2 music interrupt]       3,102          4.3%
─────────────────────────────────────────────────
TOTAL                      65,188         90.9%
Slack                       6,492          9.1%
```

Only 9% slack in the worst case. That is dangerously thin. One more enemy or a complex music pattern could push you over.

**Step 3: Find the bottleneck.** The profiling table makes it obvious: scrolling + tile rendering consume 41% of the frame in the worst case. Sprite rendering takes 19%. Enemy AI takes 8%.

**Step 4: Optimise the bottleneck.** Options, roughly in order of impact:

1. **Spread the scroll cost.** Instead of rendering the full new column in one frame, render half on frame N and half on frame N+1 using the double buffer (discussed in section 21.4). This cuts the scroll spike from ~29,000 to ~15,000 T-states per frame.

2. **Use compiled sprites for the player.** The player sprite is always on screen and always rendered. Switching from OR+AND masked (Chapter 16, method 2) to compiled sprites (method 5) saves ~30% per sprite draw, but increases memory usage. For one frequently-drawn entity, the trade-off is worth it.

3. **Reduce sprite overdraw.** If two enemies overlap, you are drawing pixels that will be overwritten. Sort entities by Y coordinate (back-to-front) and skip drawing for fully occluded sprites. This helps in the worst case when entities cluster.

4. **Tighten the AI.** Profile `run_entity_ai` for each enemy type. The Shooter's line-of-sight check (scanning tile columns for occlusion) is often the most expensive AI operation. Cache the result: only re-check line-of-sight every 8 frames instead of every 3.

After optimisation, the worst case drops to ~58,000 T-states, leaving 19% slack. That is comfortable.

### DeZog Configuration for Ironclaw

DeZog connects to an emulator that supports its debug protocol. For ZX Spectrum 128K development, ZEsarUX is the recommended choice:

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "dezog",
            "request": "launch",
            "name": "Ironclaw (ZEsarUX)",
            "remoteType": "zesarux",
            "zesarux": {
                "hostname": "localhost",
                "port": 10000
            },
            "sjasmplus": [
                {
                    "path": "src/main.a80"
                }
            ],
            "topOfStack": "0xBFFF",
            "load": "build/ironclaw.sna",
            "startAutomatically": true,
            "history": {
                "reverseDebugInstructionCount": 100000
            }
        }
    ]
}
```

The `history` setting enables reverse debugging -- you can step backwards to see how you arrived at a bug. This is invaluable for tracking down collision glitches where an entity teleported through a wall three frames ago.

---

## 21.12 The Data Pipeline in Detail

Getting data from artist tools into the game is often the most underestimated part of a project. Ironclaw's pipeline converts four kinds of assets:

### Tilesets (PNG to Spectrum pixel format)

The artist draws tiles in Aseprite, Photoshop, or any pixel art tool as an indexed-colour PNG. Tiles are arranged in a grid on a single sheet. The conversion script:

1. Reads the PNG, verifies it is 1-bit (black and white) or indexed with Spectrum-compatible colours
2. Slices into 8x8 or 16x16 tiles
3. Converts each tile to the Spectrum's interleaved pixel format (where row 0 is at offset 0, row 1 at offset 256, not offset 1 -- matching the screen layout)
4. Optionally deduplicates identical tiles
5. Writes a binary blob and a symbol table mapping tile IDs to offsets

For attributes, each tile also carries a colour byte (INK + PAPER + BRIGHT). The script extracts this from the PNG's palette and writes a parallel attribute table.

### Sprite Sheets (PNG to pre-shifted sprite data)

Sprites follow a similar pipeline, but with an additional step: pre-shifting. The conversion script:

1. Reads the PNG sprite sheet
2. Slices into individual frames
3. Generates a mask for each frame (any non-background pixel produces a 0 in the mask, background produces 1)
4. For each frame, generates 4 horizontally shifted variants (0, 2, 4, 6 pixels offset)
5. Each shifted variant is widened by one byte (a 2-byte-wide sprite becomes 3 bytes wide to hold shifted overflow)
6. Writes interleaved data+mask bytes for efficient rendering

### Level Maps (Tiled JSON to binary tilemap)

Levels are designed in Tiled, a free cross-platform tilemap editor. The designer places tiles visually, adds object layers for entity spawn points and triggers, and exports as JSON or TMX.

The conversion script:

1. Reads the Tiled export
2. Extracts the tile layer as a flat array of tile indices
3. Extracts the object layer for spawn points (enemy positions, player start, item locations)
4. Generates a collision map: for each tile, looks up whether it is solid, a platform, a hazard, or empty (based on a tile properties file)
5. Writes the tilemap, collision map, and spawn table as separate binary files

### Music (Vortex Tracker II to PT3)

Music is composed in Vortex Tracker II, which exports directly to `.pt3` format. The PT3 file is embedded into the bank data with `INCBIN`. The PT3 player code (widely available as open-source Z80 assembly, typically 1.5-2KB) is included in the music bank alongside the song data.

### Putting It Together

The complete conversion pipeline for a level:

```
tileset.png ──→ png2tiles.py ──→ tileset.bin ──→ pletter ──→ tileset.bin.plt
                                                              │
level1.tmx ──→ map2bin.py ──→ level1_map.bin ──→ zx0 ──→ level1_map.bin.zx0
              └─→ level1_collision.bin ──→ zx0 ──→ level1_col.bin.zx0
              └─→ level1_spawns.bin (uncompressed, small)
                                                              │
player.png ──→ png2sprites.py ──→ player.bin (pre-shifted) ──┘
enemies.png ──→ png2sprites.py ──→ enemies.bin              ──┘
                                                              │
level1.pt3 ──→ (direct INCBIN) ──────────────────────────────┘
                                                              │
sjasmplus main.a80 ──→ INCBIN all of the above ──→ ironclaw.tap
```

Every step is automated by the Makefile. The artist changes a tile, types `make`, and sees the result in the emulator.

---

## 21.13 Release Format: Building the .tap

The final deliverable is a `.tap` file. sjasmplus can generate `.tap` output directly using its `SAVETAP` directive:

```z80
; main.a80 -- top-level assembly file

    ; Define the BASIC loader
    DEVICE ZXSPECTRUM128

    ; Page in bank 2 at $8000
    ORG $8000

    ; Include all game code
    INCLUDE "defs.a80"
    INCLUDE "banks.a80"
    INCLUDE "render.a80"
    INCLUDE "sprites.a80"
    INCLUDE "entities.a80"
    INCLUDE "physics.a80"
    INCLUDE "collisions.a80"
    INCLUDE "ai.a80"
    INCLUDE "player.a80"
    INCLUDE "hud.a80"
    INCLUDE "menu.a80"
    INCLUDE "loader.a80"
    INCLUDE "music_driver.a80"
    INCLUDE "sfx.a80"
    INCLUDE "esxdos.a80"

    ; Entry point
entry:
    di
    ld   sp, $BFFF
    call init_system
    call detect_esxdos
    jr   c, .tape_load
    call load_from_esxdos
    jr   .loaded
.tape_load:
    call load_bank_data
.loaded:
    call init_interrupts
    ei
    jp   main_loop

    ; Bank data sections
    ; Each SLOT/PAGE directive places data into the correct bank
    SLOT 3               ; use $C000 slot
    PAGE 0               ; bank 0
    ORG $C000
    INCLUDE "data/bank0_levels.a80"   ; INCBIN compressed level data

    PAGE 1               ; bank 1
    ORG $C000
    INCLUDE "data/bank1_levels.a80"

    PAGE 3               ; bank 3
    ORG $C000
    INCLUDE "data/bank3_sprites.a80"

    PAGE 4               ; bank 4
    ORG $C000
    INCLUDE "data/bank4_music.a80"

    PAGE 6               ; bank 6
    ORG $C000
    INCLUDE "data/bank6_sfx.a80"

    ; Save as .tap with BASIC loader
    SAVETAP "build/ironclaw.tap", BASIC, "Ironclaw", 10, 2
    SAVETAP "build/ironclaw.tap", CODE, "Screen", $4000, 6912, $4000
    SAVETAP "build/ironclaw.tap", CODE, "Code", $8000, $-$8000, $8000

    ; Save bank snapshots (for .sna or manual loading)
    SAVESNA "build/ironclaw.sna", entry
```

The exact SAVETAP syntax varies by sjasmplus version. For 128K games with banked data, the cleanest approach is to generate a `.sna` snapshot (which captures all bank states) for emulator testing, and a `.tap` with a BASIC loader plus machine code blocks for distribution.

### Testing the Release

Before publishing, test on at least three emulators:

1. **Fuse** -- the reference Spectrum emulator, accurate timing for original hardware
2. **Unreal Speccy** -- Pentagon timing, the demoscene standard, good debugger
3. **ZEsarUX** -- supports 128K banking, esxDOS emulation, DeZog integration

And if possible, test on real hardware with a DivMMC. Emulators occasionally differ in timing edge cases, and a game that runs perfectly in Fuse may drop frames on a real Spectrum due to contended memory effects that the emulator models slightly differently.

---

## 21.14 Final Polish

The difference between a working game and a finished game is polish. Here is a checklist of small touches that matter:

**Screen transitions.** Do not jump between screens instantly. A simple fade-to-black (write decreasing brightness to all attributes over 8 frames) or a wipe (clear columns from left to right over 16 frames) gives the game a professional feel. Cost: negligible -- transitions happen between gameplay frames.

**Death animation.** When the player dies, freeze gameplay for 15 frames, flash the player sprite by toggling its INK between frames, play the death SFX, then respawn. Do not just teleport the player back to the checkpoint.

**Screen shake.** When the boss hits the ground or an explosion goes off, shift the viewport by 1-2 pixels for 4-6 frames. On the Spectrum, you can fake this by adjusting the scroll offset without actually moving any tiles. It is almost free and adds enormous impact.

**Attract mode.** After 30 seconds on the title screen with no input, start a demo playback -- record the player's input during a test run and replay it. This is how arcade games hook passersby, and it works for Spectrum games too.

**Colour cycling.** Animate menu text or logo colours by cycling attributes through a palette table. A 4-byte attribute cycle costs essentially zero CPU and makes static screens feel alive.

**Input debounce.** Ignore key presses that last fewer than 2 frames. Without debounce, the menu cursor will skip past options because the key was held for multiple frames. A simple frame counter per key fixes this:

```z80
; Debounced fire button
fire_held_frames:
    db   0

check_fire:
    ld   a, (input_state)
    bit  4, a
    jr   z, .released
    ; Fire is held
    ld   a, (fire_held_frames)
    inc  a
    ld   (fire_held_frames), a
    cp   1                 ; only trigger on first frame of press
    ret                    ; Z flag set if this is the first frame
.released:
    xor  a
    ld   (fire_held_frames), a
    ret                    ; Z flag clear (no fire)
```

---

## Summary

- **Project structure matters.** Separate source files by subsystem, data files by type. Use a Makefile to automate the full pipeline from PNG/TMX to `.tap`.

- **Memory map carefully.** Code in bank 2 (fixed at `$8000`), level data in banks 0-1, sprite graphics in bank 3, music in banks 4 and 6, shadow screen in bank 7. Keep a shadow copy of port `$7FFD` -- it is write-only.

- **The interrupt handler owns the music.** The IM2 handler pages in the music bank, runs the PT3 player, updates SFX, and restores the previous bank. Keep it lean -- ~3,000 T-states maximum.

- **The gameplay frame budget on Pentagon is 71,680 T-states.** A typical frame with scrolling, 8 sprites, and AI costs ~50,000 T-states average, ~65,000 worst case. Profile and optimise the worst case, not the average.

- **Scrolling is the most expensive single operation.** Use the combined scroll method (character-level LDIR + pixel offset) with shadow screen double-buffering. Spread the column copy across two frames when possible.

- **Run enemy AI every 2nd or 3rd frame.** Physics and collision detection run every frame; AI decisions can be amortised. This saves 2,000-3,000 T-states per frame in the worst case.

- **Use esxDOS for modern hardware.** The `RST $08` / `F_OPEN` / `F_READ` / `F_CLOSE` API is simple and fast. Detect DivMMC at startup and fall back to tape loading if absent.

- **Profile with DeZog.** The border stripe tells you that you are over budget. DeZog tells you where. Measure each subsystem, find the bottleneck, optimise it, measure again.

- **Choose the right compressor for each job.** Exomizer or ZX0 for one-time level loading (best ratio). Pletter for tile streaming during gameplay (fast decompression). See Chapter 14 for the full tradeoff analysis.

- **Polish is not optional.** Screen transitions, death animations, screen shake, input debounce, and attract mode are the difference between a tech demo and a game.

- **Test on multiple emulators and real hardware.** Fuse, Unreal Speccy, and ZEsarUX each model timing differently. DivMMC behaviour on real hardware can differ from emulated esxDOS.

---

> **Sources:** World of Spectrum (ZX Spectrum 128K memory map and port $7FFD documentation); Introspec "Data Compression for Modern Z80 Coding" (Hype 2017); esxDOS API documentation (DivIDE/DivMMC wiki); DeZog VS Code Extension documentation (GitHub: maziac/DeZog); sjasmplus documentation (SAVETAP, DEVICE, SLOT, PAGE directives); Vortex Tracker II PT3 format specification; Chapters 11, 14, 15, 16, 17, 18, 19 of this book.
