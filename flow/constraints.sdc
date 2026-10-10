# Clock period comes from the resolved flow configuration, so sweep runs agree.
create_clock -name core_clk -period $::env(CLOCK_PERIOD) [get_ports clk]
set_clock_uncertainty 0.25 [get_clocks core_clk]
set_input_delay -clock core_clk -max 10 [get_ports resetn]
set_input_delay -clock core_clk -min 0 [get_ports resetn]
set_output_delay -clock core_clk -max 10 [get_ports {uart_tx_o gpio_o[*] trap_o}]
set_output_delay -clock core_clk -min 0 [get_ports {uart_tx_o gpio_o[*] trap_o}]
set_input_transition 0.1 [get_ports {clk resetn}]
set_load 0.05 [get_ports {uart_tx_o gpio_o[*] trap_o}]
