from PIL import Image, ImageOps
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

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
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            tgt_w, tgt_h = resolution
            w, h = img.size
            ratio = min(tgt_w / max(1, w), tgt_h / max(1, h))
            new_w = max(1, int(round(w * ratio)))
            new_h = max(1, int(round(h * ratio)))
            resized = img.resize((new_w, new_h), Image.LANCZOS)
            bg = Image.new("RGB", (tgt_w, tgt_h), (0, 0, 0))
            off_x = (tgt_w - new_w) // 2
            off_y = (tgt_h - new_h) // 2
            bg.paste(resized, (off_x, off_y))
            bg.save(output_path, "JPEG", quality=90)

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

    # --- New OpenCV-based saliency crop --------------------------------------
    async def process_opencv_saliency(
        self,
        source_path: Path,
        output_path: Path,
        resolution: Tuple[int, int],
        image_record: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Smart crop using a simple OpenCV saliency map + integral-image scan.

        Strategy (fast and dependency-tolerant):
        - Load with PIL to respect EXIF orientation, convert to numpy (RGB).
        - Build saliency as a weighted combination of Laplacian magnitude and local variance.
        - Perform a 1D sliding-window scan that preserves the target aspect ratio while
          covering the image (like object-fit: cover), maximizing saliency sum.
        - Crop and resize to the requested resolution.

        Fallback: If OpenCV/Numpy are not available, falls back to process_smart_crop.
        """
        try:
            import numpy as np  # type: ignore
            import cv2  # type: ignore
        except Exception:
            # Graceful fallback to existing smart-crop
            await self.process_smart_crop(source_path, output_path, resolution, image_record)
            return

        settings = settings or {}

        # Load with PIL, transpose to honor EXIF, convert to RGB
        with Image.open(source_path) as pil_img:
            try:
                pil_img = ImageOps.exif_transpose(pil_img)
            except Exception:
                pass
            if pil_img.mode not in ("RGB", "L"):
                pil_img = pil_img.convert("RGB")
            w, h = pil_img.size
            # If extremely small or degenerate, fallback
            if w < 4 or h < 4:
                await self.process_smart_crop(source_path, output_path, resolution, image_record)
                return
            np_img = np.array(pil_img)

        # Convert to BGR/GRAY for OpenCV processing
        if np_img.ndim == 2:
            gray = np_img.astype("uint8")
        else:
            bgr = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # Build saliency map: Laplacian magnitude + local variance
        gray_f = gray.astype("float32")
        # Laplacian magnitude
        lap = cv2.Laplacian(gray_f, cv2.CV_32F, ksize=3)
        lap = cv2.GaussianBlur(cv2.absdiff(lap, 0), (0, 0), 1.0)
        # Local variance via mean and mean of squares
        k = int(max(5, round(min(w, h) / 50)))  # kernel adapts to image size
        if k % 2 == 0:
            k += 1
        mean = cv2.GaussianBlur(gray_f, (k, k), 0)
        mean_sq = cv2.GaussianBlur(gray_f * gray_f, (k, k), 0)
        var = cv2.max(mean_sq - mean * mean, 0)

        # Normalize to 0..1 and combine
        def norm01(x: "np.ndarray") -> "np.ndarray":
            mn, mx = float(x.min()), float(x.max())
            if mx - mn < 1e-6:
                return np.zeros_like(x, dtype="float32")
            return (x - mn) / (mx - mn)

        lap_n = norm01(lap)
        var_n = norm01(var)
        sal = 0.6 * lap_n + 0.4 * var_n

        # Optional: small blur to smooth noise
        sal = cv2.GaussianBlur(sal, (0, 0), sigmaX=1.0)

        tgt_w, tgt_h = resolution
        target_aspect = (tgt_w / tgt_h) if tgt_h else (w / max(h, 1))
        img_aspect = (w / h) if h else target_aspect

        # Choose cover-style window dimensions; slide along the other axis
        if img_aspect > target_aspect:
            # Image wider than target: use full height, slide horizontally
            win_h = h
            win_w = int(round(h * target_aspect))
            slide_axis = "x"
            steps = max(1, int(np.clip(round(w / 200), 1, 50)))
            step = max(1, int(round((w - win_w) / max(1, steps))))
        else:
            # Image taller than target: use full width, slide vertically
            win_w = w
            win_h = int(round(w / target_aspect))
            slide_axis = "y"
            steps = max(1, int(np.clip(round(h / 200), 1, 50)))
            step = max(1, int(round((h - win_h) / max(1, steps))))

        # Integral image for O(1) window sums
        sal32 = sal.astype("float32")
        integral = cv2.integral(sal32)

        def rect_sum(ii: "np.ndarray", x0: int, y0: int, x1: int, y1: int) -> float:
            # integral image shape is (h+1, w+1)
            return float(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0])

        best_score = -1.0
        best_rect = (0, 0, w, h)

        if slide_axis == "x":
            if w == win_w:
                xs = [0]
            else:
                xs = list(range(0, max(1, w - win_w + 1), step))
                if xs[-1] != w - win_w:
                    xs.append(w - win_w)
            y0, y1 = 0, win_h
            for x0 in xs:
                x1 = x0 + win_w
                s = rect_sum(integral, x0, y0, x1, y1)
                if s > best_score:
                    best_score, best_rect = s, (x0, y0, x1, y1)
        else:
            if h == win_h:
                ys = [0]
            else:
                ys = list(range(0, max(1, h - win_h + 1), step))
                if ys[-1] != h - win_h:
                    ys.append(h - win_h)
            x0, x1 = 0, win_w
            for y0 in ys:
                y1 = y0 + win_h
                s = rect_sum(integral, x0, y0, x1, y1)
                if s > best_score:
                    best_score, best_rect = s, (x0, y0, x1, y1)

        # Crop and resize with PIL for consistent output quality
        x0, y0, x1, y1 = best_rect
        with Image.open(source_path) as pil_img2:
            try:
                pil_img2 = ImageOps.exif_transpose(pil_img2)
            except Exception:
                pass
            crop_box = (int(x0), int(y0), int(x1), int(y1))
            img_cropped = pil_img2.crop(crop_box)
            if img_cropped.mode not in ("RGB", "L"):
                img_cropped = img_cropped.convert("RGB")
            img_out = img_cropped.resize((tgt_w, tgt_h), Image.LANCZOS)
            img_out.save(output_path, "JPEG", quality=90)
