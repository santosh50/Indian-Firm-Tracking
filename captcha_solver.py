import itertools
import numpy as np
import cv2
import pytesseract
from PIL import Image

TOLERANCE = 100
MAX_EDIT_DISTANCE = 1

CONFUSION_MAP = {
    '0': ['o', 'O'], 'o': ['0', 'O'], 'O': ['0', 'o'],
    '5': ['s'], 's': ['5', 'S'], 'S': ['5', 's'],
    '1': ['l', 'I'], 'l': ['1', 'I'], 'I': ['1', 'l'],
    '2': ['z'], 'z': ['Z', '2'], 'Z': ['z'],
    '6': ['b'], 'b': ['6'],
 
    'i': ['l'], 'g': ['q'], 'q': ['g'],
 
    'c': ['C'], 'C': ['c'],
    'p': ['P'], 'P': ['p'],
    'u': ['U'], 'U': ['u'],
    'v': ['V'], 'V': ['v'],
    'w': ['W'], 'W': ['w'],
    'x': ['X'], 'X': ['x'],
}

def _isolate_black_text(image_path, tolerance=TOLERANCE):
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image at: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = (gray <= tolerance).astype(np.uint8) * 255

    return 255 - mask  # black text on white background


def _run_ocr(cleaned_img):
    whitelist = ('abcdefghijklmnopqrstuvwxyz'
                 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                 '0123456789')
    config = f'--psm 7 -c tessedit_char_whitelist={whitelist}'
    raw_text = pytesseract.image_to_string(Image.fromarray(cleaned_img), config=config).strip()
    return ''.join(ch for ch in raw_text if ch.isalnum())


def _generate_candidates(text, max_candidates=200):
    positions_options = [[ch] + CONFUSION_MAP.get(ch, []) for ch in text]
    candidates = []
    for combo in itertools.product(*positions_options):
        candidates.append(''.join(combo))
        if len(candidates) >= max_candidates:
            break
    if text in candidates:
        candidates.remove(text)
    candidates.insert(0, text)
    return candidates


def _rank_and_filter(candidates, original):
    def num_diffs(candidate):
        return sum(1 for a, b in zip(candidate, original) if a != b)

    filtered = [c for c in candidates if num_diffs(c) <= MAX_EDIT_DISTANCE]
    return sorted(filtered, key=num_diffs)


def solve_captcha(image_path):
    cleaned = _isolate_black_text(image_path)
    ocr_text = _run_ocr(cleaned)
    candidates = _generate_candidates(ocr_text)
    ranked = _rank_and_filter(candidates, ocr_text)
    return ranked


if __name__ == '__main__':
    # Quick manual test
    result = solve_captcha("captcha5.png")
    print(f"{len(result)} candidate(s):")
    print(*result)
