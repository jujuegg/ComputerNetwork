from socket import *
from Packet import *
from time import process_time
from time import sleep
import os

ServerPort = 12000
NextPort = ServerPort + 1

SEPARATOR = ','

if __name__ == '__main__':

	ServerSocket = socket(AF_INET, SOCK_DGRAM)
	ServerSocket.bind(('',ServerPort))
	Server_recv_packet = Packet()
	print("Ready for client to connect...")

	while True:
		raw_packet, ClientAddress = ServerSocket.recvfrom(ReceiverBufferSize)
		Server_recv_packet.separate(raw_packet)

		if Server_recv_packet.SYN() == 1:	#new client
			client_seq_num = Server_recv_packet.seq_num()
			print("Receive a packet(SYN) from",ClientAddress[0],":",ClientAddress[1], "(seq_num:",client_seq_num,")")
			pid = os.fork()

			if pid == 0:
				#3-way handshake
				ConnectionSocket = socket(AF_INET, SOCK_DGRAM)	#create new socket for data transmission
				ConnectionSocket.bind(('', NextPort))
				recv_packet = Packet()
				send_packet = Packet()
				seq_num = server_three_way_handshake(ClientAddress, ConnectionSocket, client_seq_num)
				
				#wait for client request
				print("wait for client request...")
				raw_packet, dump = ConnectionSocket.recvfrom(ReceiverBufferSize)
				recv_packet.separate(raw_packet)
				req = recv_packet.data.decode()
				print("Client's request:",req)

				if(os.path.exists(req)):	#is an exist file
					#send file info
					filename = req
					send_packet = Packet()
					send_packet.data = filename.encode()
					send_packet.set_seq_num(seq_num)
					send_packet.set_ack_num(recv_packet.seq_num()+len(req))
					raw_packet = send_packet.wrap()
					ConnectionSocket.sendto(raw_packet, ClientAddress)
					RTTstart = process_time()
					seq_num += len(filename)

					raw_packet = ConnectionSocket.recv(ReceiverBufferSize)
					RTTend = process_time()
					recv_packet.separate(raw_packet)
					if (recv_packet.ACK() == 1 and recv_packet.ack_num() == seq_num):
						print("Received ACK ready to transmit file...")
						
					print("time: ", RTTend - RTTstart)
					
					#read file
					f = open(filename,'rb')
					File = f.read()
					file_len = len(File)
					f.close()
					
					#send file
					cwnd = MSS
					NextStartByte = 0
					EndByte = 0
					base = 0
					last_ack_num = 0
					dup_ack_count = 0
					timeoutval = 0.001	#second
					state = 0	# 0 = slow start, 1 = congestion avoid, 2 = fast recovery
					ssthresh = Threshold
					flag = 0
					timer = 0
					congest_avoid_ack_count = 0
					last_cwnd = 0
					last_threshold = 0
				
					print("*****slow start*****")
					
					seq_num = NextStartByte
					ack_num = recv_packet.seq_num() + 1
					
					while (EndByte < file_len and base < file_len) :
						while NextStartByte >= base + cwnd :						#cwnd is full -> stuck here and wait for new ack
							if timer == 1:
								elapse_time = process_time() - timer_start
							else:
								elapse_time = 0
								
							if elapse_time >= timeoutval:			#already time out
								#timeout
								ssthresh = cwnd/2
								cwnd = MSS
								dup_ack_count = 0
								NextStartByte = base								#reset NextStartByte to base
								seq_num = NextStartByte
								state = 0											#back to slow start
								flag = 1
								print("timeout!")
								print("*****slow start*****")
								continue
							else:													#not yet time out
								remain_time = timeoutval - elapse_time				#count remain time
								ConnectionSocket.settimeout(remain_time)
								
							try:
								raw_packet = ConnectionSocket.recv(ReceiverBufferSize)
							except Exception:	
								#timeout										
								ssthresh = cwnd/2
								cwnd = MSS
								dup_ack_count = 0
								NextStartByte = base								#reset NextStartByte to base
								seq_num = NextStartByte
								state = 0											#back to slow start
								flag = 1
								print("timeout!")
								print("*****slow start*****")
								continue
							
							recv_packet.separate(raw_packet)
							if recv_packet.ACK() == 1 :
								print("Receive a packet(ACK) (seq_num = %d ack_num = %d)"%(recv_packet.seq_num(),recv_packet.ack_num()))
								
								if recv_packet.ack_num() == last_ack_num:			#dup-ack
									ack_num = recv_packet.seq_num() + 1
									dup_ack_count += 1
									
									if state == 2:									#fast recovery
										cwnd = cwnd + MSS
										
									if dup_ack_count >= 3 :							#3 dup ack -> fast retransmit
										if state == 1 or state == 0:			
											ssthresh = cwnd / 2
											cwnd = ssthresh + 3 * MSS
											state = 2									#enter fast recovery
											print("*****Fast recovery*****")			
										
										#retransmit packet
										print("*****Fast retransmit*****")
										ReStartByte = last_ack_num
										seq_num = ReStartByte
										ReEndByte = ReStartByte + MSS
										bytes_read = File[ReStartByte:ReEndByte]
										mysend(ConnectionSocket, seq_num, ack_num, bytes_read, ClientAddress, 0)
										print("        Send a packet at :",ReStartByte,"byte.(fast retransmit)")
										dup_ack_count = 0								
										
								else:												#new ack
									base = recv_packet.ack_num()
									if NextStartByte < base:
										NextStartByte = base
									seq_num = NextStartByte
									last_ack_num = recv_packet.ack_num()
									ack_num = recv_packet.seq_num() + 1
									#print("seq_num: ", seq_num)
									#print("base: ", base)
									#print("NSB", NextStartByte)
									
									#slow start
									if state == 0:
										cwnd += MSS										#increase cwnd
										if cwnd >= ssthresh:								#over threshhold
											state = 1
											congest_avoid_ack_count = 0
											print("*****congestion avoidance*****")		#enter congestion avoidance
									
									#congestion avoidance
									elif state == 1:
										congest_avoid_ack_count += 1
										if congest_avoid_ack_count == cwnd / MSS:		#space enough for 1 MSS
											congest_avoid_ack_count = 0
											cwnd += MSS
									
									#fast retransmit
									elif state == 2:
										state = 1
										congest_avoid_ack_count = 0
										print("*****congestion avoidance*****")
										cwnd = ssthresh
										
									#all state need to do
									dup_ack_count = 0
									if base == NextStartByte:						#no in flight packet
										timer = 0
									else:
										timer = 1
										timer_start = process_time()				#timer for next oldest in flight packet

						if cwnd != last_cwnd or ssthresh != last_threshold:
							print("cwnd =",int(cwnd), "ssthresh = ", int(ssthresh))
							last_cwnd = cwnd
							last_threshold = ssthresh
							
						#cwnd has space , use all
						while (base + cwnd) - NextStartByte >= MSS:
							#send one MSS packet
							EndByte = NextStartByte + MSS									#create a 1MSS packet
							bytes_read = File[NextStartByte:EndByte]
							
							if state == 2: 
								mysend(ConnectionSocket, NextStartByte, ack_num, bytes_read, ClientAddress, 0)
							else: 	
								if seq_num == 8192:				#can set which byte want to loss once
									if flag == 1:
										mysend(ConnectionSocket, seq_num, ack_num, bytes_read, ClientAddress, 0)
								else :
									mysend(ConnectionSocket, seq_num, ack_num, bytes_read, ClientAddress, 0)
								print("        Send a packet at :",NextStartByte,"byte.")
									
								if NextStartByte == base:										#the packet is the first packet in cwnd
									timer_start = process_time()								#start timer
								
							NextStartByte = EndByte
							seq_num = (seq_num + len(bytes_read)) % MAX_SEQ_NUM
						
					#tell client is done
					print('Finish transmit')
					message = 'file_download_exit'.encode()
					mysend(ConnectionSocket, seq_num, ack_num, message, ClientAddress, 0)
					
				else:	#not a file
					try: 
						result = str(eval(req))
					except Exception:
						result = "Error request, file not exist or wrong input."
					
					send_packet = Packet()
					send_packet.data = result.encode()
					send_packet.set_seq_num(seq_num)
					send_packet.set_ack_num(recv_packet.seq_num()+len(req))
					raw_packet = send_packet.wrap()
					ConnectionSocket.sendto(raw_packet, ClientAddress)
					print("Send result back to the client...")
					seq_num += len(result)
					
				os._exit(0)
			else:
				NextPort += 1

