#!/usr/bin/env python3
"""
Icon Generation Script for Omneva Media Player
Converts SVG icon to .ico (Windows) and .icns (macOS) formats
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from PIL import Image, ImageDraw
import xml.etree.ElementTree as ET

def get_script_dir():
    """Get the directory where this script is located"""
    return Path(__file__).parent

def find_svg_icon():
    """Find the SVG icon file in the assets directory"""
    script_dir = get_script_dir()
    svg_path = script_dir / 'src' / 'assets' / 'icon.svg'
    
    if svg_path.exists():
        return svg_path
    else:
        print(f"❌ SVG icon not found at: {svg_path}")
        return None

def parse_svg_dimensions(svg_path):
    """Parse SVG to get viewBox dimensions"""
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Get viewBox or use default dimensions
        if 'viewBox' in root.attrib:
            viewbox = root.attrib['viewBox'].split()
            return int(viewbox[2]), int(viewbox[3])
        else:
            # Default to 512x512 if no viewBox
            return 512, 512
    except Exception as e:
        print(f"⚠️  Could not parse SVG dimensions: {e}")
        return 512, 512

def render_svg_to_png(svg_path, size):
    """Render SVG to PNG using a headless browser or alternative method"""
    print(f"🎨 Rendering SVG to PNG at {size}x{size}...")
    
    # Try different rendering methods
    png_path = svg_path.parent / f'icon_{size}.png'
    
    # Method 1: Try using Inkscape (most reliable)
    if try_render_with_inkscape(svg_path, png_path, size):
        return png_path
    
    # Method 2: Try using rsvg-convert
    if try_render_with_rsvg(svg_path, png_path, size):
        return png_path
    
    # Method 3: Try using PIL with simple SVG parsing
    if try_render_with_pil(svg_path, png_path, size):
        return png_path
    
    print(f"❌ Failed to render SVG to PNG at {size}x{size}")
    return None

def try_render_with_inkscape(svg_path, png_path, size):
    """Try rendering with Inkscape"""
    try:
        cmd = [
            'inkscape',
            '--export-type=png',
            f'--export-width={size}',
            f'--export-height={size}',
            '--export-filename=' + str(png_path.with_suffix('')),
            str(svg_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Rendered with Inkscape: {png_path}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def try_render_with_rsvg(svg_path, png_path, size):
    """Try rendering with rsvg-convert"""
    try:
        cmd = [
            'rsvg-convert',
            '-w', str(size),
            '-h', str(size),
            str(svg_path),
            str(png_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Rendered with rsvg-convert: {png_path}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def try_render_with_pil(svg_path, png_path, size):
    """Try rendering with PIL (basic SVG support)"""
    try:
        # Parse SVG and create a simple representation
        tree = ET.parse(svg_path)
        root = tree.getroot()
        
        # Create image with transparent background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Get viewBox dimensions
        width, height = parse_svg_dimensions(svg_path)
        
        # Extract basic shapes (simplified approach)
        for element in root.iter():
            if element.tag.endswith('rect'):
                render_rect(draw, element, width, height, size)
            elif element.tag.endswith('path'):
                render_path(draw, element, width, height, size)
        
        img.save(png_path, 'PNG')
        print(f"✅ Rendered with PIL: {png_path}")
        return True
    except Exception as e:
        print(f"⚠️  PIL rendering failed: {e}")
        return False

def render_rect(draw, element, svg_width, svg_height, png_size):
    """Render a rectangle element"""
    try:
        x = float(element.attrib.get('x', 0))
        y = float(element.attrib.get('y', 0))
        w = float(element.attrib.get('width', 0))
        h = float(element.attrib.get('height', 0))
        
        # Scale to PNG dimensions
        scale = png_size / svg_width
        x_png = int(x * scale)
        y_png = int(y * scale)
        w_png = int(w * scale)
        h_png = int(h * scale)
        
        # Get fill color
        fill = element.attrib.get('fill', '#000000')
        if fill.startswith('#'):
            fill_rgb = tuple(int(fill[i:i+2], 16) for i in (1, 3, 5))
            fill_rgba = fill_rgb + (255,)
        else:
            fill_rgba = (0, 0, 0, 255)
        
        draw.rectangle([x_png, y_png, x_png + w_png, y_png + h_png], fill=fill_rgba)
    except Exception:
        pass

def render_path(draw, element, svg_width, svg_height, png_size):
    """Render a path element (simplified)"""
    try:
        d = element.attrib.get('d', '')
        if not d:
            return
        
        # Very basic path rendering - just draw a bounding box
        # This is a simplified approach for complex paths
        points = []
        for command in d.split():
            if command.upper() in ['M', 'L']:
                try:
                    coords = list(map(float, d.split()[d.split().index(command)+1:d.split().index(command)+3]))
                    if len(coords) >= 2:
                        points.append((coords[0], coords[1]))
                except:
                    continue
        
        if len(points) >= 2:
            # Scale points
            scale = png_size / svg_width
            scaled_points = [(int(p[0] * scale), int(p[1] * scale)) for p in points]
            
            # Get fill color
            fill = element.attrib.get('fill', '#000000')
            if fill.startswith('#'):
                fill_rgb = tuple(int(fill[i:i+2], 16) for i in (1, 3, 5))
                fill_rgba = fill_rgb + (255,)
            else:
                fill_rgba = (0, 0, 0, 255)
            
            # Draw polygon
            if len(scaled_points) >= 3:
                draw.polygon(scaled_points, fill=fill_rgba)
    except Exception:
        pass

def create_ico_file(png_paths, ico_path):
    """Create .ico file from multiple PNG sizes"""
    print(f"🔧 Creating ICO file: {ico_path}")
    
    try:
        images = []
        for png_path in png_paths:
            if png_path.exists():
                img = Image.open(png_path)
                images.append(img)
        
        if images:
            # Save as ICO with multiple sizes
            images[0].save(ico_path, format='ICO', sizes=[(img.size[0], img.size[1]) for img in images])
            print(f"✅ Created ICO file: {ico_path}")
            return True
        else:
            print("❌ No PNG images found for ICO creation")
            return False
    except Exception as e:
        print(f"❌ Failed to create ICO file: {e}")
        return False

def create_icns_file(png_paths, icns_path):
    """Create .icns file from multiple PNG sizes"""
    print(f"🔧 Creating ICNS file: {icns_path}")
    
    try:
        # Try using iconutil (macOS)
        if try_create_icns_with_iconutil(png_paths, icns_path):
            return True
        
        # Fallback: create a simple ICNS structure
        if try_create_icns_fallback(png_paths, icns_path):
            return True
        
        print("❌ Failed to create ICNS file")
        return False
    except Exception as e:
        print(f"❌ Failed to create ICNS file: {e}")
        return False

def try_create_icns_with_iconutil(png_paths, icns_path):
    """Try creating ICNS using macOS iconutil"""
    try:
        # Create iconset directory
        iconset_dir = icns_path.parent / 'Omneva.iconset'
        iconset_dir.mkdir(exist_ok=True)
        
        # Copy PNG files to iconset with proper naming
        size_mapping = {
            16: 'icon_16x16.png',
            32: 'icon_16x16@2x.png',
            128: 'icon_128x128.png',
            256: 'icon_128x128@2x.png',
            512: 'icon_256x256@2x.png'
        }
        
        for png_path in png_paths:
            if png_path.exists():
                size = int(png_path.stem.split('_')[-1])
                if size in size_mapping:
                    target_path = iconset_dir / size_mapping[size]
                    # Resize if needed
                    img = Image.open(png_path)
                    if img.size != (size, size):
                        img = img.resize((size, size), Image.Resampling.LANCZOS)
                    img.save(target_path)
        
        # Create ICNS using iconutil
        cmd = ['iconutil', '-c', 'icns', str(iconset_dir)]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Move the generated ICNS file
        generated_icns = iconset_dir.parent / 'Omneva.icns'
        if generated_icns.exists():
            generated_icns.rename(icns_path)
        
        # Clean up
        import shutil
        shutil.rmtree(iconset_dir)
        
        print(f"✅ Created ICNS file with iconutil: {icns_path}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def try_create_icns_fallback(png_paths, icns_path):
    """Fallback ICNS creation (basic structure)"""
    try:
        # This is a simplified fallback - creates a basic ICNS structure
        # For production use, iconutil is recommended
        
        # Create a basic ICNS with the largest available PNG
        largest_png = max(png_paths, key=lambda p: p.stat().st_size if p.exists() else 0)
        if largest_png.exists():
            img = Image.open(largest_png)
            
            # Create a simple ICNS header and write the PNG data
            # This is a very basic implementation
            with open(icns_path, 'wb') as f:
                # Write ICNS header (simplified)
                f.write(b'icns\x00\x00')  # Magic number
                f.write((0).to_bytes(4, 'big'))  # File length placeholder
                f.write((0).to_bytes(4, 'big'))  # Image count
                
                # Write PNG data (simplified - just one image)
                with open(largest_png, 'rb') as f:
                    png_data = f.read()
                f.write(len(png_data).to_bytes(4, 'big'))
                f.write(png_data)
            
            print(f"✅ Created basic ICNS file: {icns_path}")
            return True
    except Exception as e:
        print(f"⚠️  Fallback ICNS creation failed: {e}")
        return False

def generate_icons():
    """Main icon generation function"""
    print("🎨 Omneva Icon Generation Script")
    print("=" * 40)
    
    # Find SVG icon
    svg_path = find_svg_icon()
    if not svg_path:
        return False
    
    print(f"📄 Found SVG icon: {svg_path}")
    
    # Define required sizes
    sizes = [16, 32, 48, 64, 128, 256, 512]
    
    # Render PNG files at different sizes
    png_paths = []
    for size in sizes:
        png_path = render_svg_to_png(svg_path, size)
        if png_path and png_path.exists():
            png_paths.append(png_path)
    
    if not png_paths:
        print("❌ No PNG files were generated successfully")
        return False
    
    print(f"✅ Generated {len(png_paths)} PNG files")
    
    # Generate ICO file (Windows)
    script_dir = get_script_dir()
    ico_path = script_dir / 'src' / 'assets' / 'icon.ico'
    ico_success = create_ico_file(png_paths, ico_path)
    
    # Generate ICNS file (macOS)
    icns_path = script_dir / 'src' / 'assets' / 'icon.icns'
    icns_success = create_icns_file(png_paths, icns_path)
    
    # Summary
    print("\n" + "=" * 40)
    print("Icon Generation Summary:")
    print(f"  SVG source: {svg_path}")
    print(f"  PNG files: {len(png_paths)} generated")
    print(f"  ICO file: {'✅' if ico_success else '❌'} {ico_path}")
    print(f"  ICNS file: {'✅' if icns_success else '❌'} {icns_path}")
    
    return ico_success or icns_success

def clean_generated_files():
    """Clean up generated PNG files"""
    print("🧹 Cleaning up generated PNG files...")
    
    script_dir = get_script_dir()
    cleaned_count = 0
    
    for size in [16, 32, 48, 64, 128, 256, 512]:
        png_path = script_dir / f'icon_{size}.png'
        if png_path.exists():
            png_path.unlink()
            cleaned_count += 1
    
    print(f"✅ Cleaned {cleaned_count} PNG files")

def main():
    parser = argparse.ArgumentParser(description='Icon generation script for Omneva Media Player')
    parser.add_argument('--clean', action='store_true', help='Clean up generated PNG files')
    parser.add_argument('--svg', help='Path to SVG icon file (auto-detect if not specified)')
    
    args = parser.parse_args()
    
    if args.clean:
        return clean_generated_files()
    else:
        return generate_icons()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
