// zx_screen.js — ZX Spectrum screen emulator for verifying Z80 effects
// 256×192 pixels, 32×24 attribute grid, authentic memory layout

const ZX_COLORS = [
    // normal                    // bright
    '#000000', '#0000CD', '#CD0000', '#CD00CD',  // black, blue, red, magenta
    '#00CD00', '#00CDCD', '#CDCD00', '#CDCDCD',  // green, cyan, yellow, white
    '#000000', '#0000FF', '#FF0000', '#FF00FF',   // bright variants
    '#00FF00', '#00FFFF', '#FFFF00', '#FFFFFF',
];

class ZXScreen {
    constructor(canvas, scale = 3) {
        this.canvas = canvas;
        this.scale = scale;
        canvas.width = 256 * scale;
        canvas.height = 192 * scale;
        this.ctx = canvas.getContext('2d');
        this.ctx.imageSmoothingEnabled = false;

        // ZX Spectrum memory: 6144 bytes pixel data + 768 bytes attributes
        this.pixels = new Uint8Array(6912);
        this.frameCount = 0;

        // ImageData for efficient rendering
        this.imgData = this.ctx.createImageData(256, 192);
    }

    // --- Memory access (authentic ZX Spectrum layout) ---

    // Convert (x, y) to screen memory offset (0..6143)
    screenAddr(x, y) {
        // H = 010 Y7Y6 Y2Y1Y0, L = Y5Y4Y3 X4X3X2X1X0
        const h = 0x40 | ((y & 0xC0) >> 3) | (y & 0x07);
        const l = ((y & 0x38) << 2) | (x >> 3);
        return ((h - 0x40) << 8) | l;
    }

    // Convert (col, row) to attribute offset (6144..6911)
    attrAddr(col, row) {
        return 6144 + row * 32 + col;
    }

    // Write to screen memory (offset 0..6911)
    poke(addr, val) {
        this.pixels[addr] = val & 0xFF;
    }

    // Read from screen memory
    peek(addr) {
        return this.pixels[addr];
    }

    // --- High-level pixel ops ---

    setPixel(x, y) {
        if (x < 0 || x > 255 || y < 0 || y > 191) return;
        const addr = this.screenAddr(x, y);
        const bit = 0x80 >> (x & 7);
        this.pixels[addr] |= bit;
    }

    clearPixel(x, y) {
        if (x < 0 || x > 255 || y < 0 || y > 191) return;
        const addr = this.screenAddr(x, y);
        const bit = 0x80 >> (x & 7);
        this.pixels[addr] &= ~bit;
    }

    getPixel(x, y) {
        if (x < 0 || x > 255 || y < 0 || y > 191) return 0;
        const addr = this.screenAddr(x, y);
        const bit = 0x80 >> (x & 7);
        return (this.pixels[addr] & bit) ? 1 : 0;
    }

    // --- Attribute ops ---

    setAttr(col, row, attr) {
        this.pixels[6144 + row * 32 + col] = attr & 0xFF;
    }

    // Make attribute byte: flash, bright, paper (0-7), ink (0-7)
    static makeAttr(ink, paper, bright = 0, flash = 0) {
        return (flash ? 0x80 : 0) | (bright ? 0x40 : 0) | ((paper & 7) << 3) | (ink & 7);
    }

    // --- Bulk ops ---

    clearScreen() {
        this.pixels.fill(0);
    }

    fillAttrs(attr) {
        for (let i = 6144; i < 6912; i++) this.pixels[i] = attr;
    }

    // --- Rendering ---

    render() {
        const data = this.imgData.data;
        const flash = (this.frameCount & 0x20) !== 0; // flash toggles every 32 frames

        for (let y = 0; y < 192; y++) {
            const row = y >> 3;
            for (let col = 0; col < 32; col++) {
                const pixelByte = this.pixels[this.screenAddr(col * 8, y)];
                const attr = this.pixels[6144 + row * 32 + col];

                const bright = (attr & 0x40) ? 8 : 0;
                let ink = (attr & 7) + bright;
                let paper = ((attr >> 3) & 7) + bright;
                if (flash && (attr & 0x80)) [ink, paper] = [paper, ink];

                for (let bit = 0; bit < 8; bit++) {
                    const x = col * 8 + bit;
                    const set = (pixelByte & (0x80 >> bit)) !== 0;
                    const c = set ? ZX_COLORS[ink] : ZX_COLORS[paper];
                    const idx = (y * 256 + x) * 4;
                    data[idx] = parseInt(c.substr(1, 2), 16);
                    data[idx + 1] = parseInt(c.substr(3, 2), 16);
                    data[idx + 2] = parseInt(c.substr(5, 2), 16);
                    data[idx + 3] = 255;
                }
            }
        }

        this.ctx.putImageData(this.imgData, 0, 0);
        // Scale up
        if (this.scale > 1) {
            this.ctx.save();
            this.ctx.imageSmoothingEnabled = false;
            this.ctx.drawImage(this.canvas, 0, 0, 256, 192, 0, 0, 256 * this.scale, 192 * this.scale);
            this.ctx.restore();
        }
        this.frameCount++;
    }

    // --- Bresenham line (matches Z80 draw_line) ---

    drawLine(x0, y0, x1, y1) {
        // Normalize left-to-right (matches our Z80 code)
        if (x0 > x1) {
            [x0, x1] = [x1, x0];
            [y0, y1] = [y1, y0];
        }
        const dx = x1 - x0;
        const dy = Math.abs(y1 - y0);
        const sy = y0 < y1 ? 1 : -1;

        if (dx >= dy) {
            // Horizontal-major
            let err = 0;
            let y = y0;
            for (let x = x0; x <= x1; x++) {
                this.setPixel(x, y);
                err += dy;
                if (err >= dx) {
                    err -= dx;
                    y += sy;
                }
            }
        } else {
            // Vertical-major
            let err = 0;
            let x = x0;
            const steps = dy;
            let y = y0;
            for (let i = 0; i <= steps; i++) {
                this.setPixel(x, y);
                y += sy;
                err += dx;
                if (err >= dy) {
                    err -= dy;
                    x++;
                }
            }
        }
    }
}

// --- Math helpers matching Z80 routines ---

const ZXMath = {
    // Signed 8-bit multiply (matches muls8: D×E → HL)
    muls8(a, b) {
        a = (a << 24) >> 24; // sign extend
        b = (b << 24) >> 24;
        return (a * b) | 0;
    },

    // Sin table (matches sin_table in math.a80)
    sinTable: new Int8Array(256),

    initSinTable() {
        for (let i = 0; i < 256; i++) {
            this.sinTable[i] = Math.round(127 * Math.sin(2 * Math.PI * i / 256));
        }
    },

    sin(angle) { return this.sinTable[angle & 0xFF]; },
    cos(angle) { return this.sinTable[(angle + 64) & 0xFF]; },

    // Rotate pair (matches rotate_pair)
    rotatePair(a, b, sin, cos) {
        const ra = ((a * cos - b * sin) * 2) >> 8;
        const rb = ((a * sin + b * cos) * 2) >> 8;
        return [this._clamp8(ra), this._clamp8(rb)];
    },

    // 3-axis rotation (matches rotate_xyz)
    rotateXYZ(x, y, z, ax, ay, az) {
        let sx, cx;
        // Z axis
        sx = this.sin(az); cx = this.cos(az);
        [x, y] = this.rotatePair(x, y, sx, cx);
        // Y axis
        sx = this.sin(ay); cx = this.cos(ay);
        [x, z] = this.rotatePair(x, z, sx, cx);
        // X axis
        sx = this.sin(ax); cx = this.cos(ax);
        [y, z] = this.rotatePair(y, z, sx, cx);
        return [x, y, z];
    },

    // Perspective projection (matches project routine)
    project(x, y, z, viewerDist = 200) {
        const denom = z + viewerDist;
        if (denom <= 0) return null;
        let scale = Math.min(255, Math.floor(viewerDist * 128 / denom));
        const sx = 128 + ((this.muls8(x, scale) * 2) >> 8);
        const sy = 96 + ((this.muls8(y, scale) * 2) >> 8);
        return [sx & 0xFF, sy & 0xFF];
    },

    _clamp8(v) {
        v = v | 0;
        if (v > 127) return 127;
        if (v < -128) return -128;
        return v;
    }
};

ZXMath.initSinTable();
