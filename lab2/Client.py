import socket
import os
from colorama import init, Fore, Style

init(autoreset=True)

BUFFER_SIZE = 4096

def send_file(file_path, server_ip, server_port):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        print(f"{Fore.YELLOW}Connecting to {server_ip}:{server_port}...")
        client_socket.connect((server_ip, server_port))
        print(f"{Fore.GREEN}Connected to server.")

        file_name_encoded = file_name.encode('utf-8')
        client_socket.send(len(file_name_encoded).to_bytes(4, 'big'))
        client_socket.send(file_name_encoded)

        client_socket.send(file_size.to_bytes(8, 'big'))

        print(f"{Fore.YELLOW}Sending file: {file_name} ({file_size} bytes)")
        with open(file_path, 'rb') as file:
            while True:
                data = file.read(BUFFER_SIZE)
                if not data:
                    break
                client_socket.sendall(data)

        result = client_socket.recv(7)
        if result == b"SUCCESS":
            print(f"{Fore.GREEN}File sent successfully.")
        else:
            print(f"{Fore.RED}File transfer failed.")

if __name__ == "__main__":
    file_path = "D:/perenos.7z"
    server_ip = "127.0.0.1"
    server_port = 1337
    send_file(file_path, server_ip, server_port)
