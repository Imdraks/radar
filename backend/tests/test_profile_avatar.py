"""Profile photos use authenticated ownership and bounded image decoding."""
from io import BytesIO
import base64
import pytest
from PIL import Image
from app.services.profile_avatar import thumbnail, MAX_UPLOAD
from fastapi import HTTPException


def image_bytes(size=(100, 80), kind='PNG'):
    output = BytesIO()
    image = Image.new('RGB', size, 'purple')
    exif = Image.Exif()
    exif[315] = 'PRIVATE TEST AUTHOR'
    image.save(output, format=kind, exif=exif)
    return output.getvalue()


def test_thumbnail_strips_metadata_and_has_bounded_dimensions():
    encoded = thumbnail(image_bytes())
    with Image.open(BytesIO(encoded)) as image:
        assert image.format == 'JPEG' and image.size == (256, 256)
        assert not image.getexif()
    assert len(encoded) <= 65536 and b'PRIVATE TEST AUTHOR' not in encoded


@pytest.mark.parametrize('content,status', [(b'<svg onload="alert(1)"/>', 422), (b'invalid', 422), (b'a' * (MAX_UPLOAD + 1), 413)])
def test_rejects_unsafe_or_oversized_data(content, status):
    with pytest.raises(HTTPException) as exc:
        thumbnail(content)
    assert exc.value.status_code == status


def test_rejects_excessive_decoded_pixel_count():
    with pytest.raises(HTTPException) as exc:
        thumbnail(image_bytes((2100, 2100)))
    assert exc.value.status_code == 422


def test_upload_requires_authentication(client):
    response = client.post('/api/v1/auth/me/avatar', files={'file': ('photo.png', image_bytes(), 'image/png')})
    assert response.status_code == 401
    assert client.delete('/api/v1/auth/me/avatar').status_code == 401


def test_custom_photo_only_changes_authenticated_account_and_preserves_sso(client, actors, headers, db_session):
    users, _ = actors
    for index, user in enumerate(users):
        user.email = f'avatar-user{index}@example.com'
    users[0].avatar_url = 'https://lh3.googleusercontent.com/test-google-photo'
    db_session.commit()
    response = client.post('/api/v1/auth/me/avatar?user_id=' + str(users[1].id),
                           headers=headers(0), files={'file': ('photo.png', image_bytes(), 'image/png')})
    assert response.status_code == 200, response.text
    uri = response.json()['avatar_url']
    assert uri.startswith('data:image/jpeg;base64,')
    db_session.refresh(users[0])
    assert base64.b64decode(uri.split(',', 1)[1]) == users[0].avatar_image
    assert users[0].avatar_url == 'https://lh3.googleusercontent.com/test-google-photo'
    db_session.refresh(users[1])
    assert users[1].avatar_image is None
    assert client.get('/api/v1/auth/me', headers=headers(1)).json()['avatar_url'] is None
    assert client.get('/api/v1/auth/me', headers=headers(0)).json()['avatar_url'] == uri
    export = client.get('/api/v1/privacy/account-export', headers=headers(0))
    assert export.json()['account']['profile_avatar_url'] == uri
    removed = client.delete('/api/v1/auth/me/avatar', headers=headers(0))
    assert removed.status_code == 200
    assert removed.json()['avatar_url'] == users[0].avatar_url
    db_session.refresh(users[0])
    assert users[0].avatar_image is None


def test_invalid_upload_does_not_overwrite_previous_photo(client, actors, headers, db_session):
    user = actors[0][0]
    user.avatar_image = thumbnail(image_bytes())
    db_session.commit()
    before = user.avatar_image
    response = client.post('/api/v1/auth/me/avatar', headers=headers(0),
                           files={'file': ('fake.png', b'not a real image', 'image/png')})
    assert response.status_code == 422
    db_session.refresh(user)
    assert user.avatar_image == before
