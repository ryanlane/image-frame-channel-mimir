from PIL import Image, ImageOps
from pathlib import Path
from typing import Tuple, Dict, Any

class ImageProcessor:
    def __init__(self, upload_dir: Path, thumb_dir: Path = None):
        self.upload_dir = upload_dir
        # thumb_dir is now unused, thumbnails go next to images
        # Keeping parameter for backward compatibility
        
    def _get_thumbnail_path(self, image_filename: str) -> Path:
        """Get the path where the thumbnail should be stored"""
        base_name = Path(image_filename).stem
        return self.upload_dir / f"{base_name}.thumb.jpg"

    async def save_upload(self, upload_file):
        # Save uploaded image and return metadata
        filename = upload_file.filename
        dest_path = self.upload_dir / filename
        thumb_path = self._get_thumbnail_path(filename)
        
        # Save original file
        with open(dest_path, 'wb') as f:
            f.write(await upload_file.read())
        
        # Open image to get dimensions and create thumbnail
        with Image.open(dest_path) as img:
            width, height = img.size
            
            # Create thumbnail (600x600 max, maintaining aspect ratio)
            thumbnail = img.copy()
            thumbnail.thumbnail((600, 600), Image.LANCZOS)
            
            # Convert to RGB if needed (for PNG with transparency)
            if thumbnail.mode in ('RGBA', 'LA', 'P'):
                thumbnail = thumbnail.convert('RGB')
            
            # Save thumbnail as JPEG next to the original image
            thumbnail.save(thumb_path, "JPEG", quality=85)
        
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

    # --- New API expected by RenderingService ---------------------------------
    async def process_smart_crop(
        self,
        source_path: Path,
        output_path: Path,
        resolution: Tuple[int, int],
        image_record: Dict[str, Any],
    ) -> None:
        """Crop to fill the target aspect ratio then resize.

        Strategy:
        1. If the image has explicit crop metadata (percent fields), apply that window first.
        2. Otherwise compute a centered crop matching the target aspect ratio (like CSS object-fit: cover).
        3. Resize to the requested resolution using high quality filter.
        """
        width_target, height_target = resolution
        target_aspect = width_target / height_target if height_target else 1.0

        with Image.open(source_path) as img:
            # Step 1: explicit crop metadata (% based) if present
            crop_keys = ["crop_x", "crop_y", "crop_width", "crop_height"]
            if all(k in image_record for k in crop_keys):
                try:
                    w, h = img.size
                    cx = float(image_record.get("crop_x", 0))
                    cy = float(image_record.get("crop_y", 0))
                    cw = float(image_record.get("crop_width", 100))
                    ch = float(image_record.get("crop_height", 100))
                    left = int(w * cx / 100)
                    top = int(h * cy / 100)
                    right = int(w * (cx + cw) / 100)
                    bottom = int(h * (cy + ch) / 100)
                    img = img.crop((left, top, right, bottom))
                except Exception:
                    # Fail soft and continue with original image
                    pass

            # Step 2: center crop to aspect ratio if needed
            w, h = img.size
            current_aspect = w / h if h else target_aspect
            if abs(current_aspect - target_aspect) > 0.0001:
                if current_aspect > target_aspect:
                    # Image is wider than target -> crop width
                    new_w = int(h * target_aspect)
                    offset = (w - new_w) // 2
                    img = img.crop((offset, 0, offset + new_w, h))
                else:
                    # Image is taller than target -> crop height
                    new_h = int(w / target_aspect)
                    offset = (h - new_h) // 2
                    img = img.crop((0, offset, w, offset + new_h))

            # Step 3: resize
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img = img.resize((width_target, height_target), Image.LANCZOS)
            img.save(output_path, "JPEG", quality=90)

    async def process_letterbox(
        self,
        source_path: Path,
        output_path: Path,
        resolution: Tuple[int, int],
    ) -> None:
        """Pad image with black bars to fit exact resolution."""
        await self.render_letterbox(source_path, output_path, resolution)

    async def process_stretch(
        self,
        source_path: Path,
        output_path: Path,
        resolution: Tuple[int, int],
    ) -> None:
        """Stretch (distort) image to fit resolution."""
        await self.render_stretch(source_path, output_path, resolution)

    async def create_solid_color_image(
        self,
        output_path: Path,
        resolution: Tuple[int, int],
        color: Tuple[int, int, int] = (128, 128, 128),
    ) -> None:
        """Create a solid color placeholder image."""
        img = Image.new("RGB", resolution, color)
        img.save(output_path, "JPEG", quality=85)
