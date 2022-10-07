`timescale 1ns / 1ps
`default_nettype none

`define CODE_FOR_MIO3

`include "monopix2_core.v"
`include "clk_gen.v"

`include "timestamp640/timestamp640.v"
`include "timestamp640/timestamp640_core.v"
`include "mono_data_rx/mono_data_rx.v"
`include "mono_data_rx/mono_data_rx_core.v"
`include "pulse_gen640/pulse_gen640.v"
`include "pulse_gen640/pulse_gen640_core.v"
`include "tlu_slave/tlu_slave.v"
`include "tlu_slave/tlu_slave_core.v"
`include "tlu_slave/tlu_slave_fsm.v"

//basil
`include "spi/spi_core.v"
`include "spi/spi.v"
`include "spi/blk_mem_gen_8_to_1_2k.v"
`include "timestamp640/timestamp640.v"
`include "timestamp640/timestamp640_core.v"
`include "pulse_gen/pulse_gen.v"
`include "pulse_gen/pulse_gen_core.v"
`include "sram_fifo/sram_fifo_core.v"
`include "sram_fifo/sram_fifo.v"
`include "gpio/gpio.v"
`include "gpio/gpio_core.v"
`include "rrp_arbiter/rrp_arbiter.v"

`include "utils/bus_to_ip.v"
`include "utils/fx2_to_bus.v"
`include "utils/reset_gen.v"
`include "utils/generic_fifo.v"
`include "utils/CG_MOD_pos.v"
`include "utils/cdc_pulse_sync.v"
`include "utils/cdc_syncfifo.v"
`include "utils/cdc_reset_sync.v"
`include "utils/ddr_des.v"
`include "utils/3_stage_synchronizer.v"
`include "utils/flag_domain_crossing.v"
`include "utils/fifo_32_to_8.v"
`include "utils/clock_divider.v"

`include "i2c/i2c.v"
`include "i2c/i2c_core.v"
`include "utils/rgmii_io.v"
`include "utils/rbcp_to_bus.v"

////SiTCP
`include "WRAP_SiTCP_GMII_XC7K_32K.V"
`include "SiTCP_XC7K_32K_BBT_V110.V"
`include "TIMER.v"

module monopix2_mio3(
// FPGA clk
    input wire FCLK_IN, // 100MHz
//LED, Triggers
    output wire [7:0] LED,
    input wire [1:0] LEMO_RX,
    input wire InjLoopIn,       //RX2 or flatcable 6
    output wire TLU_CLK,        //TX0 and RJ45
    output wire TLU_BUSY,       //TX1 and RJ45
    output wire InjLoopOut,     //TX2 or flatcable 5
    input wire TLU_RESET,       //RJ45
    input wire TLU_TRIGGER,     //RJ45
// Chip Reset & Clock
    output wire ResetBcid, //DOUT0
    output wire nRst,      //DOUT1
    output wire ClkOut,    //DOUT2
    output wire ClkBX,     //DOUT5
    output wire ClkSR,     //DOUT11
// Chip Configuration
    output wire En_Cnfg_Pix,   //DOUT7
    output wire Def_Cnfg,  //DOUT8
    output wire Ld,        //DOUT9
    output wire Si,        //DOUT10
    input  wire So,        //DIN0
// Chip RO
    output wire Freeze,    //DOUT3
    output wire Read,      //DOUT4
    input wire TokOut,     //DIN4
    input wire DataOut,    //DIN6
    input wire LVDS_Out,   //LVDSIN0
// Chip Injection & Monitor
    output wire Injection, //DOUT6
    input wire HitOr,     //DIN2
// DEBUG
    output wire DEBUG_MUTINJRISE,  //DOUT14
    output wire DEBUG,  //DOUT15
// I2C
    inout wire SDA,
    inout wire SCL,
// declarations below are for MIO3 only    
    input wire RESET_N,    
    output wire [3:0] rgmii_txd,
    output wire rgmii_tx_ctl,
    output wire rgmii_txc,
    input wire [3:0] rgmii_rxd,
    input wire rgmii_rx_ctl,
    input wire rgmii_rxc,
    output wire mdio_phy_mdc,
    inout wire mdio_phy_mdio,
    output wire phy_rst_n
);


// ------- RESRT/CLOCK  ------- //
    wire RST;
    wire BUS_CLK_PLL, CLK250PLL, CLK125PLLTX, CLK125PLLTX90, CLK125PLLRX;
    wire PLL_FEEDBACK, LOCKED;


// -------  PLL for communication with FPGA  ------- //
    PLLE2_BASE #(
        .BANDWIDTH("OPTIMIZED"),  // OPTIMIZED, HIGH, LOW
        .CLKFBOUT_MULT(10),       // Multiply value for all CLKOUT, (2-64)
        .CLKFBOUT_PHASE(0.0),     // Phase offset in degrees of CLKFB, (-360.000-360.000).
        .CLKIN1_PERIOD(10.000),      // Input clock period in ns to ps resolution (i.e. 33.333 is 30 MHz).
        .DIVCLK_DIVIDE(1),        // Master division value, (1-56)
        .REF_JITTER1(0.0),        // Reference input jitter in UI, (0.000-0.999).
        .STARTUP_WAIT("FALSE"),     // Delay DONE until PLL Locks, ("TRUE"/"FALSE")
        
        .CLKOUT0_DIVIDE(7),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT0_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT0_PHASE(0.0),      // Phase offset for CLKOUT0 (-360.000-360.000).

        .CLKOUT1_DIVIDE(4),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT1_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT1_PHASE(0.0),      // Phase offset for CLKOUT0 (-360.000-360.000).

        .CLKOUT2_DIVIDE(8),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT2_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT2_PHASE(0.0),      // Phase offset for CLKOUT0 (-360.000-360.000).

        .CLKOUT3_DIVIDE(8),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT3_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT3_PHASE(90.0),      // Phase offset for CLKOUT0 (-360.000-360.000).

        .CLKOUT4_DIVIDE(8),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT4_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT4_PHASE(-5.6)      // Phase offset for CLKOUT0 (-360.000-360.000).
        //-65 -> 0?; - 45 -> 39;  -25 -> 100; -5 -> 0;
     )
     PLLE2_BASE_inst_comm (
//        .CLKOUT0(BUS_CLK_PLL),
        .CLKOUT0(),
        .CLKOUT1(CLK250PLL),
        .CLKOUT2(CLK125PLLTX),
        .CLKOUT3(CLK125PLLTX90),
        .CLKOUT4(CLK125PLLRX),
        
        .CLKFBOUT(PLL_FEEDBACK),
        
        .LOCKED(LOCKED),     // 1-bit output: LOCK
        
        // Input 100 MHz clock
        .CLKIN1(FCLK_IN),
        
        // Control Ports
        .PWRDWN(0),
        .RST(!RESET_N),
        
        // Feedback
         .CLKFBIN(PLL_FEEDBACK)
     );

//    BUFG BUFG_inst_BUS_CKL (.O(BUS_CLK), .I(BUS_CLK_PLL) );

    wire CLK125TX, CLK125TX90, CLK125RX;
    BUFG BUFG_inst_CLK125TX (  .O(CLK125TX),  .I(CLK125PLLTX) );
    BUFG BUFG_inst_CLK125TX90 (  .O(CLK125TX90),  .I(CLK125PLLTX90) );
    BUFG BUFG_inst_CLK125RX (  .O(CLK125RX),  .I(rgmii_rxc) );


// -------  PLL for clk synthesis  ------- //

    (* KEEP = "{TRUE}" *) wire CLK320;  
    (* KEEP = "{TRUE}" *) wire CLK160;
    (* KEEP = "{TRUE}" *) wire CLK40;
    (* KEEP = "{TRUE}" *) wire CLK16;
    (* KEEP = "{TRUE}" *) wire BUS_CLK;
    (* KEEP = "{TRUE}" *) wire CLK8;

    wire PLL_FEEDBACK2, LOCKED2;
    wire CLK8_PLL, CLK16_PLL, CLK40_PLL, CLK160_PLL, CLK320_PLL;

    PLLE2_BASE #(
        .BANDWIDTH("OPTIMIZED"),  // OPTIMIZED, HIGH, LOW
        .CLKFBOUT_MULT(48),       // Multiply value for all CLKOUT, (2-64)
        .CLKFBOUT_PHASE(0.0),     // Phase offset in degrees of CLKFB, (-360.000-360.000).
        .CLKIN1_PERIOD(10.000),      // Input clock period in ns to ps resolution (i.e. 33.333 is 30 MHz).
        .DIVCLK_DIVIDE(5),        // Master division value, (1-56)
        .REF_JITTER1(0.0),        // Reference input jitter in UI, (0.000-0.999).
        .STARTUP_WAIT("FALSE"),     // Delay DONE until PLL Locks, ("TRUE"/"FALSE")

        .CLKOUT0_DIVIDE(120),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT0_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT0_PHASE(0.0),      // Phase offset for CLKOUT0 (-360.000-360.000).

        .CLKOUT1_DIVIDE(60),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT1_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT1_PHASE(0.0),      // Phase offset for CLKOUT0 (-360.000-360.000).

        .CLKOUT2_DIVIDE(24),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT2_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT2_PHASE(0.0),      // Phase offset for CLKOUT0 (-360.000-360.000).

        .CLKOUT3_DIVIDE(6),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT3_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT3_PHASE(0.0),      // Phase offset for CLKOUT0 (-360.000-360.000).

        .CLKOUT4_DIVIDE(3),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT4_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT4_PHASE(0.0),      // Phase offset for CLKOUT0 (-360.000-360.000).
        
        .CLKOUT5_DIVIDE(7),     // Divide amount for CLKOUT0 (1-128)
        .CLKOUT5_DUTY_CYCLE(0.5), // Duty cycle for CLKOUT0 (0.001-0.999).
        .CLKOUT5_PHASE(0.0)      // Phase offset for CLKOUT0 (-360.000-360.000).

     )
     PLLE2_BASE_inst_clk (
     
        .CLKOUT0(CLK8_PLL),
        .CLKOUT1(CLK16_PLL),
        .CLKOUT2(CLK40_PLL),
        .CLKOUT3(CLK160_PLL),
        .CLKOUT4(CLK320_PLL),
        .CLKOUT5(BUS_CLK_PLL),
        
        .CLKFBOUT(PLL_FEEDBACK2),
        
        .LOCKED(LOCKED2),     // 1-bit output: LOCK
        
        // Input 100 MHz clock
        .CLKIN1(FCLK_IN),
        
        // Control Ports
        .PWRDWN(0),
        .RST(!RESET_N),
        
        // Feedback
        .CLKFBIN(PLL_FEEDBACK2)
     );

    BUFG BUFG_inst_BUS_CKL (.O(BUS_CLK), .I(BUS_CLK_PLL) );

    BUFG BUFG_inst_CLK8 (  .O(CLK8),  .I(CLK8_PLL) );
    BUFG BUFG_inst_CLK16 (  .O(CLK16),  .I(CLK16_PLL) );
    BUFG BUFG_inst_CLK40 (  .O(CLK40),  .I(CLK40_PLL) );
    BUFG BUFG_inst_CLK160 (  .O(CLK160),  .I(CLK160_PLL) );
    BUFG BUFG_inst_CLK320 (  .O(CLK320),  .I(CLK320_PLL) );

     assign RST = !RESET_N | !LOCKED;
     wire   gmii_tx_clk;
     wire   gmii_tx_en;
     wire  [7:0] gmii_txd;
     wire   gmii_tx_er;
     wire   gmii_crs;
     wire   gmii_col;
     wire   gmii_rx_clk;
     wire   gmii_rx_dv;
     wire  [7:0] gmii_rxd;
     wire   gmii_rx_er;
     wire   mdio_gem_mdc;
     wire   mdio_gem_i;
     wire   mdio_gem_o;
     wire   mdio_gem_t;
     wire   link_status;
     wire  [1:0] clock_speed;
     wire   duplex_status;

    rgmii_io rgmii
    (
        .rgmii_txd(rgmii_txd),
        .rgmii_tx_ctl(rgmii_tx_ctl),
        .rgmii_txc(rgmii_txc),

        .rgmii_rxd(rgmii_rxd),
        .rgmii_rx_ctl(rgmii_rx_ctl),

        .gmii_txd_int(gmii_txd),      // Internal gmii_txd signal.
        .gmii_tx_en_int(gmii_tx_en),
        .gmii_tx_er_int(gmii_tx_er),
        .gmii_col_int(gmii_col),
        .gmii_crs_int(gmii_crs),
        .gmii_rxd_reg(gmii_rxd),   // RGMII double data rate data valid.
        .gmii_rx_dv_reg(gmii_rx_dv), // gmii_rx_dv_ibuf registered in IOBs.
        .gmii_rx_er_reg(gmii_rx_er), // gmii_rx_er_ibuf registered in IOBs.

        .eth_link_status(link_status),
        .eth_clock_speed(clock_speed),
        .eth_duplex_status(duplex_status),

                                  // FOllowing are generated by DCMs
        .tx_rgmii_clk_int(CLK125TX),     // Internal RGMII transmitter clock.
        .tx_rgmii_clk90_int(CLK125TX90),   // Internal RGMII transmitter clock w/ 90 deg phase
        .rx_rgmii_clk_int(CLK125RX),     // Internal RGMII receiver clock

        .reset(!phy_rst_n)
    );

// Instantiate tri-state buffer for MDIO
    IOBUF i_iobuf_mdio(
        .O(mdio_gem_i),
        .IO(mdio_phy_mdio),
        .I(mdio_gem_o),
        .T(mdio_gem_t));

    wire EEPROM_CS, EEPROM_SK, EEPROM_DI;
    wire TCP_CLOSE_REQ;
    wire RBCP_ACT, RBCP_WE, RBCP_RE;
    wire [7:0] RBCP_WD, RBCP_RD;
    wire [31:0] RBCP_ADDR;
    wire TCP_RX_WR;
    wire [7:0] TCP_RX_DATA;
    wire RBCP_ACK;
    wire SiTCP_RST;

    wire TCP_TX_FULL;
    wire TCP_TX_WR;
    wire [7:0] TCP_TX_DATA;
    
    WRAP_SiTCP_GMII_XC7K_32K sitcp(
        .CLK(BUS_CLK)                    ,    // in    : System Clock >129MHz
        .RST(RST)                    ,    // in    : System reset
        // Configuration parameters
        .FORCE_DEFAULTn(1'b0)        ,    // in   
        .EXT_IP_ADDR(32'hc0a80a13)            ,    // in    : IP address[31:0] 192.168.10.19  16=telescope, 17,18=oldFPGA, 19=newFPGA
        .EXT_TCP_PORT(16'd24)        ,    // in    : TCP port #[15:0]
        .EXT_RBCP_PORT(16'd4660)        ,    // in    : RBCP port #[15:0]
        .PHY_ADDR(5'd3)            ,    // in    : PHY-device MIF address[4:0]
        // EEPROM
        .EEPROM_CS(EEPROM_CS)            ,    // out    : Chip select
        .EEPROM_SK(EEPROM_SK)            ,    // out    : Serial data clock
        .EEPROM_DI(EEPROM_DI)            ,    // out    : Serial write data
        .EEPROM_DO(1'b0)            ,    // in    : Serial read data
        // user data, intialial values are stored in the EEPROM, 0xFFFF_FC3C-3F
        .USR_REG_X3C()            ,    // out    : Stored at 0xFFFF_FF3C
        .USR_REG_X3D()            ,    // out    : Stored at 0xFFFF_FF3D
        .USR_REG_X3E()            ,    // out    : Stored at 0xFFFF_FF3E
        .USR_REG_X3F()            ,    // out    : Stored at 0xFFFF_FF3F
        // MII interface
        .GMII_RSTn(phy_rst_n)            ,    // out    : PHY reset
        .GMII_1000M(1'b1)            ,    // in    : GMII mode (0:MII, 1:GMII)
        // TX 
        .GMII_TX_CLK(CLK125TX)            ,    // in    : Tx clock
        .GMII_TX_EN(gmii_tx_en)            ,    // out    : Tx enable
        .GMII_TXD(gmii_txd)            ,    // out    : Tx data[7:0]
        .GMII_TX_ER(gmii_tx_er)            ,    // out    : TX error
        // RX
        .GMII_RX_CLK(CLK125RX)           ,    // in    : Rx clock
        .GMII_RX_DV(gmii_rx_dv)            ,    // in    : Rx data valid
        .GMII_RXD(gmii_rxd)            ,    // in    : Rx data[7:0]
        .GMII_RX_ER(gmii_rx_er)            ,    // in    : Rx error
        .GMII_CRS(gmii_crs)            ,    // in    : Carrier sense
        .GMII_COL(gmii_col)            ,    // in    : Collision detected
        // Management IF
        .GMII_MDC(mdio_phy_mdc)            ,    // out    : Clock for MDIO
        .GMII_MDIO_IN(mdio_gem_i)        ,    // in    : Data
        .GMII_MDIO_OUT(mdio_gem_o)        ,    // out    : Data
        .GMII_MDIO_OE(mdio_gem_t)        ,    // out    : MDIO output enable
        // User I/F
        .SiTCP_RST(SiTCP_RST)            ,    // out    : Reset for SiTCP and related circuits
        // TCP connection control
        .TCP_OPEN_REQ(1'b0)        ,    // in    : Reserved input, shoud be 0
        .TCP_OPEN_ACK()        ,    // out    : Acknowledge for open (=Socket busy)
        .TCP_ERROR()            ,    // out    : TCP error, its active period is equal to MSL
        .TCP_CLOSE_REQ(TCP_CLOSE_REQ)        ,    // out    : Connection close request
        .TCP_CLOSE_ACK(TCP_CLOSE_REQ)        ,    // in    : Acknowledge for closing
        // FIFO I/F
        .TCP_RX_WC(1'b1)            ,    // in    : Rx FIFO write count[15:0] (Unused bits should be set 1)
        .TCP_RX_WR(TCP_RX_WR)            ,    // out    : Write enable
        .TCP_RX_DATA(TCP_RX_DATA)            ,    // out    : Write data[7:0]
        .TCP_TX_FULL(TCP_TX_FULL)            ,    // out    : Almost full flag
        .TCP_TX_WR(TCP_TX_WR)            ,    // in    : Write enable
        .TCP_TX_DATA(TCP_TX_DATA)            ,    // in    : Write data[7:0]
        // RBCP
        .RBCP_ACT(RBCP_ACT)            ,    // out    : RBCP active
        .RBCP_ADDR(RBCP_ADDR)            ,    // out    : Address[31:0]
        .RBCP_WD(RBCP_WD)                ,    // out    : Data[7:0]
        .RBCP_WE(RBCP_WE)                ,    // out    : Write enable
        .RBCP_RE(RBCP_RE)                ,    // out    : Read enable
        .RBCP_ACK(RBCP_ACK)            ,    // in    : Access acknowledge
        .RBCP_RD(RBCP_RD)                    // in    : Read data[7:0]
    );

// -------  BUS SYGNALING  ------- //
    wire BUS_WR, BUS_RD, BUS_RST;
    wire [31:0] BUS_ADD;
    wire [7:0] BUS_DATA;
    assign BUS_RST = SiTCP_RST;

    rbcp_to_bus irbcp_to_bus(
        .BUS_RST(BUS_RST),
        .BUS_CLK(BUS_CLK),

        .RBCP_ACT(RBCP_ACT),
        .RBCP_ADDR(RBCP_ADDR),
        .RBCP_WD(RBCP_WD),
        .RBCP_WE(RBCP_WE),
        .RBCP_RE(RBCP_RE),
        .RBCP_ACK(RBCP_ACK),
        .RBCP_RD(RBCP_RD),

        .BUS_WR(BUS_WR),
        .BUS_RD(BUS_RD),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA(BUS_DATA)
    ); 

// -------  MODULE ADREESSES  ------- //
    localparam I2C_BASEADDR = 32'h2000;
    localparam I2C_HIGHADDR = 32'h3000-1;
    localparam ABUSWIDTH = 32;
    
// ------- MODULES for GPAC - I2C module  ------- //   
    wire I2C_CLK;
    
    clock_divider #(
    .DIVISOR(1500)
    ) i_clock_divisor_spi (
        .CLK(BUS_CLK),
        .RESET(1'b0),
        .CE(),
        .CLOCK(I2C_CLK)
    );
    
    i2c
    #(
        .BASEADDR(I2C_BASEADDR),
        .HIGHADDR(I2C_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH),
        .MEM_BYTES(64)
    )  i_i2c
    (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(BUS_RST),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA(BUS_DATA[7:0]),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),
    
        .I2C_CLK(I2C_CLK),
        .I2C_SDA(SDA),
        .I2C_SCL(SCL)
    );

// -------  MODULES for fast data readout(FIFO) - cdc_fifo is for timing reasons
    wire ARB_READY_OUT,ARB_WRITE_OUT;
    wire [31:0]ARB_DATA_OUT;
    wire FIFO_FULL,FIFO_NEAR_FULL;
    wire [31:0] cdc_data_out;
    wire full_32to8, cdc_fifo_empty;
    cdc_syncfifo #(.DSIZE(32), .ASIZE(3)) cdc_syncfifo_i
    (
        .rdata(cdc_data_out),
        .wfull(FIFO_FULL),
        .rempty(cdc_fifo_empty),
        .wdata(ARB_DATA_OUT),
        .winc(ARB_WRITE_OUT), .wclk(BUS_CLK), .wrst(BUS_RST),
        .rinc(!full_32to8), .rclk(BUS_CLK), .rrst(BUS_RST)
    );
    assign ARB_READY_OUT = !FIFO_FULL;
    
    wire FIFO_EMPTY;
    fifo_32_to_8 #(.DEPTH(32*1024)) i_data_fifo (
        .RST(BUS_RST),
        .CLK(BUS_CLK),
        
        .WRITE(!cdc_fifo_empty),
        .READ(TCP_TX_WR),
        .DATA_IN(cdc_data_out),
        .FULL(full_32to8),
        .EMPTY(FIFO_EMPTY),
        .DATA_OUT(TCP_TX_DATA)
    );

    assign TCP_TX_WR = !TCP_TX_FULL && !FIFO_EMPTY;

// -------  USER CORE ------- //

assign LED[7]= 1'b0;
assign LED[6]= 1'b1;
assign LED[5]= 1'b0;

monopix2_core i_monopix2_core(
//local bus
    .BUS_CLK(BUS_CLK),
    .BUS_DATA(BUS_DATA),
    .BUS_ADD(BUS_ADD),
    .BUS_RD(BUS_RD),
    .BUS_WR(BUS_WR),
    .BUS_RST(BUS_RST),
//clocks
    .CLK8(CLK8),
    .CLK40(CLK40),
    .CLK16(CLK16),
    .CLK160(CLK160),
    .CLK320(CLK320),
//fifo
    .ARB_READY_OUT(ARB_READY_OUT),
    .ARB_WRITE_OUT(ARB_WRITE_OUT),
    .ARB_DATA_OUT(ARB_DATA_OUT),
    .FIFO_FULL(FIFO_FULL),
    .FIFO_NEAR_FULL(FIFO_NEAR_FULL),
//LED, LEMO, RJ45, Flatcable
    .LED(LED[4:0]),
    .LEMO_RX(LEMO_RX),
    .InjLoopIn(InjLoopIn), //Flatcable6
    .TLU_CLK(TLU_CLK),
    .TLU_BUSY(TLU_BUSY),
    .InjLoopOut(InjLoopOut), //Flatcable5 or TX2
    .TLU_RESET(TLU_RESET),
    .TLU_TRIGGER(TLU_TRIGGER),
// chip Clock & reset
    .ResetBcid(ResetBcid),   //DOUT0
    .nRst(nRst),             //DOUT1
    .ClkOut(ClkOut),         //DOUT2
    .ClkBX(ClkBX),           //DOUT5
    .ClkSR(ClkSR),           //DOUT11
// Chip Configuration
    .En_Cnfg_Pix(En_Cnfg_Pix),  //DOUT7
    .Def_Cnfg(Def_Cnfg),     //DOUT8
    .Ld(Ld),                 //DOUT9
    .Si(Si),                 //DOUT10
    .So(So),                 //DIN0
// Chip RO
    .Freeze(Freeze),       //DOUT3
    .Read(Read),           //DOUT4
    .Injection(Injection), //DOUT6
    .HitOr(HitOr),         //DIN2
    .TokOut(TokOut),       //DIN4
    .DataOut(DataOut),     //DIN6
    .LVDS_Out(LVDS_Out),   //LVDSIN0
    .DEBUG_MUTINJRISE(DEBUG_MUTINJRISE),
    .DEBUG(DEBUG)
);

// "ila" commands to debug read-out at an FPGA level. Not setup for the script-based firmware compilation, as it requires extra work on Vivado.
// ila_0 ila (.clk(CLK40), .probe0({1'b0,i_monopix2_core.mono_data_rx.mono_data_rx_core.CONF_FORCE_READ, i_monopix2_core.mono_data_rx.mono_data_rx_core.state[3:0], i_monopix2_core.mono_data_rx.mono_data_rx_core.RX_READ, i_monopix2_core.mono_data_rx.mono_data_rx_core.RX_FREEZE, i_monopix2_core.mono_data_rx.mono_data_rx_core.RX_TOKEN}));
 
endmodule
