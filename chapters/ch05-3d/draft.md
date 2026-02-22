# Chapter 5: 3D on 3.5 MHz

> *"Calculate only what you must. Derive the rest."*
> --- Dark & STS, Spectrum Expert #02 (1998)

The previous chapter gave you the building blocks: multiplication, division, sine tables, line drawing. Now we put them together. The goal is a spinning three-dimensional solid object on a ZX Spectrum --- filled polygons, backface culling, correct depth ordering --- at a usable frame rate.

This is where you hit the wall.

---

## The Problem: Twelve Multiplications Per Vertex

Rotating a point in three-dimensional space around all three axes requires a sequence of trigonometric multiplications. If you rotate sequentially --- first around Z, then Y, then X --- each axis involves four multiplications and two additions to transform two coordinates. Three axes, four multiplications each: twelve multiplications per vertex.

Take the shift-and-add multiply from Chapter 4, which costs roughly 200 T-states. Twelve of those give you 2,400 T-states to rotate a single vertex. A simple cube has 8 vertices: 19,200 T-states just for rotation. Chapter 4 showed that this fits in the frame budget --- barely.

Now try something more interesting. A sphere approximated by 20 vertices and 36 faces:

```
20 vertices x 2,400 T-states = 48,000 T-states
```

That is 67% of the Pentagon's 71,680 T-state frame budget, consumed before you have drawn a single pixel. You still need perspective projection, backface culling, polygon sorting, and the actual fill. There is no room. The object cannot be more complex than a cube unless you find a fundamentally cheaper way to compute vertex positions.

Dark and STS found one.

---

## The Midpoint Method

The insight is geometric. Not every vertex in an object carries independent information. Many vertices sit at structurally predictable positions --- midpoints of edges, centers of faces, reflections of other vertices. If you can express those relationships explicitly, you can replace expensive multiplications with cheap averages.

### The Cube as Foundation

Consider a cube centered at the origin. It has 8 vertices, but they are not 8 independent points. They are 4 pairs of diametrically opposite vertices. If you know one vertex of a pair, the other is its negation through the center:

```
v0 = ( x,  y,  z)    →    v7 = (-x, -y, -z)
v1 = ( x,  y, -z)    →    v6 = (-x, -y,  z)
v2 = ( x, -y,  z)    →    v5 = (-x,  y, -z)
v3 = ( x, -y, -z)    →    v4 = (-x,  y,  z)
```

Rotate 4 vertices using the full 12-multiplication procedure. Negate them to get the other 4. Negation on the Z80 is `NEG` --- 8 T-states for one coordinate, 24 T-states for all three. Compare that to 2,400 T-states for a full rotation. You have cut the vertex computation nearly in half.

But the midpoint method goes much further than mirroring.

### Deriving Vertices by Averaging

The key operation is the average: given two already-computed points, their midpoint is simply the mean of their coordinates.

```
v_new = (v_a + v_b) / 2
```

On the Z80, this is an addition and a shift:

```z80
; Average two signed 8-bit coordinates
; A = first coordinate, B = second coordinate
; Result in A = (A + B) / 2

    add  a, b           ;  4 T-states
    sra  a              ;  8 T-states
                        ; ----
                        ; 12 T-states total
```

`SRA` (Shift Right Arithmetic) preserves the sign bit, so this works correctly for negative coordinates. For all three coordinates (x, y, z), averaging costs 36 T-states per derived vertex. Compare that to 2,400 T-states for a full rotation.

The ratio is staggering: averaging is **66 times cheaper** than rotation.

This means you can build complex objects from a small set of "basis" vertices that you rotate fully, then derive all remaining vertices through chains of averages. The more vertices you can derive, the more time you save.

### Building Complex Objects

Suppose you want a 20-vertex object. With the midpoint method:

1. Rotate 4 basis vertices fully: 4 x 2,400 = 9,600 T-states
2. Mirror 4 vertices by negation: 4 x 24 = 96 T-states
3. Derive 12 vertices by averaging: 12 x 36 = 432 T-states
4. **Total: 10,128 T-states**

Without the midpoint method, the same 20 vertices would cost 48,000 T-states. You have saved 37,872 T-states --- more than half the frame budget freed up for projection, culling, and rendering.

The constraint is topological: you can only derive a vertex by averaging if it genuinely lies at the midpoint of two other vertices (or close enough that the error is invisible at 256x192 resolution). This shapes how you design your 3D models. You do not model freely and then optimize --- you design the model *around* the midpoint structure from the start.

Dark and STS give examples of the derivation chains:

```
v8  = (v4 + v5) / 2
v9  = (v3 + v7) / 2
v10 = (v2 + v6) / 2
v11 = (v8 + v9) / 2     ; derived from two already-derived vertices
```

Notice that v11 is derived from v8 and v9, which are themselves derived. Chains can go several levels deep. Each level adds only 36 T-states per vertex, so the cost stays negligible regardless of depth.

---

## The Virtual Processor

Here is where Dark does something that feels anachronistic for 1998. Rather than hardcoding the derivation chains for each specific object, he designs a tiny interpreter --- a virtual processor --- that executes "programs" describing how to compute vertices.

### Architecture

The virtual processor has:

- **One register** (a working register holding one 3D point --- three bytes: x, y, z)
- **64 cells of RAM** (each cell holds one 3D point --- 192 bytes total)
- **4 instructions**

| Opcode | Bits | Name | Operation |
|--------|------|------|-----------|
| 00 | `00nnnnnn` | **Load** | register <-- cell[n] |
| 01 | `01nnnnnn` | **Store** | cell[n] <-- register |
| 10 | `10nnnnnn` | **Average** | register <-- (register + cell[n]) / 2 |
| 11 | `11------` | **End** | halt execution |

Each instruction is encoded in a single byte: 2 bits for the opcode, 6 bits for the cell number (0--63). The entire instruction set fits in 256 possible values.

### Execution

The interpreter loop is remarkably compact:

```z80
; Virtual processor main loop
; IX points to the program (sequence of 1-byte instructions)
; Point RAM at a fixed address, 3 bytes per cell

vp_loop:
    ld   a, (ix+0)        ; fetch instruction
    inc  ix
    ld   b, a             ; save full instruction
    and  %11000000        ; extract opcode (top 2 bits)

    cp   %11000000        ; END?
    ret  z                ; yes — halt

    ld   a, b
    and  %00111111        ; extract cell number (bottom 6 bits)
    ; ... compute cell address from cell number ...
    ; ... dispatch based on opcode ...

    jr   vp_loop
```

The **Load** instruction copies a cell's x, y, z values into the working register. **Store** copies the working register back into a cell. **Average** adds the cell's coordinates to the working register and shifts each result right by one --- the midpoint operation. **End** terminates the program.

### Writing Programs

A vertex derivation chain becomes a simple sequence of bytes. Dark uses a compact notation in the article:

```z80
; Example: derive v8 = (v4 + v5) / 2, then store it
; Cell 4 = v4, Cell 5 = v5, Cell 8 = destination

    DB  4           ; LOAD cell[4]     (opcode 00, cell 4)
    DB  128+5       ; AVG  cell[5]     (opcode 10, cell 5 = %10000101)
    DB  64+8        ; STORE cell[8]    (opcode 01, cell 8 = %01001000)
```

The notation `128+5` encodes `%10000101` --- opcode 10 (Average) with cell number 5. `64+8` encodes `%01001000` --- opcode 01 (Store) with cell number 8. Raw numbers, packed into data bytes, forming a tiny domain-specific program.

A complete object description might look like:

```z80
; Midpoint program for a 12-vertex object
; Cells 0-3: basis vertices (rotated by main code)
; Cells 4-7: mirrored vertices (negated by main code)
; Cells 8-11: derived via midpoint averaging

midpoint_program:
    DB  0               ; LOAD v0
    DB  128+1           ; AVG  v1           -> register = (v0+v1)/2
    DB  64+8            ; STORE v8

    DB  2               ; LOAD v2
    DB  128+3           ; AVG  v3           -> register = (v2+v3)/2
    DB  64+9            ; STORE v9

    DB  4               ; LOAD v4
    DB  128+5           ; AVG  v5           -> register = (v4+v5)/2
    DB  64+10           ; STORE v10

    DB  6               ; LOAD v6
    DB  128+7           ; AVG  v7           -> register = (v6+v7)/2
    DB  64+11           ; STORE v11

    DB  192             ; END               (%11000000)
```

Thirteen bytes describe the computation of four derived vertices. The virtual processor executes them in roughly 13 x 30 = 390 T-states (each instruction takes approximately 25--35 T-states depending on type). Four fully rotated vertices would have cost 9,600 T-states. The savings are enormous.

### Why a Virtual Processor?

You might ask: why not just write the averaging code directly in Z80 assembly? Inline the additions and shifts, skip the interpreter overhead. It would be slightly faster per vertex.

The answer is flexibility. The virtual processor separates the *description* of an object's topology from the *execution* of the vertex computation. Change the object? Write a new program --- a new sequence of data bytes. The interpreter code stays the same. You can store programs for multiple objects and switch between them at zero code cost. You can even generate programs algorithmically.

This is, in essence, a domain-specific bytecode interpreter --- a pattern that modern programmers would recognize from game engines, shader compilers, and scripting languages. Dark designed it in 1998, on a ZX Spectrum, to save T-states on vertex computation. The architecture is remarkably clean.

---

## Rotation

With the midpoint method handling most vertices, you still need to rotate the basis vertices properly. Dark and STS use sequential rotation around the three axes, applied in order: Z, then Y, then X. Each rotation uses the sine and cosine tables from Chapter 4.

### Z-Axis Rotation

Rotation around Z affects only X and Y:

```
X' = X * cos(Az) + Y * sin(Az)
Y' = -X * sin(Az) + Y * cos(Az)
```

In Z80 assembly, using the 8x8 signed multiply and 256-entry sine/cosine tables:

```z80
; Rotate point around Z axis
; Input:  (px), (py) = coordinates; (angle_z) = rotation angle
; Output: (px), (py) updated
; Uses:   cos_table, sin_table (page-aligned, signed 8-bit)

rotate_z:
    ld   a, (angle_z)
    ld   l, a
    ld   h, cos_table >> 8
    ld   d, (hl)            ; D = cos(Az)
    ld   h, sin_table >> 8
    ld   e, (hl)            ; E = sin(Az)

    ; X' = X*cos(Az) + Y*sin(Az)
    ld   a, (px)
    ld   b, a
    ld   c, d               ; B=X, C=cos
    call mul_signed          ; HL = X * cos(Az)
    push hl

    ld   a, (py)
    ld   b, a
    ld   c, e               ; B=Y, C=sin
    call mul_signed          ; HL = Y * sin(Az)
    pop  de
    add  hl, de             ; HL = X*cos + Y*sin
    ld   a, h               ; take high byte as new X'
    ld   (px), a

    ; Y' = -X*sin(Az) + Y*cos(Az)
    ld   a, (px_original)   ; need the original X, not the updated one
    neg
    ld   b, a
    ld   c, e               ; B=-X, C=sin
    call mul_signed          ; HL = -X * sin(Az)
    push hl

    ld   a, (py)
    ld   b, a
    ld   c, d               ; B=Y, C=cos
    call mul_signed          ; HL = Y * cos(Az)
    pop  de
    add  hl, de             ; HL = -X*sin + Y*cos
    ld   a, h
    ld   (py), a

    ret
```

The same pattern repeats for Y-axis rotation (affecting X and Z) and X-axis rotation (affecting Y and Z). Dark wraps all three into a single `ROTATE` procedure that takes three angle parameters and transforms a point in place.

Note the detail about preserving the original X value. The second formula uses the pre-rotation X, not the X' you just computed. A common bug is to use the already-updated coordinate, which produces a skewed rotation. Dark addresses this explicitly in the article.

### Cost Per Basis Vertex

Each axis rotation requires 4 multiplications and 2 additions. At 200 T-states per multiply and 11 T-states per 16-bit add:

```
Per axis:  4 x 200 + 2 x 11 = 822 T-states
Three axes: 3 x 822 = 2,466 T-states per vertex
```

With 4 basis vertices: roughly 9,864 T-states for rotation. Add the midpoint program execution and you have the full vertex computation for an arbitrarily complex object at a fraction of the naive cost.

---

## Projection

Once all vertices are rotated in 3D space, you need to project them onto the 2D screen.

### Parallel Projection

The simplest approach: ignore the Z coordinate entirely. Just use X and Y as screen coordinates (with appropriate offset to center the object on screen).

```z80
; Parallel projection: screen coords = rotated X, Y + offset
    ld   a, (px)
    add  a, 128             ; center horizontally (128 = half of 256)
    ld   (screen_x), a

    ld   a, (py)
    add  a, 96              ; center vertically (96 = half of 192)
    ld   (screen_y), a
```

Cost: essentially zero. The result looks flat --- objects do not appear to recede into the distance. Parallel projection is useful for wireframe previews and effects where the rotation itself provides the illusion of depth, but it lacks the visceral punch of perspective.

### Perspective Projection

Perspective makes near objects larger and far objects smaller, producing the depth cue that makes 3D convincing:

```
Xscreen = (X * Scale) / (Z + Zdistance) + Xoffset
Yscreen = (Y * Scale) / (Z + Zdistance) + Yoffset
```

`Scale` controls the field of view. `Zdistance` is the distance from the camera to the projection plane --- it prevents division by zero when Z approaches the camera and controls how aggressively objects scale with depth. `Xoffset` and `Yoffset` center the projection on screen.

The expensive operation here is the division. One divide per coordinate, two coordinates per vertex. Using the logarithmic division from Chapter 4 (~60 T-states per divide), the cost is modest:

```z80
; Perspective projection for one vertex
; Input:  (px), (py), (pz) = rotated 3D coordinates
; Output: (screen_x), (screen_y)

perspective:
    ; Compute denominator: Z + Zdistance
    ld   a, (pz)
    add  a, ZDISTANCE       ; Z + viewing distance
    ld   c, a               ; C = denominator

    ; Xscreen = (X * Scale) / (Z + Zdist) + Xoffset
    ld   a, (px)
    ld   b, SCALE
    call mul_signed          ; HL = X * Scale
    ld   a, h               ; take high byte as numerator
    call log_divide          ; A = A / C (using log tables)
    add  a, XOFFSET
    ld   (screen_x), a

    ; Yscreen = (Y * Scale) / (Z + Zdist) + Yoffset
    ld   a, (py)
    ld   b, SCALE
    call mul_signed          ; HL = Y * Scale
    ld   a, h
    call log_divide          ; A = A / C
    add  a, YOFFSET
    ld   (screen_y), a

    ret
```

Each vertex costs two multiplications (400 T-states) and two log divides (120 T-states), plus overhead --- roughly 600 T-states per vertex. For 20 vertices: 12,000 T-states. Combined with the midpoint rotation, we are at roughly 22,000 T-states for all vertex computation and projection. Less than a third of the frame budget.

---

## Solid Polygons

A wireframe object is a collection of edges. A solid object is a collection of filled polygons. Going from wire to solid requires three additional capabilities: determining which faces are visible, sorting them by depth, and filling them with pixels.

### Backface Culling

A closed 3D object has faces that point toward the viewer and faces that point away. The back-facing polygons are hidden and need not be drawn. Skipping them saves both rendering time and produces a correct solid appearance without requiring a full depth buffer.

The test is geometric. For each face, compute the Z-component of the surface normal using the cross product of two edge vectors:

```
Given three vertices of a face: v0, v1, v2

Edge vectors:
    V = v1 - v0 = (Vx, Vy)    (in screen coordinates)
    W = v2 - v0 = (Wx, Wy)

Z-component of normal = Vx * Wy - Vy * Wx
```

If the result is positive, the face is oriented toward the viewer and should be drawn. If negative, the face points away --- cull it. If zero, the face is edge-on and invisible.

```z80
; Backface culling test for one face
; Input: three projected vertices (x0,y0), (x1,y1), (x2,y2)
; Output: carry flag set if face is back-facing (should be culled)

backface_test:
    ; V = v1 - v0
    ld   a, (x1)
    sub  (ix+x0)
    ld   d, a               ; D = Vx = x1 - x0

    ld   a, (y1)
    sub  (ix+y0)
    ld   e, a               ; E = Vy = y1 - y0

    ; W = v2 - v0
    ld   a, (x2)
    sub  (ix+x0)
    ld   b, a               ; B = Wx = x2 - x0

    ld   a, (y2)
    sub  (ix+y0)
    ld   c, a               ; C = Wy = y2 - y0

    ; Normal Z = Vx * Wy - Vy * Wx
    ld   a, d
    call mul_signed_c        ; HL = Vx * Wy (D * C)
    push hl

    ld   a, e
    ld   c, b
    call mul_signed_c        ; HL = Vy * Wx (E * B)

    pop  de
    ex   de, hl
    or   a
    sbc  hl, de             ; HL = Vx*Wy - Vy*Wx

    bit  7, h               ; check sign
    ret                     ; carry/sign indicates facing
```

Two multiplications and a subtraction per face. At 400 T-states for the multiplies plus overhead, the test costs roughly 500 T-states per face. For a 12-face object, that is 6,000 T-states --- and for each culled face, you save the entire cost of filling it.

On a typical rotating solid, roughly half the faces are back-facing at any time. Culling them halves your fill workload.

### Z-Sorting

For a convex object (a cube, a tetrahedron), backface culling alone produces correct results: every visible face is fully visible, with no overlapping. For concave or multi-object scenes, you need to draw faces in back-to-front order so that nearer faces overwrite farther ones --- the painter's algorithm.

Dark and STS compute a depth value for each visible face (typically the average Z of its vertices) and sort the face list accordingly. A simple insertion sort is adequate for the small face counts involved --- sorting 6--12 faces takes negligible time compared to filling them.

```z80
; Simplified depth sort: compute average Z for each visible face,
; sort face indices by descending Z (farthest first)

sort_faces:
    ; For each visible face:
    ;   average_z = (z[v0] + z[v1] + z[v2] + z[v3]) / 4
    ;   store (average_z, face_index) in sort buffer
    ; Then insertion-sort the buffer by average_z
    ; ...
```

### Convex Polygon Filling

Once you know which faces to draw and in what order, you need to fill them. A convex polygon (all interior angles less than 180 degrees) can be filled with a simple scanline approach:

1. Find the topmost and bottommost vertices.
2. Walk down the left edge and the right edge simultaneously, one scanline at a time.
3. For each scanline, draw a horizontal line from the left edge to the right edge.

The edge-walking uses Bresenham-style incremental stepping --- no division needed per scanline, just additions and conditional increments. The horizontal fill itself is a tight loop of byte writes:

```z80
; Fill one scan line from x_left to x_right at screen row Y
; Screen address already computed in HL

fill_scanline:
    ld   a, (x_right)
    sub  (ix+x_left)
    ret  c                  ; nothing to fill if right < left
    ret  z
    ld   b, a               ; B = pixel count

    ; For byte-aligned fills: write whole bytes
    ld   a, $FF             ; solid fill
.fill_loop:
    ld   (hl), a
    inc  l                  ; next byte (within same screen line)
    djnz .fill_loop
    ret
```

This is simplified --- real polygon fillers must handle partial bytes at the left and right edges, where the polygon boundary falls within a byte rather than on a byte boundary. Those edge cases add complexity but not much cost, since they occur only twice per scanline.

---

## Putting It All Together

The complete frame loop for a spinning 3D solid object follows this sequence:

```
1. Update rotation angles (Az, Ay, Ax)
2. For each basis vertex:
     Rotate through Z, Y, X axes         [~2,400 T per vertex]
3. Negate basis vertices to get mirrors   [~24 T per vertex]
4. Run midpoint program to derive rest    [~36 T per derived vertex]
5. Project all vertices (perspective)     [~600 T per vertex]
6. For each face:
     Backface test                        [~500 T per face]
     If visible: compute average Z
7. Sort visible faces by Z               [~200 T for small lists]
8. For each visible face (back to front):
     Fill polygon                         [varies with area]
9. Wait for next frame (HALT)
```

For a 20-vertex, 18-face object with 4 basis vertices, the per-frame budget breaks down as:

| Stage | Vertices/Faces | Cost per | Total |
|-------|---------------|----------|-------|
| Rotation (basis) | 4 | 2,466 | 9,864 |
| Negation (mirrors) | 4 | 24 | 96 |
| Midpoint derivation | 12 | 36 | 432 |
| Projection | 20 | 600 | 12,000 |
| Backface test | 18 | 500 | 9,000 |
| Z-sort | ~9 visible | - | ~200 |
| Polygon fill | ~9 visible | ~1,500 avg | ~13,500 |
| **Total** | | | **~45,092** |

Forty-five thousand T-states out of 71,680 available. Tight, but workable --- you have 26,000 T-states remaining for screen clearing, angle updates, and the line drawing or edge-highlighting that makes the object look crisp. And this is for a 20-vertex object, far more complex than anything you could afford with naive rotation.

---

## The Shape of Objects

The midpoint method influences how you think about 3D models. You do not design a mesh and then optimize it --- you start from the topology that the method requires.

A good midpoint object begins with a small basis. Four fully rotated points define a tetrahedron-like skeleton. Negation doubles that to eight. Midpoint averaging fills in the rest. The art is choosing basis vertices that produce useful derived points.

Consider building a 14-vertex object from scratch:

```
Basis:    v0, v1, v2, v3         (4 fully rotated)
Mirrors:  v4, v5, v6, v7         (4 negated)
Derived:
  v8  = (v0 + v1) / 2           edge midpoint
  v9  = (v2 + v3) / 2           edge midpoint
  v10 = (v4 + v5) / 2           edge midpoint on mirrored side
  v11 = (v6 + v7) / 2           edge midpoint on mirrored side
  v12 = (v0 + v2) / 2           cross-edge midpoint
  v13 = (v8 + v10) / 2          second-level derivation
```

The virtual processor program for this is 19 bytes:

```z80
object_14v_program:
    DB  0, 128+1, 64+8      ; v8  = avg(v0, v1)
    DB  2, 128+3, 64+9      ; v9  = avg(v2, v3)
    DB  4, 128+5, 64+10     ; v10 = avg(v4, v5)
    DB  6, 128+7, 64+11     ; v11 = avg(v6, v7)
    DB  0, 128+2, 64+12     ; v12 = avg(v0, v2)
    DB  8, 128+10, 64+13    ; v13 = avg(v8, v10)
    DB  192                  ; END
```

Nineteen bytes of data replace what would otherwise be 14,400 T-states of rotation multiplications for the 6 derived vertices.

You can push this further. A second level of averaging (deriving from already-derived points) costs nothing extra per instruction --- the virtual processor does not care whether a cell holds a rotated or a derived point. Dark and STS describe chains three or four levels deep, building objects with 30 or more vertices from just 3--4 basis points.

The constraint is precision. Each averaging step introduces a rounding error of up to 0.5 units (from the integer shift). After three levels of derivation, the cumulative error can reach 1.5 units --- noticeable on an object that spans 60 pixels, invisible on one that spans 120. Design your objects large enough that the rounding is below the screen resolution.

---

## Practical: A Spinning Solid Object

Here is the outline for building a complete spinning 3D solid using everything in this chapter.

### Step 1: Define the Object

Start with basis vertices. A truncated octahedron works well with the midpoint method:

```z80
; 4 basis vertices in signed 8-bit coordinates
basis_vertices:
    DB   30,   0,  30     ; v0 (x, y, z)
    DB    0,  30,  30     ; v1
    DB   30,  30,   0     ; v2
    DB    0,   0,   0     ; v3 (at origin for center reference)
```

### Step 2: Write the Midpoint Program

```z80
midpoint_prog:
    ; Mirrors: cells 4-7 are pre-negated by the main loop
    ; Derive additional vertices:
    DB  0, 128+1, 64+8        ; v8  = avg(v0, v1)
    DB  2, 128+3, 64+9        ; v9  = avg(v2, v3)
    DB  0, 128+2, 64+10       ; v10 = avg(v0, v2)
    DB  1, 128+3, 64+11       ; v11 = avg(v1, v3)
    DB  192                    ; END
```

### Step 3: Define Faces

```z80
; Face table: each face is a list of vertex indices + attribute byte
; Vertex order must be consistent (clockwise when front-facing)
face_table:
    DB  4, 0, 1, 8, 10        ; face 0: quad (4 vertices)
    DB  4, 2, 3, 9, 11        ; face 1: quad
    ; ... remaining faces ...
    DB  0                      ; end marker
```

### Step 4: The Frame Loop

```z80
main_loop:
    halt                       ; wait for vsync (IM1)

    ; Clear the screen area (or use double buffering)
    call clear_viewport

    ; Update angles
    ld   hl, angle_z
    inc  (hl)
    ld   hl, angle_x
    ld   a, (hl)
    add  a, 2
    ld   (hl), a

    ; Rotate basis vertices
    ld   b, 4                  ; 4 basis vertices
    ld   ix, basis_vertices
    ld   iy, point_ram         ; cell 0 onwards
.rotate_basis:
    push bc
    call rotate_xyz            ; rotate point at (IX) by current angles
                               ; store result at (IY)
    ld   bc, 3
    add  ix, bc
    add  iy, bc
    pop  bc
    djnz .rotate_basis

    ; Negate for mirrors (cells 4-7 = negation of cells 0-3)
    call negate_basis

    ; Run midpoint program
    ld   ix, midpoint_prog
    call virtual_processor

    ; Project all vertices
    call project_all

    ; Backface cull and sort
    call cull_and_sort

    ; Draw visible faces
    call draw_faces

    jr   main_loop
```

This is the skeleton. Each `call` hides a procedure built from the techniques in this chapter and Chapter 4. The frame loop itself is clean --- update, compute, draw, repeat.

---

## Historical Context: From Magazine to Demo

Dark and STS published the midpoint method in Spectrum Expert #02 in 1998. They were young coders in St. Petersburg, writing for a disk magazine distributed within the Russian ZX Spectrum community. The articles are written in the direct, practical style of people teaching their peers --- here is the problem, here is the trick, here is the code.

But Spectrum Expert was not an academic exercise. Dark was from X-Trade, the same group that produced *Illusion* --- the demo that won first place at ENLiGHT'96. The algorithms in the magazine are not theoretical proposals; they are the building blocks of real, competition-winning demo code. The sine tables from Chapter 4 drove the rotozoomer. The line drawer rendered the wireframes. And the midpoint method powered the 3D objects.

The virtual processor approach is particularly striking in retrospect. In 1998, the dominant paradigms in professional game development were shifting toward hardware acceleration and away from software rendering. On the Spectrum, hardware acceleration did not exist. Everything was software, and software had to be *designed* --- not just written, but architected. Dark's bytecode interpreter for vertex computation is a piece of software architecture that would not feel out of place in a modern game engine's animation system or shader compiler. It separates data from execution, enables rapid iteration on object design, and keeps the hot loop tight.

The connection to *Illusion* runs deeper than shared authorship. When Introspec disassembled *Illusion* twenty years later, he found the exact same mathematical infrastructure: the shift-and-add multiplier, the parabolic sine table, the log-table divider. The midpoint method and the virtual processor are extensions of that infrastructure --- the same thinking applied to a different problem. Dark was not just publishing algorithms; he was documenting the engineering philosophy behind his own award-winning demo.

In the next chapter, we will see one of *Illusion*'s most spectacular effects up close: the texture-mapped sphere. It uses the same sine tables and the same fixed-point arithmetic from Chapter 4, combined with the self-modifying code techniques from Chapter 3 and a completely different approach to the rendering problem. The midpoint method and the sphere are siblings --- born from the same coder, the same tools, the same relentless drive to make the impossible fit inside 71,680 T-states.

---

## Summary

- Rotating 3D objects naively requires 12 multiplications per vertex --- too expensive for complex objects on a 3.5 MHz Z80.
- The **midpoint method** rotates only a few basis vertices fully, then derives the rest through averaging. Averaging costs ~36 T-states per vertex versus ~2,400 for full rotation --- 66 times cheaper.
- A **virtual processor** with 4 instructions (Load, Store, Average, End) executes compact "programs" that describe vertex derivation chains. Object topology is data, not code.
- **Rotation** uses sequential Z/Y/X axis transforms with sine/cosine lookup tables from Chapter 4.
- **Perspective projection** uses the logarithmic division from Chapter 4 for the Z-divide.
- **Backface culling** via cross-product normal test eliminates invisible faces at ~500 T-states each.
- **Z-sorting** with the painter's algorithm handles overlapping faces for non-convex objects.
- A 20-vertex solid object can be rendered in ~45,000 T-states per frame --- tight but feasible within the 71,680 T-state budget.
- These techniques were published in Spectrum Expert #02 (1998) by the same team that built *Illusion*. The magazine articles document the engineering behind the demo.

---

*All cycle counts in this chapter are for Pentagon timing (no wait states). On a standard 48K Spectrum with contended memory, expect higher counts for code executing in the lower 32K of RAM. See Appendix A for the complete timing reference.*

> **Sources:** Dark & STS, "Programming: 3D Graphics" (Spectrum Expert #01, 1997); Dark & STS, "Programming: 3D Graphics --- Midpoint Method" (Spectrum Expert #02, 1998). The virtual processor design and midpoint derivation examples are drawn directly from the SE#02 article.
