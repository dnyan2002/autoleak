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
                        break
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

                        client_socket.sendall(b"ACK")
                     
                    except json.JSONDecodeError:
                        logging.error(f"❌ Invalid JSON format received from Device {device_id}!")
                        client_socket.sendall(b"Invalid JSON format")
                    
                    except Exception as e:
                        logging.error(f"❌ Unexpected error processing data from Device {device_id}: {e}", exc_info=True)

                except socket.timeout:
                    logging.warning(f"⚠️ Timeout reached for Device {device_id}, waiting for next data...")
                    continue  # Keep waiting for new data
                except socket.error as e:
                    logging.error(f"❌ Socket error for Device {device_id}: {e}", exc_info=True)
                    break  # Exit the loop on socket errors

        except Exception as e:
            logging.error(f"❌ Error handling client {device_id}: {e}", exc_info=True)
        
        finally:
            try:
                client_socket.close()
            except:
                pass  # Ignore errors when closing an already closed socket
            logging.info(f"🔌 Connection closed for Device {device_id}.")
            # Update connection status to 0 (disconnected) when client disconnects
            self.update_connection_status(device_id, 0)

    def process_di_changes(self, di_data, timestamp):
        prev_di_states = self.di_states.copy()
        
        for di, value in di_data.items():
            self.di_states[di] = value
            
        # Identify changes and handle transitions
        for di, value in di_data.items():
            # Check if this DI's state has changed
            old_value = prev_di_states.get(di, 0)
            if old_value != value:
                logging.info(f"🔄 {di} changed from {old_value} to {value} at timestamp {timestamp}")
                
                # Extract DI number
                current_di_num = int(di[2:])
                
                # DI1 turning OFF - save AI1 value
                if di == "DI1" and value == 0:
                    logging.info(f"🔍 DI1 turned OFF, saving AI1 value")
                    self.save_specific_ai_value("AI1", timestamp)
                
                if di == "DI2" and value == 0:
                    logging.info(f"🔍 DI2 turned OFF, saving AI2 value")
                    self.save_specific_ai_value("AI2", timestamp)
                
                # For specific DI transitions - save specific AI values
                if di == "DI3" and value == 0:
                    logging.info(f"🔍 DI3 turned OFF, saving AI3 value")
                    self.save_specific_ai_value("AI3", timestamp)
                
                if di == "DI4" and value == 0:
                    logging.info(f"🔍 DI4 turned OFF, saving AI4 value")
                    self.save_specific_ai_value("AI4", timestamp)
                    
                if di == "DI5" and value == 0:
                    logging.info(f"🔍 DI5 turned OFF, saving AI5 value")
                    self.save_specific_ai_value("AI5", timestamp)
                
                if di == "DI6" and value == 0:
                    logging.info(f"🔍 DI6 turned OFF, saving AI6 value")
                    self.save_specific_ai_value("AI6", timestamp)
                
                if di == "DI7" and value == 0:
                    logging.info(f"🔍 DI7 turned OFF, saving AI7 value")
                    self.save_specific_ai_value("AI7", timestamp)
                
                if di == "DI8" and value == 0:
                    logging.info(f"🔍 DI8 turned OFF, saving AI8 value")
                    self.save_specific_ai_value("AI8", timestamp)

                if di == "DI9" and value == 0:
                    logging.info(f"🔍 DI9 turned OFF, saving AI9 value")
                    self.save_specific_ai_value("AI9", timestamp)

                if di == "DI10" and value == 0:
                    logging.info(f"🔍 DI10 turned OFF, saving AI10 value")
                    self.save_specific_ai_value("AI10", timestamp)
                
                if di == "DI11" and value == 0:
                    logging.info(f"🔍 DI11 turned OFF, saving AI11 value")
                    self.save_specific_ai_value("AI11", timestamp)

                if di == "DI12" and value == 0:
                    logging.info(f"🔍 DI12 turned OFF, saving AI12 value")
                    self.save_specific_ai_value("AI12", timestamp)
                
                if di == "DI13" and value == 0:
                    logging.info(f"🔍 DI13 turned OFF, saving AI13 value")
                    self.save_specific_ai_value("AI13", timestamp)

                if di == "DI14" and value == 0:
                    logging.info(f"🔍 DI14 turned OFF, saving AI14 value")
                    self.save_specific_ai_value("AI14", timestamp)
                
                if di == "DI15" and value == 0:
                    logging.info(f"🔍 DI15 turned OFF, saving AI15 value")
                    self.save_specific_ai_value("AI15", timestamp)

                # DI16 turning OFF - save AI16 value
                if di == "DI16" and value == 0:
                    logging.info(f"🔍 DI16 turned OFF, saving AI16 value")
                    self.save_specific_ai_value("AI16", timestamp)

                # Only handle regular test tracking for other DI's with original logic
                # DI turned ON - potential start of filter tracking
                if value == 1:
                    # Check if previous DI is OFF (valid transition)
                    prev_di = f"DI{current_di_num-1}" if current_di_num > 1 else None
                    prev_di_state = self.di_states.get(prev_di, 0) if prev_di else 0
                    
                    # If this is a valid start or transition:
                    # 1. DI1 turning ON starts a new test
                    # 2. Any other DI turning ON when previous DI is OFF is a transition
                    if current_di_num == 1 or prev_di_state == 0:
                        # If test is already in progress, save previous filter values before switching
                        if self.test_in_progress and self.current_filter:
                            prev_filter_num = int(self.current_filter[2:])
                            # Only save if we're transitioning from previous filter to this one
                            if prev_filter_num == current_di_num - 1:
                                # This call is kept for other transitions but specific AIs are handled separately
                                self.save_filter_max_values(self.current_filter, timestamp)
                                logging.info(f"🔄 Transitioning from {self.current_filter} to {di}")
                        
                        # Start tracking this filter
                        self.start_test(timestamp, di)
                
                # DI turned OFF - potential end of filter tracking
                elif value == 0:
                    # If this is the currently tracked filter and it's turning OFF
                    if self.test_in_progress and self.current_filter == di:
                        # Check if next DI is turning ON (part of valid transition)
                        next_di = f"DI{current_di_num+1}" if current_di_num < 16 else None
                        next_di_state = self.di_states.get(next_di, 0) if next_di else 0
                        if current_di_num == 16 or next_di_state == 0:
                            # This call is kept for non-specific AIs
                            self.save_filter_max_values(di, timestamp)
                            self.end_test(timestamp)
                            logging.info(f"🏁 Test ended with {di} turning OFF")

    def save_specific_ai_value(self, ai_key, timestamp):
        """Save the max value for a specific AI key when its corresponding DI changes."""
        logging.info(f"🔍 Starting save_specific_ai_value for {ai_key} at timestamp {timestamp}")
        
        if not self.test_in_progress or self.test_start_time is None:
            logging.warning(f"⚠️ Attempted to save {ai_key} value but no test is in progress")
            return

        # Add retry logic for database operations
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logging.info(f"🔍 Getting highest value for {ai_key} between {self.test_start_time} and {timestamp}")
                
                # Get the highest value for this specific AI channel from the database
                db_max = self.database_communication.get_highest_ai(self.test_start_time, timestamp, ai_key)
                memory_max = self.ai_max_values.get(ai_key, 0)
                
                # Use the higher of DB or memory max
                max_value = max(db_max, memory_max)
                logging.info(f"📊 Found max value for {ai_key}: {max_value} (DB: {db_max}, Memory: {memory_max})")
                
                # Determine the test status based on max value
                status = self.determine_test_status(timestamp)
                logging.info(f"📊 Test status for {ai_key}: {status}")
                
                # Save only this specific filter's max value to the database
                success = self.database_communication.save_single_filter_report(
                    date=timestamp,
                    filter_no=ai_key,
                    max_value=max_value,
                    status=status
                )
                
                if success:
                    logging.info(f"✅ Successfully saved max value for {ai_key}: {max_value}")
                    return  # Success, exit the retry loop
                else:
                    logging.error(f"❌ Failed to save max value for {ai_key}, attempt {attempt+1}/{max_attempts}")
                    # Continue to next attempt
                    
            except Exception as e:
                logging.error(f"❌ Error in save_specific_ai_value for {ai_key}: {e}", exc_info=True)
                
            # Wait before retry, increasing delay each time
            time.sleep(attempt + 1)
        
        logging.critical(f"‼️ All attempts to save filter max values for {ai_key} failed")


    def start_test(self, timestamp, filter_name):
        """Start tracking for a specific filter."""
        # If this is DI1, start a completely new test
        if filter_name == "DI1":
            self.test_start_time = timestamp
            self.test_in_progress = True
            # Reset max AI values for a new test
            self.ai_max_values = {f"AI{i}": 0 for i in range(1, 17)}
            logging.info(f"🟢 Started new test with {filter_name} at timestamp {timestamp}")
        else:
            # Continue existing test but switch to tracking a different filter
            self.test_in_progress = True
            logging.info(f"🔄 Now tracking {filter_name} at timestamp {timestamp}")
        
        # Update current filter being tested
        self.current_filter = filter_name

    def save_filter_max_values(self, filter_name, timestamp):
        """Save the max AI values for the current filter and transition to the next."""
        logging.info(f"🔍 Starting save_filter_max_values for {filter_name} at timestamp {timestamp}")
        
        if not self.test_in_progress:
            logging.warning(f"⚠️ Attempted to save filter values for {filter_name} but no test is in progress")
            return

        # Add retry logic for database operations
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Extract filter number from DI name (e.g., "DI5" -> 5)
                filter_num = int(filter_name[2:])
                
                # Map to corresponding AI (e.g., DI5 -> AI5)
                ai_key = f"AI{filter_num}"
                
                logging.info(f"🔍 Getting highest value for {ai_key} between {self.test_start_time} and {timestamp}")
                
                # Get the highest value for this specific AI channel from the database
                db_max = self.database_communication.get_highest_ai(self.test_start_time, timestamp, ai_key)
                memory_max = self.ai_max_values.get(ai_key, 0)
                
                # Use the higher of DB or memory max
                max_value = max(db_max, memory_max)
                logging.info(f"📊 Found max value for {filter_name} -> {ai_key}: {max_value} (DB: {db_max}, Memory: {memory_max})")
                
                # Determine the test status based on max value
                status = self.determine_test_status(timestamp)
                logging.info(f"📊 Test status for {filter_name}: {status}")
                
                # Save only this specific filter's max value to the database
                success = self.database_communication.save_single_filter_report(
                    date=timestamp,
                    filter_no=ai_key,
                    max_value=max_value,
                    status=status
                )
                
                if success:
                    logging.info(f"✅ Successfully saved max value for {filter_name} -> {ai_key}: {max_value}")
                    return  # Success, exit the retry loop
                else:
                    logging.error(f"❌ Failed to save max value for {filter_name} -> {ai_key}, attempt {attempt+1}/{max_attempts}")
                    # Continue to next attempt
                    
            except Exception as e:
                logging.error(f"❌ Error in save_filter_max_values for {filter_name}: {e}", exc_info=True)
                
            # Wait before retry, increasing delay each time
            time.sleep(attempt + 1)
        
        logging.critical(f"‼️ All attempts to save filter max values for {filter_name} failed")

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