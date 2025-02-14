from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import easyocr
from PIL import Image, ImageDraw, ImageEnhance
import logging
import cv2

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize EasyOCR
print("Initializing EasyOCR...")
reader = easyocr.Reader(['en'])
print("EasyOCR initialized successfully")

def preprocess_image(img):
    """Apply preprocessing to enhance text recognition"""
    # Convert to numpy array
    img_array = np.array(img)
    
    # Convert to grayscale if not already
    if len(img_array.shape) == 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Apply adaptive thresholding
    img_array = cv2.adaptiveThreshold(
        img_array, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV,
        11,
        2
    )
    
    # Remove noise
    kernel = np.ones((2,2), np.uint8)
    img_array = cv2.morphologyEx(img_array, cv2.MORPH_CLOSE, kernel)
    
    # Invert back
    img_array = cv2.bitwise_not(img_array)
    
    return Image.fromarray(img_array)

def strokes_to_image(strokes, grid_size=40):
    """Convert strokes to PIL Image with enhanced processing"""
    try:
        # Create a white image
        img = Image.new('RGB', (800, 600), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw each stroke with thicker lines
        for stroke in strokes:
            points = [(point[0], point[1]) for point in stroke]
            if len(points) > 1:
                draw.line(points, fill='black', width=3)
        
        # Resize for better OCR performance
        img = img.resize((400, 300), Image.Resampling.LANCZOS)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Apply preprocessing
        img = preprocess_image(img)
        
        return img
    except Exception as e:
        logger.error(f"Error in strokes_to_image: {str(e)}")
        raise

@app.route('/recognize', methods=['POST'])
def recognize_text():
    try:
        # Get data from request
        data = request.json
        logger.debug(f"Received data: {data}")
        
        strokes = data.get('strokes', [])
        grid_size = data.get('gridSize', 40)
        
        if not strokes:
            return jsonify({'error': 'No strokes provided'}), 400
        
        # Convert strokes to image
        img = strokes_to_image(strokes, grid_size)
        
        # Save preprocessed image for debugging (optional)
        # img.save('debug_preprocessed.png')
        
        # Recognize text with additional parameters
        logger.debug("Starting text recognition")
        results = reader.readtext(
            np.array(img),
            paragraph=True,
            decoder='greedy',
            beamWidth=5,
            batch_size=1,
            workers=1,
            allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?-() '
        )
        logger.debug(f"Recognition results: {results}")
        
        # Extract and clean recognized text
        text = ' '.join([result[1] for result in results]) if results else ''
        text = ' '.join(text.split())  # Clean up whitespace
        logger.info(f"Recognized text: {text}")
        
        return jsonify({'text': text if text else 'No text detected'})
    
    except Exception as e:
        logger.error(f"Error in recognize_text: {str(e)}")
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting AI Whiteboard server...")
    app.run(debug=True)