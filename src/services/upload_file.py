import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status


class UploadFileService:
    """Service for handling file uploads to Cloudinary.

    This service provides functionality to upload and manage user avatar images
    using Cloudinary's cloud storage and transformation capabilities.
    """

    def __init__(self, cloud_name, api_key, api_secret):
        """Initialize the upload file service with Cloudinary credentials.

        Args:
            cloud_name (str): Cloudinary cloud name.
            api_key (str): Cloudinary API key.
            api_secret (str): Cloudinary API secret.
        """
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file, username) -> str:
        """Upload a user avatar file to Cloudinary.

        Validates the file type and size, then uploads it to Cloudinary with
        automatic transformations for avatar optimization.

        Args:
            file: The uploaded file object containing the image data.
            username (str): Username to use for the public ID and file organization.

        Returns:
            str: The URL of the uploaded and transformed image.

        Raises:
            HTTPException: If file validation fails (unsupported type, too large)
                          or if the upload process encounters an error.
        """
        try:
            allowed_types = [
                "image/jpeg",
                "image/jpg",
                "image/png",
                "image/gif",
                "image/webp",
            ]
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Only image files are allowed. Supported formats: JPEG, PNG, GIF, WebP",
                )

            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)

            if file_size > 5 * 1024 * 1024:  # 5MB
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File too large. Maximum size is 5MB",
                )

            public_id = f"RestApp/avatars/{username}"
            r = cloudinary.uploader.upload(
                file.file,
                public_id=public_id,
                overwrite=True,
                transformation=[
                    {"width": 250, "height": 250, "crop": "fill"},
                    {"quality": "auto", "fetch_format": "auto"},
                ],
            )

            src_url = cloudinary.CloudinaryImage(public_id).build_url(
                width=250, height=250, crop="fill", version=r.get("version")
            )
            return src_url

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload avatar: {str(e)}",
            )
