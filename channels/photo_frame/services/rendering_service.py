"""
Rendering Service - Business logic for image rendering and display
"""

import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path


class RenderingService:
    """Service for rendering images for display"""
    
    def __init__(self, channel_dir: Path, image_processor=None, placeholder_image: str = "placeholder.jpg"):
        self.channel_dir = Path(channel_dir)
        self.image_processor = image_processor
        self.placeholder_image = placeholder_image
        self.current_image_id = None
        self.last_update = None
        self.last_error = None
    
    async def render_image(
        self, 
        resolution: Tuple[int, int], 
        orientation: str = "landscape", 
        settings: Dict[str, Any] = None, 
        subchannel_id: str = None,
        gallery_service=None,
        image_service=None
    ) -> str:
        """
        Render image for specific display resolution
        
        Args:
            resolution: (width, height) in pixels
            orientation: "landscape" or "portrait"
            settings: Display settings (deprecated - use gallery settings)
            subchannel_id: Gallery ID to select from
            gallery_service: Gallery service instance
            image_service: Image service instance
            
        Returns:
            Relative path to rendered image
        """
        try:
            # Create resolution-specific directory
            width, height = resolution
            resolution_folder = f"{width}x{height}"
            resolution_dir = self.channel_dir / "current" / resolution_folder
            resolution_dir.mkdir(parents=True, exist_ok=True)
            
            # Set output path for this resolution
            output_path = resolution_dir / "current.jpg"
            
            print(f"🎯 Rendering image for photo frame at resolution {width}x{height}")
            if subchannel_id:
                print(f"   Gallery: {subchannel_id}")
            
            # Get settings from gallery if specified, otherwise use global settings
            if subchannel_id and gallery_service:
                display_settings = gallery_service.get_gallery_settings(subchannel_id)
                print(f"   Using gallery settings: {display_settings}")
            else:
                display_settings = settings or {}
                print(f"   Using global settings: {display_settings}")
            
            # Get next image based on gallery selection or all images
            if subchannel_id and gallery_service and image_service:
                all_images = image_service.get_all_images()
                image_record = gallery_service.get_next_image_from_gallery(
                    subchannel_id, all_images, display_settings, image_service=image_service
                )
                if not image_record:
                    # Extra diagnostics to understand why gallery selection failed
                    gallery_obj = gallery_service.get_gallery(subchannel_id)
                    content_len = len(getattr(gallery_obj, 'content_ids', [])) if gallery_obj else 0
                    print(f"   [GallerySelect] No image for gallery='{subchannel_id}' content_ids={content_len} enabled_global={len(all_images)}")
            else:
                image_record = await self._get_next_image(display_settings, image_service)
            
            if not image_record:
                print("   No images available, using placeholder")
                return await self._render_placeholder(output_path, resolution, display_settings)
            
            print(f"   Selected image: {image_record['filename']}")
            
            # Process image for display
            # Normalize crop_mode synonyms here so downstream processor is consistent
            if display_settings.get("crop_mode") == "fill":
                display_settings["crop_mode"] = "smart_crop"

            success = await self._process_image_for_display(
                image_record, output_path, resolution, orientation, display_settings
            )
            
            if success:
                # Update statistics
                if image_service:
                    image_service.update_image_stats(image_record["id"])
                
                self.current_image_id = image_record["id"]
                self.last_update = datetime.now(timezone.utc)
                self.last_error = None
                
                # Return relative path
                relative_path = output_path.relative_to(self.channel_dir)
                return str(relative_path)
            else:
                print("   Failed to process image, using placeholder")
                return await self._render_placeholder(output_path, resolution, display_settings)
                
        except Exception as e:
            self.last_error = str(e)
            print(f"   Error rendering image: {e}")
            return await self._get_fallback_image(resolution)
    
    async def _get_next_image(self, settings: Dict[str, Any], image_service) -> Optional[Dict[str, Any]]:
        """Select next image based on slideshow settings"""
        if not settings.get("slideshow_enabled", True):
            return None
        
        if not image_service:
            return None
        
        order_mode = settings.get("order_mode", "added")
        enabled_images = image_service.get_enabled_images()
        
        if not enabled_images:
            return None
        
        if order_mode == "random":
            return random.choice(enabled_images)
        elif order_mode == "custom":
            return self._get_next_by_custom_order(enabled_images)
        else:  # "added"
            return self._get_next_by_date_added(enabled_images)
    
    def _get_next_by_custom_order(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get next image by custom order"""
        # Sort by sort_order, then by times_shown (least shown first)
        return sorted(images, key=lambda x: (x.get("sort_order", 0), x.get("times_shown", 0)))[0]
    
    def _get_next_by_date_added(self, images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get next image by date added"""
        # Sort by times_shown (least shown first), then by creation date
        return sorted(images, key=lambda x: (x.get("times_shown", 0), x.get("created_at", "")))[0]
    
    async def _process_image_for_display(
        self, 
        image_record: Dict[str, Any], 
        output_path: Path, 
        resolution: Tuple[int, int], 
        orientation: str,
        settings: Dict[str, Any]
    ) -> bool:
        """Process image according to crop settings and display mode"""
        try:
            source_path = self.channel_dir / "assets" / "uploads" / image_record["filename"]
            
            if not source_path.exists():
                print(f"   Source image not found: {source_path}")
                return False
            
            crop_mode = settings.get("crop_mode", "smart_crop")
            processed = False
            if self.image_processor:
                try:
                    if crop_mode == "smart_crop":
                        await self.image_processor.process_smart_crop(
                            source_path, output_path, resolution, image_record
                        )
                    elif crop_mode in ("opencv-saliency", "opencv_saliency") and hasattr(self.image_processor, "process_opencv_saliency"):
                        await self.image_processor.process_opencv_saliency(
                            source_path, output_path, resolution, image_record, settings
                        )
                    elif crop_mode == "letterbox":
                        await self.image_processor.process_letterbox(
                            source_path, output_path, resolution
                        )
                    else:  # stretch
                        await self.image_processor.process_stretch(
                            source_path, output_path, resolution
                        )
                    processed = True
                except Exception as e:  # noqa: BLE001
                    print(f"   ImageProcessor failed ({e}); falling back to internal processor")
            if not processed:
                # Internal minimal processor (center-crop cover logic + resize) to guarantee output
                try:
                    from PIL import Image
                    tgt_w, tgt_h = resolution
                    with Image.open(source_path) as img:
                        if img.mode not in ("RGB", "L"):
                            img = img.convert("RGB")
                        w, h = img.size
                        target_aspect = tgt_w / tgt_h if tgt_h else 1
                        current_aspect = w / h if h else target_aspect
                        if crop_mode in ("smart_crop", "fill", "stretch") and abs(current_aspect - target_aspect) > 0.0001 and crop_mode != "letterbox":
                            if current_aspect > target_aspect:
                                # wider -> crop width
                                new_w = int(h * target_aspect)
                                x0 = (w - new_w) // 2
                                img = img.crop((x0, 0, x0 + new_w, h))
                            else:
                                new_h = int(w / target_aspect)
                                y0 = (h - new_h) // 2
                                img = img.crop((0, y0, w, y0 + new_h))
                        elif crop_mode == "letterbox":
                            # Fit inside without crop, then pad
                            # Compute scaled size
                            ratio = min(tgt_w / w, tgt_h / h)
                            new_w = max(1, int(w * ratio))
                            new_h = max(1, int(h * ratio))
                            img = img.resize((new_w, new_h), Image.LANCZOS)
                            # Create background and paste centered
                            bg = Image.new("RGB", (tgt_w, tgt_h), (0, 0, 0))
                            off_x = (tgt_w - new_w) // 2
                            off_y = (tgt_h - new_h) // 2
                            bg.paste(img, (off_x, off_y))
                            img = bg
                        if crop_mode != "letterbox":
                            if img.size != (tgt_w, tgt_h):
                                img = img.resize((tgt_w, tgt_h), Image.LANCZOS)
                        img.save(output_path, "JPEG", quality=90)
                        processed = True
                        print(f"   Internal processor produced {output_path} size={tgt_w}x{tgt_h}")
                except Exception as ie:  # noqa: BLE001
                    print(f"   Internal processing failed ({ie}); copying original")
                    import shutil
                    shutil.copy2(source_path, output_path)
                    processed = True

            # Post-process verification: ensure output matches requested resolution
            try:
                from PIL import Image
                tgt_w, tgt_h = resolution
                with Image.open(output_path) as out_img:
                    ow, oh = out_img.size
                    if (ow, oh) != (tgt_w, tgt_h):
                        print(f"   Adjusting final image size from {ow}x{oh} to {tgt_w}x{tgt_h}")
                        out_img = out_img.resize((tgt_w, tgt_h), Image.LANCZOS)
                        out_img.save(output_path, "JPEG", quality=88)
            except Exception as ve:  # noqa: BLE001
                print(f"   Verification step failed: {ve}")
            
            return True
            
        except Exception as e:
            print(f"   Error processing image: {e}")
            return False
    
    async def _render_placeholder(
        self, 
        output_path: Path, 
        resolution: Tuple[int, int], 
        settings: Dict[str, Any]
    ) -> str:
        """Render placeholder image"""
        try:
            placeholder_path = self.channel_dir / self.placeholder_image
            
            if placeholder_path.exists() and self.image_processor:
                # Process placeholder with same settings
                placeholder_record = {
                    "filename": self.placeholder_image,
                    "crop_x": 0,
                    "crop_y": 0,
                    "crop_width": 100,
                    "crop_height": 100
                }
                
                await self._process_image_for_display(
                    placeholder_record, output_path, resolution, "landscape", settings
                )
            elif placeholder_path.exists():
                # Simple copy
                import shutil
                shutil.copy2(placeholder_path, output_path)
            else:
                # Create a simple colored image
                if self.image_processor:
                    await self.image_processor.create_solid_color_image(
                        output_path, resolution, (128, 128, 128)
                    )
            
            # Return relative path
            relative_path = output_path.relative_to(self.channel_dir)
            return str(relative_path)
            
        except Exception as e:
            print(f"   Error rendering placeholder: {e}")
            return self.placeholder_image
    
    async def _get_fallback_image(self, resolution: Tuple[int, int]) -> str:
        """Get fallback image when primary rendering fails"""
        try:
            # Try last successful image
            if self.current_image_id:
                width, height = resolution
                resolution_folder = f"{width}x{height}"
                current_path = self.channel_dir / "current" / resolution_folder / "current.jpg"
                
                if current_path.exists():
                    relative_path = current_path.relative_to(self.channel_dir)
                    return str(relative_path)
            
            # Use placeholder
            return self.placeholder_image
            
        except Exception:
            return self.placeholder_image
    
    def get_rendering_status(self) -> Dict[str, Any]:
        """Get current rendering status"""
        return {
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "last_error": self.last_error,
            "current_image_id": self.current_image_id
        }
    
    def clear_cache(self) -> Dict[str, Any]:
        """Clear rendered image cache"""
        try:
            current_dir = self.channel_dir / "current"
            if not current_dir.exists():
                return {"message": "No cache to clear"}
            
            deleted_count = 0
            for resolution_dir in current_dir.iterdir():
                if resolution_dir.is_dir():
                    for file in resolution_dir.iterdir():
                        if file.is_file():
                            file.unlink()
                            deleted_count += 1
                    
                    # Remove empty directories
                    try:
                        resolution_dir.rmdir()
                    except OSError:
                        pass  # Directory not empty
            
            return {
                "message": f"Cleared {deleted_count} cached images",
                "deleted_count": deleted_count
            }
            
        except Exception as e:
            return {"error": f"Failed to clear cache: {e}"}
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached rendered images"""
        try:
            current_dir = self.channel_dir / "current"
            if not current_dir.exists():
                return {
                    "resolutions": [],
                    "total_files": 0,
                    "total_size_mb": 0
                }
            
            resolutions = []
            total_files = 0
            total_size = 0
            
            for resolution_dir in current_dir.iterdir():
                if resolution_dir.is_dir():
                    files = list(resolution_dir.iterdir())
                    dir_size = sum(f.stat().st_size for f in files if f.is_file())
                    
                    resolutions.append({
                        "resolution": resolution_dir.name,
                        "files": len(files),
                        "size_mb": round(dir_size / 1024 / 1024, 2)
                    })
                    
                    total_files += len(files)
                    total_size += dir_size
            
            return {
                "resolutions": resolutions,
                "total_files": total_files,
                "total_size_mb": round(total_size / 1024 / 1024, 2)
            }
            
        except Exception as e:
            return {"error": f"Failed to get cache info: {e}"}
    
    def validate_rendering_setup(self) -> Dict[str, Any]:
        """Validate that rendering components are properly configured"""
        issues = []
        
        # Check placeholder
        placeholder_path = self.channel_dir / self.placeholder_image
        if not placeholder_path.exists():
            issues.append(f"Placeholder image missing: {self.placeholder_image}")
        
        # Check image processor
        if not self.image_processor:
            issues.append("Image processor not configured")
        
        # Check current directory
        current_dir = self.channel_dir / "current"
        if not current_dir.exists():
            try:
                current_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create current directory: {e}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
