import time 
import os 
import libtorrent as lt 
from loggers import *
import requests
import socket




def is_internet_available():
    """Check if internet is available by resolving a common domain (Google)."""
    try:
        socket.gethostbyname("google.com")
        return True
    except socket.gaierror:
        return False
    


def download_specific_file(year, torrent_file, save_path, file_name, 
                           max_file_size_gb=1,
                           min_download_speed=10,
                           max_stall_time=300,
                           max_connection_attempts=3):
    """
    Download ONLY a specific file from a torrent by:
    1. Setting all other files to priority 0 (don't download)
    2. Using sparse allocation to save disk space
    3. Forcing sequential download for the target file
    """
    # Ensure save path exists
    os.makedirs(save_path, exist_ok=True)
    
    # Create session with optimized settings
    settings = {
        'download_rate_limit': 0,
        'upload_rate_limit': 0,
        'active_downloads': 1,
        'connections_limit': 200,
        'peer_connect_timeout': 15,
        'min_reconnect_time': 30,
        'listen_interfaces': '0.0.0.0:0',
        'enable_outgoing_utp': True,
        'enable_incoming_utp': True,
        'prefer_rc4': True,
        'enable_dht': True,
        'enable_lsd': True,
        'enable_upnp': True,
        'enable_natpmp': True,
    }
    ses = lt.session(settings)
    
    # Add the torrent with specific flags
    params = {
        'ti': lt.torrent_info(torrent_file),
        'save_path': save_path,
        'storage_mode': lt.storage_mode_t.storage_mode_sparse,  # Sparse allocation
        'flags': lt.torrent_flags.sequential_download |  # Sequential download
                 lt.torrent_flags.duplicate_is_error |
                 lt.torrent_flags.auto_managed,
    }
    
    try:
        h = ses.add_torrent(params)
    except Exception as e:
        msg = f"❌ ❌ ❌ Error adding torrent: {e}"
        return False , msg

    info = h.get_torrent_info()
    log_info(year, f"Torrent added: {info.name()}")

    # Set file priorities - only download our target file
    file_priorities = [0] * info.num_files()  # Set all files to 0 (don't download)
    target_file_index = -1
    target_file_size_bytes = 0
    
    for i, f in enumerate(info.files()):
        if f.path.split('/')[-1] == file_name:
            target_file_index = i
            target_file_size_bytes = f.size
            file_size_gb = target_file_size_bytes / (1024**3)
            
            log_info(year, f"File found: {f.path}, Size: {file_size_gb:.2f} GB")
            
            if file_size_gb > max_file_size_gb:
                msg = f"❌ ❌ ❌ Inside torrent file size exceeds maximum allowed size. Aborting."
                return False , msg
            
            file_priorities[i] = 7  # Highest priority for our target file
            log_info(year, f"Priority set to download")
            break
    
    if target_file_index == -1:
        msg = f"❌ ❌ ❌ Error: File inside not found in the torrent."
        return False , msg

    # Apply priorities and sequential download to our file
    h.prioritize_files(file_priorities)
    
    # Set sequential download for our file (this helps avoid downloading other files)
    h.set_sequential_download(True)
    
    # Calculate maximum download time based on file size
    # Formula: Allow 1 minute per 15 MB (adjustable), with a minimum of 10 minutes
    file_size_mb = target_file_size_bytes / (1024**2)
    max_download_time = max(22 * 60, int(file_size_mb /7 ) * 60)
    log_info(year, f"Calculated max download time: {max_download_time // 60} minutes based on file size of {file_size_mb:.2f} MB")

    # Enhanced tracker list with more reliable trackers
    trackers = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://tracker.openbittorrent.com:80/announce",
        "udp://tracker.internetwarriors.net:1337/announce",
        "udp://9.rarbg.to:2710/announce",
        "udp://exodus.desync.com:6969/announce",
        "udp://tracker.torrent.eu.org:451/announce",
        "udp://tracker.cyberia.is:6969/announce",
        "udp://tracker.tiny-vps.com:6969/announce",
        "udp://open.stealth.si:80/announce"
    ]
    
    # Add trackers
    for tracker in trackers:
        h.add_tracker({'url': tracker})
    
    # Force initial announce
    try:
        h.force_reannounce()
    except Exception as e:
        msg = f"❌ ❌ ❌ Reannounce error: {e}"
        return False , msg

    # Download monitoring variables
    start_time = time.time()
    elapsed_download_time = 0
    stall_time = 0
    connection_attempts = 0
    last_progress = 0
    last_check_time = start_time
    i = -1
    
    while True:
        i += 1
        current_time = time.time()
        
        # Check if internet is available
        if not is_internet_available():
            log_info(year, "Internet connection is down. Pausing timers.")
            # Update the start time to effectively pause the timer
            time_since_last_check = current_time - last_check_time
            start_time += time_since_last_check
            time.sleep(10)  # Check less frequently when internet is down
            last_check_time = time.time()
            continue
        
        # Update elapsed time only when internet is available
        elapsed_download_time = current_time - start_time
        last_check_time = current_time
        
        if i % 4 == 0:
            log_info(year, f'Downloading for {int(elapsed_download_time)} seconds i.e. {elapsed_download_time // 60} minutes')
        
        s = h.status()
        
        # Robust progress tracking
        try:
            progress = max(getattr(s, 'progress', 0), 
                           getattr(s, 'progress_ppm', 0) / 1000000.0)
            download_rate = max(getattr(s, 'download_rate', 0), 
                                getattr(s, 'download_payload_rate', 0))
            upload_rate = max(getattr(s, 'upload_rate', 0), 
                              getattr(s, 'upload_payload_rate', 0))
            num_peers = max(getattr(s, 'num_peers', 0), 
                            getattr(s, 'num_connections', 0))
        except Exception as e:
            log_info(year, f"Status tracking error: {e}")
            download_rate = 0
            upload_rate = 0
            num_peers = 0
        
        if i % 4 == 0:
            # Detailed progress logging
            log_info(year, f"Progress: {progress * 100:.2f}% | "
                f"Download: {download_rate / 1000:.2f} kB/s | "
                f"Upload: {upload_rate / 1000:.2f} kB/s | "
                f"Peers: {num_peers}")
        
        # Download complete check
        if progress >= 0.999:
            log_info(year, "Download completed successfully!")
            return True , None
        
        # Check download timeout
        if elapsed_download_time > max_download_time:
            msg = f"❌ ❌ ❌ Download aborted: Exceeded maximum time of {max_download_time // 60} minutes"
            return False , msg
        
        # Check download speed
        download_speed_kbps = download_rate / 1000
        if download_speed_kbps < min_download_speed:
            stall_time += 5
            
            # Attempt to reconnect if download is stalled
            if stall_time > max_stall_time:
                if connection_attempts < max_connection_attempts:
                    log_info(year, "Download stalled. Attempting to reconnect...")
                    try:
                        h.force_reannounce()
                        connection_attempts += 1
                    except Exception as e:
                        msg = f"❌ ❌ ❌ Reconnection error: {e}"
                        return False , msg
                    stall_time = 50
                else:
                    msg = "❌ ❌ ❌ Maximum reconnection attempts reached. Aborting download."
                    return False , msg
        else:
            stall_time = 0
        
        # Progress check to prevent false stalls
        if progress > last_progress:
            last_progress = progress
        
        time.sleep(5)

        






def download_torrent(year , url, target_folder, file_name):
    # Make sure the target folder exists
    os.makedirs(target_folder, exist_ok=True)

    # Full file path to save the torrent file
    file_path = os.path.join(target_folder, file_name)

    # Check if the file already exists
    if os.path.exists(file_path):
        log_info(year , f"File already exists at: {file_path}. Skipping download.")
        return file_path  # Optional: return the existing file path

    try:
        # Send HTTP GET request to download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an error for bad status codes

        # Write the content to a file in chunks
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        log_info(year , f"File downloaded successfully and saved to: {file_path}")
        return file_path  # Optional: return the downloaded file path

    except requests.exceptions.RequestException as e:
        log_error(year , f"An error occurred while downloading: {e}")
        return None  # Optional: return None if download failed
    
