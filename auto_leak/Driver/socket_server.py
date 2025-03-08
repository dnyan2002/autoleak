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
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.info("🚀 Leak Detection Server is starting... Logs will be recorded in server.log")

class LeakDetectionServer:
    def __init__(self, port_1, port_2):
        """Initialize the server with two ports for device connections."""
        self.port_1 = port_1
        self.port_2 = port_2
        
        # Create socket for first device
        self.server_socket_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket_1.bind(("0.0.0.0", port_1))
        self.server_socket_1.listen(5)
        
        # Create socket for second device
        self.server_socket_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket_2.bind(("0.0.0.0", port_2))
        self.server_socket_2.listen(5)
        
        # Initialize database connection
        self.database_communication = DatabaseCommunication()
        
        # State tracking variables
        self.di_states = {f"DI{i}": 0 for i in range(1, 17)}  # Track all DI states
        self.ai_max_values = {f"AI{i}": 0 for i in range(1, 17)}  # Track max AI values
        self.test_start_time = None  # Timestamp when DI1 goes to 1
        self.test_in_progress = False  # Flag to indicate active test
        self.current_filter = None  # Current active filter being tested
        
        logging.info(f"✅ Leak Detection Server started, listening on ports {port_1} and {port_2}...")

    def handle_device_data(self, device_id, client_socket, address):
        """Continuously handles incoming data from an IoT device."""
        logging.info(f"🔌 Connected to {address} (Device {device_id})")

        try:
            client_socket.settimeout(15)  # Set timeout to handle disconnections
            received_data = []  # Buffer for incoming data

            # Update connection status to 1 (connected) when client connects
            self.update_connection_status(device_id, 1)

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

                    logging.debug(f"✅ Received raw data from Device {device_id}: {combined_data}")
                    
                    try:
                        json_data = json.loads(combined_data)
                        logging.info(f"✅ Parsed JSON data from Device {device_id}: {json_data}")

                        # Extract DI and AI data
                        di_data = {k: v for k, v in json_data.items() if k.startswith("DI")}
                        ai_data = {k: v for k, v in json_data.items() if k.startswith("AI")}
                        timestamp = json_data.get("date", int(time.time()))

                        # Process DI state changes and AI values
                        if di_data:
                            self.process_di_changes(di_data, timestamp)

                        # Store AI values in database
                        if ai_data:
                            self.process_ai_values(ai_data, timestamp)
                            
                            # Update max AI values if test is in progress
                            if self.test_in_progress:
                                self.update_max_ai_values(ai_data)

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
            # Update connection status to 0 (disconnected) when client disconnects
            self.update_connection_status(device_id, 0)

    def process_di_changes(self, di_data, timestamp):
        """
        Process digital input changes and detect transitions between DIs.
        
        Key logic:
        - When DI1 goes from 0 to 1 and DI2 is 0: Start tracking AI values for DI1
        - When DI2 goes from 0 to 1 and DI1 is 0: End tracking for DI1, start for DI2
        - Same pattern for DI3 through DI8
        """
        for di, value in di_data.items():
            # Detect state changes
            old_value = self.di_states.get(di, 0)
            state_changed = (old_value != value)
            
            # Update state tracking first to ensure all states are current
            self.di_states[di] = value
            
            if state_changed:
                logging.info(f"🔄 {di} changed from {old_value} to {value} at timestamp {timestamp}")
                
                # Handle DI transitions
                if di == "DI1" and value == 1 and self.di_states.get("DI2", 0) == 0:
                    self.start_test(timestamp, "DI1")
                    
                elif di == "DI2" and value == 1 and self.di_states.get("DI1", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI1":
                        # Save max values for DI1 and start tracking for DI2
                        self.save_filter_max_values("DI1", timestamp)
                    self.start_test(timestamp, "DI2")
                    
                elif di == "DI3" and value == 1 and self.di_states.get("DI2", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI2":
                        # Save max values for DI2 and start tracking for DI3
                        self.save_filter_max_values("DI2", timestamp)
                    self.start_test(timestamp, "DI3")
                    
                elif di == "DI4" and value == 1 and self.di_states.get("DI3", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI3":
                        # Save max values for DI3 and start tracking for DI4
                        self.save_filter_max_values("DI3", timestamp)
                    self.start_test(timestamp, "DI4")
                    
                elif di == "DI5" and value == 1 and self.di_states.get("DI4", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI4":
                        # Save max values for DI4 and start tracking for DI5
                        self.save_filter_max_values("DI4", timestamp)
                    self.start_test(timestamp, "DI5")
                    
                elif di == "DI6" and value == 1 and self.di_states.get("DI5", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI5":
                        # Save max values for DI5 and start tracking for DI6
                        self.save_filter_max_values("DI5", timestamp)
                    self.start_test(timestamp, "DI6")
                    
                elif di == "DI7" and value == 1 and self.di_states.get("DI6", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI6":
                        # Save max values for DI6 and start tracking for DI7
                        self.save_filter_max_values("DI6", timestamp)
                    self.start_test(timestamp, "DI7")
                    
                elif di == "DI8" and value == 1 and self.di_states.get("DI7", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI7":
                        # Save max values for DI7 and start tracking for DI8
                        self.save_filter_max_values("DI7", timestamp)
                    self.start_test(timestamp, "DI8")
                    
                # End test when DI8 transitions to 0
                elif di == "DI8" and value == 0 and self.di_states.get("DI9", 0) == 0:
                    if self.current_filter == "DI9":
                        # Save max values for DI8 and end the test
                        self.save_filter_max_values("DI8", timestamp)
                    self.end_test(timestamp)
                
                # Handle DI transitions for device 2 (DI9-DI16)
                elif di == "DI9" and value == 1 and self.di_states.get("DI8", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI8":
                        # Save max values for DI8 and start tracking for DI9
                        self.save_filter_max_values("DI8", timestamp)
                    self.start_test(timestamp, "DI9")
                    
                elif di == "DI10" and value == 1 and self.di_states.get("DI9", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI9":
                        # Save max values for DI9 and start tracking for DI10
                        self.save_filter_max_values("DI9", timestamp)
                    self.start_test(timestamp, "DI10")
                    
                elif di == "DI11" and value == 1 and self.di_states.get("DI10", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI10":
                        # Save max values for DI10 and start tracking for DI11
                        self.save_filter_max_values("DI10", timestamp)
                    self.start_test(timestamp, "DI11")
                    
                elif di == "DI12" and value == 1 and self.di_states.get("DI11", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI11":
                        # Save max values for DI11 and start tracking for DI12
                        self.save_filter_max_values("DI11", timestamp)
                    self.start_test(timestamp, "DI12")
                    
                elif di == "DI13" and value == 1 and self.di_states.get("DI12", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI12":
                        # Save max values for DI12 and start tracking for DI13
                        self.save_filter_max_values("DI12", timestamp)
                    self.start_test(timestamp, "DI13")
                    
                elif di == "DI14" and value == 1 and self.di_states.get("DI13", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI13":
                        # Save max values for DI13 and start tracking for DI14
                        self.save_filter_max_values("DI13", timestamp)
                    self.start_test(timestamp, "DI14")
                    
                elif di == "DI15" and value == 1 and self.di_states.get("DI14", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI14":
                        # Save max values for DI14 and start tracking for DI15
                        self.save_filter_max_values("DI14", timestamp)
                    self.start_test(timestamp, "DI15")
                    
                elif di == "DI16" and value == 1 and self.di_states.get("DI15", 0) == 0:
                    if self.test_in_progress and self.current_filter == "DI15":
                        # Save max values for DI15 and start tracking for DI16
                        self.save_filter_max_values("DI15", timestamp)
                    self.start_test(timestamp, "DI16")
                    
                # End test when DI16 transitions to 0 (instead of DI8)
                elif di == "DI16" and value == 0 and self.test_in_progress:
                    if self.current_filter == "DI16":
                        # Save max values for DI16 and end the test
                        self.save_filter_max_values("DI16", timestamp)
                    self.end_test(timestamp)


    def start_test(self, timestamp, filter_name):
        """Start tracking for a specific filter."""
        self.test_start_time = timestamp
        self.test_in_progress = True
        self.current_filter = filter_name
        
        # Reset max AI values for the new filter period
        self.ai_max_values = {f"AI{i}": 0 for i in range(1, 17)}
        
        logging.info(f"🟢 Started tracking for {filter_name} at timestamp {timestamp}")

    def save_filter_max_values(self, filter_name, timestamp):
        """Save the max AI values for the current filter and transition to the next."""
        if not self.test_in_progress:
            return

        filter_num = int(filter_name[2:])
        ai_key = f"AI{filter_num}"
        
        # Get the highest value for this specific AI channel from the database
        db_max = self.database_communication.get_highest_ai(self.test_start_time, timestamp, ai_key)
        memory_max = self.ai_max_values.get(ai_key, 0)
        
        # Use the higher of DB or memory max
        max_value = max(db_max, memory_max)
        logging.info(f"📊 Saved max value for {filter_name} -> {ai_key}: {max_value}")
        
        # Determine the test status based on max value
        status = self.determine_test_status(timestamp)
        
        # Create a dictionary with just this AI value
        filter_max_values = {ai_key: max_value}
        
        # Save only this specific filter's max value to the database
        self.database_communication.save_single_filter_report(
            date=timestamp,
            filter_no=ai_key,
            max_value=max_value,
            status=status
        )

    def determine_test_status(self, timestamp):
        """Determine test status based on setpoints and AI values."""
        if not self.test_in_progress or self.test_start_time is None:
            return "Unknown"
            
        test_duration = timestamp - self.test_start_time
        
        # Get setpoints from database
        setpoints = self.database_communication.get_setpoints()
        timer1_seconds = setpoints["timer1"]
        setpoint1 = setpoints["setpoint1"]
        timer2_seconds = setpoints["timer2"]
        setpoint2 = setpoints["setpoint2"]
        
        # Check if any AI value exceeds setpoints
        status = "OK"  # Default status is OK
        
        for ai, max_value in self.ai_max_values.items():
            if test_duration <= timer1_seconds and max_value > setpoint1:
                status = "NOK"
                logging.info(f"❌ Test failed: {ai} value {max_value} exceeded setpoint1 {setpoint1} within {timer1_seconds}s")
                break
            elif test_duration <= timer2_seconds and max_value > setpoint2:
                status = "NOK"
                logging.info(f"❌ Test failed: {ai} value {max_value} exceeded setpoint2 {setpoint2} within {timer2_seconds}s")
                break
                
        return status

    def end_test(self, timestamp):
        """End the current leak test and evaluate results."""
        if not self.test_in_progress or self.test_start_time is None:
            logging.warning("⚠️ Attempted to end test but no test was in progress")
            return
            
        test_duration = timestamp - self.test_start_time
        logging.info(f"🏁 Test ended - Duration: {test_duration} seconds")
        
        # Determine final test status
        status = self.determine_test_status(timestamp)
        
        # No need to save another report here since we've already saved individual filter reports
        # during each transition. Just log the end of the test.
        logging.info(f"🏁 Final test status: {status}")

        # Reset test state
        self.test_in_progress = False
        self.test_start_time = None
        self.current_filter = None

    def update_max_ai_values(self, ai_data):
        """Update the maximum AI values observed during an active test."""
        for ai, value in ai_data.items():
            if ai in self.ai_max_values and value > self.ai_max_values[ai]:
                self.ai_max_values[ai] = value
                logging.debug(f"📈 New max value for {ai}: {value}")

    def process_ai_values(self, ai_data, timestamp):
        """Store AI values in the database."""
        try:
            # Insert data in a separate thread to avoid blocking
            threading.Thread(target=self.database_communication.insert_data_batch, args=(ai_data,)).start()
        except Exception as e:
            logging.error(f"❌ Error inserting AI data into database: {e}", exc_info=True)

    def update_connection_status(self, device_id, status):
        """Updates the connection status in the database."""
        try:
            self.database_communication.update_server_connection(device_id, status)
            logging.info(f"✅ Updated server_connection_{device_id} to {status} in the database.")
        except Exception as e:
            logging.error(f"❌ Error updating connection status for Device {device_id}: {e}", exc_info=True)

    def listen_for_clients(self, port, device_id):
        """Continuously listens for new client connections on a given port."""
        server_socket = self.server_socket_1 if device_id == 1 else self.server_socket_2
        logging.info(f"🔄 Listening for clients on port {port}...")

        while True:
            client_socket, address = server_socket.accept()
            logging.info(f"📡 New connection on port {port} from {address}")
            threading.Thread(target=self.handle_device_data, args=(device_id, client_socket, address), daemon=True).start()

    def run(self):
        """Starts the server by running two listener threads."""
        threading.Thread(target=self.listen_for_clients, args=(self.port_1, 1), daemon=True).start()
        threading.Thread(target=self.listen_for_clients, args=(self.port_2, 2), daemon=True).start()
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("🛑 Server shutting down...")
        finally:
            self.stop()

    def stop(self):
        """Stops the server and closes connections."""
        self.server_socket_1.close()
        self.server_socket_2.close()
        self.database_communication.close_connection()
        logging.info("✅ Server stopped.")

if __name__ == "__main__":
    server = LeakDetectionServer(port_1=9090, port_2=5050)
    server.run()