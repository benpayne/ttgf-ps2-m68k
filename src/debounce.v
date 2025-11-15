
//
// This is a simple debouncer that will output the input signal after it has been stable for 128 clocks.
// Includes 2-FF synchronizer to prevent metastability from async inputs.
//

module debounce (
    input wire clk,
    input wire reset,
    inout wire VPWR,     // Power rail
    inout wire VGND,     // Ground rail
    input wire button,
    output wire debounced_button
);
    // 2-FF synchronizer to prevent metastability
    reg        sync_ff1;
    reg        sync_ff2;

    reg [7:0]  counter;  // use high bit to flag completion
    reg        debounced_button_reg;
    reg        last_button;

    assign debounced_button = debounced_button_reg;

    // First synchronizer stage (may capture metastable state)
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            sync_ff1 <= 0;
            sync_ff2 <= 0;
        end else begin
            sync_ff1 <= button;
            sync_ff2 <= sync_ff1;  // Second stage ensures stability
        end
    end

    // Debounce logic using synchronized signal
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            counter <= 0;
            debounced_button_reg <= 0;
            last_button <= 0;
        end else begin
            last_button <= sync_ff2;  // Use synchronized signal
            if (sync_ff2 != last_button) begin
                counter <= 0;
            end else if (counter[7] == 1) begin
                debounced_button_reg <= last_button;
            end else begin
                counter <= counter + 1;
            end
        end
    end

endmodule
