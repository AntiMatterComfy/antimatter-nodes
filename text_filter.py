import json
import re
from typing import Any, List, Optional, Sequence, Tuple


class AnyType(str):
    """ComfyUI socket type that accepts connected STRING or other text-like payloads."""

    def __ne__(self, __value: object) -> bool:
        return False


any_type = AnyType("*")

_OPERATIONS = [
    "pass_through",
    "extract_after",
    "extract_after_last",
    "extract_before",
    "extract_before_last",
    "extract_between",
    "remove_before",
    "remove_after",
    "remove_words",
    "remove_phrases",
    "remove_lines_containing",
    "keep_lines_containing",
    "remove_sentences_containing",
    "keep_sentences_containing",
    "remove_paragraphs_containing",
    "keep_paragraphs_containing",
    "replace_text",
    "regex_extract",
    "regex_remove",
    "regex_replace",
    "split_take",
    "dedupe_lines",
    "sort_lines",
    "trim_each_line",
    "remove_empty_lines",
    "clean_whitespace",
]

_SPLIT_SEPARATORS = ["newline", "comma", "semicolon", "pipe", "space", "custom"]
_JOIN_SEPARATORS = ["newline", "space", "comma", "semicolon", "pipe", "empty"]


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, tuple) and len(value) == 1:
        return _as_text(value[0])
    if isinstance(value, (list, tuple)):
        return "\n".join(_as_text(item) for item in value)
    if isinstance(value, (dict, set)):
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            return str(value)
    return str(value)


def _regex_flags(match_case: bool) -> int:
    flags = re.DOTALL | re.MULTILINE
    if not match_case:
        flags |= re.IGNORECASE
    return flags


def _literal_pattern(text: str, whole_word: bool) -> str:
    pattern = re.escape(text)
    if whole_word:
        pattern = rf"(?<!\w){pattern}(?!\w)"
    return pattern


def _compile(pattern: str, match_case: bool) -> re.Pattern:
    try:
        return re.compile(pattern, _regex_flags(match_case))
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}") from exc


def _find_spans(
    text: str,
    pattern: str,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> List[Tuple[int, int]]:
    pattern = _as_text(pattern)
    if not pattern:
        return []

    compiled = _compile(
        pattern if pattern_is_regex else _literal_pattern(pattern, whole_word),
        match_case,
    )
    return [match.span() for match in compiled.finditer(text)]


def _select_span(
    text: str,
    pattern: str,
    occurrence: str,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> Optional[Tuple[int, int]]:
    spans = _find_spans(text, pattern, match_case, whole_word, pattern_is_regex)
    if not spans:
        return None
    return spans[-1] if occurrence == "last" else spans[0]


def _extract_after(
    text: str,
    marker: str,
    occurrence: str,
    include_marker: bool,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> str:
    span = _select_span(text, marker, occurrence, match_case, whole_word, pattern_is_regex)
    if span is None:
        return ""
    start, end = span
    return text[start:] if include_marker else text[end:]


def _extract_before(
    text: str,
    marker: str,
    occurrence: str,
    include_marker: bool,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> str:
    span = _select_span(text, marker, occurrence, match_case, whole_word, pattern_is_regex)
    if span is None:
        return ""
    start, end = span
    return text[:end] if include_marker else text[:start]


def _extract_between(
    text: str,
    start_marker: str,
    end_marker: str,
    occurrence: str,
    include_markers: bool,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> str:
    start_span = _select_span(
        text,
        start_marker,
        occurrence,
        match_case,
        whole_word,
        pattern_is_regex,
    )
    if start_span is None:
        return ""

    search_from = start_span[1]
    end_span = None
    if end_marker:
        suffix = text[search_from:]
        suffix_spans = _find_spans(suffix, end_marker, match_case, whole_word, pattern_is_regex)
        if suffix_spans:
            end_span = (search_from + suffix_spans[0][0], search_from + suffix_spans[0][1])

    if include_markers:
        start = start_span[0]
        end = end_span[1] if end_span else len(text)
    else:
        start = start_span[1]
        end = end_span[0] if end_span else len(text)
    return text[start:end]


def _parse_items(items: Any, fallback: str = "") -> List[str]:
    source = _as_text(items)
    values: List[str] = []
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        for part in line.split(","):
            item = part.strip()
            if item:
                values.append(item)

    if not values:
        fallback_text = _as_text(fallback).strip()
        if fallback_text:
            values.append(fallback_text)
    return values


def _contains_any(
    text: str,
    patterns: Sequence[str],
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> bool:
    if not patterns:
        return False

    for pattern in patterns:
        if pattern_is_regex:
            if _compile(pattern, match_case).search(text):
                return True
        elif whole_word:
            if _compile(_literal_pattern(pattern, True), match_case).search(text):
                return True
        elif match_case:
            if pattern in text:
                return True
        elif pattern.lower() in text.lower():
            return True
    return False


def _remove_items(
    text: str,
    patterns: Sequence[str],
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> str:
    out = text
    for pattern in patterns:
        compiled = _compile(
            pattern if pattern_is_regex else _literal_pattern(pattern, whole_word),
            match_case,
        )
        out = compiled.sub("", out)

    out = re.sub(r"[ \t]+([,.;:!?])", r"\1", out)
    out = re.sub(r"([,;:]){2,}", r"\1", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out


def _filter_lines(
    text: str,
    patterns: Sequence[str],
    keep_matches: bool,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> str:
    if not patterns:
        return text
    lines = text.splitlines()
    kept = [
        line
        for line in lines
        if _contains_any(line, patterns, match_case, whole_word, pattern_is_regex) == keep_matches
    ]
    return "\n".join(kept)


def _split_sentences(text: str) -> List[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"(?<=[.!?])\s+|\n+", normalized)
    return [part for part in parts if part]


def _filter_sentences(
    text: str,
    patterns: Sequence[str],
    keep_matches: bool,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> str:
    if not patterns:
        return text
    sentences = _split_sentences(text)
    kept = [
        sentence.strip()
        for sentence in sentences
        if _contains_any(sentence, patterns, match_case, whole_word, pattern_is_regex) == keep_matches
    ]
    return " ".join(sentence for sentence in kept if sentence)


def _split_paragraphs(text: str) -> List[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [part for part in re.split(r"\n\s*\n+", normalized) if part]


def _filter_paragraphs(
    text: str,
    patterns: Sequence[str],
    keep_matches: bool,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
) -> str:
    if not patterns:
        return text
    paragraphs = _split_paragraphs(text)
    kept = [
        paragraph.strip()
        for paragraph in paragraphs
        if _contains_any(paragraph, patterns, match_case, whole_word, pattern_is_regex) == keep_matches
    ]
    return "\n\n".join(paragraph for paragraph in kept if paragraph)


def _regex_extract(text: str, pattern: str, match_case: bool, joiner: str) -> str:
    if not pattern:
        return ""
    matches = []
    for match in _compile(pattern, match_case).finditer(text):
        if match.lastindex:
            groups = [group for group in match.groups() if group is not None]
            matches.append(" ".join(groups) if len(groups) > 1 else groups[0])
        else:
            matches.append(match.group(0))
    return joiner.join(matches)


def _split_separator(kind: str, custom: str) -> str:
    if kind == "comma":
        return ","
    if kind == "semicolon":
        return ";"
    if kind == "pipe":
        return "|"
    if kind == "space":
        return " "
    if kind == "custom":
        return _as_text(custom)
    return "\n"


def _join_separator(kind: str) -> str:
    if kind == "space":
        return " "
    if kind == "comma":
        return ", "
    if kind == "semicolon":
        return "; "
    if kind == "pipe":
        return " | "
    if kind == "empty":
        return ""
    return "\n"


def _split_take(text: str, separator: str, index: int) -> str:
    if not separator:
        parts = list(text)
    elif separator == " ":
        parts = text.split()
    else:
        parts = text.split(separator)

    if not parts:
        return ""

    try:
        idx = int(index)
    except Exception:
        idx = 1
    idx = idx - 1 if idx > 0 else idx

    if -len(parts) <= idx < len(parts):
        return parts[idx]
    return ""


def _dedupe_lines(text: str, match_case: bool) -> str:
    seen = set()
    kept = []
    for line in text.splitlines():
        key = line if match_case else line.lower()
        if key in seen:
            continue
        seen.add(key)
        kept.append(line)
    return "\n".join(kept)


def _trim_each_line(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines())


def _remove_empty_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if line.strip())


def _clean_whitespace(text: str) -> str:
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r" *\n *", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _post_process(
    text: str,
    strip_output: bool,
    remove_blank_lines: bool,
    collapse_whitespace: bool,
) -> str:
    out = text
    if remove_blank_lines:
        out = _remove_empty_lines(out)
    if collapse_whitespace:
        out = re.sub(r"\s+", " ", out).strip()
    if strip_output:
        out = out.strip()
    return out


def _split_pair(value: str) -> Tuple[str, str]:
    for marker in ("=>", "||"):
        if marker in value:
            left, right = value.split(marker, 1)
            return left.strip(), right.strip()
    return value.strip(), ""


def _apply_operation(
    text: str,
    operation: str,
    marker_or_pattern: str,
    end_marker: str,
    items: str,
    replacement: str,
    occurrence: str,
    split_separator: str,
    custom_separator: str,
    split_index: int,
    join_matches_with: str,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
    include_markers: bool,
) -> str:
    op = _as_text(operation).strip()
    marker = _as_text(marker_or_pattern)
    end = _as_text(end_marker)
    patterns = _parse_items(items, marker)
    joiner = _join_separator(join_matches_with)

    if op == "pass_through":
        return text
    if op == "extract_after":
        return _extract_after(text, marker, occurrence, include_markers, match_case, whole_word, pattern_is_regex)
    if op == "extract_after_last":
        return _extract_after(text, marker, "last", include_markers, match_case, whole_word, pattern_is_regex)
    if op == "extract_before":
        return _extract_before(text, marker, occurrence, include_markers, match_case, whole_word, pattern_is_regex)
    if op == "extract_before_last":
        return _extract_before(text, marker, "last", include_markers, match_case, whole_word, pattern_is_regex)
    if op == "extract_between":
        return _extract_between(text, marker, end, occurrence, include_markers, match_case, whole_word, pattern_is_regex)
    if op == "remove_before":
        return _extract_after(text, marker, occurrence, include_markers, match_case, whole_word, pattern_is_regex)
    if op == "remove_after":
        return _extract_before(text, marker, occurrence, include_markers, match_case, whole_word, pattern_is_regex)
    if op == "remove_words":
        return _remove_items(text, patterns, match_case, True, pattern_is_regex)
    if op == "remove_phrases":
        return _remove_items(text, patterns, match_case, whole_word, pattern_is_regex)
    if op == "remove_lines_containing":
        return _filter_lines(text, patterns, False, match_case, whole_word, pattern_is_regex)
    if op == "keep_lines_containing":
        return _filter_lines(text, patterns, True, match_case, whole_word, pattern_is_regex)
    if op == "remove_sentences_containing":
        return _filter_sentences(text, patterns, False, match_case, whole_word, pattern_is_regex)
    if op == "keep_sentences_containing":
        return _filter_sentences(text, patterns, True, match_case, whole_word, pattern_is_regex)
    if op == "remove_paragraphs_containing":
        return _filter_paragraphs(text, patterns, False, match_case, whole_word, pattern_is_regex)
    if op == "keep_paragraphs_containing":
        return _filter_paragraphs(text, patterns, True, match_case, whole_word, pattern_is_regex)
    if op == "replace_text":
        if not marker:
            return text
        if pattern_is_regex:
            return _compile(marker, match_case).sub(_as_text(replacement), text)
        return _compile(_literal_pattern(marker, whole_word), match_case).sub(_as_text(replacement), text)
    if op == "regex_extract":
        return _regex_extract(text, marker, match_case, joiner)
    if op == "regex_remove":
        if not marker:
            return text
        return _compile(marker, match_case).sub("", text)
    if op == "regex_replace":
        if not marker:
            return text
        return _compile(marker, match_case).sub(_as_text(replacement), text)
    if op == "split_take":
        return _split_take(text, _split_separator(split_separator, custom_separator), split_index)
    if op == "dedupe_lines":
        return _dedupe_lines(text, match_case)
    if op == "sort_lines":
        return "\n".join(sorted(text.splitlines(), key=(lambda line: line if match_case else line.lower())))
    if op == "trim_each_line":
        return _trim_each_line(text)
    if op == "remove_empty_lines":
        return _remove_empty_lines(text)
    if op == "clean_whitespace":
        return _clean_whitespace(text)
    return text


def _apply_rule(
    text: str,
    rule: str,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
    include_markers: bool,
    join_matches_with: str,
) -> str:
    raw = rule.strip()
    if not raw or raw.startswith("#") or raw.startswith("//"):
        return text

    if ":" in raw:
        key, value = raw.split(":", 1)
        key = key.strip().lower().replace("-", "_").replace(" ", "_")
        value = value.strip()
    else:
        key = raw.strip().lower().replace("-", "_").replace(" ", "_")
        value = ""

    if key in ("after", "extract_after"):
        return _extract_after(text, value, "first", include_markers, match_case, whole_word, pattern_is_regex)
    if key in ("after_last", "extract_after_last"):
        return _extract_after(text, value, "last", include_markers, match_case, whole_word, pattern_is_regex)
    if key in ("before", "extract_before"):
        return _extract_before(text, value, "first", include_markers, match_case, whole_word, pattern_is_regex)
    if key in ("before_last", "extract_before_last"):
        return _extract_before(text, value, "last", include_markers, match_case, whole_word, pattern_is_regex)
    if key in ("between", "extract_between"):
        left, right = _split_pair(value)
        return _extract_between(text, left, right, "first", include_markers, match_case, whole_word, pattern_is_regex)
    if key in ("remove", "delete", "remove_phrase", "remove_phrases"):
        return _remove_items(text, _parse_items(value), match_case, whole_word, pattern_is_regex)
    if key in ("remove_word", "remove_words"):
        return _remove_items(text, _parse_items(value), match_case, True, pattern_is_regex)
    if key in ("remove_line", "remove_lines", "remove_lines_containing"):
        return _filter_lines(text, _parse_items(value), False, match_case, whole_word, pattern_is_regex)
    if key in ("keep_line", "keep_lines", "keep_lines_containing"):
        return _filter_lines(text, _parse_items(value), True, match_case, whole_word, pattern_is_regex)
    if key in ("remove_sentence", "remove_sentences", "remove_sentences_containing"):
        return _filter_sentences(text, _parse_items(value), False, match_case, whole_word, pattern_is_regex)
    if key in ("keep_sentence", "keep_sentences", "keep_sentences_containing"):
        return _filter_sentences(text, _parse_items(value), True, match_case, whole_word, pattern_is_regex)
    if key in ("remove_paragraph", "remove_paragraphs", "remove_paragraphs_containing"):
        return _filter_paragraphs(text, _parse_items(value), False, match_case, whole_word, pattern_is_regex)
    if key in ("keep_paragraph", "keep_paragraphs", "keep_paragraphs_containing"):
        return _filter_paragraphs(text, _parse_items(value), True, match_case, whole_word, pattern_is_regex)
    if key == "replace":
        left, right = _split_pair(value)
        if not left:
            return text
        return _compile(_literal_pattern(left, whole_word), match_case).sub(right, text)
    if key == "regex_extract":
        return _regex_extract(text, value, match_case, _join_separator(join_matches_with))
    if key == "regex_remove":
        if not value:
            return text
        return _compile(value, match_case).sub("", text)
    if key == "regex_replace":
        left, right = _split_pair(value)
        if not left:
            return text
        return _compile(left, match_case).sub(right, text)
    if key in ("strip", "trim"):
        return text.strip()
    if key in ("trim_lines", "trim_each_line"):
        return _trim_each_line(text)
    if key in ("remove_empty_lines", "no_empty_lines"):
        return _remove_empty_lines(text)
    if key in ("dedupe_lines", "unique_lines"):
        return _dedupe_lines(text, match_case)
    if key == "sort_lines":
        return "\n".join(sorted(text.splitlines(), key=(lambda line: line if match_case else line.lower())))
    if key in ("clean_whitespace", "collapse_spaces", "collapse_whitespace"):
        return _clean_whitespace(text)
    return text


def _apply_extra_rules(
    text: str,
    rules: str,
    match_case: bool,
    whole_word: bool,
    pattern_is_regex: bool,
    include_markers: bool,
    join_matches_with: str,
) -> str:
    out = text
    for rule in _as_text(rules).splitlines():
        out = _apply_rule(
            out,
            rule,
            match_case,
            whole_word,
            pattern_is_regex,
            include_markers,
            join_matches_with,
        )
    return out


class AntiMatterTextFilter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True}),
                "text": ("STRING", {"multiline": True, "default": ""}),
                "operation": (_OPERATIONS, {"default": "extract_after_last"}),
                "marker_or_pattern": (
                    "STRING",
                    {"multiline": False, "default": "Final video prompt:"},
                ),
                "end_marker": ("STRING", {"multiline": False, "default": ""}),
                "items": ("STRING", {"multiline": True, "default": ""}),
                "replacement": ("STRING", {"multiline": True, "default": ""}),
                "occurrence": (["first", "last"], {"default": "last"}),
                "split_separator": (_SPLIT_SEPARATORS, {"default": "newline"}),
                "custom_separator": ("STRING", {"multiline": False, "default": ""}),
                "split_index": ("INT", {"default": 1, "min": -100000, "max": 100000, "step": 1}),
                "join_matches_with": (_JOIN_SEPARATORS, {"default": "newline"}),
                "match_case": ("BOOLEAN", {"default": False}),
                "whole_word": ("BOOLEAN", {"default": False}),
                "pattern_is_regex": ("BOOLEAN", {"default": False}),
                "include_markers": ("BOOLEAN", {"default": False}),
                "strip_output": ("BOOLEAN", {"default": True}),
                "remove_empty_lines": ("BOOLEAN", {"default": False}),
                "collapse_whitespace": ("BOOLEAN", {"default": False}),
                "extra_rules": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "text_input": (any_type,),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "filter_text"
    CATEGORY = "AntiMatter/Text"

    def filter_text(
        self,
        enabled: bool,
        text: str,
        operation: str,
        marker_or_pattern: str,
        end_marker: str,
        items: str,
        replacement: str,
        occurrence: str,
        split_separator: str,
        custom_separator: str,
        split_index: int,
        join_matches_with: str,
        match_case: bool,
        whole_word: bool,
        pattern_is_regex: bool,
        include_markers: bool,
        strip_output: bool,
        remove_empty_lines: bool,
        collapse_whitespace: bool,
        extra_rules: str,
        text_input: Any = None,
    ):
        source = _as_text(text_input if text_input is not None else text)
        if not enabled:
            return {"ui": {"preview": (source,), "status": ("OFF",)}, "result": (source,)}

        out = _apply_operation(
            source,
            operation,
            marker_or_pattern,
            end_marker,
            items,
            replacement,
            occurrence,
            split_separator,
            custom_separator,
            split_index,
            join_matches_with,
            bool(match_case),
            bool(whole_word),
            bool(pattern_is_regex),
            bool(include_markers),
        )
        out = _apply_extra_rules(
            out,
            extra_rules,
            bool(match_case),
            bool(whole_word),
            bool(pattern_is_regex),
            bool(include_markers),
            join_matches_with,
        )
        out = _post_process(out, bool(strip_output), bool(remove_empty_lines), bool(collapse_whitespace))

        status = f"{operation}: {len(source)} -> {len(out)} chars"
        return {"ui": {"preview": (out,), "status": (status,)}, "result": (out,)}


NODE_CLASS_MAPPINGS = {
    "AntiMatter_TextFilter": AntiMatterTextFilter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AntiMatter_TextFilter": "AntiMatter Text Filter",
}
