import re
import matplotlib.pyplot as plt

# Sample ping data (you can replace this with reading from a file)
ping_data = """
64 bytes from 12.0.15.18: icmp_seq=1 ttl=59 time=6.89 ms
64 bytes from 12.0.15.18: icmp_seq=2 ttl=59 time=3.78 ms
64 bytes from 12.0.15.18: icmp_seq=3 ttl=59 time=3.94 ms
64 bytes from 12.0.15.18: icmp_seq=4 ttl=59 time=3.89 ms
64 bytes from 12.0.15.18: icmp_seq=5 ttl=59 time=3.72 ms
64 bytes from 12.0.15.18: icmp_seq=6 ttl=59 time=3.70 ms
64 bytes from 12.0.15.18: icmp_seq=7 ttl=59 time=3.99 ms
64 bytes from 12.0.15.18: icmp_seq=8 ttl=59 time=4.11 ms
64 bytes from 12.0.15.18: icmp_seq=9 ttl=59 time=4.00 ms
64 bytes from 12.0.15.18: icmp_seq=10 ttl=59 time=3.74 ms
64 bytes from 12.0.15.18: icmp_seq=11 ttl=59 time=3.39 ms
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
plt.title('MOTIF Ping Times for ICMP Sequences')
plt.xlabel('ICMP Sequence')
plt.ylabel('Time (ms)')
plt.grid(True)
plt.legend()
plt.show()