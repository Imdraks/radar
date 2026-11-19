"""Bounded image decoding and metadata-free profile thumbnails."""
from io import BytesIO
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import HTTPException

MAX_UPLOAD = 2 * 1024 * 1024
MAX_PIXELS = 4_000_000


def thumbnail(content: bytes) -> bytes:
    if not content or len(content) > MAX_UPLOAD:
        raise HTTPException(413, 'Choisissez une image de 2 Mo maximum.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('Unsupported format')
                if source.width * source.height > MAX_PIXELS:
                    raise ValueError('Image too large')
                source.load()
                oriented = ImageOps.exif_transpose(source)
                resized = ImageOps.fit(oriented, (256, 256), method=Image.Resampling.LANCZOS).convert('RGBA')
                image = Image.new('RGB', (256, 256), 'white')
                image.paste(resized, mask=resized.getchannel('A'))
                output = BytesIO()
                image.save(output, format='JPEG', quality=82, optimize=True)
        result = output.getvalue()
        if len(result) > 64 * 1024:
            raise ValueError('Thumbnail too large')
        return result
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, OverflowError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(422, 'Image invalide : utilisez un fichier JPEG, PNG ou WebP de 4 millions de pixels maximum.') from exc
