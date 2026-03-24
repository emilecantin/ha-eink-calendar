#!/bin/bash
# Script to download and convert MDI icons

ICONS_DIR="../custom_components/eink_calendar/renderer/icons"
SVG_DIR="./icons_svg_cache"

mkdir -p "$ICONS_DIR"
mkdir -p "$SVG_DIR"

success=0
failed=0

while IFS= read -r icon; do
  [ -z "$icon" ] && continue
  
  png_file="$ICONS_DIR/${icon}.png"
  svg_file="$SVG_DIR/${icon}.svg"
  
  # Skip if PNG already exists
  if [ -f "$png_file" ]; then
    echo "✓ Skipping $icon (already exists)"
    ((success++))
    continue
  fi
  
  # Download SVG if not cached
  if [ ! -f "$svg_file" ]; then
    echo "Downloading $icon..."
    curl -sL "https://cdn.jsdelivr.net/npm/@mdi/svg@latest/svg/${icon}.svg" -o "$svg_file"
    
    # Check if download succeeded
    if ! grep -q "<svg" "$svg_file" 2>/dev/null; then
      echo "  ✗ Failed to download $icon"
      rm -f "$svg_file"
      ((failed++))
      continue
    fi
    
    # Add width and height attributes if missing
    sed -i '' 's/<svg /<svg width="24" height="24" /' "$svg_file"
  fi
  
  # Convert SVG to PNG using node
  node -e "
    const fs = require('fs');
    const { createCanvas, loadImage } = require('canvas');
    
    const svgContent = fs.readFileSync('$svg_file', 'utf8');
    const svgDataUrl = \`data:image/svg+xml;base64,\${Buffer.from(svgContent).toString('base64')}\`;
    
    loadImage(svgDataUrl).then(img => {
      const canvas = createCanvas(24, 24);
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, 24, 24);
      const buffer = canvas.toBuffer('image/png');
      fs.writeFileSync('$png_file', buffer);
      console.log('  ✓ Generated ${icon}.png');
    }).catch(err => {
      console.error('  ✗ Error converting ${icon}:', err.message);
      process.exit(1);
    });
  " && ((success++)) || ((failed++))
  
  sleep 0.05
done < /tmp/icons_to_generate.txt

echo ""
echo "Successfully generated: $success"
echo "Failed: $failed"

# Generate list
ls "$ICONS_DIR"/*.png | xargs -n 1 basename | sed 's/.png$//' | sort > /tmp/available_icons.txt
echo ""
echo "Total icons available: $(wc -l < /tmp/available_icons.txt | tr -d ' ')"
