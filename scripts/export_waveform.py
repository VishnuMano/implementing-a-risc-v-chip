"""Read the first UART frame from the real RTL VCD, preserving timestamps."""
import json
import pathlib
root=pathlib.Path(__file__).resolve().parent.parent
scope=[]
tx_id=None
started=False
start=0
now=0
previous=None
points=[]
with (root/"build/soc.vcd").open() as stream:
    for line in stream:
        parts=line.split()
        if not started:
            if parts and parts[0]=="$scope":scope.append(parts[2])
            elif parts and parts[0]=="$upscope":scope.pop()
            elif parts and parts[0]=="$var" and scope==["tb_soc"] and parts[4]=="tx":tx_id=parts[3]
            elif "$enddefinitions" in line:started=True
            continue
        if line.startswith("#"):
            now=int(line[1:])
            if points and now-start>87_000_000:
                points.append([87.0,previous])
                break
        elif tx_id and line.strip()[1:]==tx_id and line[0] in "01":
            bit=int(line[0])
            if not points and previous==1 and bit==0:
                start=now
                points=[[0.0,0]]
            elif points:points.append([(now-start)/1_000_000,bit])
            previous=bit
if not points:raise SystemExit("No UART frame found")
bits=[]
for index in range(10):
    midpoint=(index+0.5)*8.7
    bits.append([value for at,value in points if at<=midpoint][-1])
byte=sum(bits[index+1]<<index for index in range(8))
if bits[0]!=0 or bits[9]!=1:raise SystemExit("Invalid captured UART frame")
result={"unit":"microseconds","bit_period_us":8.7,"byte_hex":f"{byte:02X}","character":chr(byte),"points":points,"bits":bits,
        "source":"build/soc.vcd","vcd_timescale":"1 ps","start_time_ps":start}
(root/"results/waveform.json").write_text(json.dumps(result,indent=2)+"\n")
