
//----------------------------------------------------

patrik_rak_cmwc_rnd:
	ld  hl,.table
.idx:   ld  bc,0       ; i
	add  hl,bc
	ld  a,c
	inc  a
	and  7
	ld  (.idx+1),a  ; i = ( i + 1 ) & 7
	ld  c,(hl)    ; y = q[i]
	ex  de,hl
	ld  h,c    ; t = 256 * y
	ld  l,b
	sbc  hl,bc    ; t = 255 * y
	sbc  hl,bc    ; t = 254 * y
	sbc  hl,bc    ; t = 253 * y
.car:   ld  c,0    ; c
	add  hl,bc    ; t = 253 * y + c
	ld  a,h    ; c = t / 256
	ld  (.car+1),a
	ld  a,l    ; x = t % 256
	cpl      ; x = (b-1) - x = -x - 1 = ~x + 1 - 1 = ~x
	ld  (de),a
	ret

.table    db   82,97,120,111,102,116,20,12

//----------------------------------------------------

raxoft_rnd:    ld   hl, rnd_table
        ld   a, (hl) ; i = ( i & 7 ) + 1
        and  7
        inc  a
        ld   (hl), a
        inc  l      ; hl = &cy
        ld   d, h    ; de = &q[i]
        add  a, l
        ld   e, a
        ld   a, (de) ; y = q[i]
        ld   b,a
        ld   c,a
        ld   a, (hl) ; ba = 256 * y + cy
        sub  c      ; ba = 255 * y + cy
        jr   nc, $+3
        dec  b
        sub  c      ; ba = 254 * y + cy
        jr   nc, $+3
        dec  b
        sub  c      ; ba = 253 * y + cy
        jr   nc, $+3
        dec  b
        ld   (hl), b ; cy = ba >> 8, x = ba & 255
        cpl         ; x = (b-1) - x = -x - 1 = ~x + 1 - 1 = ~x
        ld   (de), a ; q[i] = x
        ret

rnd_table:
	db   0,0,82,97,120,111,102,116,20,15

        if (rnd_table/256)-((rnd_table+9)/256)
            error "rnd table must be within single 256 byte block"
        endif

//----------------------------------------------------

ion_rnd:
        ld      hl, 0
        ld      a, r
        ld      d, a
        ld      e, (hl)
        add     hl, de
        add     a, l
        xor     h
        ld      (ion_rnd + 1), hl
        ret

//----------------------------------------------------

xorshift_rnd:
	ld hl,1 	; HL = ABCDEFGH abcdefgh
	ld a,h		; A = ABCDEFGH
	rra		; A = ?ABCDEFG, CY=H
	ld a,l		; A = abcdefgh
	rra		; A = Habcdefg, CY=h	
	xor h		; A = Habcdefg ^ ABCDEFGH, CY=0
	ld h,a		; H = Habcdefg ^ ABCDEFGH
	ld a,l		; A = abcdefgh
	rra		; A = 0abcdefg, CY=h
	ld a,h		; A = Habcdefg ^ ABCDEFGH
	rra		; A = h[Habcdef ^ ABCDEFG], CY=g^H
	xor l		; A = (h[Habcdef ^ ABCDEFG]) ^ abcdefgh, CY=0
	ld l,a		; L = (h[Habcdef ^ ABCDEFG]) ^ abcdefgh
	xor h		; A = (h[Habcdef ^ ABCDEFG]) ^ abcdefgh ^ Habcdefg ^ ABCDEFGH
	ld h,a		; H = (h[Habcdef ^ ABCDEFG]) ^ abcdefgh ^ Habcdefg ^ ABCDEFGH
	ld (xorshift_rnd+1),hl
	ret

//----------------------------------------------------

