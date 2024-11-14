import hashlib

def generate_magnet_link(file_path):
    # Calculate SHA-1 hash of the file content
    hasher = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            hasher.update(chunk)
    file_hash = hasher.hexdigest()
    return f"magnet:?xt=urn:btih:{file_hash}"

def generate_file_hash(file_path):
    """Generate a file hash (SHA-1) from the file content."""
    sha1_hash = hashlib.sha1()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):  # Read file in chunks
                sha1_hash.update(chunk)
        return sha1_hash.hexdigest()
    except Exception as e:
        print(f"Error generating hash for {file_path}: {e}")
        return None

# H:/Study/CS/Computer networks/Assignment/src/tc1.txt