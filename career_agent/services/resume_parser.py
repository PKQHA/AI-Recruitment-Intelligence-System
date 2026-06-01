"""
Resume file text extraction for the Web product layer.

Supported inputs:
- PDF resumes through pypdf
- Image resumes through optional OCR with pytesseract
"""

from __future__ import annotations

from io import BytesIO


class ResumeParser:
    """Extract plain text from uploaded resume files."""

    PDF_CONTENT_TYPES = {"application/pdf"}
    IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

    def parse(self, content: bytes, filename: str, content_type: str | None = None) -> str:
        normalized_type = (content_type or "").lower()
        normalized_name = filename.lower()

        if normalized_type in self.PDF_CONTENT_TYPES or normalized_name.endswith(".pdf"):
            return self._parse_pdf(content)

        if normalized_type in self.IMAGE_CONTENT_TYPES or normalized_name.endswith(
            (".png", ".jpg", ".jpeg", ".webp")
        ):
            return self._parse_image(content)

        raise ValueError("仅支持 PDF、PNG、JPG、JPEG 或 WEBP 格式的简历文件。")

    def _parse_pdf(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "未安装 pypdf，无法解析 PDF 简历。请先执行：pip install -r requirements.txt"
            ) from error

        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(page.strip() for page in pages if page.strip()).strip()

        if not text:
            raise ValueError("PDF 中未提取到文本。如果这是扫描版简历，请上传图片版或启用 OCR。")

        return text

    def _parse_image(self, content: bytes) -> str:
        try:
            from PIL import Image
            import pytesseract
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "未安装图片 OCR 依赖，无法解析图片简历。请安装 pillow、pytesseract，"
                "并确保本机已安装 Tesseract OCR。"
            ) from error

        image = Image.open(BytesIO(content))
        text = pytesseract.image_to_string(image, lang="chi_sim+eng").strip()

        if not text:
            raise ValueError("图片中未识别到有效文本，请尝试上传更清晰的简历图片。")

        return text
