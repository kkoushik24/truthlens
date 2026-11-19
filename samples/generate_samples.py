"""Generate sample test images for image forensics testing."""

from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ExifTags

samples_dir = Path(__file__).resolve().parent
samples_dir.mkdir(parents=True, exist_ok=True)

# 1. Clean photo simulation (smooth gradient + standard EXIF)
clean_img = Image.new("RGB", (320, 240), color=(135, 206, 235))
draw = ImageDraw.Draw(clean_img)
draw.rectangle([40, 100, 280, 220], fill=(34, 139, 34))
draw.ellipse([200, 30, 260, 90], fill=(255, 223, 0))

# Attach realistic EXIF using Pillow native Image.Exif
clean_exif = clean_img.getexif()
clean_exif[0x010F] = "Canon"  # Make
clean_exif[0x0110] = "Canon EOS 80D"  # Model
clean_exif[0x0132] = "2024:05:12 14:32:00"  # DateTime
clean_path = samples_dir / "clean_photo.jpg"
clean_img.save(clean_path, "JPEG", quality=95, exif=clean_exif)

# 2. Stripped photo (no EXIF at all)
stripped_path = samples_dir / "stripped_photo.jpg"
clean_img.save(stripped_path, "JPEG", quality=85)

# 3. Edited / spliced photo: save base at low quality, paste a high-contrast square, add Photoshop EXIF
base_buffer = Image.new("RGB", (320, 240), color=(100, 100, 100))
draw_base = ImageDraw.Draw(base_buffer)
draw_base.rectangle([0, 0, 320, 120], fill=(70, 130, 180))
# Re-save base at Q=60
base_temp = samples_dir / "temp_base.jpg"
base_buffer.save(base_temp, "JPEG", quality=60)

reopened_base = Image.open(base_temp)
# Paste a high-frequency noisy patch in top-right corner [200, 20, 300, 100]
np.random.seed(42)
noise_arr = np.random.randint(0, 255, (80, 100, 3), dtype=np.uint8)
noise_patch = Image.fromarray(noise_arr)
reopened_base.paste(noise_patch, (200, 20))

# Add Photoshop tag to EXIF
edited_exif = reopened_base.getexif()
edited_exif[0x0131] = "Adobe Photoshop 2024"  # Software
edited_exif[0x0132] = "2026:01:01 10:00:00"  # DateTime
edited_path = samples_dir / "edited_photo.jpg"
reopened_base.save(edited_path, "JPEG", quality=95, exif=edited_exif)

if base_temp.exists():
    base_temp.unlink()

print("Sample images successfully generated in samples/ directory.")

