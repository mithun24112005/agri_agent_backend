"""
Image quality and preliminary plant suitability screening heuristics.
NOTE: These checks provide fast client/server image pre-filtering and blur detection.
Per design specification, they are documented as heuristic filters, NOT certified plant detectors.
"""
from pathlib import Path
from typing import Tuple, Dict, Any, Union
import numpy as np
from PIL import Image

def analyze_image_quality(image_input: Union[str, Path, bytes, Image.Image]) -> Dict[str, Any]:
    """
    Performs preliminary image-quality inspection:
    - Minimum brightness / overexposure check
    - Sharpness / variance heuristic (simplified gradient energy)
    - Basic color distribution check (Excess Green Index: 2G - R - B)
    """
    if isinstance(image_input, (str, Path)):
        img = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, bytes):
        import io
        img = Image.open(io.BytesIO(image_input)).convert("RGB")
    elif isinstance(image_input, Image.Image):
        img = image_input.convert("RGB")
    else:
        raise ValueError(f"Unsupported image input type: {type(image_input)}")

    # Resize to standard thumbnail for fast numerical analysis
    thumb = img.resize((128, 128))
    arr = np.array(thumb, dtype=np.float32)

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    # Mean brightness
    mean_brightness = float(np.mean(arr))
    
    # Very dark / completely black image check
    is_too_dark = mean_brightness < 20.0
    # Overexposed / pure white image check
    is_too_bright = mean_brightness > 245.0

    # Simplified sharpness / Laplacian gradient approximation
    # High variance of neighbor differences indicates sharp edges; near-zero indicates solid color or extreme blur
    dx = np.diff(arr, axis=1)
    dy = np.diff(arr, axis=0)
    gradient_energy = float(np.var(dx) + np.var(dy))
    is_blurry = gradient_energy < 40.0

    # Excess Green Index (ExG = 2*G - R - B)
    exg = 2.0 * g - r - b
    mean_exg = float(np.mean(exg))
    
    # Vegetation/foliage heuristic: leaves typically exhibit positive Excess Green Index
    has_vegetative_color = mean_exg > -10.0

    warnings = []
    if is_too_dark:
        warnings.append("Image appears underexposed or very dark. Consider taking a photo in better lighting.")
    if is_too_bright:
        warnings.append("Image appears washed out or overexposed. Glare may reduce diagnosis accuracy.")
    if is_blurry:
        warnings.append("Image may be blurry or out of focus. Clear focus on the leaf lesion is recommended.")

    return {
        "mean_brightness": round(mean_brightness, 2),
        "gradient_energy": round(gradient_energy, 2),
        "mean_exg": round(mean_exg, 2),
        "is_too_dark": is_too_dark,
        "is_too_bright": is_too_bright,
        "is_blurry": is_blurry,
        "has_vegetative_color": has_vegetative_color,
        "quality_warnings": warnings,
        "is_usable": not (is_too_dark or is_too_bright)
    }

