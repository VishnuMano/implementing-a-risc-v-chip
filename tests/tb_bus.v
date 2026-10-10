`timescale 1ns/1ps
// Isolate the bus from the CPU so corner cases are tested independently of firmware.
module tb_bus;
    reg clk=0, resetn=0;
    always #5 clk=!clk;
    wire tx, trap;
    wire [7:0] gpio;
    soc #(.UART_DIV(4)) dut(.clk(clk), .resetn(resetn),
        .uart_tx_o(tx), .gpio_o(gpio), .trap_o(trap));
    reg valid=0;
    reg [31:0] addr=0, wdata=0;
    reg [3:0] strobe=0;
    reg [31:0] value, saved_rom, old_timer;
    integer waits;
    task access;
        input [31:0] a, d;
        input [3:0] s;
        output [31:0] result;
        begin
            @(negedge clk); addr=a; wdata=d; strobe=s; valid=1;
            waits=0;
            @(negedge clk);
            while (!dut.mem_ready) begin
                waits=waits+1;
                if(waits>100) $fatal(1,"Bus timeout");
                @(negedge clk);
            end
            result=dut.mem_rdata;
            valid=0;
            @(negedge clk);
        end
    endtask
    initial begin
        force dut.mem_valid=valid;
        force dut.mem_addr=addr;
        force dut.mem_wdata=wdata;
        force dut.mem_wstrb=strobe;
        repeat(4) @(negedge clk); resetn=1;
        access(32'h10000000,32'h11223344,4'hf,value);
        access(32'h10000000,32'haabbccdd,4'h5,value);
        access(32'h10000000,0,0,value);
        if(value!==32'h11bb33dd) $fatal(1,"RAM byte enables");
        access(32'h100003fc,32'habcdef12,4'hf,value);
        access(32'h100003fc,0,0,value);
        if(value!==32'habcdef12) $fatal(1,"RAM upper boundary");
        access(32'h10000400,0,0,value);
        if(value!==32'hdeadbeef) $fatal(1,"RAM boundary alias");
        access(0,0,0,saved_rom);
        access(0,32'hffffffff,4'hf,value);
        access(0,0,0,value);
        if(value!==saved_rom) $fatal(1,"ROM was writable");
        access(32'h20000008,32'h123456a5,4'h1,value);
        access(32'h20000008,32'h00001100,4'h2,value);
        access(32'h20000008,0,0,value);
        if(value!==32'ha5 || gpio!==8'ha5) $fatal(1,"GPIO byte enables");
        access(32'h2000000c,0,0,old_timer);
        access(32'h2000000c,0,0,value);
        if(value<=old_timer) $fatal(1,"Timer did not advance");
        access(32'h30000000,0,0,value);
        if(value!==32'hdeadbeef) $fatal(1,"Unmapped read");
        access(32'h20000000,32'h55,4'h1,value);
        access(32'h20000004,0,0,value);
        if(value!==1) $fatal(1,"UART busy status");
        access(32'h20000000,32'haa,4'h1,value);
        if(waits<20) $fatal(1,"UART failed to back-pressure");
        resetn=0; repeat(2) @(negedge clk);
        if(tx!==1 || gpio!==0 || dut.mem_ready!==0) $fatal(1,"Reset during UART");
        $display("BUS PASS: byte writes, boundaries, ROM protection, GPIO, timer, UART stall/reset");
        $finish;
    end
endmodule
