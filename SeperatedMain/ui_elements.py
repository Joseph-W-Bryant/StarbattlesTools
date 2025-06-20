# ui_elements.py
# Description: Contains classes for UI elements like buttons.

import pygame

class Button:
    """A class to create and manage clickable buttons in the UI."""
    def __init__(self, rect, text, action_id, font, colors):
        """
        Initializes a Button object.
        
        Args:
            rect (pygame.Rect): The position and dimensions of the button.
            text (str): The text to display on the button.
            action_id (str): A unique identifier for the button's action (e.g., 'new', 'back').
            font (pygame.font.Font): The font to use for the button text.
            colors (dict): A dictionary of colors for different states 
                           (e.g., 'base', 'hover', 'disabled_bg', 'disabled_fg', 'text').
        """
        self.rect = rect
        self.text = text
        self.action_id = action_id
        self.font = font
        self.colors = colors
        
        self.is_hovered = False
        self.is_disabled = False

    def handle_event(self, event):
        """
        Handles mouse events for the button.
        
        Args:
            event (pygame.event.Event): The Pygame event to process.
            
        Returns:
            str or None: The action_id if the button is clicked, otherwise None.
        """
        self.is_hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered and not self.is_disabled:
            return self.action_id
        return None

    def draw(self, screen):
        """Draws the button on the screen."""
        if self.is_disabled:
            bg_color = self.colors['disabled_bg']
            text_color = self.colors['disabled_fg']
        else:
            bg_color = self.colors['hover'] if self.is_hovered else self.colors['base']
            text_color = self.colors['text']

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        
        text_surf = self.font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)


