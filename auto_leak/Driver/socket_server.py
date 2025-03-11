import logging
import socket
import threading
import json
import time
from database_communication import DatabaseCommunication
logging.info("🚀 Leak Detection Server is starting... Logs will be recorded in server.log")

class LeakDetectionServer:
    def __init__(self, port_1, port_2):
        """Initialize the server with two ports for device connections."""
        self.port_1 = port_1
        self.port_2 = port_2
        self.server_socket_1 = None
        self.server_socket_2 = None
        
        self.database_communication = DatabaseCommunication()
        self.di_states = {f"DI{i}": 0 for i in range(1, 17)}  # Track all DI states
        self.ai_max_values = {f"AI{i}": 0 for i in range(1, 17)}  # Track max AI values
        self.test_start_time = None  # Timestamp when DI1 goes to 1
        self.test_in_progress = False  # Flag to indicate active test
        self.current_filter = None
        self.initialize_sockets()
        
        logging.info(f"✅ Leak Detection Server started, listening on ports {port_1} and {port_2}...")

    def initialize_sockets(self):
        """Initialize socket bindings with retry logic."""
        max_retries = 10
        retry_interval = 5
        
        for attempt in range(max_retries):
            try:
                # Create socket for first device
                if self.server_socket_1:
                    self.server_socket_1.close()
                self.server_socket_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket_1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket_1.bind(("0.0.0.0", self.port_1))
                self.server_socket_1.listen(5)
                
                # Create socket for second device
                if self.server_socket_2:
                    self.server_socket_2.close()
                self.server_socket_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket_2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket_2.bind(("0.0.0.0", self.port_2))
                self.server_socket_2.listen(5)
                
                logging.info(f"✅ Successfully bound to ports {self.port_1} and {self.port_2}")
                return True
                
            except OSError as e:
                logging.error(f"❌ Socket binding failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logging.info(f"🔄 Waiting {retry_interval} seconds before retry...")
                    time.sleep(retry_interval)
                else:
                    logging.critical(f"‼️ Failed to bind sockets after {max_retries} attempts. Exiting.")
                    raise

    def handle_device_data(self, device_id, client_socket, address):
        """Continuously handles incoming data from an IoT device."""
        logging.info(f"🔌 Connected to {address} (Device {device_id})")

        # Update connection status to 1 (connected) when client connects
        retry_attempts = 3
        for attempt in range(retry_attempts):
            try:
                self.update_connection_status(device_id, 1)
                self.send_message_to_specific_iot(device_id=1, status_value=1)
                self.send_message_to_specific_iot(device_id=2, status_value=1)
                break
            except Exception as e:
                logging.error(f"❌ Failed to update connection status for Device {device_id} (attempt {attempt+1}/{retry_attempts}): {e}")
                if attempt == retry_attempts - 1:
                    logging.warning(f"⚠️ Could not update connection status after {retry_attempts} attempts, continuing anyway")

        try:
            client_socket.settimeout(15)
            received_data = []
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
                            self.retry_operation(lambda: self.process_di_changes(di_data, timestamp))

                        if ai_data:
                            self.retry_operation(lambda: self.process_ai_values(ai_data, timestamp))
                            if self.test_in_progress:
                                self.retry_operation(lambda: self.update_max_ai_values(ai_data))

                        self.send_message_to_specific_iot(device_id=1, status_value=1)
                        self.send_message_to_specific_iot(device_id=2, status_value=0)
                    except json.JSONDecodeError:
                        logging.error(f"❌ Invalid JSON format received from Device {device_id}! Skipping this data.")
                        continue  # Skip invalid JSON and continue processing
                    
                    except Exception as e:
                        logging.error(f"❌ Unexpected error processing data from Device {device_id}: {e}", exc_info=True)
                        time.sleep(1)  # Wait before retry
                    
                except socket.timeout:
                    logging.warning(f"⚠️ Timeout reached for Device {device_id}, waiting for next data...")
                    continue
                except socket.error as e:
                    logging.error(f"❌ Socket error for Device {device_id}: {e}", exc_info=True)
                    break

        except Exception as e:
            logging.error(f"❌ Error handling client {device_id}: {e}", exc_info=True)
        
        finally:
            try:
                client_socket.close()
            except:
                pass
            logging.info(f"🔌 Connection closed for Device {device_id}.")
            
            # Try several times to update the connection status
            for attempt in range(retry_attempts):
                try:
                    self.update_connection_status(device_id, 0)
                    break
                except Exception as e:
                    logging.error(f"❌ Failed to update disconnection status (attempt {attempt+1}/{retry_attempts}): {e}")

    def send_message_to_specific_iot(self, device_id, status_value):
        # Device connection information
        if device_id == 1:
            iot_ip = "192.168.1.13"  # First IOT device IP
            iot_port = 9090          # First IOT device port
        elif device_id == 2:
            iot_ip = "127.0.0.1"     # Second IOT device IP
            iot_port = 5050          # Second IOT device port
        else:
            logging.error(f"❌ Unknown device ID: {device_id}")
            return False
        
        # Important: Check if at least one device is connected BEFORE attempting a new connection
        other_device_id = 2 if device_id == 1 else 1
        other_server_connected = self._check_other_server_connected(other_device_id)
        
        # Check if we already have an active connection to this device
        socket_attr = f'_device_{device_id}_socket'
        client_socket = None
        
        if hasattr(self, socket_attr) and getattr(self, socket_attr) is not None:
            client_socket = getattr(self, socket_attr)
            # Test if the connection is still valid with minimal operations
            try:
                client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
                logging.info(f"✅ Using existing connection to IOT device {device_id}")
            except (socket.error, OSError):
                # Socket is no longer valid, close it and prepare to create a new one
                logging.info(f"🔄 Existing connection to IOT device {device_id} is invalid. Will attempt reconnect.")
                try:
                    client_socket.close()
                except:
                    pass
                client_socket = None
                setattr(self, socket_attr, None)
                
                # Update connection status in database
                try:
                    self.update_connection_status(device_id, 0)
                except Exception as e:
                    logging.error(f"❌ Failed to update connection status: {e}")
        
        # If we need to create a new connection
        if client_socket is None:
            try:
                logging.info(f"🔄 Connecting to IOT device {device_id} at {iot_ip}:{iot_port}")
                
                # Create new socket with shorter timeout
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(3)  # Shorter timeout for connection attempt
                
                # Connect to the IOT device
                client_socket.connect((iot_ip, iot_port))
                
                # Set up keep-alive parameters to maintain connection
                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # Set timeout for future recv operations to a longer value
                client_socket.settimeout(60)  # 60 second timeout for data operations
                
                # Store the socket for future use
                setattr(self, socket_attr, client_socket)
                
                # Update connection status in database
                try:
                    self.update_connection_status(device_id, 1)
                except Exception as e:
                    logging.error(f"❌ Failed to update connection status: {e}")
                    
                logging.info(f"✅ Successfully connected to IOT device {device_id} at {iot_ip}:{iot_port}")
                
            except (ConnectionRefusedError, socket.timeout) as e:
                logging.warning(f"⚠️ Could not connect to IOT device {device_id}: {e}")
                
                # Update connection status in database
                try:
                    self.update_connection_status(device_id, 0)
                except Exception as db_e:
                    logging.error(f"❌ Failed to update connection status: {db_e}")
                
                # If other server is connected, continue operation
                if other_server_connected:
                    logging.info(f"ℹ️ Device {device_id} connection failed, but Device {other_device_id} is connected. Continuing operation.")
                    return False
                else:
                    logging.warning(f"⚠️ Could not connect to IOT device {device_id} and no other devices are connected.")
                    return False
                    
            except Exception as e:
                logging.error(f"❌ Unexpected error connecting to IOT device {device_id}: {e}", exc_info=True)
                return False
        
        # Now send the message
        try:
            # Send the status value
            client_socket.sendall(bytes([status_value]))
            logging.info(f"✅ Sent status value {status_value} to IOT device {device_id}")
            
            # Wait for response in a non-blocking way
            # Start a new thread to handle waiting for and processing responses
            threading.Thread(
                target=self._receive_iot_response, 
                args=(device_id, client_socket),
                daemon=True
            ).start()
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Error sending message to IOT device {device_id}: {e}", exc_info=True)
            
            # Close and invalidate the socket
            try:
                client_socket.close()
            except:
                pass
            
            setattr(self, socket_attr, None)
            
            # Update connection status in database
            try:
                self.update_connection_status(device_id, 0)
            except Exception as db_e:
                logging.error(f"❌ Failed to update connection status: {db_e}")
            
            return False

    def _check_other_server_connected(self, device_id):

        socket_attr = f'_device_{device_id}_socket'
        if hasattr(self, socket_attr) and getattr(self, socket_attr) is not None:
            socket_obj = getattr(self, socket_attr)
            try:
                # Test socket validity with a non-blocking operation
                socket_obj.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
                logging.info(f"✅ Device {device_id} has an active connection")
                return True
            except (socket.error, OSError):
                # Socket is no longer valid, clean it up
                try:
                    socket_obj.close()
                except:
                    pass
                setattr(self, socket_attr, None)
        
        # Only check database status as a fallback and cache the result
        try:
            is_connected = self.database_communication.ensure_connection()
            if is_connected:
                logging.info(f"✅ Device {device_id} is connected according to database")
            return is_connected
        except Exception as e:
            logging.error(f"❌ Error checking connection status for device {device_id}: {e}")
            return False

    def _receive_iot_response(self, device_id, client_socket):
        received_data = []
        
        try:
            while True:
                try:
                    # Wait for response data
                    data = client_socket.recv(1024)
                    
                    if not data:
                        logging.warning(f"⚠️ Connection closed by IOT device {device_id}")
                        break
                        
                    received_data.append(data)
                    
                    # Process complete messages
                    combined_data = b''.join(received_data)
                    
                    # Attempt to process the data
                    logging.info(f"✅ Received data from IOT device {device_id}: {combined_data}")
                    
                    # Process the data based on your protocol
                    try:
                        # Try to parse as JSON if applicable
                        json_data = json.loads(combined_data.decode().strip())
                        # Insert into the database or process values as needed
                        threading.Thread(
                            target=self.process_iot_data, 
                            args=(device_id, json_data),
                            daemon=True
                        ).start()
                    except json.JSONDecodeError:
                        # Not JSON or incomplete data, keep collecting
                        logging.debug(f"Received non-JSON or incomplete data: {combined_data}")
                    except Exception as proc_e:
                        logging.error(f"❌ Error processing data from IOT device {device_id}: {proc_e}")
                    
                    # Reset data buffer after processing
                    received_data = []
                    
                except socket.timeout:
                    # Timeout on receive is fine, just continue waiting
                    continue
                    
        except Exception as e:
            logging.error(f"❌ Error receiving data from IOT device {device_id}: {e}", exc_info=True)
        
        finally:
            # Connection is lost or closed, clean up
            try:
                client_socket.close()
            except:
                pass
            
            # Clear the stored socket
            setattr(self, f'_device_{device_id}_socket', None)
            
            # Update connection status in database
            try:
                self.update_connection_status(device_id, 0)
            except Exception as e:
                logging.error(f"❌ Failed to update connection status: {e}")
            
            # Check if at least one server is still connected
            other_device_id = 2 if device_id == 1 else 1
            if self._check_other_server_connected(other_device_id):
                logging.info(f"ℹ️ Connection to Device {device_id} closed, but Device {other_device_id} is connected. Continuing operation.")
            else:
                logging.warning(f"⚠️ Connection to IOT device {device_id} closed and no other devices are connected.")

    def process_iot_data(self, device_id, data):
        try:
            logging.info(f"📊 Processing data from device {device_id}: {data}")
            
            # Extract DI and AI data if present
            di_data = {k: v for k, v in data.items() if k.startswith("DI")}
            ai_data = {k: v for k, v in data.items() if k.startswith("AI")}
            timestamp = data.get("date", int(time.time()))
            
            # Process DI state changes and AI values
            if di_data:
                self.retry_operation(lambda: self.process_di_changes(di_data, timestamp))
            
            if ai_data:
                self.retry_operation(lambda: self.process_ai_values(ai_data, timestamp))
                if self.test_in_progress:
                    self.retry_operation(lambda: self.update_max_ai_values(ai_data))
                    
        except Exception as e:
            logging.error(f"❌ Error processing IOT data: {e}", exc_info=True)

    def close_iot_connections(self):
        """Close all open IOT device connections."""
        for device_id in [1, 2]:
            socket_attr = f'_device_{device_id}_socket'
            if hasattr(self, socket_attr) and getattr(self, socket_attr) is not None:
                try:
                    socket_obj = getattr(self, socket_attr)
                    socket_obj.close()
                    setattr(self, socket_attr, None)
                    logging.info(f"🔌 Closed connection to IOT device {device_id}")
                except Exception as e:
                    logging.error(f"❌ Error closing connection to IOT device {device_id}: {e}")

    def retry_operation(self, operation, max_attempts=3, delay=1):
        """Generic retry function for operations."""
        for attempt in range(max_attempts):
            try:
                return operation()
            except Exception as e:
                logging.error(f"❌ Operation failed (attempt {attempt+1}/{max_attempts}): {e}", exc_info=True)
                if attempt < max_attempts - 1:
                    time.sleep(delay * (attempt + 1))  # Incremental delay
                else:
                    logging.error(f"‼️ Operation failed after {max_attempts} attempts")

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
                if value == 1:
                    # Check if previous DI is OFF (valid transition)
                    prev_di = f"DI{current_di_num-1}" if current_di_num > 1 else None
                    prev_di_state = self.di_states.get(prev_di, 0) if prev_di else 0

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
                elif value == 0:
                    if self.test_in_progress and self.current_filter == di:
                        next_di = f"DI{current_di_num+1}" if current_di_num < 16 else None
                        next_di_state = self.di_states.get(next_di, 0) if next_di else 0
                        if current_di_num == 16 or next_di_state == 0:
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
            try:
                client_socket, address = server_socket.accept()
                logging.info(f"📡 New connection on port {port} from {address}")
                threading.Thread(target=self.handle_device_data, args=(device_id, client_socket, address), daemon=True).start()
            except socket.error as e:
                logging.error(f"❌ Socket accept error on port {port}: {e}")
                time.sleep(1)  # Prevent high CPU usage on continuous errors
                
                # Check if the server socket is still valid
                try:
                    # Try a simple socket operation to check if it's still valid
                    server_socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
                except socket.error:
                    logging.error(f"❌ Server socket for device {device_id} is no longer valid. Recreating...")
                    try:
                        # Recreate the socket
                        if device_id == 1:
                            self.server_socket_1.close()
                            self.server_socket_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.server_socket_1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            self.server_socket_1.bind(("0.0.0.0", port))
                            self.server_socket_1.listen(5)
                            server_socket = self.server_socket_1
                        else:
                            self.server_socket_2.close()
                            self.server_socket_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.server_socket_2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            self.server_socket_2.bind(("0.0.0.0", port))
                            self.server_socket_2.listen(5)
                            server_socket = self.server_socket_2
                        logging.info(f"✅ Successfully recreated socket for device {device_id}")
                    except Exception as rebind_error:
                        logging.error(f"❌ Failed to recreate socket: {rebind_error}")
                        time.sleep(5)

    def run(self):
        """Starts the server by running two listener threads."""
        retry_count = 0
        max_retries = 10
        
        while retry_count < max_retries:
            try:
                # Create and start listener threads
                thread1 = threading.Thread(target=self.listen_for_clients, args=(self.port_1, 1), daemon=True)
                thread2 = threading.Thread(target=self.listen_for_clients, args=(self.port_2, 2), daemon=True)
                
                thread1.start()
                thread2.start()
                
                # Start database heartbeat in a separate thread
                heartbeat_thread = threading.Thread(target=self.database_heartbeat, daemon=True)
                heartbeat_thread.start()
                
                # Keep the main thread alive and monitor thread health
                while True:
                    if not thread1.is_alive():
                        logging.error("⚠️ Thread 1 has stopped unexpectedly. Restarting...")
                        thread1 = threading.Thread(target=self.listen_for_clients, args=(self.port_1, 1), daemon=True)
                        thread1.start()
                    
                    if not thread2.is_alive():
                        logging.error("⚠️ Thread 2 has stopped unexpectedly. Restarting...")
                        thread2 = threading.Thread(target=self.listen_for_clients, args=(self.port_2, 2), daemon=True)
                        thread2.start()
                    
                    if not heartbeat_thread.is_alive():
                        logging.error("⚠️ Database heartbeat thread has stopped. Restarting...")
                        heartbeat_thread = threading.Thread(target=self.database_heartbeat, daemon=True)
                        heartbeat_thread.start()
                    
                    time.sleep(5)
                    
            except Exception as e:
                retry_count += 1
                logging.error(f"❌ Error in main server loop (attempt {retry_count}/{max_retries}): {e}", exc_info=True)
                logging.info(f"🔄 Restarting server in {retry_count * 5} seconds...")
                time.sleep(retry_count * 5)  # Exponential backoff
                
            except KeyboardInterrupt:
                logging.info("🛑 Server shutting down...")
                break
        
        if retry_count >= max_retries:
            logging.critical(f"‼️ Server failed to run properly after {max_retries} attempts. Exiting.")
        
        self.stop()
    
    def database_heartbeat(self):
        """Periodically checks and maintains database connection."""
        while True:
            try:
                time.sleep(30)
                if time.time() - self.database_communication.last_used > 25:
                    self.database_communication.ping_connection()
            except Exception as e:
                logging.error(f"❌ Database heartbeat error: {e}")
                time.sleep(10)

    def stop(self):
        """Stops the server and closes connections."""
        self.server_socket_1.close()
        self.server_socket_2.close()
        self.database_communication.close_connection()
        logging.info("✅ Server stopped.")

if __name__ == "__main__":
    server = LeakDetectionServer(port_1=9090, port_2=5050)
    server.run()