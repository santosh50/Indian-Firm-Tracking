"""
Minimal pipeline: isolate black text -> OCR -> print candidate variants
accounting for commonly confused characters.

No command-line arguments — edit the settings below and run:
    python ocr_candidates.py

Requirements:
    pip install opencv-python numpy pillow pytesseract --break-system-packages
    + tesseract binary: apt install tesseract-ocr / brew install tesseract
"""

import itertools
import numpy as np
import cv2
import pytesseract
from PIL import Image

# ---- Edit these ----
INPUT_PATH = "captcha2.png"
OUTPUT_PATH = "output.png"
TOLERANCE = 100
DILATE_ITER = 0
# ---------------------

CONFUSION_MAP = {
    'o': ['0'], '0': ['o', 'O'], 'O': ['0'],
    's': ['5', 'S'], '5': ['s', 'S'], 'S': ['5', 's'],
    'q': ['g'], 'g': ['q'],
    'l': ['1', 'I'], '1': ['l', 'I'], 'I': ['1', 'l'],
    'z': ['2'], '2': ['z'],
    'b': ['6'], '6': ['b'],
}


def isolate_black_text(input_path, output_path, tolerance, dilate_iter):
    img = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image at: {input_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = (gray <= tolerance).astype(np.uint8) * 255

    if dilate_iter > 0:
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=dilate_iter)

    cleaned = 255 - mask
    cv2.imwrite(output_path, cleaned)
    return cleaned


def run_ocr(cleaned_img):
    whitelist = ('abcdefghijklmnopqrstuvwxyz'
                 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                 '0123456789')
    config = f'--psm 7 -c tessedit_char_whitelist={whitelist}'
    raw_text = pytesseract.image_to_string(Image.fromarray(cleaned_img), config=config).strip()
    return ''.join(ch for ch in raw_text if ch.isalnum())


def generate_candidates(text, max_candidates=200):
    positions_options = [[ch] + CONFUSION_MAP.get(ch, []) for ch in text]
    candidates = []
    for combo in itertools.product(*positions_options):
        candidates.append(''.join(combo))
        if len(candidates) >= max_candidates:
            break
    if text in candidates:
        candidates.remove(text)
    candidates.insert(0, text)  # original OCR guess first
    return candidates


cleaned = isolate_black_text(INPUT_PATH, OUTPUT_PATH, TOLERANCE, DILATE_ITER)
ocr_text = run_ocr(cleaned)
candidates = generate_candidates(ocr_text)

print(f"OCR result: '{ocr_text}'")
print(f"\n{len(candidates)} candidate(s):")
for c in candidates:
    print(c)
