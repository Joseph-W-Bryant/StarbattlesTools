# ==================================================================================================
#
#   Unique Line Aggregator
#
#   Author: Isaiah Tadrous
#   Version: 1.0.0
#
# --------------------------------------------------------------------------------------------------
#
#   Description:
#   This script serves as a command-line utility to process a directory of text files.
#   It reads all lines from every '.txt' file within a specified folder, identifies
#   all unique lines, and aggregates them into a single output file. It also reports
#   any duplicate lines that were found across all files.
#
#   This tool is useful for cleaning up and consolidating data from multiple sources,
#   such as log files, data dumps, or lists.
#
# --------------------------------------------------------------------------------------------------
#
#   Usage:
#   python your_script_name.py <input_directory> [-o <output_file_name>]
#
#   Example:
#   python your_script_name.py ./my_files -o unique_lines.txt
#
# ==================================================================================================

import os
import argparse # Use argparse for a professional and flexible command-line interface.

def process_folder(input_dir, output_filename):
    """
    Reads all .txt files in a directory, extracts unique lines, writes them to a
    single output file, and prints any duplicate lines found.

    Args:
        input_dir (str): The path to the directory containing the text files.
        output_filename (str): The name of the file to save unique lines to.
    """
    # --- Data Structures Initialization ---
    # `seen_items` uses a set for O(1) average time complexity on lookups, which is highly
    # efficient for checking if a line has been encountered before.
    seen_items = set()

    # `duplicate_items` stores any line that is seen more than once.
    duplicate_items = set()

    # `unique_items` maintains the original order of the first occurrence of each unique line.
    unique_items_in_order = []

    print(f"Processing all .txt files in '{input_dir}'...")

    # --- File Processing Loop ---
    try:
        # Iterate through each entry in the specified directory.
        for filename in sorted(os.listdir(input_dir)): # Sorting ensures a consistent processing order.
            if filename.endswith(".txt"):
                file_path = os.path.join(input_dir, filename)
                
                # Use 'utf-8' encoding as a robust default for text files.
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file:
                        # .strip() removes leading/trailing whitespace, including newlines.
                        item = line.strip()

                        # Ignore empty lines after stripping.
                        if not item:
                            continue

                        # Check for duplicates.
                        if item in seen_items:
                            duplicate_items.add(item)
                        else:
                            # If it's the first time seeing this item, record it.
                            seen_items.add(item)
                            unique_items_in_order.append(item)
    except FileNotFoundError:
        print(f"Error: Input directory not found at '{input_dir}'")
        return # Exit the function if the directory doesn't exist.
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    # --- Output Generation ---
    # Write the unique items to the specified output file.
    output_path = os.path.join(input_dir, output_filename)
    print(f"\nWriting {len(unique_items_in_order)} unique lines to '{output_path}'...")
    with open(output_path, 'w', encoding='utf-8') as file:
        for item in unique_items_in_order:
            file.write(item + "\n")

    # --- Reporting Duplicates ---
    # Print any found duplicates to the console for review.
    print("\n--- Duplicate Analysis ---")
    if duplicate_items:
        print(f"Found {len(duplicate_items)} duplicate lines:")
        # Sorting the duplicates makes the output clean and easy to read.
        for dup in sorted(list(duplicate_items)):
            print(f"  - {dup}")
    else:
        print("No duplicate lines were found.")

if __name__ == "__main__":
    # --- Command-Line Argument Parsing ---
    # This setup makes the script a reusable and professional command-line tool.
    parser = argparse.ArgumentParser(
        description="A utility to aggregate unique lines from all .txt files in a directory."
    )

    # Define the positional argument for the input directory.
    parser.add_argument(
        "input_directory",
        help="The path to the folder containing .txt files to process."
    )

    # Define an optional argument for the output file name.
    parser.add_argument(
        "-o", "--output",
        default="combined.txt", # Provide a sensible default value.
        help="The name for the output file containing unique lines. Defaults to 'combined.txt'."
    )

    args = parser.parse_args()

    # Call the main processing function with the parsed arguments.
    process_folder(args.input_directory, args.output)