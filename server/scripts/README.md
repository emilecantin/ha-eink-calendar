# Server Utility Scripts

Helper scripts for server development and asset management.

## Icon Management Scripts

### `download_icons_fixed.sh`
Downloads Material Design Icons (MDI) SVG files with proper error handling.

**Features**:
- Downloads icons from Pictogrammers CDN
- Fixed version with better error handling
- Creates `icons_svg_cache/` directory
- Skips already downloaded icons

**Usage**:
```bash
cd server
./scripts/download_icons_fixed.sh
```

### `download_icons_simple.sh`
Simple version of icon downloader without error handling.

**Usage**:
```bash
cd server
./scripts/download_icons_simple.sh
```

**Note**: Use `download_icons_fixed.sh` for production. This is kept for reference.

## Notes

Icon SVG files are cached in `server/icons_svg_cache/` to avoid repeated downloads.
The server converts these SVGs to PNGs at runtime for rendering on the e-paper display.
