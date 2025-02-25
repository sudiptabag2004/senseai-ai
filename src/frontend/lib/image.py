import base64
from io import BytesIO
from typing import List
from PIL import Image, ImageOps
import imgkit
import tempfile


def get_image_aspect_ratio(image_path: str) -> float:
    with Image.open(image_path) as img:
        return img.height / img.width


def read_svg(image_path: str, custom_class: str = ""):
    svg_content = open(image_path, "r").read()
    if not custom_class:
        return svg_content

    return svg_content.replace("<svg", f'<svg class="{custom_class}"', 1)


def get_image_embed_for_html(
    image_path: str, width: int = 200, custom_class: str = ""
) -> str:
    if image_path.endswith(".svg"):
        return read_svg(image_path, custom_class)

    file_ = open(image_path, "rb")
    contents = file_.read()
    data_url = base64.b64encode(contents).decode("utf-8")
    file_.close()

    image_aspect_ratio = get_image_aspect_ratio(image_path)

    height = int(width * image_aspect_ratio)

    return f'<img src="data:image/gif;base64,{data_url}" alt="cat gif" width="{width}" height="{height}" class="{custom_class}">'


def standardize_image_size(
    src_image_path: str, dest_image_path: str, width: int, height: int
):
    with Image.open(src_image_path) as img:
        # Calculate the aspect ratio of the original image
        aspect_ratio = img.width / img.height

        # Calculate the aspect ratio of the desired size
        target_aspect_ratio = width / height

        if aspect_ratio > target_aspect_ratio:
            # Image is wider than target, adjust height
            new_width = width
            new_height = int(width / aspect_ratio)
        else:
            # Image is taller than target, adjust width
            new_height = height
            new_width = int(height * aspect_ratio)

        # Resize the image while maintaining aspect ratio
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)

        # Create a new image with the desired size and paste the resized image
        new_img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        paste_x = (width - new_width) // 2
        paste_y = (height - new_height) // 2
        new_img.paste(img_resized, (paste_x, paste_y))

        # Save the standardized image
        new_img.save(dest_image_path)

    return dest_image_path


def add_padding_to_image(
    source_image_path: str, dest_image_path: str, padding: int = 10
) -> str:
    with Image.open(source_image_path) as img:
        img_with_padding = ImageOps.expand(img, border=padding, fill=(255, 255, 255, 0))
        img_with_padding.save(dest_image_path)


def convert_html_to_image(html: str, resolution: int = 300) -> Image:
    # create a temporary file and save the html to it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
        temp_file.write(html.encode("utf-8"))
        temp_file.flush()

        # create a temporary file to save the image to
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".jpg"
        ) as temp_image_file:
            options = {
                "format": "jpg",
                "quality": "100",
                "zoom": str(resolution / 96),  # Convert DPI to zoom factor
            }
            imgkit.from_file(temp_file.name, temp_image_file.name, options=options)
            image = Image.open(temp_image_file.name)
            # return image.crop((0, 0, image_dims[0], image_dims[1]))
            return image


def get_base64_image(image: Image) -> str:
    """base64 encode the given image"""
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_base64_images(
    raw_images: List[Image.Image],
) -> List[str]:
    """Convert the raw images to base64 encoded images"""
    return [get_base64_image(image) for image in raw_images]
