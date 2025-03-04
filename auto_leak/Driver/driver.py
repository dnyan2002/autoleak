import threading
import logging
import time
from database_communication import DatabaseCommunication
from socket_server import GreetingServer

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
        
        self.db_com = DatabaseCommunication()
        self.port1 = 9090
        self.port2 = 5050

        self.server1 = GreetingServer(self.port1)
        self.server2 = GreetingServer(self.port2)

        self.thread1 = threading.Thread(target=self.server1.run, daemon=True)
        self.thread2 = threading.Thread(target=self.server2.run, daemon=True)
        self.running = True
        logging.info("✅ MainSocketService initialized.")

    def shutdown_services(self):
        """Stops servers and exits gracefully."""
        logging.info("🛑 Shutting down services...")
        self.running = False
        
        self.server1.stop()
        self.server2.stop()
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
        
        try:
            while self.running:
                time.sleep(5)
        except KeyboardInterrupt:
            self.shutdown_services()

if __name__ == "__main__":
    service = MainSocketService()
    service.run()
