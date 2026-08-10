import re
from typing import List, Dict, Any

class JSToken:
    def __init__(self, token_type: str, value: str, line: int):
        self.type = token_type
        self.value = value
        self.line = line

    def __repr__(self):
        return f"JSToken({self.type}, {repr(self.value)}, Line {self.line})"

class JavaScriptParser:
    """
    Tokenizer and parser for JavaScript files.
    Strips single-line and block comments, isolates string literals,
    and returns code tokens with precise line number attribution.
    """

    @classmethod
    def strip_comments(cls, js_code: str) -> str:
        """
        Replace comments with whitespace while preserving strings and line count.
        """
        result = []
        i = 0
        n = len(js_code)
        in_string = None
        escaped = False

        while i < n:
            char = js_code[i]
            nxt = js_code[i + 1] if i + 1 < n else ""

            if in_string:
                result.append(char)
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == in_string:
                    in_string = None
                i += 1
                continue

            if char in ("'", '"', "`"):
                in_string = char
                result.append(char)
                i += 1
                continue

            if char == "/" and nxt == "/":
                result.extend("  ")
                i += 2
                while i < n and js_code[i] not in "\r\n":
                    result.append(" ")
                    i += 1
                continue

            if char == "/" and nxt == "*":
                result.extend("  ")
                i += 2
                while i < n:
                    if js_code[i] == "*" and i + 1 < n and js_code[i + 1] == "/":
                        result.extend("  ")
                        i += 2
                        break
                    result.append("\n" if js_code[i] == "\n" else " ")
                    i += 1
                continue

            result.append(char)
            i += 1

        return "".join(result)

    @classmethod
    def mask_string_literals(cls, js_code: str, replacement: str = " ") -> str:
        """
        Replace string/template literal contents with whitespace, preserving code layout.
        Comments should already be removed or harmlessly ignored by strip_comments().
        """
        clean = cls.strip_comments(js_code)
        result = []
        i = 0
        n = len(clean)
        in_string = None
        escaped = False

        while i < n:
            char = clean[i]

            if in_string:
                result.append("\n" if char == "\n" else replacement)
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == in_string:
                    in_string = None
                i += 1
                continue

            if char in ("'", '"', "`"):
                in_string = char
                result.append(replacement)
                i += 1
                continue

            result.append(char)
            i += 1

        return "".join(result)

    @classmethod
    def parse_code_lines(cls, js_code: str) -> List[Dict[str, Any]]:
        """
        Returns line-by-line breakdown of code, stripping comments while preserving line numbers.
        Strings and identifiers are preserved.
        """
        lines = js_code.splitlines()
        clean_lines = cls.strip_comments(js_code).splitlines()
        parsed_lines = []

        for i, line_text in enumerate(lines, start=1):
            cleaned = clean_lines[i - 1] if i - 1 < len(clean_lines) else ""
            parsed_lines.append({
                "line": i,
                "raw": line_text,
                "clean": cleaned
            })

        return parsed_lines

    @classmethod
    def extract_string_literals(cls, js_code: str) -> List[Dict[str, Any]]:
        """
        Extracts all string literals with line number attribution.
        Handles double quotes, single quotes, and template literals.
        """
        clean_code = cls.strip_comments(js_code)
        results = []
        i = 0
        n = len(clean_code)
        current_line = 1

        while i < n:
            char = clean_code[i]
            if char == "\n":
                current_line += 1
                i += 1
                continue
            if char not in ("'", '"', "`"):
                i += 1
                continue

            quote = char
            start = i
            line_num = current_line
            i += 1
            escaped = False

            while i < n:
                current = clean_code[i]
                if current == "\n":
                    current_line += 1
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    i += 1
                    break
                i += 1

            raw = clean_code[start:i]
            if len(raw) >= 2 and raw[-1] == quote:
                results.append({
                    "line": line_num,
                    "raw_string": raw,
                    "value": raw[1:-1]
                })

        return results
