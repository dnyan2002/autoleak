import socket
import threading
import logging
import json
import binascii

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class IoTServer:
    def __init__(self, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("0.0.0.0", port))
        self.server_socket.listen(5)
        logging.info(f"✅ Server started, listening on port {port}...")

    def handle_client(self, client_socket, address):
        """Handles an incoming connection from an IoT device."""
        logging.info(f"🔌 Connected to {address}")

        try:
            received_data = b""
            while True:
                data = client_socket.recv(1024)  # Receive raw data
                if not data:
                    logging.warning("⚠️ No data received, closing connection.")
                    break

                received_data += data  # Accumulate data
                logging.info(f"📩 Received raw data (hex) from {address}: {received_data.hex()}")

            if not received_data:
                return

            try:
                # Decode received data
                decoded_data = received_data.decode().strip()
                logging.debug(f"📩 Decoded string data: {decoded_data}")

                # Check if the data is hex-encoded JSON
                if all(c in "0123456789abcdefABCDEF" for c in decoded_data):
                    try:
                        decoded_data = binascii.unhexlify(decoded_data).decode()
                        logging.info(f"🔄 Converted hex data to JSON: {decoded_data}")
                    except Exception as e:
                        logging.error(f"❌ Failed to convert hex to JSON: {e}")
                        return

                # Parse JSON
                json_data = json.loads(decoded_data)
                logging.info(f"✅ Parsed JSON data: {json_data}")

                # Print JSON data on the console
                for key, value in json_data.items():
                    print(f"{key}: {value}")

                # Send acknowledgment
                client_socket.sendall(b"ACK")

            except json.JSONDecodeError:
                logging.error("❌ Invalid JSON format received!")
                client_socket.sendall(b"Invalid JSON format")

        except Exception as e:
            logging.error(f"❌ Error receiving data: {e}")
        finally:
            client_socket.close()
            logging.info("🔌 Connection closed.")

    def run(self):
        """Starts the server and listens for incoming connections."""
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address)).start()
        except KeyboardInterrupt:
            logging.info("🛑 Server shutting down...")
        finally:
            self.server_socket.close()

# Start server
if __name__ == "__main__":
    server = IoTServer(port=9090)
    server.run()
