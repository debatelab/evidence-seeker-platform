#!/usr/bin/env python3
"""
Script to fix missing data in existing documents.
This script can be run to populate missing file_size, mime_type, and other fields
for documents that were created before these fields were properly implemented.
"""

import logging
import os
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.models.document import Document

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_document_data() -> None:
    """Fix missing data in existing documents"""
    db = SessionLocal()

    try:
        # Import select for SQLAlchemy 2.0 compatibility
        from sqlalchemy import select

        # Get all documents
        result = db.execute(select(Document))
        documents = result.scalars().all()
        logger.info(f"Found {len(documents)} documents to check")

        fixed_count = 0

        for doc in documents:
            needs_update = False

            # Fix file_size if missing or zero
            if doc.file_size is None or doc.file_size == 0:
                try:
                    if os.path.exists(doc.file_path):
                        file_size = os.path.getsize(doc.file_path)
                        doc.file_size = file_size  # type: ignore
                        needs_update = True
                        logger.info(
                            f"Fixed file_size for document {doc.id}: {file_size} bytes"
                        )
                    else:
                        # Set default size if file doesn't exist
                        doc.file_size = 0  # type: ignore
                        needs_update = True
                        logger.warning(
                            f"File not found for document {doc.id}, setting size to 0"
                        )
                except Exception as e:
                    logger.error(f"Error getting file size for document {doc.id}: {e}")
                    doc.file_size = 0  # type: ignore
                    needs_update = True

            # Fix mime_type if missing or generic
            if (
                doc.mime_type is None
                or doc.mime_type == "application/octet-stream"
                or doc.mime_type == ""
            ):

                # Determine mime type from file extension
                mime_type = Document.get_mime_type_from_filename(str(doc.file_path))
                if mime_type != "application/octet-stream":
                    doc.mime_type = mime_type  # type: ignore
                    needs_update = True
                    logger.info(f"Fixed mime_type for document {doc.id}: {mime_type}")
                else:
                    # Keep a generic type if we can't determine it
                    doc.mime_type = "application/octet-stream"  # type: ignore
                    if needs_update is False:
                        needs_update = True

            # Commit changes if document was updated
            if needs_update:
                db.commit()
                db.refresh(doc)
                fixed_count += 1

        logger.info(f"Fixed {fixed_count} documents")
        print(f"Successfully fixed {fixed_count} documents with missing data")

    except Exception as e:
        logger.error(f"Error fixing document data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting document data fix...")
    fix_document_data()
    print("Document data fix completed!")
