import pytest
from unittest.mock import MagicMock, patch, Mock
from fastapi import HTTPException, status
from io import BytesIO

from src.services.upload_file import UploadFileService


@pytest.fixture
def mock_file():
    file = MagicMock()
    file.content_type = "image/jpeg"
    file.file = BytesIO(b"fake image content")
    return file


@pytest.fixture
def upload_service():
    return UploadFileService(
        cloud_name="test_cloud", api_key="test_key", api_secret="test_secret"
    )


class TestUploadFileService:

    def test_upload_service_initialization(self, upload_service):
        assert upload_service.cloud_name == "test_cloud"
        assert upload_service.api_key == "test_key"
        assert upload_service.api_secret == "test_secret"

    @patch("src.services.upload_file.cloudinary.config")
    def test_upload_service_config_called(self, mock_config):
        UploadFileService(
            cloud_name="test_cloud", api_key="test_key", api_secret="test_secret"
        )

        mock_config.assert_called_once_with(
            cloud_name="test_cloud",
            api_key="test_key",
            api_secret="test_secret",
            secure=True,
        )

    @patch("src.services.upload_file.cloudinary.uploader.upload")
    @patch("src.services.upload_file.cloudinary.CloudinaryImage")
    def test_upload_file_success(self, mock_cloudinary_image, mock_upload, mock_file):
        mock_upload.return_value = {"version": "1234567890"}

        mock_image = MagicMock()
        mock_image.build_url.return_value = "https://res.cloudinary.com/test/image/upload/c_fill,h_250,w_250/v1234567890/RestApp/avatars/testuser"
        mock_cloudinary_image.return_value = mock_image

        result = UploadFileService.upload_file(mock_file, "testuser")

        assert (
            result
            == "https://res.cloudinary.com/test/image/upload/c_fill,h_250,w_250/v1234567890/RestApp/avatars/testuser"
        )
        mock_upload.assert_called_once_with(
            mock_file.file,
            public_id="RestApp/avatars/testuser",
            overwrite=True,
            transformation=[
                {"width": 250, "height": 250, "crop": "fill"},
                {"quality": "auto", "fetch_format": "auto"},
            ],
        )
        mock_cloudinary_image.assert_called_once_with("RestApp/avatars/testuser")
        mock_image.build_url.assert_called_once_with(
            width=250, height=250, crop="fill", version="1234567890"
        )

    def test_upload_file_invalid_content_type(self, mock_file):
        mock_file.content_type = "text/plain"

        with pytest.raises(HTTPException) as exc_info:
            UploadFileService.upload_file(mock_file, "testuser")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "content_type",
        ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"],
    )
    @patch("src.services.upload_file.cloudinary.uploader.upload")
    @patch("src.services.upload_file.cloudinary.CloudinaryImage")
    def test_upload_file_allowed_content_types(
        self, mock_cloudinary_image, mock_upload, content_type, mock_file
    ):
        mock_file.content_type = content_type
        mock_upload.return_value = {"version": "1234567890"}

        mock_image = MagicMock()
        mock_image.build_url.return_value = "https://test.url/image.jpg"
        mock_cloudinary_image.return_value = mock_image

        result = UploadFileService.upload_file(mock_file, "testuser")

        assert result == "https://test.url/image.jpg"
        mock_upload.assert_called_once()

    def test_upload_file_too_large(self):
        large_file = MagicMock()
        large_file.content_type = "image/jpeg"
        large_file.file = BytesIO(b"x" * (6 * 1024 * 1024))  # 6MB file

        with pytest.raises(HTTPException) as exc_info:
            UploadFileService.upload_file(large_file, "testuser")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_file_size_limit_boundary(self):
        boundary_file = MagicMock()
        boundary_file.content_type = "image/jpeg"
        boundary_file.file = BytesIO(b"x" * (5 * 1024 * 1024))  # Exactly 5MB

        with patch(
            "src.services.upload_file.cloudinary.uploader.upload"
        ) as mock_upload:
            with patch(
                "src.services.upload_file.cloudinary.CloudinaryImage"
            ) as mock_cloudinary_image:
                mock_upload.return_value = {"version": "1234567890"}
                mock_image = MagicMock()
                mock_image.build_url.return_value = "https://test.url/image.jpg"
                mock_cloudinary_image.return_value = mock_image

                result = UploadFileService.upload_file(boundary_file, "testuser")
                assert result == "https://test.url/image.jpg"

    @patch("src.services.upload_file.cloudinary.uploader.upload")
    def test_upload_file_cloudinary_error(self, mock_upload, mock_file):
        mock_upload.side_effect = Exception("Cloudinary service unavailable")

        with pytest.raises(HTTPException) as exc_info:
            UploadFileService.upload_file(mock_file, "testuser")

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("src.services.upload_file.cloudinary.uploader.upload")
    @patch("src.services.upload_file.cloudinary.CloudinaryImage")
    def test_upload_file_different_usernames(
        self, mock_cloudinary_image, mock_upload, mock_file
    ):
        mock_upload.return_value = {"version": "1234567890"}
        mock_image = MagicMock()
        mock_image.build_url.return_value = "https://test.url/image.jpg"
        mock_cloudinary_image.return_value = mock_image

        usernames = ["user1", "admin_user", "test.user", "user-123"]

        for username in usernames:
            UploadFileService.upload_file(mock_file, username)

            expected_public_id = f"RestApp/avatars/{username}"
            mock_upload.assert_called_with(
                mock_file.file,
                public_id=expected_public_id,
                overwrite=True,
                transformation=[
                    {"width": 250, "height": 250, "crop": "fill"},
                    {"quality": "auto", "fetch_format": "auto"},
                ],
            )
            mock_cloudinary_image.assert_called_with(expected_public_id)

    def test_upload_file_file_seeking_behavior(self):
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.file = MagicMock()

        mock_file.file.seek.return_value = None
        mock_file.file.tell.return_value = 1024  # 1KB file

        with patch(
            "src.services.upload_file.cloudinary.uploader.upload"
        ) as mock_upload:
            with patch(
                "src.services.upload_file.cloudinary.CloudinaryImage"
            ) as mock_cloudinary_image:
                mock_upload.return_value = {"version": "1234567890"}
                mock_image = MagicMock()
                mock_image.build_url.return_value = "https://test.url/image.jpg"
                mock_cloudinary_image.return_value = mock_image

                UploadFileService.upload_file(mock_file, "testuser")

                assert mock_file.file.seek.call_count == 2
                mock_file.file.seek.assert_any_call(0, 2)  # Seek to end for size
                mock_file.file.seek.assert_any_call(0)  # Seek back to beginning
                mock_file.file.tell.assert_called_once()  # Get file size

    @patch("src.services.upload_file.cloudinary.uploader.upload")
    @patch("src.services.upload_file.cloudinary.CloudinaryImage")
    def test_upload_file_transformation_parameters(
        self, mock_cloudinary_image, mock_upload, mock_file
    ):
        mock_upload.return_value = {"version": "1234567890"}
        mock_image = MagicMock()
        mock_image.build_url.return_value = "https://test.url/image.jpg"
        mock_cloudinary_image.return_value = mock_image

        UploadFileService.upload_file(mock_file, "testuser")

        call_args = mock_upload.call_args
        transformation = call_args[1]["transformation"]

        assert len(transformation) == 2
        assert {"width": 250, "height": 250, "crop": "fill"} in transformation
        assert {"quality": "auto", "fetch_format": "auto"} in transformation

        assert call_args[1]["public_id"] == "RestApp/avatars/testuser"
        assert call_args[1]["overwrite"] is True

    @patch("src.services.upload_file.cloudinary.uploader.upload")
    @patch("src.services.upload_file.cloudinary.CloudinaryImage")
    def test_upload_file_build_url_parameters(
        self, mock_cloudinary_image, mock_upload, mock_file
    ):
        mock_upload.return_value = {"version": "1234567890"}
        mock_image = MagicMock()
        mock_image.build_url.return_value = "https://test.url/image.jpg"
        mock_cloudinary_image.return_value = mock_image

        UploadFileService.upload_file(mock_file, "testuser")

        mock_image.build_url.assert_called_once_with(
            width=250, height=250, crop="fill", version="1234567890"
        )


class TestUploadFileServiceErrorScenarios:

    def test_upload_file_http_exception_propagation(self, mock_file):
        mock_file.content_type = "application/pdf"

        with pytest.raises(HTTPException) as exc_info:
            UploadFileService.upload_file(mock_file, "testuser")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @patch("src.services.upload_file.cloudinary.CloudinaryImage")
    def test_upload_file_cloudinary_image_error(self, mock_cloudinary_image, mock_file):
        with patch(
            "src.services.upload_file.cloudinary.uploader.upload"
        ) as mock_upload:
            mock_upload.return_value = {"version": "1234567890"}
            mock_cloudinary_image.side_effect = Exception("CloudinaryImage error")

            with pytest.raises(HTTPException) as exc_info:
                UploadFileService.upload_file(mock_file, "testuser")

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
