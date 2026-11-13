"""
Model for storing artist metric snapshots over time
Used for predictions and trend analysis
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base


class ArtistSnapshot(Base):
    """
    Snapshot des métriques d'un artiste à un instant T.
    Utilisé pour calculer les prédictions et tendances.
    """
    __tablename__ = "artist_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    
    # Lien vers l'artiste (via son nom normalisé)
    artist_name = Column(String(255), nullable=False, index=True)
    artist_name_normalized = Column(String(255), nullable=False, index=True)
    
    # Workspace isolation
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)
    workspace = relationship("Workspace", backref="artist_snapshots")
    
    # Timestamp du snapshot
    snapshot_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # === Métriques Spotify ===
    spotify_monthly_listeners = Column(Integer, nullable=True)
    spotify_followers = Column(Integer, nullable=True)
    spotify_popularity = Column(Integer, nullable=True)  # 0-100
    
    # === Métriques TikTok ===
    tiktok_followers = Column(Integer, nullable=True)
    tiktok_likes = Column(Integer, nullable=True)
    
    # === Métriques YouTube ===
    youtube_subscribers = Column(Integer, nullable=True)
    youtube_views_30d = Column(Integer, nullable=True)
    youtube_total_views = Column(Integer, nullable=True)
    
    # === Métriques Instagram ===
    instagram_followers = Column(Integer, nullable=True)
    
    # === Métriques Concerts ===
    concerts_next_30d = Column(Integer, default=0)
    concerts_next_90d = Column(Integer, default=0)
    
    # === Qualité des données ===
    source_quality_score = Column(Float, nullable=True)  # Optional empirical calibration; never invent a default
    sources_used = Column(String(500), nullable=True)  # Comma-separated
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Index composite pour recherches optimisées
    __table_args__ = (
        Index('ix_artist_snapshots_artist_date', 'artist_name_normalized', 'snapshot_date'),
        Index('ix_artist_snapshots_workspace_artist', 'workspace_id', 'artist_name_normalized'),
    )
    
    def __repr__(self):
        return f"<ArtistSnapshot(artist={self.artist_name}, date={self.snapshot_date})>"
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalise le nom d'artiste pour les comparaisons"""
        import unicodedata
        import re
        # Lowercase
        name = name.lower().strip()
        # Remove accents
        name = unicodedata.normalize('NFD', name)
        name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
        # Remove special chars
        name = re.sub(r'[^a-z0-9\s]', '', name)
        # Normalize spaces
        name = re.sub(r'\s+', ' ', name).strip()
        return name
