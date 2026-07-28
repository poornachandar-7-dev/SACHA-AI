import tools

def test_detect_domain_not_confused_with_filename():
    """Regression test: filenames shouldn't be misdetected as domains."""
    tool, arg = tools.detect_tool_call("take a picture named my_photo.jpg")
    assert tool == "capture_webcam"

    tool, arg = tools.detect_tool_call("read image test.png")
    assert tool == "get_image_info"


def test_detect_domain_not_confused_with_filename():
    """Regression test: filenames shouldn't be misdetected as domains."""
    tool, arg = tools.detect_tool_call("take a picture named my_photo.jpg")
    assert tool == "capture_webcam"

    tool, arg = tools.detect_tool_call("read image test.png")
    assert tool == "get_image_info"

    tool, arg = tools.detect_tool_call("open example.com")
    assert tool == "open_site"