import datetime
from typing import Annotated

from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app._crud.projects import (
    event_message_reactions as crud_event_message_reactions,
)
from app._crud.projects import event_messages as crud_event_messages
from app._dependencies.authentication import get_user
from app.dependencies import (
    get_project_name_short_async,
)
from app.interfaces import UserAuthed
from core import enumerations

router = APIRouter(
    prefix="/event-message-reactions",
    tags=["event_message_reactions"],
)


# --- Pydantic Schemas ---
class EventMessageReactionCreate(BaseModel):
    """todo"""

    event_message_id: int
    reaction_type: str  # 'thumbs_up', 'eyes', 'question_mark', etc.


class EventMessageReaction(BaseModel):
    """todo"""

    reaction_id: int
    event_message_id: int
    user_id: str
    reaction_type: str
    created_at: datetime.datetime


def _string_to_reaction_type(*, reaction_type_str: str) -> enumerations.ReactionType:
    """Convert string reaction type to ReactionType enum.

    Args:
        reaction_type_str: Description for reaction_type_str.
    """
    try:
        return enumerations.ReactionType(reaction_type_str)
    except ValueError:
        # If not a valid enum value, raise error
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reaction_type: {reaction_type_str}. "
            f"Valid types: {', '.join([e.value for e in enumerations.ReactionType])}",
        )


# --- API Endpoints ---
@router.get("")
async def get_event_message_reactions(
    *,
    project_db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],
    event_message_id: int | None = Query(default=None),
    event_id: int | None = Query(default=None),
) -> list[EventMessageReaction]:
    """Get all reactions for a specific event message or all reactions for an event.

        Path Parameters:
            project_id: The project ID (required to determine schema)
        Query Parameters:
            event_message_id: The ID of the message to get reactions for (optional)
            event_id: The ID of the event to get all reactions for (optional)

        Returns:
            List of reactions for the message(s)

    Args:
        project_db: Description for project_db.
        event_message_id: Description for event_message_id.
        event_id: Description for event_id.
    """

    if event_id is not None:
        # Batch fetch all reactions for the event
        reaction_models = (
            await crud_event_message_reactions.get_event_message_reactions_by_event_id(
                db=project_db, event_id=event_id
            )
        )
    elif event_message_id is not None:
        # Single message reactions (backward compatibility)
        reaction_models = (
            await crud_event_message_reactions.get_event_message_reactions(
                db=project_db, event_message_id=event_message_id
            )
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either event_message_id or event_id must be provided",
        )

    return [
        EventMessageReaction(
            reaction_id=r.reaction_id,
            event_message_id=r.event_message_id,
            user_id=r.user_id,
            reaction_type=r.reaction_type.value,
            created_at=r.created_at,
        )
        for r in reaction_models
    ]


@router.post("")
async def toggle_event_message_reaction(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    project_schema: Annotated[str, Depends(get_project_name_short_async)] = "",
    reaction: EventMessageReactionCreate,
    user_data: Annotated[UserAuthed, Depends(get_user)],
) -> EventMessageReaction:
    """Toggle a reaction on a message (add if not exists, remove if exists).

    Request Body:
        event_message_id: The ID of the message
        reaction_type: The type of reaction ('thumbs_up', 'eyes',
            'question_mark', etc.)

    Returns:
        The created reaction (if added) or the deleted reaction info (if removed)

    Args:
        project_db: Description for project_db.
        project_schema: Description for project_schema.
        reaction: Description for reaction.
        user_data: Description for user_data.
    """
    # Convert string to enum
    reaction_type_enum = _string_to_reaction_type(
        reaction_type_str=reaction.reaction_type
    )

    # Verify message exists and is not deleted before allowing reaction
    message = await crud_event_messages.get_event_message_by_id(
        event_message_id=reaction.event_message_id
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )
    if not message:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Event message {reaction.event_message_id} not found or has been "
                "deleted"
            ),
        )

    # Check if reaction already exists
    existing = await crud_event_message_reactions.get_event_message_reaction(
        event_message_id=reaction.event_message_id,
        user_id=user_data.user_id,
        reaction_type=reaction_type_enum,
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )

    if existing:
        # Remove reaction (toggle off)
        await crud_event_message_reactions.delete_event_message_reaction(
            db=project_db, reaction=existing
        )
        await project_db.commit()
        # Return the deleted reaction info
        return EventMessageReaction(
            reaction_id=existing.reaction_id,
            event_message_id=existing.event_message_id,
            user_id=existing.user_id,
            reaction_type=existing.reaction_type.value,
            created_at=existing.created_at,
        )
    else:
        # Add reaction
        reaction_model = (
            await crud_event_message_reactions.create_event_message_reaction(
                db=project_db,
                event_message_id=reaction.event_message_id,
                user_id=user_data.user_id,
                reaction_type=reaction_type_enum,
            )
        )
        # Access all attributes before commit to avoid lazy loading issues
        reaction_id = reaction_model.reaction_id
        event_message_id = reaction_model.event_message_id
        user_id = reaction_model.user_id
        reaction_type_value = reaction_model.reaction_type.value
        created_at = reaction_model.created_at

        await project_db.commit()

        return EventMessageReaction(
            reaction_id=reaction_id,
            event_message_id=event_message_id,
            user_id=user_id,
            reaction_type=reaction_type_value,
            created_at=created_at,
        )
