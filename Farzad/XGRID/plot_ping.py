import re
import matplotlib.pyplot as plt

# Sample ping data (you can replace this with reading from a file)
ping_data = """
64 bytes from 12.0.24.178: icmp_seq=1 ttl=61 time=6.81 ms
64 bytes from 12.0.24.178: icmp_seq=2 ttl=61 time=4.02 ms
64 bytes from 12.0.24.178: icmp_seq=3 ttl=61 time=4.43 ms
64 bytes from 12.0.24.178: icmp_seq=4 ttl=61 time=3.89 ms
64 bytes from 12.0.24.178: icmp_seq=5 ttl=61 time=3.34 ms
64 bytes from 12.0.24.178: icmp_seq=6 ttl=61 time=4.53 ms
64 bytes from 12.0.24.178: icmp_seq=7 ttl=61 time=3.96 ms
64 bytes from 12.0.24.178: icmp_seq=8 ttl=61 time=4.02 ms
64 bytes from 12.0.24.178: icmp_seq=9 ttl=61 time=3.71 ms
64 bytes from 12.0.24.178: icmp_seq=10 ttl=61 time=3.69 ms
64 bytes from 12.0.24.178: icmp_seq=11 ttl=61 time=3.46 ms
"""

# Function to parse the ping data and extract icmp_seq and time values
def parse_ping_data(data):
    icmp_seq = []
    time_ms = []
    
    # Regular expression to match icmp_seq and time values
    pattern = r"icmp_seq=(\d+) ttl=\d+ time=([\d\.]+) ms"
    
    # Find all matches
    matches = re.findall(pattern, data)
    
    # Extract the values
    for match in matches:
        icmp_seq.append(int(match[0]))
        time_ms.append(float(match[1]))
    
    return icmp_seq, time_ms

# Parse the sample data
icmp_seq, time_ms = parse_ping_data(ping_data)

# Plotting the data
plt.figure(figsize=(10, 6))
plt.plot(icmp_seq, time_ms, marker='o', linestyle='-', color='b', label='Ping time')
plt.title('XGRID Ping Times for ICMP Sequences')
plt.xlabel('ICMP Sequence')
plt.ylabel('Time (ms)')
plt.grid(True)
plt.legend()
plt.show()