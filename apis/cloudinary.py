import os
import cloudinary
import cloudinary.uploader

NAME = os.environ.get("CLOUDINARY_NAME")
API_KEY = os.environ.get("CLOUDINARY_API_KEY")
SECRET = os.environ.get("CLOUDINARY_SECRET")

cloudinary.config(
    cloud_name=NAME,
    api_key=API_KEY,
    api_secret=SECRET,
    secure=True
)
