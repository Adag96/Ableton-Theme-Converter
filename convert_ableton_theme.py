import xml.etree.ElementTree as ET
import re
import os
import sys
from pathlib import Path

def rgb_to_hex(r, g, b, a=255):
    # Convert to integers, handling possible float values
    try:
        r_int = int(float(r))
        g_int = int(float(g))
        b_int = int(float(b))
        
        # Handle alpha as float or int
        try:
            a_int = int(float(a))
        except ValueError:
            a_int = 255
        
        if a_int == 255:
            return f"#{r_int:02x}{g_int:02x}{b_int:02x}"
        else:
            return f"#{r_int:02x}{g_int:02x}{b_int:02x}{a_int:02x}"
    except Exception as e:
        print(f"Error converting color values {r},{g},{b},{a}: {str(e)}")
        return "#bcbcbc"  # Return a default gray if conversion fails

def darken_hex_color(hex_color, percent=0.94):
    """Darken a hex color by multiplying RGB values by the given percent."""
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    # Convert to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Darken by multiplying by percent
    r = int(r * percent)
    g = int(g * percent)
    b = int(b * percent)
    
    # Ensure values are in valid range
    r = min(255, max(0, r))
    g = min(255, max(0, g))
    b = min(255, max(0, b))
    
    # Convert back to hex
    return f"#{r:02x}{g:02x}{b:02x}"

def find_ableton_resources_folder():
    """Try to automatically find the Ableton Resources folder based on OS"""
    if sys.platform == "darwin":  # macOS
        potential_paths = [
            "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Themes",
            "/Applications/Ableton Live 12.app/Contents/App-Resources/Themes",
            "/Applications/Ableton Live 11 Suite.app/Contents/App-Resources/Themes",
            "/Applications/Ableton Live 11.app/Contents/App-Resources/Themes"
        ]
    elif sys.platform == "win32":  # Windows
        potential_paths = [
            r"C:\Program Files\Ableton\Live 12 Suite\Resources\Themes",
            r"C:\Program Files\Ableton\Live 12\Resources\Themes",
            r"C:\Program Files\Ableton\Live 11 Suite\Resources\Themes",
            r"C:\Program Files\Ableton\Live 11\Resources\Themes",
            r"C:\ProgramData\Ableton\Live 12 Suite\Resources\Themes",
            r"C:\ProgramData\Ableton\Live 12\Resources\Themes"
        ]
    else:  # Linux or other OS
        return None
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    return None

def get_theme_files(directory, exclude_prefix=None, include_prefix=None):
    """Get .ask files in a directory, optionally filtered by prefix"""
    try:
        if os.path.exists(directory):
            files = [f for f in os.listdir(directory) if f.endswith('.ask')]
            if exclude_prefix:
                files = [f for f in files if not f.startswith(exclude_prefix)]
            if include_prefix:
                files = [f for f in files if f.startswith(include_prefix)]
            return files
        return []
    except Exception:
        return []

def select_file_from_list(files, prompt):
    """Let user select a file from a list"""
    print(prompt)
    for i, file in enumerate(files, 1):
        print(f"{i}. {file}")
    
    while True:
        try:
            choice = input("Enter number (or 0 to specify a different path): ")
            if choice == "0":
                return None
            choice = int(choice)
            if 1 <= choice <= len(files):
                return files[choice-1]
            print(f"Please enter a number between 1 and {len(files)}")
        except ValueError:
            print("Please enter a valid number")

def get_file_path(prompt, default_dir=None, must_exist=True):
    """Get a file path from the user with validation"""
    while True:
        path = input(prompt)
        
        # Strip quotes and apostrophes that might be added when copying paths
        path = path.strip()
        if (path.startswith("'") and path.endswith("'")) or (path.startswith('"') and path.endswith('"')):
            path = path[1:-1]
        
        # Handle relative paths and ~
        path = os.path.expanduser(path)
        if not os.path.isabs(path) and default_dir:
            path = os.path.join(default_dir, path)
        
        if must_exist and not os.path.exists(path):
            print(f"The file/directory '{path}' does not exist. Please try again.")
        else:
            return path

def convert_theme(live10_file, live12_template_file, output_dir=None):
    # Validate input files
    if not os.path.exists(live10_file):
        print(f"Error: Input file '{live10_file}' does not exist.")
        return None
    
    if not os.path.exists(live12_template_file):
        print(f"Error: Template file '{live12_template_file}' does not exist.")
        return None
    
    # Get the original filename and create the new filename
    original_filename = os.path.basename(live10_file)
    # Remove .ask extension if present
    base_name = original_filename.replace('.ask', '')
    new_filename = f"{base_name} Live 12.ask"
    
    # If output_dir is provided, use it; otherwise, use the same directory as the input file
    if output_dir:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, new_filename)
    else:
        output_file = os.path.join(os.path.dirname(live10_file), new_filename)
    
    print(f"\nConverting {original_filename} to {new_filename}")
    
    try:
        # Parse the Live 10 file
        tree_live10 = ET.parse(live10_file)
        root_live10 = tree_live10.getroot()
    except Exception as e:
        print(f"Error parsing input file: {str(e)}")
        return None
    
    try:
        # Parse the Live 12 template file
        tree_live12 = ET.parse(live12_template_file)
        root_live12 = tree_live12.getroot()
        theme_live12 = root_live12.find(".//Theme")
        
        if theme_live12 is None:
            print("Error: Could not find Theme element in Live 12 template.")
            return None
    except Exception as e:
        print(f"Error parsing template file: {str(e)}")
        return None
    
    # Create a mapping of Live 10 parameters to their RGB values
    live10_params = {}
    for element in root_live10.findall(".//SkinManager/*"):
        tag_name = element.tag
        
        # Skip non-color parameters
        if element.find("R") is None:
            continue
            
        r = element.find("R").get("Value")
        g = element.find("G").get("Value")
        b = element.find("B").get("Value")
        
        alpha_element = element.find("Alpha")
        alpha = alpha_element.get("Value") if alpha_element is not None else "255"
        
        live10_params[tag_name] = (r, g, b, alpha)
    
    # Count how many parameters were updated
    updated_count = 0
    
    # Update the Live 12 template with values from Live 10 where parameter names match
    for element in theme_live12:
        if element.tag in live10_params:
            r, g, b, alpha = live10_params[element.tag]
            # Use our updated rgb_to_hex function that handles float values
            try:
                hex_value = rgb_to_hex(r, g, b, alpha)
                element.set("Value", hex_value)
                updated_count += 1
            except Exception as e:
                print(f"Error converting {element.tag}: {r},{g},{b},{alpha} - {str(e)}")
    
    # Special handling for BrowserTagBackground - use StandbySelectionBackground color
    browser_tag_element = theme_live12.find("BrowserTagBackground")
    if browser_tag_element is not None and "StandbySelectionBackground" in live10_params:
        r, g, b, alpha = live10_params["StandbySelectionBackground"]
        try:
            hex_value = rgb_to_hex(r, g, b, alpha)
            browser_tag_element.set("Value", hex_value)
            print(f"Set BrowserTagBackground to match StandbySelectionBackground: {hex_value}")
            updated_count += 1
        except Exception as e:
            print(f"Error setting BrowserTagBackground: {r},{g},{b},{alpha} - {str(e)}")
    
    # Special handling for take lane colors based on surface colors
    # First, find the hex color values for SurfaceHighlight and SurfaceBackground
    if "SurfaceHighlight" in live10_params:
        r, g, b, alpha = live10_params["SurfaceHighlight"]
        try:
            surface_highlight_color = rgb_to_hex(r, g, b, alpha)
            
            # Set TakeLaneTrackHighlighted to match SurfaceHighlight
            take_lane_highlighted_element = theme_live12.find("TakeLaneTrackHighlighted")
            if take_lane_highlighted_element is not None:
                take_lane_highlighted_element.set("Value", surface_highlight_color)
                print(f"Set TakeLaneTrackHighlighted to match SurfaceHighlight: {surface_highlight_color}")
                updated_count += 1
        except Exception as e:
            print(f"Error setting TakeLaneTrackHighlighted: {r},{g},{b},{alpha} - {str(e)}")
    
    if "SurfaceBackground" in live10_params:
        r, g, b, alpha = live10_params["SurfaceBackground"]
        try:
            surface_background_color = rgb_to_hex(r, g, b, alpha)
            
            # Set TakeLaneTrackNotHighlighted to be slightly darker than SurfaceBackground
            take_lane_not_highlighted_element = theme_live12.find("TakeLaneTrackNotHighlighted")
            if take_lane_not_highlighted_element is not None:
                darkened_color = darken_hex_color(surface_background_color, 0.94)  # 6% darker
                take_lane_not_highlighted_element.set("Value", darkened_color)
                print(f"Set TakeLaneTrackNotHighlighted to be darker than SurfaceBackground: {darkened_color}")
                updated_count += 1
        except Exception as e:
            print(f"Error setting TakeLaneTrackNotHighlighted: {r},{g},{b},{alpha} - {str(e)}")
    
    # Special handling for ViewControlOn - use ChosenDefault color
    if "ChosenDefault" in live10_params:
        r, g, b, alpha = live10_params["ChosenDefault"]
        try:
            chosen_default_color = rgb_to_hex(r, g, b, alpha)
            
            # Set ViewControlOn to match ChosenDefault
            view_control_on_element = theme_live12.find("ViewControlOn")
            if view_control_on_element is not None:
                view_control_on_element.set("Value", chosen_default_color)
                print(f"Set ViewControlOn to match ChosenDefault: {chosen_default_color}")
                updated_count += 1
        except Exception as e:
            print(f"Error setting ViewControlOn: {r},{g},{b},{alpha} - {str(e)}")
    
    # Special handling for ViewControlOff - use TransportOffBackground color
    if "TransportOffBackground" in live10_params:
        r, g, b, alpha = live10_params["TransportOffBackground"]
        try:
            transport_off_background_color = rgb_to_hex(r, g, b, alpha)
            
            # Set ViewControlOff to match TransportOffBackground
            view_control_off_element = theme_live12.find("ViewControlOff")
            if view_control_off_element is not None:
                view_control_off_element.set("Value", transport_off_background_color)
                print(f"Set ViewControlOff to match TransportOffBackground: {transport_off_background_color}")
                updated_count += 1
        except Exception as e:
            print(f"Error setting ViewControlOff: {r},{g},{b},{alpha} - {str(e)}")
    
    try:
        # Save the updated Live 12 template to the output file
        tree_live12.write(output_file, encoding='utf-8', xml_declaration=True)
        print(f"Wrote converted theme to {output_file}")
        
        # Format the XML for better readability
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple indentation for readability
        formatted_content = ""
        indent_level = 0
        for line in content.split("\n"):
            if re.search(r'<\/[^>]+>', line) and not re.search(r'<[^\/]', line):
                # Closing tag only
                indent_level -= 1
            
            formatted_content += "\t" * indent_level + line + "\n"
            
            if re.search(r'<[^\/][^>]*[^\/]>$', line):
                # Opening tag
                indent_level += 1
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        print(f"\nSuccess! Updated {updated_count} color parameters.")
        print(f"Formatted theme file saved to {output_file}")
        return output_file
    except Exception as e:
        print(f"Error saving output file: {str(e)}")
        return None

def main():
    print("=" * 60)
    print("Ableton Live Theme Converter")
    print("Convert Ableton Live 10/11 themes to Live 12 format")
    print("=" * 60 + "\n")
    
    # Try to find Ableton Themes folder
    themes_folder = find_ableton_resources_folder()
    if themes_folder:
        print(f"Found Ableton Themes folder: {themes_folder}")
    else:
        print("Couldn't automatically find Ableton Themes folder.")
        themes_folder = os.path.expanduser("~")  # Default to home directory
    
    # Step 1: Get the Live 10/11 theme file to convert
    print("\nSTEP 1: Select the theme file to convert")
    
    if themes_folder:
        # Get all themes EXCEPT those starting with "Default"
        theme_files = get_theme_files(themes_folder, exclude_prefix="Default")
        if theme_files:
            print(f"Found {len(theme_files)} custom theme files in Ableton Themes folder.")
            file_choice = select_file_from_list(theme_files, "Select a theme file to convert:")
            if file_choice:
                live10_file = os.path.join(themes_folder, file_choice)
            else:
                # User wants to specify a different path
                live10_file = get_file_path("Enter the full path to your theme file: ")
        else:
            print("No custom themes found in the Ableton Themes folder.")
            live10_file = get_file_path("Enter the full path to your theme file: ")
    else:
        # No themes folder found, ask for path
        print("Couldn't find Ableton Themes folder. Please provide the path manually.")
        live10_file = get_file_path("Enter the full path to your theme file: ")
    
    # Step 2: Get the Live 12 template file
    print("\nSTEP 2: Select a Live 12 template file")
    
    if themes_folder:
        # Only get themes that start with "Default"
        theme_files = get_theme_files(themes_folder, include_prefix="Default")
        if theme_files:
            print(f"Found {len(theme_files)} default Ableton theme files.")
            file_choice = select_file_from_list(theme_files, "Select a default Live 12 theme to use as template:")
            if file_choice:
                live12_template_file = os.path.join(themes_folder, file_choice)
            else:
                # User wants to specify a different path
                print("\nNOTE: It's recommended to use an official Ableton default theme as a template.")
                live12_template_file = get_file_path("Enter the full path to a Live 12 theme file to use as template: ")
        else:
            print("No default Ableton themes found in the themes folder.")
            live12_template_file = get_file_path("Enter the full path to a Live 12 theme file to use as template: ")
    else:
        # No themes folder found, ask for path
        print("\nNOTE: It's recommended to use an official Ableton default theme as a template.")
        live12_template_file = get_file_path("Enter the full path to a Live 12 theme file to use as template: ")
    
    # Step 3: Get the output directory
    print("\nSTEP 3: Choose where to save the converted theme")

    # Check if input file is already in the themes folder
    input_in_themes_folder = themes_folder and os.path.dirname(live10_file) == themes_folder

    # Offer appropriate options based on input file location
    print("Where would you like to save the converted theme?")

    if not input_in_themes_folder:
        print("1. Same directory as the input file")
        print("2. Ableton Themes folder") if themes_folder else None
        print("3. Custom location")
        
        while True:
            try:
                max_choice = 3 if themes_folder else 2
                choice = int(input(f"Enter your choice (1-{max_choice}): "))
                if choice == 1:
                    output_dir = os.path.dirname(live10_file)
                    break
                elif choice == 2 and themes_folder:
                    output_dir = themes_folder
                    break
                elif choice == 3 or (choice == 2 and not themes_folder):
                    output_dir = get_file_path("Enter the full path where you want to save the converted theme: ", 
                                            default_dir=os.path.expanduser("~"), 
                                            must_exist=False)
                    break
                else:
                    print(f"Invalid choice. Please enter a number between 1 and {max_choice}.")
            except ValueError:
                print("Please enter a valid number.")
    else:
        # Input file is already in themes folder
        print("1. Ableton Themes folder (same as input file)")
        print("2. Custom location")
        
        while True:
            try:
                choice = int(input("Enter your choice (1-2): "))
                if choice == 1:
                    output_dir = themes_folder
                    break
                elif choice == 2:
                    output_dir = get_file_path("Enter the full path where you want to save the converted theme: ", 
                                            default_dir=os.path.expanduser("~"), 
                                            must_exist=False)
                    break
                else:
                    print("Invalid choice. Please enter either 1 or 2.")
            except ValueError:
                print("Please enter a valid number.")
    
    # Step 4: Convert the theme
    print("\nSTEP 4: Converting theme...")
    result = convert_theme(live10_file, live12_template_file, output_dir)
    
    if result:
        print("\nConversion complete!")
        print(f"The converted theme has been saved to: {result}")
        
        # Ask if user wants to copy to Ableton Themes folder
        if themes_folder and os.path.dirname(result) != themes_folder:
            copy_choice = input("\nWould you like to copy the theme to the Ableton Themes folder? (y/n): ").lower()
            if copy_choice == 'y' or copy_choice == 'yes':
                import shutil
                try:
                    dest_path = os.path.join(themes_folder, os.path.basename(result))
                    shutil.copy2(result, dest_path)
                    print(f"Theme copied to: {dest_path}")
                except Exception as e:
                    print(f"Error copying theme: {str(e)}")
    else:
        print("\nConversion failed. Please check the errors above.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
    
    input("\nPress Enter to exit...")