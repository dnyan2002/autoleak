import socket

def update_production_status1(status, server_name="192.168.1.12", port=5050):
    print(f"Sending message to {server_name}:{port} with status {status}")
    try:
        with socket.create_connection((server_name, port), timeout=5) as client:
            client.sendall(bytes([status]))
            print("Message sent successfully.")
    except Exception as e:
        print(f"Error in socket_client1: {e}")
