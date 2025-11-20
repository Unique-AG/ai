import base64
import io

from PIL.ImageFile import ImageFile


def image_to_base64(image: ImageFile) -> str:
    # Convert to RGB if needed
    img = image
    if image.mode != "RGB":
        img = image.convert("RGB")

    # Create BytesIO object to store compressed image
    img_byte_arr = io.BytesIO()

    # Save with compression
    img.save(img_byte_arr, format="JPEG", quality=85, optimize=True)
    img_byte_arr.seek(0)

    # Encode compressed image
    encoded_string = base64.b64encode(img_byte_arr.getvalue())
    image_string = encoded_string.decode("utf-8")

    image_string = "data:image/jpeg;base64," + image_string
    return image_string
