#!/usr/bin/env python3
"""
Generate simple placeholder icons for the Hodhod Chrome extension.
Requires: pillow (pip install pillow)
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_gradient_icon(size, filename):
    """Create a simple gradient icon with the bird emoji."""
    # Create image with gradient background
    img = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    for i in range(size):
        # Gradient from #667eea to #764ba2
        r = int(102 + (118 - 102) * i / size)
        g = int(126 + (75 - 126) * i / size)
        b = int(234 + (162 - 234) * i / size)
        draw.line([(0, i), (size, i)], fill=(r, g, b))

    # Draw a circle
    margin = size // 5
    circle_color = (255, 255, 255, 200)
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=None,
        outline='white',
        width=max(2, size // 32)
    )

    # Try to add text
    try:
        # Try different font sizes
        font_size = int(size * 0.5)
        # Use a system font that supports emojis
        try:
            # Mac
            font = ImageFont.truetype(
                "/System/Library/Fonts/Apple Color Emoji.ttc", font_size
            )
        except:
            try:
                # Windows
                font = ImageFont.truetype("seguiemj.ttf", font_size)
            except:
                # Linux or fallback
                try:
                    font = ImageFont.truetype(
                        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
                        font_size
                    )
                except:
                    font = ImageFont.load_default()

        # Draw the hodhod emoji
        text = "🐦"
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center the text
        x = (size - text_width) // 2
        y = (size - text_height) // 2

        draw.text((x, y), text, font=font, fill='white')
    except Exception as e:
        print(f"Warning: Could not add emoji to icon: {e}")
        # Draw a simple "H" instead
        font_size = int(size * 0.6)
        try:
            font = ImageFont.truetype("Arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        text = "H"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        draw.text((x, y), text, font=font, fill='white')

    # Save the icon
    img.save(filename, 'PNG')
    print(f"Created {filename} ({size}x{size})")


def main():
    """Generate all three icon sizes."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(script_dir, 'icons')

    # Create icons directory if it doesn't exist
    os.makedirs(icons_dir, exist_ok=True)

    # Generate icons
    create_gradient_icon(16, os.path.join(icons_dir, 'icon16.png'))
    create_gradient_icon(48, os.path.join(icons_dir, 'icon48.png'))
    create_gradient_icon(128, os.path.join(icons_dir, 'icon128.png'))

    print("\n✅ Icons generated successfully!")
    print(f"📁 Location: {icons_dir}")
    print("\nNext steps:")
    print("1. Go to chrome://extensions/")
    print("2. Enable 'Developer mode'")
    print("3. Click 'Load unpacked'")
    print(f"4. Select: {script_dir}")


if __name__ == '__main__':
    try:
        main()
    except ImportError:
        print("❌ Error: Pillow is not installed")
        print("\nInstall it with:")
        print("  pip install pillow")
        print("or")
        print("  uv pip install pillow")
