# Icons

The extension needs three icon sizes:
- icon16.png (16x16)
- icon48.png (48x48)
- icon128.png (128x128)

## Quick Fix: Remove Icon References

If you want to test the extension immediately without icons, edit `manifest.json` and remove/comment out the `icons` and `action.default_icon` sections.

## Creating Icons

### Option 1: Use an online tool
1. Go to https://www.favicon-generator.org/ or similar
2. Upload any hodhod/bird image
3. Generate icons in 16x16, 48x48, and 128x128 sizes
4. Save them in this directory

### Option 2: Use this Python script

```python
from PIL import Image, ImageDraw, ImageFont

def create_icon(size, filename):
    # Create a gradient background
    img = Image.new('RGB', (size, size), '#667eea')
    draw = ImageDraw.Draw(img)

    # Draw a circle for the bird
    margin = size // 6
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill='#764ba2', outline='white', width=2)

    # Add emoji/text
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", size//2)
        draw.text((size//2, size//2), "🐦", font=font, anchor="mm")
    except:
        pass

    img.save(filename)

create_icon(16, 'icon16.png')
create_icon(48, 'icon48.png')
create_icon(128, 'icon128.png')
```

### Option 3: Use emojis as icons
1. Take a screenshot of 🐦 emoji at different sizes
2. Crop and save as icon16.png, icon48.png, icon128.png
