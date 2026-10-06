"""
SUTRA — Image Normalisation Utility
====================================
Centralised, reusable image-processing pipeline used by ProductImage and
Category models.  Every uploaded image is automatically:

  1. Validated (format, minimum dimensions, file size)
  2. EXIF-orientation corrected (portrait DSLR images no longer appear rotated)
  3. White/transparent padding trimmed so the actual subject fills the frame
  4. Smart-cropped to a fixed 4:5 aspect ratio (800 × 1000 px) using
     centre-crop — the standard used by Myntra, Flipkart, and Amazon Fashion
  5. Converted to RGB JPEG (with transparency → white canvas for PNG inputs)
  6. Compressed at quality=88 with progressive encoding and chroma subsampling
     optimised for web delivery

No external libraries beyond Pillow are required.
"""

import io
import os
import logging
from PIL import Image, ImageOps, ExifTags

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

# Target canvas for product images — 4:5 ratio, professional e-commerce standard
PRODUCT_TARGET_WIDTH = 800
PRODUCT_TARGET_HEIGHT = 1000

# Target canvas for category banner images — 1:1 square
CATEGORY_TARGET_WIDTH = 600
CATEGORY_TARGET_HEIGHT = 600

# JPEG quality (88 balances quality vs file size; 85-90 is industry standard)
JPEG_QUALITY = 88

# Minimum acceptable dimensions for any upload (guards against broken/unusable files)
MIN_WIDTH = 100
MIN_HEIGHT = 100

# Maximum file size accepted before processing (50 MB — covers RAW-converted JPEGs)
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

# Allowed input formats
ALLOWED_FORMATS = {'JPEG', 'JPG', 'PNG', 'WEBP', 'BMP', 'TIFF', 'GIF'}

# Trim sensitivity: pixels within this brightness of pure-white (255) are treated
# as empty padding.  Increase to trim off-white backgrounds; lower for products
# with very light colours.
TRIM_THRESHOLD = 240


# ── Public API ─────────────────────────────────────────────────────────────────

def normalise_product_image(upload_file) -> io.BytesIO:
    """
    Process a raw upload for a ProductImage field.
    Returns a BytesIO containing the final JPEG bytes.
    Raises ValueError with a user-friendly message on invalid input.
    """
    return _normalise(upload_file, PRODUCT_TARGET_WIDTH, PRODUCT_TARGET_HEIGHT)


def normalise_category_image(upload_file) -> io.BytesIO:
    """
    Process a raw upload for a Category image field.
    Returns a BytesIO containing the final JPEG bytes.
    Raises ValueError with a user-friendly message on invalid input.
    """
    return _normalise(upload_file, CATEGORY_TARGET_WIDTH, CATEGORY_TARGET_HEIGHT)


# ── Internal pipeline ──────────────────────────────────────────────────────────

def _normalise(upload_file, target_w: int, target_h: int) -> io.BytesIO:
    """
    Full normalisation pipeline:
      open → validate → fix EXIF → trim padding → smart-crop → resize → save
    """
    # ── Step 1: Open and validate ──────────────────────────────────────────────
    img = _open_and_validate(upload_file)

    # ── Step 2: Apply EXIF orientation (fix rotated DSLR/mobile photos) ────────
    img = _apply_exif_orientation(img)

    # ── Step 3: Flatten transparency onto a white canvas ────────────────────────
    img = _flatten_transparency(img)

    # ── Step 4: Trim excessive white / empty margins ────────────────────────────
    img = _trim_padding(img)

    # ── Step 5: Centre-crop to target aspect ratio ──────────────────────────────
    img = _centre_crop_to_ratio(img, target_w, target_h)

    # ── Step 6: Resize to exact canvas dimensions ───────────────────────────────
    img = img.resize((target_w, target_h), Image.LANCZOS)

    # ── Step 7: Ensure RGB for JPEG output ──────────────────────────────────────
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # ── Step 8: Save as optimised progressive JPEG ──────────────────────────────
    output = io.BytesIO()
    img.save(
        output,
        format='JPEG',
        quality=JPEG_QUALITY,
        optimize=True,
        progressive=True,
        subsampling=2,   # 4:2:0 chroma subsampling — standard for web images
    )
    output.seek(0)
    return output


def _open_and_validate(upload_file) -> Image.Image:
    """Open the upload and run basic sanity checks."""
    # Guard against oversized uploads consuming too much memory
    upload_file.seek(0, 2)          # seek to end
    file_size = upload_file.tell()
    upload_file.seek(0)             # rewind

    if file_size > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Image file is too large ({file_size // (1024*1024)} MB). "
            f"Maximum allowed size is {MAX_UPLOAD_BYTES // (1024*1024)} MB."
        )

    try:
        img = Image.open(upload_file)
        img.verify()                # detect truncated/corrupt files early
    except Exception as exc:
        raise ValueError(f"Invalid or corrupt image file: {exc}") from exc

    # Re-open after verify() (verify() leaves the file in an unknown state)
    upload_file.seek(0)
    img = Image.open(upload_file)

    # Format check
    fmt = (img.format or '').upper()
    if fmt not in ALLOWED_FORMATS:
        raise ValueError(
            f"Unsupported image format '{fmt}'. "
            f"Accepted formats: {', '.join(sorted(ALLOWED_FORMATS))}."
        )

    # Minimum dimension check
    w, h = img.size
    if w < MIN_WIDTH or h < MIN_HEIGHT:
        raise ValueError(
            f"Image is too small ({w}×{h} px). "
            f"Minimum accepted size is {MIN_WIDTH}×{MIN_HEIGHT} px."
        )

    return img


def _apply_exif_orientation(img: Image.Image) -> Image.Image:
    """
    Rotate/flip the image to honour EXIF orientation metadata.
    This fixes the common problem where mobile and DSLR photos appear
    rotated or mirrored when opened on other devices.
    """
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        # If EXIF data is malformed, continue without correction
        pass
    return img


def _flatten_transparency(img: Image.Image) -> Image.Image:
    """
    Composite RGBA/PA images onto a solid white canvas.
    This prevents black or grey backgrounds appearing on transparent PNGs
    when saved as JPEG.
    """
    if img.mode in ('RGBA', 'LA', 'PA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'PA':
            img = img.convert('RGBA')
        # Use the alpha channel as the compositing mask
        background.paste(img, mask=img.split()[-1])
        return background
    return img


def _trim_padding(img: Image.Image) -> Image.Image:
    """
    Remove excessive white or transparent borders that appear when product
    photos are taken against a white background or include excess canvas.

    Uses a greyscale threshold approach:
      - Convert to greyscale
      - Find the bounding box of pixels darker than TRIM_THRESHOLD
      - Crop to that bounding box with a small safety margin

    If the image is already well-framed (no significant padding), the crop
    will be minimal and the original proportions are preserved.
    """
    # Work in greyscale for the threshold check
    grey = img.convert('L')
    w, h = img.size

    # Build the bounding box of "non-background" pixels
    pixels = grey.load()
    min_x, min_y = w, h
    max_x, max_y = 0, 0

    for y in range(h):
        for x in range(w):
            if pixels[x, y] < TRIM_THRESHOLD:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y

    # If the entire image is "background" (fully white/transparent), skip trim
    if max_x <= min_x or max_y <= min_y:
        return img

    # Add a small proportional margin so the subject isn't flush to the edge
    margin_x = max(int((max_x - min_x) * 0.04), 4)
    margin_y = max(int((max_y - min_y) * 0.04), 4)

    crop_box = (
        max(0, min_x - margin_x),
        max(0, min_y - margin_y),
        min(w, max_x + margin_x),
        min(h, max_y + margin_y),
    )

    # Only crop if we're actually removing something meaningful (>5% of dimension)
    left_removed = crop_box[0]
    top_removed = crop_box[1]
    right_removed = w - crop_box[2]
    bottom_removed = h - crop_box[3]

    significant_trim = (
        left_removed > w * 0.05 or right_removed > w * 0.05 or
        top_removed > h * 0.05 or bottom_removed > h * 0.05
    )

    if significant_trim:
        img = img.crop(crop_box)

    return img


def _centre_crop_to_ratio(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Crop the image to the exact target aspect ratio using a centre-crop
    strategy.  This means:
      - Portrait images: may lose a little off the top/bottom
      - Landscape images: loses the sides
      - Square images: loses a little off the top/bottom

    Centre-crop is the industry standard for e-commerce product imagery
    because it keeps the subject centred and eliminates distortion.
    """
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        # Image is wider than target — crop horizontally
        new_w = int(src_h * target_ratio)
        offset_x = (src_w - new_w) // 2
        img = img.crop((offset_x, 0, offset_x + new_w, src_h))
    elif src_ratio < target_ratio:
        # Image is taller than target — crop vertically
        new_h = int(src_w / target_ratio)
        offset_y = (src_h - new_h) // 2
        img = img.crop((0, offset_y, src_w, offset_y + new_h))
    # If ratios match exactly, no crop needed

    return img


def delete_image_file(image_field) -> None:
    """
    Delete the physical file referenced by a Django ImageField.
    Call this before replacing or deleting a ProductImage instance
    to prevent orphaned files accumulating in the media directory.

    Usage:
        delete_image_file(product_image_instance.image)
    """
    if not image_field:
        return
    try:
        path = image_field.path
        if path and os.path.isfile(path):
            os.remove(path)
            logger.debug("Deleted image file: %s", path)
    except Exception as exc:
        # Log but never raise — a missing file should not block a save/delete
        logger.warning("Could not delete image file '%s': %s", image_field.name, exc)
