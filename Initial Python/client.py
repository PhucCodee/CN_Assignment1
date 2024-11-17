import socket
import json
import os
import time
import base64
from process import generate_file_hash, generate_magnet_link


class Client:
    def __init__(self, tracker_host="127.0.0.1", tracker_port=2901):
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.node_id = None
        self.client_socket = None

    def connect_to_tracker(self):
        """Establish a connection with the tracker."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.tracker_host, self.tracker_port))
            print("Connected to tracker.")
        except Exception as e:
            print(f"Failed to connect to tracker: {e}")
            exit(1)

    def upload_file(self, file_path, file_name):
        if not os.path.isfile(file_path):
            print(f"Error: {file_path} is not a valid file.")
            return

        print(f"Uploading file: {file_path}")
        file_hash = generate_file_hash(file_path)
        if file_hash is None:
            print(f"Error generating hash for {file_path}")
            return

        magnet_link = generate_magnet_link(file_path)
        pieces = self.divide_file(file_path)
        for index, piece in pieces:
            self.upload_piece(file_hash, index, piece)
            self.save_piece(file_hash, index, piece)  # Save piece locally
            print(f"Piece {index} saved successfully.")
        request = {
            "node_id": self.node_id,
            "command": "upload",
            "file_name": file_name,
            "file_hash": file_hash,
            "file_pieces": [index for index, _ in pieces],
            "magnet_link": magnet_link,
        }
        response = self.send_request(request)
        if response:
            response = json.loads(response)
            if response["status"] == "success":
                print("File uploaded successfully.")
            else:
                print(f"Error from tracker: {response['message']}")
        else:
            print("No response from tracker.")

    def download_file(self, file_name, save_location):
        print(f"Downloading file: {file_name}")
        request = {
            "command": "download",
            "file_name": file_name,
        }
        response = self.send_request(request)
        try:
            if response:
                response = json.loads(response)
                if response["status"] == "success":
                    missing_pieces = response.get("missing_pieces", [])
                    self.request_missing_pieces(file_name, missing_pieces)
                    for piece in missing_pieces:
                        piece_index = piece["piece_index"]
                        piece_data = base64.b64decode(piece["piece_data"])
                        self.save_piece(file_name, piece_index, piece_data)
                        print(f"Piece {piece_index} downloaded and saved successfully.")
                    self.reassemble_file(file_name, save_location, file_name)
                    print(f"File {file_name} reassembled successfully.")
                else:
                    print(f"Error from tracker: {response['message']}")
            else:
                print("No response from tracker.")
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON response: {e}")
        except Exception as e:
            print(f"Error receiving response: {e}")

    def send_request(self, request, expect_response=True):
        """Send a request to the tracker with an optional response handling."""
        try:
            # Convert the request dictionary to a JSON string
            request_str = json.dumps(request)
            # Send request as a JSON string
            self.client_socket.send(request_str.encode("utf-8"))

            if expect_response:
                # Wait indefinitely for a response
                response = self.client_socket.recv(1024).decode("utf-8")
                return response
        except (socket.error, Exception) as e:
            print(f"Error sending request: {e}")
        return None

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
                self.download_file(file_name, save_location)
            elif choice == "3":
                print("Exiting...")
                self.client_socket.close()
                time.sleep(2)
                print("Session terminated successfully")
                break
            else:
                print("Invalid option. Please try again.")

            print("\n")

    def divide_file(self, file_path, piece_size=1024):
        pieces = []
        with open(file_path, "rb") as f:
            index = 0
            while chunk := f.read(piece_size):
                pieces.append((index, chunk))
                index += 1
        return pieces

    def upload_piece(self, file_hash, piece_index, piece_data):
        encoded_piece_data = base64.b64encode(piece_data).decode("utf-8")
        request = {
            "command": "upload_piece",
            "file_hash": file_hash,
            "piece_index": piece_index,
            "piece_data": encoded_piece_data,
        }
        self.send_request(request, expect_response=False)

    def request_missing_pieces(self, file_name, missing_pieces):
        request = {
            "command": "download_pieces",
            "file_name": file_name,
            "missing_pieces": missing_pieces,
        }
        self.send_request(request)

    def save_piece(self, file_hash, piece_index, piece_data):
        os.makedirs(file_hash, exist_ok=True)
        with open(f"{file_hash}/{piece_index}.piece", "wb") as f:
            f.write(piece_data)

    def reassemble_file(self, file_hash, output_dir, file_name):
        pieces = sorted(os.listdir(file_hash), key=lambda x: int(x.split(".")[0]))
        output_path = os.path.join(output_dir, file_name)
        with open(output_path, "wb") as outfile:
            for piece in pieces:
                with open(f"{file_hash}/{piece}", "rb") as infile:
                    outfile.write(infile.read())


if __name__ == "__main__":
    client = Client()
    client.connect_to_tracker()
    # client.run()

    name = "test.txt"
    client.upload_file(f"/Users/tranhoangphuc/Downloads/{name}", f"{name}")
    print("\n")
    client.download_file(f"{name}", "/Users/tranhoangphuc/")
    print("\n")
