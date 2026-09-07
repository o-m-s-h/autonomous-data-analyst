from fastapi import APIRouter, UploadFile, File, HTTPException

from app.storage.dataset_manager import save_dataset
from app.api.analysis import register_dataset


router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)


@router.post("/")
async def upload_csv(
    file: UploadFile = File(...)
):

    if not file.filename.endswith(".csv"):

        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported."
        )

    dataset_id, file_path = await save_dataset(
        file
    )

    register_dataset(
        dataset_id,
        file_path
    )

    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "message": "CSV uploaded successfully."
    }