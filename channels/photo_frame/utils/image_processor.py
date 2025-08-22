from PIL import Image, ImageOps
from pathlib import Path

class ImageProcessor:
    def __init__(self, upload_dir: Path, thumb_dir: Path):
        self.upload_dir = upload_dir
        self.thumb_dir = thumb_dir

    async def save_upload(self, upload_file):
        # Save uploaded image and return metadata
        filename = upload_file.filename
        dest_path = self.upload_dir / filename
        with open(dest_path, 'wb') as f:
            f.write(await upload_file.read())
        with Image.open(dest_path) as img:
            width, height = img.size
        return {
            "filename": filename,
            "original_name": filename,
            "width": width,
            "height": height
        }

    async def render_with_crop(self, source_path, output_path, resolution, crop_x, crop_y, crop_width, crop_height):
        with Image.open(source_path) as img:
            w, h = img.size
            left = int(w * crop_x / 100)
            top = int(h * crop_y / 100)
            right = int(w * (crop_x + crop_width) / 100)
            bottom = int(h * (crop_y + crop_height) / 100)
            cropped = img.crop((left, top, right, bottom))
            resized = cropped.resize(resolution, Image.LANCZOS)
            resized.save(output_path)

    async def render_letterbox(self, source_path, output_path, resolution):
        with Image.open(source_path) as img:
            thumb = ImageOps.pad(img, resolution, color="black")
            thumb.save(output_path)

    async def render_stretch(self, source_path, output_path, resolution):
        with Image.open(source_path) as img:
            stretched = img.resize(resolution, Image.LANCZOS)
            stretched.save(output_path)
