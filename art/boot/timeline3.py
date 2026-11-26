# Timing for the K.OS startup video (seconds). Shared by picture and sound.
# Set KOS_LONG=1 for the 10 second version (longer opening hold so the
# console finishes loading behind it, longer shots, more recording blinks).
import os

FPS = 60

if os.environ.get("KOS_LONG") == "1":
    DUR = 10.0
    T = {
        "streak": 1.10,   # calm hold on the boot logo first
        "c1": 1.60,
        "c2": 2.10,
        "c3": 2.60,
        "op": 3.10,
        "eye": 4.20,
        "rush": 5.00,
        "gap": 5.12,
        "K": 5.20,
        "dot": 5.70,
        "roll": 6.70,
        "fade": 8.60,
    }
    # signal locking on at the very start: glitch windows, then the logo locks
    BOOT = [(0.05, 0.09), (0.13, 0.16), (0.21, 0.31), (0.36, 0.39), (0.45, 0.56), (0.60, 0.66)]
    LOCK = 0.70
else:
    DUR = 7.0
    T = {
        "streak": 0.40,
        "c1": 0.80,
        "c2": 1.20,
        "c3": 1.60,
        "op": 2.00,
        "eye": 2.80,
        "rush": 3.40,
        "gap": 3.52,
        "K": 3.60,
        "dot": 4.00,
        "roll": 5.00,
        "fade": 6.00,
    }
    BOOT = []
    LOCK = 0.0
