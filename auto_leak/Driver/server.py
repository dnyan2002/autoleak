import socket
import json
import time
import random
import threading

# Simulate IoT device sending AI and DI data (Device 1: AI1-AI8, DI1-DI8)
def create_test_data_device1():
    """Simulate IoT device data for Device 1."""
    ai_data = {f"AI{i}": round(random.uniform(10.0, 80.0), 2) for i in range(1, 9)}
    di_data = {f"DI{i}": 0 for i in range(1, 9)}

    # Cycle through DI values
    active_di_index = (int(time.time()) // 15) % 8 + 1
    di_data[f"DI{active_di_index}"] = 1

    return ai_data, di_data

# Simulate IoT device sending AI and DI data (Device 2: AI9-AI16, DI9-DI16)
def create_test_data_device2():
    """Simulate IoT device data for Device 2."""
    ai_data = {f"AI{i}": round(random.uniform(10.0, 80.0), 2) for i in range(9, 17)}
    di_data = {f"DI{i}": 0 for i in range(9, 17)}

    # Cycle through DI values
    active_di_index = (int(time.time()) // 15) % 8 + 9
    di_data[f"DI{active_di_index}"] = 1

    return ai_data, di_data


# Send data from a given device to the server
def send_data(device_id, host="127.0.0.1", port=9090):
    """Simulate an IoT device sending AI and DI data to the server."""
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            print(f"✅ Connected to the server at {host}:{port} (Device {device_id})")
            client_socket.settimeout(5)

            while True:
                # Get AI & DI data
                if device_id == 1:
                    ai_data, di_data = create_test_data_device1()
                elif device_id == 2:
                    ai_data, di_data = create_test_data_device2()
                else:
                    print(f"❌ Invalid device_id: {device_id}")
                    break

                # Convert to JSON string and send separately
                ai_json = json.dumps(ai_data) + "\n"
                di_json = json.dumps(di_data) + "\n"

                # Send AI data
                print(f"📤 Sending AI data from Device {device_id}: {ai_json.strip()}")
                client_socket.sendall(ai_json.encode())

                # Send DI data
                print(f"📤 Sending DI data from Device {device_id}: {di_json.strip()}")
                client_socket.sendall(di_json.encode())

                # Wait for acknowledgment
                try:
                    response = client_socket.recv(1024)
                    print(f"📥 Server response: {response.decode().strip()}")
                except socket.timeout:
                    print("⚠️ No response from server, continuing...")

                # Wait before sending next batch
                time.sleep(1)

        except Exception as e:
            print(f"❌ Error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
        finally:
            client_socket.close()
            print(f"🔌 Connection closed for Device {device_id}. Retrying...")


# Start sending data from both devices in parallel
if __name__ == "__main__":
    time.sleep(2)  # Ensure server is up before starting
    threading.Thread(target=send_data, args=(1,), daemon=True).start()
    threading.Thread(target=send_data, args=(2,), daemon=True).start()

    while True:
        time.sleep(1)  # Keep main thread alive
