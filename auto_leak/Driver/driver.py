import threading
import logging
import time
from database_communication import DatabaseCommunication
from socket_server import LeakDetectionServer
from database import DatabaseCommunication as DatabaseMonitor  # Import the DatabaseCommunication class from database.py

# Configure logging
logging.basicConfig(
    filename="service.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)

class MainSocketService:
    def __init__(self):
        logging.info("🔄 Initializing MainSocketService...")
        
        # Initialize database communication for the socket server
        self.db_com = DatabaseCommunication()
        
        # Initialize database monitor from database.py
        self.db_monitor = DatabaseMonitor()
        
        # Ports for the socket server
        self.port1 = 9090
        self.port2 = 5050

        # Initialize LeakDetectionServer with the two ports
        self.server = LeakDetectionServer(port_1=self.port1, port_2=self.port2)

        # Flag to control the main loop
        self.running = True
        
        logging.info("✅ MainSocketService initialized.")

    def shutdown_services(self):
        """Stops servers and exits gracefully."""
        logging.info("🛑 Shutting down services...")
        self.running = False
        
        # Stop the LeakDetectionServer
        self.server.stop()
        
        # Close the database monitor connection
        self.db_monitor.close_connection()
        
        logging.info("✅ Services stopped. Exiting...")

    def run_database_monitor(self):
        """Runs the database monitoring loop from database.py."""
        logging.info("🚀 Starting database monitor loop...")
        
        while self.running:
            try:
                # Fetch the current prodstatus
                current_prodstatus = self.db_monitor.fetch_prodstatus()

                if current_prodstatus is not None:
                    # If this is the first iteration, set the previous_prodstatus
                    if self.db_monitor.previous_prodstatus is None:
                        self.db_monitor.previous_prodstatus = current_prodstatus
                        logging.info(f"First iteration: Set previous_prodstatus to {current_prodstatus}")

                    # Check for transitions in prodstatus
                    if self.db_monitor.previous_prodstatus == 1 and current_prodstatus == 0:
                        logging.info("✅ Transition from prodstatus 0 to 1 detected. Sending data...")

                        # Fetch filter values and insert into foihighest_tbl
                        filter_values = self.db_monitor.fetch_max_filter_values()
                        if filter_values:
                            for filter_no, filter_value in filter_values.items():
                                highest_value = filter_value  # Customize this logic if needed
                                self.db_monitor.insert_foihighest(filter_no, filter_value, highest_value, batch_counter=1)

                            # Attempt to send the POST request
                            if self.db_monitor.send_post_request(filter_values):
                                # If the POST request is successful, delete data from foi_tbl
                                self.db_monitor.delete_from_foi_tbl()
                            else:
                                logging.warning("❌ POST request failed. Not deleting data from foi_tbl.")
                        else:
                            logging.warning("❌ No valid filter values found.")

                    # Update the previous_prodstatus if it has changed
                    if current_prodstatus != self.db_monitor.previous_prodstatus:
                        self.db_monitor.previous_prodstatus = current_prodstatus
                        logging.info(f"Updated previous_prodstatus to {self.db_monitor.previous_prodstatus}")

                else:
                    logging.warning("❌ Could not fetch prodstatus. Skipping this cycle.")

                # Sleep for a short duration before the next iteration
                time.sleep(0.3)

            except Exception as e:
                logging.error(f"❌ An error occurred during the database monitor loop: {e}")
                time.sleep(0.3)

    def run(self):
        """Starts the socket servers and runs the database monitor loop."""
        logging.info("🚀 Starting socket servers and database monitor...")
        
        try:
            # Start the LeakDetectionServer in a separate thread
            server_thread = threading.Thread(target=self.server.run, daemon=True)
            server_thread.start()

            # Start the database monitor loop in a separate thread
            db_monitor_thread = threading.Thread(target=self.run_database_monitor, daemon=True)
            db_monitor_thread.start()

        except Exception as e:
            logging.error(f"❌ Error starting server or database monitor: {str(e)}", exc_info=True)
            return

        logging.info("✅ Servers and database monitor started. Entering main loop...")
        
        try:
            while self.running:
                time.sleep(5)  # Keep the main thread alive
        except KeyboardInterrupt:
            self.shutdown_services()

if __name__ == "__main__":
    service = MainSocketService()
    service.run()