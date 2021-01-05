module clk_gen
(
    input CLKIN, //48 MHz
    output BUS_CLK,
    output U1_CLK8,
    output U2_CLK40,
    output U2_CLK16,
    output U2_CLK160,
    output U2_CLK320,
    output U2_LOCKED
);
`systemc_header
    extern vluint64_t main_time;
`systemc_interface
    bool clk640(bool clk_in) {
        bool clko;
        clko = ((main_time-1) /260) % 2 == 0; 
        return clko;
    }
`verilog
    wire CLK;
    reg [7:0] cnt_reg = 8'b00000000;
    reg CLK160_reg = 1'b0;
    reg CLK16_reg = 1'b0;
    reg CLK320_reg = 1'b0;
    reg CLK40_reg = 1'b0;
    reg CLK8_reg = 1'b0;
    reg BUS_CLK_reg = 1'b0;
    reg CLK_reg = 1'b0;
    reg CLK640_reg = 1'b0;

    assign CLK = CLK_reg;
    assign U2_CLK160 = CLK160_reg;
    assign U2_CLK16  = CLK16_reg;
    assign U2_CLK320 = CLK320_reg;
    assign U2_CLK40  = CLK40_reg;
    assign U1_CLK8   = CLK8_reg;
    assign BUS_CLK= CLKIN;

    assign CLK_reg = $c("clk640(",CLKIN,")");
    always@(posedge CLK) begin
        CLK320_reg = ~ CLK320_reg;
        if (cnt_reg[0]==1'b0)
            CLK160_reg = ~ CLK160_reg;
        if (cnt_reg[2:0]==3'b000)
            CLK40_reg = ~ CLK40_reg;
        if (cnt_reg==0)
           CLK8_reg = ~ CLK8_reg;
        if (cnt_reg==0 | cnt_reg==120)
           CLK16_reg = ~ CLK16_reg;
    end
    
    reg[63:0] TIMESTAMP_reg;
    always @(posedge CLK) begin
        if (cnt_reg==239)
            cnt_reg = 8'b00000000;
        else
            cnt_reg = cnt_reg +1;
        TIMESTAMP_reg=$time;
    end
endmodule