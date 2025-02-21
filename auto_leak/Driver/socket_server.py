import socket
import threading
import json
from database_communication import DatabaseCommunication  # Assuming a separate DB handling module

class GreetingServer:
    def __init__(self, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("0.0.0.0", port))
        self.server_socket.listen(5)
        self.database_communication = DatabaseCommunication()
        self.status = True
        print(f"Server started, listening on port {port}...")

    def send_message(self, msg, server_name="192.168.1.12", port=5050):
        """Send a message to another server (similar to sendMessage() in Java)."""
        try:
            print(f"Trying to send message: {msg} to {server_name}:{port}")
            with socket.create_connection((server_name, port)) as client:
                client.sendall(msg.encode())
                response = client.recv(1024).decode()
                print(f"Response received from {server_name}:{port} -> {response}")
                return response
        except Exception as e:
            print(f"Error sending message: {e}")
            return None

    def handle_client(self, client_socket, address):
        """Handles an individual client connection."""
        print(f"Connected to {address}")
        try:
            data = client_socket.recv(1024).decode().strip()
            print(f"Received raw data from client: {data}")

            if not data:
                print("No data received.")
                client_socket.close()
                return

            # Try to parse JSON (if applicable)
            try:
                json_data = json.loads(data)
                print(f"Parsed JSON data: {json_data}")
            except json.JSONDecodeError:
                print("Invalid JSON format received.")
                client_socket.sendall(b"Invalid JSON format")
                return

            part_number = self.database_communication.get_part_number_from_selected_part()
            print(f"Retrieved part number: {part_number}")

            if len(json_data) == 8:
                for key, value in json_data.items():
                    print(f"Processing: {key} = {value}")
                    self.database_communication.insert_into_database(part_number, key, value)
                    self.database_communication.update_database(part_number, key, value)
            else:
                print(f"Expected 8 key-value pairs, but received {len(json_data)}.")

            # Send acknowledgment
            response_message = f"Server received: {json_data}"
            client_socket.sendall(response_message.encode())
            print(f"Sent acknowledgment: {response_message}")

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def run(self):
        """Starts the server and listens for incoming connections."""
        try:
            while self.status:
                print("Waiting for client...")
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address)).start()
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self.server_socket.close()

    def stop(self):
        """Stops the server."""
        self.status = False
        self.server_socket.close()
        print("Server stopped.")

if __name__ == "__main__":
    server = GreetingServer(port=9090)
    server.start()


class GreetingServer1:
    def __init__(self, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("0.0.0.0", port))
        self.server_socket.listen(5)  # Allow up to 5 connections in the queue
        self.status = True
        self.database_communication = DatabaseCommunication()
        print(f"Server started on port {port}, waiting for clients...")

    @staticmethod
    def send_message(self, msg, server_name="192.168.1.12", port=9090):
        """Send a message to another server (similar to sendMessage() in Java)."""
        try:
            print(f"Trying to send message: {msg} to {server_name}:{port}")
            with socket.create_connection((server_name, port)) as client:
                client.sendall(msg.encode())
                response = client.recv(1024).decode()
                print(f"Response received from {server_name}:{port} -> {response}")
                return response
        except Exception as e:
            print(f"Error sending message: {e}")
            return None


    def handle_client(self, client_socket, address):
        """Handles an individual client connection."""
        print(f"Connected to {address}")
        try:
            data = client_socket.recv(1024).decode().strip()
            print(f"Received raw data from client: {data}")

            if not data:
                print("No data received.")
                client_socket.close()
                return

            # Try to parse JSON (if applicable)
            try:
                json_data = json.loads(data)
                print(f"Parsed JSON data: {json_data}")
            except json.JSONDecodeError:
                print("Invalid JSON format received.")
                client_socket.sendall(b"Invalid JSON format")
                return

            part_number = self.database_communication.get_part_number_from_selected_part()
            print(f"Retrieved part number: {part_number}")

            if len(json_data) == 8:
                for key, value in json_data.items():
                    print(f"Processing: {key} = {value}")
                    self.database_communication.insert_into_database(part_number, key, value)
                    self.database_communication.update_database(part_number, key, value)
            else:
                print(f"Expected 8 key-value pairs, but received {len(json_data)}.")

            # Send acknowledgment
            response_message = f"Server received: {json_data}"
            client_socket.sendall(response_message.encode())
            print(f"Sent acknowledgment: {response_message}")

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()

    def run(self):
        """Main loop for handling client connections."""
        while self.status:
            try:
                client_socket, addr = self.server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.start()
            except Exception as e:
                print(f"Server error: {e}")
                break

    def stop_server(self):
        """Stops the server gracefully."""
        self.status = False
        self.server_socket.close()
        print("Server stopped.")

# Start the server
if __name__ == "__main__":
    server = GreetingServer1(5050)
    server.run()
