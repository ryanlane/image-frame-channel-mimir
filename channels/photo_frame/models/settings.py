"""
Settings Data Models for Photo Frame Channel
"""

from typing import Dict, Any


class ChannelSettings:
    """Channel-level settings for photo frame"""
    
    VALID_ORDER_MODES = ["added", "random", "custom"]
    # Supported crop/display modes. Keep UI-friendly names here; rendering maps to internal ops.
    VALID_CROP_MODES = [
        "smart_crop",    # content-aware center/cover
        "fit",           # letterbox/pad
        "fill",          # alias to smart_crop
        "opencv-saliency",  # OpenCV saliency-based smart crop
        "opencv_saliency",  # legacy/alias spelling
        "face-portrait",    # Face detection portrait crop
        "face_portrait",    # alias
    ]
    VALID_TRANSITIONS = ["fade", "slide", "none"]
    VALID_UNITS = ["days", "hours", "minutes", "seconds"]

    def __init__(self, settings_data: Dict[str, Any] = None):
        """Initialize with settings data"""
        data = settings_data or {}
        
        # Core slideshow settings
        self.slideshow_enabled = self._get_setting_value(data, "slideshow_enabled", True)
        self.order_mode = self._get_setting_value(data, "order_mode", "added")
        self.crop_mode = self._get_setting_value(data, "crop_mode", "smart_crop")
        self.transition_effect = self._get_setting_value(data, "transition_effect", "fade")
        
        # Update interval settings
        self.update_interval_unit = self._get_setting_value(data, "update_interval_unit", "minutes")
        self.update_interval_value = self._get_setting_value(data, "update_interval_value", 30)

    def _get_setting_value(self, data: Dict[str, Any], key: str, default: Any) -> Any:
        """Extract setting value from data, handling both direct values and setting objects"""
        setting = data.get(key, default)
        
        # Handle settings stored as objects with 'value' property
        if isinstance(setting, dict) and 'value' in setting:
            return setting['value']
        
        return setting

    def validate(self) -> Dict[str, str]:
        """Validate all settings and return any errors"""
        errors = {}

        if self.order_mode not in self.VALID_ORDER_MODES:
            errors["order_mode"] = f"Must be one of: {', '.join(self.VALID_ORDER_MODES)}"

        if self.crop_mode not in self.VALID_CROP_MODES:
            errors["crop_mode"] = f"Must be one of: {', '.join(self.VALID_CROP_MODES)}"

        if self.transition_effect not in self.VALID_TRANSITIONS:
            errors["transition_effect"] = f"Must be one of: {', '.join(self.VALID_TRANSITIONS)}"

        if self.update_interval_unit not in self.VALID_UNITS:
            errors["update_interval_unit"] = f"Must be one of: {', '.join(self.VALID_UNITS)}"

        if not isinstance(self.update_interval_value, int) or self.update_interval_value < 1:
            errors["update_interval_value"] = "Must be a positive integer"

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "slideshow_enabled": self.slideshow_enabled,
            "order_mode": self.order_mode,
            "crop_mode": self.crop_mode,
            "transition_effect": self.transition_effect,
            "update_interval_unit": self.update_interval_unit,
            "update_interval_value": self.update_interval_value
        }

    def update(self, new_settings: Dict[str, Any]) -> None:
        """Update settings with new values"""
        for key, value in new_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)


class GallerySettings:
    """Gallery-specific display settings"""
    
    def __init__(self, settings_data: Dict[str, Any] = None):
        """Initialize with settings data"""
        data = settings_data or {}
        
        # Use same defaults as ChannelSettings
        self.order_mode = data.get("order_mode", "added")
        self.crop_mode = data.get("crop_mode", "smart_crop")
        self.transition_effect = data.get("transition_effect", "fade")
        self.update_interval_value = data.get("update_interval_value", 30)
        self.update_interval_unit = data.get("update_interval_unit", "minutes")
        self.slideshow_enabled = data.get("slideshow_enabled", True)

    def validate(self) -> Dict[str, str]:
        """Validate gallery settings"""
        # Use same validation as ChannelSettings
        temp_channel_settings = ChannelSettings(self.to_dict())
        return temp_channel_settings.validate()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "order_mode": self.order_mode,
            "crop_mode": self.crop_mode,
            "transition_effect": self.transition_effect,
            "update_interval_value": self.update_interval_value,
            "update_interval_unit": self.update_interval_unit,
            "slideshow_enabled": self.slideshow_enabled
        }

    def update(self, new_settings: Dict[str, Any]) -> None:
        """Update settings with new values"""
        for key, value in new_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def from_channel_defaults(cls, channel_settings: ChannelSettings) -> "GallerySettings":
        """Create gallery settings from channel defaults"""
        return cls(channel_settings.to_dict())


class SettingsSchema:
    """Schema definitions for settings validation"""
    
    @staticmethod
    def get_channel_schema() -> Dict[str, Any]:
        """Get schema for channel settings"""
        return {
            "type": "object",
            "properties": {
                "slideshow_enabled": {
                    "type": "boolean",
                    "title": "Enable Slideshow",
                    "description": "Automatically rotate through images"
                },
                "order_mode": {
                    "type": "string",
                    "enum": ChannelSettings.VALID_ORDER_MODES,
                    "title": "Image Order",
                    "description": "How to order images in slideshow"
                },
                "crop_mode": {
                    "type": "string", 
                    "enum": ChannelSettings.VALID_CROP_MODES,
                    "title": "Display Mode",
                    "description": "How to fit images to display"
                },
                "transition_effect": {
                    "type": "string",
                    "enum": ChannelSettings.VALID_TRANSITIONS,
                    "title": "Transition Effect",
                    "description": "Visual transition between images"
                },
                "update_interval_unit": {
                    "type": "string",
                    "enum": ChannelSettings.VALID_UNITS,
                    "title": "Update Interval Unit",
                    "description": "Unit for channel update frequency"
                },
                "update_interval_value": {
                    "type": "integer",
                    "minimum": 1,
                    "title": "Update Interval Value", 
                    "description": "Numeric value for channel update frequency"
                }
            }
        }

    @staticmethod
    def get_gallery_schema() -> Dict[str, Any]:
        """Get schema for gallery settings"""
        # Gallery settings use the same schema as channel settings
        return SettingsSchema.get_channel_schema()


class SettingsManager:
    """Manager for handling settings operations"""
    
    def __init__(self, default_settings: Dict[str, Any] = None):
        self.defaults = ChannelSettings(default_settings)

    def validate_channel_settings(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """Validate channel settings"""
        channel_settings = ChannelSettings(settings)
        return channel_settings.validate()

    def validate_gallery_settings(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """Validate gallery settings"""
        gallery_settings = GallerySettings(settings)
        return gallery_settings.validate()

    def get_default_gallery_settings(self) -> Dict[str, Any]:
        """Get default settings for new galleries"""
        return self.defaults.to_dict()

    def merge_with_defaults(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Merge provided settings with defaults"""
        merged = self.defaults.to_dict()
        merged.update(settings)
        return merged
