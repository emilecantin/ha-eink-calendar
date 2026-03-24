#!/usr/bin/env node
/**
 * Generate PNG icons from Material Design Icons (MDI) SVG files.
 *
 * This script downloads SVG icons from the @mdi/svg npm package and converts
 * them to 24x24 PNG files for use in the E-Ink Calendar renderer.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const { createCanvas, loadImage } = require('canvas');

// Icon names to generate (without mdi: prefix)
const ICONS_TO_GENERATE = [
  // Existing icons (for reference/regeneration)
  'airplane',
  'bell',
  'briefcase',
  'calendar',
  'car',
  'check',
  'email',
  'food',
  'gift',
  'heart',
  'home',
  'medical',
  'party',
  'phone',
  'school',
  'shopping',
  'star',
  // New common calendar icons
  'infinity',
  'account',
  'account-group',
  'baby-face',
  'bank',
  'basket',
  'beach',
  'beer',
  'bike',
  'book',
  'bookmark',
  'brush',
  'bug',
  'cake',
  'camera',
  'cash',
  'charity',
  'chart-line',
  'church',
  'city',
  'clipboard',
  'clock',
  'coffee',
  'cog',
  'compass',
  'controller-classic',
  'creation',
  'domain',
  'dumbbell',
  'earth',
  'family-tree',
  'ferry',
  'file-document',
  'film',
  'finance',
  'fire',
  'flag',
  'flask',
  'flower',
  'football',
  'forest',
  'fuel',
  'gamepad',
  'glass-cocktail',
  'golf',
  'hammer',
  'handshake',
  'hiking',
  'hospital',
  'image',
  'karate',
  'key',
  'ladder',
  'laptop',
  'leaf',
  'library',
  'lightbulb',
  'link',
  'lock',
  'map-marker',
  'meditation',
  'microphone',
  'monitor',
  'motorbike',
  'music',
  'nature',
  'newspaper',
  'notebook',
  'palette',
  'paw',
  'pencil',
  'pharmacy',
  'piano',
  'pill',
  'pizza',
  'presentation',
  'printer',
  'puzzle',
  'racquetball',
  'restore',
  'robot',
  'rocket',
  'run',
  'sail-boat',
  'scale-balance',
  'scissors',
  'shield',
  'ship-wheel',
  'sitemap',
  'soccer',
  'sofa',
  'spa',
  'subway',
  'swim',
  'sync',
  'taxi',
  'teach',
  'television',
  'tennis',
  'thumb-up',
  'tools',
  'train',
  'trophy',
  'truck',
  'umbrella',
  'video',
  'wallet',
  'water',
  'waves',
  'weight-lifter',
  'wifi',
  'wrench',
  'yoga',
];

// Icon size (24x24 to match existing icons)
const ICON_SIZE = 24;

/**
 * Download MDI SVG icon from jsdelivr CDN
 */
async function downloadSvg(iconName, svgDir) {
  const svgFile = path.join(svgDir, `${iconName}.svg`);

  // Skip if already exists
  if (fs.existsSync(svgFile)) {
    return svgFile;
  }

  const url = `https://cdn.jsdelivr.net/npm/@mdi/svg@latest/svg/${iconName}.svg`;

  return new Promise((resolve, reject) => {
    console.log(`Downloading ${iconName}...`);

    https.get(url, (res) => {
      if (res.statusCode !== 200) {
        console.log(`  Warning: Failed to download ${iconName} (HTTP ${res.statusCode})`);
        resolve(null);
        return;
      }

      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        const svgContent = Buffer.concat(chunks).toString('utf8');

        if (!svgContent.includes('<svg')) {
          console.log(`  Warning: Invalid SVG for ${iconName}`);
          resolve(null);
          return;
        }

        fs.writeFileSync(svgFile, svgContent);
        resolve(svgFile);
      });
    }).on('error', (err) => {
      console.log(`  Error downloading ${iconName}: ${err.message}`);
      resolve(null);
    });
  });
}

/**
 * Convert SVG to PNG using node-canvas
 */
async function svgToPng(svgFile, pngFile) {
  try {
    const svgContent = fs.readFileSync(svgFile, 'utf8');

    // Extract viewBox or use default 24x24
    const viewBoxMatch = svgContent.match(/viewBox="([^"]+)"/);
    let viewBox = '0 0 24 24';
    if (viewBoxMatch) {
      viewBox = viewBoxMatch[1];
    }

    const [, , vbWidth, vbHeight] = viewBox.split(' ').map(Number);

    // Create a data URL from the SVG
    const svgDataUrl = `data:image/svg+xml;base64,${Buffer.from(svgContent).toString('base64')}`;

    // Load SVG as image
    const img = await loadImage(svgDataUrl);

    // Create canvas
    const canvas = createCanvas(ICON_SIZE, ICON_SIZE);
    const ctx = canvas.getContext('2d');

    // Draw the SVG scaled to fit
    ctx.drawImage(img, 0, 0, ICON_SIZE, ICON_SIZE);

    // Save as PNG
    const buffer = canvas.toBuffer('image/png');
    fs.writeFileSync(pngFile, buffer);

    return true;
  } catch (error) {
    console.log(`  Error converting ${path.basename(svgFile)}: ${error.message}`);
    return false;
  }
}

/**
 * Main function
 */
async function main() {
  const iconsDir = path.join(__dirname, 'icons');
  const svgDir = path.join(__dirname, 'icons_svg_cache');

  // Create directories
  if (!fs.existsSync(iconsDir)) {
    fs.mkdirSync(iconsDir);
  }
  if (!fs.existsSync(svgDir)) {
    fs.mkdirSync(svgDir);
  }

  console.log(`Generating ${ICONS_TO_GENERATE.length} icons...`);
  console.log(`Icons directory: ${iconsDir}`);
  console.log(`SVG cache directory: ${svgDir}`);
  console.log('');

  let successCount = 0;
  const failedIcons = [];

  for (const iconName of ICONS_TO_GENERATE) {
    const pngFile = path.join(iconsDir, `${iconName}.png`);

    // Download SVG
    const svgFile = await downloadSvg(iconName, svgDir);
    if (!svgFile) {
      failedIcons.push(iconName);
      continue;
    }

    // Convert to PNG
    if (await svgToPng(svgFile, pngFile)) {
      console.log(`  ✓ Generated ${iconName}.png`);
      successCount++;
    } else {
      failedIcons.push(iconName);
    }
  }

  console.log('');
  console.log(`Successfully generated ${successCount}/${ICONS_TO_GENERATE.length} icons`);

  if (failedIcons.length > 0) {
    console.log(`\nFailed to generate ${failedIcons.length} icons:`);
    failedIcons.forEach((icon) => console.log(`  - ${icon}`));
  }

  // Generate a JSON file listing all available icons
  const availableIcons = fs.readdirSync(iconsDir)
    .filter((f) => f.endsWith('.png'))
    .map((f) => f.replace('.png', ''))
    .sort();

  const iconsListFile = path.join(iconsDir, 'available_icons.json');
  fs.writeFileSync(iconsListFile, JSON.stringify(availableIcons, null, 2));

  console.log(`\nTotal icons available: ${availableIcons.length}`);
  console.log(`Icon list saved to: ${iconsListFile}`);
}

main().catch(console.error);
