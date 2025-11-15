# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Edge, First
from cocotb.clock import Clock, Timer

async def send_bit(ps2_clk, ps2_data, bit):
    ps2_data.value = bit
    ps2_clk.value = 1
    await Timer(50, units="us")
    ps2_clk.value = 0
    await Timer(50, units="us")


async def send_bits(ps2_clk, ps2_data, value, bit_count=8, parity_valid=True, stop_valid=True):
    await send_bit(ps2_clk, ps2_data, 0)  # start bit
    parity = 0
    for i in range(bit_count):
        bit = (value >> (i)) & 1
        parity ^= bit
        await send_bit(ps2_clk, ps2_data, bit)
    if parity_valid:
        await send_bit(ps2_clk, ps2_data, not parity)
    else:
        await send_bit(ps2_clk, ps2_data, parity)
    if stop_valid:
        await send_bit(ps2_clk, ps2_data, 1)  # stop bit
    ps2_clk.value = 1


async def read_byte(dut):
    await Timer(40, units="ns")
    assert dut.uio_oe.value == 0x00, "uio_oe must not be set before a read"
    dut.cs.value = 1
    # wait 3 clock to ensure that cs doesn't double trigger and read multiple bytes. only one byte per rising edge.
    await Timer(120, units="ns")
    assert dut.uio_oe.value == 0xFF, "uio_oe must be set when reading data"
    dut.cs.value = 0
    return dut.uio_out.value


@cocotb.test()
async def ps2_decode_test(dut):
    """Test getting one byte from keyboard."""

    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    #cocotb.start_saving_waves()
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1
    
    await Timer(1, units="us")

    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0xC2))

    # wait for rising edge of valid and check data
    await RisingEdge(dut.valid)

    await Timer(80, units="ns")

    # wait enough time for the valid signal to go low and validate
    assert dut.valid == 0, "Valid not cleared properly"
    assert dut.interupt == 1, f"Interupt not clear after reset"
    assert dut.data_rdy == 1, f"data ready not set after valid"

    value = await read_byte(dut)
    assert value == 0xC2, f"Expected 0xC2, got {value}"

    await Timer(100, units="us")

    dut.clear_int.value = 1
    await Timer(80, units="ns")
    dut.clear_int.value = 0
    await Timer(40, units="ns")
    assert dut.interupt == 0, f"Interupt not clear after reset"

    assert dut.data_rdy == 0, f"data ready not cleared after read"


@cocotb.test()
async def ps2_decode_second_test(dut):
    """Test another byte."""

    #cocotb.start_saving_waves()
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0xF0))

    # wait for rising edge of valid and check data
    await RisingEdge(dut.valid)

    await Timer(80, units="ns")

    # wait enough time for the valid signal to go low and validate
    assert dut.valid == 0, "Valid not cleared properly"
    assert dut.interupt == 1, f"Interupt not clear after reset"
    assert dut.data_rdy == 1, f"data ready not set after valid"

    value = await read_byte(dut)
    assert value == 0xF0, f"Expected 0xC2, got {value}"

    await Timer(100, units="us")

    # clear interupt
    dut.clear_int.value = 1
    await Timer(80, units="ns")
    dut.clear_int.value = 0
    await Timer(40, units="ns")
    assert dut.interupt == 0, f"Interupt not clear after reset"


@cocotb.test()
async def ps2_decode_partial_test(dut):
    """Test the a failed transmit."""

    #cocotb.start_saving_waves()
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0xF0, bit_count=5, parity_valid=False, stop_valid=False))

    # wait for rising edge of valid and check data
    to = Timer(1.5, units='ms')
    res = await First(RisingEdge(dut.valid), to)

    print(f"res: {res}")

    assert isinstance(res, Timer) , "Expected timeout got rising edge"


async def send_two_bytes(ps2_clk, ps2_data, value1, value2):
    await send_bits(ps2_clk, ps2_data, value1)
    await Timer(100, units="us")
    await send_bits(ps2_clk, ps2_data, value2)

@cocotb.test()
async def ps2_decode_two_bytes_test(dut):
    """Test receiveing two keycodes."""

    #cocotb.start_saving_waves()
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    cocotb.start_soon(send_two_bytes(dut.ps2_clk, dut.ps2_data, 0xF0, 0x15))

    # wait for rising edge of valid and check data
    await RisingEdge(dut.valid)
    await RisingEdge(dut.valid)

    await Timer(80, units="ns")

    # wait enough time for the valid signal to go low and validate
    assert dut.valid == 0, "Valid not cleared properly"
    assert dut.interupt == 1, f"Interupt not clear after reset"
    assert dut.data_rdy == 1, f"data ready not set after valid"

    value = await read_byte(dut)
    assert value == 0xF0, f"Expected 0xF0, got {value.hex()}"

    value = await read_byte(dut)
    assert value == 0x15, f"Expected 0x15, got {value.hex()}"

    await Timer(100, units="us")

    # clear interupt
    dut.clear_int.value = 1
    await Timer(80, units="ns")
    dut.clear_int.value = 0
    await Timer(40, units="ns")
    assert dut.interupt == 0, f"Interupt not clear after reset"


@cocotb.test()
async def ps2_decode_two_bytes_int_clear_test(dut):
    """Test receiveing two keycodes."""

    #cocotb.start_saving_waves()
    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    assert dut.interupt == 0, f"Interupt not clear before test"

    cocotb.start_soon(send_two_bytes(dut.ps2_clk, dut.ps2_data, 0xF1, 0x16))

    # wait for rising edge of valid and check data
    await RisingEdge(dut.interupt)
    await Timer(1, units="us")

    value = await read_byte(dut)
    assert value == 0xF1, f"Expected 0xF1, got {value.hex()}"

    assert dut.data_rdy == 0, f"data ready not cleared after read"
    assert dut.interupt == 1, f"Interupt not set after read"

    # clear interupt
    dut.clear_int.value = 1
    await Timer(80, units="ns")
    dut.clear_int.value = 0
    await Timer(40, units="ns")
    assert dut.interupt == 0, f"Interupt not clear after reset"

    # wait for rising edge of valid and check data
    await RisingEdge(dut.interupt)

    await Timer(1, units="us")

    value = await read_byte(dut)
    assert value == 0x16, f"Expected 0x16, got {value.hex()}"

    assert dut.data_rdy == 0, f"data ready not cleared after read"
    assert dut.interupt == 1, f"Interupt not set after read"

    # clear interupt
    dut.clear_int.value = 1
    await Timer(80, units="ns")
    dut.clear_int.value = 0
    await Timer(40, units="ns")
    assert dut.interupt == 0, f"Interupt not clear after reset"


@cocotb.test()
async def test_fifo_overflow(dut):
    """Test FIFO overflow - send 5 bytes, verify 5th triggers full flag."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Send 5 bytes without reading - FIFO depth is 4
    for i in range(5):
        value = 0xA0 + i
        cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, value))
        await RisingEdge(dut.valid)
        await Timer(100, units="us")

    # Check that FIFO full flag is set
    assert dut.fifo_full == 1, "FIFO full flag should be set after 4 writes"

    # Read all 4 bytes from FIFO
    for i in range(4):
        expected = 0xA0 + i
        value = await read_byte(dut)
        assert value == expected, f"Expected 0x{expected:02X}, got {value}"

    # FIFO should now be empty
    assert dut.data_rdy == 0, "FIFO should be empty after reading 4 bytes"
    assert dut.fifo_full == 0, "FIFO full flag should be clear"


@cocotb.test()
async def test_parity_error(dut):
    """Test that bytes with parity errors are rejected."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Send byte with WRONG parity
    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0xAA, parity_valid=False))

    # Wait for potential valid signal
    to = Timer(1.5, units='ms')
    res = await First(RisingEdge(dut.valid), to)

    # Should timeout, not get valid
    assert isinstance(res, Timer), "Expected timeout - invalid parity should be rejected"


@cocotb.test()
async def test_start_bit_error(dut):
    """Test that frames with wrong start bit are rejected."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Manually send frame with start bit = 1 (should be 0)
    await send_bit(dut.ps2_clk, dut.ps2_data, 1)  # Wrong start bit
    # Send 8 data bits
    for i in range(8):
        await send_bit(dut.ps2_clk, dut.ps2_data, (0x55 >> i) & 1)
    # Send parity
    await send_bit(dut.ps2_clk, dut.ps2_data, 0)
    # Send stop bit
    await send_bit(dut.ps2_clk, dut.ps2_data, 1)
    dut.ps2_clk.value = 1

    await Timer(500, units="us")

    # Should not have triggered valid
    assert dut.data_rdy == 0, "No data should be in FIFO with bad start bit"


@cocotb.test()
async def test_stop_bit_error(dut):
    """Test that frames with wrong stop bit are rejected."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Send byte with WRONG stop bit (0 instead of 1)
    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0x33, stop_valid=False))

    # Wait for potential valid signal
    to = Timer(1.5, units='ms')
    res = await First(RisingEdge(dut.valid), to)

    # Should timeout, not get valid
    assert isinstance(res, Timer), "Expected timeout - invalid stop bit should be rejected"


@cocotb.test()
async def test_back_to_back_bytes(dut):
    """Test rapid byte transmission with minimal gap."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Send 3 bytes with only 150us gap (fast typing)
    # Gap must be >100us for decoder timeout to trigger
    async def send_rapid_bytes():
        await send_bits(dut.ps2_clk, dut.ps2_data, 0x1C)
        await Timer(150, units="us")  # Minimal gap for decoder
        await send_bits(dut.ps2_clk, dut.ps2_data, 0x1B)
        await Timer(150, units="us")
        await send_bits(dut.ps2_clk, dut.ps2_data, 0x23)

    cocotb.start_soon(send_rapid_bytes())

    # Wait for all 3 valid pulses
    await RisingEdge(dut.valid)
    await RisingEdge(dut.valid)
    await RisingEdge(dut.valid)

    await Timer(100, units="us")

    # Verify all 3 bytes received correctly
    value = await read_byte(dut)
    assert value == 0x1C, f"Expected 0x1C, got {value}"

    value = await read_byte(dut)
    assert value == 0x1B, f"Expected 0x1B, got {value}"

    value = await read_byte(dut)
    assert value == 0x23, f"Expected 0x23, got {value}"


@cocotb.test()
async def test_cs_held_high(dut):
    """Test that holding CS high only reads one byte (no double-trigger)."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Send 2 bytes
    cocotb.start_soon(send_two_bytes(dut.ps2_clk, dut.ps2_data, 0x44, 0x55))

    await RisingEdge(dut.valid)
    await RisingEdge(dut.valid)

    await Timer(100, units="us")

    # Hold CS high for extended period (1us = 25 cycles)
    assert dut.uio_oe.value == 0x00, "uio_oe must not be set before CS"
    dut.cs.value = 1
    await Timer(1, units="us")  # Hold for 25 cycles

    # Should see first byte
    first_value = dut.uio_out.value
    assert first_value == 0x44, f"Expected 0x44, got {first_value}"

    # Hold CS high longer - value should NOT change to second byte
    await Timer(500, units="ns")
    still_value = dut.uio_out.value
    assert still_value == 0x44, f"Value changed during held CS - got {still_value}"

    dut.cs.value = 0
    await Timer(100, units="ns")

    # Now read second byte with fresh CS cycle
    value = await read_byte(dut)
    assert value == 0x55, f"Expected 0x55, got {value}"


@cocotb.test()
async def test_reset_during_transmission(dut):
    """Test that reset during byte transmission recovers cleanly."""

    # Initialize signals
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Start sending a byte but interrupt it mid-transmission
    async def send_interrupted_byte():
        await send_bit(dut.ps2_clk, dut.ps2_data, 0)  # start
        await send_bit(dut.ps2_clk, dut.ps2_data, 1)  # bit 0
        await send_bit(dut.ps2_clk, dut.ps2_data, 0)  # bit 1
        # Reset happens here

    cocotb.start_soon(send_interrupted_byte())
    await Timer(200, units="us")

    # Assert reset
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    await Timer(500, units="ns")

    # Verify reset state
    assert dut.interupt == 0, "Interrupt should be cleared by reset"
    assert dut.data_rdy == 0, "FIFO should be empty after reset"

    # Now send a complete valid byte
    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0x66))
    await RisingEdge(dut.valid)
    await Timer(100, units="ns")

    value = await read_byte(dut)
    assert value == 0x66, f"Expected 0x66 after reset recovery, got {value}"


@cocotb.test()
async def test_all_zeros(dut):
    """Test transmitting 0x00 (all zeros)."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0x00))

    await RisingEdge(dut.valid)
    await Timer(80, units="ns")

    value = await read_byte(dut)
    assert value == 0x00, f"Expected 0x00, got {value}"


@cocotb.test()
async def test_all_ones(dut):
    """Test transmitting 0xFF (all ones)."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0xFF))

    await RisingEdge(dut.valid)
    await Timer(80, units="ns")

    value = await read_byte(dut)
    assert value == 0xFF, f"Expected 0xFF, got {value}"


@cocotb.test()
async def test_variable_ps2_clock_fast(dut):
    """Test with faster PS/2 clock (12 kHz instead of 10 kHz)."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Send byte at 12kHz (period = 83.3us, half period = 41.6us)
    async def send_bit_fast(ps2_clk, ps2_data, bit):
        ps2_data.value = bit
        ps2_clk.value = 1
        await Timer(42, units="us")
        ps2_clk.value = 0
        await Timer(42, units="us")

    async def send_byte_fast(value):
        await send_bit_fast(dut.ps2_clk, dut.ps2_data, 0)  # start
        parity = 0
        for i in range(8):
            bit = (value >> i) & 1
            parity ^= bit
            await send_bit_fast(dut.ps2_clk, dut.ps2_data, bit)
        await send_bit_fast(dut.ps2_clk, dut.ps2_data, not parity)  # parity
        await send_bit_fast(dut.ps2_clk, dut.ps2_data, 1)  # stop
        dut.ps2_clk.value = 1

    cocotb.start_soon(send_byte_fast(0x77))

    await RisingEdge(dut.valid)
    await Timer(80, units="ns")

    value = await read_byte(dut)
    assert value == 0x77, f"Expected 0x77 with fast clock, got {value}"


@cocotb.test()
async def test_variable_ps2_clock_slow(dut):
    """Test with slower PS/2 clock (8 kHz)."""

    # Initialize and reset DUT
    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    assert dut.interupt == 0, f"Interupt not clear after reset"

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1

    await Timer(1, units="us")

    # Send byte at 8kHz (period = 125us, half period = 62.5us)
    async def send_bit_slow(ps2_clk, ps2_data, bit):
        ps2_data.value = bit
        ps2_clk.value = 1
        await Timer(62, units="us")
        ps2_clk.value = 0
        await Timer(62, units="us")

    async def send_byte_slow(value):
        await send_bit_slow(dut.ps2_clk, dut.ps2_data, 0)  # start
        parity = 0
        for i in range(8):
            bit = (value >> i) & 1
            parity ^= bit
            await send_bit_slow(dut.ps2_clk, dut.ps2_data, bit)
        await send_bit_slow(dut.ps2_clk, dut.ps2_data, not parity)  # parity
        await send_bit_slow(dut.ps2_clk, dut.ps2_data, 1)  # stop
        dut.ps2_clk.value = 1

    cocotb.start_soon(send_byte_slow(0x88))

    await RisingEdge(dut.valid)
    await Timer(80, units="ns")

    value = await read_byte(dut)
    assert value == 0x88, f"Expected 0x88 with slow clock, got {value}"


# ========================================
# UART TX Test Helper Functions
# ========================================

async def uart_receive_byte(dut, timeout_us=1000):
    """Receive one byte from UART TX line (115200 baud, 25 MHz clock)."""
    # 115200 baud = 8.68 us per bit = 217 clock cycles @ 25 MHz
    bit_time_ns = 8680  # 8.68 us in nanoseconds

    # Wait for start bit (falling edge from idle high to 0)
    start_time = cocotb.utils.get_sim_time(units='us')
    while dut.uart_tx.value == 1:
        await Timer(100, units="ns")
        if cocotb.utils.get_sim_time(units='us') - start_time > timeout_us:
            raise TimeoutError("UART start bit timeout")

    # Wait to middle of start bit
    await Timer(bit_time_ns // 2, units="ns")
    assert dut.uart_tx.value == 0, "UART start bit must be 0"

    # Read 8 data bits (LSB first)
    data = 0
    for i in range(8):
        await Timer(bit_time_ns, units="ns")
        bit = int(dut.uart_tx.value)
        data |= (bit << i)

    # Check stop bit
    await Timer(bit_time_ns, units="ns")
    assert dut.uart_tx.value == 1, "UART stop bit must be 1"

    return data


async def uart_receive_two_bytes(dut, timeout_us=2000):
    """Receive two bytes from UART: status byte + data byte."""
    status = await uart_receive_byte(dut, timeout_us)
    data = await uart_receive_byte(dut, timeout_us)
    return status, data


# ========================================
# UART TX Tests
# ========================================

@cocotb.test()
async def test_uart_tx_single_byte(dut):
    """Test UART TX sends status + data when PS/2 byte is received."""

    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1
    await Timer(1, units="us")

    # Send PS/2 byte 0xAB
    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0xAB))

    # Receive UART transmission
    status, data = await uart_receive_two_bytes(dut)

    # Verify status byte: bit 0 = valid (1), bit 1 = interrupt (1), bit 2 = data_rdy (1), bit 3 = fifo_full (0)
    assert (status & 0x01) == 0x01, f"Valid bit should be set in status: {status:02x}"
    assert (status & 0x02) == 0x02, f"Interrupt bit should be set in status: {status:02x}"
    assert (status & 0x04) == 0x04, f"Data ready bit should be set in status: {status:02x}"
    assert (status & 0x08) == 0x00, f"FIFO full bit should not be set in status: {status:02x}"

    # Verify data byte matches PS/2 byte
    assert data == 0xAB, f"Expected UART data 0xAB, got 0x{data:02x}"


@cocotb.test()
async def test_uart_tx_multiple_bytes(dut):
    """Test UART TX sends multiple PS/2 bytes correctly."""

    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1
    await Timer(1, units="us")

    test_bytes = [0x1C, 0x23, 0x3A]

    for test_byte in test_bytes:
        # Send PS/2 byte
        cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, test_byte))

        # Receive UART transmission
        status, data = await uart_receive_two_bytes(dut, timeout_us=3000)

        # Verify data byte
        assert data == test_byte, f"Expected UART data 0x{test_byte:02x}, got 0x{data:02x}"

        # Small delay between bytes
        await Timer(50, units="us")


@cocotb.test()
async def test_uart_tx_fifo_full_status(dut):
    """Test UART TX reports FIFO full status correctly."""

    dut.clear_int.value = 0
    dut.cs.value = 0
    dut.rst_n.value = 0
    await Timer(1, units="us")
    dut.rst_n.value = 1

    cocotb.start_soon(Clock(dut.clk, 40, units="ns").start())

    dut.ps2_clk.value = 1
    dut.ps2_data.value = 1
    await Timer(1, units="us")

    # Send 4 bytes to fill FIFO (capacity = 4)
    for i in range(4):
        cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0x10 + i))
        await RisingEdge(dut.valid)
        await Timer(200, units="ns")

    # Send 5th byte - should trigger FIFO full
    cocotb.start_soon(send_bits(dut.ps2_clk, dut.ps2_data, 0x99))

    # Receive UART transmission for 5th byte
    status, data = await uart_receive_two_bytes(dut, timeout_us=3000)

    # FIFO should be full (bit 3 = 1)
    assert (status & 0x08) == 0x08, f"FIFO full bit should be set in status: {status:02x}"
    assert data == 0x99, f"Expected UART data 0x99, got 0x{data:02x}"
