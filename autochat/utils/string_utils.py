import ast
import json
import re
from collections.abc import Callable
from typing import Any
from wave import Error

import jellyfish


def check_no_accent_vn_char(char: str) -> bool:
    if char in "àáạảãâầấậẩẫăằắặẳẵ":
        return False
    if char in "ÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪ":
        return False
    if char in "èéẹẻẽêềếệểễ":
        return False
    if char in "ÈÉẸẺẼÊỀẾỆỂỄ":
        return False
    if char in "òóọỏõôồốộổỗơờớợởỡ":
        return False
    if char in "ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ":
        return False
    if char in "ìíịỉĩ":
        return False
    if char in "ÌÍỊỈĨ":
        return False
    if char in "ùúụủũưừứựửữ":
        return False
    if char in "ƯỪỨỰỬỮÙÚỤỦŨ":
        return False
    if char in "ỳýỵỷỹ":
        return False
    if char in "ỲÝỴỶỸ":
        return False
    if char in "Đ":
        return False
    if char in "đ":
        return False
    return True


def no_accent_vietnamese(s: str) -> str:
    s = re.sub("[àáạảãâầấậẩẫăằắặẳẵ]", "a", s)
    s = re.sub("[ÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪ]", "A", s)
    s = re.sub("[èéẹẻẽêềếệểễ]", "e", s)
    s = re.sub("[ÈÉẸẺẼÊỀẾỆỂỄ]", "E", s)
    s = re.sub("[òóọỏõôồốộổỗơờớợởỡ]", "o", s)
    s = re.sub("[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]", "O", s)
    s = re.sub("[ìíịỉĩ]", "i", s)
    s = re.sub("[ÌÍỊỈĨ]", "I", s)
    s = re.sub("[ùúụủũưừứựửữ]", "u", s)
    s = re.sub("[ƯỪỨỰỬỮÙÚỤỦŨ]", "U", s)
    s = re.sub("[ỳýỵỷỹ]", "y", s)
    s = re.sub("[ỲÝỴỶỸ]", "Y", s)
    s = re.sub("Đ", "D", s)
    s = re.sub("đ", "d", s)
    return s


def get_no_accent_vn_char(char: str) -> str:
    if char in "àáạảãâầấậẩẫăằắặẳẵ":
        return "a"
    if char in "ÀÁẠẢÃĂẰẮẶẲẴÂẦẤẬẨẪ":
        return "A"
    if char in "èéẹẻẽêềếệểễ":
        return "e"
    if char in "ÈÉẸẺẼÊỀẾỆỂỄ":
        return "E"
    if char in "òóọỏõôồốộổỗơờớợởỡ":
        return "o"
    if char in "ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ":
        return "O"
    if char in "ìíịỉĩ":
        return "i"
    if char in "ÌÍỊỈĨ":
        return "I"
    if char in "ùúụủũưừứựửữ":
        return "u"
    if char in "ƯỪỨỰỬỮÙÚỤỦŨ":
        return "U"
    if char in "ỳýỵỷỹ":
        return "y"
    if char in "ỲÝỴỶỸ":
        return "Y"
    if char in "Đ":
        return "D"
    if char in "đ":
        return "d"
    return char


def jaccard_similarity(text_a: str, text_b: str) -> float:
    s1 = set(text_a)
    s2 = set(text_b)
    return len(s1.intersection(s2)) / len(s1.union(s2))


def vn_jaro_score(s1: str, s2: str, no_accent_ratio: float = 0.3) -> float:
    raw_score: float = jellyfish.jaro_similarity(s1, s2)
    no_accent_score: float = jellyfish.jaro_similarity(no_accent_vietnamese(s1), no_accent_vietnamese(s2))
    score = (1 - no_accent_ratio) * raw_score + no_accent_ratio * no_accent_score
    return score


def find_sub_string_similarity(
        string: str,
        sub_string: str,
        similarity: Callable[[Any, Any], Any],
        threshold: float = 0.93,
        jaccard_score_thresh: float = 0.6
) -> list[tuple[str, tuple[int, int], float]]:
    len_sub_string = len(sub_string.split(" "))
    matches = []
    length = len(string)
    for i in range(length):
        if i == 0 or string[i] in [" ", "", "\n"]:
            _sub_string_list = string[i:].strip(" ").split(" ")[: len_sub_string]
            _sub_string = " ".join(_sub_string_list)
            if _sub_string == sub_string:
                matches.append((_sub_string, (i, i + len(_sub_string)), 1.0))

            jaccard_score = jaccard_similarity(sub_string, _sub_string)
            if jaccard_score < jaccard_score_thresh:
                continue

            score = similarity(sub_string, _sub_string)
            if score >= threshold:
                matches.append((_sub_string, (i, i + len(_sub_string)), score))
    return matches


def parser_string_to_json(text: str):  # type: ignore
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return ast.literal_eval(text)
    except Error:
        return {}


def extract_json_from_markdown(text: str) -> str:
    pattern = re.compile(r"```json(.*?)```", re.DOTALL)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    else:
        return text
