import logging
import socket
import threading
import json
from database_communication import DatabaseCommunication

# Configure logging
LOG_FILE = "server.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
        logging.StreamHandler()
    ]
)

logging.info("🚀 Server is starting... Logs will be recorded in server.log")

class GreetingServer:
    def __init__(self, port_1, port_2):
        self.server_socket_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket_1.bind(("0.0.0.0", port_1))
        self.server_socket_1.listen(5)

        self.server_socket_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket_2.bind(("0.0.0.0", port_2))
        self.server_socket_2.listen(5)

        self.database_communication = DatabaseCommunication()
        logging.info(f"✅ Server started, listening on ports {port_1} and {port_2}...")

    def handle_device_data(self, device_id, client_socket, address):
        """Continuously handles incoming data from an IoT device."""
        logging.info(f"🔌 Connected to {address} (Device {device_id})")

        try:
            client_socket.settimeout(15)  # Set timeout to handle disconnections
            received_data = []  # Buffer for incoming data

            while True:
                try:
                    data = client_socket.recv(1024)  # Read incoming data
                    if not data:
                        logging.warning(f"⚠️ No data received from Device {device_id}, closing connection.")
                        break  # Exit loop if connection is lost

                    received_data.append(data)  # Store received data chunks
                    
                    # Process received data
                    combined_data = b''.join(received_data).decode().strip()
                    received_data = []  # Reset buffer after processing

                    logging.info(f"✅ Received raw data from Device {device_id}: {combined_data}")
                    
                    try:
                        json_data = json.loads(combined_data)
                        logging.info(f"✅ Parsed JSON data from Device {device_id}: {json_data}")

                        # Insert data using threading to avoid blocking
                        if json_data:
                            threading.Thread(target=self.insert_data_batch, args=(json_data,)).start()

                        client_socket.sendall(b"ACK")  # Acknowledge receipt
                    
                    except json.JSONDecodeError:
                        logging.error(f"❌ Invalid JSON format received from Device {device_id}!")
                        client_socket.sendall(b"Invalid JSON format")
                    
                    except Exception as e:
                        logging.error(f"❌ Unexpected error processing data from Device {device_id}: {e}", exc_info=True)

                except socket.timeout:
                    logging.warning(f"⚠️ Timeout reached for Device {device_id}, waiting for next data...")
                    continue  # Keep waiting for new data
            
        except Exception as e:
            logging.error(f"❌ Error handling client {device_id}: {e}", exc_info=True)
        
        finally:
            client_socket.close()
            logging.info(f"🔌 Connection closed for Device {device_id}.")

    def insert_data_batch(self, json_data):
        """Inserts batch data into the database."""
        try:
            self.database_communication.insert_data_batch(json_data)  # No need for `m, c` calculation
        except Exception as e:
            logging.error(f"❌ Database error while inserting batch data: {e}", exc_info=True)

    def run(self):
        """Starts the server and listens for incoming connections."""
        try:
            while True:
                logging.info("🔄 Waiting for client on port 9090...")
                client_socket_1, address_1 = self.server_socket_1.accept()
                threading.Thread(target=self.handle_device_data, args=(1, client_socket_1, address_1)).start()

                logging.info("🔄 Waiting for client on port 5050...")
                client_socket_2, address_2 = self.server_socket_2.accept()
                threading.Thread(target=self.handle_device_data, args=(2, client_socket_2, address_2)).start()

        except KeyboardInterrupt:
            logging.info("🛑 Server shutting down...")
        finally:
            self.server_socket_1.close()
            self.server_socket_2.close()

    def stop(self):
        """Stops the server."""
        self.server_socket_1.close()
        self.server_socket_2.close()
        logging.info("✅ Server stopped.")

if __name__ == "__main__":
    server = GreetingServer(port_1=9090, port_2=5050)
    server.run()
