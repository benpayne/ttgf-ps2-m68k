<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This decoder works by first debouncing the inputs to make sure that we get a clean sample of them that is synchronized to our clock.  It then looks at the down transition of ps2_clk and reads the value of ps2_data.  It shifts this into a 11 bit shift register.  When ps2_clk remains high for more than 1/2 of the 10kHz ps2_clk cycle it knows that the end of the data has arrived.  It then triggers a valid flag to tell the system that something has arrived.  The valid flag, which is exposed on a pin, will trigger the fifo to read the byte of data and it will be stored for retrieval by the host.  When valid is triggered it will also trigger the interrupt pin.  The valid pin is a pulse for one system clock cycle, but the interrupt will remain set until it is cleared.  We also include a data_rdy signal that tells the host that there is data to read.  This is useful if your interrupt handler needs to read multiple bytes.

When the host wants to read a byte, it asserts the chip select (cs) signal when the system clock goes high.  This will result in the uio bus being set with the data value.  The uio bus will be put into an output state only when cs is asserted, at all other times it will be an input bus (but we never read it...).  The CS signal includes glitch filtering - it must be held stable high for at least 2 clock cycles (80ns @ 25MHz) to trigger a read.  This prevents accidental double-reads from noisy bus signals.

The design includes a fifo_full output signal that indicates when the FIFO buffer is full (4 bytes).  When full, additional bytes from the keyboard will be silently dropped until space becomes available.  Software should monitor this flag to detect potential data loss during rapid typing.

## GF180 Advantages for PS/2 Interface

This design takes advantage of GlobalFoundries GF180MCU's native **5V I/O tolerance**:

- **No level shifters required** - PS/2 keyboards use 5V signaling, which is directly compatible with GF180's I/O
- **3.3V core voltage** provides better noise margins than Sky130's 1.8V
- **Industrial temperature range** (-40°C to 125°C) supports harsh environments
- **Larger process** (180nm) provides more routing resources and better ESD protection

## How to test

Simply interface a PS2 keyboard directly to the PS2 clock and data lines. **No level shifting needed** - the GF180 I/O pads handle 5V signaling natively! At this point you can hit keys and they will be queued in the fifo.  Then you would want to interface a retro computer to the CS, interrupt and data lines to read the fifo.  This will depend on the system you're using, but note you'll need external address decoding logic and for chips like the m68k you'll need to generate the DTACK and other signals elsewhere.

## External hardware

Connect a standard PS/2 keyboard directly to the chip:
- PS/2 pin 1 (DATA) → ui_in[1]
- PS/2 pin 5 (CLK) → ui_in[0]
- PS/2 pin 3 (GND) → GND
- PS/2 pin 4 (VCC) → 5V supply

**Note**: Unlike Sky130 designs, GF180's native 5V tolerance means no level shifters or voltage dividers are required!

Interface to your microprocessor:
- Connect CS, interrupt, and data_out[7:0] signals
- Add external address decoding logic as needed
- For 68000: Generate DTACK externally based on CS timing
