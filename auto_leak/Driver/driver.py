import sys
import threading
import logging
import time
from database_communication import DatabaseCommunication
from socket_server import GreetingServer, GreetingServer1
from socket_client1 import update_production_status1
from socket_client2 import update_production_status2

# Configure logging
logging.basicConfig(
    filename="service.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)

class MainSocketService:
    counter = 0
    status = 0
    previous_status = 0
    running = True  # Graceful shutdown flag

    def __init__(self):
        logging.info("🔄 Initializing MainSocketService...")
        
        self.db_com = DatabaseCommunication()
        self.server_name1 = "192.168.1.12"
        self.server_name2 = "192.168.1.12"
        self.port1 = 5050
        self.port2 = 9090

        self.greeting_server = GreetingServer(self.port1)
        self.greeting_server1 = GreetingServer1(self.port2)

        self.thread1 = threading.Thread(target=self.greeting_server.run, daemon=True)
        self.thread2 = threading.Thread(target=self.greeting_server1.run, daemon=True)

        logging.info("✅ MainSocketService initialized.")

    def send_query(self):
        """Fetches and updates system status."""
        logging.info("🔍 Fetching status from the database...")

        try:
            self.status = self.db_com.insert_data(1, "AI1", 1, "OK")
            logging.info(f"📌 Status retrieved: {self.status}")

            logging.info(f"🌐 PLC IP1: {self.server_name1}, PLC IP2: {self.server_name2}")
            logging.info(f"🔌 Port1: {self.port1}, Port2: {self.port2}")

            logging.info(f"📌 Current Status: {self.status}, Previous Status: {self.previous_status}")

            if self.status == 99:
                logging.warning("🛑 Status 99 detected! Stopping services...")
                self.shutdown_services()
                return

            if self.status == 0:
                logging.warning(f"⚠️ Production stopped. Previous status: {self.previous_status}")

                if self.previous_status == 1:
                    logging.info("🔄 Resetting production status...")
                    update_production_status1(0)
                    update_production_status2(0)

                self.previous_status = 0
                time.sleep(0.35)
                return

            if self.status == 2:
                logging.info("🔄 Resetting production and counter...")
                self.previous_status = 0
                self.counter = 0
                update_production_status1(0)
                update_production_status2(0)
                self.db_com.update_production_status1(0)
                self.db_com.update_production_status2(0)

            elif self.status == 1 and self.previous_status == 0:
                logging.info("🚀 Production started!")
                self.previous_status = self.status
                update_production_status1(1)
                update_production_status2(1)

        except Exception as e:
            logging.error(f"❌ Error in send_query: {str(e)}", exc_info=True)

    def shutdown_services(self):
        """Stops servers and exits gracefully."""
        self.running = False
        self.db_com.update_production_status1(0)
        self.db_com.update_production_status2(0)
        self.greeting_server.stop_server()
        self.greeting_server1.stop_server()
        logging.info("✅ Services stopped. Exiting...")

    def run(self):
        """Starts the socket servers and runs the query loop."""
        logging.info("🚀 Starting socket servers...")

        try:
            self.thread1.start()
            self.thread2.start()
        except Exception as e:
            logging.error(f"❌ Error starting threads: {str(e)}", exc_info=True)
            return

        logging.info("✅ Servers started. Entering main loop...")

        while self.running:
            time.sleep(5)
            self.send_query()

if __name__ == "__main__":
    service = MainSocketService()
    service.run()
