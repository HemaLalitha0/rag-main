import os
from PIL import Image

src_dir = r"C:\Users\lenovo\.gemini\antigravity-ide\brain\284fe077-f934-40f0-ad69-ef1a1bb5f269"
out_dir = r"C:\Users\lenovo\Downloads\Insta_Ready"

if not os.path.exists(out_dir):
    os.makedirs(out_dir)

# Target Instagram Square size
TARGET_SIZE = 1080

files = [
    "carousel_slide1_cover_1791444383571.png",
    "carousel_slide2_basic_idea_1791444413552.png",
    "carousel_slide3_diff1_2_1791444446774.png",
    "carousel_slide4_diff3_4_1791444475381.png",
    "carousel_slide5_diff5_when_1791444740717.png",
    "carousel_slide6_cta_30hrs_1791454620610.png"
]

for file in files:
    src_path = os.path.join(src_dir, file)
    if not os.path.exists(src_path):
        continue
    
    img = Image.open(src_path).convert("RGBA")
    
    # Get background color from the top-left pixel
    bg_color = img.getpixel((0, 0))
    
    # Calculate new size while keeping aspect ratio
    img_ratio = img.width / img.height
    
    if img_ratio > 1:
        # Wider than tall
        new_w = TARGET_SIZE
        new_h = int(TARGET_SIZE / img_ratio)
    else:
        # Taller than wide
        new_h = TARGET_SIZE
        new_w = int(TARGET_SIZE * img_ratio)
        
    resized_img = img.resize((new_w, new_h), Image.LANCZOS)
    
    # Create the new 1080x1080 canvas with the background color
    new_canvas = Image.new("RGBA", (TARGET_SIZE, TARGET_SIZE), bg_color)
    
    # Calculate centered coordinates
    x = (TARGET_SIZE - new_w) // 2
    y = (TARGET_SIZE - new_h) // 2
    
    # Paste the resized image
    new_canvas.paste(resized_img, (x, y), resized_img)
    
    # Save the output
    out_name = file.split("_179")[0] + "_insta_ready.png"
    out_path = os.path.join(out_dir, out_name)
    new_canvas.save(out_path, "PNG")
    print(f"Saved: {out_path}")
