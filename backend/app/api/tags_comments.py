"""
Tags & Comments System for Opportunities
Custom labels, comments, favorites
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, and_, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import Session, relationship
from pydantic import BaseModel, Field
from collections import defaultdict

from app.db import get_db
from app.db.base import Base
from app.db.models.user import User
from app.db.models.opportunity import Opportunity
from app.api.deps import get_current_user

router = APIRouter(prefix="/tags", tags=["tags"])


# ============================================================================
# DATABASE MODELS
# ============================================================================

# Association table for opportunity-tags many-to-many
# Use extend_existing to avoid conflicts if already defined elsewhere
opportunity_tags = Table(
    'custom_opportunity_tags',
    Base.metadata,
    Column('opportunity_id', Integer, ForeignKey('opportunities.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    extend_existing=True
)


class Tag(Base):
    """Custom tag/label model"""
    __tablename__ = "tags"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20), default="#3B82F6")  # Tailwind blue-500
    icon = Column(String(50), nullable=True)  # Optional emoji or icon name
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_system = Column(Boolean, default=False)  # System tags can't be deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships - use unique backref names to avoid conflicts
    user = relationship("User", backref="user_tags")
    opportunities = relationship(
        "Opportunity",
        secondary=opportunity_tags,
        backref="opportunity_tags_rel",
        lazy="dynamic"
    )


class Comment(Base):
    """Comment on an opportunity"""
    __tablename__ = "comments"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=True)  # Internal = not visible to external
    parent_id = Column(Integer, ForeignKey("comments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - use unique backref names to avoid conflicts
    user = relationship("User", backref="user_comments")
    opportunity = relationship("Opportunity", backref="opportunity_comments")
    replies = relationship("Comment", backref="comment_parent", remote_side=[id])


class Favorite(Base):
    """User favorites/starred opportunities"""
    __tablename__ = "favorites"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = None


class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    icon: Optional[str]
    is_system: bool
    opportunities_count: int = 0
    
    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    is_internal: bool = True
    parent_id: Optional[int] = None


class CommentResponse(BaseModel):
    id: int
    content: str
    is_internal: bool
    user_id: int
    user_name: str
    created_at: datetime
    updated_at: datetime
    parent_id: Optional[int] = None
    replies_count: int = 0
    
    class Config:
        from_attributes = True


# ============================================================================
# TAG ENDPOINTS
# ============================================================================

@router.get("")
def list_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List all tags for current user"""
    tags = db.query(Tag).filter(Tag.user_id == current_user.id).all()
    
    result = []
    for tag in tags:
        count = len(tag.opportunities) if tag.opportunities else 0
        result.append({
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "icon": tag.icon,
            "is_system": tag.is_system,
            "opportunities_count": count
        })
    
    return result


@router.post("")
def create_tag(
    data: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new tag"""
    # Check if tag with same name exists
    existing = db.query(Tag).filter(
        Tag.user_id == current_user.id,
        func.lower(Tag.name) == data.name.lower()
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists"
        )
    
    tag = Tag(
        name=data.name,
        color=data.color,
        icon=data.icon,
        user_id=current_user.id
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    
    return {
        "id": tag.id,
        "name": tag.name,
        "color": tag.color,
        "icon": tag.icon,
        "is_system": tag.is_system,
        "opportunities_count": 0
    }


@router.put("/{tag_id}")
def update_tag(
    tag_id: int,
    data: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a tag"""
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == current_user.id
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system tags")
    
    if data.name is not None:
        tag.name = data.name
    if data.color is not None:
        tag.color = data.color
    if data.icon is not None:
        tag.icon = data.icon
    
    db.commit()
    
    return {
        "id": tag.id,
        "name": tag.name,
        "color": tag.color,
        "icon": tag.icon,
        "is_system": tag.is_system,
        "opportunities_count": len(tag.opportunities)
    }


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a tag"""
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == current_user.id
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system tags")
    
    db.delete(tag)
    db.commit()
    
    return {"status": "deleted"}


@router.post("/opportunities/{opportunity_id}/tags/{tag_id}")
def add_tag_to_opportunity(
    opportunity_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Add a tag to an opportunity"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == current_user.id
    ).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag not in opportunity.tags:
        opportunity.tags.append(tag)
        db.commit()
    
    return {"status": "added"}


@router.delete("/opportunities/{opportunity_id}/tags/{tag_id}")
def remove_tag_from_opportunity(
    opportunity_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Remove a tag from an opportunity"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == current_user.id
    ).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag in opportunity.tags:
        opportunity.tags.remove(tag)
        db.commit()
    
    return {"status": "removed"}


@router.get("/opportunities/{opportunity_id}")
def get_opportunity_tags(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get all tags for an opportunity"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Filter to user's tags only
    user_tags = [t for t in opportunity.tags if t.user_id == current_user.id]
    
    return [
        {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "icon": tag.icon
        }
        for tag in user_tags
    ]


# ============================================================================
# COMMENT ENDPOINTS
# ============================================================================

comments_router = APIRouter(prefix="/comments", tags=["comments"])


@comments_router.get("/opportunities/{opportunity_id}")
def get_comments(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get all comments for an opportunity"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    comments = db.query(Comment).filter(
        Comment.opportunity_id == opportunity_id,
        Comment.parent_id.is_(None)  # Top-level comments only
    ).order_by(Comment.created_at.desc()).all()
    
    result = []
    for comment in comments:
        replies = db.query(Comment).filter(Comment.parent_id == comment.id).count()
        result.append({
            "id": comment.id,
            "content": comment.content,
            "is_internal": comment.is_internal,
            "user_id": comment.user_id,
            "user_name": comment.user.full_name or comment.user.email,
            "created_at": comment.created_at.isoformat(),
            "updated_at": comment.updated_at.isoformat(),
            "parent_id": comment.parent_id,
            "replies_count": replies
        })
    
    return result


@comments_router.post("/opportunities/{opportunity_id}")
def create_comment(
    opportunity_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a comment on an opportunity"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Validate parent if provided
    if data.parent_id:
        parent = db.query(Comment).filter(
            Comment.id == data.parent_id,
            Comment.opportunity_id == opportunity_id
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")
    
    comment = Comment(
        opportunity_id=opportunity_id,
        user_id=current_user.id,
        content=data.content,
        is_internal=data.is_internal,
        parent_id=data.parent_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return {
        "id": comment.id,
        "content": comment.content,
        "is_internal": comment.is_internal,
        "user_id": comment.user_id,
        "user_name": current_user.full_name or current_user.email,
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
        "parent_id": comment.parent_id,
        "replies_count": 0
    }


@comments_router.put("/{comment_id}")
def update_comment(
    comment_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a comment"""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.user_id == current_user.id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    comment.content = data.content
    comment.is_internal = data.is_internal
    db.commit()
    
    return {
        "id": comment.id,
        "content": comment.content,
        "is_internal": comment.is_internal,
        "user_id": comment.user_id,
        "user_name": current_user.full_name or current_user.email,
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
        "parent_id": comment.parent_id,
        "replies_count": 0
    }


@comments_router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a comment"""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.user_id == current_user.id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    db.delete(comment)
    db.commit()
    
    return {"status": "deleted"}


@comments_router.get("/opportunities/{opportunity_id}/count")
def get_comments_count(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, int]:
    """Get comment count for an opportunity"""
    count = db.query(Comment).filter(
        Comment.opportunity_id == opportunity_id
    ).count()
    
    return {"count": count}


# ============================================================================
# FAVORITES ENDPOINTS
# ============================================================================

favorites_router = APIRouter(prefix="/favorites", tags=["favorites"])


@favorites_router.get("")
def get_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[int]:
    """Get all favorite opportunity IDs for current user"""
    favorites = db.query(Favorite.opportunity_id).filter(
        Favorite.user_id == current_user.id
    ).all()
    
    return [f[0] for f in favorites]


@favorites_router.post("/{opportunity_id}")
def add_favorite(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Add an opportunity to favorites"""
    opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.opportunity_id == opportunity_id
    ).first()
    
    if existing:
        return {"status": "already_favorited"}
    
    favorite = Favorite(
        user_id=current_user.id,
        opportunity_id=opportunity_id
    )
    db.add(favorite)
    db.commit()
    
    return {"status": "added"}


@favorites_router.delete("/{opportunity_id}")
def remove_favorite(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Remove an opportunity from favorites"""
    favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.opportunity_id == opportunity_id
    ).first()
    
    if not favorite:
        return {"status": "not_found"}
    
    db.delete(favorite)
    db.commit()
    
    return {"status": "removed"}


@favorites_router.get("/{opportunity_id}/check")
def check_favorite(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, bool]:
    """Check if an opportunity is favorited"""
    exists = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.opportunity_id == opportunity_id
    ).first() is not None
    
    return {"is_favorite": exists}
