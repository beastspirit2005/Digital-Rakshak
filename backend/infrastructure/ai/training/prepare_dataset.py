import os
import random
from PIL import Image, ImageDraw, ImageFont

def create_synthetic_dataset(base_dir="dataset", num_train=100, num_val=20):
    """
    Creates a synthetic dataset of dummy currency images for testing the training pipeline.
    This generates colored rectangles with text to simulate 'genuine' and 'counterfeit' notes.
    """
    
    classes = ['genuine', 'counterfeit']
    splits = {'train': num_train, 'val': num_val}
    
    print(f"Creating synthetic dataset at '{os.path.abspath(base_dir)}'...")
    
    for split, num_images in splits.items():
        for cls in classes:
            dir_path = os.path.join(base_dir, split, cls)
            os.makedirs(dir_path, exist_ok=True)
            
            for i in range(num_images):
                # Generate a dummy image
                width, height = 400, 200
                
                # Base color depends on class for the model to easily learn the difference
                # Genuine: greenish tint. Counterfeit: reddish/yellowish tint
                if cls == 'genuine':
                    bg_color = (
                        random.randint(200, 230), 
                        random.randint(220, 255), 
                        random.randint(200, 230)
                    )
                else:
                    bg_color = (
                        random.randint(230, 255), 
                        random.randint(200, 220), 
                        random.randint(200, 220)
                    )
                    
                img = Image.new('RGB', (width, height), color=bg_color)
                draw = ImageDraw.Draw(img)
                
                # Add some random noise/shapes
                for _ in range(10):
                    x0 = random.randint(0, width)
                    y0 = random.randint(0, height)
                    x1 = x0 + random.randint(10, 50)
                    y1 = y0 + random.randint(10, 50)
                    shape_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                    draw.rectangle([x0, y0, x1, y1], fill=shape_color)
                
                # Add text
                text = f"₹500 NOTE - {cls.upper()}"
                try:
                    # Try to use a default font if available, else standard
                    draw.text((50, 80), text, fill=(0, 0, 0))
                except Exception:
                    pass
                
                # Save image
                img_path = os.path.join(dir_path, f"{cls}_{i}.jpg")
                img.save(img_path)
                
    print(f"Dataset generated successfully!")
    print(f"Train images per class: {num_train}")
    print(f"Val images per class: {num_val}")
    print("You can now run 'python train_counterfeit.py'")

if __name__ == "__main__":
    create_synthetic_dataset()
