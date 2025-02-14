from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import easyocr
import io
from PIL import Image, ImageDraw

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize EasyOCR
reader = easyocr.Reader(['en'])

def strokes_to_image(strokes):
    """Convert strokes to PIL Image"""
    # Create a white image
    img = Image.new('RGB', (800, 600), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw each stroke
    for stroke in strokes:
        if len(stroke) > 1:
            draw.line(stroke, fill='black', width=3)
    
    return img

@app.route('/recognize', methods=['POST'])
def recognize_text():
    try:
        # Get strokes data from request
        data = request.json
        strokes = data.get('strokes', [])
        
        if not strokes:
            return jsonify({'error': 'No strokes provided'}), 400
        
        # Convert strokes to image
        img = strokes_to_image(strokes)
        
        # Recognize text
        results = reader.readtext(np.array(img))
        
        # Extract recognized text
        text = ' '.join([result[1] for result in results]) if results else ''
        
        return jsonify({'text': text})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting AI Whiteboard server...")
    app.run(debug=True)