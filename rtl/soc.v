`default_nettype none
// Educational SoC core: external synchronous clock/reset, no pad ring.
module soc #(parameter integer UART_DIV = 87)(
    input wire clk, input wire resetn,
    output wire uart_tx_o, output reg [7:0] gpio_o,
    output wire trap_o
);
    wire mem_valid;
    wire [31:0] mem_addr, mem_wdata;
    wire [3:0] mem_wstrb;
    reg mem_ready;
    reg [31:0] mem_rdata;
    reg [31:0] ram [0:255];
    reg [31:0] timer;
    wire [31:0] rom_data;
    wire uart_busy;
    wire request = mem_valid && !mem_ready;
    wire uart_send = resetn && request && mem_addr == 32'h20000000 &&
                     mem_wstrb[0] && !uart_busy;

    picorv32 #(
        .PROGADDR_RESET(32'h00000000), .STACKADDR(32'h10000400),
        .ENABLE_IRQ(0), .ENABLE_MUL(0), .ENABLE_DIV(0),
        .COMPRESSED_ISA(0), .REGS_INIT_ZERO(0)
    ) cpu (
        .clk(clk), .resetn(resetn), .trap(trap_o),
        .mem_valid(mem_valid), .mem_instr(), .mem_ready(mem_ready),
        .mem_addr(mem_addr), .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb), .mem_rdata(mem_rdata),
        .mem_la_read(), .mem_la_write(), .mem_la_addr(),
        .mem_la_wdata(), .mem_la_wstrb(),
        .pcpi_valid(), .pcpi_insn(), .pcpi_rs1(), .pcpi_rs2(),
        .pcpi_wr(1'b0), .pcpi_rd(32'b0), .pcpi_wait(1'b0),
        .pcpi_ready(1'b0), .irq(32'b0), .eoi(),
        .trace_valid(), .trace_data()
    );
    boot_rom rom (.addr(mem_addr[11:2]), .data(rom_data));
    uart_tx #(.CLOCKS_PER_BIT(UART_DIV)) uart (
        .clk(clk), .resetn(resetn), .send(uart_send),
        .data(mem_wdata[7:0]), .tx(uart_tx_o), .busy(uart_busy)
    );

    integer lane;
    always @(posedge clk) begin
        if (!resetn) begin
            mem_ready <= 0;
            mem_rdata <= 0;
            gpio_o <= 0;
            timer <= 0;
        end else begin
            timer <= timer + 1'b1;
            mem_ready <= 0;
            if (request) begin
                mem_ready <= 1;
                mem_rdata <= 32'hdeadbeef;
                if (mem_addr < 32'h00001000) begin
                    // ROM writes are acknowledged but ignored.
                    mem_rdata <= rom_data;
                end else if (mem_addr >= 32'h10000000 && mem_addr < 32'h10000400) begin
                    mem_rdata <= ram[mem_addr[9:2]];
                    for (lane = 0; lane < 4; lane = lane + 1)
                        if (mem_wstrb[lane])
                            ram[mem_addr[9:2]][lane*8 +: 8] <= mem_wdata[lane*8 +: 8];
                end else if (mem_addr == 32'h20000000) begin
                    mem_rdata <= 0;
                    // Back-pressure an attempted UART write until idle.
                    if (mem_wstrb[0] && uart_busy) mem_ready <= 0;
                end else if (mem_addr == 32'h20000004) begin
                    mem_rdata <= {31'b0, uart_busy};
                end else if (mem_addr == 32'h20000008) begin
                    mem_rdata <= {24'b0, gpio_o};
                    if (mem_wstrb[0]) gpio_o <= mem_wdata[7:0];
                end else if (mem_addr == 32'h2000000c) begin
                    mem_rdata <= timer;
                end
            end
        end
    end
endmodule
`default_nettype wire
