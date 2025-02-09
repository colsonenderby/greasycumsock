# image_selector.py

import os
import random
from tag_grouping import tag_categories  # Ensure tag_grouping.py is in the same directory or in PYTHONPATH

# Define Category Weights as per user specification
CATEGORY_WEIGHTS = {
    "Sexual & Explicit Content": 6,
    "Relationship Dynamics": 5,
    "Emotions": 4,
    "Interaction Styles": 3,
    "Intentions & Behaviors": 3,
    "Topics & Activities": 2,
    "Values & Ethics": 1,
    "Miscellaneous": 1
}

# Define Category Hierarchy for tie-breaking (higher priority first)
CATEGORY_HIERARCHY = [
    "Sexual & Explicit Content",
    "Relationship Dynamics",
    "Emotions",
    "Interaction Styles",
    "Intentions & Behaviors",
    "Topics & Activities",
    "Values & Ethics",
    "Miscellaneous"
]

# Define Subcategory Hierarchy within Primary Categories for tie-breaking
SUBCATEGORY_HIERARCHY = {
    "Emotions": [
        "Positive Emotions",
        "Negative Emotions",
        "Mixed Emotions",
        "Neutral Emotions"
    ],
    "Relationship Dynamics": [
        "Positive Relationships",
        "Negative Relationships",
        "Unclear Relationships"
    ],
    # Add similar hierarchies for other categories if needed
}

# Define the base path for images
IMAGE_BASE_PATH = r"C:\Users\colso\Documents\Side_Bitch\New_gpt_interface\base_images\toxic"

# Define the default image path
DEFAULT_IMAGE_PATH = r"C:\Users\colso\Documents\Side_Bitch\New_gpt_interface\base_images\toxic\Miscellaneous\Others\116455_A gothic realistic anime-style girlfriend with sle_xl-1024-v1-0.png"  # Update as needed

def map_tag_to_category(tag):
    """
    Maps a single tag to its primary category and subcategory.

    Args:
        tag (str): The context tag.

    Returns:
        tuple: (Primary Category, Subcategory)
    """
    for primary_category, subcategories in tag_categories.items():
        for subcategory, tags in subcategories.items():
            if tag.lower() in [t.lower() for t in tags]:
                return primary_category, subcategory
    # If tag not found, assign to Miscellaneous > Others
    return "Miscellaneous", "Others"

def categorize_tags(context_tags):
    """
    Categorizes all tags from user and assistant responses.

    Args:
        context_tags (dict): Dictionary containing tags from 'user' and 'assistant'.

    Returns:
        list of dict: List containing tag information with category mappings.
    """
    consolidated_tags = []

    for role, tags in context_tags.items():
        for tag_info in tags:
            tag = tag_info.get('tag', '').strip()
            if tag:
                primary, subcategory = map_tag_to_category(tag)
                consolidated_tags.append({
                    "tag": tag,
                    "primary": primary,
                    "subcategory": subcategory,
                    "score": tag_info.get('score', 0),
                    "role": role  # To differentiate user vs assistant tags if needed
                })
    return consolidated_tags

def calculate_category_scores(mapped_tags):
    """
    Calculates the cumulative scores for each primary category based on mapped tags.

    Args:
        mapped_tags (list of dict): List containing tag information with category mappings.

    Returns:
        dict: Dictionary with primary categories as keys and their cumulative scores as values.
    """
    category_scores = {category: 0 for category in CATEGORY_WEIGHTS.keys()}

    for tag_info in mapped_tags:
        primary = tag_info["primary"]
        weight = CATEGORY_WEIGHTS.get(primary, 1)  # Default weight = 1
        # Multiply category weight by absolute score to emphasize intensity
        category_scores[primary] += weight * abs(tag_info["score"])

    return category_scores

def determine_dominant_category(category_scores):
    """
    Determines the dominant category based on cumulative scores and predefined hierarchy.

    Args:
        category_scores (dict): Dictionary with primary categories as keys and their cumulative scores as values.

    Returns:
        str: The dominant primary category.
    """
    # Find the maximum score
    max_score = max(category_scores.values())
    # Find all categories that have the maximum score
    top_categories = [cat for cat, score in category_scores.items() if score == max_score]

    if len(top_categories) == 1:
        return top_categories[0]
    else:
        # Tie-breaking based on hierarchy
        for category in CATEGORY_HIERARCHY:
            if category in top_categories:
                return category
    return "Miscellaneous"  # Fallback

def select_subcategory(mapped_tags, dominant_category):
    """
    Selects the most relevant subcategory within the dominant category based on tag frequency.

    Args:
        mapped_tags (list of dict): List containing tag information with category mappings.
        dominant_category (str): The dominant primary category.

    Returns:
        str: The selected subcategory.
    """
    # Filter tags that belong to the dominant category
    dominant_tags = [tag for tag in mapped_tags if tag["primary"] == dominant_category]

    # Count occurrences per subcategory
    subcategory_counts = {}
    for tag in dominant_tags:
        subcat = tag["subcategory"]
        subcategory_counts[subcat] = subcategory_counts.get(subcat, 0) + 1

    if not subcategory_counts:
        return "Others"

    # Find the subcategory with the highest count
    max_count = max(subcategory_counts.values())
    top_subcategories = [subcat for subcat, count in subcategory_counts.items() if count == max_count]

    if len(top_subcategories) == 1:
        return top_subcategories[0]
    else:
        # Tie-breaking based on subcategory hierarchy
        hierarchy = SUBCATEGORY_HIERARCHY.get(dominant_category, [])
        for subcat in hierarchy:
            if subcat in top_subcategories:
                return subcat
        return top_subcategories[0]  # Fallback

def select_image(dominant_category, selected_subcategory):
    """
    Selects a random image from the specified category and subcategory folder.

    Args:
        dominant_category (str): The dominant primary category.
        selected_subcategory (str): The selected subcategory within the dominant category.

    Returns:
        str: Path to the selected image.
    """
    # Construct the image folder path
    image_folder = os.path.join(IMAGE_BASE_PATH, dominant_category, selected_subcategory)

    # Check if the folder exists
    if not os.path.isdir(image_folder):
        print(f"Folder not found: {image_folder}. Using default image.")
        return DEFAULT_IMAGE_PATH

    # List all image files in the folder
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    available_images = [img for img in os.listdir(image_folder) if img.lower().endswith(valid_extensions)]

    if not available_images:
        print(f"No images found in: {image_folder}. Using default image.")
        return DEFAULT_IMAGE_PATH

    # Randomly select an image
    selected_image = random.choice(available_images)
    image_path = os.path.join(image_folder, selected_image)
    return image_path

def get_selected_image(context_tags):
    """
    Main function to process context tags and return the selected image path.

    Args:
        context_tags (dict): Dictionary containing tags from 'user' and 'assistant'.

    Returns:
        str: Path to the selected image.
    """
    # Categorize tags
    mapped_tags = categorize_tags(context_tags)

    if not mapped_tags:
        print("No mapped tags found. Using default image.")
        return DEFAULT_IMAGE_PATH

    # Calculate category scores
    category_scores = calculate_category_scores(mapped_tags)

    # Determine dominant category
    dominant_category = determine_dominant_category(category_scores)

    # Select subcategory within dominant category
    selected_subcategory = select_subcategory(mapped_tags, dominant_category)

    # Select image path
    selected_image_path = select_image(dominant_category, selected_subcategory)

    return selected_image_path
