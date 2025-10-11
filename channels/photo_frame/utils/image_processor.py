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
        """Smart crop using OpenCV saliency + multi-scale 2D search.

        Improvements vs earlier version:
        - 2D sliding-window search at multiple scales (not just full-height/width), so
          salient regions near top/bottom can be captured (e.g., a subject's head).
        - Edge-cut penalty discourages crops that slice through high-saliency regions
          at the borders (reduces decapitations).
        - Optional center/thirds bias can gently pull crop boxes toward pleasing framing.

        Tunables via settings (all optional):
        - saliency_scales: list[float] window scales, default [1.0, 0.9, 0.8, 0.7]
        - saliency_stride_frac: float stride as frac of window min-dim, default 0.08
        - saliency_center_bias: float in [0..1], default 0.05
        - saliency_edge_penalty: float in [0..1], default 0.15
        - saliency_edge_band_frac: float fraction of window size used as border band, default 0.06
        - saliency_color_weight: optional additional color variance weight, default 0.2

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

        # Build saliency map: Laplacian magnitude + local variance (+ optional color variance)
        gray_f = gray.astype("float32")
        lap = cv2.Laplacian(gray_f, cv2.CV_32F, ksize=3)
        lap = cv2.GaussianBlur(cv2.absdiff(lap, 0), (0, 0), 1.0)
        k = int(max(5, round(min(w, h) / 50)))
        if k % 2 == 0:
            k += 1
        mean = cv2.GaussianBlur(gray_f, (k, k), 0)
        mean_sq = cv2.GaussianBlur(gray_f * gray_f, (k, k), 0)
        var = cv2.max(mean_sq - mean * mean, 0)
        # Optional color variance (S channel) to help on low-contrast structures
        color_weight = float(settings.get("saliency_color_weight", 0.2))
        if np_img.ndim == 3 and color_weight > 0.0:
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            s_chan = hsv[:, :, 1].astype("float32")
            mean_s = cv2.GaussianBlur(s_chan, (k, k), 0)
            mean_sq_s = cv2.GaussianBlur(s_chan * s_chan, (k, k), 0)
            var_s = cv2.max(mean_sq_s - mean_s * mean_s, 0)
        else:
            var_s = np.zeros_like(var)

        # Normalize to 0..1 and combine
        def norm01(x: "np.ndarray") -> "np.ndarray":
            mn, mx = float(x.min()), float(x.max())
            if mx - mn < 1e-6:
                return np.zeros_like(x, dtype="float32")
            return (x - mn) / (mx - mn)

        lap_n = norm01(lap)
        var_n = norm01(var)
        var_s_n = norm01(var_s)
        sal = 0.6 * lap_n + 0.4 * var_n + color_weight * var_s_n

        # Optional: small blur to smooth noise
        sal = cv2.GaussianBlur(sal, (0, 0), sigmaX=1.0)

        tgt_w, tgt_h = resolution
        target_aspect = (tgt_w / tgt_h) if tgt_h else (w / max(h, 1))
        # Compute maximum window that matches target aspect
        if (w / h) >= target_aspect:
            max_h = h
            max_w = int(round(h * target_aspect))
        else:
            max_w = w
            max_h = int(round(w / target_aspect))

        # Downscale saliency for faster search; remember scale
        max_dim = 512
        scale = 1.0
        Hs, Ws = sal.shape[:2]
        if max(Hs, Ws) > max_dim:
            scale = max_dim / float(max(Hs, Ws))
            sal_small = cv2.resize(sal, (int(round(Ws * scale)), int(round(Hs * scale))), interpolation=cv2.INTER_AREA)
        else:
            sal_small = sal
        Hs, Ws = sal_small.shape
        scale_back = 1.0 / scale

        # Precompute integral image
        sal32 = sal_small.astype("float32")
        integral = cv2.integral(sal32)

        def rect_sum(ii: "np.ndarray", x0: int, y0: int, x1: int, y1: int) -> float:
            return float(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0])

        # Tunables
        scales = list(settings.get("saliency_scales", [1.0, 0.9, 0.8, 0.7]))
        stride_frac = float(settings.get("saliency_stride_frac", 0.08))
        center_bias = float(settings.get("saliency_center_bias", 0.05))
        edge_penalty = float(settings.get("saliency_edge_penalty", 0.15))
        edge_band_frac = float(settings.get("saliency_edge_band_frac", 0.06))

        # Precompute gentle center/thirds bias mask
        yy, xx = np.mgrid[0:Hs, 0:Ws].astype("float32")
        cx, cy = Ws * 0.5, Hs * 0.45  # slight upward bias
        sig = 0.35 * max(Ws, Hs)
        center_mask = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (sig ** 2))))
        thirds_points = [(Ws * 1/3, Hs * 1/3), (Ws * 2/3, Hs * 1/3), (Ws * 1/3, Hs * 2/3), (Ws * 2/3, Hs * 2/3)]
        thirds_mask = np.zeros_like(center_mask)
        for tx, ty in thirds_points:
            thirds_mask = np.maximum(thirds_mask, np.exp(-(((xx - tx) ** 2 + (yy - ty) ** 2) / (2 * (sig ** 2)))))

        best_score = -1e18
        best_rect_small = (0, 0, Ws, Hs)

        # Search across scales and 2D positions
        for s in scales:
            win_w = max(8, int(round(max_w * s * scale)))
            win_h = max(8, int(round(max_h * s * scale)))
            if win_w > Ws or win_h > Hs:
                continue
            step = max(1, int(round(min(win_w, win_h) * stride_frac)))
            x_max = Ws - win_w
            y_max = Hs - win_h
            band = max(1, int(round(min(win_w, win_h) * edge_band_frac)))

            for y0 in range(0, y_max + 1, step):
                y1 = y0 + win_h
                for x0 in range(0, x_max + 1, step):
                    x1 = x0 + win_w
                    area = float(win_w * win_h)
                    # Saliency sum
                    s_sum = rect_sum(integral, x0, y0, x1, y1)
                    # Edge band penalty (high saliency near borders is penalized)
                    if win_w > 2 * band and win_h > 2 * band:
                        inner = rect_sum(integral, x0 + band, y0 + band, x1 - band, y1 - band)
                        edge_sal = s_sum - inner
                    else:
                        edge_sal = 0.0
                    edge_term = (edge_sal / max(1.0, area)) * edge_penalty
                    # Center/thirds gentle bias (sample center point of the window)
                    cxw = (x0 + x1) // 2
                    cyw = (y0 + y1) // 2
                    bias = center_mask[cyw, cxw] * 0.6 + thirds_mask[cyw, cxw] * 0.4
                    bias_term = center_bias * float(bias)
                    # Final score: avg saliency with penalties/bonuses
                    score = (s_sum / area) - edge_term + bias_term
                    if score > best_score:
                        best_score = score
                        best_rect_small = (x0, y0, x1, y1)

        # Crop and resize with PIL for consistent output quality
        x0s, y0s, x1s, y1s = best_rect_small
        # Map back to original coordinates
        x0 = int(round(x0s * scale_back))
        y0 = int(round(y0s * scale_back))
        x1 = int(round(x1s * scale_back))
        y1 = int(round(y1s * scale_back))
        # Clamp just in case
        x0 = max(0, min(x0, w - 1))
        y0 = max(0, min(y0, h - 1))
        x1 = max(x0 + 1, min(x1, w))
        y1 = max(y0 + 1, min(y1, h))
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
