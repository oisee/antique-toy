;Hole 17 enigma
;ZX Spectrum 48K+AY, 256 bytes intro
;code - .ded^RMDA
;22.02.2021, Russia, Samara

;How to build:

;in Pasmo http://pasmo.speccy.org/
;pasmo.exe --bin hole17.asm hole17.bin
;pasmo.exe --tapbas --name enigma hole17.asm hole17.tap

;in SjASMplus https://github.com/z00m128/sjasmplus
;sjasmplus.exe hole17.asm

		DEVICE	ZXSPECTRUM48	;comment this for Pasmo

; generated	#5b00 - #ffff, any memory filled with 00,00,00
; intro code  	#fd00 - you can move it to block from #5c to #fd  
; im2 JP        #fdfd - 3 bytes
; im2 table     #fe00 - #ff00, filled with #fd

start_mem:	equ #5b00	;start address of generated CALL
end_mem:	equ #fd	        ;end of memory,not used in final
start_scr:	equ #5800       ;end of refreshing screen area
fx_shift:	equ 24		;only even number, 2=shift 0
				;4=shift 2 bytes, 6=shift 4
				;34=scroll 34-2=32 bytes
				;and so on...

complexity:	equ #eb		;#eb is close to the maximum

        org	#fd00		;if you change ORG you need 
				;clean RAM/decrease complexity

begin:	equ	$
table:	equ	$+17		;10 bytes of pRNG table is here

	di
;-------AY-MUSIC------------------------------------------------
	ld	de,#fe0d	;D=#fe IM2 table, E=#0d for AY
	ld	hl,begin+73	;+3,+10,+32,+37,+45,+68,+78
ayl:	
	ld	bc,#fffd
	out	(c),e
	ld	b,#bf
	outi
	dec	e
	jr	nz,ayl
;-------IM2 table generator-------------------------------------
	ld	a,c		;ld  a,#fd
im2tab:
        ld	(de),a		;HL=#fe00, IM2 table #fe00-#ff00
        inc	e
        jr	nz,im2tab
        inc	d		;last byte of IM2 table at #ff00
        ld	(de),a
        inc	a 
	out	(#fe),a		;BORDER 6
        ld	i,a
        im	2		
;-------Maximum ZERO all free RAM before code generation--------
				;select one of this options:
	ld	l,e             ;for relocation code
;	ld	l,#22		;or for maximum zeroing, +1 byte

clear:
	ld	(hl),e
	dec	hl
	ld	a,h
	cp	#57		
	jr	nz,clear        ;hidden free LD SP,HL is here!
attr:
	inc	hl
	ld	(hl),#36
	ld	a,h
	cp	#5b
	jr	nz,attr-1	;jr attr-1 give us free LD SP,HL
;---------------------------------------------------------------
;	ld	sp,hl		;for visual decrunch,this damage
;	inc	sp		;first CALL at #5B00 but we fix 
				;it with PUSH after decrunch.
	pop	af              ;set SP position for decrunch
;---------------------------------------------------------------
				;HL - current address for CALL
				;DE - destination for CALL
				;BC - counter generated of CALLs
newrnd:

	ld	(hl),#cd	;new address, lets put #CD/CALL
	inc	hl		; 
;!!! very important to secure 2 next bytes
;	ld	(hl),h		;and secure 2 more bytes
	inc	hl              ;with anything, but not #00
	ld	(hl),h          ;coz #00 is the mark of free RAM
	dec	hl		;for CALL generator
;---------------------------------------------------------------
rernd:

	call	prnd		;get pRNG for high byte of DE

	cp	#5b		;must be more than #5a
;	jr	c,rernd		;if not - redo pRNG for hi-byte
	jr	nc,next		;
;	cp	end_mem		;...but less then end of memory
;	jr	nc,rernd	;if not - redo pRNG for hi-byte

				;And we can save a lot of bytes
	cpl			;if just CPL wrong number!

next:	
	ld	d,a		;store pRNG high byte in D
;---------------------------------------------------------------
	ex	af,af'		;4 bytes offset here for right 
				;colors in decrunch attribute.
	ld	a,#06           ;lets use them to initialize AF'
	ex	af,af'          ;which is used later in IM2.
;---------------------------------------------------------------
	call	prnd		;get pRNG for low byte
	ld	e,a		;any pRNG is valid so store it E
;---------------------------------------------------------------
;in HL adress of LOW byte for new CALL
;in DE destination adress of new CALL
	ld	a,(de)          
	or	a               ;check is there 0 in RAM for #CD
	jr	nz,rernd	;if not 0 then redo pRNG
;---------------------------------------------------------------
	inc	de
	ld	a,(de)
	or	a
	jr	nz,rernd	;is there 0 in RAM for low byte?
;---------------------------------------------------------------
	inc	de
	ld	a,(de)		
	or	a
	jr	nz,rernd        ;is there 0 for high byte?
;---------------------------------------------------------------
	dec	de
	dec	de

	ld	(hl),e		;put argument (new PC address) 
	inc	hl		;for #CD, chosen in nextrnd.
	ld	(hl),d       

	ld	h,d		;set this new adress as next 
	ld	l,e		;VALID address for #CD or any 
				;other 1-2-3 bytes oppcode.
			
	inc	bc

	ld	a,b
	cp	complexity	;check amount of generated data
	jr	nz,newrnd
;---------------------------------------------------------------
	ld	de,#cd36	;#CD to restore CALL
	push	de              ;#36 to restore decrunch attr
;---------------------------------------------------------------
	ld	(hl),d		;put CALL #5b00 at the end
	inc	hl		;to loop generated data.
;	ld	(hl),c       	;memory is filled with #00, skip
	inc	hl          
	ld	(hl),#5b	;generated code is looped.

;-------first run + end part of IM2 handler---------------------
im2exit:
	dec	hl		;not so important for 1st start
	dec	hl              ;but reused for IM2 handler.
	
	ei
	ld	sp,start_scr	;we need to JP #5b00 at 1st time 
	jp	(hl)            ;but not a problem to JP at any 
				;valid address to save bytes.

int:	;check SP value with debugger at this point
	;to understand how fast/slow your hardware

;-------derandomize screen attrs--------------------------------

	ld	de,%0000001100001111	;used later in HOLE code
	
enigma2:
	ld	h,#58		;L is random from last IM2
	ld	b,d		;B=3 for 3 attr parts of the scr
	ex	af,af'
attr2:	ld	(hl),a
	rlc	l
;---------------------------------------------------------------
;	ld	(hl),a		;more speed per frame
;	rlc	l		;but +3 bytes...
;---------------------------------------------------------------
	inc	l		;or more speed per frame 
	ld	(hl),a		;poor randomness but +2 bytes
;---------------------------------------------------------------
	inc 	h			
	djnz	attr2

	xor	#36
	ex	af,af'

;-------2d object-----------------------------------------------
	ld	hl,#4973	;H=#49 for visible object
				;L=#71 fill with C pattern
				;L=#73 fill with D pattern
fill	
				;ld	(hl),d
	dec	h
	jr	nz,fill-2	;-1 byte saver,reuse #73

;-------keyboard------------------------------------------------
enigma:	ld	bc,#7ffe
	in	a,(c)
	rrca
	jr	nc,enigma	;SPACE to solve enigma.
;	jr	nc,enigma2	;try it for even more FX

;-------mistery hole: left half---------------------------------

	ld	hl,#40ef	;L value used in OR action, so
;-1				;no chance to change HOLE place 
	ld	a,(hl)
	or	d
	ld	(hl),a

	inc	h
;-2
	ld	a,(hl)
	or	e
	ld	(hl),a
	inc	h
;-3
	ld	a,(hl)          
	or	%00011111
	ld	(hl),a
	inc	h
;-4
;	ld	a,(hl)		;fake#1 hole byte saver
	or	b
	ld	(hl),a
	inc	h
;-5
;	ld 	a,(hl)		;fake#1 hole byte saver
;	or 	b		;fake#1 hole byte saver
	ld 	(hl),a
	inc 	h
;-6
	ld	a,(hl)          
	or	%00011111		
	ld	(hl),a
	inc	h
;-7
	ld	a,(hl)
	or	e
	ld	(hl),a
	inc	h		;fake#3 - make hole asymmetric
				;and save up to 8 bytes.
;-8
	ld	a,(hl)		;fake#3
	or	d		;fake#3
	ld	(hl),a		;fake#3
;---------------------------------------------------------------
;#030F - D E
;#1F7F - N B
;#C0F0 - D L
;#F8FE - E C
;some of the command also can useful to DRAW hole but not 
;in our case, we have preloaded BC mask for left and right 
;pixels: sll (hl) / sla (hl) / sra (hl) / set 7,(hl)
;-------mistery hole: right half--------------------------------

	inc l
	ld	de,%1100000011111000
;-1
	ld	a,(hl)		;fake#2, but 2 pix always ON
	or	d
	ld	(hl),a
	dec	h
;-2
	ld	a,(hl)
	or	l
	ld	(hl),a
	dec	h
;-3
	ld	a,(hl)
	or	e
	ld	(hl),a
	dec	h
;-4
;	ld	a,(hl)		;fake#1 hole byte saver
	or	c
	ld	(hl),a
	dec	h
;-5
;	ld	a,(hl)		;fake#1 hole byte saver
;	or	c		;fake#1 hole byte saver
	ld	(hl),a
	dec	h
;-6
	ld	a,(hl)
	or	e
	ld	(hl),a
	dec	h
;-7
	ld	a,(hl)
	or	l
	ld	(hl),a
	dec	h		;fake#3
;-8
	ld	a,(hl)		;fake#3
	or	d		;fake#3
	ld	(hl),a		;fake#3
;---------------------------------------------------------------
	ld	hl,(start_scr-fx_shift)          
;	dec	hl
;	dec	hl
	dec	hl
	jr	im2exit
;---------------------------------------------------------------
;Fast quality CMWC random number generator by Patrik Rak 
;---------------------------------------------------------------
prnd:	
	exx

	ld   hl,table

;	ld	h,#58	;one byte saver + additional visuals if 
			;H = #40-#5A but... decrunch takes more
			;time and seems less random than normal
			;pRNG table

        ld   a,(hl) ; i = ( i & 7 ) + 1
        and  7
        inc  a
        ld   (hl),a

        inc  l      ; hl = &cy

        ld   d,h    ; de = &q[i]
        add  a,l
        ld   e,a

        ld   a,(de) ; y = q[i]
        ld   b,a
        ld   c,a
        ld   a,(hl) ; ba = 256 * y + cy

        sub  c      ; ba = 255 * y + cy
        jr   nc,$+3
        dec  b

        sub  c      ; ba = 254 * y + cy
        jr   nc,$+3
        dec  b

        sub  c      ; ba = 253 * y + cy
        jr   nc,$+3
        dec  b

        ld   (hl),b ; cy = ba >> 8, x = ba & 255
        cpl         ; x = (b-1) - x = -x - 1 = ~x + 1 - 1 = ~x
        ld   (de),a ; q[i] = x

	exx
        ret
;---------------------------------------------------------------

        org	#fdfd

	jp	int	;set JP to IM2 handler
fin:
;-----comment this for Pasmo or uncomment for SjAsm-------------
	SAVESNA	"hole17.sna", begin
	SAVEBIN	"hole17.bin", begin,fin-begin
;	EMPTYTRD"hole17.trd","Hole17"
;	SAVETRD	"hole17.trd","enigma.C",begin,fin-begin
;	EMPTYTAP"hole17.tap"
;	SAVETAP	"hole17.tap",CODE,"enigma",begin,fin-begin
;-------=RMDA=---------------------------------------------[eof]