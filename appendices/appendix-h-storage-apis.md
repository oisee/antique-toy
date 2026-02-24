# Appendix H: Storage APIs --- TR-DOS and esxDOS

> *"A technically impressive demo that ships as a .tzx when the rules require .trd will be disqualified."*
> -- Chapter 20

Two storage APIs dominate the ZX Spectrum world: **TR-DOS** (the disk operating system of the Soviet Beta Disk 128 interface, standard on Pentagon and Scorpion clones) and **esxDOS** (the modern SD card operating system running on DivMMC and DivIDE hardware). Most Russian and Ukrainian demoscene releases ship as `.trd` disk images. Most modern Western releases use `.tap` tape images or esxDOS-compatible file layouts. If you are releasing a demo or game today, the practical choice is to provide a `.trd` image for compatibility with the enormous Russian/Ukrainian install base, and a `.tap` file for everyone else. If your loader supports esxDOS detection (as described in Chapter 21), users with DivMMC hardware get fast SD card loading for free.

This appendix is the API reference you keep open while writing your loader. Chapter 21 covers integration in a full game project. Chapter 15 covers the hardware details of memory banking and port mapping that underpin both APIs.

---

## 1. TR-DOS (Beta Disk 128)

### Hardware

The Beta Disk 128 interface is the standard floppy disk controller for Pentagon, Scorpion, and most Soviet ZX Spectrum clones. It is based on the Western Digital WD1793 floppy disk controller chip, which communicates with the Z80 through five I/O ports.

The TR-DOS ROM (8 KB) occupies `$0000`--`$3FFF` when the Beta Disk interface is active. It is paged in automatically when the Z80 executes code at address `$3D13` (the magic entry point), and paged out when execution returns to the main ROM area.

### Disk Format

| Property | Value |
|----------|-------|
| Tracks | 80 |
| Sides | 2 |
| Sectors per track | 16 |
| Bytes per sector | 256 |
| Total capacity | 640 KB (655,360 bytes) |
| Image format | `.trd` (raw disk image, 640 KB) |
| System track | Track 0, side 0 |

Track 0 contains the disk directory (sectors 1--8) and the disk information sector (sector 9). The directory holds up to 128 file entries. Each entry is 16 bytes:

```
Bytes 0-7:   Filename (8 characters, space-padded)
Byte  8:     File type: 'C' = code, 'B' = BASIC, 'D' = data, '#' = sequential
Bytes 9-10:  Start address (or BASIC line number)
Bytes 11-12: Length in bytes
Byte  13:    Length in sectors
Byte  14:    Starting sector
Byte  15:    Starting track
```

### WD1793 Port Map

| Port | Read | Write |
|------|------|-------|
| `$1F` | Status register | Command register |
| `$3F` | Track register | Track register |
| `$5F` | Sector register | Sector register |
| `$7F` | Data register | Data register |
| `$FF` | TR-DOS system register | TR-DOS system register |

Port `$FF` is the Beta Disk system port. It controls drive selection, side selection, head load, and density. The upper bits also reflect the DRQ (Data Request) and INTRQ (Interrupt Request) signals from the WD1793.

### WD1793 Commands

| Command | Code | Description |
|---------|------|-------------|
| Restore | `$08` | Move head to track 0. Verify track. |
| Seek | `$18` | Move head to track in data register. |
| Step In | `$48` | Step head one track toward centre. |
| Step Out | `$68` | Step head one track toward edge. |
| Read Sector | `$88` | Read one 256-byte sector. |
| Write Sector | `$A8` | Write one 256-byte sector. |
| Read Address | `$C0` | Read the next sector ID field. |
| Force Interrupt | `$D0` | Abort current command. |

The low nibble of each command byte carries modifier flags (step rate, verify, side select, delay). The values above use common defaults. Consult the WD1793 datasheet for the full bit layout.

### ROM API: Loading a File

The standard approach to file I/O under TR-DOS is to call the ROM routines at `$3D13`. The TR-DOS ROM provides high-level file operations through a command system: you place parameters in registers and in the system area at `$5D00`--`$5FFF`, then call into the ROM.

```z80
; TR-DOS: Load a file by name
; Loads a code file ('C' type) to its stored start address
;
; The filename must be placed at $5D02 (8 bytes, space-padded).
; The file type goes to $5D0A.
;
; Call $3D13 with C = $08 (load file command)

load_trdos_file:
    ; Set up filename at TR-DOS system area
    ld   hl, my_filename
    ld   de, $5D02
    ld   bc, 8
    ldir                    ; copy 8-char filename

    ld   a, 'C'             ; file type: code
    ld   ($5D0A), a

    ld   c, $08             ; TR-DOS command: load file
    call $3D13              ; enter TR-DOS ROM
    ret

my_filename:
    db   "SCREEN  "         ; 8 characters, space-padded
```

To load to a specific address (overriding the stored start address):

```z80
; TR-DOS: Load file to explicit address
; HL = destination address
; DE = length to load
; Filename already at $5D02, type at $5D0A

load_trdos_to_addr:
    ld   hl, $4000          ; load to screen memory
    ld   de, 6912           ; 6912 bytes (one screen)
    ld   ($5D03), hl        ; override start address
    ld   ($5D05), de        ; override length
    ld   c, $08             ; load file
    call $3D13
    ret
```

### Direct Sector Access

For demos that stream data from disk --- fullscreen animations, music data that exceeds available RAM, or multipart demos that load effects on the fly --- direct sector access bypasses the file system entirely. You control the head position, read sectors one at a time, and process the data as it arrives.

```z80
; Read a single sector directly via WD1793 ports
; B = track number (0-159, with side encoded in bit 0 of $FF)
; C = sector number (1-16)
; HL = destination buffer (256 bytes)

read_sector:
    ld   a, b
    out  ($3F), a           ; set track register
    ld   a, c
    out  ($5F), a           ; set sector register

    ld   a, $88             ; Read Sector command
    out  ($1F), a           ; issue command

    ; Wait for DRQ and read 256 bytes
    ld   b, 0               ; 256 bytes to read
.wait_drq:
    in   a, ($FF)           ; read system register
    bit  6, a               ; test DRQ bit
    jr   z, .wait_drq       ; wait until data ready
    in   a, ($7F)           ; read data byte
    ld   (hl), a
    inc  hl
    djnz .wait_drq

    ; Wait for command completion
.wait_done:
    in   a, ($1F)           ; read status register
    bit  0, a               ; test BUSY bit
    jr   nz, .wait_done
    ret
```

**Warning:** Direct sector access is timing-sensitive. Interrupts must be disabled during the data transfer loop, or bytes will be lost. The WD1793 asserts DRQ for a limited time window; if the Z80 does not read the data register before the next byte arrives, data is overwritten. At 250 kbit/s (double density), you have approximately 32 microseconds per byte --- about 112 T-states on a Pentagon. The tight loop above runs in roughly 50--60 T-states per byte, leaving adequate margin.

### Disk Detection

To detect whether a Beta Disk interface is present:

```z80
; Detect Beta Disk 128
; Returns: carry clear if present, carry set if absent
detect_beta_disk:
    ; The TR-DOS ROM signature is at $0069 when paged in.
    ; We can check port $FF for a sane response:
    ; If no Beta Disk is present, port $FF reads as floating bus.
    in   a, ($1F)           ; read WD1793 status
    cp   $FF                ; floating bus returns $FF
    scf
    ret  z                  ; probably no controller
    or   a                  ; clear carry = present
    ret
```

A more robust method is to attempt to call `$3D13` and check if TR-DOS ROM signature bytes are present. Production code typically checks for a known byte sequence at the TR-DOS ROM entry points.

---

## 2. esxDOS (DivMMC / DivIDE)

### Hardware

DivMMC (and its older sibling DivIDE) is a mass storage interface that connects an SD card to the ZX Spectrum. The esxDOS firmware provides a POSIX-like file API accessible from Z80 code through `RST $08`. esxDOS supports FAT16 and FAT32 file systems, long filenames, subdirectories, and multiple open file handles.

DivMMC uses auto-mapping: when the Z80 fetches an instruction from certain "trap" addresses (notably `$0000`, `$0008`, `$0038`, `$0066`, `$04C6`, `$0562`), the DivMMC hardware automatically pages in its own ROM at `$0000`--`$1FFF`. The `RST $08` trap is the primary API entry point.

### API Pattern

Every esxDOS call follows the same pattern:

```z80
    rst  $08              ; trigger DivMMC auto-map
    db   function_id      ; function number (byte after RST)
    ; Returns:
    ;   Carry clear = success
    ;   Carry set   = error, A = error code
```

The function number is the byte immediately following the `RST $08` instruction in memory. The Z80 executes `RST $08`, which jumps to address `$0008`. DivMMC auto-maps its ROM at that address, reads the next byte (the function number), dispatches the call, then un-maps its ROM and returns to the instruction after the `DB`.

### Function Reference

| Function | ID | Description | Input | Output |
|----------|-----|------------|-------|--------|
| `M_GETSETDRV` | `$89` | Get/set default drive | A = `'*'` for default | A = drive letter |
| `F_OPEN` | `$9A` | Open file | IX = filename (zero-terminated), B = mode, A = drive | A = file handle |
| `F_CLOSE` | `$9B` | Close file | A = file handle | -- |
| `F_READ` | `$9D` | Read bytes | A = handle, IX = buffer, BC = count | BC = bytes read |
| `F_WRITE` | `$9E` | Write bytes | A = handle, IX = buffer, BC = count | BC = bytes written |
| `F_SEEK` | `$9F` | Seek in file | A = handle, L = whence, BCDE = offset | BCDE = new position |
| `F_FSTAT` | `$A1` | File status (by handle) | A = handle, IX = buffer | 11-byte stat block |
| `F_OPENDIR` | `$A3` | Open directory | IX = path (zero-terminated) | A = dir handle |
| `F_READDIR` | `$A4` | Read directory entry | A = dir handle, IX = buffer | entry at (IX) |
| `F_CLOSEDIR` | `$A5` | Close directory | A = dir handle | -- |
| `F_GETCWD` | `$A8` | Get current directory | IX = buffer | path at (IX) |
| `F_CHDIR` | `$A9` | Change directory | IX = path | -- |
| `F_STAT` | `$AC` | File status (by name) | IX = filename | 11-byte stat block |

### File Open Modes

| Mode | Value | Description |
|------|-------|-------------|
| Read only | `$01` | Open existing file for reading |
| Create/truncate | `$06` | Create new or truncate existing for writing |
| Create new only | `$04` | Create new file; fail if exists |
| Append | `$0E` | Open for writing at end of file |

### Seek Whence Values

| Whence | Value | Description |
|--------|-------|-------------|
| `SEEK_SET` | `$00` | Offset from beginning of file |
| `SEEK_CUR` | `$01` | Offset from current position |
| `SEEK_END` | `$02` | Offset from end of file |

### Code Example: Load a File

```z80
; esxDOS: Load a binary file into memory
;
; Uses register conventions from esxDOS API documentation.
; Note: F_READ uses IX for the destination buffer, not HL.

    ld   a, '*'             ; use default drive
    ld   ix, filename       ; pointer to zero-terminated filename
    ld   b, $01             ; FA_READ: open for reading
    rst  $08
    db   $9A                ; F_OPEN
    jr   c, .error          ; carry set = error

    ld   (.file_handle), a  ; save file handle

    ld   ix, $4000          ; destination buffer (screen memory)
    ld   bc, 6912           ; bytes to read (one full screen)
    ld   a, (.file_handle)
    rst  $08
    db   $9D                ; F_READ
    jr   c, .error

    ld   a, (.file_handle)
    rst  $08
    db   $9B                ; F_CLOSE
    ret

.error:
    ; A contains the esxDOS error code
    ; Common errors:
    ;   5 = file not found
    ;   7 = file already exists (on create)
    ;   9 = invalid file handle
    ret

filename:
    db   "screen.scr", 0

.file_handle:
    db   0
```

### Code Example: Streaming Data from File

For demos that load data incrementally --- decompressing level chunks between frames, streaming a pre-rendered animation, or loading music patterns on demand --- the pattern is: open the file once, read a chunk per frame, close when done.

```z80
; Streaming: read N bytes per frame from an open file
; Call stream_init once, then stream_chunk from your main loop.

CHUNK_SIZE  equ  256        ; bytes per frame (tune to budget)

stream_handle:  db 0
stream_done:    db 0

; Initialise: open the file
stream_init:
    ld   a, '*'
    ld   ix, stream_file
    ld   b, $01             ; FA_READ
    rst  $08
    db   $9A                ; F_OPEN
    ret  c                  ; error
    ld   (stream_handle), a
    xor  a
    ld   (stream_done), a   ; not done yet
    ret

; Per-frame: read one chunk into buffer
; Returns: BC = bytes actually read (may be < CHUNK_SIZE at EOF)
stream_chunk:
    ld   a, (stream_done)
    or   a
    ret  nz                 ; already finished

    ld   a, (stream_handle)
    ld   ix, stream_buffer
    ld   bc, CHUNK_SIZE
    rst  $08
    db   $9D                ; F_READ
    jr   c, .eof

    ; BC = bytes actually read
    ld   a, b
    or   c
    jr   z, .eof            ; zero bytes read = end of file
    ret

.eof:
    ld   a, (stream_handle)
    rst  $08
    db   $9B                ; F_CLOSE
    ld   a, 1
    ld   (stream_done), a
    ret

stream_file:
    db   "anim.bin", 0

stream_buffer:
    ds   CHUNK_SIZE
```

### Detecting esxDOS

```z80
; Detect esxDOS presence
; Returns: carry clear = esxDOS available, carry set = not available
;
; Strategy: attempt M_GETSETDRV. If esxDOS is present, it returns
; the current drive letter. If not present, RST $08 goes to the
; Spectrum ROM's error handler at $0008 (a benign instruction on
; the 128K ROM) and does not crash.

detect_esxdos:
    ld   a, '*'             ; request default drive
    rst  $08
    db   $89                ; M_GETSETDRV
    ret                     ; carry flag set by esxDOS on error
```

A more conservative approach checks for the DivMMC's trap signature before calling any API functions. In practice, the method above works on all 128K models because the 128K ROM's `$0008` handler does not crash --- it executes a benign sequence and returns. On a 48K machine without esxDOS, `RST $08` goes to the error restart, which may need special handling. Chapter 21 discusses this in the context of a production game loader.

---

## 3. +3DOS (Amstrad +3)

The Amstrad Spectrum +3, with its built-in 3-inch floppy drive, has its own DOS: +3DOS. The API uses a different mechanism --- calls to entry points in the +3DOS ROM at page `$01`, accessed through `RST $08` with a different set of function codes.

+3DOS is rarely used in the demoscene for two reasons. First, the +3 was primarily sold in Western Europe and was never the dominant Spectrum model in any scene community. Second, the +3's non-standard memory layout and ROM paging scheme make it incompatible with most demoscene code written for the 128K/Pentagon architecture. If you need +3 compatibility, the +3DOS API is documented in the Spectrum +3 technical manual (Amstrad, 1987). For most demo and game projects, providing a `.tap` file is sufficient --- the +3 loads `.tap` files natively through its tape compatibility mode.

---

## 4. Practical Patterns

### Loading Screen from Disk (TR-DOS)

The loading screen is the user's first impression. On TR-DOS, the screen file (`SCREEN  C`, 6912 bytes) loads directly to `$4000` and appears immediately:

```z80
; TR-DOS: Load a .scr file directly to screen memory
; The screen appears as it loads, line by line.
load_screen_trdos:
    ld   hl, scr_filename
    ld   de, $5D02
    ld   bc, 8
    ldir
    ld   a, 'C'
    ld   ($5D0A), a
    ld   hl, $4000          ; destination: screen memory
    ld   ($5D03), hl
    ld   de, 6912           ; length: full screen
    ld   ($5D05), de
    ld   c, $08             ; load file
    call $3D13
    ret

scr_filename:
    db   "SCREEN  "         ; 8 chars, padded
```

### Loading Screen from SD (esxDOS)

Same visual result, different API:

```z80
; esxDOS: Load a .scr file to screen memory
load_screen_esxdos:
    ld   a, '*'
    ld   ix, scr_filename_esx
    ld   b, $01             ; FA_READ
    rst  $08
    db   $9A                ; F_OPEN
    ret  c

    push af                 ; save handle
    ld   ix, $4000          ; destination: screen memory
    ld   bc, 6912
    pop  af
    push af
    rst  $08
    db   $9D                ; F_READ
    pop  af
    rst  $08
    db   $9B                ; F_CLOSE
    ret

scr_filename_esx:
    db   "screen.scr", 0
```

### Dual-Mode Loader

A production loader should detect the available storage and use it:

```z80
; Unified loader: try esxDOS first, fall back to TR-DOS, then tape
load_data:
    call detect_esxdos
    jr   nc, .use_esxdos    ; carry clear = esxDOS present

    call detect_beta_disk
    jr   nc, .use_trdos     ; carry clear = Beta Disk present

    ; Fall back to tape loading
    jp   load_from_tape

.use_esxdos:
    jp   load_from_esxdos

.use_trdos:
    jp   load_from_trdos
```

### Streaming Compressed Data

The most powerful pattern combines storage API with compression (Appendix C). Open a file containing compressed data, read chunks into a buffer each frame, decompress into the destination, and advance:

```
Frame 1:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
Frame 2:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
Frame 3:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
...
Frame N:  F_READ < 256 bytes (EOF)     |  decompress, close file
```

At 256 bytes per frame and 50 fps, you stream 12.5 KB/sec from the SD card --- enough for a compressed fullscreen animation. On TR-DOS, direct sector reads at one sector per frame give 12.8 KB/sec (256 bytes * 50 fps). The bottleneck is decompression speed, not I/O.

---

## 5. File Format Reference

| Format | Extension | Usage | Notes |
|--------|-----------|-------|-------|
| TR-DOS disk image | `.trd` | Standard for Pentagon/Scorpion releases | Raw 640 KB image. Every emulator supports it. |
| TR-DOS file container | `.scl` | Simpler than .trd | Contains files without full disk structure. Good for distribution. |
| Tape image | `.tap` | Universal tape format | Works on every Spectrum model and emulator. No file system. |
| Extended tape image | `.tzx` | Tape with copy protection / turbo loaders | Preserves exact tape timing. Rarely needed for new releases. |
| Snapshot (48K/128K) | `.sna` | Quick load, no file system | Captures full machine state. No loading code needed. |
| Snapshot (compressed) | `.z80` | Like .sna but compressed | Multiple versions; .z80 v3 supports 128K. |
| Next distribution | `.nex` | ZX Spectrum Next executable | Self-contained binary with header specifying bank layout. |

**Choosing a release format:** For a demoscene release, provide at least two formats:

1. **`.trd`** for TR-DOS users (the Russian/Ukrainian community, Pentagon/Scorpion owners, and emulator users who prefer disk images). This is the default for parties like Chaos Constructions and DiHalt.
2. **`.tap`** for everyone else (real 128K hardware with tape input, DivMMC users via `.tap` loader, and all emulators). sjasmplus can generate `.tap` output directly with its `SAVETAP` directive.

If your demo is small enough (under 48 KB), a `.sna` snapshot also works well --- it loads instantly with no loader code.

---

## 6. See Also

- **Chapter 15** --- Hardware Anatomy: memory banking, port `$7FFD`, the full port map that TR-DOS and esxDOS sit alongside.
- **Chapter 20** --- Demo Workflow: release formats, party submission rules, `.trd` vs `.tap` requirements.
- **Chapter 21** --- Full Game: production-quality tape and esxDOS loading code, dual-mode detection, bank-by-bank loading.
- **Appendix C** --- Compression: which compressors to pair with streaming I/O.
- **Appendix E** --- eZ80 / Agon Light 2: the MOS file API on Agon, which provides similar file operations (`mos_fopen`, `mos_fread`, `mos_fclose`) through a different mechanism (RST $08 with MOS function codes in ADL mode).

---

> **Sources:** WD1793 datasheet (Western Digital, 1983); TR-DOS v5.03 disassembly (various, public domain); esxDOS API documentation (Wikipedia, zxe.io); DivMMC hardware specification (Mario Prato / ByteDelight); Spectrum +3 Technical Manual (Amstrad, 1987); Introspec, "Loading and saving on the Spectrum" (Hype, 2016)
