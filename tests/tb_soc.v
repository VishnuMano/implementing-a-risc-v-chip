`timescale 1ns/1ps
module tb_soc;
    localparam DIV = 87;
    reg clk = 0;
    always #50 clk = !clk; // 10 MHz
    reg resetn = 0;
    wire tx, trap;
    wire [7:0] gpio;
`ifdef GATE_TEST
    soc dut (.clk(clk), .resetn(resetn),
`else
    soc #(.UART_DIV(DIV)) dut (.clk(clk), .resetn(resetn),
`endif
        .uart_tx_o(tx), .gpio_o(gpio), .trap_o(trap));
    reg [7:0] byte_value;
    reg [8*64-1:0] message = 0;
    integer i, count = 0;
    integer cycles = 0;
    integer out_file, trace_file;
    initial begin
`ifdef GATE_TEST
        $dumpfile("build/gate.vcd");
        $dumpvars(1, tb_soc);
        out_file = $fopen("build/gate_uart.txt", "w");
        trace_file = $fopen("build/gate_bus.csv", "w");
`else
        $dumpfile("build/soc.vcd");
        $dumpvars(0, tb_soc);
        out_file = $fopen("build/uart.txt", "w");
        trace_file = $fopen("build/bus.csv", "w");
`endif
        $fdisplay(trace_file, "cycle,address,write_strobes,write_data,read_data");
        repeat (8) @(negedge clk);
        resetn = 1;
    end
    always @(posedge clk) begin
        cycles <= cycles + 1;
        if (resetn && trap) $fatal(1, "CPU trapped at cycle %0d", cycles);
        if (cycles > 250000) $fatal(1, "Firmware timeout");
        if (resetn && dut.mem_valid && dut.mem_ready)
            $fdisplay(trace_file, "%0d,%08x,%x,%08x,%08x", cycles,
                dut.mem_addr, dut.mem_wstrb, dut.mem_wdata, dut.mem_rdata);
    end
    // Decode the physical UART output, rather than observing its write register.
    initial forever begin
        @(negedge tx);
        repeat (DIV/2) @(negedge clk);
        if (tx !== 0) $fatal(1, "Invalid UART start bit");
        for (i = 0; i < 8; i = i + 1) begin
            repeat (DIV) @(negedge clk);
            byte_value[i] = tx;
        end
        repeat (DIV) @(negedge clk);
        if (tx !== 1) $fatal(1, "Invalid UART stop bit");
        message = {message[8*63-1:0], byte_value};
        count = count + 1;
        $fwrite(out_file, "%c", byte_value);
        $write("%c", byte_value);
        if (message[39:0] == "PASS\n") begin
            if (message !== "Hello from RTL!\nchecksum=0x00002040\nPASS\n")
                $fatal(1, "Unexpected UART transcript");
            if (gpio !== 8'ha5) $fatal(1, "GPIO result mismatch");
            $fclose(out_file); $fclose(trace_file);
            $display("SIMULATION PASS: %0d bytes, %0d cycles", count, cycles);
            $finish;
        end
        if (message[39:0] == "FAIL\n") $fatal(1, "Firmware reported failure");
    end
endmodule
