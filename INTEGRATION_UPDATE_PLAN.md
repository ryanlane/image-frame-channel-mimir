# Photo Frame Channel API Integration Updates

## Current Status
The photo frame channel has excellent modular architecture but needs updates to integrate properly with the centralized Mimir API that we just fixed.

## Key Updates Needed

### 1. Path Resolution Updates
- Update all file path references to use the channel discovery service
- Ensure paths align with the `/var/opt/mimir/mimir-api/channels/photo_frame/` structure
- Update thumbnail serving to use the correct API endpoints

### 2. Route Integration
- Modify routes to work as sub-routes under `/api/channels/com.epaperframe.photoframe/`
- Ensure compatibility with the main API router structure
- Update endpoint paths for consistency

### 3. API Endpoint Alignment
- Align subchannel operations with the main API's subchannel endpoints
- Ensure image upload/management works with the centralized API
- Update thumbnail serving to use the correct fallback hierarchy

### 4. Configuration Updates
- Verify config.json is correctly using the proper channel ID
- Update any hardcoded paths to use dynamic resolution
- Ensure settings integration works with the main API

## Implementation Plan

### Phase 1: Path Resolution ✅
- Update channel.py to use proper channel directory resolution
- Fix thumbnail path references
- Update image upload/serving paths

### Phase 2: Route Integration 🔄
- Modify route structure to work as sub-routes
- Update endpoint definitions
- Ensure proper dependency injection

### Phase 3: API Compatibility 📋
- Test integration with main API
- Verify subchannel operations work correctly
- Validate image upload and serving

### Phase 4: Testing & Validation 🧪
- Run comprehensive API tests
- Verify photo frame specific functionality
- Test thumbnail serving and image operations

## Files to Update
1. `channel.py` - Main channel class
2. `routes/*.py` - All route modules
3. `services/*.py` - Service layer updates
4. Path references throughout the codebase

## Testing
- Use the comprehensive test suite we created
- Focus on subchannel operations since that was the original issue
- Verify thumbnail serving works correctly
