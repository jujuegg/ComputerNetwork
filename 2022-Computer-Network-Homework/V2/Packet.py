import random as rand
import numpy as np

RTT = 20	#ms
MSS = 1024	#byte
Threshold = 64*1024	#byte
ReceiverBufferSize = 512*1024	#byte
HEADER_LEN = 50
MAX_SEQ_NUM = 2**32 - 1

LOSS_ON = 0
loss_rate = 10**(-6)
Probability = [1-loss_rate, loss_rate]	#weight

class Packet:
	def __init__(self):
#						    -----		   ---------- -
		self.header = "00000000000000000000000000000000000000000000000000"
#					   -----	 ----------			 -
		self.data = b''

	def separate(self, packet):
		self.header = packet[:50].decode()
		self.data = packet[50:]
	def wrap(self):
		return self.header.encode() + self.data

	def set_source_port_num(self, num):
		new = str(num).zfill(5)
		self.header = self.header[:0] + new + self.header[5:]
	def source_port_num(self):
		return int(self.header[0:5])

	def set_dest_port_num(self, num):
		new = str(num).zfill(5)
		self.header = self.header[:5] + new + self.header[10:]
	def dest_port_num(self):
		return int(self.header[5:10])

	def set_seq_num(self, num):
		new = str(num).zfill(10)
		self.header = self.header[:10] + new + self.header[20:]
	def seq_num(self):
		return int(self.header[10:20])

	def set_ack_num(self, num):
		new = str(num).zfill(10)
		self.header = self.header[:20] + new + self.header[30:]
	def ack_num(self):
		return int(self.header[20:30])

	def set_ACK(self, num):
		new = str(num).zfill(1)
		self.header = self.header[:30] + new + self.header[31:]
	def ACK(self):
		return int(self.header[30:31])

	def set_SYN(self, num):
		new = str(num).zfill(1)
		self.header = self.header[:31] + new + self.header[32:]
	def SYN(self):
		return int(self.header[31:32])

def client_three_way_handshake(isn, server, ClientSocket):
	print("=====Start the three-way-handshake=====")
	send_packet = Packet()
	recv_packet = Packet()
	send_packet.set_seq_num(isn)
	send_packet.set_SYN(1)
	raw_packet = send_packet.wrap()
	ClientSocket.sendto(raw_packet, server)
	isn += 1
	print("send a packet(SYN) to",server[0],":",server[1])
	
	raw_packet, newDest = ClientSocket.recvfrom(ReceiverBufferSize)
	recv_packet.separate(raw_packet)
	print("Receive a packet(SYN/ACK) from",newDest[0],":",newDest[1], "(seq_num:",recv_packet.seq_num(),",ack_num:",recv_packet.ack_num(),")")

	send_packet = Packet()
	send_packet.set_seq_num(isn)
	send_packet.set_ack_num(recv_packet.seq_num() + 1)
	send_packet.set_ACK(1)
	raw_packet = send_packet.wrap()
	ClientSocket.sendto(raw_packet, newDest)
	print("send a packet(ACK) to",newDest[0],":",newDest[1])
	print("=====Complete the three-way-handshake=====")

	return newDest,recv_packet.seq_num() + 1

def server_three_way_handshake(client, ConnectionSocket, client_seq_num):
	Dest = client
	seq_num = rand.randint(1,10000)
	print("start seq_num",seq_num)

	send_packet = Packet()
	send_packet.set_ACK(1)
	send_packet.set_seq_num(seq_num)
	send_packet.set_ack_num(client_seq_num+1)
	raw_packet = send_packet.wrap()
	ConnectionSocket.sendto(raw_packet, Dest)
	print("send a packet(SYN/ACK) to",Dest[0],":",Dest[1])

	Connection_recv_packet = Packet()
	raw_packet, dump = ConnectionSocket.recvfrom(ReceiverBufferSize)
	Connection_recv_packet.separate(raw_packet)
	if Connection_recv_packet.ACK() == 1:
		print("Receive a packet(ACK) from",Dest[0],":",Dest[1], "(seq_num:",Connection_recv_packet.seq_num(),",ack_num:",Connection_recv_packet.ack_num(),")")
	seq_num += 1

	return seq_num

def sendACK(Socket, previous_packet, seq_num, dest):
	packet = Packet()
	packet.set_ACK(1)
	data_len = len(previous_packet.data)
	if data_len == 0:
		data_len = 1
	packet.set_ack_num(previous_packet.seq_num()+data_len)
	packet.set_seq_num(seq_num)
	raw_packet = packet.wrap()
	Socket.sendto(raw_packet, dest)
	
def mysend(Socket ,seq_num, ack_num, data, dest, loss_on):		#data should be encoded, loss_on = 1 -> loss occur
	send_packet = Packet()
	send_packet.data = data
	send_packet.set_seq_num(seq_num)
	send_packet.set_ack_num(ack_num)
	raw_packet = send_packet.wrap()
	
	x = np.random.choice([1,0], p = Probability)		#1 means no loss
	if loss_on == 1 and x == 0:
		return
		
	Socket.sendto(raw_packet, dest)

