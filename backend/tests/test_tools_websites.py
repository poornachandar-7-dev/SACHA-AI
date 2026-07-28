import tools

def test_detect_go_to_domain():
    tool, arg = tools.detect_tool_call("go to github.com")
    assert tool == "open_site"
    assert "github.com" in arg

def test_detect_go_to_domain():
       tool, arg = tools.detect_tool_call("go to github.com")
       assert tool == "open_site"
       assert "github.com" in arg