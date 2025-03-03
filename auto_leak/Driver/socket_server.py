import logging
import socket
import threading
import json
import time
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
    def __init__(self, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("0.0.0.0", port))
        self.server_socket.listen(5)
        self.database_communication = DatabaseCommunication()
        logging.info(f"✅ Server started, listening on port {port}...")

    def handle_client(self, client_socket, address):
        """Handles an incoming connection from an IoT device and saves data."""
        logging.info(f"🔌 Connected to {address}")
        received_data = b""

        try:
            client_socket.settimeout(10)  # Prevent hanging connections

            while True:
                data = client_socket.recv(1024)  # Receive raw data
                if not data:
                    logging.warning("⚠️ No data received, closing connection.")
                    break

                received_data += data  # Accumulate data
                logging.info(f"📩 Received raw data from {address}: {received_data}")

            if not received_data:
                return

            # Decode and parse JSON data
            try:
                decoded_data = received_data.decode().strip()
                json_data = json.loads(decoded_data)
                logging.info(f"✅ Parsed JSON data: {json_data}")

                # Define transformation parameters
                m, c = 67.8, -406.7

                for filter_no, raw_value in json_data.items():
                    calculated_value = (m * raw_value) + c
                    logging.info(f"🔢 Processed {filter_no}: Raw={raw_value}, Adjusted={calculated_value}")

                    # Define status logic (adjust as needed)
                    status = "ok" if calculated_value > 0 else "nok"

                    # Insert into database
                    self.database_communication.insert_data(part_number=8, filter_no=filter_no,
                                                            filter_values=calculated_value, status=status)

                client_socket.sendall(b"ACK")

            except json.JSONDecodeError:
                logging.error("❌ Invalid JSON format received!")
                client_socket.sendall(b"Invalid JSON format")
            except Exception as e:
                logging.error(f"❌ Unexpected error processing data: {e}", exc_info=True)

        except Exception as e:
            logging.error(f"❌ Error handling client: {e}", exc_info=True)
        finally:
            client_socket.close()
            logging.info("🔌 Connection closed.")

    def run(self):
        """Starts the server and listens for incoming connections."""
        try:
            while True:
                logging.info("🔄 Waiting for client...")
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address)).start()
        except KeyboardInterrupt:
            logging.info("🛑 Server shutting down...")
        finally:
            self.server_socket.close()

    def stop(self):
        """Stops the server."""
        self.server_socket.close()
        logging.info("✅ Server stopped.")

if __name__ == "__main__":
    server = GreetingServer(port=9090)
    server.run()
