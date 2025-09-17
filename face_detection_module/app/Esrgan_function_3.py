import torch
import cv2
import numpy as np
from pathlib import Path
from collections import OrderedDict
import os
from basicsr.archs.rrdbnet_arch import RRDBNet
import gc
import PIL
class ESRGANUpscaler:
    def __init__(self, model_path):
        """
        ESRGAN upscaler for image enhancement.
        
        Args:
            model_path: Path to the ESRGAN model weights
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        # Load the model weights
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Load and examine the model structure
        checkpoint = torch.load(model_path, map_location=self.device)
        if isinstance(checkpoint, dict):
            print(f"Model contains keys: {list(checkpoint.keys())}")
            # Find the appropriate weights key
            if 'params_ema' in checkpoint:
                state_dict = checkpoint['params_ema']
                print("Using params_ema for weights")
            elif 'params' in checkpoint:
                state_dict = checkpoint['params']
                print("Using params for weights")
            else:
                # Try to find a key that looks like a state dict
                for key in checkpoint.keys():
                    if isinstance(checkpoint[key], dict) or (isinstance(checkpoint[key], OrderedDict)):
                        state_dict = checkpoint[key]
                        print(f"Using {key} for weights")
                        break
                else:
                    state_dict = checkpoint
                    print("Using entire checkpoint as weights")
        else:
            state_dict = checkpoint
            print("Using entire checkpoint as weights")
        
        # Define the RRDBNet model
        try:
           
            self.model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            print("Using RRDBNet architecture from basicsr")
        except ImportError:
            raise ImportError("The 'basicsr' module is required for ESRGAN model but was not found.")
        
        # Try to load state dict
        try:
            # Sometimes we need to remove the 'module.' prefix
            new_state_dict = OrderedDict()
            for k, v in state_dict.items():
                name = k
                if k.startswith('module.'):
                    name = k[7:]  # remove 'module.' prefix
                new_state_dict[name] = v
            
            # Try loading with strict=False to handle missing keys
            self.model.load_state_dict(new_state_dict, strict=False)
            print("Model weights loaded successfully (with potential missing keys)")
        except Exception as e:
            print(f"Warning: Could not load state dict properly: {e}")
            print("Continuing with uninitialized model")
        
        # Move model to device and eval mode
        self.model.to(self.device)
        self.model.eval()
        
        # Set to half precision if using GPU
        self.half = torch.cuda.is_available()
        if self.half:
            self.model = self.model.half()

    def upscale(self, img, outscale=3):
        """
        Upscale the input image using ESRGAN model.
        
        Args:
            img: Input BGR image (numpy array)
            outscale: Output scale factor
            
        Returns:
            Upscaled image as numpy array
        """
        # Convert BGR to RGB (because the model expects RGB input)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Normalize to [0, 1]
        img_rgb = img_rgb.astype(np.float32) / 255.0
        
        # HWC to NCHW (change from height, width, channels to channels, height, width)
        img_tensor = torch.from_numpy(np.transpose(img_rgb, (2, 0, 1))).unsqueeze(0)
        img_tensor = img_tensor.to(self.device)
        if self.half:
            img_tensor = img_tensor.half()
        
        # Inference (use the model to upscale by a fixed factor of 4)
        with torch.no_grad():
            try:
                output = self.model(img_tensor)
            except Exception as e:
                print(f"Inference error: {e}")
                raise e
        
        # Convert back to numpy array (HWC format)
        output = output.squeeze().float().cpu().numpy()
        output = np.transpose(output, (1, 2, 0))
        
        # Clip to [0, 1] and convert to 8-bit (ensure the values are in the proper range)
        output = np.clip(output, 0, 1) * 255.0
        output = output.astype(np.uint8)
        
        # Convert back to BGR (because OpenCV expects BGR format for saving and displaying)
        output_bgr = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)
        
        # Apply resizing with the desired outscale factor (after model's 4x upscale)
        h, w = output_bgr.shape[:2]
        output_bgr_resized = cv2.resize(output_bgr, (w * outscale // 4, h * outscale // 4), interpolation=cv2.INTER_CUBIC)
        
        return output_bgr_resized

    def save_upscaled_image(self, img, input_image_path, outscale=3, output_folder="upscaled_images"):
        """
        Save the upscaled image to a new directory created in the current folder.
        
        Args:
            img: The upscaled image (numpy array)
            input_image_path: Path to the original image
            outscale: Output scale factor
            output_folder: Directory where the image will be saved
            
        Returns:
            Path to the saved image
        """
        # Create the output folder if it doesn't exist
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # Get the base name of the input image (without extension)
        base_name = Path(input_image_path).stem
        
        # Construct the new file name dynamically
        output_image_name = f"upscaled_image_{base_name}.png"
        
        # Save the upscaled image
        output_image_path = os.path.join(output_folder, output_image_name)
        cv2.imwrite(output_image_path, img)
        
        print(f"Image saved to {output_image_path}")
        return output_image_path

def upscale_image(image):
    model_path = "./RealESRGAN_x4plus.pth"
    
    # Create the upscaler instance
    upscaler = ESRGANUpscaler(model_path)
    try:
        if isinstance(image, str):
            image = cv2.imread(image)  # If the image is a file path, read it into a NumPy array
        elif isinstance(image, PIL.Image.Image):
            image = np.array(image)  # Convert a PIL image to NumPy array
        
        # Check if the image was loaded properly
        if image is None:
            raise ValueError("Image not loaded properly. Please check the image path or format.")
        
        # Upscale the image
        print("Upscaling image...")
        upscaled_img = upscaler.upscale(image, outscale=2)
        # Cleanup: Delete the model after use
        del upscaler  # Delete the object to free up memory
        gc.collect()  # Force garbage collection
    except Exception as e:
        print(f'upscaling error: {e}')
    print('upscaling successfull....')
    upscaled_img = PIL.Image.fromarray(upscaled_img)  # Convert NumPy array to PIL Image

    return upscaled_img  # Return the upscaled image


# Main execution
if __name__ == "__main__":
    # Input and output paths
    # input_image_path = "/home/afsara/Code/meta_glass02/meta-glass/backend/saved_images/949bc3ec5b104118adc17b63dccf087b.png"
    input_image_path = "../IMG_4551.JPG"
    
    # Load the input image
    image = cv2.imread(input_image_path)
    if image is None:
        raise ValueError(f"Error: Unable to load image at path {input_image_path}")
    upscaled_img = upscale_image(image=image)
   
    # # Print original dimensions
    # original_size = image.shape
    # print(f"Original Image Size: {original_size} (HxWxC)")
    
    # # Initialize our ESRGAN upscaler
    # model_path = "/workspace/Reverse-Face-Search/telegram_bot/RealESRGAN_x4plus.pth"
    # print(f"Loading model from {model_path}...")
    # try:
    #     upscaler = ESRGANUpscaler(model_path)
        
    #     # Upscale the image
    #     print("Upscaling image...")
    #     upscaled_img = upscaler.upscale(image, outscale=2)
        
    #     # Get upscaled dimensions
    #     upscaled_size = upscaled_img.shape
    #     print(f"Upscaled Image Size: {upscaled_size} (HxWxC)")
        
    #     # Save the result
    #     saved_image_path = upscaler.save_upscaled_image(upscaled_img, input_image_path, outscale=3)
    #     print(f"Upscaling complete! Saved as {saved_image_path}")
    #     print(f"Upscaling factor: {upscaled_size[1]/original_size[1]:.2f}x width, {upscaled_size[0]/original_size[0]:.2f}x height")
    
    # except Exception as e:
    #     print(f"Error during upscaling: {e}")
