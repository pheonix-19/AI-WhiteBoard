import pygame
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tensorflow as tf
import cv2

class SmartWhiteboard:
    def __init__(self, width=1280, height=720):
        # Initialize Pygame
        pygame.init()
        
        # Set up display
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Smart Whiteboard")
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.BLUE = (0, 0, 255)
        
        # Drawing parameters
        self.drawing = False
        self.points = []
        self.all_strokes = []
        self.current_stroke = []
        
        # Initialize text recognition (using Python-tesseract for handwriting recognition)
        import pytesseract
        self.ocr = pytesseract
        
        # Font for displaying recognized text
        self.font = pygame.font.Font(None, 36)
        
        # Store recognized text and their positions
        self.recognized_texts = []
        
        # Recognition cooldown
        self.last_recognition_time = 0
        self.recognition_cooldown = 1.0  # seconds
        
    def process_stroke(self, stroke):
        """Convert stroke to image for recognition"""
        # Create a blank image
        img = Image.new('L', (200, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Normalize stroke points
        if len(stroke) < 2:
            return None
            
        # Scale points to fit in image
        points = np.array(stroke)
        min_x, min_y = points.min(axis=0)
        max_x, max_y = points.max(axis=0)
        
        width = max_x - min_x
        height = max_y - min_y
        scale = min(180 / width, 180 / height) if width > 0 and height > 0 else 1
        
        normalized_points = []
        for point in stroke:
            x = 10 + (point[0] - min_x) * scale
            y = 10 + (point[1] - min_y) * scale
            normalized_points.append((x, y))
        
        # Draw the stroke
        if len(normalized_points) > 1:
            draw.line(normalized_points, fill='black', width=3)
        
        return img
        
    def recognize_text(self, image):
        """Recognize text from the processed image"""
        # Convert PIL image to OpenCV format for preprocessing
        img_cv = np.array(image)
        
        # Preprocess the image
        _, binary = cv2.threshold(img_cv, 128, 255, cv2.THRESH_BINARY_INV)
        
        # Perform OCR
        try:
            text = self.ocr.image_to_string(binary, config='--psm 10')
            text = text.strip()
            return text if text else None
        except Exception as e:
            print(f"Recognition error: {e}")
            return None
            
    def run(self):
        """Main loop for the whiteboard application"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.drawing = True
                    self.current_stroke = []
                    
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.drawing = False
                    if self.current_stroke:
                        # Process the completed stroke
                        img = self.process_stroke(self.current_stroke)
                        if img:
                            text = self.recognize_text(img)
                            if text:
                                # Get the average position of the stroke
                                points = np.array(self.current_stroke)
                                pos = points.mean(axis=0)
                                self.recognized_texts.append({
                                    'text': text,
                                    'position': pos,
                                    'color': self.BLACK
                                })
                        self.current_stroke = []
                        
                elif event.type == pygame.MOUSEMOTION and self.drawing:
                    pos = pygame.mouse.get_pos()
                    self.current_stroke.append(pos)
                    
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_c:  # Clear screen
                        self.recognized_texts = []
                        self.current_stroke = []
                        
            # Draw background
            self.screen.fill(self.WHITE)
            
            # Draw current stroke
            if len(self.current_stroke) > 1:
                pygame.draw.lines(self.screen, self.BLUE, False, self.current_stroke, 2)
                
            # Draw recognized text
            for text_obj in self.recognized_texts:
                text_surface = self.font.render(text_obj['text'], True, text_obj['color'])
                text_rect = text_surface.get_rect(center=text_obj['position'])
                self.screen.blit(text_surface, text_rect)
                
            pygame.display.flip()
            
        pygame.quit()

if __name__ == "__main__":
    whiteboard = SmartWhiteboard()
    whiteboard.run()
    

    