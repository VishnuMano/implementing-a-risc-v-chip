`default_nettype none
// 8N1 UART. A send pulse is accepted only while idle. No derived clocks.
module uart_tx #(parameter integer CLOCKS_PER_BIT = 87)(
    input wire clk, input wire resetn,
    input wire send, input wire [7:0] data,
    output wire tx, output wire busy
);
    reg [9:0] frame;
    reg [3:0] bits_left;
    reg [15:0] ticks;
    assign busy = bits_left != 0;
    assign tx = busy ? frame[0] : 1'b1;
    always @(posedge clk) begin
        if (!resetn) begin
            frame <= 10'h3ff;
            bits_left <= 0;
            ticks <= 0;
        end else if (!busy) begin
            if (send) begin
                frame <= {1'b1, data, 1'b0};
                bits_left <= 10;
                ticks <= CLOCKS_PER_BIT - 1;
            end
        end else if (ticks == 0) begin
            frame <= {1'b1, frame[9:1]};
            bits_left <= bits_left - 1'b1;
            ticks <= CLOCKS_PER_BIT - 1;
        end else ticks <= ticks - 1'b1;
    end
endmodule
`default_nettype wire
