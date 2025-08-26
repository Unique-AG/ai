import base64
import math
import re
from enum import Enum
from io import BytesIO

from PIL import Image


class DetailLevel(Enum):
    LOW = "low"
    HIGH = "high"


# https://platform.openai.com/docs/guides/vision/calculating-costs#calculating-costs
def calculate_image_tokens(width, height, detail: DetailLevel):
    """
    Calculate the token cost of an image based on its dimensions and detail level.
    NOTE: While we followed the documentation provided by openai to calculate image token cost, in practice,
    we notice that this function overestimate the number of tokens consumed by the model.

    Parameters:
    - width (int): The width of the image in pixels.
    - height (int): The height of the image in pixels.
    - detail (str): The detail level, either "low" or "high".

    Returns:
    - int: The token cost of the image.
    """
    # Base cost for low detail
    if detail == DetailLevel.LOW:
        return 85

    # Scaling for high detail
    # Scale down to fit within 2048x2048 square
    max_long_dim = 2048
    long_dim = max(width, height)
    if long_dim > max_long_dim:
        scale_factor = long_dim / max_long_dim
        width = int(width / scale_factor)
        height = int(height / scale_factor)

    # Scale down the shortest side to 768
    max_short_dim = 768
    short_dim = min(width, height)
    if short_dim > max_short_dim:
        scale_factor = short_dim / max_short_dim
        width = int(width / scale_factor)
        height = int(height / scale_factor)

    # Step 3: Calculate the number of 512x512 tiles
    tiles = math.ceil(width / 512) * math.ceil(height / 512)
    # Step 4: Compute token cost
    token_cost = (tiles * 170) + 85
    return token_cost


def calculate_image_tokens_from_base64(base64_string: str):
    base64_string = remove_base64_header(base64_string)
    image = Image.open(BytesIO(base64.b64decode(base64_string)))
    # DETAIL LEVEL HIGH IS THE DEFAULT TO BE ON THE SAFE SIDE
    return calculate_image_tokens(image.width, image.height, DetailLevel.HIGH)


def remove_base64_header(base64_string: str):
    header_pattern = r"^data:image/\w+;base64,"
    return re.sub(header_pattern, "", base64_string)
