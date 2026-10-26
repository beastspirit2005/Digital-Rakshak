import os
import numpy as np
from PIL import Image, ImageFilter, ImageOps
import scipy.ndimage as ndi

def main():
    src_path = r"C:\Users\Lenovo\.gemini\antigravity\brain\deb6f069-e106-4283-941c-75a661af5236\logo-reference.jpg"
    out_dir = r"c:\Users\Lenovo\Desktop\DigitalRakshak\frontend\public\brand"
    os.makedirs(out_dir, exist_ok=True)

    img = Image.open(src_path).convert("RGB")
    arr = np.array(img, dtype=np.float32)

    # 1. SHIELD EMBLEM EXTRACTION
    # Shield region in 1024x1024
    # The shield outer rim brightness is high (> 40), while outside is dark (< 15).
    # Inside the shield has the dark blue map plate and the white/tricolor R.
    # We want a mask that covers the entire shield (rim + inside).
    
    # Let's detect the shield outer rim
    brightness = arr.max(axis=2)
    # Threshold for shield rim is around 30-35
    rim_or_content = brightness > 30

    # Outside bounding box of shield is definitely outside
    # Y: 180 to 632, X: 300 to 704
    # Let's create an initial mask
    shield_bbox_mask = np.zeros_like(rim_or_content, dtype=bool)
    shield_bbox_mask[175:636, 295:710] = True
    
    # Content inside shield bbox
    shield_inside = rim_or_content & shield_bbox_mask

    # Flood fill holes inside the shield boundary so the inner map plate is 100% solid
    filled_shield = ndi.binary_fill_holes(shield_inside)

    # Clean up any stray noise outside using binary opening/closing
    struct = ndi.generate_binary_structure(2, 2)
    clean_mask = ndi.binary_opening(filled_shield, structure=struct, iterations=1)
    clean_mask = ndi.binary_closing(clean_mask, structure=struct, iterations=3)
    clean_mask = ndi.binary_fill_holes(clean_mask)

    # Convert to smooth float alpha mask with anti-aliasing (slight Gaussian blur on edge)
    alpha_img = Image.fromarray((clean_mask * 255).astype(np.uint8), mode="L")
    alpha_smooth = alpha_img.filter(ImageFilter.GaussianBlur(radius=0.8))

    # Create RGBA shield image
    rgba_img = img.convert("RGBA")
    rgba_img.putalpha(alpha_smooth)

    # Crop to shield bounding box
    # Find bounding box of alpha
    alpha_arr = np.array(alpha_smooth)
    y_idx, x_idx = np.where(alpha_arr > 10)
    ymin, ymax = y_idx.min(), y_idx.max()
    xmin, xmax = x_idx.min(), x_idx.max()

    shield_cropped = rgba_img.crop((xmin, ymin, xmax + 1, ymax + 1))
    
    # Place on square 512x512 with subtle aesthetic margin (~8%)
    square_size = 512
    margin = 32
    target_dim = square_size - (margin * 2)
    
    # Scale keeping aspect ratio
    w, h = shield_cropped.size
    ratio = min(target_dim / w, target_dim / h)
    new_w, new_h = int(w * ratio), int(h * ratio)
    shield_resized = shield_cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas_512 = Image.new("RGBA", (square_size, square_size), (0, 0, 0, 0))
    paste_x = (square_size - new_w) // 2
    paste_y = (square_size - new_h) // 2
    canvas_512.paste(shield_resized, (paste_x, paste_y), shield_resized)

    # Save logo-shield.png (512x512)
    shield_512_path = os.path.join(out_dir, "logo-shield.png")
    canvas_512.save(shield_512_path, "PNG", optimize=True)
    print("Saved:", shield_512_path)

    # Save smaller sizes: 256, 128, 64, 32
    for sz in [256, 128, 64, 32]:
        p = os.path.join(out_dir, f"logo-shield-{sz}.png")
        canvas_512.resize((sz, sz), Image.Resampling.LANCZOS).save(p, "PNG", optimize=True)
        print(f"Saved: {p}")

    # 2. GENERATE MULTI-RESOLUTION FAVICON.ICO
    # Favicon needs sizes: 16x16, 32x32, 48x48
    ico_path = r"c:\Users\Lenovo\Desktop\DigitalRakshak\frontend\src\app\favicon.ico"
    # Also save in public/favicon.ico
    public_ico_path = r"c:\Users\Lenovo\Desktop\DigitalRakshak\frontend\public\favicon.ico"
    
    # Favicon benefits from slightly tighter crop so it's readable at 16x16
    fav_target = 512 - 16
    ratio_fav = min(fav_target / w, fav_target / h)
    fw, fh = int(w * ratio_fav), int(h * ratio_fav)
    fav_resized = shield_cropped.resize((fw, fh), Image.Resampling.LANCZOS)
    fav_canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    fav_canvas.paste(fav_resized, ((512 - fw) // 2, (512 - fh) // 2), fav_resized)
    
    fav_canvas.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)]
    )
    fav_canvas.save(
        public_ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)]
    )
    print("Updated favicons:", ico_path, public_ico_path)

    # 3. APPLE TOUCH ICON (180x180)
    # Apple touch icon looks best with dark background plate #08131A and rounded aesthetic
    apple_icon = Image.new("RGBA", (180, 180), (8, 19, 26, 255))
    apple_shield = canvas_512.resize((150, 150), Image.Resampling.LANCZOS)
    apple_icon.paste(apple_shield, (15, 15), apple_shield)
    apple_path = r"c:\Users\Lenovo\Desktop\DigitalRakshak\frontend\public\apple-touch-icon.png"
    apple_icon.save(apple_path, "PNG", optimize=True)
    print("Saved apple-touch-icon:", apple_path)

    # 4. FULL LOGO TRANSPARENT (SHIELD + TEXT)
    # The text is from Y=650 to 780, X=80 to 945
    # Let's extract full logo with clean transparent background
    full_mask_raw = np.zeros((1024, 1024), dtype=bool)
    # Shield part is clean_mask
    full_mask_raw |= clean_mask
    
    # Text part: brightness thresholding
    text_region = (brightness > 28) & (np.arange(1024)[:, None] >= 635) & (np.arange(1024)[:, None] <= 785)
    full_mask_raw |= text_region
    
    full_alpha = Image.fromarray((full_mask_raw * 255).astype(np.uint8), mode="L")
    full_alpha = full_alpha.filter(ImageFilter.GaussianBlur(radius=0.6))
    
    full_rgba = img.convert("RGBA")
    full_rgba.putalpha(full_alpha)
    
    # Find full bounding box
    fy_idx, fx_idx = np.where(np.array(full_alpha) > 10)
    full_cropped = full_rgba.crop((fx_idx.min(), fy_idx.min(), fx_idx.max() + 1, fy_idx.max() + 1))
    
    full_logo_path = os.path.join(out_dir, "logo-full.png")
    full_cropped.save(full_logo_path, "PNG", optimize=True)
    print("Saved full logo:", full_logo_path)

    # 5. OPEN GRAPH BANNER (1200x630)
    # Professional social preview banner
    og_canvas = Image.new("RGB", (1200, 630), (8, 19, 26)) # #08131A
    
    # Center the full logo in the canvas
    fw, fh = full_cropped.size
    # Desired height ~480
    og_scale = min(500 / fh, 900 / fw)
    og_w, og_h = int(fw * og_scale), int(fh * og_scale)
    full_og = full_cropped.resize((og_w, og_h), Image.Resampling.LANCZOS)
    
    og_x = (1200 - og_w) // 2
    og_y = (630 - og_h) // 2
    og_canvas.paste(full_og, (og_x, og_y), full_og)
    
    og_path = os.path.join(out_dir, "og-image.png")
    og_canvas.save(og_path, "PNG", optimize=True)
    print("Saved OG image:", og_path)

if __name__ == "__main__":
    main()
