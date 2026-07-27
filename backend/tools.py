"""
SACHA — Tools & automation module.

v2 scope: Improved architecture with decorator-based registration, 
robust intent detection, and added OpenCV capabilities.



Will import other librariers for connections
"""

import re
import webbrowser
import os
from typing import Optional, Tuple, Dict, Callable

# --- OpenCV Availability Check -------------------------------------------
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


# --- Tool Registry -------------------------------------------------------
# Dictionary to hold registered tools: {tool_name: function}
TOOLS: Dict[str, Callable[[str], str]] = {}


def register_tool(name: str):
    """
    Decorator to register a tool function in the TOOLS dictionary.
    This makes adding new tools clean and automatic.
    """
    def decorator(func: Callable[[str], str]):
        TOOLS[name] = func
        return func
    return decorator


# --- Tool: Open Website --------------------------------------------------

KNOWN_SITES = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "twitter": "https://twitter.com",
    "linkedin": "https://linkedin.com",
}


@register_tool("open_site")
def _run_open_site(query: str) -> str:
    """Opens a website based on the query. Supports known site names or direct URLs."""
    query = query.lower().strip()
    
    # Check if it's a direct URL
    if query.startswith(("http://", "https://")):
        url = query
    else:
        # Check against known sites
        url = KNOWN_SITES.get(query)
        
    if not url:
        return f"I don't know a site called '{query}' yet. Try adding it to KNOWN_SITES or provide a full URL."
    
    try:
        webbrowser.open(url)
        return f"Successfully opened '{query}' in your web browser."
    except Exception as e:
        return f"Failed to open '{query}': {str(e)}"


# --- Tool: OpenCV Image Info ---------------------------------------------

@register_tool("get_image_info")
def _run_get_image_info(file_path: str) -> str:
    """Reads an image using OpenCV and returns its dimensions and basic info."""
    if not OPENCV_AVAILABLE:
        return "OpenCV (cv2) is not installed. Please install it using 'pip install opencv-python'."

    # Clean up the file path (remove quotes if user included them)
    file_path = file_path.strip().strip('\'"')
    
    if not os.path.exists(file_path):
        return f"File not found: '{file_path}'. Please provide a valid absolute or relative path."
    
    try:
        img = cv2.imread(file_path)
        if img is None:
            return f"Failed to read image: '{file_path}'. The file might be corrupted or in an unsupported format."
        
        height, width, channels = img.shape
        channel_info = f"{channels} channels (e.g., BGR)" if channels > 1 else "Grayscale"
        return f"Image info for '{os.path.basename(file_path)}': {width}x{height} pixels, {channel_info}."
    except Exception as e:
        return f"Error processing image '{file_path}': {str(e)}"


# --- Tool: OpenCV Webcam Capture -----------------------------------------

@register_tool("capture_webcam")
def _run_capture_webcam(arg: str) -> str:
    """
    Captures a single frame from the default webcam and saves it.
    Argument can be the output filename (e.g., 'photo.jpg').
    """
    if not OPENCV_AVAILABLE:
        return "OpenCV (cv2) is not installed. Please install it using 'pip install opencv-python'."
    
    filename = arg.strip().strip('\'"') or "webcam_capture.jpg"
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        filename += ".jpg"
        
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Failed to open webcam. Make sure it is connected and not in use by another application."
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return "Failed to capture frame from webcam."
            
        cv2.imwrite(filename, frame)
        return f"Successfully captured image from webcam and saved as '{filename}'."
    except Exception as e:
        return f"Error capturing webcam image: {str(e)}"


# --- Intent Detection ----------------------------------------------------

def detect_tool_call(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Intent detection using pattern matching.
    Later this can be replaced with proper LLM-based function calling.
    
    Returns:
        Tuple of (tool_name, arg) if a tool matches, otherwise (None, None).
    """
    message_lower = message.lower().strip()
    
    # Pattern 1: "open <site/url>"
    match = re.search(r"\bopen\s+(.+)", message_lower)
    if match:
        return "open_site", match.group(1).strip()
        
    # Pattern 2: "go to <site>" or "launch <site>"
    match = re.search(r"\b(?:go to|launch)\s+(.+)", message_lower)
    if match:
        return "open_site", match.group(1).strip()
        
    # Pattern 3: Direct URL detection (if the message is or contains a URL)
    url_match = re.search(r"(https?://\S+)", message)
    if url_match:
        return "open_site", url_match.group(1)

    # Pattern 4: "get info for image <path>" or "read image <path>"
    img_match = re.search(r"(?:get info|read|analyze)\s+(?:image|photo|picture)\s+(.+)", message_lower)
    if img_match:
        return "get_image_info", img_match.group(1).strip()
        
    # Pattern 5: "take a picture" or "capture webcam"
    if re.search(r"\b(?:take|capture|snap)\s+(?:a\s+)?(?:picture|photo|webcam|selfie)\b", message_lower):
        # Extract filename if provided, e.g., "take a picture named test.jpg"
        name_match = re.search(r"named\s+(.+)", message_lower)
        arg = name_match.group(1).strip() if name_match else "webcam_capture.jpg"
        return "capture_webcam", arg
        
    return None, None


# --- Tool Execution ------------------------------------------------------

def run_tool(tool_name: str, arg: str) -> str:
    """Executes a tool by name with the given argument."""
    tool_fn = TOOLS.get(tool_name)
    if not tool_fn:
        return f"Unknown tool: '{tool_name}'. Available tools: {', '.join(TOOLS.keys())}"
    
    try:
        return tool_fn(arg)
    except Exception as e:
        return f"Error running tool '{tool_name}': {str(e)}"


# --- Example Usage / Testing ---------------------------------------------
if __name__ == "__main__":
    print("--- SACHA Tool Tests ---")
    
    # Test 1: Open known site
    tool, arg = detect_tool_call("Open youtube")
    print(f"Detected: {tool}, Arg: '{arg}'\nResult: {run_tool(tool, arg)}\n")
    
    # Test 2: Open direct URL
    tool, arg = detect_tool_call("Go to https://github.com")
    print(f"Detected: {tool}, Arg: '{arg}'\nResult: {run_tool(tool, arg)}\n")
    
    # Test 3: Webcam capture
    tool, arg = detect_tool_call("Take a picture named my_photo.jpg")
    print(f"Detected: {tool}, Arg: '{arg}'\nResult: {run_tool(tool, arg)}\n")
    
    # Test 4: Image info (will fail gracefully if file doesn't exist)
    tool, arg = detect_tool_call("Read image test.png")
    print(f"Detected: {tool}, Arg: '{arg}'\nResult: {run_tool(tool, arg)}\n")