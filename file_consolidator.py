import os
from pathlib import Path
from typing import Dict

def read_and_write_files(directory: str, output_file: str, file_extensions: tuple = ('.py', '.txt')) -> None:
    """
    Recursively reads files with specified extensions and writes them to a single output file.
    
    Args:
        directory (str): The root directory path to start searching from
        output_file (str): Path to the output file where all contents will be written
        file_extensions (tuple): File extensions to include (default: .py and .txt files)
    """
    try:
        root_path = Path(directory)
        
        # Open output file in write mode
        with open(output_file, 'w', encoding='utf-8') as outfile:
            # Write header
            outfile.write(f"Consolidated files from: {directory}\n\n")
            
            # Counter for processed files
            file_count = 0
            
            # Walk through all files recursively
            for path in root_path.rglob("*"):
                if path.suffix.lower() in file_extensions and "__pycache__" not in str(path):
                    try:
                        # Read the file content
                        with open(path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            
                        # Write file separator and path
                        outfile.write(f"\n{'='*50}\n")
                        outfile.write(f"File: {path.relative_to(root_path)}\n")
                        outfile.write(f"{'='*50}\n")
                        
                        # Write the content
                        outfile.write(content)
                        outfile.write("\n")
                        
                        file_count += 1
                        
                    except Exception as e:
                        print(f"Error reading file {path}: {str(e)}")
            
            # Write summary at the end
            outfile.write(f"\n\nTotal files processed: {file_count}")
            print(f"Successfully consolidated {file_count} files to {output_file}")
            
    except Exception as e:
        print(f"Error accessing directory {directory}: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Replace with your directory path
    directory_path = "C:/Users/21mds/OneDrive/Documents/deep-gram-voice-agent/venv/Lib/site-packages/deepgram"
    output_path = "consolidated_files.txt"
    
    # Read files and write to single output file
    read_and_write_files(
        directory=directory_path,
        output_file=output_path,
        file_extensions=('.py')  # Add more extensions as needed
    )
