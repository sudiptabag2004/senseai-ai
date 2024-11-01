from typing import List, Tuple, Dict
import pdf2image
import pypdf
from PIL import Image


def get_pdf_args(
    max_pages: int = None,
    first_page: int = None,
    last_page: int = None,
) -> Dict:
    if not first_page:
        first_page = 1

    if not last_page and not max_pages:
        raise ValueError("Either of last_page or max_pages must be not None")

    if not last_page:
        last_page = first_page + max_pages - 1

    return first_page, last_page


def get_raw_images_from_pdf(
    pdf_path: str,
    pdf_page_dims: Tuple[float, float],
    max_pages: int = None,
    first_page: int = None,
    last_page: int = None,
    resize: bool = True,
    resize_scale: float = 1.0,
) -> List[Image.Image]:
    """Given a pdf path, return the raw images of the first `max_pages` number of pages adjusted to match the height and width of the pdf"""
    first_page, last_page = get_pdf_args(max_pages, first_page, last_page)

    args = {"pdf_path": pdf_path, "first_page": first_page, "last_page": last_page}
    if resize:
        # aspect_ratio = (
        #     input_pdf.pages[0].mediabox.width / input_pdf.pages[0].mediabox.height
        # )
        # height = min(input_pdf.pages[0].mediabox.height, 800)
        # width = int(aspect_ratio * height)

        args["size"] = (
            pdf_page_dims[0] * resize_scale,
            pdf_page_dims[1] * resize_scale,
        )

        # if the page rotation is 90/270, we need to switch the width and height
        # so that the image is in the correct orientation
        # Ref: https://github.com/Belval/pdf2image/issues/272
        page_rotation = int(pdf2image.pdfinfo_from_path(pdf_path).get("Page rot", "0"))
        if page_rotation % 180:
            args["size"] = (args["size"][1], args["size"][0])

    return pdf2image.convert_from_path(**args)


def get_links_from_pdf(pdf: pypdf.PdfReader) -> List[str]:
    links = []
    for page in pdf.pages:
        if "/Annots" in page:
            for annot in page["/Annots"]:
                annotation = annot.get_object()
                if annotation["/Subtype"] == "/Link" and "/A" in annotation:
                    if "/URI" in annotation["/A"]:
                        links.append(annotation["/A"]["/URI"])
    return links
