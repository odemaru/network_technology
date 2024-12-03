import socket
import threading
import os
import time
from colorama import init, Fore, Style

init(autoreset=True)

UPLOADS_DIR = 'uploads'
BUFFER_SIZE = 4096
CHECK_INTERVAL = 3

def handle_client(client_socket, client_address):
    try:
        file_name_size = int.from_bytes(client_socket.recv(4), 'big')
        file_name = client_socket.recv(file_name_size).decode('utf-8')
        file_name = os.path.basename(file_name)
        file_size = int.from_bytes(client_socket.recv(8), 'big')
        os.makedirs(UPLOADS_DIR, exist_ok=True)

        file_path = os.path.join(UPLOADS_DIR, file_name)
        received_bytes = 0
        start_time = time.time()
        last_report_time = start_time
        last_received_bytes = 0

        with open(file_path, 'wb') as file:
            while received_bytes < file_size:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                file.write(data)
                received_bytes += len(data)

                current_time = time.time()
                elapsed_time = current_time - last_report_time

                if elapsed_time >= CHECK_INTERVAL:
                    bytes_since_last_report = received_bytes - last_received_bytes
                    instant_speed = bytes_since_last_report / elapsed_time
                    gb_speed = (bytes_since_last_report / (1024 ** 3)) / elapsed_time
                    gb_file = (received_bytes / (1024 ** 3))
                    print(
                        f"{Fore.CYAN}[{client_address}] Received {received_bytes} bytes ({gb_file:.2f} GB) "
                        f"({Fore.RED}{instant_speed:.2f} B/s{Fore.CYAN}, {Fore.RED}{gb_speed:.2f} GB/s)")
                    last_received_bytes = received_bytes
                    last_report_time = current_time

        if received_bytes == file_size:
            client_socket.send(b"SUCCESS")
            print(f"{Fore.GREEN}[{client_address}] File received successfully.")
        else:
            client_socket.send(b"FAILURE")
            print(f"{Fore.RED}[{client_address}] File transfer failed.")

    except Exception as e:
        print(f"{Fore.RED}Error with client {client_address}: {e}")
    finally:
        client_socket.close()

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', port))
    server_socket.listen(5)
    print(f"{Fore.YELLOW}Server started, listening on port {port}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"{Fore.GREEN}Accepted connection from {client_address}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_handler.start()

if __name__ == "__main__":
    port = 1337
    start_server(port)
