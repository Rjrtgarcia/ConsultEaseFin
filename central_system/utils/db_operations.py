"""
Database operation utilities for ConsultEase.
Provides common database operations with retry logic.
"""
import logging
from sqlalchemy.exc import SQLAlchemyError
from ..models.base import db_operation_with_retry

logger = logging.getLogger(__name__)


@db_operation_with_retry(max_retries=3)
def get_by_id(db, model_class, id):
    """
    Get a model instance by ID with retry logic.

    Args:
        db: Database session
        model_class: SQLAlchemy model class
        id: Primary key ID

    Returns:
        Model instance or None if not found
    """
    return db.query(model_class).filter(model_class.id == id).first()


@db_operation_with_retry(max_retries=3)
def create_entity(db, model_class, **kwargs):
    """
    Create a new entity with retry logic.

    Args:
        db: Database session
        model_class: SQLAlchemy model class
        **kwargs: Entity attributes

    Returns:
        Created entity
    """
    entity = model_class(**kwargs)
    db.add(entity)
    db.flush()  # Flush to get the ID
    return entity


@db_operation_with_retry(max_retries=3)
def update_entity(db, entity, **kwargs):
    """
    Update an entity with retry logic.

    Args:
        db: Database session
        entity: Entity to update
        **kwargs: Attributes to update

    Returns:
        Updated entity
    """
    for key, value in kwargs.items():
        setattr(entity, key, value)
    db.flush()
    return entity


@db_operation_with_retry(max_retries=3)
def delete_entity(db, entity):
    """
    Delete an entity with retry logic.

    Args:
        db: Database session
        entity: Entity to delete

    Returns:
        True if successful
    """
    db.delete(entity)
    return True


@db_operation_with_retry(max_retries=3)
def get_all(db, model_class, **filters):
    """
    Get all entities of a model class with optional filters.

    Args:
        db: Database session
        model_class: SQLAlchemy model class
        **filters: Optional filters

    Returns:
        List of entities
    """
    query = db.query(model_class)

    # Apply filters if provided
    for attr, value in filters.items():
        if hasattr(model_class, attr):
            query = query.filter(getattr(model_class, attr) == value)

    return query.all()


def safe_commit(db):
    """
    Safely commit changes to the database with error handling.

    Args:
        db: Database session

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error committing changes: {e}")
        return False
