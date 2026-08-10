from analyzers.javascript_parser import JavaScriptParser

def test_strip_comments_and_parse_lines():
    code = """// Line 1 single line comment
const a = 10; /* Block comment */
/* Multi line
   block comment */
const b = 20;
"""
    parsed = JavaScriptParser.parse_code_lines(code)
    assert len(parsed) == 5
    assert parsed[0]["clean"].strip() == ""
    assert "const a = 10;" in parsed[1]["clean"]
    assert parsed[2]["clean"].strip() == ""
    assert "const b = 20;" in parsed[4]["clean"]

def test_extract_string_literals():
    code = """
const url = "https://example.com/api";
const template = `Hello ${name}`;
"""
    strings = JavaScriptParser.extract_string_literals(code)
    assert len(strings) == 2
    assert strings[0]["value"] == "https://example.com/api"
    assert strings[0]["line"] == 2

def test_urls_inside_strings_are_not_treated_as_comments():
    code = """
const api = "http://127.0.0.1:8000/test";
const secure = 'https://example.com/path';
// const ignored = "https://comment.example/path";
"""
    parsed = JavaScriptParser.parse_code_lines(code)

    assert '"http://127.0.0.1:8000/test"' in parsed[1]["clean"]
    assert "'https://example.com/path'" in parsed[2]["clean"]
    assert "comment.example" not in parsed[3]["clean"]

def test_mask_string_literals_keeps_real_code_and_removes_demo_strings():
    code = """
const demo = "chrome.history.search()";
chrome.cookies.getAll({}, callback);
"""
    masked = JavaScriptParser.mask_string_literals(code)

    assert "chrome.history.search" not in masked
    assert "chrome.cookies.getAll" in masked

def test_block_comments_and_escaped_quotes_are_handled():
    code = r'''
const text = "quoted \" // still string";
/* chrome.cookies.getAll() */
chrome.cookies.getAll({}, callback);
'''
    parsed = JavaScriptParser.parse_code_lines(code)

    assert "still string" in parsed[1]["clean"]
    assert "chrome.cookies.getAll" not in parsed[2]["clean"]
    assert "chrome.cookies.getAll" in parsed[3]["clean"]
