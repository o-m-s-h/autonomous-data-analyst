import os
import uuid
from fastapi import UploadFile
from app.config import UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_dataset(file: UploadFile) -> tuple[str, str]:
    """
    Save uploaded CSV locally.

    Returns:
        dataset_id
        file_path
    """

    dataset_id = str(uuid.uuid4())

    filename = f"{dataset_id}.csv"

    file_path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    return dataset_id, file_path