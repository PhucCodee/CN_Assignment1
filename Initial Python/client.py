import socket
import json
import os
from process import generate_file_hash, generate_magnet_link


class Client:
    def __init__(self, tracker_host="127.0.0.1", tracker_port=5001):
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.node_id = (
            None  # Node ID will be generated when registering with the tracker
        )

    def connect_to_tracker(self):
        """Establish a connection with the tracker."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.tracker_host, self.tracker_port))
        except Exception as e:
            print(f"Failed to connect to tracker: {e}")
            exit(1)

    def upload_file(self, file_path, file_name):
        """Upload a file by registering it with the tracker (called only once)."""
        print(f"Uploading file: {file_path}")
        file_hash = generate_file_hash(file_path)
        magnet_link = generate_magnet_link(file_path)
        request = {
            "node_id": self.node_id,
            "command": "upload",
            "file_name": file_name,
            "file_hash": file_hash,
            "file_pieces": [],  # No pieces for now
            "magnet_link": magnet_link,
        }
        self.send_request(request)

    def download_file(self, file_name):
        """Request peers for downloading a file."""
        request = {
            "command": "download",
            "file_name": file_name,
            "file_hash": "",
            "file_pieces": [],  # No pieces for now
            "magnet_link": "",
        }

        self.send_request(request)

    def send_request(self, request):
        """Send a request to the tracker with a retry mechanism."""
        try:
            # Send request
            self.client_socket.send(json.dumps(request).encode("utf-8"))

            # Increase timeout in case of delayed response
            self.client_socket.settimeout(10)

            # Receive response
            response = self.client_socket.recv(1024).decode("utf-8")
            print("Response from tracker:", response)
        except socket.timeout:
            print("Request timed out. Retrying...")
        except Exception as e:
            print(f"Error sending request: {e}")

    def run(self):
        """Run the client interface for uploading and downloading files."""
        while True:
            print("Choose an option:")
            print("1. Upload file")
            print("2. Download file")
            print("3. Exit")
            choice = input("Enter your choice: ")

            if choice == "1":
                file_path = input("Enter the path of the file to upload: ")
                file_name = input("Enter the name of the file to upload: ")
                if os.path.exists(file_path):
                    self.upload_file(file_path, file_name)
                else:
                    print("File does not exist.")
            elif choice == "2":
                file_name = input("Enter the file name to download: ")
                save_location = input("Enter the location to save the file: ")
                self.download_file(file_name)
            elif choice == "3":
                print("Exiting...")
                self.client_socket.close()
                break
            else:
                print("Invalid option. Please try again.")


if __name__ == "__main__":
    client = Client()
    client.connect_to_tracker()
    client.run()
