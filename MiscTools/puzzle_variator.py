# ==================================================================================================
#
#   Star Battle Puzzle Variator
#
#   Author: Isaiah Tadrous
#   Version: 1.0.0
#
# --------------------------------------------------------------------------------------------------
#
#   Description:
#   This script is a command-line utility for augmenting datasets of Star Battle puzzles.
#   It reads puzzles in the Star Battle Notation (SBN) format from an input file and
#   generates a larger set of unique symmetrical variations.
#
#   The variation process involves applying geometric transformations to each input
#   puzzle's region grid:
#   1.  A horizontal flip.
#   2.  A vertical flip.
#   3.  Four 90-degree rotations for the original, horizontally-flipped, and
#       vertically-flipped versions.
#
#   This methodology can generate up to 8 variations from a single seed puzzle. The
#   resulting set is then deduplicated to ensure only unique puzzles are outputted,
#   preventing isomorphic duplicates in the final dataset.
#
# --------------------------------------------------------------------------------------------------
#
#   Usage:
#   python puzzle_variator.py <input_path> <output_path> [-a]
#
#   Arguments:
#     input_path     Path to the source text file containing SBN puzzles.
#     output_path    Path to the file where unique variations will be written.
#     -a, --append   Optional. If present, appends puzzles to the output file
#                    instead of overwriting it.
#
# ==================================================================================================

import sys
import math
from collections import deque
import argparse # Using argparse for a more robust and user-friendly CLI.

# --- SBN Format Constants ---
# These constants define the Star Battle Notation format and must be synchronized
# with any other tools in the ecosystem (e.g., solvers, GUI applications).

SBN_B64_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
SBN_CHAR_TO_INT = {c: i for i, c in enumerate(SBN_B64_ALPHABET)}
SBN_INT_TO_CHAR = {i: c for i, c in enumerate(SBN_B64_ALPHABET)}
SBN_CODE_TO_DIM_MAP = {
    '55': 5,  '66': 6,  '77': 7,  '88': 8,  '99': 9, 'AA': 10, 'BB': 11, 'CC': 12, 'DD': 13,
    'EE': 14, 'FF': 15, 'GG': 16, 'HH': 17, 'II': 18, 'JJ': 19, 'KK': 20, 'LL': 21, 'MM': 22,
    'NN': 23, 'OO': 24, 'PP': 25
}
DIM_TO_SBN_CODE_MAP = {v: k for k, v in SBN_CODE_TO_DIM_MAP.items()}

# --- Grid Transformation Functions ---
# These functions perform the geometric operations on the puzzle grid.

def rotate_grid_90_clockwise(grid):
    """ Rotates a 2D list (grid) 90 degrees clockwise.

    Args:
        grid (list[list]): The 2D list to rotate.

    Returns:
        list[list]: The rotated grid.
    """
    if not grid or not grid[0]:
        return grid
    # A standard and efficient way to rotate a matrix is to transpose it and then
    # reverse each row.
    return [list(reversed(row)) for row in zip(*grid)]

def flip_grid_horizontally(grid):
    """ Flips a 2D list (grid) horizontally.

    Args:
        grid (list[list]): The 2D list to flip.

    Returns:
        list[list]: The flipped grid.
    """
    if not grid or not grid[0]:
        return grid
    # Slicing with [::-1] is a concise way to reverse each row.
    return [row[::-1] for row in grid]

def flip_grid_vertically(grid):
    """ Flips a 2D list (grid) vertically.

    Args:
        grid (list[list]): The 2D list to flip.

    Returns:
        list[list]: The flipped grid.
    """
    if not grid or not grid[0]:
        return grid
    # Reversing the outer list flips the grid vertically.
    return grid[::-1]


# --- SBN Handling Functions ---
# These functions handle the conversion between SBN strings and grid data.

def decode_sbn(sbn_string):
    """
    Decodes an SBN string into its constituent parts: a region grid and stars.

    Args:
        sbn_string (str): The SBN puzzle string to decode.

    Returns:
        dict: A dictionary {'grid': region_grid, 'stars': stars} or None on failure.
    """
    try:
        dim = SBN_CODE_TO_DIM_MAP.get(sbn_string[0:2])
        if dim is None:
            print(f"Warning: Could not determine dimension from SBN code '{sbn_string[0:2]}'. Skipping.")
            return None
            
        stars = int(sbn_string[2])
        border_bits_needed = 2 * dim * (dim - 1)
        border_chars_needed = math.ceil(border_bits_needed / 6)
        
        region_data_part = sbn_string[4 : 4 + border_chars_needed]
        
        # Ensure the region data has the expected length, padding if necessary.
        region_data_part = region_data_part.ljust(border_chars_needed, SBN_B64_ALPHABET[0])

        full_bitfield = "".join(bin(SBN_CHAR_TO_INT.get(c, 0))[2:].zfill(6) for c in region_data_part)
        
        # Trim excess bits resulting from character padding.
        actual_bitfield = full_bitfield[-border_bits_needed:]
        
        v_bits = actual_bitfield[:dim * (dim - 1)]
        h_bits = actual_bitfield[dim * (dim - 1):]
        
        # Use a flood-fill algorithm to reconstruct the regions from border definitions.
        region_grid = reconstruct_grid_from_borders(dim, v_bits, h_bits)
        
        return {'grid': region_grid, 'stars': stars}
    except (KeyError, IndexError, ValueError) as e:
        print(f"Warning: Failed to decode SBN string '{sbn_string}'. Error: {e}. Skipping.")
        return None

def reconstruct_grid_from_borders(dim, v_bits, h_bits):
    """Reconstructs the region grid from its border definitions using a flood-fill algorithm."""
    grid, region_id = [[0] * dim for _ in range(dim)], 1
    for r_start in range(dim):
        for c_start in range(dim):
            # If this cell hasn't been assigned to a region yet, start a new flood-fill.
            if grid[r_start][c_start] == 0:
                q = deque([(r_start, c_start)])
                grid[r_start][c_start] = region_id
                while q:
                    r, c = q.popleft()
                    # Explore neighbors if there is no border ('0') between them.
                    # Check right neighbor
                    if c < dim - 1 and grid[r][c+1] == 0 and v_bits[r * (dim - 1) + c] == '0':
                        grid[r][c+1] = region_id; q.append((r, c+1))
                    # Check left neighbor
                    if c > 0 and grid[r][c-1] == 0 and v_bits[r * (dim - 1) + c - 1] == '0':
                        grid[r][c-1] = region_id; q.append((r, c-1))
                    # Check bottom neighbor
                    if r < dim - 1 and grid[r+1][c] == 0 and h_bits[c * (dim - 1) + r] == '0':
                        grid[r+1][c] = region_id; q.append((r+1, c))
                    # Check top neighbor
                    if r > 0 and grid[r-1][c] == 0 and h_bits[c * (dim - 1) + r - 1] == '0':
                        grid[r-1][c] = region_id; q.append((r-1, c))
                region_id += 1
    return grid

def encode_to_sbn(region_grid, stars):
    """Encodes a region grid and star count back into a valid SBN string."""
    if not region_grid or not region_grid[0]:
        return None
    dim = len(region_grid)
    sbn_code = DIM_TO_SBN_CODE_MAP.get(dim)
    if not sbn_code:
        return None

    # Define borders: '1' if regions differ, '0' if they are the same.
    vertical_bits = ['1' if c < dim - 1 and region_grid[r][c] != region_grid[r][c+1] else '0' for r in range(dim) for c in range(dim - 1)]
    horizontal_bits = ['1' if r < dim - 1 and region_grid[r][c] != region_grid[r+1][c] else '0' for c in range(dim) for r in range(dim - 1)]
    
    clean_bitfield = "".join(vertical_bits) + "".join(horizontal_bits)
    
    # Pad with leading zeros to make the length a multiple of 6 for Base64 conversion.
    padding_needed = (6 - len(clean_bitfield) % 6) % 6
    padded_bitfield = ('0' * padding_needed) + clean_bitfield
    
    # Convert 6-bit chunks to their corresponding Base64 characters.
    region_data_chars = [SBN_INT_TO_CHAR[int(padded_bitfield[i:i+6], 2)] for i in range(0, len(padded_bitfield), 6)]
    region_data = "".join(region_data_chars)

    # Flag 'W' is for a plain puzzle definition without player annotations.
    return f"{sbn_code}{stars}W{region_data}"

# --- Main Application Logic ---

def generate_puzzle_variations(sbn_string):
    """
    Takes a single SBN string and generates all unique symmetrical variations.
    
    Args:
        sbn_string (str): The seed puzzle in SBN format.

    Returns:
        A set of unique SBN strings representing the variations.
    """
    decoded_puzzle = decode_sbn(sbn_string)
    if not decoded_puzzle:
        return set()

    initial_grid = decoded_puzzle['grid']
    stars = decoded_puzzle['stars']
    
    generated_sbns = set()

    # Create the three base grids for transformations.
    base_grids = [
        initial_grid,
        flip_grid_horizontally(initial_grid),
        flip_grid_vertically(initial_grid)
    ]

    for grid in base_grids:
        current_grid = grid
        # Perform 4 rotations (0, 90, 180, 270 degrees) for each base grid.
        for _ in range(4):
            sbn = encode_to_sbn(current_grid, stars)
            if sbn:
                generated_sbns.add(sbn)
            current_grid = rotate_grid_90_clockwise(current_grid)
            
    return generated_sbns


def main():
    """
    Main function to run the script from the command line.
    """
    # Set up the command-line argument parser.
    parser = argparse.ArgumentParser(
        description="Generates unique symmetrical variations of Star Battle puzzles from an SBN file.",
        formatter_class=argparse.RawTextHelpFormatter # Preserves newlines in help text.
    )
    parser.add_argument("input_path", help="Path to the source text file containing SBN puzzles.")
    parser.add_argument("output_path", help="Path to the file where unique variations will be written.")
    parser.add_argument(
        "-a", "--append",
        action="store_true", # Makes this a flag; if present, value is True.
        help="Append the generated puzzles to the output file instead of overwriting it."
    )
    args = parser.parse_args()

    # Read source puzzles from the input file.
    try:
        with open(args.input_path, 'r') as f:
            source_sbns = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Input file not found at '{args.input_path}'")
        sys.exit(1)

    print(f"Reading {len(source_sbns)} puzzles from '{args.input_path}'...")
    
    all_generated_sbns = set()
    for sbn in source_sbns:
        variations = generate_puzzle_variations(sbn)
        all_generated_sbns.update(variations)

    print(f"Generated {len(all_generated_sbns)} unique puzzles.")

    # Determine the file mode based on the --append flag.
    file_mode = 'a' if args.append else 'w'
    action_word = "Appending" if args.append else "Writing"

    with open(args.output_path, file_mode) as f:
        # Sorting provides a consistent, deterministic output file.
        for sbn in sorted(list(all_generated_sbns)):
            f.write(sbn + '\n')

    print(f"Successfully {action_word.lower()} all unique puzzles to '{args.output_path}'.")


if __name__ == "__main__":
    main()