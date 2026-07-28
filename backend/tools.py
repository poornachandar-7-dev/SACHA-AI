"""
SACHA — Tools & automation module (refactored).

"""

from __future__ import annotations

import logging
import os
import re
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union
from urllib.parse import urlparse, quote_plus

# --- Logging ----------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Simple default logging configuration if none is configured by app
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# --- Optional dependencies ---------------------------------------------------
try:
    import cv2  # type: ignore
    OPENCV_AVAILABLE = True
except Exception:
    cv2 = None  # type: ignore
    OPENCV_AVAILABLE = False

try:
    from PIL import Image  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    Image = None  # type: ignore
    PIL_AVAILABLE = False


# --- Types & Registry -------------------------------------------------------
ToolReturn = Union[str, Dict[str, Any]]
TOOLS: Dict[str, Callable[[Optional[str]], ToolReturn]] = {}


def register_tool(name: str) -> Callable[[Callable[[Optional[str]], ToolReturn]], Callable[[Optional[str]], ToolReturn]]:
    """Decorator to register a tool function in the TOOLS dictionary."""
    def decorator(func: Callable[[Optional[str]], ToolReturn]) -> Callable[[Optional[str]], ToolReturn]:
        TOOLS[name] = func
        logger.debug("Registered tool '%s' -> %s", name, func)
        return func
    return decorator


# --- Known sites ------------------------------------------------------------
KNOWN_SITES: Dict[str, str] = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "twitter": "https://twitter.com",
    "linkedin": "https://linkedin.com",
}


# --- Utilities --------------------------------------------------------------
def is_headless() -> bool:
    """Rudimentary check for headless environment (Linux DISPLAY or CI)."""
    if os.name == "nt":
        # On Windows, assume not headless (best-effort)
        return False
    # Common CI or docker indicators
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return True
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return True
    return False


def _normalize_url(candidate: str) -> Optional[str]:
    """
    Return a normalized URL if candidate looks like a URL or known site.
    Adds https:// if scheme missing for domain-like inputs.
    """
    if not candidate:
        return None
    candidate = candidate.strip().strip('\'"')
    # Direct full URL
    parsed = urlparse(candidate)
    if parsed.scheme in ("http", "https"):
        return candidate
    # If candidate matches known site key
    lower = candidate.lower()
    if lower in KNOWN_SITES:
        return KNOWN_SITES[lower]
    # If looks like domain e.g. "github.com" or "youtube.com" or "example"
    if re.match(r"^[\w.-]+\.[a-zA-Z]{2,}$", candidate):
        return f"https://{candidate}"
    # If simple name, try known sites' keys
    if lower in KNOWN_SITES:
        return KNOWN_SITES[lower]
    return None


def _safe_filename(name: str) -> str:
    """Sanitize filename to avoid directory traversal etc."""
    name = name.strip().strip('\'"')
    p = Path(name).name  # drop directories
    # fallback default
    if not p:
        return "output.jpg"
    return p


# --- Tools ------------------------------------------------------------------
@register_tool("open_site")
def _run_open_site(arg: Optional[str]) -> str:
    """
    Opens a website based on the arg. Accepts:
      - Known site keys (youtube, github)
      - Domain strings (github.com)
      - Full URLs (https://github.com/...)
      - Anything else: falls back to a web search for the term.
    """
    if not arg:
        return "No site or URL provided."

    if is_headless():
        logger.warning("Environment appears headless; not opening a browser.")
        return "Headless environment detected; cannot open a browser."

    url = _normalize_url(arg)
    if not url:
        # Unknown site/domain: fall back to a web search instead of failing.
        query = arg.strip().strip('\'"')
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        try:
            webbrowser.open_new_tab(url)
            logger.info("Unknown site '%s'; opened web search instead: %s", arg, url)
            return f"I don't know a site called '{arg}', so I searched the web for it: {url}"
        except Exception as exc:  # pragma: no cover - environment-specific
            logger.exception("Failed to open search URL %s", url)
            return f"I don't know a site called '{arg}' and failed to open a search: {exc}"

    try:
        # Prefer a non-blocking new tab
        webbrowser.open_new_tab(url)
        logger.info("Opened URL: %s", url)
        return f"Opened {url} in your web browser."
    except Exception as exc:  # pragma: no cover - environment-specific
        logger.exception("Failed to open URL %s", url)
        return f"Failed to open '{url}': {exc}"


@register_tool("get_image_info")
def _run_get_image_info(arg: Optional[str]) -> str:
    """
    Reads an image using OpenCV if available, else Pillow, and returns dimensions and basic info.
    Argument is a file path.
    """
    if not arg:
        return "No file path provided."

    path = Path(arg.strip().strip('\'"'))
    if not path.exists():
        return f"File not found: {path}"

    # Try OpenCV first
    try:
        if OPENCV_AVAILABLE and cv2 is not None:
            img = cv2.imread(str(path))
            if img is None:
                # OpenCV couldn't decode; fall through to Pillow if available
                raise ValueError("cv2.imread returned None")
            height, width = img.shape[:2]
            channels = img.shape[2] if img.ndim == 3 else 1
            channel_info = f"{channels} channels (e.g., BGR)" if channels > 1 else "Grayscale"
            return f"Image '{path.name}': {width}x{height} pixels, {channel_info}."
    except Exception:
        logger.debug("OpenCV could not read image '%s', trying Pillow if available.", path, exc_info=True)

    # Pillow fallback
    try:
        if PIL_AVAILABLE and Image is not None:
            with Image.open(path) as im:
                width, height = im.size
                mode = im.mode
                channel_info = f"mode={mode}"
                return f"Image '{path.name}': {width}x{height} pixels, {channel_info}."
    except Exception as exc:
        logger.exception("Failed to read image '%s' with Pillow", path)
        return f"Failed to read image '{path}': {exc}"

    return f"Unable to read image '{path}'. Install opencv-python or pillow (PIL)."


@register_tool("capture_webcam")
def _run_capture_webcam(arg: Optional[str]) -> str:
    """
    Captures a single frame from a webcam and saves it.
    Arg may be:
      - filename (e.g., 'photo.jpg')
      - or 'device:INDEX filename' e.g., 'device:1 myphoto.png'
    """
    if not OPENCV_AVAILABLE or cv2 is None:
        return "OpenCV (cv2) is not installed. Please install with 'pip install opencv-python'."

    # Default values
    device_idx = 0
    filename = "webcam_capture.jpg"

    if arg:
        # support optional "device:1 filename.jpg"
        parts = arg.strip().split()
        # look for device:
        for p in parts[:2]:
            m = re.match(r"device:(\d+)", p, re.IGNORECASE)
            if m:
                device_idx = int(m.group(1))
        # last part that looks like a filename
        filename_candidate = parts[-1]
        if not re.match(r"^device:\d+$", filename_candidate, re.IGNORECASE):
            filename = filename_candidate

    filename = _safe_filename(filename)
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        filename += ".jpg"

    out_path = Path.cwd() / filename

    cap = None
    try:
        cap = cv2.VideoCapture(device_idx)
        if not cap.isOpened():
            return f"Failed to open webcam device {device_idx}. Is the camera connected and accessible?"

        ret, frame = cap.read()
        if not ret or frame is None:
            return "Failed to capture a frame from the webcam."

        # cv2.imwrite returns boolean success
        ok = cv2.imwrite(str(out_path), frame)
        if not ok:
            return f"Failed to write image to '{out_path}'."
        logger.info("Saved webcam image to %s", out_path)
        return f"Captured image and saved to '{out_path}'."
    except Exception as exc:
        logger.exception("Error capturing webcam image")
        return f"Error capturing webcam image: {exc}"
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                logger.debug("Exception releasing webcam capture", exc_info=True)


# --- Intent Detection -------------------------------------------------------
@dataclass
class ToolCall:
    tool: Optional[str]
    arg: Optional[str]


def detect_tool_call(message: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Heuristic intent detection returning (tool_name, arg) or (None, None).

    Supported examples:
      - "open youtube"
      - "go to github.com"
      - "open https://github.com/..."
      - "read image 'images/pic.png'"
      - "take a picture named my_photo.jpg"
      - "capture webcam device:1 myphoto.png"
    """
    if not message:
        return None, None
    msg = message.strip()
    msg_lower = msg.lower()

    # Direct URL anywhere in the string
    url_match = re.search(r"(https?://[^\s'\"<>]+)", msg)
    if url_match:
        return "open_site", url_match.group(1)

    # Image info: "read image <path>", "get info for image 'path'"
    # (checked before the domain match so filenames like 'test.png' aren't
    # misdetected as a website domain)
    m = re.search(r"(?:get info|read|analyze|info for)\s+(?:image|photo|picture)\s+['\"]?([^'\"]+)['\"]?", msg_lower)
    if m:
        return "get_image_info", m.group(1).strip()

    # Webcam capture: "take a picture named xyz.jpg" or "capture webcam device:1 name"
    # (also checked before the domain match, for the same reason as above)
    if re.search(r"\b(?:take|capture|snap)\b.*\b(?:picture|photo|webcam|selfie)\b", msg_lower):
        # optional named <filename>
        name_m = re.search(r"(?:named|called|as)\s+['\"]?([^'\"]+)['\"]?", msg_lower)
        device_m = re.search(r"device:(\d+)", msg_lower)
        parts = []
        if device_m:
            parts.append(f"device:{device_m.group(1)}")
        if name_m:
            parts.append(name_m.group(1).strip())
        arg = " ".join(parts) if parts else "webcam_capture.jpg"
        return "capture_webcam", arg

    # Domain-like without scheme: github.com or example.org
    domain_match = re.search(r"\b([\w.-]+\.[a-zA-Z]{2,})\b", msg)
    if domain_match:
        candidate = domain_match.group(1)
        url = _normalize_url(candidate)
        if url:
            return "open_site", url

    # "open <site>" or "go to <site>" or "launch <site>"
    m = re.search(r"\b(?:open|go to|launch)\s+['\"]?([^'\"]+)['\"]?", msg, re.IGNORECASE)
    if m:
        return "open_site", m.group(1).strip()

    return None, None


# --- Tool Execution --------------------------------------------------------
def run_tool(tool_name: Optional[str], arg: Optional[str]) -> str:
    """Executes a tool by name with the given argument and returns a string result."""
    if not tool_name:
        return "No tool specified."

    tool_fn = TOOLS.get(tool_name)
    if not tool_fn:
        return f"Unknown tool: '{tool_name}'. Available: {', '.join(sorted(TOOLS.keys()))}"

    try:
        result = tool_fn(arg)
        if isinstance(result, dict):
            # Convert to readable string summary
            return str(result)
        return result
    except Exception as exc:
        logger.exception("Error running tool %s", tool_name)
        return f"Error running tool '{tool_name}': {exc}"


# --- Module exports ---------------------------------------------------------
__all__ = [
    "TOOLS",
    "register_tool",
    "detect_tool_call",
    "run_tool",
    "KNOWN_SITES",
    "is_headless",
]


# --- CLI / Example usage ---------------------------------------------------
if __name__ == "__main__":  # pragma: no cover - manual testing helper
    import argparse

    parser = argparse.ArgumentParser(description="SACHA tools manual runner")
    parser.add_argument("action", choices=["test", "open", "img", "capture"], help="Action to run")
    parser.add_argument("arg", nargs="*", help="Argument for the tool (path, url, filename)")
    args = parser.parse_args()

    if args.action == "test":
        tests = [
            "Open youtube",
            "Go to https://github.com",
            "Take a picture named my_photo.jpg",
            "Read image test.png"
        ]
        for t in tests:
            tool, a = detect_tool_call(t)
            print(f"> {t}\nDetected: {tool}, Arg: {a}\nResult: {run_tool(tool, a)}\n")
    elif args.action == "open":
        tool, a = detect_tool_call(" ".join(["open"] + args.arg))
        print(run_tool(tool, a))
    elif args.action == "img":
        tool, a = detect_tool_call(" ".join(["read image"] + args.arg))
        print(run_tool(tool, a))
    elif args.action == "capture":
        tool, a = detect_tool_call(" ".join(["capture webcam"] + args.arg))
        print(run_tool(tool, a))