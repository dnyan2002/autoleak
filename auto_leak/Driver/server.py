import socket
import json
import time
import random
import threading

# Simulate the IoT device sending data
def create_test_data(device_id):
    """Simulate IoT device data with random values for each filter."""
    data = {
        f"AI{i}": round(random.uniform(10.0, 100.0), 2)  # Random float between 10.0 and 100.0
        for i in range(1 + (device_id - 1) * 8, 9 + (device_id - 1) * 8)  # Creates 8 filters per device
    }
    return data

def send_data(device_id, host='127.0.0.1', port=9090):
    """Simulate an IoT device sending data to the GreetingServer."""
    while True:
        try:
            # Create a socket object
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            print(f"✅ Connected to the server at {host}:{port} (Device {device_id})")

            # Set socket timeout to avoid indefinite blocking
            client_socket.settimeout(5)

            # Keep sending data continuously (150 sets in 15 seconds)
            for _ in range(150):  # 150 data points
                # Simulate the IoT device sending random data
                data = create_test_data(device_id)
                json_data = json.dumps(data)  # Convert the data to JSON format
                print(f"📤 Sending data from Device {device_id}: {json_data}")
                
                # Send the data
                client_socket.sendall(json_data.encode())

                # Wait for server's acknowledgment (optional)
                try:
                    response = client_socket.recv(1024)
                    print(f"📥 Server response: {response.decode()}")
                except socket.timeout:
                    # No response from server, continue sending data
                    print("⚠️ No response from server, continuing...")

                # Wait 0.1 second to send 10 sets per second (150 sets in 15 seconds)
                time.sleep(0.1)

        except Exception as e:
            print(f"❌ Error occurred: {e}")
            print("🔄 Reconnecting to the server...")
            time.sleep(5)  # Wait before reconnecting if an error occurs
            continue  # Retry connecting to the server

        finally:
            client_socket.close()
            print(f"🔌 Connection closed for Device {device_id}. Retrying...")

# Start sending data from both devices
if __name__ == "__main__":
    time.sleep(2)  # Ensure the server is up before the client starts
    # Device 1
    threading.Thread(target=send_data, args=(1,)).start()
    # Device 2
    threading.Thread(target=send_data, args=(2,)).start()
