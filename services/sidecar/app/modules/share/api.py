"""Share cards: the caption and the X link for an achievement. The image is drawn by the
renderer and saved or copied through Electron; nothing is uploaded by the app."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.schemas import StrictIn
from app.modules.share import captions

router = APIRouter(prefix="/share", tags=["share"])


class ShareIn(StrictIn):
    # The `share` object from a trainer message: {"kind": "pr", "exercise": ..., ...}.
    payload: dict[str, Any]


class ShareCardOut(BaseModel):
    kind: str
    title: str
    headline: str
    detail: str
    caption: str
    # Opens X's own post composer with the caption filled in (nothing is posted for you).
    x_url: str
    version: str = captions.SHARE_VERSION


@router.post("/card", response_model=ShareCardOut)
def share_card(body: ShareIn) -> ShareCardOut:
    """Text for a share card: title, headline, detail, caption and the X web-intent link.
    Only the achievement goes in; never body weight, photos or profile data."""
    try:
        c = captions.build(body.payload)
    except captions.ShareError as e:
        raise HTTPException(422, str(e)) from e
    return ShareCardOut(
        kind=c.kind,
        title=c.title,
        headline=c.headline,
        detail=c.detail,
        caption=c.caption,
        x_url=c.x_url,
    )
