import socket
import threading
import json
import os
from process import generate_file_hash, generate_magnet_link
import uuid


class Tracker:
    def __init__(self, host="0.0.0.0", port=2901):
        self.host = host
        self.port = port
        self.nodes = {}  # Stores file hash -> node_id -> node data (including file pieces)
        self.file_registry = {}  # Stores file name -> file hash for quick lookup
        self.lock = threading.Lock()

    def start_server(self):
        """Start the tracker server to listen for client connections."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Tracker server started on {self.host}:{self.port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"New connection from {client_address}")
            threading.Thread(target=self.handle_request, args=(client_socket,)).start()

    def handle_request(self, client_socket):
        """Handle incoming requests from clients (upload, download, etc.)."""
        try:
            data = client_socket.recv(1024).decode("utf-8")
            if not data:
                print("Received empty data. Closing connection.")
                return

            request = json.loads(data)
            command = request.get("command")
            print(f"Received command: {command}")

            if command == "register":
                self.register_node(request, client_socket)
            elif command == "upload":
                self.handle_upload(request, client_socket)
            elif command == "download":
                self.handle_download(request, client_socket)
            elif command == "upload_piece":
                self.handle_piece_upload(request, client_socket)
            else:
                response = {"error": "Unknown command"}
                client_socket.send(json.dumps(response).encode("utf-8"))

        except Exception as e:
            print(f"Error: {e}")
            response = {"error": f"Server error: {e}"}
            client_socket.send(json.dumps(response).encode("utf-8"))
        finally:
            client_socket.close()

    def generate_node_id(self):
        """Generates a unique ID for each node."""
        return f"node_{uuid.uuid4().hex[:8]}"

    def register_node(self, request, client_socket):
        """Register a new node and assign a unique node ID."""
        try:
            # Generate a unique node ID
            node_id = self.generate_node_id()

            # The peer sends the file name and file hash for the initial registration
            file_name = request.get("file_name")
            file_hash = request.get("file_hash")
            file_pieces = request.get("file_pieces", [])
            magnet_link = request.get("magnet_link")

            # Store the file registry for quick lookup by file name
            self.file_registry[file_name] = file_hash

            # Store the node information under the corresponding file hash
            with self.lock:
                if file_hash not in self.nodes:
                    self.nodes[file_hash] = {}
                self.nodes[file_hash][node_id] = {
                    "file_pieces": file_pieces,
                    "magnet_link": magnet_link,
                }

            response = {
                "status": "success",
                "node_id": node_id,
                "message": "Node registered successfully",
            }
            client_socket.send(json.dumps(response).encode("utf-8"))
        except Exception as e:
            print(f"Error in register_node: {e}")
            response = {"status": "error", "message": f"Server error: {e}"}
            client_socket.send(json.dumps(response).encode("utf-8"))

    def handle_upload(self, request, client_socket):
        """Handle file upload by registering the file and sharing pieces among peers."""
        try:
            node_id = request.get("node_id")
            file_name = request.get("file_name")
            file_hash = request.get("file_hash")
            file_pieces = request.get("file_pieces")
            magnet_link = request.get("magnet_link")

            with self.lock:
                if file_hash not in self.nodes:
                    self.nodes[file_hash] = {}

                self.nodes[file_hash][node_id] = {
                    "file_pieces": file_pieces,
                    "magnet_link": magnet_link,
                }

            # Share the file pieces with other peers for this file
            peers = self.get_peers(file_hash, node_id)

            response = {
                "status": "success",
                "message": "File uploaded successfully",
                "peers": peers,
            }
            client_socket.send(json.dumps(response).encode("utf-8"))
        except Exception as e:
            print(f"Error in handle_upload: {e}")
            response = {"status": "error", "message": f"Server error: {e}"}
            client_socket.send(json.dumps(response).encode("utf-8"))

    def get_peers(self, file_hash, exclude_node_id=None):
        """Return a list of peers (excluding the given node ID) holding file pieces."""
        peers = []
        for node_id, node_info in self.nodes[file_hash].items():
            if node_id != exclude_node_id:
                peers.append(
                    {
                        "node_id": node_id,
                        "magnet_link": node_info["magnet_link"],
                        "file_pieces": node_info["file_pieces"],
                    }
                )
        return peers

    def handle_download(self, request, client_socket):
        """Handle file download by finding peers that have the missing file pieces."""
        file_name = request.get("file_name")
        file_hash = self.file_registry.get(file_name)

            if not file_hash:
                response = {"status": "error", "message": "File not found"}
                client_socket.send(json.dumps(response).encode("utf-8"))
                return

        missing_pieces = request.get("missing_pieces", [])

        with self.lock:
            # Find peers with the missing file pieces
            peers = self.get_peers_with_pieces(file_hash, missing_pieces)

        if peers:
            response = {
                "status": "success",
                "message": "Peers found for downloading",
                "peers": peers,
            }
        else:
            response = {"status": "error", "message": "No peers with missing pieces"}
        client_socket.send(json.dumps(response).encode("utf-8"))

    def get_peers_with_pieces(self, file_hash, missing_pieces):
        """Return peers that have the requested file pieces."""
        peers = []
        for node_id, node_info in self.nodes[file_hash].items():
            file_pieces = node_info["file_pieces"]
            # Check if the peer has any of the missing pieces
            common_pieces = set(file_pieces).intersection(missing_pieces)
            if common_pieces:
                peers.append(
                    {
                        "node_id": node_id,
                        "file_pieces": list(common_pieces),
                        "magnet_link": node_info["magnet_link"],
                    }
                )
        return peers

    def save_piece(self, file_hash, piece_index, piece_data):
        os.makedirs(file_hash, exist_ok=True)
        with open(f"{file_hash}/{piece_index}.piece", "wb") as f:
            f.write(piece_data)

    def handle_piece_upload(self, request, client_socket):
        try:
            file_hash = request["file_hash"]
            piece_index = request["piece_index"]
            piece_data = base64.b64decode(request["piece_data"])

            self.save_piece(file_hash, piece_index, piece_data)

            response = {"status": "success", "message": "Piece saved successfully."}
            client_socket.send(json.dumps(response).encode("utf-8"))
        except Exception as e:
            print(f"Error in handle_piece_upload: {e}")
            response = {"status": "error", "message": f"Server error: {e}"}
            client_socket.send(json.dumps(response).encode("utf-8"))

    def get_missing_pieces(self, file_hash, client_pieces):
        stored_pieces = set(os.listdir(file_hash))
        missing = set(client_pieces) - {int(p.split(".")[0]) for p in stored_pieces}
        return list(missing)

    def assemble_file(self, file_hash):
        pieces = sorted(os.listdir(file_hash), key=lambda x: int(x.split(".")[0]))
        with open(f"{file_hash}.complete", "wb") as outfile:
            for piece in pieces:
                with open(f"{file_hash}/{piece}", "rb") as infile:
                    outfile.write(infile.read())


if __name__ == "__main__":
    tracker = Tracker()
    tracker.start_server()
