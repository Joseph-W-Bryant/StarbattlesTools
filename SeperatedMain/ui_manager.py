# ui_manager.py
# Description: Manages all Pygame drawing functions and the data-driven UI layout.

import pygame
import math
from ui_elements import Button

from constants import (
    GRID_AREA_WIDTH, GRID_AREA_HEIGHT, PANEL_WIDTH, WINDOW_HEIGHT, GUTTER,
    BORDER_NORMAL, BORDER_THICK, PYGAME_UNIFIED_COLORS, COLOR_GRID_LINES,
    COLOR_BLACK, COLOR_STAR, COLOR_X, COLOR_DOT, COLOR_PANEL, COLOR_BUTTON,
    COLOR_BUTTON_HOVER, COLOR_BUTTON_TEXT, COLOR_CORRECT, COLOR_INCORRECT,
    COLOR_SELECTED, COLOR_STAR_NUM, DIFFICULTY_COLORS, STATE_STAR,
    STATE_SECONDARY_MARK, PUZZLE_DEFINITIONS, COLOR_DISABLED_BUTTON, COLOR_DISABLED_TEXT
)

def get_input_from_console():
    """Minimizes the Pygame window and prompts for a puzzle string in the console."""
    pygame.display.iconify()
    input_string = input("\n--- PASTE PUZZLE STRING (or 'q' to cancel) AND PRESS ENTER ---\n> ")
    if input_string.lower() == 'q': return None
    return input_string.strip()

def get_comment_from_console():
    """Minimizes the Pygame window and prompts for a comment in the console."""
    pygame.display.iconify()
    comment = input("\n--- ENTER A COMMENT FOR THE SAVED PUZZLE (or leave blank) ---\n> ")
    return comment.strip()

def build_panel_from_layout(layout_def, fonts):
    """Constructs a list of UI element objects based on a flexible, proportional layout."""
    ui_elements = {}
    
    ideal_flowing_height = 0
    num_gaps = -1 
    
    flowing_elements = [elem for elem in layout_def if 'fixed_bottom' not in elem]
    for element_def in flowing_elements:
        ideal_flowing_height += element_def.get('ideal_height', 0)
        num_gaps += 1
            
    ideal_gap_height = 15
    ideal_flowing_height += num_gaps * ideal_gap_height
    
    bottom_buttons = [elem for elem in layout_def if 'fixed_bottom' in elem]
    total_bottom_height = sum(b.get('ideal_height', 45) + 15 for b in bottom_buttons)

    top_padding = 15
    final_buffer = 15 
    
    available_space = WINDOW_HEIGHT - top_padding - total_bottom_height - final_buffer
    scaling_factor = min(1.0, available_space / ideal_flowing_height) if ideal_flowing_height > 0 else 1.0
    
    if scaling_factor == 1.0 and num_gaps > 0:
        actual_gap_height = (available_space - (ideal_flowing_height - num_gaps * ideal_gap_height)) / num_gaps
    else:
        actual_gap_height = ideal_gap_height * scaling_factor
        
    current_y = top_padding
    h_padding = 15
    
    default_colors = {
        'base': COLOR_BUTTON, 'hover': COLOR_BUTTON_HOVER, 'text': COLOR_BUTTON_TEXT,
        'disabled_bg': COLOR_DISABLED_BUTTON, 'disabled_fg': COLOR_DISABLED_TEXT
    }

    for element_def in flowing_elements:
        elem_type = element_def['type']
        scaled_elem_height = element_def.get('ideal_height', 0) * scaling_factor
        
        if elem_type == 'button_group':
            group_width = PANEL_WIDTH - (h_padding * 2)
            current_x = h_padding
            for i, btn_def in enumerate(element_def['items']):
                btn_width = (group_width * btn_def['width_ratio']) - (5 * (len(element_def['items']) - 1))
                rect = pygame.Rect(GRID_AREA_WIDTH + current_x, current_y, btn_width, scaled_elem_height)
                font = fonts.get(btn_def.get('font'), fonts['default'])
                ui_elements[btn_def['id']] = Button(rect, btn_def['text'], btn_def['id'], font, default_colors)
                current_x += btn_width + 10
            current_y += scaled_elem_height + actual_gap_height
            
        elif elem_type == 'button':
            rect = pygame.Rect(GRID_AREA_WIDTH + h_padding, current_y, PANEL_WIDTH - (h_padding * 2), scaled_elem_height)
            ui_elements[element_def['id']] = Button(rect, element_def['text'], element_def['id'], fonts['default'], default_colors)
            current_y += scaled_elem_height + actual_gap_height

        elif elem_type == 'title':
            element_def['y_pos'] = current_y + (scaled_elem_height / 2)
            ui_elements[element_def['id']] = element_def
            current_y += scaled_elem_height + actual_gap_height

        elif elem_type == 'size_grid':
            size_buttons = {}
            s_radius, s_cols = 22, 4
            s_h_padding = (PANEL_WIDTH - (s_cols * s_radius * 2)) / (s_cols + 1)
            num_rows = 3
            v_padding = (scaled_elem_height - (num_rows * s_radius * 2)) / (num_rows -1) if num_rows > 1 else 0
            for i in range(12):
                row, col = divmod(i, s_cols)
                y_pos = current_y + (row * (s_radius * 2 + v_padding)) + s_radius
                x_pos = GRID_AREA_WIDTH + s_h_padding + col * (s_radius * 2 + s_h_padding) + s_radius
                size_buttons[i] = {'rect': pygame.Rect(x_pos - s_radius, y_pos - s_radius, s_radius * 2, s_radius * 2), 'radius': s_radius}
            ui_elements[element_def['id']] = size_buttons
            current_y += scaled_elem_height + actual_gap_height
            
    current_bottom_y = WINDOW_HEIGHT - 15
    for btn_def in reversed(bottom_buttons):
        height = btn_def.get('ideal_height', 45)
        rect = pygame.Rect(GRID_AREA_WIDTH + h_padding, current_bottom_y - height, PANEL_WIDTH - (h_padding * 2), height)
        ui_elements[btn_def['id']] = Button(rect, btn_def['text'], btn_def['id'], fonts['default'], default_colors)
        current_bottom_y -= (height + 15)
            
    return ui_elements

def draw_control_panel(screen, fonts, ui_elements, current_size_selection, mark_is_x, solution_status, z3_available, history_manager):
    """Draws the entire right-side control panel."""
    pygame.draw.rect(screen, COLOR_PANEL, (GRID_AREA_WIDTH, 0, PANEL_WIDTH, WINDOW_HEIGHT))
    mouse_pos = pygame.mouse.get_pos()

    for name, elem in ui_elements.items():
        if isinstance(elem, Button):
            if name == 'toggle':
                elem.text = "Xs" if mark_is_x else "Dots"
            
            elem.is_disabled = (name in ['find', 'check'] and not z3_available) or \
                               (name == 'back' and not history_manager.can_undo()) or \
                               (name == 'forward' and not history_manager.can_redo())
            elem.draw(screen)

    if 'size_title' in ui_elements:
        title_def = ui_elements['size_title']
        title_surf = fonts['default'].render(title_def['text'], True, COLOR_BUTTON_TEXT)
        title_rect = title_surf.get_rect(center=(GRID_AREA_WIDTH + PANEL_WIDTH // 2, title_def['y_pos']))
        screen.blit(title_surf, title_rect)

    if 'size_selector' in ui_elements:
        size_buttons = ui_elements['size_selector']
        for size_id, b in size_buttons.items():
            puzzle_def = PUZZLE_DEFINITIONS[size_id]
            diff_colors = DIFFICULTY_COLORS[puzzle_def['difficulty']]
            color = diff_colors['hover'] if b['rect'].collidepoint(mouse_pos) else diff_colors['base']
            pygame.draw.circle(screen, color, b['rect'].center, b['radius'])
            if size_id == current_size_selection:
                pygame.draw.circle(screen, COLOR_SELECTED, b['rect'].center, b['radius'], 3)
            num_surf = fonts['small'].render(str(puzzle_def['dim']), True, COLOR_BUTTON_TEXT)
            screen.blit(num_surf, num_surf.get_rect(center=b['rect'].center))
            draw_star_indicator(screen, b['rect'], puzzle_def['stars'], fonts['tiny'])

    if solution_status:
        bottom_button_y = WINDOW_HEIGHT - 45 - 15 - 45 - 15 
        color = COLOR_CORRECT if "Correct" in solution_status else COLOR_INCORRECT
        status_surf = fonts['default'].render(solution_status, True, color)
        status_rect = status_surf.get_rect(center=(GRID_AREA_WIDTH + PANEL_WIDTH // 2, bottom_button_y))
        screen.blit(status_surf, status_rect)


# --- UNCHANGED DRAWING HELPER FUNCTIONS ---

def calculate_star_points(center_x, center_y, outer_radius, inner_radius):
    points = [];
    for i in range(10):
        angle = math.pi / 5 * i - math.pi / 2
        radius = outer_radius if i % 2 == 0 else inner_radius
        points.append((center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
    return points

def draw_star_indicator(screen, rect, count, font):
    star_radius = 12
    center_x = rect.right - star_radius + 5; center_y = rect.top + star_radius - 8
    star_points = calculate_star_points(center_x, center_y, star_radius, star_radius/2)
    pygame.draw.polygon(screen, COLOR_STAR, star_points)
    num_surf = font.render(str(count), True, COLOR_STAR_NUM)
    screen.blit(num_surf, num_surf.get_rect(center=(center_x, center_y + 1)))

def draw_background_colors(screen, region_grid, cell_size):
    dim = len(region_grid)
    for r in range(dim):
        for c in range(dim):
            rect = pygame.Rect(c * cell_size, r * cell_size, cell_size, cell_size)
            if region_grid[r][c] > 0:
                pygame.draw.rect(screen, PYGAME_UNIFIED_COLORS[(region_grid[r][c] - 1) % len(PYGAME_UNIFIED_COLORS)][1], rect)

def draw_grid_lines(screen, region_grid, cell_size):
    dim = len(region_grid)
    for i in range(dim + 1):
        pygame.draw.line(screen, COLOR_GRID_LINES, (i * cell_size, 0), (i * cell_size, GRID_AREA_HEIGHT), BORDER_NORMAL)
        pygame.draw.line(screen, COLOR_GRID_LINES, (0, i * cell_size), (GRID_AREA_WIDTH, i * cell_size), BORDER_NORMAL)
    for r in range(dim):
        for c in range(dim):
            if c < dim - 1 and region_grid[r][c] != region_grid[r][c+1]:
                pygame.draw.line(screen, COLOR_BLACK, ((c + 1) * cell_size, r * cell_size), ((c + 1) * cell_size, (r + 1) * cell_size), BORDER_THICK)
            if r < dim - 1 and region_grid[r][c] != region_grid[r+1][c]:
                pygame.draw.line(screen, COLOR_BLACK, (c * cell_size, (r + 1) * cell_size), ((c + 1) * cell_size, (r + 1) * cell_size), BORDER_THICK)
    pygame.draw.rect(screen, COLOR_BLACK, (0, 0, GRID_AREA_WIDTH, GRID_AREA_HEIGHT), BORDER_THICK)

def draw_player_marks(screen, player_grid, mark_is_x, cell_size):
    dim = len(player_grid)
    for r in range(dim):
        for c in range(dim):
            cell_state = player_grid[r][c]
            center_x = c * cell_size + cell_size // 2; center_y = r * cell_size + cell_size // 2
            if cell_state == STATE_STAR:
                outer_rad = cell_size / 2 - GUTTER * 1.5; inner_rad = outer_rad / 2
                pygame.draw.polygon(screen, COLOR_STAR, calculate_star_points(center_x, center_y, outer_rad, inner_rad))
            elif cell_state == STATE_SECONDARY_MARK:
                if mark_is_x:
                    margin = GUTTER * 2.5; line_width = max(1, int(cell_size / 15))
                    pygame.draw.line(screen, COLOR_X, (c * cell_size + margin, r * cell_size + margin), ((c+1) * cell_size - margin, (r+1) * cell_size - margin), line_width)
                    pygame.draw.line(screen, COLOR_X, ((c+1) * cell_size - margin, r * cell_size + margin), (c * cell_size + margin, (r+1) * cell_size - margin), line_width)
                else:
                    pygame.draw.circle(screen, COLOR_DOT, (center_x, center_y), cell_size / 6)

def draw_feedback_overlay(screen, color, alpha):
    if alpha > 0:
        overlay = pygame.Surface((GRID_AREA_WIDTH, GRID_AREA_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*color, alpha)); screen.blit(overlay, (0, 0))

