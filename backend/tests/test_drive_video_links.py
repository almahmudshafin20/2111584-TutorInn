import pytest
from pydantic import ValidationError

from app.schemas import GroupTaskCreate


def test_group_task_accepts_secure_google_drive_video_share_links():
    payload = GroupTaskCreate(
        title="Watch lesson",
        video_url="https://drive.google.com/file/d/abc_123-XYZ/view?usp=sharing",
    )
    assert payload.video_url == "https://drive.google.com/file/d/abc_123-XYZ/view?usp=sharing"


def test_group_task_accepts_google_drive_open_link():
    payload = GroupTaskCreate(
        title="Watch lesson",
        video_url="https://drive.google.com/open?id=abc_123-XYZ",
    )
    assert payload.video_url == "https://drive.google.com/open?id=abc_123-XYZ"


@pytest.mark.parametrize("url", [
    "http://drive.google.com/file/d/abc123/view",
    "https://evil.example/file/d/abc123/view",
    "https://drive.google.com/file/d/invalid%20id/view",
    "javascript:alert(1)",
])
def test_group_task_rejects_non_https_or_non_drive_video_links(url):
    with pytest.raises(ValidationError):
        GroupTaskCreate(title="Watch lesson", video_url=url)
