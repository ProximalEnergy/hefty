import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel

from app import dependencies
from app._crud.projects import (
    event_message_reactions as crud_event_message_reactions,
)
from app._crud.projects import event_messages as crud_event_messages
from app.dependencies import (
    _with_async_db,
    check_project_access_async,
    get_project_name_short_async,
)
from core import enumerations

router = APIRouter(
    prefix="/projects/{project_id}/event-message-reactions",
    tags=["event_message_reactions"],
    dependencies=[Depends(check_project_access_async)],
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
        reaction_type_str: TODO: describe.
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
    project_id: Annotated[UUID, Path(...)],
    event_message_id: int | None = Query(default=None),
    event_id: int | None = Query(default=None),
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
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
        project_id: TODO: describe.
        event_message_id: TODO: describe.
        event_id: TODO: describe.
        user_data: TODO: describe.
    """
    project_name_short = await get_project_name_short_async(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    async with _with_async_db(schema=project_name_short) as project_db:
        if event_id is not None:
            # Batch fetch all reactions for the event
            reaction_models = await crud_event_message_reactions.get_event_message_reactions_by_event_id(
                db=project_db, event_id=event_id
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
    project_id: Annotated[UUID, Path(...)],
    reaction: EventMessageReactionCreate,
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
) -> EventMessageReaction:
    """Toggle a reaction on a message (add if not exists, remove if exists).

    Path Parameters:
        project_id: The project ID (required to determine schema)
    Request Body:
        event_message_id: The ID of the message
        reaction_type: The type of reaction ('thumbs_up', 'eyes',
            'question_mark', etc.)

    Returns:
        The created reaction (if added) or the deleted reaction info (if removed)

    Args:
        project_id: TODO: describe.
        reaction: TODO: describe.
        user_data: TODO: describe.
    """
    project_name_short = await get_project_name_short_async(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Convert string to enum
    reaction_type_enum = _string_to_reaction_type(
        reaction_type_str=reaction.reaction_type
    )

    async with _with_async_db(schema=project_name_short) as project_db:
        # Verify message exists and is not deleted before allowing reaction
        message = await crud_event_messages.get_event_message_by_id(
            db=project_db, event_message_id=reaction.event_message_id
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
            db=project_db,
            event_message_id=reaction.event_message_id,
            user_id=user_data.user_id,
            reaction_type=reaction_type_enum,
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
