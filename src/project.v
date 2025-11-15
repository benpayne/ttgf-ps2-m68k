/*
 * Copyright (c) 2024 Ben Payne
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_benpayne_ps2_decoder (
    input  wire       clk,      // clock
    input  wire       ena,      // always 1 when the design is powered
    input  wire       rst_n,    // reset_n - low to reset
    inout  wire       VPWR,     // Power rail (3.3V)
    inout  wire       VGND,     // Ground rail
    input  wire [7:0] ui_in,    // Dedicated inputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uo_out    // Dedicated outputs
);

  // All output pins must be assigned. If not used, assign to 0.
  assign uio_oe = cs ? 8'b11111111 : 8'b00000000; // uio_out[7:0] are always outputs when CS active
  assign uo_out[7:4] = 4'b0000; // uo_out[7:4] set to always 0

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, uio_in, ui_in[7:4], 1'b0};

  wire ps2_clk_internal;
  wire ps2_data_internal;
  wire [7:0] ps2_key_data;
  wire valid;
  wire interupt;
  wire int_clear;
  wire cs;
  wire data_rdy;
  wire fifo_full;

  reg cs_prev;
  reg cs_trigger;
  reg cs_stable;  // Require 2 stable cycles before triggering

  assign int_clear = ui_in[2];
  assign cs = ui_in[3];

  assign uo_out[0] = valid;
  assign uo_out[1] = interupt;
  assign uo_out[2] = ~data_rdy;
  assign uo_out[3] = fifo_full;  // FIFO overflow indicator

  // CS edge detection with glitch filtering
  // Requires CS to be stable high for 2 cycles after rising edge before triggering read
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cs_prev <= 0;
      cs_trigger <= 0;
      cs_stable <= 0;
    end else begin
      cs_prev <= cs;

      // Rising edge detected - wait one more cycle for stability
      if (cs_prev == 0 && cs == 1) begin
        cs_stable <= 1;
        cs_trigger <= 0;
      end
      // Second cycle of stable high - trigger read
      else if (cs == 1 && cs_stable == 1) begin
        cs_trigger <= 1;
        cs_stable <= 0;  // Reset to prevent re-trigger while CS held
      end
      // CS went low - reset
      else if (cs == 0) begin
        cs_stable <= 0;
        cs_trigger <= 0;
      end
      // Default - clear trigger
      else begin
        cs_trigger <= 0;
      end
    end
  end

  debounce ps2_clk_debounce(
    .clk(clk),
    .reset(~rst_n),
    .VPWR(VPWR),
    .VGND(VGND),
    .button(ui_in[0]),
    .debounced_button(ps2_clk_internal)
  );

  debounce ps2_data_debounce(
    .clk(clk),
    .reset(~rst_n),
    .VPWR(VPWR),
    .VGND(VGND),
    .button(ui_in[1]),
    .debounced_button(ps2_data_internal)
  );

  dual_port_fifo memory(
    .clk(clk),
    .rst(~rst_n),
    .VPWR(VPWR),
    .VGND(VGND),
    .wr_en(valid),
    .rd_en(cs_trigger),
    .empty(data_rdy),
    .full(fifo_full),  // Connect full signal
    .data_in(ps2_key_data),
    .data_out(uio_out)
  );

  ps2_decoder ps2_decoder_inst (
    .clk(clk),
    .reset(~rst_n),
    .VPWR(VPWR),
    .VGND(VGND),
    .ps2_clk(ps2_clk_internal),
    .ps2_data(ps2_data_internal),
    .data(ps2_key_data),
    .valid(valid),
    .interupt(interupt),
    .int_clear(int_clear)
  );
endmodule
