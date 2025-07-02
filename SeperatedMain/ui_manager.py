# ui_manager.py
# Description: Manages all Pygame drawing functions and the data-driven UI layout.

import pygame
import math
from ui_elements import Button
from z3_solver import Z3_AVAILABLE

from constants import (
    GRID_AREA_WIDTH, GRID_AREA_HEIGHT, LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH,
    WINDOW_HEIGHT, GUTTER, BORDER_NORMAL, BORDER_THICK, PYGAME_UNIFIED_COLORS,
    COLOR_GRID_LINES, COLOR_BLACK, COLOR_STAR, COLOR_X, COLOR_DOT, COLOR_PANEL,
    COLOR_BUTTON, COLOR_BUTTON_HOVER, COLOR_BUTTON_TEXT, COLOR_CORRECT, COLOR_INCORRECT,
    COLOR_SELECTED, COLOR_STAR_NUM, DIFFICULTY_COLORS, STATE_STAR, STATE_SECONDARY_MARK,
    PUZZLE_DEFINITIONS, COLOR_DISABLED_BUTTON, COLOR_DISABLED_TEXT, DRAWING_COLORS,
    BORDER_CUSTOM_THICKNESS, GRID_START_X
)

# --- Console Interaction ---

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

# --- Main Drawing and Layout Functions ---

def draw_game(game_state):
    """Main drawing function that orchestrates all visual updates for the new layout."""
    game_state.screen.fill(COLOR_PANEL)
    grid_surface = pygame.Surface((GRID_AREA_WIDTH, GRID_AREA_HEIGHT))
    
    if game_state.region_grid:
        draw_background_colors(grid_surface, game_state.region_grid, game_state.cell_size)
        draw_custom_borders(grid_surface, game_state)
        draw_grid_lines(grid_surface, game_state.region_grid, game_state.cell_size)
        grid_surface.blit(game_state.draw_surface, (0, 0))
        draw_player_marks(grid_surface, game_state.player_grid, game_state.mark_is_x, game_state.cell_size)
        draw_feedback_overlay(grid_surface, game_state)

    game_state.screen.blit(grid_surface, (GRID_START_X, 0))
    
    if game_state.feedback_overlay_alpha > 0:
        game_state.feedback_overlay_alpha = max(0, game_state.feedback_overlay_alpha - 4)
        
    draw_panels(game_state)
    pygame.display.set_caption(f"Star Battle ({game_state.stars_per_region} Stars)")
    pygame.display.flip()


def draw_panels(game_state):
    """Draws all UI elements in both panels and handles dynamic state changes."""
    screen = game_state.screen
    fonts = game_state.fonts
    ui_elements = game_state.ui_elements
    mouse_pos = pygame.mouse.get_pos()

    for name, elem in ui_elements.items():
        if isinstance(elem, Button):
            if name == 'toggle': elem.text = "Xs" if game_state.mark_is_x else "Dots"
            if name == 'toggle_mode': elem.text = "Mark Mode" if game_state.is_draw_mode else "Draw Mode"
            if name == 'border_mode': elem.text = "Mark Mode" if game_state.is_border_mode else "Add Border"

            elem.is_disabled = (name in ['find', 'check'] and not Z3_AVAILABLE) or \
                               (name in ['back', 'forward'] and (game_state.is_draw_mode or game_state.is_border_mode)) or \
                               (name == 'back' and not game_state.history.can_undo()) or \
                               (name == 'forward' and not game_state.history.can_redo())
            elem.draw(screen)
        
        elif elem.get('type') == 'title':
            title_surf = fonts['default'].render(elem['text'], True, COLOR_BUTTON_TEXT)
            screen.blit(title_surf, title_surf.get_rect(center=elem['rect'].center))

        elif elem.get('type') == 'size_grid':
            size_buttons = elem.get('buttons', {})
            for size_id, b in size_buttons.items():
                puzzle_def = PUZZLE_DEFINITIONS[size_id]
                diff_colors = DIFFICULTY_COLORS[puzzle_def['difficulty']]
                color = diff_colors['hover'] if b['rect'].collidepoint(mouse_pos) else diff_colors['base']
                pygame.draw.circle(screen, color, b['rect'].center, b['radius'])
                if size_id == game_state.current_size_selection:
                    pygame.draw.circle(screen, COLOR_SELECTED, b['rect'].center, b['radius'], 3)
                num_surf = fonts['small'].render(str(puzzle_def['dim']), True, COLOR_BUTTON_TEXT)
                screen.blit(num_surf, num_surf.get_rect(center=b['rect'].center))
                draw_star_indicator(screen, b['rect'], puzzle_def['stars'], fonts['tiny'])
    
    if game_state.is_draw_mode or game_state.is_border_mode:
        color_ids = ['color_r', 'color_b', 'color_y', 'color_g']
        selected_id = color_ids[game_state.current_color_index]
        if selected_id in ui_elements:
            pygame.draw.rect(screen, COLOR_SELECTED, ui_elements[selected_id].rect, 3, border_radius=8)

    if game_state.is_border_mode and 'border_mode' in ui_elements:
        pygame.draw.rect(screen, COLOR_SELECTED, ui_elements['border_mode'].rect, 3, border_radius=8)
    
    if game_state.is_draw_mode and 'toggle_mode' in ui_elements:
         pygame.draw.rect(screen, COLOR_SELECTED, ui_elements['toggle_mode'].rect, 3, border_radius=8)

    if game_state.solution_status:
        bottom_y = ui_elements['check'].rect.top - 15
        center_x = GRID_START_X + GRID_AREA_WIDTH + RIGHT_PANEL_WIDTH // 2
        color = COLOR_CORRECT if "Correct" in game_state.solution_status else COLOR_INCORRECT
        status_surf = fonts['default'].render(game_state.solution_status, True, color)
        status_rect = status_surf.get_rect(center=(center_x, bottom_y))
        screen.blit(status_surf, status_rect)


def _build_single_panel(layout_def, fonts, panel_width, panel_start_x):
    """Builds UI elements for one panel based on a layout, width, and starting X."""
    ui_elements = {}
    h_padding, ideal_gap = 15, 15
    default_colors = {'base': COLOR_BUTTON, 'hover': COLOR_BUTTON_HOVER, 'text': COLOR_BUTTON_TEXT,
                      'disabled_bg': COLOR_DISABLED_BUTTON, 'disabled_fg': COLOR_DISABLED_TEXT}

    flowing = [e for e in layout_def if 'fixed_bottom' not in e]
    bottom = [e for e in layout_def if 'fixed_bottom' in e]
    
    flowing_h = sum(e.get('ideal_height', 0) + ideal_gap for e in flowing) - ideal_gap
    bottom_h = sum(e.get('ideal_height', 45) + ideal_gap for e in bottom)
    
    available_space = WINDOW_HEIGHT - 15 - bottom_h - 15
    scale = min(1.0, available_space / flowing_h if flowing_h > 0 else 1.0)
    gap = ideal_gap * scale
    
    current_y = 15
    for elem_def in flowing:
        h = elem_def.get('ideal_height', 0) * scale
        rect = pygame.Rect(panel_start_x + h_padding, current_y, panel_width - (h_padding * 2), h)
        elem_type = elem_def['type']

        if elem_type == 'button':
            ui_elements[elem_def['id']] = Button(rect, elem_def['text'], elem_def['id'], fonts['default'], default_colors)
        elif elem_type == 'button_group':
            group_w, spacing = rect.width, 10
            btn_w_avail = group_w - ((len(elem_def['items']) - 1) * spacing)
            current_x = rect.left
            for btn_def in elem_def['items']:
                btn_w = btn_w_avail * btn_def['width_ratio']
                btn_rect = pygame.Rect(current_x, current_y, btn_w, h)
                colors = default_colors
                if btn_def['id'].startswith('color_'):
                    idx = ['r','b','y','g'].index(btn_def['id'][-1])
                    opaque = DRAWING_COLORS[idx][:3]
                    colors = {'base': opaque, 'hover': tuple(min(c + 30, 255) for c in opaque), 
                              'text': COLOR_BUTTON_TEXT, 'disabled_bg': COLOR_DISABLED_BUTTON, 'disabled_fg': COLOR_DISABLED_TEXT}
                ui_elements[btn_def['id']] = Button(btn_rect, btn_def['text'], btn_def['id'], fonts['default'], colors)
                current_x += btn_w + spacing
        elif elem_type == 'title':
            elem_def['rect'] = rect
            ui_elements[elem_def['id']] = elem_def
        elif elem_type == 'size_grid':
            buttons, s_rad, s_cols = {}, 22, 4
            s_h_pad = (panel_width - (s_cols * s_rad * 2)) / (s_cols + 1)
            s_v_pad = (h - (3 * s_rad * 2)) / 2 if 3 > 1 else 0
            for i in range(12):
                r, c = divmod(i, s_cols)
                y, x = rect.top + (r * (s_rad * 2 + s_v_pad)) + s_rad, panel_start_x + s_h_pad + c * (s_rad * 2 + s_h_pad) + s_rad
                buttons[i] = {'rect': pygame.Rect(x - s_rad, y - s_rad, s_rad * 2, s_rad * 2), 'radius': s_rad}
            ui_elements[elem_def['id']] = {'type': 'size_grid', 'buttons': buttons}
        current_y += h + gap
            
    current_y = WINDOW_HEIGHT - 15
    for btn_def in reversed(bottom):
        h = btn_def.get('ideal_height', 45)
        rect = pygame.Rect(panel_start_x + h_padding, current_y - h, panel_width - (h_padding * 2), h)
        ui_elements[btn_def['id']] = Button(rect, btn_def['text'], btn_def['id'], fonts['default'], default_colors)
        current_y -= (h + ideal_gap)
        
    return ui_elements

def build_panels(panel_layout_defs, fonts):
    all_elems = {}
    for panel_def in panel_layout_defs:
        side, layout = panel_def['side'], panel_def['layout']
        width, start_x = (LEFT_PANEL_WIDTH, 0) if side == 'left' else (RIGHT_PANEL_WIDTH, GRID_START_X + GRID_AREA_WIDTH)
        all_elems.update(_build_single_panel(layout, fonts, width, start_x))
    return all_elems

# --- Drawing Helper Functions ---
def draw_custom_borders(surface, game_state):
    thickness = BORDER_CUSTOM_THICKNESS
    all_borders = game_state.custom_borders[:]
    if game_state.current_border_path:
        current_color = DRAWING_COLORS[game_state.current_color_index][:3]
        all_borders.append((game_state.current_border_path, current_color))
    for shape, color in all_borders:
        if not shape: continue
        for r,c in shape:
            x,y=c*game_state.cell_size, r*game_state.cell_size
            if (r-1,c) not in shape: pygame.draw.rect(surface,color,(x,y,game_state.cell_size,thickness))
            if (r+1,c) not in shape: pygame.draw.rect(surface,color,(x,y+game_state.cell_size-thickness,game_state.cell_size,thickness))
            if (r,c-1) not in shape: pygame.draw.rect(surface,color,(x,y,thickness,game_state.cell_size))
            if (r,c+1) not in shape: pygame.draw.rect(surface,color,(x+game_state.cell_size-thickness,y,thickness,game_state.cell_size))

def calculate_star_points(cx,cy,r_out,r_in): return [(cx+r*math.cos(math.pi/5*i-math.pi/2),cy+r*math.sin(math.pi/5*i-math.pi/2)) for i in range(10) for r in ((r_out,r_in)[i%2],)]
def draw_star_indicator(screen,rect,count,font):
    cx,cy,r = rect.right-12+5,rect.top+12-8,12
    pygame.draw.polygon(screen,COLOR_STAR,calculate_star_points(cx,cy,r,r/2))
    num_surf = font.render(str(count),True,COLOR_STAR_NUM); screen.blit(num_surf,num_surf.get_rect(center=(cx,cy+1)))
def draw_background_colors(surface,region_grid,cell_size):
    for r,row in enumerate(region_grid):
        for c,region_id in enumerate(row):
            if region_id>0: pygame.draw.rect(surface,PYGAME_UNIFIED_COLORS[(region_id-1)%len(PYGAME_UNIFIED_COLORS)][1],(c*cell_size,r*cell_size,cell_size,cell_size))
def draw_grid_lines(surface,region_grid,cell_size):
    dim=len(region_grid)
    for i in range(dim+1):
        pygame.draw.line(surface,COLOR_GRID_LINES,(i*cell_size,0),(i*cell_size,GRID_AREA_HEIGHT),BORDER_NORMAL)
        pygame.draw.line(surface,COLOR_GRID_LINES,(0,i*cell_size),(GRID_AREA_WIDTH,i*cell_size),BORDER_NORMAL)
    for r in range(dim):
        for c in range(dim):
            if c<dim-1 and region_grid[r][c]!=region_grid[r][c+1]: pygame.draw.line(surface,COLOR_BLACK,((c+1)*cell_size,r*cell_size),((c+1)*cell_size,(r+1)*cell_size),BORDER_THICK)
            if r<dim-1 and region_grid[r][c]!=region_grid[r+1][c]: pygame.draw.line(surface,COLOR_BLACK,(c*cell_size,(r+1)*cell_size),((c+1)*cell_size,(r+1)*cell_size),BORDER_THICK)
    pygame.draw.rect(surface,COLOR_BLACK,(0,0,GRID_AREA_WIDTH,GRID_AREA_HEIGHT),BORDER_THICK)
def draw_player_marks(surface,player_grid,mark_is_x,cell_size):
    if not player_grid: return
    for r,row in enumerate(player_grid):
        for c,state in enumerate(row):
            cx,cy=c*cell_size+cell_size/2, r*cell_size+cell_size/2
            if state==STATE_STAR: r_out=cell_size/2-GUTTER*1.5; pygame.draw.polygon(surface,COLOR_STAR,calculate_star_points(cx,cy,r_out,r_out/2))
            elif state==STATE_SECONDARY_MARK:
                if mark_is_x:
                    m=GUTTER*2.5; lw=max(1,int(cell_size/15)); p1,p2=(c*cell_size+m,r*cell_size+m),((c+1)*cell_size-m,(r+1)*cell_size-m); p3,p4=((c+1)*cell_size-m,r*cell_size+m),(c*cell_size+m,(r+1)*cell_size-m)
                    pygame.draw.line(surface,COLOR_X,p1,p2,lw); pygame.draw.line(surface,COLOR_X,p3,p4,lw)
                else: pygame.draw.circle(surface,COLOR_DOT,(cx,cy),cell_size/6)
def draw_feedback_overlay(surface,game_state):
    if game_state.feedback_overlay_alpha>0:
        overlay=pygame.Surface((GRID_AREA_WIDTH,GRID_AREA_HEIGHT),pygame.SRCALPHA)
        overlay.fill((*game_state.feedback_overlay_color, game_state.feedback_overlay_alpha)); surface.blit(overlay,(0,0))

