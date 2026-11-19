import os
from PIL import Image, ImageDraw, ImageFont

img_dir = r"C:\Users\lenovo\Downloads\Insta_Ready"

files = [f for f in os.listdir(img_dir) if f.endswith(".png")]

bg_color = (5, 10, 30, 255)

try:
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 36)
except:
    font = ImageFont.load_default()

for file in files:
    path = os.path.join(img_dir, file)
    img = Image.open(path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    # Define rectangle area for top right logo (approximate)
    # 1080x1080 image. Let's cover from x=750 to 1080, and y=0 to 150.
    # We might need to cover a bit more just in case. Let's do x=700 to 1080, y=0 to 150
    draw.rectangle([700, 0, 1080, 150], fill=bg_color)
    
    # Add text "Generative AI"
    text = "Generative AI"
    
    # Get text size to right-align it
    # For newer Pillow versions, textbbox is preferred
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        text_width = 200
        text_height = 40
        
    # Position: right aligned with a margin of 50px, top margin of 50px
    x = 1080 - text_width - 50
    y = 50
    
    # Text color: probably white or light gray to match the design. Let's use light gray
    text_color = (200, 200, 200, 255)
    
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Save over the same file
    img.save(path, "PNG")
    print(f"Processed {file}")
