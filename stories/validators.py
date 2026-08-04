from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_upload_size(uploaded_file):
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError("File is too large; the limit is 10 MB.")
