from socket import *
from Packet import *
import random as rand
import os
import sys


ServerName = '127.0.0.1'
ServerPort = 12000
ServerAddress = (ServerName,ServerPort)

ClientSocket = socket(AF_INET, SOCK_DGRAM)
seq_num = rand.randint(1,10000)

send_packet = Packet()
recv_packet = Packet()

if __name__ == '__main__':
	#3-way-handshake
	ServerAddress, ack_num = client_three_way_handshake(seq_num, ServerAddress, ClientSocket)
	seq_num += 2

	#send request
	#request = input("Your request: ")
	request = sys.argv[1]
	print("Your request is: ",request)
	mysend(ClientSocket ,seq_num, ack_num, request.encode(), ServerAddress, 0)
	seq_num += len(request)
	print("send request to server...")

	#receive result
	raw_packet = ClientSocket.recv(ReceiverBufferSize)
	recv_packet.separate(raw_packet)
	sendACK(ClientSocket, recv_packet, seq_num, ServerAddress)
	seq_num += 1

	print("Receive result from",ServerAddress,"(seq_num:",recv_packet.seq_num(),"ack_num:",recv_packet.ack_num(),")")
	result = recv_packet.data.decode()

	if result == request:
		filename = request
		
		#prepare to receive video file
		expected_seq_num = 0
		unack = 1									#use for delay ack
		oldest_in_order_packet = Packet()			#when recv out of order packet, ack this
		preserve_newest_packet = Packet()			#when gap perfectly filled, ack this
		preserve_data = b''							#when recv out of order packet, preserve it if is in order
		preserve_data_start_byte = -1
		preserve_data_expect_byte = 0
		timer = 0									#used for delay ack timer
		dupcount = 0
		
		with open('copy'+filename, 'wb') as f:
			while True:
				if timer == 1:		#if delay ack is on
					ClientSocket.settimeout(0.5)
				else:
					ClientSocket.settimeout(None)
					
				try:
					raw_packet = ClientSocket.recv(ReceiverBufferSize)		#recv data
				except Exception:	#time out means ack now
					unack = 0
					sendACK(ClientSocket, recv_packet, seq_num, ServerAddress)
					print("send ACK (delay timeout)")
					timer = 0
					continue
					
				recv_packet.separate(raw_packet)
				print("Receive a packet (seq_num = %d ack_num = %d)"%(recv_packet.seq_num(), recv_packet.ack_num()))
				
				if recv_packet.seq_num() == expected_seq_num:				#in order packet
					if recv_packet.seq_num() < preserve_data_start_byte:								#gap fill in -> ack now
						sendACK(ClientSocket, recv_packet, seq_num, ServerAddress)
						seq_num += 1
						expected_seq_num += len(recv_packet.data)
						f.write(recv_packet.data)
						
						if expected_seq_num == preserve_data_start_byte:							#if gap fully filled
							f.write(preserve_data)													#write preserve data into file
							expected_seq_num = preserve_data_expect_byte
							preserve_data_start_byte = -1											#reset
							sendACK(ClientSocket, preserve_newest_packet, seq_num, ServerAddress)	#tell server gap fill
							recv_packet.data = preserve_newest_packet.data
							recv_packet.header = preserve_newest_packet.header
							seq_num += 1
							
					else:	#no gap
						if unack == 1:		#exist unack packet	-> sendack
							sendACK(ClientSocket, recv_packet, seq_num, ServerAddress)
							seq_num += 1

							unack = 0
							timer = 0		#no need timer, just wait
							
						else:				#unack == 0 -> means can delay ack -> start 500ms timer
							timer = 1
							unack = 1
						
						
						if recv_packet.data == b'file_download_exit':	#done
							print("Done!")
							break
							
						expected_seq_num += len(recv_packet.data)
						f.write(recv_packet.data)

					oldest_in_order_packet.data = recv_packet.data
					oldest_in_order_packet.header = recv_packet.header
					dupcount = 0
					
				elif recv_packet.seq_num() > expected_seq_num:			#out of order packet
					if dupcount <= 5:
						sendACK(ClientSocket, oldest_in_order_packet, seq_num, ServerAddress)			#send dup ack
					dupcount += 1
					print("send dup ACK")
					seq_num += 1
					
					if preserve_data_start_byte == -1:												#not yet have out of order packet
						preserve_data = recv_packet.data
						preserve_data_start_byte = recv_packet.seq_num()
						preserve_data_expect_byte = preserve_data_start_byte + len(recv_packet.data)
						preserve_newest_packet.data = recv_packet.data
						preserve_newest_packet.header = recv_packet.header
						
					elif preserve_data_expect_byte == recv_packet.seq_num():							#although out of order but preserve is in order
						preserve_data = preserve_data + recv_packet.data
						preserve_data_expect_byte += len(recv_packet.data)
						preserve_newest_packet.data = recv_packet.data
						preserve_newest_packet.header = recv_packet.header
						
					timer = 0
						
	else:
		print(result)

	ClientSocket.close()

