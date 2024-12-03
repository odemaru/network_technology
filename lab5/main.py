import socket
import selectors
import struct
import logging
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

selector = selectors.DefaultSelector()

def send_response(conn, rep):
    response = b"\x05" + bytes([rep]) + b"\x00\x01\x00\x00\x00\x00\x00\x00"
    conn.sendall(response)

def handle_client(sock):
    try:
        data = sock.recv(4096)
        if not data:
            close_connection(sock)
            return

        state = sock_state[sock]

        if state == "handshake":
            if data[0] != 0x05:
                logging.error(Fore.RED + "Only SOCKS5 is supported.")
                close_connection(sock)
                return
            sock.sendall(b"\x05\x00")  # No authentication required
            sock_state[sock] = "connect"

        elif state == "connect":
            if len(data) < 10 or data[1] != 0x01:
                send_response(sock, 0x07)  # Command not supported
                close_connection(sock)
                return

            addr_type = data[3]
            if addr_type == 0x01:  # IPv4
                target_addr = socket.inet_ntoa(data[4:8])
                target_port = struct.unpack("!H", data[8:10])[0]
            elif addr_type == 0x03:  # Domain name
                domain_len = data[4]
                target_addr = data[5:5 + domain_len].decode()
                target_port = struct.unpack("!H", data[5 + domain_len:5 + domain_len + 2])[0]
            else:
                send_response(sock, 0x08)  # Address type not supported
                close_connection(sock)
                return

            logging.info(Fore.BLUE + f"Connecting to {target_addr}:{target_port}")

            try:
                target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_sock.setblocking(False)
                target_sock.connect_ex((target_addr, target_port))

                connections[sock] = target_sock
                connections[target_sock] = sock
                sock_state[target_sock] = "connected"
                sock_state[sock] = "connected"

                selector.register(target_sock, selectors.EVENT_READ, handle_client)
                send_response(sock, 0x00)  # Connection established

            except Exception as e:
                logging.error(Fore.RED + f"Connection error: {e}")
                send_response(sock, 0x01)  # General failure
                close_connection(sock)

        elif state == "connected":
            target_sock = connections.get(sock)
            if target_sock:
                target_sock.sendall(data)

    except Exception as e:
        logging.error(Fore.RED + f"Error: {e}")
        close_connection(sock)

def close_connection(sock):
    target_sock = connections.pop(sock, None)
    if target_sock:
        connections.pop(target_sock, None)
        selector.unregister(target_sock)
        target_sock.close()
    selector.unregister(sock)
    sock.close()

def main():
    host = ""
    port = 1337

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setblocking(False)
    server.bind((host, port))
    server.listen(100)

    selector.register(server, selectors.EVENT_READ, accept_client)
    logging.info(Fore.MAGENTA + f"SOCKS5 proxy listening on port {port}")

    while True:
        events = selector.select()
        for key, _ in events:
            callback = key.data
            callback(key.fileobj)

def accept_client(sock):
    conn, addr = sock.accept()
    conn.setblocking(False)
    selector.register(conn, selectors.EVENT_READ, handle_client)
    sock_state[conn] = "handshake"
    logging.info(Fore.CYAN + f"New connection from {addr}")

if __name__ == "__main__":
    connections = {}
    sock_state = {}
    main()
