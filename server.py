from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import easyocr
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import logging
import cv2
from scipy.ndimage import rotate
import math

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize EasyOCR with additional parameters
print("Initializing EasyOCR...")
reader = easyocr.Reader(
    ['en'],
    recog_network='english_g2',  # Use more accurate model
    gpu=True  # Enable GPU if available
)
print("EasyOCR initialized successfully")

def detect_text_angle(image_array):
    """Detect text angle for rotation correction"""
    try:
        # Convert to grayscale if needed
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_array

        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Use Hough Transform to detect lines
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is not None:
            angles = []
            for rho, theta in lines[:, 0]:
                angle = np.degrees(theta)
                if angle < 45:
                    angles.append(angle)
                elif angle > 135:
                    angles.append(angle - 180)
            
            if angles:
                median_angle = np.median(angles)
                return -median_angle if abs(median_angle) > 0.5 else 0
                
        return 0
    except Exception as e:
        logger.warning(f"Error in angle detection: {str(e)}")
        return 0

def enhance_image_quality(img):
    """Apply various image enhancement techniques"""
    try:
        # Convert to PIL Image if needed
        if isinstance(img, np.ndarray):
            img = Image.fromarray(img)

        # Apply multiple enhancement steps
        # Sharpen the image
        img = img.filter(ImageFilter.SHARPEN)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Enhance sharpness again
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)
        
        return img
    except Exception as e:
        logger.error(f"Error in image enhancement: {str(e)}")
        return img

def remove_noise(img_array):
    """Remove noise from image"""
    try:
        # Apply bilateral filter to remove noise while preserving edges
        denoised = cv2.bilateralFilter(img_array, 9, 75, 75)
        
        # Apply median blur to remove salt-and-pepper noise
        denoised = cv2.medianBlur(denoised, 3)
        
        return denoised
    except Exception as e:
        logger.error(f"Error in noise removal: {str(e)}")
        return img_array

def preprocess_image(img):
    """Enhanced preprocessing pipeline"""
    try:
        # Convert to numpy array if needed
        if isinstance(img, Image.Image):
            img_array = np.array(img)
        else:
            img_array = img

        # Detect and correct text angle
        angle = detect_text_angle(img_array)
        if angle != 0:
            img_array = rotate(img_array, angle, reshape=False)

        # Remove noise
        img_array = remove_noise(img_array)
        
        # Convert to grayscale if not already
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11,
            2
        )

        # Clean up using morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Invert back
        binary = cv2.bitwise_not(binary)
        
        return Image.fromarray(binary)
    except Exception as e:
        logger.error(f"Error in preprocessing: {str(e)}")
        return img

def strokes_to_image(strokes, grid_size=40):
    """Enhanced stroke to image conversion"""
    try:
        # Create a high-resolution white image
        img = Image.new('RGB', (1600, 1200), 'white')  # Doubled resolution
        draw = ImageDraw.Draw(img)
        
        # Scale up strokes for higher resolution
        scaled_strokes = [[(p[0]*2, p[1]*2) for p in stroke] for stroke in strokes]
        
        # Draw each stroke with smoother lines
        for stroke in scaled_strokes:
            if len(stroke) > 1:
                # Draw multiple passes for smoother lines
                for offset in [-1, 0, 1]:
                    for i in range(len(stroke)-1):
                        x1, y1 = stroke[i]
                        x2, y2 = stroke[i+1]
                        draw.line([(x1, y1+offset), (x2, y2+offset)], 
                                fill='black', 
                                width=4)  # Thicker lines for better recognition
        
        # Resize with high-quality downsampling
        img = img.resize((400, 300), Image.Resampling.LANCZOS)
        
        # Enhance image quality
        img = enhance_image_quality(img)
        
        # Apply preprocessing
        img = preprocess_image(img)
        
        return img
    except Exception as e:
        logger.error(f"Error in strokes_to_image: {str(e)}")
        raise

@app.route('/recognize', methods=['POST'])
def recognize_text():
    try:
        data = request.json
        logger.debug(f"Received data: {data}")
        
        strokes = data.get('strokes', [])
        grid_size = data.get('gridSize', 40)
        
        if not strokes:
            return jsonify({'error': 'No strokes provided'}), 400
        
        # Convert strokes to image with enhanced processing
        img = strokes_to_image(strokes, grid_size)
        
        # Save preprocessed image for debugging (optional)
        # img.save('debug_preprocessed.png')
        
        # Recognize text with optimized parameters
        logger.debug("Starting text recognition")
        results = reader.readtext(
            np.array(img),
            paragraph=True,
            decoder='beamsearch',
            beamWidth=10,
            batch_size=1,
            workers=1,
            contrast_ths=0.3,
            adjust_contrast=0.5,
            text_threshold=0.7,
            low_text=0.4,
            link_threshold=0.4,
            mag_ratio=2.0,
            slope_ths=0.1,
            ycenter_ths=0.5,
            height_ths=0.5,
            width_ths=0.5,
            add_margin=0.1,
            allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?-() '
        )
        
        logger.debug(f"Recognition results: {results}")
        
        # Process and clean recognized text
        if results:
            # Combine results and clean text
            text = ' '.join([result[1] for result in results])
            # Remove extra spaces and normalize punctuation
            text = ' '.join(text.split())
            text = text.replace(' ,', ',').replace(' .', '.')
            logger.info(f"Recognized text: {text}")
            return jsonify({'text': text})
        else:
            return jsonify({'text': 'No text detected'})
    
    except Exception as e:
        logger.error(f"Error in recognize_text: {str(e)}")
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting AI Whiteboard server...")
    app.run(debug=True)