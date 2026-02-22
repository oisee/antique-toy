# Chapter 12: Digital Drums and Music Sync

> *"My brain is not coping with asynchronous coding well."*
> -- Introspec, file_id.diz for the party version of Eager (to live), 3BM Open Air 2015

---

A demo is not a slideshow of effects. A demo is a performance -- one where every visual event lands on the beat, every transition breathes with the music, and the audience never suspects that behind the curtain, a 3.5MHz processor is juggling half a dozen competing demands with no operating system, no threads, and no safety net.

This chapter is about the architecture that makes that juggling act possible. We have spent the previous chapters building individual effects -- tunnels, zoomers, scrollers, colour animations -- and in Chapter 11 we learned how the AY chip produces music. Now we must wire everything together. The questions are no longer "how do I draw a tunnel?" or "how do I play a note?" but rather: How do I play a drum sample that consumes nearly all the CPU while keeping the visuals smooth? How do I synchronise effect changes to the beat of the music? How do I structure a two-minute demo so that it runs reliably from start to finish?

The answers come from three sources. Introspec's Eager (2015) gives us digital drum synthesis and asynchronous frame generation. diver4d's GABBA (2019) shows a radically different approach to music sync using a video editor as a timeline tool. And Robus's threading system (2015) demonstrates that honest multithreading on the Z80 is possible, if rarely necessary.

Together, these three techniques represent the architectural thinking that separates a collection of effects from a finished demo.

---

## 12.1 Digital Drums on the AY

### The Problem: The AY Cannot Play Samples

The AY-3-8910, as we covered in Chapter 11, is a synthesiser. It generates square waves, noise, and envelope shapes. It has no sample playback capability, no DAC, no waveform RAM. Every sound it makes is built from those primitive sources in real time. If you want a realistic kick drum -- the kind with a sharp transient punch followed by a resonant decay -- the AY's noise generator and envelope can approximate it, but the result sounds unmistakably synthetic. It lacks the weight of a real percussive hit.

But there is a back door.

Registers R8, R9, and R10 control the volume of channels A, B, and C. Each is a 4-bit value (0-15). If you write to a volume register once per frame, you get a static volume level. But what if you write to it thousands of times per frame? What if you treat the volume register as a crude 4-bit DAC and feed it successive sample values from a digitised recording?

You get PCM playback. Crude, noisy, 4-bit, but recognisable. The AY becomes a sample player -- not by design, but by brute force.

### The Cost: CPU Annihilation

Here is the problem. To play a digitised drum sample at any reasonable quality, you need to update the volume register at audio rates. A sample rate of 8 kHz means one update every 125 microseconds. At 3.5 MHz, 125 microseconds is approximately 437 T-states. That is tight but feasible -- you can do useful work in the gaps between sample writes.

But 8 kHz sounds terrible. For a punchy kick drum, you want at least the perception of higher fidelity. And here the economics collapse. At higher effective sample rates, you need an interrupt or a tight polling loop that fires every 125-250 T-states. At that frequency, there is almost no CPU time left for anything else. While the drum sample is playing, the processor is a dedicated audio playback engine. Video generation, scripting, input handling -- everything stops.

A typical kick drum sample lasts 20-40 milliseconds for the critical attack portion. At 50 Hz, that is 1-2 frames. During those frames, the CPU is gone.

### n1k-o's Insight: The Hybrid Drum

n1k-o, the musician behind Eager's soundtrack, found the solution. The key observation: a drum sound has two distinct phases. The **attack** -- the initial transient, the sharp "click" or "thud" that gives a kick drum its punch -- is short, complex, and impossible to synthesise convincingly on the AY. But the **decay** -- the resonant tail that follows -- is a smooth volume falloff, exactly the kind of thing the AY's envelope generator handles naturally.

The hybrid approach: play the attack as a digital sample (consuming CPU time for 1-2 frames), then hand off to the AY's envelope generator for the decay (consuming zero CPU time, since the hardware does the work automatically). Digital attack plus AY decay equals a drum sound that has the realistic punch of a sample and the smooth tail of hardware synthesis.

In practice, the implementation works like this:

```z80
; Play hybrid kick drum
; 1. Start digital sample playback for attack phase
; 2. When sample ends, configure AY envelope for decay

play_kick_drum:
    di                        ; disable interrupts -- timing critical

    ; --- Digital attack phase ---
    ; Play ~800 samples at ~8kHz = ~100ms = ~2 frames
    ld   hl, kick_sample      ; pointer to 4-bit sample data
    ld   b, 0                 ; 256 samples per loop pass
    ld   c, $FD               ; low byte of AY data port ($BFFD)

    ; Select volume register R8 (channel A)
    ld   a, 8
    ld   bc, $FFFD
    out  (c), a               ; select R8
    ld   c, $FD               ; prepare for $BFFD writes

.sample_loop:
    ld   a, (hl)              ; 7 T  - load sample byte
    inc  hl                   ; 6 T  - advance pointer
    ld   b, $BF               ; 7 T  - high byte of $BFFD
    out  (c), a               ; 12 T - write volume = sample value
    ; ... timing padding to hit target sample rate ...
    djnz .sample_loop         ; 13 T (approx 45 T per sample)

    ; --- AY decay phase ---
    ; Configure envelope for smooth volume decay
    ; The AY takes over -- zero CPU cost from here

    ld   a, R_ENV_LO
    ld   e, 200               ; envelope period: moderate decay speed
    call ay_write
    ld   a, R_ENV_HI
    ld   e, 0
    call ay_write
    ld   a, R_ENV_SHAPE
    ld   e, $00               ; \___  single decay to silence
    call ay_write
    ld   a, R_VOL_A
    ld   e, $10               ; switch channel A to envelope mode
    call ay_write

    ei
    ret

kick_sample:
    ; 4-bit PCM data: attack portion of a kick drum
    ; Each byte = one sample, value 0-15
    DB 0, 2, 8, 15, 14, 12, 15, 13
    DB 10, 14, 11, 8, 12, 9, 6, 10
    ; ... (typically 400-800 bytes for the full attack)
```

The sample data itself -- those 400-800 bytes of 4-bit PCM -- comes from a real drum recording, downsampled and quantised to 4 bits. The attack transient preserves the character of the original instrument: the beater hitting the drum head, the initial compression of air, the sharp onset that our ears use to identify the sound. The AY's envelope then provides a clean, smooth decay that our ears accept as the natural resonance of the drum body.

The result is startlingly convincing. On a chip that has no sample playback capability at all, you hear something that sounds like a real kick drum. Not studio quality, not even Amiga quality, but worlds better than pure AY synthesis.

### The Frame Budget: Two Frames Per Hit

The frame cost is concrete: two frames per drum hit. During these frames, approximately 140,000 T-states (two full frame periods on Pentagon) are consumed by the sample playback loop. The CPU does nothing else. The display continues showing whatever was in screen memory, but no new frames are generated. No music data is processed (the drum IS the music for those two frames). No scripting engine runs.

Two frames at 50 Hz is 40 milliseconds. For a musical track with kick drums on the beat at 130 BPM, that is roughly one drum hit every 23 frames. Two frames out of every 23 consumed by drum playback -- about 9% of total CPU time, delivered in sharp bursts that completely monopolise the processor.

This is the architectural challenge that drives the rest of the chapter. How do you keep the visuals running smoothly when the audio steals the CPU for two frames at a time, unpredictably, dozens of times per minute?

---

## 12.2 Asynchronous Frame Generation

### The Naive Approach Fails

The simplest demo architecture is synchronous: generate one frame of the visual effect, wait for HALT (vsync), display it. Generate the next frame, HALT, display it. This is what we built in every practical exercise so far. It works perfectly when frame generation takes less than one frame period.

Now add digital drums. The music engine signals: "play kick drum on the next beat." The sample playback routine seizes the CPU for two frames. During those two frames, no new video frames are generated. When the drum finishes, the display has been showing the same frame for three refreshes (the last generated frame was shown once normally, then twice during the drum hit). The visual effect stutters.

With one drum hit every 23 frames, the audience sees a brief freeze every half-second. It is noticeable. It is ugly. It is unacceptable for a competition demo.

### Introspec's Solution: Stockpile Frames

Introspec's architecture in Eager decouples frame generation from frame display. The visual engine does not generate one frame and immediately show it. Instead, it generates frames into a buffer -- as many as it can fit -- and the display system shows them at a steady 50 Hz rate regardless of what the generator is doing.

The mechanism is double-buffered attribute frames. Two pages of attribute data exist in memory. While one page is being displayed (the ULA reads from it during the screen refresh), the generator writes the next frame into the other page. When a new frame is ready, the engine flips the pages: the newly generated frame becomes the display page, and the old display page becomes the new generation target.

```
Time ──────────────────────────────────────────────────►

Display:   [Frame 1] [Frame 2] [Frame 3] [Frame 4] [Frame 5]
Generator: ──gen F2──|──gen F3──|──gen F4──|── DRUM ──|──gen F5──
                                           ↑          ↑
                                      drum starts  drum ends

During the drum hit, the display shows Frame 4 (already generated).
Frame 5 generation resumes immediately after the drum finishes.
```

But simple double buffering only gives you one frame of slack. If the drum consumes two frames, you need to have generated two frames ahead. This is where Introspec's asynchronous generation truly diverges from simple double buffering: the engine can **stockpile** multiple frames in advance.

On the 128K Spectrum, memory banking provides the space. Attribute frames are small -- 768 bytes each. A single 16KB memory page can hold roughly 20 attribute frames. The generator runs as fast as it can, writing frame after frame into the buffer. The display system reads from the buffer at a steady 50 Hz. When the generator is faster than real time (which it usually is, since attribute plasma is cheap), the buffer fills up. When a drum hit pauses generation, the display system draws down the buffer. As long as the buffer does not run dry, the audience sees smooth 50 Hz animation.

### The Buffer Dynamics

Think of it as a producer-consumer problem, but on a machine with no concurrency.

The **producer** is the plasma/tunnel/zoomer effect generator. It produces attribute frames at a variable rate -- sometimes faster than 50 Hz (when the calculation is simple and no drums are playing), sometimes zero (during drum playback).

The **consumer** is the display system, reading one frame per screen refresh at exactly 50 Hz.

The **buffer** sits between them, absorbing the difference.

The dynamics are straightforward:

- **Between drum hits:** The generator runs faster than the display. The buffer fills up. If it reaches capacity, the generator idles (or the engine advances the scripting state).
- **During a drum hit:** The generator stops. The display drains the buffer at 50 Hz. A two-frame drum hit consumes two buffered frames.
- **After a drum hit:** The generator resumes, running as fast as possible to refill the buffer before the next hit.

The critical constraint: **the buffer must never run dry during a drum hit.** If two drum hits occur in rapid succession -- say, a kick-snare pattern two frames apart -- the buffer needs at least four frames of reserve. Introspec's scripting engine manages this by knowing the music timeline in advance. When a dense drum passage approaches, the engine generates extra frames to pad the buffer. When a quiet passage follows, the buffer naturally fills.

The catch: if the drum pattern is too dense -- too many hits too close together -- the generator cannot keep up. The buffer runs dry, and the display repeats a frame. This is a hard constraint of the architecture, and it influenced n1k-o's composition. The music was written with knowledge of the engine's capacity: drum hits are spaced far enough apart that the generator can always recover. The musician and the coder designed together, each understanding the other's constraints.

---

## 12.3 The Scripting Engine

### Why You Need a Script

By this point, the list of things that need coordination is long:

- The visual effect generator (which effect is active, what parameters it uses)
- The music player (which pattern is playing, when drums trigger)
- The frame buffer (how full it is, when to generate more)
- Transitions between effects (fade out one, fade in the next)
- The overall timeline (the demo runs for two minutes -- what happens when)

You could hardcode all of this in a monolithic main loop. Some demos do. But Introspec chose a different path: a two-level scripting system that separates *what happens* from *when it happens*.

### Outer Script: The Sequence of Effects

The outer script is a linear sequence of commands that control the overall structure of the demo. Think of it as a setlist for a concert:

```
; Outer script (conceptual, not exact syntax)
EFFECT  tunnel, params_set_1     ; start the tunnel effect
WAIT    200                       ; run for 200 frames (4 seconds)
EFFECT  zoomer, params_set_1     ; switch to chaos zoomer
WAIT    150                       ; 3 seconds
EFFECT  tunnel, params_set_2     ; tunnel again, different colours
WAIT    250                       ; 5 seconds
; ... and so on for the full demo
```

Each `EFFECT` command loads the generator function and its parameter block. Each `WAIT` tells the engine how many frames to run the current effect before advancing to the next command. Transitions between effects -- crossfades, hard cuts, colour sweeps -- are themselves scripted as effects.

### Inner Script: Variations Within an Effect

Within a single effect, parameters change over time. The tunnel's plasma frequencies shift, the colour palette rotates, the zoom speed accelerates. These variations are controlled by the inner script -- a per-effect sequence of parameter changes keyed to frame numbers:

```
; Inner script for tunnel effect (conceptual)
FRAME  0:   plasma_freq = 3, palette = warm
FRAME  50:  plasma_freq = 5                   ; frequency shift
FRAME  100: palette = cool                     ; colour change
FRAME  120: plasma_freq = 2, palette = hot     ; both change
```

The inner script runs independently of the outer script. When the outer script says "run tunnel for 200 frames," the inner script handles the visual evolution within those 200 frames.

### kWORK: The Key Command

The most important command in the scripting system is what Introspec calls **kWORK**: "generate N frames, then show them independently of generation." This single command is the bridge between the scripting system and the asynchronous architecture.

When the engine encounters `kWORK 8`, it:

1. Generates 8 frames of the current effect into the frame buffer.
2. Hands those frames to the display system.
3. While the display system shows them (over 8/50 = 160ms), the engine is free to do other work: process the next script command, prepare the next batch, or yield CPU time for drum playback.

This decoupling -- generate now, display later -- is the fundamental enabler for asynchronous operation. Without kWORK, the engine would be locked into a synchronous generate-display-generate-display cycle with no slack for drum interruptions.

In practice, the engine calls kWORK repeatedly, generating small batches of frames (4-8 at a time). Between batches, it checks whether a drum trigger is pending. If so, it lets the drum play, knowing that the display system has enough buffered frames to continue smoothly. After the drum finishes, it generates the next batch to replenish the buffer.

```z80
; Simplified engine loop (conceptual)
engine_loop:
    ; Check if drum is pending
    ld   a, (drum_pending)
    or   a
    jr   z, .no_drum
    call play_drum            ; consumes 2 frames of CPU time
    xor  a
    ld   (drum_pending), a

.no_drum:
    ; Generate a batch of frames
    call generate_batch       ; kWORK: produce N frames into buffer
    ; (generate_batch returns when batch is done)

    ; Check outer script for effect changes
    call advance_script

    jr   engine_loop
```

The beauty of this architecture is its simplicity at the macro level. The engine is a loop: check for drums, generate frames, advance the script. All the complexity is inside `generate_batch` (which manages the buffer, handles the plasma calculation, and writes attribute data) and `play_drum` (which runs the digital sample routine from section 12.1). The scripting system provides the sequencing; the buffer provides the temporal decoupling; the drum routine provides the audio impact. Each component has a clear responsibility.

---

## 12.4 GABBA's Innovation: The Video Editor as Timeline Tool

In 2019, diver4d (of 4th Dimension) took first place at CAFe with GABBA, a gabber-themed demo with punishingly tight audio-visual synchronisation. The sync was so precise that every visual hit landed exactly on the musical beat, every transition matched a phrase boundary, and the whole production felt like a music video rather than a demo.

The technical surprise was in the workflow, not the code.

### The Problem with Code-Based Sync

The traditional approach to music sync in ZX demos is to embed timing data in the code. You know that the kick drum hits at frame 47, so you write a script command that triggers the visual event at frame 47. Then you watch the demo, decide the timing is slightly off, change the number to 49, recompile, re-test, and repeat. For a two-minute demo at 50 fps, that is 6,000 frames of potential sync points. Getting them all right by trial and error takes weeks.

Introspec's Eager was built this way, and the development was gruelling. Every sync adjustment required recompilation -- assembling the Z80 code, loading the binary into an emulator, watching the relevant section, noting what was off, editing the source, and repeating. The feedback loop was measured in minutes per iteration.

### diver4d's Answer: Luma Fusion

diver4d bypassed the code-edit-compile-test cycle entirely. He used **Luma Fusion**, an iOS video editor, as his synchronisation tool.

The workflow:

1. **n1k-o composed the gabber track** with frame-level structural markers. The musician and coder worked from the same document: a timeline where every beat, every fill, every breakdown was marked with a frame number. This was not a rough tempo guide -- it was a frame-accurate map of the entire track.

2. **diver4d recorded each visual effect** running at 50 fps in an emulator and exported the recordings as video clips.

3. **In Luma Fusion**, he arranged the video clips on a 50 fps timeline alongside the audio track. He could scrub through the demo frame by frame, seeing exactly how each visual aligned with each musical event. Moving a transition was as simple as dragging a clip on the timeline.

4. **Once the timing was right in the editor**, he extracted the frame numbers for each transition and effect change, and wrote those numbers into the Z80 script data.

The insight is deceptively simple: use the right tool for the job. A video editor is purpose-built for frame-level multimedia synchronisation. Z80 assembly is not. By doing the creative synchronisation work in the editor and the implementation work in assembly, diver4d separated the artistic decisions from the engineering constraints.

### What This Changes

The immediate benefit is speed. Adjusting sync timing in a video editor takes seconds. Adjusting it in assembly takes minutes. Over hundreds of sync points, the cumulative time saving is enormous. But the deeper benefit is creative freedom. When iteration is cheap, you experiment more. You try the transition two frames early, see how it feels, try it two frames late. You notice that the visual works better hitting slightly *before* the beat (a technique borrowed from film editing, where cuts on the beat feel late because of human reaction time). You could never discover this insight through code-based iteration -- the feedback loop is too slow.

The limitation is that this workflow works best for demos where the timing is fixed -- where the demo always plays the same way. If you want interactive or generative elements that respond to runtime conditions, you need the code-based approach. But for the overwhelming majority of ZX demos, which are linear fixed-timeline productions, the video editor workflow is superior.

GABBA demonstrated that demoscene production tools do not have to be retro. The Z80 code is from 1985. The sync workflow can be from 2019. There is no contradiction.

---

## 12.5 Z80 Threading: A Different Path

Robus, writing in Hype in 2015, presented a technique that attacks the concurrency problem from a completely different angle: actual multithreading on the Z80.

### The Problem, Restated

The fundamental tension in a demo engine is that multiple tasks need CPU time in the same frame: effect generation, music playback, drum samples, scripting, transitions. Introspec's solution is cooperative: the engine manually interleaves these tasks using a scripting system and frame buffer. This works, but it requires careful manual scheduling and the entire asynchronous architecture we have been discussing.

What if the Z80 could run two tasks simultaneously?

### IM2-Based Context Switching

It can, after a fashion. The Z80's IM2 interrupt provides a natural context switch point. Every frame, the interrupt fires. If the interrupt handler saves the current task's state and loads another task's state, you have preemptive multithreading.

Robus's `SwitchThread` procedure does exactly this:

```z80
; SwitchThread: save current thread, resume next thread
; Called from within the IM2 interrupt handler
SwitchThread:
    ; Save current thread's stack pointer
    ld   (thread_sp_save), sp

    ; Save current memory page configuration
    ld   a, (current_7ffd)
    ld   (thread_page_save), a

    ; Load next thread's state
    ld   a, (next_thread_page)
    ld   (current_7ffd), a
    ld   bc, $7FFD
    out  (c), a               ; switch memory page

    ld   sp, (next_thread_sp)  ; switch stack pointer

    ; Execution continues in the next thread's context
    ; (it was previously suspended at this same point)
    ret
```

Each thread gets its own **128-byte stack** and a **dedicated memory page** (one of the 128K Spectrum's eight 16KB banks). The stack is small but sufficient -- Z80 code rarely nests deeply. The dedicated memory page gives each thread its own workspace without interfering with the other.

### How It Works in Practice

In Robus's WAYHACK demo, two threads run concurrently:

- **Thread 1:** Calculates the visual effect (a dungeon-crawling perspective renderer).
- **Thread 2:** Renders scrolling text along the bottom of the screen.

Neither thread knows about the other. Each runs in its own memory page with its own stack. Every frame, the IM2 interrupt fires and `SwitchThread` alternates between them. Thread 1 gets one frame of CPU time, then Thread 2 gets one frame, and so on.

The result: the text scroller runs at a steady 25 Hz (every other frame), and the visual effect runs at 25 Hz. Neither task needs to be aware of the other's existence. No cooperative scheduling, no yield points, no manual interleaving. The interrupt handles everything.

### The Threading Model

The model is simple:

```
Frame 1: Interrupt → save Thread 2 → restore Thread 1 → Thread 1 runs
Frame 2: Interrupt → save Thread 1 → restore Thread 2 → Thread 2 runs
Frame 3: Interrupt → save Thread 2 → restore Thread 1 → Thread 1 runs
...
```

Each thread sees a consistent world: its registers, its stack, its memory page. The switch happens at a fixed point (the interrupt), so there are no race conditions on shared data. If the threads need to communicate (e.g., Thread 1 signals Thread 2 to change the text), they do so through a shared memory location that both threads can access -- a simple flag or mailbox.

### Practical Considerations

Robus's own assessment is characteristically honest: **"Honest multithreading rarely requires more than two threads"** on the Z80. The overhead of context switching (saving and restoring SP plus a memory page switch) is modest -- perhaps 100 T-states -- but each additional thread halves the available CPU time per thread. With two threads, each gets 25 Hz. With three, each gets roughly 16.7 Hz. On a machine where visual smoothness demands close to 50 Hz, two threads is the practical limit.

The threading approach is orthogonal to Introspec's asynchronous buffering approach. You could combine them: one thread generates effect frames into a buffer while the other handles music and drum playback. In practice, this combination is rare -- the two techniques solve the same problem (interleaving CPU-hungry tasks) through different mechanisms, and most demo coders choose one or the other based on the specific demands of their production.

Threading works best when two tasks are truly independent and neither needs more than 25 Hz. The asynchronous buffer approach works best when one task (visuals) needs 50 Hz and the other (drums) needs unpredictable bursts. For Eager's architecture, where visual smoothness was paramount and drum timing was dictated by the music, the buffer approach won. For WAYHACK's architecture, where two steady-state tasks ran in parallel, threading won.

---

## 12.6 Practical: A Minimal Scripted Demo Engine

Let us build a minimal demo engine that ties together the concepts from this chapter. The goal is not Eager-level sophistication -- it is a skeleton that demonstrates the architecture.

### What We Build

- **Three simple effects:** plasma (attribute-based, from Chapter 9), colour bars (horizontal attribute stripes), and a text scroller.
- **AY music** playing via IM2 interrupt (using a .pt3 player, as described in Chapter 11).
- **A digital kick drum sample** that plays on the beat, stealing 2 frames of CPU.
- **A simple timeline script** that switches between effects at defined points.
- **Double-buffered attributes** to absorb the drum hit pauses.

### The Memory Map

```
$6000-$7FFF   Engine code + effect routines
$8000-$9FFF   Music player + song data
$A000-$AFFF   Sine tables, colour maps, sample data
$B000-$BFFF   Frame ring buffer (attribute frames)
$C000-$DFFF   Shadow screen (second display page)
$E000-$FFFF   Stack + IM2 vector table + workspace

Bank 0-3:     Not used (available for larger effects)
Bank 5:       Normal screen ($4000-$5AFF display)
Bank 7:       Shadow screen ($C000-$DAFF display)
```

### The Timeline Script

```z80
; Timeline script: sequence of (effect_id, duration_frames, param_ptr)
timeline:
    DB  EFFECT_PLASMA,   0, 150   ; plasma for 150 frames (3 sec)
    DW  plasma_params_1
    DB  EFFECT_BARS,     0, 100   ; colour bars for 100 frames (2 sec)
    DW  bars_params_1
    DB  EFFECT_SCROLLER, 0, 200   ; text scroller for 200 frames (4 sec)
    DW  scroller_params_1
    DB  EFFECT_PLASMA,   0, 150   ; plasma again, different params
    DW  plasma_params_2
    DB  $FF                        ; end marker: loop from start

EFFECT_PLASMA   EQU 0
EFFECT_BARS     EQU 1
EFFECT_SCROLLER EQU 2
```

### The Main Engine Loop

```z80
; Main engine loop
; Assumes IM2 is set up and music player runs in the ISR

engine_init:
    ; Set up display: fill pixel memory with checkerboard
    call fill_checkerboard

    ; Initialise ring buffer
    xor  a
    ld   (buf_write_idx), a
    ld   (buf_read_idx), a
    ld   (buf_count), a

    ; Load first effect from timeline
    ld   hl, timeline
    ld   (script_ptr), hl
    call load_next_effect

engine_main:
    ; === Step 1: Check for drum trigger ===
    ld   a, (drum_pending)
    or   a
    jr   z, .no_drum

    ; Play the drum -- this consumes ~2 frames
    call play_kick_drum
    xor  a
    ld   (drum_pending), a
    jr   .after_drum

.no_drum:
    ; === Step 2: Generate a frame into the buffer ===
    ld   a, (buf_count)
    cp   BUF_CAPACITY         ; buffer full?
    jr   nc, .buffer_full

    ; Generate one frame of the current effect
    call generate_frame       ; writes 768 bytes to ring buffer

    ; Advance buffer write pointer
    ld   a, (buf_write_idx)
    inc  a
    cp   BUF_CAPACITY
    jr   nz, .no_wrap_w
    xor  a
.no_wrap_w:
    ld   (buf_write_idx), a
    ld   a, (buf_count)
    inc  a
    ld   (buf_count), a

.buffer_full:
.after_drum:
    ; === Step 3: Advance timeline ===
    ld   hl, (frame_counter)
    inc  hl
    ld   (frame_counter), hl

    ; Check if current effect duration has elapsed
    ld   de, (effect_duration)
    or   a
    sbc  hl, de
    jr   c, .effect_continues

    ; Load next effect from timeline
    call load_next_effect
    ld   hl, 0
    ld   (frame_counter), hl

.effect_continues:
    ; === Step 4: Wait if we are ahead of display ===
    halt                      ; sync to frame boundary

    jr   engine_main
```

### The Display ISR

```z80
; IM2 interrupt handler: runs every frame (50 Hz)
frame_isr:
    push af
    push bc
    push de
    push hl

    ; Play music (updates AY registers)
    call music_play

    ; Check if music engine signals a drum hit
    ld   a, (music_drum_flag)
    or   a
    jr   z, .no_drum_signal
    xor  a
    ld   (music_drum_flag), a
    ld   a, 1
    ld   (drum_pending), a    ; signal main loop
.no_drum_signal:

    ; Display next frame from ring buffer
    ld   a, (buf_count)
    or   a
    jr   z, .no_frame         ; buffer empty, keep current frame

    ; Copy buffered attributes to display page
    call copy_buf_to_screen

    ; Advance read pointer
    ld   a, (buf_read_idx)
    inc  a
    cp   BUF_CAPACITY
    jr   nz, .no_wrap_r
    xor  a
.no_wrap_r:
    ld   (buf_read_idx), a
    ld   a, (buf_count)
    dec  a
    ld   (buf_count), a

.no_frame:
    pop  hl
    pop  de
    pop  bc
    pop  af
    ei
    reti

BUF_CAPACITY EQU 8           ; 8 frames of buffer (8 x 768 = 6,144 bytes)
```

### The Effect Generator Dispatch

```z80
; Generate one frame of the current effect
; Writes attribute data to the ring buffer
generate_frame:
    ld   a, (current_effect)
    or   a
    jr   z, .do_plasma
    cp   1
    jr   z, .do_bars
    cp   2
    jr   z, .do_scroller
    ret

.do_plasma:
    call calc_plasma          ; from Chapter 9 -- writes 768 bytes
    ret
.do_bars:
    call calc_colour_bars     ; horizontal attribute stripes
    ret
.do_scroller:
    call calc_text_scroll     ; text rendering into attributes
    ret
```

### Observations

This skeleton is deliberately simple. A production engine would add:

- **Inner scripts** for parameter variation within each effect.
- **Transition effects** (crossfades between two attribute buffers).
- **Multiple drum sounds** (kick, snare, hi-hat), each with its own sample data.
- **Buffer level monitoring** so the generator can prioritise catching up after dense drum passages.
- **Memory banking** to store more frames and support larger effect data.

But even in this minimal form, the architecture demonstrates the key principles:

1. **Decoupled generation and display.** The generator and the display ISR communicate only through the ring buffer. Neither knows or cares about the other's timing.

2. **Drum hits are absorbed by the buffer.** When `play_kick_drum` consumes two frames, the display ISR continues showing buffered frames. The audience sees no stutter.

3. **The script drives the timeline.** Adding a new effect or changing the sequence means editing the `timeline` data table, not restructuring the engine code.

4. **The music player runs in the ISR.** It updates AY registers every frame regardless of what the main loop is doing. The only interaction is the `drum_pending` flag -- a one-byte mailbox between the ISR and the main loop.

This is the architecture of a demo. Not the effects, not the music, not the art -- the *plumbing* that makes all of those work together. It is the least visible part of a demo and the hardest to get right. Introspec spent ten weeks on Eager, and the architecture consumed more of that time than any single effect.

---

## 12.7 Practical Exercises

**Exercise 1: Basic Engine.** Implement the skeleton above with a single effect (plasma from Chapter 9) and no drum samples. Verify that the ring buffer works correctly: the display shows smooth animation while the generator runs at its natural speed.

**Exercise 2: Add the Drum.** Record (or synthesise) a 4-bit kick drum sample (400-800 bytes). Add the `play_kick_drum` routine and trigger it every 25 frames. Verify that the display remains smooth during drum playback. What is the maximum drum rate before the buffer runs dry?

**Exercise 3: Multi-Effect Timeline.** Add a second effect (colour bars or text scroller). Write a timeline script that switches between effects every 3-4 seconds. Verify that transitions happen at the correct frame.

**Exercise 4: Sync to Music.** Load a short .pt3 tune and modify the player to set `music_drum_flag` when a particular pattern event occurs (e.g., a note on channel C below a certain pitch). Now the drums are driven by the music, not by a fixed frame counter. This is real music sync.

**Exercise 5: Video Editor Workflow.** Record your running demo in an emulator at 50 fps. Import the recording into a video editor (any editor that supports frame-level editing). Adjust the timeline script frame numbers based on what you see in the editor. Experience the difference in iteration speed compared to code-only sync.

---

## Summary

This chapter was not about any single effect or technique. It was about architecture -- the invisible structure that lets a demo exist as a coherent, synchronised, two-minute performance rather than a collection of disjointed screens.

The core problems are universal. Every demo engine must answer: How do I share the CPU between audio and video? How do I keep the display smooth when the audio steals processing time? How do I sequence effects and synchronise them to music? How do I manage the timeline of a multi-minute production?

The solutions we examined are complementary:

- **Digital drums** (n1k-o/Introspec) exploit the AY's volume registers as a crude DAC, blending digital samples with hardware synthesis to produce percussion that transcends the chip's designed capabilities.
- **Asynchronous frame generation** (Introspec) decouples video production from display through a ring buffer, absorbing the CPU bursts consumed by drum playback.
- **Scripted timelines** (Introspec) separate the *what* and *when* of a demo from the *how*, making it possible to design and adjust a two-minute production without restructuring the engine.
- **Video editor sync** (diver4d) moves the creative timing work to a tool purpose-built for it, dramatically accelerating the sync iteration cycle.
- **Z80 threading** (Robus) provides genuine concurrency for tasks that are independent and steady-state, at the cost of halving the frame rate for each task.

With this chapter, we close the circle on the demoscene section of the book. We have built effects (Parts I-II), made sound (Chapter 11), and now wired everything into a running engine. The reader who has followed from Chapter 1 has a complete picture: from T-state counting to a synchronised, scripted demo with digital drums.

In the next chapter, we shift gears entirely. Part IV takes us into size-coding -- the art of fitting an entire production into 256 bytes. The architecture goes from "how do I manage a ring buffer?" to "how do I make every single byte do double duty?" The constraints tighten by three orders of magnitude, and the thinking changes to match.

---

> **Sources:** Introspec, "Making of Eager," Hype, 2015 (hype.retroscene.org/blog/demo/261.html); Introspec, file_id.diz from Eager (to live), 3BM Open Air 2015; diver4d, "Making of GABBA," Hype, 2019 (hype.retroscene.org/blog/demo/948.html); Robus, "Threads on Z80," Hype, 2015 (hype.retroscene.org/blog/dev/271.html); Eager source code excerpts courtesy of Introspec (Life on Mars)
