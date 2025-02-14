import pygame
import numpy as np
from PIL import Image
import easyocr
import torch
import time

class SmartWhiteboard:
    def __init__(self, width=800, height=600):
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
        self.RED = (255, 0, 0)
        
        # Drawing parameters
        self.drawing = False
        self.current_stroke = []
        self.strokes = []  # Store all strokes
        
        # Initialize EasyOCR
        print("Initializing EasyOCR (this may take a moment)...")
        self.reader = easyocr.Reader(['en'])
        
        # Font for displaying text
        self.font = pygame.font.Font(None, 36)
        
        # Store recognized text
        self.recognized_texts = []
        
        # Recognition cooldown
        self.last_recognition_time = time.time()
        self.recognition_cooldown = 1.0  # seconds
        
    def stroke_to_image(self, stroke):
        """Convert stroke to PIL Image for recognition"""
        if len(stroke) < 2:
            return None
            
        # Create a white image
        img = Image.new('RGB', (200, 200), 'white')
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        
        # Scale points to fit in image
        points = np.array(stroke)
        min_x, min_y = points.min(axis=0)
        max_x, max_y = points.max(axis=0)
        
        width = max_x - min_x
        height = max_y - min_y
        if width == 0 or height == 0:
            return None
            
        scale = min(180 / width, 180 / height)
        
        # Normalize points
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
        """Recognize text from the image using EasyOCR"""
        try:
            results = self.reader.readtext(np.array(image))
            if results:
                return results[0][1]  # Return the recognized text
            return None
        except Exception as e:
            print(f"Recognition error: {e}")
            return None
    
    def run(self):
        running = True
        self.screen.fill(self.WHITE)
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.drawing = True
                    self.current_stroke = []
                    pos = pygame.mouse.get_pos()
                    self.current_stroke.append(pos)
                    
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.drawing = False
                    if self.current_stroke:
                        # Process the stroke for recognition
                        img = self.stroke_to_image(self.current_stroke)
                        if img:
                            current_time = time.time()
                            if current_time - self.last_recognition_time > self.recognition_cooldown:
                                text = self.recognize_text(img)
                                if text:
                                    # Calculate average position of stroke
                                    points = np.array(self.current_stroke)
                                    pos = points.mean(axis=0)
                                    self.recognized_texts.append({
                                        'text': text,
                                        'position': pos,
                                        'color': self.BLACK
                                    })
                                    # Clear the stroke area
                                    self.screen.fill(self.WHITE)
                                    # Redraw all recognized text
                                    for text_obj in self.recognized_texts:
                                        text_surface = self.font.render(
                                            text_obj['text'], True, text_obj['color'])
                                        text_rect = text_surface.get_rect(
                                            center=text_obj['position'])
                                        self.screen.blit(text_surface, text_rect)
                                self.last_recognition_time = current_time
                    self.current_stroke = []
                    
                elif event.type == pygame.MOUSEMOTION and self.drawing:
                    pos = pygame.mouse.get_pos()
                    self.current_stroke.append(pos)
                    if len(self.current_stroke) > 1:
                        pygame.draw.lines(self.screen, self.BLUE, False, 
                                       self.current_stroke[-2:], 2)
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_c:  # Clear screen
                        self.screen.fill(self.WHITE)
                        self.recognized_texts = []
                        self.current_stroke = []
                    
            pygame.display.flip()
            
        pygame.quit()

if __name__ == "__main__":
    whiteboard = SmartWhiteboard()
    whiteboard.run()